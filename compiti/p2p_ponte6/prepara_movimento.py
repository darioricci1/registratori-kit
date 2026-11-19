"""Prepara movimento.json per il compito movimento1 (ponte 0.21.0, movimento.py 0.2.0): l'indice di movimento dei
registratori Focus sulle ore con un abbandono vero (Dario, 19/11: «mettilo in coda»; kit-rifiuti-programma
analisi/coda-lavori.md, punto 11).

Per ogni registratore con un UID: le finestre degli abbandoni veri ancora (forse) sul disco e le ore vuote note, giorno
per giorno e telecamera per telecamera. Il compito legge per ognuno il modo di registrazione (OnRecordModeStatus) e i
tipi dei 1440 minuti di ieri; dove il movimento si registra, i tipi dei giorni chiesti qui (GetRecordDaily).
Fonti (sola lettura, niente rete):
  - la prova ferma (analisi/prova_ferma_0.99.16.json, le sue 204 ore in <ore>/<nome>/ora.json: 137 positive col
    momento dell'abbandono, compreso il banco delle 60, e 67 negative);
  - la scorta del 14/11 (scorta.json di questa cartella: 153 ore positive, con l'UID);
  - positive1, positive1c, positive1d (banco_positive.json dei risultati: la clip dell'operatrice, dal minuto del nome
    alla fine stimata, su una qualunque telecamera della clip);
  - le clip giudicate «abbandono» sul sito kit-rifiuti (op=video: gruppo «trovato», esito «ok» di Dario), dal minuto
    del nome della clip alla sua fine, sulla telecamera della clip;
  - le ore vuote: le negative della prova ferma e del banco delle 120 (analisi/banco_ore_120.json).
Ogni abbandono vale un caso (stesso kit, stessa telecamera, finestre che si toccano: uno solo). Si tengono i giorni dal
--dal in poi (il disco dei registratori gira in 2-4 settimane: quello che non c'e' piu' il compito lo dice «non sul
disco»). Ogni clip del sito (di qualunque esito) e' un «noto» del suo giorno: l'ora che lo contiene e quelle accanto non
contano fra le ore vuote.
Uso: python3 prepara_movimento.py <registratori.json> <ore della prova ferma> <video.json> <banco_ore_120.json>
       <banco_positive.json>... [--dal AAAA-MM-GG] [--fuori movimento.json]
  registratori.json = quello di positive1d ({"283": {"uid", "canali", ...}}).
Nel json niente targhe, password o indirizzi (gli UID si', come in scorta.json).
version: 0.1.0 (19/11/2026)
"""
import datetime
import glob
import json
import os
import re
import sys

import movimento as mv

QUI = os.path.dirname(os.path.abspath(__file__))
VERSIONE = "0.1.0"
MARGINE_MIN = 2
ESCLUSI = {"998"}   # il kit di prova di Dario


def _dt(s):
    return datetime.datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


def numero(kit):
    m = re.search(r"\d+", str(kit or ""))
    return str(int(m.group())) if m else None


def ora_del_nome(nome):
    """Il momento d'inizio scritto nel nome della clip («a mano 185400», «06290100S(2)»): le prime 6 cifre di fila come
    HHMMSS, se sono un'ora vera. Funzione pura."""
    m = re.search(r"(\d{6})", str(nome or ""))
    if not m:
        return None
    h, mi, s = int(m.group(1)[:2]), int(m.group(1)[2:4]), int(m.group(1)[4:])
    return (h, mi, s) if h < 24 and mi < 60 and s < 60 else None


def finestra(da, a, margine=MARGINE_MIN):
    """(giorno, "HH:MM" da, "HH:MM" a) con il margine, dentro il giorno di `da` (un abbandono a mezzanotte resta nel
    suo giorno). Funzione pura."""
    g = da.replace(hour=0, minute=0, second=0, microsecond=0)
    x = max(g, da - datetime.timedelta(minutes=margine))
    y = min(g + datetime.timedelta(seconds=86399), a + datetime.timedelta(minutes=margine))
    return f"{g:%Y-%m-%d}", f"{x:%H:%M}", f"{y:%H:%M}"


def unisci_casi(casi):
    """Un caso per abbandono: stesso kit, stesso giorno, stesse telecamere e finestre che si toccano diventano uno
    (le fonti si sommano). Funzione pura."""
    out = []
    for c in sorted(casi, key=lambda c: (c["kit"], c["giorno"], tuple(c["canali"]), c["da"])):
        p = out[-1] if out else None
        if (p and p["kit"] == c["kit"] and p["giorno"] == c["giorno"] and p["canali"] == c["canali"]
                and c["da"] <= p["a"]):
            p["a"] = max(p["a"], c["a"])
            p["fonti"] = sorted(set(p["fonti"]) | set(c["fonti"]))
            p["eventi"] = sorted(set(p["eventi"]) | set(c["eventi"]))
            continue
        out.append(dict(c))
    for i, c in enumerate(out):
        c["nome"] = f"c{i + 1:04d}_kit{c['kit']}"
    return out


