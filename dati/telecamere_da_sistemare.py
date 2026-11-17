"""
telecamere_da_sistemare.py - l'elenco delle telecamere dei kit da mettere a fuoco o da liberare, per la pagina
«Telecamere da sistemare» di stato.html (op=sistemare di api/p2p.js).
VERSION 0.5.0 (17/11/2026) - le righe «da spostare» portano «caldo», i punti degli abbandoni giudicati su quella
  telecamera (kit.json «heatmap»), per la heatmap sulla foto (Dario: «nelle foto di abbandoni sul margine metti la
  heatmap?»). KIT_JSON si può dare dall'ambiente.
VERSION 0.4.1 (16/11/2026) - le telecamere che le operatrici non salvano escono da qui e vanno nella sezione «Errori di
  salvataggio» (dati/errori_salvataggio.json, op=errori; Dario: «voglio una sezione di registratori kit»).
VERSION 0.4.0 (16/11/2026) - anche le telecamere che le operatrici non salvano (Dario, 16/11: «aggiungilo a quello che
  stiamo facendo nella pagina registratori kit»): da dati/operatrici_telecamere.json (kit con almeno 2 clip a cui manca
  una telecamera mentre lo stesso giorno, entro 3 ore, c'e' una clip completa), una riga per kit e telecamera che manca;
  problema «non salvata dall'operatrice», cosa fare «dire alle operatrici», gruppo 1.7. Fuori i kit EX come sempre.
VERSION 0.3.1 (15/11/2026) - KIT577 Vergato cam 2 non e' sfocata (foto dal vivo a fuoco): inquadratura sbagliata, sul
  posto. Nuovo problema «inquadratura sbagliata».
VERSION 0.3.0 (15/11/2026) - anche le telecamere da riposizionare (Dario, 15/11: «lo vorrei in registratore»): dal campo
  «spostare» di kit-rifiuti-web/dati/kit.json (pagina_kit.py 0.3.0, contato dagli abbandoni giudicati): l'abbandono
  avviene lontano, sul margine dell'immagine o dietro un cassonetto. Problema «da spostare: ...», cosa fare «sul posto:
  riposizionare», gruppo 1.5 (dopo le viste a occhio, prima della sola misura).
VERSION 0.2.0 (14/11/2026) - fuori i kit «EX» (Dario): sono posizioni dove il kit non c'e' piu' (spostato altrove,
  nome nuovo); la telecamera si misura e si sistema nella posizione nuova.
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

VERSION = "0.4.1"
QUI = os.path.dirname(os.path.abspath(__file__))
INGRESSO = os.path.join(QUI, "..", "..", "kit-rifiuti-programma", "analisi", "nitidezza_telecamere.json")
USCITA = os.path.join(QUI, "telecamere_da_sistemare.json")

# le note a occhio che non sono (ancora) nel json della misura: (numero del kit, EX, telecamera) -> nota
OCCHIO_IN_PIU = {
    # 0.3.1: la prova del 15/11 (compito fuoco2) ha mostrato la foto dal vivo a fuoco: e' l'inquadratura, non il fuoco
    (577, False, 2): "a fuoco nella foto dal vivo del 15/11: inquadra solo la strada, non i cassonetti, va girata sul posto",
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
    if re.search(r"va girata|inquadra solo", n):   # 0.3.1
        return "inquadratura sbagliata", "sul posto"
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
        if ex:   # 0.2.0: posizione lasciata, il kit ora e' altrove
            continue
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
        "esclusi": "i kit «EX»: posizioni lasciate (il kit e' stato spostato e ha un nome nuovo)",
    }


KIT_JSON = os.environ.get("KIT_JSON") or os.path.join(QUI, "..", "..", "kit-rifiuti-programma", "kit-rifiuti-web", "dati", "kit.json")
SPOSTARE = {"lontano": "da spostare: abbandoni lontani", "bordo": "da spostare: abbandoni sul margine",
            "dietro": "da spostare: abbandoni dietro i cassonetti"}


def da_spostare(kit):
    """Funzione pura: le righe «da spostare» dai kit di kit.json (campo spostare), senza i kit EX."""
    righe = []
    for k in kit:
        n, ex = numero_kit(k.get("kit") or "")
        if ex or not k.get("spostare"):
            continue
        ultima = max(k.get("giudicate") or [{}], key=lambda c: (c.get("giorno") or "", c.get("ora") or 0))
        for m in k["spostare"]:
            righe.append({"kit": k["kit"], "kit_n": n, "ex": False, "comune": k.get("comune") or "", "cam": int(m["cam"]),
                          "nitidezza": "-", "rispetto_kit": None, "rango": None, "misura": "-",
                          "giro": ultima.get("evento") or "-", "giorno": ultima.get("giorno") or "",
                          "problema": SPOSTARE.get(m["motivo"], "da spostare"), "certezza": "contato dagli abbandoni",
                          "cosa_fare": "sul posto: riposizionare", "nota": m["testo"], "gruppo": 1.5,
                          "quota": round(m["quanti"] / max(1, m["su"]), 2),
                          # 0.5.0: dove sono gli abbandoni giudicati, per la heatmap sulla foto (centro, in frazioni)
                          "caldo": [p["c"] for p in (k.get("heatmap") or {}).get(str(m["cam"]), []) if p.get("c")]})
    return sorted(righe, key=lambda r: -r["quota"])


OPERATRICI = os.path.join(QUI, "operatrici_telecamere.json")


def da_operatrici(kit):
    """Funzione pura (0.4.0): una riga per kit e telecamera che le operatrici non salvano (almeno 2 clip con una clip
    completa vicina), senza i kit EX. La telecamera e' il canale + 1."""
    righe = []
    for k in kit:
        n, ex = numero_kit(k.get("kit") or "")
        if ex or (k.get("entro_3_ore") or 0) < 2:
            continue
        for canale, quante in sorted((k.get("canale_mancante") or {}).items(), key=lambda t: -t[1]):
            if quante < 2:
                continue
            righe.append({"kit": k["kit"], "kit_n": n, "ex": False, "comune": k.get("comune") or "", "cam": int(canale) + 1,
                          "nitidezza": "-", "rispetto_kit": None, "rango": None, "misura": "-", "giro": "-",
                          "giorno": k.get("al") or "", "problema": "non salvata dall'operatrice",
                          "certezza": "contato sul NAS", "cosa_fare": "dire alle operatrici",
                          "nota": f"{quante} clip su {k.get('eventi')} senza questa telecamera, dal {k.get('dal')} al {k.get('al')}; "
                                  f"in {k.get('entro_3_ore')} c'era una clip completa lo stesso giorno, entro 3 ore",
                          "gruppo": 1.7, "quota": round(quante / max(1, k.get("eventi") or 1), 3)})
    return sorted(righe, key=lambda r: -int(r["nota"].split()[0]))


