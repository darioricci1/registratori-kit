"""La misura delle varianti di b_tavolino.py sulle ore della prova pilota (pilota.json e le miniature minuti/ scaricate
dal compito), a tavolino: per ogni variante gli abbandoni trovati (al 1o posto, nei primi 3, negli 8 che si guardano)
e i falsi allarmi per ora fra i primi 3 e fra i primi 8.
Uso: python3 misura_b_tavolino.py CARTELLA_PILOTA [variante ...] [--json uscita.json]
     (CARTELLA_PILOTA contiene pilota.json e pilota/<ora>/minuti/; kit_rifiuti.py da KR_SCRIPTS o dal repo accanto)
version: 0.1.0 (12/11/2026): prima versione.
"""
import datetime
import json
import os
import sys
from multiprocessing import Pool

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get("KR_SCRIPTS") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")
sys.path.insert(0, QUI)
sys.path.insert(0, SCRIPTS)
import b_tavolino as bt   # noqa: E402

VERSIONE = "0.1.0"
D = datetime.datetime

# Le varianti misurate, una alla volta rispetto a quella di partenza, poi insieme (analisi-abbandono-in-un-ora.md).
VARIANTI = {
    "oggi": {},
    "pesata": {"zona": "pesata", "peso_fuori": 0.5},
    "radice": {"punteggio": "dE_radice"},
    "ombra": {"ombra": 0.6},
    "fermo": {"fermo": 0.5},
    "durata10": {"durata_min": 10},
    "base": {"peso_base": 3.0},
    "resta8": {"resta_n": 8},
    "memoria30": {"memoria": 30},
    "massimi8": {"massimi": 8},
    "fino": {"solo_fino": True},
    "mosso4": {"mosso_max": 4.0},
    "area3000": {"area_max": 0.0075},
    # insieme: le regole che da sole non tolgono abbandoni e tolgono falsi
    "insieme": {"memoria": 30, "solo_fino": True, "mosso_max": 4.0, "area_max": 0.0075},
    "insieme_m5": {"memoria": 30, "solo_fino": True, "mosso_max": 5.0, "area_max": 0.0075},
    "insieme_m35": {"memoria": 30, "solo_fino": True, "mosso_max": 3.5, "area_max": 0.0075},
    "insieme_m45": {"memoria": 30, "solo_fino": True, "mosso_max": 4.5, "area_max": 0.0075},
    "insieme_senza_memoria": {"solo_fino": True, "mosso_max": 4.0, "area_max": 0.0075},
    "insieme_senza_area": {"memoria": 30, "solo_fino": True, "mosso_max": 4.0},
    "insieme_senza_fino": {"memoria": 30, "mosso_max": 4.0, "area_max": 0.0075},
    "insieme_fuori": {"memoria": 30, "solo_fino": True, "mosso_max": 4.0, "area_max": 0.0075, "fuori": "dopo"},
}


def _dt(s):
    return D.strptime(s, "%Y-%m-%d %H:%M:%S")


def un_ora(arg):
    cartella, ora, varianti = arg
    import cv2
    import kit_rifiuti as kr
    cv2.setNumThreads(1)   # quattro processi, un filo ciascuno: con i fili di OpenCV in piu' si pestano i piedi
    fot, ts = bt.leggi_minuti(os.path.join(cartella, "pilota", ora["nome"], "minuti"), ora["minuti"], cv2)
    inizio = _dt(ora["inizio"])
    fine = _dt(ora["fine"])
    out = {}
    for nome, k in varianti.items():
        cand = bt.scansione(kr, cv2, fot, ts, inizio, fine, ora["zona"]["riquadri"], ora["zona"].get("escludi") or [],
                            bt.opzioni(**k))
        out[nome] = [{"box": c["box"], "comparsa": f"{c['comparsa']:%Y-%m-%d %H:%M:%S}",
                      "comparsa_prima": f"{c['comparsa_prima']:%Y-%m-%d %H:%M:%S}", "punteggio": c["punteggio"],
                      "area": c["area"], "dE": c["dE"], "durata_min": c["durata_min"], "fino": c["fino_alla_fine"],
                      "tess": c.get("tess"), "mosso": c.get("mosso")} for c in cand[:30]]
    return ora["nome"], out


def conti(ore, risultati, nome):
    """{"trovati1", "trovati3", "trovati8", "falsi3", "falsi8" (per ora), "posti": {ora: posto o None}}."""
    t1 = t3 = t8 = f3 = f8 = 0
    posti = {}
    for o in ore:
        cand = risultati[o["nome"]][nome]
        for c in cand:
            c["_c"], c["_p"] = _dt(c["comparsa"]), _dt(c["comparsa_prima"])
        if o["tipo"] == "positiva":
            at, bd = _dt(o["atteso"]), o["box_dario"]
            posto = next((k + 1 for k, c in enumerate(cand) if bt.trovato(
                {"box": c["box"], "comparsa": c["_c"], "comparsa_prima": c["_p"]}, at, bd)), None)
            posti[o["nome"]] = posto
            t1 += posto == 1
            t3 += bool(posto and posto <= 3)
            t8 += bool(posto and posto <= 8)
            falso = [bt.iou(c["box"], bd) < 0.1 for c in cand]
        else:
            falso = [True] * len(cand)
        f3 += sum(falso[:3])
        f8 += sum(falso[:8])
    n = len(ore)
    return {"trovati1": t1, "trovati3": t3, "trovati8": t8, "falsi3": round(f3 / n, 2), "falsi8": round(f8 / n, 2),
            "posti": posti}


def main(argv):
    cartella = argv[1]
    uscita = None
    if "--json" in argv:
        uscita = argv[argv.index("--json") + 1]
        argv = argv[:argv.index("--json")] + argv[argv.index("--json") + 2:]
    nomi = argv[2:] or list(VARIANTI)
    varianti = {n: VARIANTI[n] if n in VARIANTI else json.loads(n) for n in nomi}
    varianti = {(n if n in VARIANTI else "v" + str(k)): v for k, (n, v) in enumerate(zip(nomi, varianti.values()))}
    ore = [o for o in json.load(open(os.path.join(cartella, "pilota.json"), encoding="utf-8"))["ore"]
           if o.get("valutabile")]
    with Pool(4) as p:
        risultati = dict(p.map(un_ora, [(cartella, o, varianti) for o in ore]))
    print(f"{'variante':<12} {'1o':>3} {'pr3':>4} {'pr8':>4} {'falsi3/h':>9} {'falsi8/h':>9}")
    righe = {}
    for n in varianti:
        c = conti(ore, risultati, n)
        righe[n] = c
        print(f"{n:<12} {c['trovati1']:>3} {c['trovati3']:>4} {c['trovati8']:>4} {c['falsi3']:>9} {c['falsi8']:>9}  "
              + " ".join(f"{k[:5]}:{v or '-'}" for k, v in c["posti"].items()))
    if uscita:
        for o in risultati.values():
            for v in o.values():
                for c in v:
                    c.pop("_c", None)
                    c.pop("_p", None)
        json.dump({"varianti": varianti, "conti": righe, "candidati": risultati}, open(uscita, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv)