def casi_prova_ferma(cartella):
    casi, vuote, uid = [], [], {}
    for f in sorted(glob.glob(os.path.join(cartella, "*", "ora.json"))):
        o = json.load(open(f, encoding="utf-8"))
        k = numero(o.get("kit"))
        if o.get("uid"):
            uid[k] = o["uid"]
        can = int(o.get("canale") if o.get("canale") is not None else int(o.get("telecamera") or 1) - 1)
        if o.get("tipo") == "positiva":
            for e in o.get("eventi") or [{"evento": o.get("evento"), "atteso": o.get("atteso")}]:
                if not e.get("atteso"):
                    continue
                t = _dt(e["atteso"])
                g, da, a = finestra(t, t)
                casi.append({"kit": k, "giorno": g, "da": da, "a": a, "canali": [can], "canale_certo": True,
                             "fonti": ["prova ferma"], "eventi": [e.get("evento") or ""]})
        elif o.get("tipo") == "negativa":
            t = _dt(o["inizio"])
            g, da, a = finestra(t, t + datetime.timedelta(minutes=60), 0)
            vuote.append({"kit": k, "giorno": g, "da": da, "a": a, "canale": can, "fonte": "prova ferma"})
    return casi, vuote, uid


def casi_scorta(scorta):
    casi, uid = [], {}
    for o in (scorta or {}).get("ore") or []:
        k = numero(o.get("kit"))
        if o.get("uid"):
            uid[k] = o["uid"]
        if o.get("tipo") != "positiva":
            continue
        for e in o.get("eventi") or []:
            t = _dt(e["atteso"])
            g, da, a = finestra(t, t)
            casi.append({"kit": k, "giorno": g, "da": da, "a": a, "canali": [int(o["canale"])], "canale_certo": True,
                         "fonti": ["scorta 14/11"], "eventi": [e.get("evento") or ""]})
    return casi, uid


def casi_positive(banco, nome_fonte):
    """Una clip dell'operatrice per gruppo: la finestra dal momento alla fine stimata, sulle telecamere della clip."""
    per = {}
    for o in (banco or {}).get("ore") or []:
        v = o.get("verita") or {}
        if not v.get("momento"):
            continue
        k = numero(o.get("kit"))
        gr = o.get("gruppo") or v.get("evento")
        x = per.setdefault((k, gr), {"kit": k, "v": v, "canali": set()})
        tele = v.get("telecamere_della_clip") or [v.get("telecamera") or int(o.get("canale") or 0) + 1]
        x["canali"].update(int(t) - 1 for t in tele if t)
    casi = []
    for (k, gr), x in per.items():
        v = x["v"]
        t0, t1 = _dt(v["momento"]), _dt(v.get("fine_clip") or v["momento"])
        g, da, a = finestra(t0, max(t0, t1), int(v.get("margine_min") or MARGINE_MIN))
        casi.append({"kit": k, "giorno": g, "da": da, "a": a, "canali": sorted(x["canali"]),
                     "canale_certo": bool(v.get("telecamera_certa")), "fonti": [nome_fonte], "eventi": [v.get("evento") or gr]})
    return casi


def clip_del_sito(video):
    """Dalle righe di op=video: (casi delle clip «trovato» con esito «ok», noti {(kit, giorno): ["HH:MM"]} di tutte le
    clip). La finestra va dal minuto del nome alla fine della clip (durata), sulla sua telecamera."""
    casi, noti = [], {}
    for r in (video or {}).get("video") or []:
        d = r.get("dati") or {}
        k, giorno, hms = numero(d.get("kit")), d.get("giorno"), ora_del_nome(d.get("nome"))
        if not k or not giorno or not hms:
            continue
        t0 = datetime.datetime.strptime(giorno, "%Y-%m-%d").replace(hour=hms[0], minute=hms[1], second=hms[2])
        noti.setdefault((k, giorno), set()).add(f"{t0:%H:%M}")
        if r.get("gruppo") != "trovato" or r.get("esito") != "ok":
            continue
        try:
            can = int(r.get("cam")) - 1
        except (TypeError, ValueError):
            continue
        t1 = t0 + datetime.timedelta(seconds=float(d.get("durata") or 0))
        g, da, a = finestra(t0, t1)
        casi.append({"kit": k, "giorno": g, "da": da, "a": a, "canali": [can], "canale_certo": True,
                     "fonti": ["sito ok"], "eventi": [r.get("evento") or ""]})
    return casi, {k: sorted(v) for k, v in noti.items()}


def vuote_banco(banco):
    out = []
    for o in (banco or {}).get("ore") or []:
        if o.get("con_abbandono") or not o.get("inizio"):
            continue
        t = _dt(o["inizio"])
        g, da, a = finestra(t, t + datetime.timedelta(minutes=int(o.get("durata_min") or 60)), 0)
        out.append({"kit": numero(o.get("kit")), "giorno": g, "da": da, "a": a,
                    "canale": int(o.get("canale") if o.get("canale") is not None else int(o.get("telecamera") or 1) - 1),
                    "fonte": "banco 120"})
    return out


