"""
telecamere_da_sistemare.py - l'elenco delle telecamere dei kit da mettere a fuoco o da liberare, per la pagina
«Telecamere da sistemare» di stato.html (op=sistemare di api/p2p.js).
VERSION 0.1.0 (14/11/2026) - prima versione.

Perche' (Dario, 14/11/2026: «mi fai in registratori kit anche un elenco di queste? KIT249 Viano telecamera 3 sfocata
davvero ... o altre simili»). Legge la misura di nitidezza_telecamere.py (repo kit-rifiuti-programma, analisi/) e ci
aggiunge le note di chi ha guardato a occhio i ritagli a piena risoluzione delle peggiori (14/11).

Chi entra nell'elenco:
  - le telecamere guardate a occhio con un problema vero (sfocata, morbida, ostruzione, incerta);
  - le «si» della misura (8% peggiore di tutte E almeno 1 sotto le altre dello stesso kit) non ancora guardate;
  - le «forse» con indice <= -1,5 e almeno 1 sotto le altre del kit (circa il 10% peggiore, e peggio delle sorelle):
    le altre «forse» sono una condizione sola e sarebbero rumore.
Le guardate a occhio e risultate a posto o non giudicabili (asfalto uniforme, ombre, misura ingannata dalla scena)
restano in fondo come «falso allarme della misura»: cosi' non tornano a sembrare da sistemare e si vede che sono gia'
state guardate.

Uso: python3 dati/telecamere_da_sistemare.py [nitidezza_telecamere.json] [uscita.json]
  (difetti: ../kit-rifiuti-programma/analisi/nitidezza_telecamere.json e dati/telecamere_da_sistemare.json)
"""
import json
import os
import re
import sys

VERSION = "0.1.0"
QUI = os.path.dirname(os.path.abspath(__file__))
INGRESSO = os.path.join(QUI, "..", "..", "kit-rifiuti-programma", "analisi", "nitidezza_telecamere.json")
USCITA = os.path.join(QUI, "telecamere_da_sistemare.json")

# le note a occhio che non sono (ancora) nel json della misura: (numero del kit, EX, telecamera) -> nota
OCCHIO_IN_PIU = {
    (577, False, 2): "sfocata (20° posto della misura)",
}

FORSE_INDICE, FORSE_KIT = -1.5, -1.0


def numero_kit(nome):
    m = re.search(r"(EX\s*)?KIT\s*0*(\d+)", nome, re.I)
    return (int(m.group(2)), bool(m.group(1))) if m else (None, False)


def classifica(nota):
    """Dalla nota a occhio: (problema, cosa fare) oppure None se e' un falso allarme."""
    n = nota.lower()
    if re.search(r"a posto|non si giudica", n):
        return None
    if re.search(r"palo|staffa", n):
        return "ostruzione: palo o staffa", "sul posto"
    if re.search(r"rami|foglie davanti", n):
        return "rami", "sul posto"
    if "incert" in n:
        return "da verificare", "da guardare"
    if "morbid" in n:
        return "morbida", "fuoco da remoto: prova"
    if "sfocat" in n:
        return "sfocata", "fuoco da remoto: prova"
    return "da verificare", "da guardare"


def elenco(misura):
    tele = misura["telecamere"]
    righe = []
    for t in tele:
        n, ex = numero_kit(t["kit"])
        nota = t.get("a_occhio") or OCCHIO_IN_PIU.get((n, ex, t["cam"]))
        base = {
            "kit": t["kit"], "kit_n": n, "ex": ex, "comune": t["comune"], "cam": t["cam"],
            "nitidezza": t["indice"], "rispetto_kit": t.get("rispetto_kit"), "rango": t["rango"],
            "misura": t["sfocata"], "giro": t["giro"], "giorno": t["giorno"],
        }
        if nota:
            c = classifica(nota)
            if c:
                righe.append({**base, "problema": c[0], "certezza": "visto a occhio", "cosa_fare": c[1], "nota": nota, "gruppo": 1})
            else:
                righe.append({**base, "problema": "falso allarme della misura", "certezza": "visto a occhio",
                              "cosa_fare": "niente", "nota": nota, "gruppo": 3})
            continue
        forte = t["sfocata"] == "forse" and t["indice"] <= FORSE_INDICE and (t.get("rispetto_kit") or 0) <= FORSE_KIT
        if t["sfocata"] == "si" or forte:
            spiega = "misura: " + ("8% peggiore e sotto le altre del kit" if t["sfocata"] == "si"
                                   else "forse (" + (t.get("nota") or "una condizione sola") + ")")
            righe.append({**base, "problema": "da verificare", "certezza": "solo misura", "cosa_fare": "da guardare",
                          "nota": spiega, "gruppo": 2})
    righe.sort(key=lambda r: (r["gruppo"], r["rango"]))
    return {
        "versione": VERSION, "misura_versione": misura.get("versione"), "telecamere_misurate": len(tele),
        "criterio": "visto a occhio con un problema; poi le «si» della misura; poi le «forse» con indice <= "
                    f"{FORSE_INDICE} e almeno {-FORSE_KIT} sotto le altre del kit; in fondo i falsi allarmi visti a occhio",
        "guardate_a_occhio": misura.get("guardate_a_occhio"),
        "telecamere": righe,
    }


def prova():
    assert classifica("sfocata davvero (la c1 dello stesso kit e' nitida)") == ("sfocata", "fuoco da remoto: prova")
    assert classifica("morbida rispetto alla c1, probabile fuoco")[0] == "morbida"
    assert classifica("un palo/staffa a pochi cm dall'obiettivo, fuori fuoco: e' l'inquadratura, non il fuoco")[1] == "sul posto"
    assert classifica("rami e foglie davanti all'obiettivo: ostruzione, non fuoco")[0] == "rami"
    assert classifica("ombre di foglie su asfalto: sembra a posto") is None
    assert classifica("solo asfalto uniforme: non si giudica") is None
    assert classifica("strisce un po' morbide, scena povera: incerta")[0] == "da verificare"
    assert numero_kit("EX KIT206 Via Marega") == (206, True) and numero_kit("KIT 452 Via Foggia") == (452, False)


if __name__ == "__main__":
    prova()
    ing = sys.argv[1] if len(sys.argv) > 1 else INGRESSO
    usc = sys.argv[2] if len(sys.argv) > 2 else USCITA
    with open(ing, encoding="utf-8") as f:
        e = elenco(json.load(f))
    with open(usc, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(e["telecamere"]), "telecamere;", dict(Counter(r["problema"] for r in e["telecamere"])),
          dict(Counter(r["certezza"] for r in e["telecamere"] if r["gruppo"] < 3)))
