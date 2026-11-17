"""
Compito fps1 (registratori-kit) per il COMPUTERONE: a quanti fotogrammi al secondo registrano DAVVERO le telecamere
di tutti i kit, misurato sul registratore Focus in P2P (senza VPN e senza le password delle telecamere Dahua).
VERSION 0.1.0 (17/11/2026)

Perche': i .ssf sono H.264 grezzo e Kit_Rifiuti li tratta a 25 fps; dagli scarichi passati alcune telecamere ne fanno
circa 17,857 (KIT252, 261, 341, 373, 461, 506, 632 su circa 60 misurate): lette a 25 scorrono 1,4 volte piu' veloci.
Serve la misura di TUTTE le telecamere.

Come gira (Dario, 17/11: molti kit rispondono solo in certe ore, i solari si spengono di notte e altri di giorno):
24 ore, e prende il posto del ponte sul COMPUTERONE anche per la pagina «Registrazioni dei kit». Fa il giro del sito
come il ponte (op=prendi: il sito rimette in coda tutti i registratori appena il giro prima e' finito) e per ogni
richiesta, nello stesso collegamento al registratore (lavoro.py, un processo per richiesta):
  1. quello che fa il ponte 0.20.1 nel giro leggero (ponte_pezzi.py, copiato da p2p_ponte6): canali, minuti di oggi e
     delle 24 ore, l'archivio quando il sito lo chiede, le foto delle telecamere una volta al giorno per kit; e lo manda
     al sito con op=esito appena e' pronto, come il ponte;
  2. per i canali che non hanno ancora la misura: 10 secondi di registrazione di un'ora recente in cui il canale
     registra (di giorno se si puo'), fps dai tempi dei fotogrammi dati dal registratore, fotogrammi del file grezzo
     diviso la durata dichiarata, fps dichiarati nell'SPS, risoluzione; poi il video si cancella.
Cosi' ogni kit si riprova a ogni giro finche' ogni suo canale e' misurato, e quelli che rispondono solo in certe
fasce si prendono quando rispondono. Se il sito non risponde per 15 minuti, il compito fa da solo un giro ogni ora sui
kit non ancora misurati (elenco: kit.json, registratori.json dello zip o l'ultimo op=stato), senza mandare niente.

Sola lettura: collegamento, canali, minuti, archivio, riproduzione. Niente impostazioni ai registratori o alle
telecamere. Un kit alla volta («insieme»: 1, si puo' alzare in fps.json; ogni processo in piu' ha la sua copia della
libreria). Tetto di 8 minuti per kit (il processo e' ucciso dopo), 24 ore in tutto. Si ferma da solo a fine tempo,
con ferma.txt nella cartella del compito o con un compito nuovo per questo PC su Drive. Ripreso dopo una caduta,
riparte dallo stato salvato (uscita/risultato.json, lavori/) e conta le 24 ore dal primo avvio.

Uscita (uscita/, che Kit_Rifiuti manda su Drive in risultato_fps1.zip): risultato.json (per kit: le ore in cui ha
risposto, quante volte no, modello, e per canale fps, fotogrammi, durata, risoluzione, esito; il riassunto con
«telecamere sotto 24 fps»), avanzamento.txt (ultima riga «fatto»), stato.json, guasti/ (i guasti dei processi caduti).
Mai gli UID ne' le password: gli UID stanno solo in lavori/, che si cancella alla fine.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request

VERSION = "0.1.0"
C = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, C)
U = os.path.join(C, "uscita")
L = os.path.join(C, "lavori")
API = "https://prova-nvr-remoto.vercel.app/api/p2p"
DESTINATARIO = "https://mappakit.alma/nvr-remoto"
PC = os.environ.get("COMPUTERNAME", "PC")[:40]
NOFIN = 0x08000000 if os.name == "nt" else 0
SOTTO_NORMALE = 0x00004000 if os.name == "nt" else 0

import fps   # noqa: E402
import ponte_pezzi as pp   # noqa: E402

DIFETTI = {
    "durata_ore": 24,
    "insieme": 1,                  # quanti registratori insieme (processi); piu' di 1 non e' ancora provato (parallelo1)
    "copia_libreria": True,        # con insieme > 1: ogni processo con la sua cartella FocusNetSDK
    "tetto_kit_min": 8,            # poi il processo del kit si uccide
    "grazia_s": 30,                # dopo il tetto del kit, prima di uccidere il processo
    "margine_kit_s": 45,           # il processo smette di scaricare canali quando mancano questi secondi al tetto
    "attesa": 20,                  # secondi per l'esito del collegamento (il ponte nel giro: 12)
    "attesa_fps": 40,              # per ricollegarsi quando il relay sta per chiudersi
    "secondi": 10,                 # quanto si scarica per canale
    "ore_giorno": [9, 17],
    "margine_min": 10,
    "attesa_vuoto": 20,
    "relay_ricollega_s": 240,
    "max_tentativi_canale": 6,     # prove senza misura dopo cui un canale non si scarica piu'
    "soglia_fps": 24.0,
    "misura_fps": True,
    "foto": True,                  # le foto del ponte, una volta al giorno per kit
    "fonte": "sito",               # «sito»: il giro del sito come il ponte; «da_solo»: giro ogni ora, niente al sito
    "sito_muto_min": 15,           # dopo questi minuti senza sito si passa a «da_solo»
    "giro_ogni_min": 60,
    "pausa_coda_vuota_s": 15,
    "controlla_drive": True,
    "solo": [],                    # numeri di kit: se c'e', solo quelli (solo per «da_solo»)
}


# ------------------------------------------------------------------ registri e file

def _riga(nome, t):
    os.makedirs(U, exist_ok=True)
    with open(os.path.join(U, nome), "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%H:%M:%S ") + t + "\n")


def av(t):
    _riga("avanzamento.txt", t)
    print(t, flush=True)


def leggi_json(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def scrivi_json(p, dati):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(dati, fh, ensure_ascii=False, indent=1, default=str)
    os.replace(p + ".tmp", p)


def carica_cfg():
    cfg = dict(DIFETTI)
    d = leggi_json(os.path.join(C, "fps.json"))
    if isinstance(d, dict):
        cfg.update({k: v for k, v in d.items() if not k.startswith("_")})
    return cfg


# ------------------------------------------------------------------ il sito (come il ponte)

_big = {"t": "", "fino": 0}


def biglietto():
    if _big["t"] and time.time() < _big["fino"]:
        return _big["t"]
    import drive_alma
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    chiave = drive_alma.file_chiave((C, os.path.dirname(sys.executable)))
    cred = service_account.IDTokenCredentials.from_service_account_file(chiave, target_audience=DESTINATARIO)
    cred.refresh(Request())
    _big.update(t=cred.token, fino=time.time() + 45 * 60)
    return cred.token


def chiama(op, dati=None):
    """POST (o GET con dati None) al sito del ponte col biglietto dell'account di servizio; FPS1_SITO_FINTO nelle prove."""
    finto = os.environ.get("FPS1_SITO_FINTO")
    if finto:
        import prova_fps1 as pf
        return pf.sito_finto(finto, op, dati)
    req = urllib.request.Request(f"{API}?op={op}", data=None if dati is None else json.dumps(dati).encode(),
                                 method="GET" if dati is None else "POST",
                                 headers={"Authorization": "Bearer " + biglietto(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode() or "{}")


def compito_nuovo_su_drive():
    """Su Drive c'e' un compito con un altro nome per questo PC (o per nessuno)? Allora questo si chiude (come i ponti)."""
    try:
        import drive_alma
        f = drive_alma.trova("compito.zip", (C, os.path.dirname(sys.executable)))
        pr = (f or {}).get("appProperties") or {}
        try:
            pc = drive_alma.nome_del_pc()
        except Exception:   # noqa: BLE001
            pc = PC
        nome, per = str(pr.get("compito") or ""), str(pr.get("pc") or "")
        return bool(nome) and nome != os.path.basename(os.path.normpath(C)) and (not per or per.upper() == str(pc).upper())
    except Exception:   # noqa: BLE001
        return False


# ------------------------------------------------------------------ l'elenco per il giro fatto da solo

def kit_da_solo(cfg):
    """[{uid, numero, etichetta}] per il giro senza sito: kit.json nella cartella, l'op=stato del sito, o
    registratori.json dello zip. Tenuto in lavori/kit.json (ha gli UID)."""
    tenuti = os.path.join(L, "kit.json")
    if os.path.exists(tenuti):
        return leggi_json(tenuti) or []
    kit = None
    f = os.path.join(C, "kit.json")
    if os.path.exists(f):
        kit = leggi_json(f)
    if kit is None:
        try:
            kit, _salt = fps.scegli_kit(chiama("stato"), anche_muti=True, solo=cfg.get("solo"))
        except Exception as ex:   # noqa: BLE001
            av(f"op=stato non letto: {type(ex).__name__}: {str(ex)[:200]}")
    if kit is None and os.path.exists(os.path.join(C, "registratori.json")):
        kit, _salt = fps.kit_da_registratori(leggi_json(os.path.join(C, "registratori.json")), solo=cfg.get("solo"))
    kit = kit or []
    scrivi_json(tenuti, kit)
    return kit


# ------------------------------------------------------------------ un processo per richiesta

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


def libreria_del_posto(cfg, posto):
    sdk = os.path.join(C, "FocusNetSDK")
    if int(cfg["insieme"]) <= 1 or not cfg.get("copia_libreria") or not os.path.isdir(sdk):
        return sdk
    d = os.path.join(L, f"libreria{posto}", "FocusNetSDK")
    if not os.path.isdir(d):
        shutil.copytree(sdk, d)
    return d


def lancia(cfg, posto, kit, rid, serve_archivio, fai_foto, salta, n):
    d = os.path.join(L, f"posto{posto}", f"lavoro{n}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "uscita"), exist_ok=True)
    shutil.copy2(os.path.join(C, "lavoro.py"), os.path.join(d, "compito.py"))
    par = {k: cfg[k] for k in ("tetto_kit_min", "margine_kit_s", "secondi", "ore_giorno", "margine_min", "attesa_vuoto",
                               "relay_ricollega_s", "misura_fps", "attesa_fps")}
    scrivi_json(os.path.join(d, "lavoro.json"), {
        "radice": C, "sdk": libreria_del_posto(cfg, posto), "kit": kit, "rid": rid, "pc": PC,
        "serve_archivio": bool(serve_archivio), "fai_foto": bool(fai_foto), "salta": salta, "attesa": cfg["attesa"],
        "parametri": par})
    p = subprocess.Popen(comando_figlio(d), cwd=d, env=ambiente_figlio(), stdin=subprocess.DEVNULL,
                         stdout=open(os.path.join(d, "uscita_processo.txt"), "a"), stderr=subprocess.STDOUT,
                         creationflags=SOTTO_NORMALE | NOFIN)
    return {"p": p, "d": d, "kit": kit, "rid": rid, "t0": time.time(), "sito_mandato": False, "posto": posto,
            "limite": time.time() + float(cfg["tetto_kit_min"]) * 60 + float(cfg["grazia_s"])}


def codice_leggibile(c):
    if c is None:
        return None
    c = int(c)
    if c < 0:
        c &= 0xFFFFFFFF
    return f"0x{c:08X}" if c > 0xFFFF else str(c)


def manda_al_sito(lav, versione_sito, ok, esito):
    try:
        chiama("esito", {"pc": PC, "versione": versione_sito, "id": lav["rid"], "ok": ok, "esito": esito, "foto": None})
        lav["sito_mandato"] = True
    except Exception as ex:   # noqa: BLE001
        av(f"{lav['kit']['etichetta']}: esito non mandato al sito: {type(ex).__name__}: {str(ex)[:200]}")
        lav["sito_mandato"] = True   # non si riprova: il sito rimette in coda da solo dopo 5 minuti


def guarda(lav, versione_sito):
    """Manda al sito la parte del ponte appena il processo l'ha scritta."""
    if lav["rid"] is None or lav["sito_mandato"]:
        return
    s = leggi_json(os.path.join(lav["d"], "uscita", "sito.json"))
    if s:
        manda_al_sito(lav, versione_sito, bool(s.get("ok")), s.get("esito") or {})


def chiudi(lav, versione_sito, ucciso):
    """Il processo e' finito (o e' stato ucciso): il suo risultato, il guasto se c'e', e il sito avvisato comunque."""
    guarda(lav, versione_sito)
    r = leggi_json(os.path.join(lav["d"], "uscita", "risultato.json")) or {"kit": lav["kit"]["etichetta"], "canali": []}
    codice = lav["p"].returncode
    if ucciso or codice not in (0, None) or not r.get("finito"):
        r["caduto"] = "ucciso al tetto del kit" if ucciso else f"processo caduto, codice {codice_leggibile(codice)}"
        r.setdefault("esito", r["caduto"])
        g = os.path.join(lav["d"], "uscita", "guasto_memoria.txt")
        if os.path.exists(g) and os.path.getsize(g):
            dest = os.path.join(U, "guasti", f"{lav['kit']['etichetta']}_{time.strftime('%m%d_%H%M%S')}.txt")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(g, dest)
    if lav["rid"] is not None and not lav["sito_mandato"]:
        parziale = leggi_json(os.path.join(lav["d"], "uscita", "sito_parziale.json"))
        if parziale:   # il registratore ha risposto, il processo e' caduto dopo (nelle foto): il sito sa che risponde
            es = dict(parziale.get("esito") or {})
            es["errore"] = (r.get("caduto") or "?") + " durante le foto"
            manda_al_sito(lav, versione_sito, True, es)
        else:
            manda_al_sito(lav, versione_sito, False, {"pc": PC, "errore": r.get("caduto") or r.get("esito") or "?"})
    shutil.rmtree(lav["d"], ignore_errors=True)   # anche i video, se ne e' rimasto uno
    return r


# ------------------------------------------------------------------ il giro di 24 ore

def main():
    os.makedirs(U, exist_ok=True)
    os.makedirs(L, exist_ok=True)
    cfg = carica_cfg()
    f_ris, f_stato, f_uid = os.path.join(U, "risultato.json"), os.path.join(U, "stato.json"), os.path.join(L, "uid.json")
    stato = leggi_json(f_stato) or {}
    if stato.get("fase") == "finito":
        av("compito gia' finito: non rifaccio niente")
        av("fatto")
        return
    if not stato.get("primo_avvio"):
        stato["primo_avvio"] = time.time()
    fine = float(stato["primo_avvio"]) + float(cfg["durata_ore"]) * 3600
    prima = leggi_json(f_ris) or {}
    ris = {"compito": "fps1", "versione": VERSION, "pc": PC, "ripreso": bool(prima.get("kit")),
           "primo_avvio": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stato["primo_avvio"])),
           "parametri": {k: cfg[k] for k in DIFETTI}, "fonte": prima.get("fonte") or cfg["fonte"],
           "kit": prima.get("kit") or {}, "riavvii": int(prima.get("riavvii") or 0) + (1 if prima else 0)}
    mappa = leggi_json(f_uid) or {}
    versione_sito = fps.versione_per_il_sito(pp.VERSIONE_PONTE)
    max_t = int(cfg["max_tentativi_canale"])

    def salva():
        ris["riassunto"] = fps.riassunto(ris["kit"], float(cfg["soglia_fps"]))
        ris["ora"] = time.strftime("%Y-%m-%d %H:%M:%S")
        scrivi_json(f_ris, ris)
        scrivi_json(f_uid, mappa)

    def segna(fase):
        stato.update(fase=fase, ora=time.strftime("%Y-%m-%d %H:%M:%S"), versione=VERSION)
        scrivi_json(f_stato, stato)

    av(f"fps1 {VERSION} su {PC}: fino alle {time.strftime('%d/%m %H:%M', time.localtime(fine))}, "
       f"{cfg['insieme']} kit insieme, fonte {ris['fonte']}" + (" (ripreso)" if ris["ripreso"] else ""))
    segna("in corso")
    lavori, coda, n = [], [], 0
    ultimo_drive, prossima_presa, sito_muto_da = time.time(), 0.0, None
    inizio_giro, motivo = 0.0, None
    try:
        while True:
            # --- fermarsi?
            if motivo is None:
                if time.time() > fine:
                    motivo = f"{cfg['durata_ore']} ore finite"
                elif os.path.exists(os.path.join(C, "ferma.txt")):
                    motivo = "ferma.txt nella cartella del compito"
                elif cfg.get("controlla_drive") and time.time() - ultimo_drive > 300:
                    ultimo_drive = time.time()
                    if compito_nuovo_su_drive():
                        motivo = "su Drive c'e' un compito nuovo per questo PC"
                if motivo:
                    av(f"mi fermo: {motivo}" + (f" (aspetto {len(lavori)} kit in corso)" if lavori else ""))
            # --- i processi in corso
            for lav in list(lavori):
                guarda(lav, versione_sito)
                finito = lav["p"].poll() is not None
                ucciso = False
                if not finito and time.time() > lav["limite"]:
                    lav["p"].kill()
                    try:
                        lav["p"].wait(60)
                    except subprocess.TimeoutExpired:
                        pass
                    finito = ucciso = True
                if not finito:
                    continue
                lavori.remove(lav)
                r = chiudi(lav, versione_sito, ucciso)
                e = lav["kit"]["etichetta"]
                ris["kit"][e] = fps.unisci(ris["kit"].get(e), r, datetime.datetime.now(), max_t)
                k = ris["kit"][e]
                nuovi = [c for c in r.get("canali") or [] if c.get("fps")]
                av(f"{e}: {r.get('esito') or r.get('collegamento')} in {round(time.time() - lav['t0'])} s"
                   + (" - " + ", ".join(f"CH{c['canale']} {c['fps']} fps" for c in nuovi) if nuovi else "")
                   + f" [risposto {k.get('risposte_n', 0)}, non risposto {k['non_risposto']}]")
                salva()
            if motivo:
                if not lavori:
                    break
                time.sleep(0.5)
                continue
            # --- un posto libero: la prossima richiesta
            if len(lavori) >= max(1, int(cfg["insieme"])) or time.time() < prossima_presa:
                time.sleep(0.5)
                continue
            liberi = sorted(set(range(1, max(1, int(cfg["insieme"])) + 1)) - {x["posto"] for x in lavori})
            kit, rid, serve_arch = None, None, False
            if ris["fonte"] == "sito":
                try:
                    d = chiama("prendi", {"pc": PC, "versione": versione_sito})
                    sito_muto_da = None
                    rq = d.get("richiesta")
                    if not rq:
                        prossima_presa = time.time() + float(cfg["pausa_coda_vuota_s"])
                        continue
                    e = fps.etichetta_per_uid(rq["uid"], rq.get("kit"), mappa)
                    kit = {"uid": rq["uid"], "numero": fps.numero_da_richiesta(rq.get("kit")), "etichetta": e}
                    rid, serve_arch = rq["id"], bool(rq.get("serve_archivio"))
                except Exception as ex:   # noqa: BLE001
                    sito_muto_da = sito_muto_da or time.time()
                    av(f"sito non raggiunto: {type(ex).__name__}: {str(ex)[:200]}")
                    prossima_presa = time.time() + 60
                    if time.time() - sito_muto_da > float(cfg["sito_muto_min"]) * 60:
                        ris["fonte"] = "da_solo"
                        av(f"il sito non risponde da {cfg['sito_muto_min']} minuti: faccio il giro da solo, ogni ora")
                    continue
            else:
                if not coda:
                    adesso = time.time()
                    prossimo = fps.prossimo_giro(inizio_giro, adesso, float(cfg["giro_ogni_min"]) * 60)
                    if adesso < prossimo:
                        prossima_presa = min(adesso + 30, prossimo)
                        continue
                    tutti = kit_da_solo(cfg)
                    for x in tutti:
                        mappa.setdefault(x["uid"].upper(), x["etichetta"])
                    coda = fps.da_fare(tutti, ris["kit"], max_t)
                    inizio_giro = adesso
                    av(f"giro da solo: {len(coda)} kit da misurare su {len(tutti)}")
                    if not coda:
                        continue
                kit = coda.pop(0)
            if any(x["kit"]["uid"].upper() == kit["uid"].upper() for x in lavori):
                continue   # lo stesso registratore e' gia' in mano a un altro posto
            k = ris["kit"].get(kit["etichetta"]) or {}
            salta = fps.canali_da_saltare(k, max_t) if cfg.get("misura_fps", True) else []
            fai_foto = bool(cfg.get("foto")) and rid is not None and fps.serve_foto(k, datetime.date.today())
            n += 1
            lavori.append(lancia(cfg, liberi[0], kit, rid, serve_arch, fai_foto, salta, n))
            av(f"{kit['etichetta']}: comincio" + (f" (richiesta {rid})" if rid is not None else "")
               + (", archivio" if serve_arch else "") + (", foto" if fai_foto else "")
               + (f", gia' misurati CH {salta}" if salta else ""))
    except Exception as ex:   # noqa: BLE001
        ris["errore"] = f"{type(ex).__name__}: {str(ex)[:400]}"
        av(ris["errore"])
        _riga("avanzamento.txt", traceback.format_exc()[-2000:])
        for lav in lavori:
            try:
                lav["p"].kill()
            except Exception:   # noqa: BLE001
                pass
        segna("in corso")   # un errore inatteso non chiude il compito: alla ripresa si riparte da qui
        salva()
        return
    ris["fermato"] = motivo
    ris["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    salva()
    rs = ris["riassunto"]
    av(f"riassunto: {rs['kit_collegati']} kit risposti su {rs['kit']}, {rs['telecamere_misurate']} telecamere misurate, "
       f"{rs['telecamere_sotto_soglia']} sotto {rs['soglia_fps']} fps")
    shutil.rmtree(L, ignore_errors=True)   # gli UID e le copie della libreria restano solo sul PC: via
    segna("finito")
    av("fatto")


if __name__ == "__main__":
    main()
