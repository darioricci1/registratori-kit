"""Prepara grande.json: le ore della «prova grande» del metodo «insieme» (analisi-abbandono-in-un-ora.md, sezioni 4 e 5:
80 positive da almeno 40 kit e 150 negative, soglie congelate, misura a tavolino con misura_b_tavolino.py). Al PC
serve solo scaricare le miniature di ogni minuto (pilota.py con «solo_minuti»): niente metodo (a), niente fitte.

Due popolazioni che non si sommano mai, come nella pilota (prepara_pilota.py):
  - ~80 ORE POSITIVE: un'ora di un kit che contiene un abbandono giudicato SICURO da Claude, col momento e il riquadro
    (analisi/etichette_claude.json, analisi/etichette_prova.json e i finali.json dei giri di Guarda: evento, cam, t,
    box). L'ora vera della clip viene dal nome (HHMMSS) e dal giorno, dall'elenco di ArchiveData del NAS o dal sito.
    Fuori: i kit della parte cieca del banco (l'esame finale), le clip dei casi limite (analisi/casi_limite.json), gli
    eventi della pilota (le soglie sono state viste li'), i giudizi senza riquadro, i kit «EX» (la zona disegnata e'
    quella del posto di oggi), le telecamere senza zona dei cassonetti, i registratori che non hanno risposto al giro e
    le ore che il registratore non ha piu' (il disco gira). L'inizio dell'ora si sorteggia fra 5 e 55 minuti prima
    dell'abbandono. Al massimo 2 ore per kit (prima un giro con una sola ora per kit), mai due ore dello stesso
    kit che si sovrappongono; meta' di notte o col sole basso se ci sono. Per ogni positiva: «dentro_zona» (il
    riquadro tocca la zona disegnata?) e gli altri abbandoni sicuri noti dentro la stessa ora («altri_noti»), cosi' a
    tavolino non si contano come falsi.
  - ~150 ORE-CAMERA NEGATIVE (piu' 30 di riserva): sorteggiate alla cieca come nella pilota (kit che hanno risposto,
    fuori dal cieco, una telecamera con la zona, un giorno degli ultimi 7 registrato intero, meta' di notte), con un
    seme nuovo; prima una per kit, poi una seconda per kit se non bastano. Solo dopo il sorteggio si scartano quelle a
    meno di 2 ore da un abbandono noto dello stesso kit (eventi del sito, elenco del NAS, giudizi di Claude) e quelle
    che si sovrappongono a un'ora della pilota.

Sola lettura: i file passati (op=video leggero, op=stato, elenco del NAS). Niente rete. Le funzioni di scelta sono
pure (prova_grande.py).
Uso: python3 prepara_grande.py <video.json> <stato_nvr.json> <elenco.tsv.gz> <cartella dei giri> [grande.json]
  (cartella dei giri: quella che contiene giro*/finali.json; la pilota si legge da pilota.json qui accanto)
Nel json niente targhe, password o indirizzi (gli UID si', come in pilota.json).
version: 0.1.0 (12/11/2026)
"""
import datetime
import glob
import gzip
import json
import os
import sys

import prepara_pilota as pp

QUI = os.path.dirname(os.path.abspath(__file__))
ANALISI, SCRIPTS = pp.ANALISI, pp.SCRIPTS

VERSIONE = "0.1.0"
SEME = "grande-2026-11-12"
POSITIVE, NEGATIVE, RISERVE = 80, 150, 30
PER_KIT_POS, PER_KIT_NEG = 4, 2      # 82 positive possibili da 40 kit (12/11): con 2 per kit sarebbero 56
MARGINE_POS = 0                       # le positive sono poche e il disco gira: dentro tutte quelle che ci sono oggi,
                                      # in coda prima quelle che spariscono prima (resta_giorni); al PC un'ora gia'
                                      # sparita e' «non valutabile», e si scrive
