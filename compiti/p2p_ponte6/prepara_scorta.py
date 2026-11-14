"""Prepara scorta.json per il compito 35 (ponte 0.18.0): la scorta serale degli abbandoni sicuri ancora sul registratore
(backlog-ridotto-2026-11-11.md di kit-rifiuti-programma, «scorta di ore dai registratori») e la catena dell'ora con Qwen
su ore mai viste (analisi-abbandono-in-un-ora.md, 8b: «mettere Qwen dentro la catena dell'ora»).

Due liste nello stesso file, che sul PC fa scorta.py:
  - ORE POSITIVE: un'ora intorno a ogni abbandono sicuro con riquadro (etichette_claude, etichette_prova, giri di Guarda,
    clip corrette da Dario sul sito) ancora sul disco del registratore. L'inizio dell'ora si sorteggia fra 5 e 55 minuti
    prima dell'abbandono (seme nuovo). Un abbandono che cade dentro un'ora gia' presa dello stesso kit e della stessa
    telecamera non fa un'ora sua: entra in quella («eventi» dell'ora), e scarica solo il suo video. Per ogni abbandono il
    video a piena risoluzione da PRIMA_VIDEO_S prima a DOPO_VIDEO_S dopo, sulla sua telecamera.
    Fuori: casi limite, eventi CONFERIMENTI (Dario, 14/11), etichette da ignorare, esclusi del banco, giudizi «no» di
    Dario, registratori che non hanno risposto al giro, ore che il registratore non ha piu'.
    «catena»: l'ora entra anche nella misura della catena (b_tavolino «insieme» -> pezzi -> Qwen) solo se la telecamera
    ha la zona dei cassonetti, il kit non e' della parte cieca e non e' un EX (la zona e' del posto di oggi). Le altre si
    salvano soltanto. «vista»: l'abbandono era gia' nella pilota o nella prova grande (l'ora e' un'altra, col seme
    nuovo, ma l'abbandono e' gia' stato guardato): la misura «su ore mai viste» le toglie.
  - ORE NEGATIVE: una per ogni ora positiva della catena (al massimo NEG_PER_KIT per kit), dello STESSO kit e della
    STESSA telecamera, sorteggiata fra
    gli ultimi NEG_GIORNI giorni (meta' di notte), lontana almeno LONTANO_MIN minuti da ogni evento noto del kit (sito,
    elenco del NAS, giudizi), mai lo stesso giorno di un'altra negativa del kit, mai sopra un'ora positiva del kit.
    Senza riquadro: ogni candidato e' un falso.
Sola lettura dei file passati. Niente rete. Le funzioni di scelta sono pure (prova_scorta.py).
Uso: python3 prepara_scorta.py <video.json> <stato_nvr.json> <elenco.tsv.gz> <cartella dei giri> <eventi_corrette.json>
       [scorta.json] [--lancio AAAA-MM-GG]
  eventi_corrette.json = {evento: righe di op=evento} delle clip corrette da Dario (i suoi riquadri).
  --lancio: il giorno in cui il compito parte (di difetto oggi): conta per «ancora sul disco».
Nel json niente targhe, password o indirizzi (gli UID si', come in pilota.json).
version: 0.1.0 (14/11/2026)
"""
import datetime
import glob
import gzip
import hashlib
import json
import os
import sys

import prepara_grande as pg
import prepara_pilota as pp

QUI = os.path.dirname(os.path.abspath(__file__))
ANALISI, SCRIPTS = pp.ANALISI, pp.SCRIPTS

VERSIONE = "0.1.0"
SEME = "scorta-2026-11-14"
PRIMA_VIDEO_S, DOPO_VIDEO_S = 30, 60      # il video a piena risoluzione intorno all'abbandono: 90 s
NEG_GIORNI = 7
NEG_PER_KIT = 2
LONTANO_MIN = 120
FONTI = ("dario", "etichette_prova", "etichette_claude", "giri")   # a parita' di momento vince la prima


def _h(*parti):
    return int(hashlib.sha256("|".join([SEME] + [str(p) for p in parti]).encode("utf-8")).hexdigest(), 16)


