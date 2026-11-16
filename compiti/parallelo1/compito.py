"""
Compito parallelo1 (registratori-kit) per il COMPUTERONE: si possono interrogare piu' registratori Focus insieme?
VERSION 0.1.0 (16/11/2026)

Dario, 16/11/2026: come interrogare piu' registratori contemporaneamente. Il ponte li fa uno alla volta (SDK =
threading.Lock()) e ogni collegamento P2P prende 30-60 secondi: un giro su ~300 kit dura ore. La libreria e' quella di
UVMS, che tiene collegati molti registratori insieme. Questo compito misura due strade sugli STESSI kit (fino a 40,
scelti fra quelli che rispondono, dall'elenco del sito https://prova-nvr-remoto.vercel.app op=stato), con la sola
lettura leggera (collegamento, modello, canali, minuti registrati oggi; niente video, niente comandi alle telecamere):
  A) piu' collegamenti nella stessa libreria: un processo, una istanza, N Connect insieme (N = 4, 8, 16), le funzioni
     di ritorno smistate per hSERVER (parallelo.LibreriaFocus);
  B) piu' processi, ognuno con la sua copia della libreria (cartella FocusNetSDK copiata) e una parte dei kit, uno alla
     volta (N = 2, 4, 8). «Due processi con la libreria Focus insieme: mai provato» fino a qui.
La base e' N=1 (un processo, un collegamento alla volta: come il ponte), e vale per tutte e due le strade.
Ogni prova gira in processi a parte (lavoro.py), cosi' un crash della libreria non ferma il compito: si vede dal
codice d'uscita (0xC0000005) e da guasto_memoria.txt.

Ordine: N=1, B2, A4, B4, A8, B8, A16 (prima gli N piccoli), 30 s di pausa fra una prova e l'altra. Una strada si
ferma da sola alla prima prova con un crash o con i falliti saliti di piu' di 5 punti rispetto a N=1; tetto 2 ore per
tutto il compito (la prova in corso viene fermata e conta come «fermata dal tetto»).

Criterio scritto prima (parallelo.CRITERIO): una strada vince se con N=8 fa il giro in meno di un quarto del tempo di
N=1 senza piu' falliti di N=1.

Uscita: uscita/parallelo.json (kit per etichetta, mai l'UID; per ogni prova tempo totale, riusciti e falliti contro
N=1, persi e guadagnati, crash e codici d'uscita, memoria per processo e in tutto, i risultati kit per kit), il
verdetto, uscita/avanzamento.txt, uscita/prove/<prova>_pN_*.txt (avanzamento e guasti dei processi).
Le credenziali: focus_accesso.txt nella cartella del compito (come il ponte); restano sul PC. I lavori con l'UID
(cartella lavori/, fuori da uscita) si cancellano alla fine.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

VERSION = "0.1.0"
C = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, C)
U = os.path.join(C, "uscita")
L = os.path.join(C, "lavori")
API = "https://prova-nvr-remoto.vercel.app/api/p2p"
DESTINATARIO = "https://mappakit.alma/nvr-remoto"
PC = os.environ.get("COMPUTERNAME", "PC")[:40]
NOFIN = 0x08000000 if os.name == "nt" else 0          # niente finestra
SOTTO_NORMALE = 0x00004000 if os.name == "nt" else 0  # come i processi a parte del ponte

DIFETTI = {
    "kit_quanti": 40,
    "seme": 1,
    "ordine": [["1", 1], ["B", 2], ["A", 4], ["B", 4], ["A", 8], ["B", 8], ["A", 16]],
    "tetto_ore": 2.0,
    "pausa_s": 30,
    "attesa": 40,                 # secondi per l'esito di un collegamento (come collega_con del ponte)
    "soglia_punti": 5.0,
    "minuti_minimi_prova": 3,     # sotto questo tempo rimasto non si comincia un'altra prova
    "copia_libreria": True,       # strada B: ogni processo con la sua cartella FocusNetSDK
    "agenti_p2p": None,           # P2PAgentInit: None = 16 (come il ponte), o 2N se N e' piu' grande di 8
}

import parallelo as pa   # noqa: E402


def av(t):
    os.makedirs(U, exist_ok=True)
    with open(os.path.join(U, "avanzamento.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + t + "\n")
    print(t, flush=True)


def carica_cfg():
    cfg = dict(DIFETTI)
    f = os.path.join(C, "parallelo.json")
    if os.path.exists(f):
        cfg.update({k: v for k, v in json.load(open(f, encoding="utf-8")).items() if not k.startswith("_")})
    return cfg


def agenti(cfg, n):
    if cfg.get("agenti_p2p"):
        return int(cfg["agenti_p2p"])
    return max(16, 2 * int(n))


# ------------------------------------------------------------------ i kit

def biglietto():
    import drive_alma
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    chiave = drive_alma.file_chiave((C, os.path.dirname(sys.executable)))
    cred = service_account.IDTokenCredentials.from_service_account_file(chiave, target_audience=DESTINATARIO)
    cred.refresh(Request())
    return cred.token


def kit_da_provare(cfg):
    """kit.json nella cartella del compito (se c'e'), altrimenti op=stato del sito. Una volta scelti restano in
    lavori/kit.json: un compito ripreso usa gli stessi."""
    tenuti = os.path.join(L, "kit.json")
    if os.path.exists(tenuti):
        return json.load(open(tenuti, encoding="utf-8")), "ripresi"
    f = os.path.join(C, "kit.json")
    if os.path.exists(f):
        kit, da = json.load(open(f, encoding="utf-8"))[:int(cfg["kit_quanti"])], "kit.json"
    else:
        req = urllib.request.Request(f"{API}?op=stato", headers={"Authorization": "Bearer " + biglietto()})
        with urllib.request.urlopen(req, timeout=90) as r:
            stato = json.loads(r.read().decode())
        kit, da = pa.scegli_kit(stato, int(cfg["kit_quanti"]), int(cfg["seme"])), "sito op=stato"
    os.makedirs(L, exist_ok=True)
    json.dump(kit, open(tenuti, "w", encoding="utf-8"))
    return kit, da


# ------------------------------------------------------------------ una prova

def ambiente_figlio():
    """Come il ponte: PyInstaller riparte da capo, e nel PATH non c'e' una cartella FocusNetSDK."""
    env = dict(os.environ)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    for k in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL", "TCL_LIBRARY",
              "TK_LIBRARY"):
        env.pop(k, None)
    env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep) if p and "focusnetsdk" not in p.lower())
    return env


def comando_figlio(d):
    if getattr(sys, "frozen", False):          # dentro Kit_Rifiuti: l'exe fa girare d/compito.py
        return [sys.executable, "--compito", d]
    return [sys.executable, os.path.join(d, "compito.py"), d]


def _leggi_json(f):
    try:
        return json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _copia_testo(da, a, massimo=200_000):
    try:
        if os.path.exists(da) and 0 < os.path.getsize(da):
            with open(da, "rb") as fh:
                dati = fh.read()[-massimo:]
            os.makedirs(os.path.dirname(a), exist_ok=True)
            with open(a, "wb") as fh:
                fh.write(dati)
    except OSError:
        pass


def una_prova(nome, strada, n, kit, cfg, scadenza, limite=None):
    """Lancia i processi della prova e li aspetta fino alla fine, al tetto (scadenza) o al limite della prova (una
    prova parallela che dura piu' del doppio di N=1 e' ferma dentro la libreria: si conta come un crash)."""
    base = os.path.join(L, nome)
    shutil.rmtree(base, ignore_errors=True)
    if strada == "B":
        gruppi, fili = pa.parti(kit, n), 1
    else:
        gruppi, fili = [kit], n
    cartelle = []
    for i, g in enumerate(gruppi):
        d = os.path.join(base, f"p{i + 1}")
        os.makedirs(os.path.join(d, "uscita"), exist_ok=True)
        shutil.copy2(os.path.join(C, "lavoro.py"), os.path.join(d, "compito.py"))
        sdk = os.path.join(C, "FocusNetSDK")
        if strada == "B" and cfg.get("copia_libreria") and os.path.isdir(sdk):
            shutil.copytree(sdk, os.path.join(d, "FocusNetSDK"))
            sdk = os.path.join(d, "FocusNetSDK")
        json.dump({"radice": C, "sdk": sdk, "fili": fili, "agenti_p2p": agenti(cfg, fili), "attesa": cfg["attesa"],
                   "kit": g}, open(os.path.join(d, "lavoro.json"), "w", encoding="utf-8"))
        cartelle.append(d)
    av(f"{nome}: {len(cartelle)} processi x {fili} collegamenti insieme, {len(kit)} kit")
    t0 = time.time()
    procs = []
    for d in cartelle:
        procs.append(subprocess.Popen(comando_figlio(d), cwd=d, env=ambiente_figlio(), stdin=subprocess.DEVNULL,
                                      stdout=open(os.path.join(d, "uscita_processo.txt"), "a"),
                                      stderr=subprocess.STDOUT, creationflags=SOTTO_NORMALE | NOFIN))
    fermata_tetto, bloccata, ultimo = False, False, time.time()
    while any(p.poll() is None for p in procs):
        time.sleep(0.5)
        if time.time() > scadenza or (limite and time.time() > limite):
            fermata_tetto = time.time() > scadenza
            bloccata = not fermata_tetto
            for p in procs:
                if p.poll() is None:
                    p.kill()
            for p in procs:
                try:
                    p.wait(60)
                except subprocess.TimeoutExpired:
                    pass
            break
        if time.time() - ultimo >= 60:
            ultimo = time.time()
            fatti = sum(len((_leggi_json(os.path.join(d, "uscita", "risultato.json")) or {}).get("risultati") or [])
                        for d in cartelle)
            av(f"{nome}: {fatti}/{len(kit)} kit dopo {round(time.time() - t0)} s")
    secondi = round(time.time() - t0, 1)
    processi, per_kit, crash = [], {}, []
    for i, (d, p) in enumerate(zip(cartelle, procs)):
        es = _leggi_json(os.path.join(d, "uscita", "risultato.json")) or {}
        codice = p.returncode
        guasto = ""
        try:
            guasto = open(os.path.join(d, "uscita", "guasto_memoria.txt"), encoding="utf-8", errors="replace").read()
        except OSError:
            pass
        caduto = not fermata_tetto and (codice not in (0, None) or not es.get("finito"))
        if caduto:
            motivo = (es.get("errore") or ("ferma oltre il doppio del tempo di N=1, uccisa" if bloccata
                                           else "codice " + str(pa.codice_leggibile(codice))))
            crash.append(f"processo {i + 1}: {motivo}")
        for r in es.get("risultati") or []:
            per_kit[r["kit"]] = r
        processi.append({"processo": i + 1, "kit": len(gruppi[i]), "codice": pa.codice_leggibile(codice),
                         "finito": bool(es.get("finito")), "caduto": caduto, "errore": es.get("errore"),
                         "secondi_libreria": es.get("secondi_libreria"), "secondi_lavoro": es.get("secondi_lavoro"),
                         "massimo_insieme": es.get("massimo_insieme"), "esiti_orfani": es.get("esiti_orfani"),
                         "memoria": es.get("memoria") or es.get("memoria_dopo_libreria"),
                         "chiuso": es.get("chiuso"), "guasto_memoria": guasto[-3000:] or None})
        for nome_f in ("avanzamento.txt", "guasto_memoria.txt", "registro_python.txt"):
            _copia_testo(os.path.join(d, "uscita", nome_f), os.path.join(U, "prove", f"{nome}_p{i + 1}_{nome_f}"))
        _copia_testo(os.path.join(d, "uscita_processo.txt"), os.path.join(U, "prove", f"{nome}_p{i + 1}_uscita.txt"))
    picchi = [x["memoria"].get("picco_mb") for x in processi if isinstance(x.get("memoria"), dict)
              and x["memoria"].get("picco_mb") is not None]
    return {"nome": nome, "strada": strada, "n": n, "processi_n": len(cartelle), "fili": fili,
            "agenti_p2p": agenti(cfg, fili), "secondi": secondi, "fermata_tetto": fermata_tetto,
            "crash": "; ".join(crash) or None, "processi": processi,
            "memoria_mb": {"picco_per_processo_max": max(picchi) if picchi else None,
                           "somma_picchi": round(sum(picchi), 1) if picchi else None},
            "kit_fatti": len(per_kit), "per_kit": [per_kit[k["etichetta"]] for k in kit if k["etichetta"] in per_kit]}


# ------------------------------------------------------------------ il giro delle prove

def main():
    os.makedirs(U, exist_ok=True)
    cfg = carica_cfg()
    f_es, f_stato = os.path.join(U, "parallelo.json"), os.path.join(U, "stato.json")
    stato = _leggi_json(f_stato) or {}
    if stato.get("fase") == "finito":
        av("compito gia' finito: non rifaccio niente")
        return
    t_inizio = time.time()
    scadenza = t_inizio + float(cfg["tetto_ore"]) * 3600
    prima = _leggi_json(f_es) or {}
    es = {"versione": VERSION, "pc": PC, "inizio": time.strftime("%Y-%m-%d %H:%M:%S"),
          "parametri": {k: cfg[k] for k in DIFETTI}, "criterio": pa.CRITERIO, "ripreso": bool(prima.get("prove")),
          "prove": prima.get("prove") or [], "fermate": prima.get("fermate") or {}}

    def salva():
        es["verdetto"] = pa.verdetto(es["prove"])
        tmp = f_es + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(es, fh, ensure_ascii=False, indent=1, default=str)
        os.replace(tmp, f_es)

    def segna(fase):
        stato.update(fase=fase, ora=time.strftime("%Y-%m-%d %H:%M:%S"))
        json.dump(stato, open(f_stato, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    av(f"parallelo1 {VERSION} su {PC}")
    segna("prove")
    try:
        kit, da = kit_da_provare(cfg)
        es["kit"] = [k["etichetta"] for k in kit]
        es["kit_da"] = da
        av(f"{len(kit)} kit da {da}")
        if not kit:
            es["esito"] = "nessun kit che risponde"
            return
        etichette = es["kit"]
        fatte = {p["nome"] for p in es["prove"]}
        for strada, n in cfg["ordine"]:
            nome = "N1" if strada == "1" else f"{strada}{n}"
            if nome in fatte:
                continue
            if strada != "1" and strada in es["fermate"]:
                av(f"{nome}: saltata, strada {strada} ferma ({es['fermate'][strada]})")
                continue
            rimasti = scadenza - time.time()
            if rimasti < float(cfg["minuti_minimi_prova"]) * 60:
                es["fermate"]["tetto"] = f"tetto di {cfg['tetto_ore']} ore: {nome} e le prove dopo non fatte"
                av(es["fermate"]["tetto"])
                break
            if es["prove"]:
                time.sleep(float(cfg["pausa_s"]))
            base = next((x for x in es["prove"] if x["strada"] == "1"), None)
            limite = time.time() + max(600.0, 2 * base["secondi"]) if base else None
            p = una_prova(nome, strada, int(n), kit, cfg, scadenza, limite)
            base = base or (p if strada == "1" else None)
            ok_base = {r["kit"]: r["ok"] for r in base["per_kit"]} if base else {}
            p["confronto"] = pa.confronta(ok_base, {r["kit"]: r["ok"] for r in p["per_kit"]}, etichette)
            es["prove"].append(p)
            c = p["confronto"]
            av(f"{nome}: {c['riusciti']}/{c['kit']} riusciti in {p['secondi']} s (N=1: {base['secondi'] if base else '-'} s), "
               f"falliti {c['falliti']} contro {c['falliti_base']}, crash {p['crash'] or 'no'}, "
               f"memoria {p['memoria_mb']}" + (" - FERMATA DAL TETTO" if p["fermata_tetto"] else ""))
            if strada == "1":
                if p["crash"] or not c["riusciti"]:
                    es["fermate"]["tutto"] = "N=1 senza kit riusciti o con un crash: niente da confrontare"
                    av(es["fermate"]["tutto"])
                    salva()
                    break
            else:
                motivo = pa.da_fermare(p, float(cfg["soglia_punti"]))
                if motivo:
                    es["fermate"][strada] = motivo
                    av(f"strada {strada} ferma: {motivo}")
            salva()
            if p["fermata_tetto"]:
                es["fermate"]["tetto"] = f"tetto di {cfg['tetto_ore']} ore durante {nome}"
                break
    except Exception as ex:   # noqa: BLE001
        es["errore"] = f"{type(ex).__name__}: {str(ex)[:400]}"
        av(es["errore"])
    finally:
        es["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
        es["minuti"] = round((time.time() - t_inizio) / 60, 1)
        salva()
        v = es["verdetto"]
        av("verdetto: " + json.dumps({s: x.get("perche") for s, x in v.get("strade", {}).items()}, ensure_ascii=False)
           + f" -> vince {v.get('vince') or 'nessuna'}")
        shutil.rmtree(L, ignore_errors=True)   # i lavori con l'UID e le copie della libreria restano solo sul PC: via
        segna("finito")
        av("fatto")


if __name__ == "__main__":
    main()
