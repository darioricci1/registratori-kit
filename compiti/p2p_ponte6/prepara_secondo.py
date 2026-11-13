"""Il secondo passaggio della prova grande (analisi-abbandono-in-un-ora.md, sezione 8; Dario, 13/11: «dai fai questa
cosa»). Per ogni ora della prova grande, i primi 3 candidati del metodo «insieme» (misura_b_tavolino.py --json) diventano
pezzi di video a piena risoluzione da scaricare dal registratore e da far analizzare a Kit_Rifiuti (scarico_lungo di
compito.py, lungo.json): da 60 s prima del minuto in cui il pezzo non c'era a 30 s dopo il minuto in cui c'e', solo
sulla telecamera dell'ora. I candidati della stessa ora con le finestre che si toccano diventano un pezzo solo.
Prima le ore piu' vecchie: il registratore tiene circa 20 giorni.

  python3 prepara_secondo.py misura_insieme.json grande.json lungo.json [--quanti 3]

version: 0.1.0 (13/11/2026)
"""
import datetime as D
import json
import sys

VERSIONE = "0.1.0"
PRIMA_S, DOPO_S = 60, 30


def _t(s):
    return D.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def finestre(candidati, quanti=3):
    """[(inizio, fine, [posti dei candidati])] in ordine di tempo, dai primi `quanti` candidati (gia' in classifica)."""
    righe = []
    for posto, x in enumerate(candidati[:quanti], 1):
        righe.append((_t(x["comparsa_prima"]) - D.timedelta(seconds=PRIMA_S),
                      _t(x["comparsa"]) + D.timedelta(seconds=DOPO_S), posto))
    righe.sort()
    fuori = []
    for a, b, posto in righe:
        if fuori and a <= fuori[-1][1]:
            fuori[-1][1] = max(fuori[-1][1], b)
            fuori[-1][2].append(posto)
        else:
            fuori.append([a, b, [posto]])
    return [tuple(f) for f in fuori]


def prepara(misura, grande, quanti=3):
    ore = {o["nome"]: o for o in grande["ore"]}
    voci = []
    for nome, c in misura["candidati"].items():
        o = ore.get(nome)
        if not o or not c.get("insieme"):
            continue
        for i, (a, b, posti) in enumerate(finestre(c["insieme"], quanti)):
            voci.append({"nome": f"{nome}_{i + 1}", "ora": nome, "uid": o["uid"], "kit": o["kit"],
                         "canali": [o["canale"]], "inizio": a.strftime("%Y-%m-%d %H:%M:%S"),
                         "minuti": round((b - a).total_seconds() / 60, 2), "posti": posti,
                         "tipo": "positiva" if nome.startswith("pos") else "negativa",
                         "atteso": o.get("atteso"), "leggero": True})
    voci.sort(key=lambda v: (v["inizio"][:10], v["ora"], v["inizio"]))
    return voci


if __name__ == "__main__":
    a = sys.argv[1:]
    quanti = 3
    if "--quanti" in a:
        quanti = int(a[a.index("--quanti") + 1])
        a = a[:a.index("--quanti")] + a[a.index("--quanti") + 2:]
    voci = prepara(json.load(open(a[0])), json.load(open(a[1])), quanti)
    json.dump(voci, open(a[2], "w"), ensure_ascii=False, indent=1)
    sec = sum(v["minuti"] * 60 for v in voci)
    print(f"{len(voci)} pezzi, {sec / 3600:.1f} ore di video, dal {voci[0]['inizio'][:10]} al {voci[-1]['inizio'][:10]}")
