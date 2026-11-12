"""pilota_lavoro.py: un'ora di pilota.json in un processo suo (lanciato dal ponte come compito a parte: exe --compito
<cartella>, come allunga_lavoro.py). Nella cartella ci sono ponte.py (il compito.py del ponte, da cui si prendono le
definizioni fino al ciclo, senza farlo partire) e ora.json ({"ora": {...}, "cfg": {...}, "compito": la cartella del
compito, dove stanno focus_nvr.py, pilota.py, dimezza.py, movimento.py, allunga.py, FocusNetSDK e focus_accesso.txt,
"uscita": la cartella in uscita dell'ora}). Se la libreria Focus fa cadere il processo, muore solo lui: il ponte scrive
il codice e passa all'ora dopo. Scrive <uscita>/ora.json man mano; le miniature grezze restano in grezzi/ qui.
Esce con os._exit (niente scarico della DLL). Codici: 0 finito, 3 una chiamata non e' tornata in tempo, 1 errore.
version: 0.1.0 (12/11/2026)
"""
import faulthandler
import json
import os
import sys
import traceback

D = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
os.makedirs(os.path.join(D, "uscita"), exist_ok=True)
_guasti = open(os.path.join(D, "uscita", "guasto_memoria.txt"), "a", encoding="utf-8")
faulthandler.enable(_guasti, all_threads=True)
codice = 1
try:
    lavoro = json.load(open(os.path.join(D, "ora.json"), encoding="utf-8"))
    FINE = "\nt_fine = time.time() + DURATA"   # da qui in giu' il ponte ascolta: non si esegue
    src = open(os.path.join(D, "ponte.py"), encoding="utf-8").read()
    g = {"__name__": "ponte", "__file__": os.path.join(D, "ponte.py")}
    exec(compile(src[:src.index(FINE)], os.path.join(D, "ponte.py"), "exec"), g)   # noqa: S102 - il nostro codice
    g["C"] = lavoro["compito"]   # credenziali() e FocusNetSDK stanno nella cartella del compito
    sys.path.insert(0, lavoro["compito"])
    import pilota as pl  # noqa: E402

    ora, cfg, uscita = lavoro["ora"], lavoro.get("cfg") or {}, lavoro["uscita"]
    os.makedirs(uscita, exist_ok=True)
    g["av"](f"pilota_lavoro {pl.VERSIONE}: ora {ora['nome']} in un processo suo (pid {os.getpid()})")
    cimitero = []   # i Registratori chiusi restano vivi fino a os._exit
    mezzi = pl.mezzi_veri(os.path.join(lavoro["compito"], "FocusNetSDK"), g["collega_con"], g["ffmpeg"](), ora, uscita,
                          os.path.join(D, "grezzi"), cimitero, g["NOFIN"])

    def scrivi(x):
        p = os.path.join(uscita, "ora.json")
        with open(p + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(x, fh, ensure_ascii=False, indent=1, default=str)
        os.replace(p + ".tmp", p)
    x = pl.lavora_ora(ora, cfg, mezzi, scrivi, g["av"])
    codice = 3 if x.get("bloccato") else 0
except BaseException:   # noqa: BLE001 - tutto nel registro, poi fuori
    traceback.print_exc()
    try:
        with open(os.path.join(D, "uscita", "avanzamento.txt"), "a", encoding="utf-8") as fh:
            fh.write(traceback.format_exc()[-1500:] + "\n")
    except OSError:
        pass
    codice = 1
finally:
    try:
        sys.stdout.flush()
        sys.stderr.flush()
        _guasti.flush()
    except Exception:   # noqa: BLE001
        pass
    os._exit(codice)
