"""allunga_lavoro.py: un evento di allunga.json in un processo suo (lanciato dal ponte come compito a parte: exe
--compito <cartella>, come owl_misura.py). Nella cartella ci sono ponte.py (il compito.py del ponte, da cui si prendono
le definizioni fino al ciclo, senza farlo partire) ed evento.json ({"evento": {...}, "cfg": {...}, "compito": la
cartella del compito, dove stanno focus_nvr.py, allunga.py, movimento.py, FocusNetSDK e focus_accesso.txt}).
Perche' a parte: stasera (compito 28, 11/11 18:11) il ponte e' morto con un errore di memoria della libreria
(3221225477); se succede qui muore solo questo processo e il ponte passa all'evento dopo (allunga.py, in alto).
Scrive uscita/allunga_evento.json man mano, i fogli dei fotogrammi in uscita/fogli e gli mp4 in video/; un errore della
libreria dentro un suo filo lascia le pile di Python in uscita/guasto_memoria.txt (faulthandler).
Esce con os._exit: niente scarico della DLL a fine processo (un'altra occasione di chiamate a funzioni gia' liberate).
Codici: 0 finito, 3 una chiamata non e' tornata in tempo, 1 errore in Python.
version: 0.1.0 (11/11/2026)
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
    lavoro = json.load(open(os.path.join(D, "evento.json"), encoding="utf-8"))
    FINE = "\nt_fine = time.time() + DURATA"   # da qui in giu' il ponte ascolta: non si esegue
    src = open(os.path.join(D, "ponte.py"), encoding="utf-8").read()
    g = {"__name__": "ponte", "__file__": os.path.join(D, "ponte.py")}
    exec(compile(src[:src.index(FINE)], os.path.join(D, "ponte.py"), "exec"), g)   # noqa: S102 - il nostro codice
    # le credenziali e la libreria stanno nella cartella del compito, non qui: credenziali() e FocusNetSDK leggono g["C"]
    g["C"] = lavoro["compito"]
    sys.path.insert(0, lavoro["compito"])
    import allunga as al  # noqa: E402

    ev, cfg = lavoro["evento"], lavoro.get("cfg") or {}
    g["av"](f"allunga_lavoro {al.VERSIONE}: evento {ev['evento']} in un processo suo (pid {os.getpid()})")
    cimitero = []   # i Registratori chiusi restano vivi fino a os._exit
    mezzi = al.mezzi_veri(os.path.join(lavoro["compito"], "FocusNetSDK"), g["collega_con"], g["ffmpeg"](), ev, D, cimitero,
                          g["NOFIN"])
    scrivi = lambda x: g["scrivi_json"]("allunga_evento.json", x)   # noqa: E731
    x = al.lavora_evento(ev, cfg, mezzi, scrivi, g["av"])
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
