"""Le carte per Qwen sul secondo passaggio della prova grande (compito 34): per ogni candidato «insieme» fra i primi 3
di ogni ora, il pezzo del compito 33 che lo contiene, i secondi «prima» (il pezzo non c'era) e «dopo» (c'e'), il
riquadro e se e' l'abbandono vero (posti di misura_b_tavolino). Il compito ricava i fotogrammi dai video rimasti sul
COMPUTERONE (p2p_ponte33/lungo/<pezzo>/video).
  python3 prepara_vlm33.py misura_insieme_grande.json secondo.json pezzi_vlm.json
version: 0.1.0 (13/11/2026)"""
import datetime as D
import json
import sys

VERSIONE = "0.1.0"


def _t(s):
    return D.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def prepara(misura, secondo, quanti=3):
    posti = misura["conti"]["insieme"]["posti"]
    pezzi = {}
    for v in secondo:
        pezzi.setdefault(v["ora"], []).append(v)
    out = []
    for ora, c in misura["candidati"].items():
        for rango, x in enumerate(c.get("insieme", [])[:quanti], 1):
            a, b = _t(x["comparsa_prima"]), _t(x["comparsa"])
            for v in pezzi.get(ora, []):
                i = _t(v["inizio"])
                fine = i + D.timedelta(seconds=v["minuti"] * 60)
                if i <= a and b <= fine:
                    out.append({"id": f"{ora}_{rango}", "ora": ora, "pezzo": v["nome"], "rango": rango,
                                "t_prima": max(0.0, (a - i).total_seconds() - 3),
                                "t_dopo": min(v["minuti"] * 60 - 1, (b - i).total_seconds() + 25),
                                "box": x["box"], "vero": posti.get(ora) == rango})
                    break
    return out


if __name__ == "__main__":
    p = prepara(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
    json.dump(p, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
    print(len(p), "carte,", sum(x["vero"] for x in p), "vere")
