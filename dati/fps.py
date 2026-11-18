# registratori-kit/dati/fps.py - version: 0.1.0 (18/11/2026)
# 0.1.0: gli fps veri delle telecamere dei kit (Dario, 17/11: «I FPS LI METTI IN REGISTRAZIONI KIT?»), dal risultato del
#        compito fps1 (risultato_fps1.zip su Drive «Analisi video», uscita/risultato.json). Una riga per telecamera misurata
#        o provata, i kit con le ore in cui hanno risposto, i kit che non hanno mai risposto. Lo serve op=fps di api/p2p.js.
#
#        La velocità che conta è fps_conteggio: fotogrammi arrivati diviso il tempo vero fra il primo e l'ultimo. Il
#        compito chiamava «fps» la mediana degli intervalli del registratore (fps_tempi): quando i fotogrammi arrivano a
#        gruppi la mediana dice 25 anche se in 10 secondi ne arrivano 180 (KIT201, 252, 407, 411, 597...), e un video così
#        letto a 25 scorre più veloce lo stesso. Per questo qui fps = fps_conteggio (poi tempi, poi file grezzo).
#
# Uso: python3 -I dati/fps.py <risultato.json> [dati/fps.json]
# Niente UID né password: il risultato del compito non li ha, e qui si copiano solo i campi elencati.
import datetime
import json
import os
import re
import sys

VERSION = "0.1.0"
SOGLIA = 24.0
LETTO_A = 25.0   # Kit_Rifiuti legge i .ssf a 25 fps


def numero(e):
    m = re.match(r"^KIT(\d+)$", e)
    return int(m.group(1)) if m else None


def fps_vero(c):
    for k in ("fps_conteggio", "fps_tempi", "fps_grezzo"):
        if c.get(k):
            return round(float(c[k]), 2)
    return None


def costruisci(r):
    kit, tele, mai = [], [], []
    for e in sorted(r["kit"], key=lambda x: (numero(x) is None, numero(x) or 0, x)):
        k = r["kit"][e] or {}
        risposte = list(k.get("risposte") or [])
        if not risposte:
            mai.append({"kit": e, "n": numero(e), "prove": int(k.get("provato") or 0), "errore": k.get("ultimo_errore") or k.get("esito") or "-"})
            continue
        canali = k.get("canali") or []
        mis = [c for c in canali if fps_vero(c)]
        kit.append({"kit": e, "n": numero(e), "modello": k.get("modello") or "-", "canali": k.get("canali_n"),
                    "risposte": risposte, "ore_risposta": k.get("ore_risposta") or [], "risposte_n": len(risposte),
                    "non_risposto": int(k.get("non_risposto") or 0), "misurate": len(mis),
                    "lente": sum(1 for c in mis if fps_vero(c) < SOGLIA)})
        for c in canali:
            f = fps_vero(c)
            registrato = (c.get("minuti_oggi") or 0) + (c.get("minuti_ieri") or 0)
            if not f and (c.get("esito") == "niente registrato oggi e ieri" or not registrato and not c.get("inizio")):
                continue   # canale senza telecamera (o spento da due giorni): non è una riga
            tele.append({
                "kit": e, "n": numero(e), "canale": int(c["canale"]), "titolo": c.get("titolo") or "",
                "fps": f, "accelerazione": round(LETTO_A / f, 2) if f else None,
                "fps_registratore": c.get("fps_tempi"), "fps_file": c.get("fps_grezzo"), "fps_dichiarato": c.get("fps_sps"),
                "fotogrammi": c.get("fotogrammi"), "secondi": c.get("durata_tempi_s"), "misure": 1 if f else 0,
                "prove": int(c.get("tentativi") or 0), "risoluzione": c.get("risoluzione") or "-", "codec": c.get("codec") or "-",
                "tratto": c.get("inizio") or "", "scelta": c.get("scelta") or "", "misurato_il": c.get("il") or "",
                "discordanti": bool(c.get("discordanti")) or bool(f and c.get("fps_tempi") and abs(f - c["fps_tempi"]) > 0.1 * max(f, c["fps_tempi"])),
                "esito": "misurato" if f else (c.get("esito") or "-"),
                "ore_risposta": k.get("ore_risposta") or [], "risposte_n": len(risposte), "non_risposto": int(k.get("non_risposto") or 0),
            })
    tele.sort(key=lambda t: (t["fps"] is None, t["fps"] if t["fps"] is not None else 0, t["n"] or 0, t["kit"], t["canale"]))
    misurate = [t for t in tele if t["fps"]]
    lente = [t for t in misurate if t["fps"] < SOGLIA]
    per = {}
    for t in misurate:
        v = f"{round(t['fps'])}"
        per[v] = per.get(v, 0) + 1
    p = r.get("parametri") or {}
    return {
        "versione": VERSION, "fatto_il": datetime.date.today().isoformat(),
        "fonte": f"compito fps1 {r.get('versione', '')} sul {r.get('pc', '?')}, dal {r.get('primo_avvio', '?')} al {r.get('fine', '?')}"
                 f" ({r.get('fermato') or 'finito'}); un giro sulla coda del sito, {p.get('secondi', 10)} secondi per telecamera",
        "soglia": SOGLIA, "letto_a": LETTO_A,
        "conti": {"kit": len(r["kit"]), "kit_risposto": len(kit), "kit_mai_risposto": len(mai), "telecamere_misurate": len(misurate),
                  "telecamere_senza_misura": len(tele) - len(misurate), "sotto_soglia": len(lente),
                  "kit_con_lente": len({t["kit"] for t in lente}), "per_fps": dict(sorted(per.items(), key=lambda x: -x[1]))},
        "telecamere": tele, "kit": kit, "mai_risposto": mai,
    }


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "fps.json")
    with open(src, encoding="utf-8") as fh:
        r = json.load(fh)
    out = costruisci(r)
    testo = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    if re.search(r"passw|\buid\b", testo, re.I):
        sys.exit("nel risultato c'è qualcosa che sembra una password o un UID: non scrivo")
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(testo)
    c = out["conti"]
    print(f"{c['telecamere_misurate']} telecamere misurate in {c['kit_risposto']} kit, {c['sotto_soglia']} sotto {SOGLIA:g} fps "
          f"in {c['kit_con_lente']} kit; {c['kit_mai_risposto']} kit mai risposto -> {dst} ({len(testo) // 1024} kB)")


if __name__ == "__main__":
    main()