def _dt(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def _s(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ funzioni pure

def giudizi_dario(eventi, verita_di, esito_di):
    """Dalle righe di op=evento ({evento: righe}) i riquadri d'abbandono di Dario: [{"evento", "cam", "t", "box",
    "fonte": "dario"}], il primo per telecamera. Un evento con esito diverso da «ok» o bizzarro non entra.
    verita_di, esito_di: quelle di banco_prova (passate da fuori per provarle senza il repository)."""
    out = []
    for e, righe in sorted(eventi.items()):
        if not righe or esito_di(righe) != "ok" or any(y.get("bizzarro") for y in righe):
            continue
        for cam, lista in (verita_di(righe).get("riquadri") or {}).items():
            if lista:
                r = lista[0]
                out.append({"evento": e, "cam": int(cam), "t": float(r["inizio"]), "box": [float(v) for v in r["box"]],
                            "fonte": "dario"})
    return out


def primo_per_evento(giudizi):
    """{evento: il giudizio col momento piu' presto}; a parita' la fonte prima in FONTI."""
    out = {}
    for g in sorted(giudizi, key=lambda g: (g["evento"], g["t"], FONTI.index(g["fonte"]) if g["fonte"] in FONTI else 9)):
        out.setdefault(g["evento"], g)
    return out


def inizio_ora(evento, atteso, offset_min=pp.OFFSET_MIN):
    """L'inizio dell'ora: l'abbandono cade fra 5 e 55 minuti dopo (sorteggio col seme nuovo)."""
    a, b = offset_min
    off = a * 60 + _h("offset", evento) % ((b - a) * 60 + 1)
    return (atteso - datetime.timedelta(seconds=off)).replace(microsecond=0), off


def video_di(atteso, prima_s=PRIMA_VIDEO_S, dopo_s=DOPO_VIDEO_S):
    """Il tratto di video a piena risoluzione intorno all'abbandono: (inizio, secondi)."""
    return (atteso - datetime.timedelta(seconds=prima_s)).replace(microsecond=0), int(prima_s + dopo_s)


def raggruppa_ore(schede):
    """Le schede (una per abbandono: «evento», «kit», «canale», «atteso», «inizio», «resta_giorni») in ore: in ordine di
    urgenza (resta_giorni, poi sorteggio) ogni scheda prende un'ora sua, a meno che il suo abbandono cada dentro
    un'ora gia' presa dello stesso kit e della stessa telecamera (fra l'inizio e la fine): allora entra in quella.
    Ritorna [{"scheda" (quella che ha fatto l'ora), "eventi": [schede]}] nell'ordine di urgenza. Funzione pura."""
    ordine = sorted(schede, key=lambda s: (s["resta_giorni"] if s.get("resta_giorni") is not None else 99,
                                           _h("pos", s["evento"])))
    ore = []
    for s in ordine:
        at = _dt(s["atteso"])
        casa = next((o for o in ore if o["scheda"]["kit"] == s["kit"] and o["scheda"]["canale"] == s["canale"]
                     and _dt(o["scheda"]["inizio"]) <= at < _dt(o["scheda"]["inizio"]) + datetime.timedelta(hours=1)), None)
        if casa:
            casa["eventi"].append(s)
        else:
            ore.append({"scheda": s, "eventi": [s]})
    return ore


def negative_per(ore_pos, archivi, eventi_kit, oggi, giorni=NEG_GIORNI, lontano_min=LONTANO_MIN, tentativi=60,
                 per_kit=NEG_PER_KIT):
    """Una negativa per ogni ora positiva della catena, stesso kit e stessa telecamera. ore_pos: [{"nome", "kit",
    "uid", "canale", "inizio"}]; archivi: {(uid, canale): riga dell'archivio}; eventi_kit: {kit: [datetime]}.
    Sorteggio col seme e il nome dell'ora: giorno fra gli ultimi `giorni`, notte (20-6) e giorno a turno, il primo tentativo
    a sorte;
    scartata se il registratore non ha l'ora, se e' lo stesso giorno di un'altra negativa del kit, se tocca un'ora
    positiva del kit o se un evento noto del kit e' a meno di `lontano_min`. Al massimo `per_kit` negative per kit (un kit
    con tante ore positive non deve pesare troppo sui falsi). Ritorna (negative, scartate). Pura."""
    presi, fuori = [], []
    for o in ore_pos:
        if sum(1 for p in presi if p["kit"] == o["kit"]) >= per_kit:
            continue
        for n in range(tentativi):
            g = oggi - datetime.timedelta(days=1 + _h("neg-giorno", o["nome"], n) % giorni)
            di_notte = (n + _h("neg-notte", o["nome"])) % 2 == 0   # meta' delle ore cominciano di notte
            ora_ = (20 + _h("neg-ora", o["nome"], n) % 10) % 24 if di_notte else 6 + _h("neg-ora", o["nome"], n) % 14
            da = datetime.datetime.combine(g, datetime.time(ora_, _h("neg-min", o["nome"], n) % 60))
            voce = {"kit": o["kit"], "uid": o["uid"], "canale": o["canale"], "inizio": _s(da), "notte": pp.notte(da),
                    "per": o["nome"], "n": n}
            ok, perche = pp.sul_disco(archivi.get((o["uid"], o["canale"])), da, da + datetime.timedelta(hours=1), oggi, 0)
            if not ok:
                fuori.append(dict(voce, perche=perche))
                continue
            if any(p["kit"] == o["kit"] and p["inizio"][:10] == voce["inizio"][:10] for p in presi):
                continue
            if any(q["kit"] == o["kit"] and abs(_dt(q["inizio"]) - da) < datetime.timedelta(hours=1) for q in ore_pos):
                fuori.append(dict(voce, perche="tocca un'ora positiva del kit"))
                continue
            t = pg.vicino(voce, eventi_kit.get(o["kit"], ()), lontano_min)
            if t:
                fuori.append(dict(voce, perche=f"evento noto alle {_s(t)}"))
                continue
            presi.append(voce)
            break
    return presi, fuori


# ------------------------------------------------------------------ il file

def main(argv):
    lancio = None
    if "--lancio" in argv:
        lancio = datetime.date.fromisoformat(argv[argv.index("--lancio") + 1])
        argv = argv[:argv.index("--lancio")] + argv[argv.index("--lancio") + 2:]
    if len(argv) < 6:
        sys.exit(__doc__)
    sys.path.insert(0, ANALISI)
    sys.path.insert(0, SCRIPTS)
    import banco_prova as bp
    import archivio_kit as ak
    video = json.load(open(argv[1], encoding="utf-8"))
    stato = json.load(open(argv[2], encoding="utf-8"))
    righe = [r.rstrip("\n").split("\t") for r in gzip.open(argv[3], "rt", encoding="utf-8", errors="replace")]
    elenco = ak.indice_da_elenco(righe)
    corrette = json.load(open(argv[5], encoding="utf-8"))
    uscita = argv[6] if len(argv) > 6 else os.path.join(QUI, "scorta.json")
    zone = json.load(open(os.path.join(SCRIPTS, "zone_cassonetti.json"), encoding="utf-8"))["zone"]
    parti = bp.Parti(bp.carica_banco())
    oggi = lancio or datetime.date.today()
    archivio = stato.get("archivio") or []

    def leggi(nome, chiave):
        return json.load(open(os.path.join(ANALISI, nome), encoding="utf-8"))[chiave]
    limite = {c["evento"] for c in leggi("casi_limite.json", "casi")}
    conferimenti = set(leggi("conferimenti_ids.json", "ids"))
    ignorare = {c["evento"] for c in leggi("etichette_da_ignorare.json", "eventi")}
    visti = {}   # gli abbandoni gia' nella pilota o nella prova grande: si segnano («vista»), la misura li puo' togliere
    for f in ("grande.json", "pilota.json"):
        try:
            visti.update({o["evento"]: f[:-5] for o in json.load(open(os.path.join(QUI, f), encoding="utf-8"))["ore"]
                          if o.get("evento")})
        except OSError:
            pass
    no_dario = {e for e, r in corrette.items() if r and bp.esito_di(r) == "no"}
    no_dario |= {y["evento"] for y in video if y.get("esito") == "no"}

    finali = []
    for f in sorted(glob.glob(os.path.join(argv[4], "giro*", "finali.json"))):
        finali.append((os.path.basename(os.path.dirname(f)), json.load(open(f, encoding="utf-8"))))
    giudizi = pg.giudizi_sicuri(leggi("etichette_claude.json", "etichette"), leggi("etichette_prova.json", "etichette"),
                                finali)
    giudizi += giudizi_dario(corrette, bp.verita_di, bp.esito_di)
    primi = primo_per_evento(giudizi)

    info = {e["id"]: {"comune": str(e.get("comune") or "").upper(), "kit": e.get("kit"), "nome": e.get("nome"),
                      "giorno": str(e.get("quando") or "")[:10], "cartella": str(e.get("cartella") or "")} for e in elenco}
    for y in video:
        d = y.get("dati") or {}
        if y["evento"] not in info and d.get("giorno"):
            info[y["evento"]] = {"comune": str(d.get("comune") or "").upper(), "kit": d.get("kit"), "nome": d.get("nome"),
                                 "giorno": str(d.get("giorno"))[:10], "cartella": ""}

    def parte_di(comune, kit_nome):
        k = bp.kit_id(kit_nome)
        p = [parti.di_kit(f"{comune}|{k}")]
        if k.startswith("EX"):
            p.append(parti.di_kit(f"{comune}|{k[2:]}"))
        return "cieco" if "cieco" in p else p[0]

    def zona(n, cam):
        z = (zone.get(pp.kit_zone(n)) or {}).get(str(cam)) or {}
        r = ([z["zona"]] if z.get("zona") else []) + [b for b in z.get("altre") or [] if b]
        return {"riquadri": r, "escludi": [b for b in z.get("escludi") or [] if b]} if r else None

    # gli abbandoni noti per kit (altri_noti e lontananza delle negative)
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
    for n, lista in noti.items():
        ev_kit.setdefault(n, set()).update(x["atteso"] for x in lista)

    schede, scartate = [], {}
    for e, g in sorted(primi.items()):
        i = info.get(e)
        perche = ("caso limite" if e in limite else "CONFERIMENTI" if e in conferimenti
                  else "etichetta da ignorare" if e in ignorare else "escluso dal banco" if e in bp.ESCLUSI
                  else "Dario ha detto no" if e in no_dario else "evento non trovato (ne' NAS ne' sito)" if not i else None)
        if not perche and "CONFERIMENT" in (i["cartella"] or "").upper():
            perche = "CONFERIMENTI"
        if perche:
            scartate[e] = perche
            continue
        n, o = pp.numero(i["kit"]), pp.ora_nome(i["nome"])
        if not n or not o or not i["giorno"]:
            scartate[e] = "kit o ora della clip illeggibile"
            continue
        reg = pp.registratore(n, stato.get("kit") or [], oggi)
        if not reg:
            scartate[e] = "il registratore non ha risposto al giro"
            continue
        s_clip = datetime.datetime.strptime(f"{i['giorno']} {o}", "%Y-%m-%d %H:%M:%S")
        atteso = s_clip + datetime.timedelta(seconds=g["t"])
        inizio, off = inizio_ora(e, atteso)
        arch = pp.archivio_di(archivio, reg["uid"], g["cam"] - 1)
        ok_, perche = pp.sul_disco(arch, inizio, inizio + datetime.timedelta(hours=1), oggi, 0)
        if not ok_:
            scartate[e] = perche
            continue
        ex = bp.kit_id(i["kit"]).startswith("EX")
        p = parte_di(i["comune"], i["kit"])
        z = zona(n, g["cam"]) if not ex else None
        catena = "parte cieca" if p == "cieco" else "kit EX" if ex else "telecamera senza zona" if not z else None
        v0, vs = video_di(atteso)
        schede.append({"evento": e, "kit": n, "uid": reg["uid"], "canale": g["cam"] - 1, "notte": pp.notte(atteso),
                       "inizio": _s(inizio), "atteso": _s(atteso), "atteso_s": off, "box": g["box"], "fonte": g["fonte"],
                       "giro": g.get("giro"), "resta_giorni": pg.resta_giorni(arch, inizio, oggi), "zona": z,
                       "parte": p, "ex": ex, "dentro_zona": pg.tocca(g["box"], z["riquadri"]) if z else None,
                       "catena": catena is None, "fuori_catena": catena, "giorno_clip": i["giorno"],
                       "vista": visti.get(e),
                       "video": {"evento": e, "canale": g["cam"] - 1, "inizio": _s(v0), "secondi": vs}})
    gruppi = raggruppa_ore(schede)
    ore = []
    per_kit = {}
    for k, gr in enumerate(gruppi):
        s = gr["scheda"]
        per_kit[s["kit"]] = per_kit.get(s["kit"], 0) + 1
        nome = f"pos{k + 1:03d}_kit{s['kit']}"
        ora = {"nome": nome, "tipo": "positiva", "kit": s["kit"], "uid": s["uid"], "canale": s["canale"],
               "inizio": s["inizio"], "notte": s["notte"], "zona": s["zona"] or {"riquadri": [], "escludi": []},
               "evento": s["evento"], "atteso": s["atteso"], "atteso_s": s["atteso_s"], "box_dario": s["box"],
               "box_da": s["fonte"], "fonte": s["fonte"], "giro": s["giro"], "resta_giorni": s["resta_giorni"],
               "parte": s["parte"], "ex": s["ex"], "dentro_zona": s["dentro_zona"], "catena": s["catena"],
               "fuori_catena": s["fuori_catena"], "ora_del_kit": per_kit[s["kit"]], "vista": s["vista"],
               "eventi": [{"evento": x["evento"], "atteso": x["atteso"], "box": x["box"], "fonte": x["fonte"]}
                          for x in gr["eventi"]],
               "video": [x["video"] for x in gr["eventi"]]}
        nk = {"inizio": s["inizio"], "evento": s["evento"], "canale": s["canale"]}
        ora["altri_noti"] = pg.altri_noti(nk, noti.get(s["kit"], []))
        ore.append(ora)

    pos_catena = [o for o in ore if o["catena"]]
    archivi = {(a.get("uid"), a.get("canale")): a for a in archivio if a.get("primo")}
    negative, scartate_neg = negative_per(pos_catena, archivi, ev_kit, oggi)
    for k, v in enumerate(negative):
        p = next(o for o in pos_catena if o["nome"] == v["per"])
        ore.append(dict(v, nome=f"neg{k + 1:03d}_kit{v['kit']}", tipo="negativa", zona=p["zona"], parte=p["parte"],
                        catena=True))

    mb_pos = 3.4 + 34.0 + 3 * 39.0   # miniature, 90 s dell'abbandono, 3 pezzi da ~100 s (compito 33: 57 MB per 150 s)
    cfg = {"pc": "COMPUTERONE", "preparato_il": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "prepara": VERSIONE,
           "seme": SEME, "lancio": oggi.isoformat(), "solo_minuti": True,
           "finestra": {"dalle": "19:00", "alle": "07:00"},
           "limiti": {"ore_di_lavoro": 11.0, "minuti_per_ora": 20.0, "mb_per_kit": 1000.0, "mb_in_tutto": 30000.0,
                      "mb_parte_drive": 180.0},
           "gb_liberi_min": 15,
           "catena": {"variante": "insieme", "opzioni": {"memoria": 30, "solo_fino": True, "mosso_max": 4.0,
                                                         "area_max": 0.0075},
                      "candidati": 3, "prima_s": 12, "dopo_s": 30, "carta_prima_s": -3, "carta_dopo_s": 25,
                      "qwen": [["Qwen/Qwen3-VL-4B-Instruct", "nf4", "v3", "c35"]]},
           "posti_drive": [f"scorta35_{k}.zip" for k in range(1, 9)],
           "come": ("scorta.py: per ogni ora, in un processo suo (scorta_lavoro.py), le 72 miniature dei minuti "
                    "(pilota.py solo_minuti) e, per ogni abbandono dell'ora, 90 s a piena risoluzione sulla sua "
                    "telecamera; se l'ora e' della catena, b_tavolino «insieme» sulle miniature, i pezzi a piena "
                    "risoluzione dei primi 3 candidati e le carte prima/dopo per Qwen (domanda v3, come il compito 34). "
                    "Video e miniature restano sul PC (~/kr_lavori/scorta/p2p_ponte35); su Drive le miniature in "
                    "zip da al massimo 180 MB (scorta35_N.zip) e nel risultato solo json e immagini piccole."),
           "ore": ore,
           "scelta": {"giudizi_sicuri": len(giudizi), "eventi_con_giudizio": len(primi), "abbandoni_presi": len(schede),
                      "ore_positive": len(gruppi), "ore_positive_catena": len(pos_catena),
                      "kit_positive": len({o["kit"] for o in ore if o["tipo"] == "positiva"}),
                      "kit_catena": len({o["kit"] for o in pos_catena}),
                      "negative": len(negative), "negative_scartate": scartate_neg[:200],
                      "fuori_catena": {k: sum(1 for o in ore if o.get("fuori_catena") == k)
                                       for k in sorted({o.get("fuori_catena") for o in ore if o.get("fuori_catena")})},
                      "positive_scartate": scartate, "elenco_nas_letto": len(elenco),
                      "stima_mb_senza_tetti": round(len(gruppi) * 3.4 + len(schede) * 34 + len(pos_catena) * 117
                                                    + len(negative) * 120),
                      "stima_mb_per_ora_catena": mb_pos,
                      "regola_negative": f"stesso kit e telecamera di un'ora positiva della catena, ultimi {NEG_GIORNI} "
                                         f"giorni, lontana {LONTANO_MIN} min da ogni evento noto del kit"}}
    with open(uscita, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=1)
    sc = cfg["scelta"]
    print(f"abbandoni {len(schede)} in {len(gruppi)} ore positive ({sc['kit_positive']} kit), di cui nella catena "
          f"{len(pos_catena)} ({sc['kit_catena']} kit); negative {len(negative)}; fuori catena {sc['fuori_catena']}; "
          f"stima {sc['stima_mb_senza_tetti']} MB dal registratore senza tetti")
    perche = {}
    for v in scartate.values():
        k = v.split(":")[0][:40]
        perche[k] = perche.get(k, 0) + 1
    print("scartati:", sorted(perche.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    main(sys.argv)