def prova():
    o = da_operatrici([{"kit": "KIT667 Via Correggio", "comune": "BUSTO", "eventi": 268, "entro_3_ore": 13,
                        "canale_mancante": {"02": 84, "00": 1}, "dal": "2026-09-09", "al": "2026-10-18"},
                       {"kit": "EX KIT263 Via X", "comune": "P", "eventi": 90, "entro_3_ore": 5, "canale_mancante": {"01": 80}}])
    assert len(o) == 1 and o[0]["cam"] == 3 and o[0]["problema"] == "non salvata dall'operatrice" and o[0]["gruppo"] == 1.7
    r = da_spostare([{"kit": "KIT1 Via A", "comune": "X", "giudicate": [{"evento": "a", "giorno": "2026-11-01"}],
                      "spostare": [{"motivo": "dietro", "cam": "2", "quanti": 3, "su": 5, "testo": "t"}]},
                     {"kit": "EX KIT2", "comune": "Y", "spostare": [{"motivo": "bordo", "cam": "1", "quanti": 4, "su": 4, "testo": "u"}]}])
    assert len(r) == 1 and r[0]["cam"] == 2 and r[0]["problema"].endswith("dietro i cassonetti") and r[0]["gruppo"] == 1.5
    assert da_spostare([{"kit": "KIT1", "spostare": [{"motivo": "bordo", "cam": "2", "quanti": 1, "su": 1, "testo": "t"}],
                         "heatmap": {"2": [{"c": [0.1, 0.9]}], "1": [{"c": [0.5, 0.5]}]}}])[0]["caldo"] == [[0.1, 0.9]]
    assert classifica("sfocata davvero (la c1 dello stesso kit e' nitida)") == ("sfocata", "fuoco da remoto: prova")
    assert classifica("morbida rispetto alla c1, probabile fuoco")[0] == "morbida"
    assert classifica("un palo/staffa a pochi cm dall'obiettivo, fuori fuoco: e' l'inquadratura, non il fuoco")[1] == "sul posto"
    assert classifica("rami e foglie davanti all'obiettivo: ostruzione, non fuoco")[0] == "rami"
    assert classifica("ombre di foglie su asfalto: sembra a posto") is None
    assert classifica("solo asfalto uniforme: non si giudica") is None
    assert classifica("strisce un po' morbide, scena povera: incerta")[0] == "da verificare"
    assert classifica("a fuoco: inquadra solo la strada, va girata sul posto") == ("inquadratura sbagliata", "sul posto")
    assert numero_kit("EX KIT206 Via Marega") == (206, True) and numero_kit("KIT 452 Via Foggia") == (452, False)


if __name__ == "__main__":
    prova()
    ing = sys.argv[1] if len(sys.argv) > 1 else INGRESSO
    usc = sys.argv[2] if len(sys.argv) > 2 else USCITA
    with open(ing, encoding="utf-8") as f:
        e = elenco(json.load(f))
    if os.path.exists(KIT_JSON):   # 0.3.0
        with open(KIT_JSON, encoding="utf-8") as f:
            e["telecamere"] = sorted(e["telecamere"] + da_spostare(json.load(f)["kit"]), key=lambda r: r["gruppo"])
        e["criterio"] += "; dopo le viste a occhio, le telecamere da riposizionare contate dagli abbandoni giudicati"
    if False and os.path.exists(OPERATRICI):   # 0.4.0; 0.4.1: nella sezione «Errori di salvataggio»
        with open(OPERATRICI, encoding="utf-8") as f:
            e["telecamere"] = sorted(e["telecamere"] + da_operatrici(json.load(f)["kit"]), key=lambda r: r["gruppo"])
        e["criterio"] += "; poi le telecamere che le operatrici non salvano (contate sul NAS)"
    with open(usc, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(e["telecamere"]), "telecamere;", dict(Counter(r["problema"] for r in e["telecamere"])),
          dict(Counter(r["certezza"] for r in e["telecamere"] if r["gruppo"] < 3)))