def per_registratore(casi, vuote, noti, uid, dal, escludi=ESCLUSI):
    """{kit: {"kit", "uid", "giorni": {giorno: {"canali", "noti"}}, "casi", "vuote"}} dei kit con un UID, dal giorno
    `dal`. I «noti» di un giorno sono i minuti delle clip del sito e dei casi (servono a togliere le ore non vuote).
    Funzione pura."""
    out, senza = {}, set()
    for c in casi:
        if c["giorno"] < dal or c["kit"] in escludi:
            continue
        if c["kit"] not in uid:
            senza.add(c["kit"])
            continue
        r = out.setdefault(c["kit"], {"kit": int(c["kit"]), "uid": uid[c["kit"]], "giorni": {}, "casi": [], "vuote": []})
        r["casi"].append({k: c[k] for k in ("nome", "giorno", "da", "a", "canali", "canale_certo", "fonti", "eventi")})
        gg = r["giorni"].setdefault(c["giorno"], {"canali": set(), "noti": set()})
        gg["canali"].update(c["canali"])
        gg["noti"].update((c["da"], c["a"]))
    for v in vuote:
        if v["giorno"] < dal or v["kit"] in escludi or v["kit"] not in uid:
            continue
        r = out.setdefault(v["kit"], {"kit": int(v["kit"]), "uid": uid[v["kit"]], "giorni": {}, "casi": [], "vuote": []})
        r["vuote"].append({k: v[k] for k in ("giorno", "da", "a", "canale", "fonte")})
        r["giorni"].setdefault(v["giorno"], {"canali": set(), "noti": set()})["canali"].add(v["canale"])
    for k, r in out.items():
        for g, gg in r["giorni"].items():
            gg["noti"].update(noti.get((k, g)) or [])
            r["giorni"][g] = {"canali": sorted(gg["canali"]), "noti": sorted(gg["noti"])}
        r["giorni"] = dict(sorted(r["giorni"].items(), reverse=True))   # prima i giorni piu' recenti: spariscono prima
    return out, sorted(senza, key=lambda x: int(x))


def main(argv):
    if len(argv) < 6:
        print(__doc__)
        return 2
    dal = argv[argv.index("--dal") + 1] if "--dal" in argv else "2026-10-22"
    fuori = argv[argv.index("--fuori") + 1] if "--fuori" in argv else os.path.join(QUI, "movimento.json")
    pos = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and argv[i - 1] not in ("--dal", "--fuori")]
    reg = json.load(open(pos[0], encoding="utf-8"))
    uid = {numero(k): v["uid"] for k, v in reg.items() if (v or {}).get("uid")}
    c_pf, v_pf, u_pf = casi_prova_ferma(pos[1])
    c_sc, u_sc = casi_scorta(json.load(open(os.path.join(QUI, "scorta.json"), encoding="utf-8")))
    for u in (u_pf, u_sc):
        for k, v in u.items():
            uid.setdefault(k, v)
    c_si, noti = clip_del_sito(json.load(open(pos[2], encoding="utf-8")))
    v_bc = vuote_banco(json.load(open(pos[3], encoding="utf-8")))
    c_po = []
    for f in pos[4:]:
        b = json.load(open(f, encoding="utf-8"))
        c_po += casi_positive(b, str(b.get("compito") or os.path.basename(os.path.dirname(f))))
    casi = unisci_casi(c_pf + c_sc + c_si + c_po)
    regs, senza = per_registratore(casi, v_pf + v_bc, noti, uid, dal)
    ordine = sorted(regs.values(), key=lambda r: (-len(r["casi"]), r["kit"]))
    conta = {}
    for r in ordine:
        for c in r["casi"]:
            for f in c["fonti"]:
                conta[f] = conta.get(f, 0) + 1
    cfg = {"pc": "COMPUTERONE", "preparato_il": datetime.date.today().isoformat(), "prepara": f"prepara_movimento {VERSIONE}",
           "come": ("movimento.py 0.2.0, il giro dei registratori: per ogni registratore il modo di registrazione "
                    "(OnRecordModeStatus) e i tipi dei minuti di ieri su ogni telecamera; dove il movimento si registra, "
                    "i tipi dei giorni con un abbandono vero (GetRecordDaily) e per ogni abbandono se cade in un minuto "
                    "«movimento» (+-2 minuti), con la quota di minuti e di ore «movimento» nelle ore vuote delle stesse "
                    "telecamere. Niente miniature, niente video. Dopo i registratori con un caso, tutti quelli che "
                    "hanno risposto al ponte nelle ultime 24 ore (op=stato del sito)."),
           "dal": dal, "margine_min": MARGINE_MIN, "tutti_da_stato": True, "registratori": ordine,
           "scelta": {"casi": sum(len(r["casi"]) for r in ordine), "per_fonte": conta,
                      "vuote": sum(len(r["vuote"]) for r in ordine), "registratori_con_casi": len(ordine),
                      "giorni_telecamera": sum(len(g["canali"]) for r in ordine for g in r["giorni"].values()),
                      "kit_senza_uid": senza}}
    with open(fuori, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=1)
    print(json.dumps(cfg["scelta"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
