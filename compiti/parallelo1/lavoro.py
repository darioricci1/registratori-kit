"""
lavoro - un processo del compito parallelo1 (registratori-kit). Il compito lo copia come compito.py in una cartella
sua e lo lancia come un compito (exe --compito <cartella>): legge lavoro.json (radice del compito, cartella della
libreria, kit con l'UID, quanti fili, agenti P2P, attesa) e fa la lettura leggera di quei kit con UNA istanza della
libreria Focus e «fili» collegamenti insieme. Strada A: un processo, N fili. Strada B: N processi, un filo ognuno.
VERSION 0.1.0 (16/11/2026)

Uscita in <cartella>/uscita: risultato.json (riscritto dopo ogni kit, cosi' un crash lascia quello che c'era),
avanzamento.txt (solo etichette dei kit: niente UID), guasto_memoria.txt (faulthandler, se la libreria fa cadere il
processo).
"""
import datetime
import json
import os
import queue
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

import parallelo as pa   # noqa: E402

_scrivi = threading.Lock()


def av(t):
    with _scrivi:
        with open(os.path.join(U, "avanzamento.txt"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + t + "\n")


def libreria():
    """La libreria vera; con PARALLELO_FINTA (solo nelle prove a tavolino) quella finta di prova_parallelo."""
    import focus_nvr as fn
    finta = os.environ.get("PARALLELO_FINTA")
    if finta:
        import prova_parallelo as pp
        return pa.LibreriaFocus(pp.dll_finta(json.loads(finta)), fn)
    return pa.LibreriaFocus(pa.carica_dll(CFG["sdk"], CFG.get("agenti_p2p", 16)), fn)


def main():
    es = {"versione": VERSION, "fili": CFG["fili"], "kit_dati": len(CFG["kit"]), "pid": os.getpid(),
          "inizio": time.strftime("%Y-%m-%d %H:%M:%S"), "risultati": [], "finito": False}
    f_es = os.path.join(U, "risultato.json")

    def salva():
        with _scrivi:
            tmp = f_es + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(es, fh, ensure_ascii=False, indent=1, default=str)
            os.replace(tmp, f_es)

    t0 = time.time()
    try:
        lib = libreria()
    except Exception as ex:   # noqa: BLE001
        es["errore"] = f"libreria non caricata: {type(ex).__name__}: {str(ex)[:300]}"
        es["finito"] = True
        salva()
        av(es["errore"])
        return 2
    es["secondi_libreria"] = round(time.time() - t0, 2)
    es["memoria_dopo_libreria"] = pa.memoria_mb()
    salva()
    accesso = pa.leggi_accesso([CFG["radice"], os.path.dirname(sys.executable),
                                os.path.dirname(os.path.dirname(sys.executable)), os.path.expanduser("~")])
    oggi = datetime.datetime.combine(datetime.date.today(), datetime.time())
    coda = queue.Queue()
    for k in CFG["kit"]:
        coda.put(k)
    insieme = [0, 0]   # adesso, massimo

    def filo(i):
        while True:
            try:
                k = coda.get_nowait()
            except queue.Empty:
                return
            with _scrivi:
                insieme[0] += 1
                insieme[1] = max(insieme[1], insieme[0])
            cr = pa.credenziali(k["uid"], k.get("numero"), accesso)
            r = pa.un_kit(lib, k, cr, CFG.get("attesa", 40), oggi)
            r["filo"] = i
            with _scrivi:
                insieme[0] -= 1
                es["risultati"].append(r)
            av(f"{r['kit']}: {'ok' if r['ok'] else 'NO'} {r.get('collegamento', '')} in {r['secondi']} s"
               + (f" ({r['errore']})" if r.get("errore") else ""))
            es["memoria"] = pa.memoria_mb()
            salva()

    t1 = time.time()
    fili = [threading.Thread(target=filo, args=(i,), daemon=True) for i in range(max(1, int(CFG["fili"])))]
    for x in fili:
        x.start()
    for x in fili:
        x.join()
    es["secondi_lavoro"] = round(time.time() - t1, 1)
    es["massimo_insieme"] = insieme[1]
    es["esiti_orfani"] = lib.smista.orfani
    es["memoria"] = pa.memoria_mb()
    es["finito"] = True
    es["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    salva()
    av(f"fine: {sum(1 for r in es['risultati'] if r['ok'])}/{len(es['risultati'])} in {es['secondi_lavoro']} s")
    try:
        lib.chiudi()
        es["chiuso"] = True
    except Exception as ex:   # noqa: BLE001
        es["chiuso"] = f"{type(ex).__name__}: {ex}"
    salva()
    return 0


if __name__ == "__main__":
    codice = main()
    sys.stdout.flush()
    os._exit(codice)   # niente distruttori della DLL all'uscita: il risultato e' gia' scritto