MARGINE_NEG = 3                       # le negative sono degli ultimi 7 giorni: il margine non costa niente
LONTANO_MIN = 120                     # una negativa sta ad almeno 2 ore da un abbandono noto dello stesso kit
FONTI = ("etichette_prova", "etichette_claude", "giri")   # a parita' di momento vince la prima


def _h(*parti):
    import hashlib
    return int(hashlib.sha256("|".join([SEME] + [str(p) for p in parti]).encode("utf-8")).hexdigest(), 16)


# ------------------------------------------------------------------ funzioni pure: i giudizi

def giudizi_sicuri(etichette_claude, etichette_prova, finali):
    """Le righe sicure con riquadro, uniformi: [{"evento", "cam", "t", "box", "fonte"}]. finali: [(nome del giro,
    [righe])]. Un giudizio con esito diverso da «abbandono», senza riquadro o non sicuro non entra."""
    out = []
    for fonte, righe, campo_t in (("etichette_prova", etichette_prova, "inizio"),
                                  ("etichette_claude", etichette_claude, "inizio")):
        for x in righe:
            if x.get("sicuro") is True and x.get("box") and x.get("evento") and x.get(campo_t) is not None:
                out.append({"evento": x["evento"], "cam": int(x["cam"]), "t": float(x[campo_t]),
                            "box": [float(v) for v in x["box"]], "fonte": fonte})
    for giro, righe in finali:
        for x in righe:
            ev = x.get("evento") or str(x.get("giro") or "")[:10]
            if (x.get("sicuro") is True and x.get("box") and ev and x.get("t") is not None
                    and x.get("esito", "abbandono") == "abbandono" and len(x["box"]) == 4):
                out.append({"evento": ev, "cam": int(x["cam"]), "t": float(x["t"]),
                            "box": [float(v) for v in x["box"]], "fonte": "giri", "giro": giro})
    return out


def primo_per_evento(giudizi):
    """{evento: il giudizio col momento piu' presto} (a parita', la fonte prima in FONTI). Come la pilota: l'abbandono
    atteso e' il primo."""
    out = {}
    for g in sorted(giudizi, key=lambda g: (g["evento"], g["t"], FONTI.index(g["fonte"]))):
        out.setdefault(g["evento"], g)
    return out


def tocca(box, riquadri):
    """Il riquadro (x, y, w, h normalizzati) tocca uno dei riquadri della zona?"""
    x, y, w, hh = box
    for r in riquadri or []:
        if x < r[0] + r[2] and r[0] < x + w and y < r[1] + r[3] and r[1] < y + hh:
            return True
    return False


def inizio_positiva(evento, atteso):
    a, b = pp.OFFSET_MIN
    off = a * 60 + _h("offset", evento) % ((b - a) * 60 + 1)
    return (atteso - datetime.timedelta(seconds=off)).replace(microsecond=0), off


def si_sovrappone(a, b, margine_min=0):
    """Due ore [inizio, inizio+60') dello stesso kit si sovrappongono (con margine)?"""
    return abs(_dt(a["inizio"]) - _dt(b["inizio"])) < datetime.timedelta(minutes=60 + margine_min)


