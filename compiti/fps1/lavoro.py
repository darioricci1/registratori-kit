"""
lavoro - un processo del compito fps1 (registratori-kit): UNA richiesta, cioe' un registratore. Il compito lo copia
come compito.py in una cartella sua e lo lancia come un compito (exe --compito <cartella>): legge lavoro.json (radice
del compito, cartella della libreria, il kit con l'UID, i canali gia' misurati, se servono archivio e foto, i
parametri) e nello stesso collegamento fa:
  1. quello che fa il ponte nel giro leggero (ponte_pezzi: registratore, canali, minuti; l'archivio se il sito lo
     chiede; le foto una volta al giorno) e lo scrive in uscita/sito.json, che il compito manda subito al sito
     (op=esito) mentre questo processo va avanti;
  2. la misura degli fps dei canali non ancora misurati (fps.misura_canali), in uscita/risultato.json, riscritto dopo
     ogni canale.
VERSION 0.1.0 (17/11/2026)

Un processo per richiesta: se la libreria Focus fa cadere il processo (0xC0000005) o si pianta, cade solo questo kit;
il compito lo vede dal codice d'uscita, dal risultato a meta' e da guasto_memoria.txt, e va avanti. Il video
scaricato sta in <cartella>/video e si cancella appena misurato.
"""
import json
import os
import sys
import threading
import time

VERSION = "0.1.0"
D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
U = os.path.join(D, "uscita")
os.makedirs(U, exist_ok=True)
CFG = json.load(open(os.path.join(D, "lavoro.json"), encoding="utf-8"))
sys.path.insert(0, CFG["radice"])
try:
    import faulthandler
    faulthandler.enable(open(os.path.join(U, "guasto_memoria.txt"), "a", encoding="utf-8"), all_threads=True)
except Exception:   # noqa: BLE001
    pass

import fps   # noqa: E402
import ponte_pezzi as pp   # noqa: E402

CIMITERO = []   # il Registratore non si libera mai (come il ponte 0.13.0): si esce con os._exit
_scrivi = threading.Lock()


def registratore():
    """Il Registratore vero; con FPS1_FINTA (solo nelle prove a tavolino) quello finto di prova_fps1."""
    finta = os.environ.get("FPS1_FINTA")
    if finta:
        import prova_fps1 as pf
        return pf.RegistratoreFinto(json.loads(finta))
    import focus_nvr as fn
    return fn.Registratore(CFG["sdk"], log=lambda *_: None)


def scrivi_json(nome, dati):
    with _scrivi:
        p = os.path.join(U, nome)
        with open(p + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(dati, fh, ensure_ascii=False, default=str)
        os.replace(p + ".tmp", p)


def main():
    import focus_nvr as fn
    pp.U = os.path.join(D, "foto")
    os.makedirs(pp.U, exist_ok=True)
    kit, p = CFG["kit"], CFG["parametri"]
    r = {"kit": kit["etichetta"], "collegato": False, "canali": [], "inizio": time.strftime("%Y-%m-%d %H:%M:%S"),
         "versione_lavoro": VERSION}

    def scrivi(x):
        scrivi_json("risultato.json", x)

    scadenza = time.time() + float(p.get("tetto_kit_min", 8)) * 60 - float(p.get("margine_kit_s", 45))
    accesso = fps.leggi_accesso([CFG["radice"], os.path.dirname(sys.executable),
                                 os.path.dirname(os.path.dirname(sys.executable)), os.path.expanduser("~")])
    cred = fps.credenziali(kit["uid"], kit.get("numero"), accesso)
    if not cred:
        r.update(esito="sul PC manca focus_accesso.txt con utente e password dei registratori", finito=True)
        scrivi_json("sito.json", {"ok": False, "esito": {"pc": CFG.get("pc"), "errore": r["esito"]}})
        scrivi(r)
        return 0
    try:
        reg = registratore()
        CIMITERO.append(reg)
    except Exception as ex:   # noqa: BLE001
        r.update(esito=f"libreria non caricata: {type(ex).__name__}: {str(ex)[:300]}", finito=True, libreria=False)
        scrivi(r)
        return 2
    t0 = time.time()
    ok, testo, tent, cr = fps.collega(reg, kit["uid"], cred, float(CFG.get("attesa", 12)))
    sito = {"pc": CFG.get("pc"), "collegamento": testo, "secondi_collegamento": round(time.time() - t0, 1)}
    if "(" in testo:
        sito["modo"] = r["modo"] = testo.split("(", 1)[1].rstrip(")")
    if tent > 1:   # come prova() del ponte
        sito["credenziali"] = f"entrato con la {tent}a password provata" if ok else "nessuna password giusta"
    r.update(collegamento=testo, secondi_collegamento=sito["secondi_collegamento"], tentativi=tent)
    if not ok:
        scrivi_json("sito.json", {"ok": False, "esito": sito})
        r.update(esito="non collegato: " + testo, finito=True)
        scrivi(r)
        return 0
    r["collegato"] = True
    scrivi(r)
    try:
        es, oggi = pp.stato_leggero(reg, fn)
        sito.update(es)
        if CFG.get("serve_archivio"):   # prima delle foto: il collegamento e' fresco (come il ponte)
            sito["archivio"] = pp.archivio(reg)
        # se le foto piantano il processo, il compito manda al sito almeno questo (sito_parziale.json)
        scrivi_json("sito_parziale.json", {"ok": True, "esito": sito})
        if CFG.get("fai_foto"):
            r["foto_fatte"] = True   # anche se non finiscono: domani di nuovo, non a ogni giro
            scrivi(r)
            sito["camere"] = pp.foto_camere(reg, oggi, es["canali"], CFG.get("rid") or kit["etichetta"])
    except Exception as ex:   # noqa: BLE001 - il sito riceve quello che c'e'
        sito["errore"] = f"{type(ex).__name__}: {str(ex)[:300]}"
    scrivi_json("sito.json", {"ok": True, "esito": sito})
    info = sito.get("registratore") or {}
    canali = reg.canali()
    r.update(modello=info.get("modello"), telecamere=info.get("telecamere"), canali_n=len(canali))
    scrivi(r)
    if p.get("misura_fps", True):
        fps.misura_canali(reg, canali, cr, kit["uid"], p, os.path.join(D, "video"), r, scrivi=scrivi,
                          scadenza=scadenza, salta=set(CFG.get("salta") or []))
    misurati = sum(1 for c in r["canali"] if c.get("fps"))
    r["esito"] = f"fatto: {misurati} canali misurati in questa prova" + (" (tetto del kit)" if r.get("tetto_kit") else "")
    r["finito"] = True
    r["secondi"] = round(time.time() - t0, 1)
    scrivi(r)
    try:
        reg.chiudi()
    except Exception:   # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    codice = main()
    sys.stdout.flush()
    os._exit(codice)   # niente distruttori della DLL all'uscita: il risultato e' gia' scritto