def _dt(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def scegli_positive(schede, quante=POSITIVE, per_kit=PER_KIT_POS):
    """Schede gia' controllate (una per evento: «evento», «kit», «notte», «inizio»): ordine per sha256(seme, evento);
    giro 1 una per kit alternando notte e giorno finche' ce ne sono, poi giri successivi fino a per_kit ore per kit;
    mai due ore dello stesso kit che si sovrappongono. Funzione pura."""
    ordine = sorted(schede, key=lambda s: _h("positive", s["evento"]))
    presi, per = [], {}

    def puo(s, giro):
        if len(presi) >= quante or s in presi or per.get(s["kit"], 0) >= giro:
            return False
        return not any(p["kit"] == s["kit"] and si_sovrappone(p, s) for p in presi)

    for giro in range(1, per_kit + 1):
        notte = [s for s in ordine if s["notte"]]
        giorno = [s for s in ordine if not s["notte"]]
        while notte or giorno:
            for lista in (notte, giorno):   # una di notte e una di giorno, a turno
                while lista:
                    s = lista.pop(0)
                    if puo(s, giro):
                        presi.append(s)
                        per[s["kit"]] = per.get(s["kit"], 0) + 1
                        break
    return sorted(presi, key=lambda s: _h("positive", s["evento"]))


def altri_noti(scheda, noti_kit):
    """Gli altri abbandoni sicuri noti dello stesso kit e della stessa telecamera dentro l'ora (piu' 5 minuti dopo):
    [{"evento", "atteso", "box"}]. noti_kit: [{"evento", "cam", "atteso" datetime, "box"}]."""
    da = _dt(scheda["inizio"])
    a = da + datetime.timedelta(minutes=65)
    return [{"evento": n["evento"], "atteso": n["atteso"].strftime("%Y-%m-%d %H:%M:%S"), "box": n["box"]}
            for n in sorted(noti_kit, key=lambda n: n["atteso"])
            if n["evento"] != scheda["evento"] and n["cam"] == scheda["canale"] + 1 and da <= n["atteso"] <= a]


def resta_giorni(arch, da, oggi):
    """Per quanti giorni ancora (da oggi) l'ora che comincia a `da` resta sul registratore, se il disco avanza di un
    giorno al giorno (la regola di prepara_pilota.sul_disco). None se l'archivio non si legge."""
    try:
        primo = datetime.datetime.strptime(arch["primo"][:16], "%Y-%m-%d %H:%M")
        letto = datetime.date.fromisoformat(str(arch.get("letto_il") or oggi.isoformat())[:10])
    except (KeyError, TypeError, ValueError):
        return None
    return (da - (primo + datetime.timedelta(days=(oggi - letto).days))).days


def estrai_negative(pool, oggi, quante, per_kit=PER_KIT_NEG, giorni=pp.GIORNI_NEGATIVE, margine=MARGINE_NEG):
    """Come prepara_pilota.estrai_negative (stesso sorteggio, seme nuovo), ma con un primo giro di una ora per kit e
    poi, se non bastano, fino a per_kit ore per kit (giorni diversi). Ritorna (estratte in ordine, non disponibili)."""
    fuori, presi, per = [], [], {}
    for giro in range(1, per_kit + 1):
        n = 0
        while len(presi) < quante and n < 8000 and pool:
            x = pool[_h("neg-kit", giro, n) % len(pool)]
            c = x["canali"][_h("neg-can", giro, n) % len(x["canali"])]
            g = oggi - datetime.timedelta(days=1 + _h("neg-giorno", giro, n) % giorni)
            ora_ = (20 + _h("neg-ora", giro, n) % 10) % 24 if n % 2 == 0 else 6 + _h("neg-ora", giro, n) % 14
            da = datetime.datetime.combine(g, datetime.time(ora_, _h("neg-min", giro, n) % 60))
            n += 1
            if per.get(x["kit"], 0) >= giro or any(p["kit"] == x["kit"] and p["inizio"][:10] == da.strftime("%Y-%m-%d")
                                                   for p in presi):
                continue
            ok, perche = pp.sul_disco(x["archivio"].get(c), da, da + datetime.timedelta(hours=1), oggi, margine)
            voce = {"kit": x["kit"], "uid": x["uid"], "canale": c, "inizio": da.strftime("%Y-%m-%d %H:%M:%S"),
                    "n": f"{giro}.{n - 1}", "notte": pp.notte(da)}
            if not ok:
                fuori.append(dict(voce, perche=perche))
                continue
            presi.append(voce)
            per[x["kit"]] = per.get(x["kit"], 0) + 1
    return presi, fuori


def vicino(voce, eventi_kit, minuti=LONTANO_MIN):
    """Il primo abbandono noto (datetime) del kit a meno di `minuti` dall'ora (prima dell'inizio o dopo la fine)."""
    da = _dt(voce["inizio"])
    a, b = da - datetime.timedelta(minutes=minuti), da + datetime.timedelta(minutes=60 + minuti)
    return next((t for t in sorted(eventi_kit) if a <= t <= b), None)


# ------------------------------------------------------------------ il file

def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    sys.path.insert(0, ANALISI)
    sys.path.insert(0, SCRIPTS)
    import banco_prova as bp
    import archivio_kit as ak
    video = json.load(open(sys.argv[1], encoding="utf-8"))
    stato = json.load(open(sys.argv[2], encoding="utf-8"))
    righe = [r.rstrip("\n").split("\t") for r in gzip.open(sys.argv[3], "rt", encoding="utf-8", errors="replace")]
    elenco = ak.indice_da_elenco(righe)
    uscita = sys.argv[5] if len(sys.argv) > 5 else os.path.join(QUI, "grande.json")
    zone = json.load(open(os.path.join(SCRIPTS, "zone_cassonetti.json"), encoding="utf-8"))["zone"]
    parti = bp.Parti(bp.carica_banco())
    oggi = datetime.date.today()
    archivio = stato.get("archivio") or []
    pilota = json.load(open(os.path.join(QUI, "pilota.json"), encoding="utf-8"))
    eventi_pilota = {o["evento"] for o in pilota["ore"] if o.get("evento")}
    limite = {c["evento"] for c in json.load(open(os.path.join(ANALISI, "casi_limite.json"), encoding="utf-8"))["casi"]}

    finali = []
    for f in sorted(glob.glob(os.path.join(sys.argv[4], "giro*", "finali.json"))):
        finali.append((os.path.basename(os.path.dirname(f)), json.load(open(f, encoding="utf-8"))))
    giudizi = giudizi_sicuri(json.load(open(os.path.join(ANALISI, "etichette_claude.json"), encoding="utf-8"))["etichette"],
                             json.load(open(os.path.join(ANALISI, "etichette_prova.json"), encoding="utf-8"))["etichette"],
                             finali)
    primi = primo_per_evento(giudizi)

    # dove e quando: l'elenco del NAS, poi il sito
    info = {e["id"]: {"comune": str(e.get("comune") or "").upper(), "kit": e.get("kit"), "nome": e.get("nome"),
                      "giorno": str(e.get("quando") or "")[:10]} for e in elenco}
    for y in video:
        d = y.get("dati") or {}
        if y["evento"] not in info and d.get("giorno"):
            info[y["evento"]] = {"comune": str(d.get("comune") or "").upper(), "kit": d.get("kit"), "nome": d.get("nome"),
                                 "giorno": str(d.get("giorno"))[:10]}

    def parte_di(comune, kit_nome):
        """La parte del kit; un EX conta anche col numero di oggi (il cieco vince)."""
        k = bp.kit_id(kit_nome)
        p = [parti.di_kit(f"{comune}|{k}")]
        if k.startswith("EX"):
            p.append(parti.di_kit(f"{comune}|{k[2:]}"))
        return "cieco" if "cieco" in p else p[0]

    def zona(n, cam):
        z = (zone.get(pp.kit_zone(n)) or {}).get(str(cam)) or {}
        r = ([z["zona"]] if z.get("zona") else []) + [b for b in z.get("altre") or [] if b]
        return {"riquadri": r, "escludi": [b for b in z.get("escludi") or [] if b]} if r else None

    # gli abbandoni noti per kit: tutti i giudizi sicuri (per «altri_noti») e tutti gli eventi (per le negative)
    noti = {}
    for g in giudizi:
        i = info.get(g["evento"])
        o = pp.ora_nome((i or {}).get("nome"))
        n = pp.numero((i or {}).get("kit"))
        if not i or not o or not n or not i["giorno"]:
            continue
        s = datetime.datetime.strptime(f"{i['giorno']} {o}", "%Y-%m-%d %H:%M:%S")
        noti.setdefault(n, []).append({"evento": g["evento"], "cam": g["cam"], "atteso": s + datetime.timedelta(seconds=g["t"]),
                                       "box": g["box"]})
    ev_kit = pp.eventi_per_kit(video, elenco)
    for n, l in noti.items():
        ev_kit.setdefault(n, set()).update(x["atteso"] for x in l)

    # ---- positive
    schede, scartate = [], {}
    for e, g in sorted(primi.items()):
        i = info.get(e)
        if e in limite:
            scartate[e] = "caso limite"
            continue
        if e in eventi_pilota:
            scartate[e] = "gia' nella pilota"
            continue
        if e in bp.ESCLUSI:
            scartate[e] = "escluso dal banco"
            continue
        if not i:
            scartate[e] = "evento non trovato (ne' NAS ne' sito)"
            continue
        n, o = pp.numero(i["kit"]), pp.ora_nome(i["nome"])
        if not n or not o or not i["giorno"]:
            scartate[e] = "kit o ora della clip illeggibile"
            continue
        p = parte_di(i["comune"], i["kit"])
        if p == "cieco":
            scartate[e] = "kit nella parte cieca"
            continue
        if bp.kit_id(i["kit"]).startswith("EX"):
            scartate[e] = "kit EX (la zona e' del posto di oggi)"
            continue
        z = zona(n, g["cam"])
        if not z:
            scartate[e] = f"la telecamera {g['cam']} del kit non ha la zona dei cassonetti"
            continue
        reg = pp.registratore(n, stato.get("kit") or [], oggi)
        if not reg:
            scartate[e] = "il registratore non ha risposto al giro"
            continue
        s_clip = datetime.datetime.strptime(f"{i['giorno']} {o}", "%Y-%m-%d %H:%M:%S")
        atteso = s_clip + datetime.timedelta(seconds=g["t"])
        inizio, off = inizio_positiva(e, atteso)
        arch = pp.archivio_di(archivio, reg["uid"], g["cam"] - 1)
        ok_, perche = pp.sul_disco(arch, inizio, inizio + datetime.timedelta(hours=1), oggi, MARGINE_POS)
        if not ok_:
            scartate[e] = perche
            continue
        schede.append({"evento": e, "kit": n, "notte": pp.notte(atteso), "uid": reg["uid"], "canale": g["cam"] - 1,
                       "inizio": inizio.strftime("%Y-%m-%d %H:%M:%S"), "atteso": atteso.strftime("%Y-%m-%d %H:%M:%S"),
                       "atteso_s": off, "box_dario": g["box"], "box_da": "claude", "fonte": g["fonte"],
                       "giro": g.get("giro"), "resta_giorni": resta_giorni(arch, inizio, oggi), "zona": z, "parte": p, "dentro_zona": tocca(g["box"], z["riquadri"]),
                       "clip": s_clip.strftime("%H:%M:%S"),
                       "come_atteso": f"clip delle {s_clip:%H:%M:%S} + {g['t']:g} s (giudizio sicuro di Claude, "
                                      f"{g['fonte']}) sulla telecamera {g['cam']}"})
    positive = scegli_positive(schede)
    visti = {}
    for s in positive:   # 1 = la prima ora di quel kit nell'ordine del sorteggio: le «1» sono 40 kit indipendenti
        visti[s["kit"]] = visti.get(s["kit"], 0) + 1
        s["ora_del_kit"] = visti[s["kit"]]
    positive.sort(key=lambda s: (s["resta_giorni"] if s["resta_giorni"] is not None else 99, _h("positive", s["evento"])))
    for s in positive:
        s["altri_noti"] = altri_noti(s, noti.get(s["kit"], []))

    # ---- negative
    pool = []
    for k in sorted({str(x.get("kit") or "").lstrip("0") for x in stato.get("kit") or []}, key=lambda s: (len(s), s)):
        if not k.isdigit():
            continue
        n = int(k)
        reg = pp.registratore(n, stato.get("kit") or [], oggi)
        comune = None
        for e in elenco:
            if pp.numero(e.get("kit")) == n and not bp.kit_id(e.get("kit")).startswith("EX"):
                comune = str(e.get("comune") or "").upper()
        p = parti.di_kit(f"{comune}|{pp.kit_zone(n)}") if comune else None
        if not reg or p in (None, "cieco"):
            continue
        canali = [c for c in range(8) if zona(n, c + 1) and pp.archivio_di(archivio, reg["uid"], c)]
        if canali:
            pool.append({"kit": n, "uid": reg["uid"], "canali": canali, "parte": p,
                         "archivio": {c: pp.archivio_di(archivio, reg["uid"], c) for c in canali}})
    estratte, non_disp = estrai_negative(pool, oggi, (NEGATIVE + RISERVE) * 2)
    ore_pilota = [o for o in pilota["ore"]]
    negative, scartate_neg = [], []
    for v in estratte:
        t = vicino(v, ev_kit.get(v["kit"], ()))
        if t:
            scartate_neg.append(dict(v, perche=f"abbandono o evento noto alle {t:%Y-%m-%d %H:%M:%S}"))
            continue
        if any(o["kit"] == v["kit"] and si_sovrappone(o, v) for o in ore_pilota):
            scartate_neg.append(dict(v, perche="si sovrappone a un'ora della pilota"))
            continue
        v["zona"] = zona(v["kit"], v["canale"] + 1)
        v["parte"] = next(x["parte"] for x in pool if x["kit"] == v["kit"])
        negative.append(v)
    ore = []
    for i, s in enumerate(positive):
        ore.append(dict(s, nome=f"pos{i + 1:03d}_kit{s['kit']}", tipo="positiva"))
    for i, v in enumerate(negative[:NEGATIVE + RISERVE]):
        ore.append(dict(v, nome=f"neg{i + 1:03d}_kit{v['kit']}", tipo="negativa", riserva=i >= NEGATIVE))
    cfg = {"pc": "COMPUTERONE", "preparato_il": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "prepara": VERSIONE,
           "seme": SEME, "solo_minuti": True,
           "come": ("pilota.py con solo_minuti: per ogni ora solo le miniature di ogni minuto (da 6 minuti prima a 5 "
                    "dopo, 72 per ora) in uscita/pilota/<ora>/minuti/ e ora.json; niente metodo (a), niente candidati, "
                    "niente fitte. La misura del metodo «insieme» a soglie ferme si fa a tavolino "
                    "(misura_b_tavolino.py oggi insieme insieme_fuori). Positive e negative non si sommano."),
           "negative_quante": NEGATIVE, "limiti": {"minuti_per_ora": 8.0}, "ore": ore,
           "scelta": {"positive_possibili": len(schede), "positive_notte_possibili": sum(1 for s in schede if s["notte"]),
                      "kit_positive_possibili": len({s["kit"] for s in schede}),
                      "giudizi_sicuri": len(giudizi), "eventi_con_giudizio": len(primi),
                      "positive_scartate": scartate, "negative_estratte": len(estratte),
                      "negative_scartate": scartate_neg, "negative_non_disponibili": non_disp[:80],
                      "kit_nel_pool_negative": len(pool), "margine_giorni_positive": MARGINE_POS,
                      "margine_giorni_negative": MARGINE_NEG,
                      "regola_scarto": f"abbandono noto o evento del sito o del NAS dello stesso kit a meno di "
                                       f"{LONTANO_MIN} min dall'ora",
                      "elenco_nas_letto": len(elenco)}}
    with open(uscita, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=1)
    pos_kit = {s["kit"] for s in positive}
    print(f"positive {len(positive)} da {len(pos_kit)} kit (possibili {len(schede)} da "
          f"{len({s['kit'] for s in schede})} kit; notte {sum(1 for s in positive if s['notte'])}, fuori zona "
          f"{sum(1 for s in positive if not s['dentro_zona'])}), negative {len(negative[:NEGATIVE])} + riserve "
          f"{len(negative[NEGATIVE:NEGATIVE + RISERVE])} da {len({v['kit'] for v in negative[:NEGATIVE + RISERVE]})} kit, "
          f"scartate {len(scartate_neg)}, pool {len(pool)} kit")


if __name__ == "__main__":
    main()
