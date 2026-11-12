"""Prepara pilota.json: le ore della prova pilota del registratore (backlog-ridotto-2026-11-11.md di kit-rifiuti-programma,
intervento 5; decisione-p2p-2026-11-11.md, sezione 4; protocollo-valutazione-2026-11-11.md, Scorecard B). Dario, 12/11:
«l'obiettivo e' il programma che lavora da solo».

Due popolazioni che non si sommano mai (protocollo, 3.2):
  - 10 ORE POSITIVE: un'ora di un kit che contiene un abbandono vero e noto (evento giudicato «ok» da Dario con un suo
    riquadro d'abbandono, le regole di analisi/banco_prova.py: niente bizzarri, niente esclusi), un kit per ora, kit
    fuori dalla parte cieca del banco; la telecamera e' quella del riquadro e deve avere una zona dei cassonetti;
    l'inizio dell'ora si sorteggia fra 5 e 55 minuti prima del momento dell'abbandono (non piu' sempre 23); almeno 3 di
    notte se ci sono; l'ora deve essere ancora sul registratore con un margine di giorni (il disco gira).
  - 20 ORE-CAMERA NEGATIVE (piu' 10 di riserva, nell'ordine estratto): kit sorteggiati fra quelli che hanno risposto al
    giro di oggi (op=stato), fuori dalla parte cieca, una telecamera con la zona, un giorno degli ultimi 7 registrato
    intero, meta' di notte (20-6); sorteggiate SENZA guardare gli eventi. Solo dopo il sorteggio si scartano quelle che
    si sovrappongono a un evento segnalato dalle operatrici (Dario, 12/11: fuori da un abbandono segnalato e' sicuramente
    niente): eventi del sito e dell'elenco di ArchiveData (NAS) dello stesso kit fra 15 minuti prima dell'ora e 5 dopo.
    Lo scarto si scrive; al lavoro, una negativa non disponibile si sostituisce con la prima riserva (protocollo,
    Negativi, punto 4), una positiva no (decisione P2P: «non valutabile»).

Sola lettura: kit-rifiuti.vercel.app (op=video leggero, op=evento), prova-nvr-remoto.vercel.app (op=stato), elenco di
ArchiveData su Drive. Le funzioni di scelta sono pure (prova_pilota.py).
Uso: python3 prepara_pilota.py <video.json> <stato_nvr.json> <elenco.tsv.gz> <chiave.json> [pilota.json]
  video.json = op=video&leggero=1 (tutte le pagine), stato_nvr.json = op=stato; la chiave serve per op=evento.
Nel json niente targhe, password o indirizzi (gli UID si', come in dimezza.json).
version: 0.1.0 (12/11/2026)
"""
import datetime
import hashlib
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
ANALISI = os.environ.get("KR_ANALISI") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "analisi")
SCRIPTS = os.environ.get("KR_SCRIPTS") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")

VERSIONE = "0.1.0"
SEME = "pilota-2026-11-12"
POSITIVE, NEGATIVE, RISERVE = 10, 20, 10
NOTTE_MIN = 3                         # almeno 3 positive di notte, se ci sono
OFFSET_MIN = (5, 55)                  # l'abbandono cade fra 5 e 55 minuti dopo l'inizio dell'ora
MARGINE_GIORNI = 4                    # il compito parte fra 1-3 giorni: l'ora deve stare sul disco con questo margine
GIORNI_NEGATIVE = 7
MINUTI_GIORNO_PIENO = 1380            # un giorno «registrato intero» per il sorteggio delle negative
SCARTO_PRIMA_MIN, SCARTO_DOPO_MIN = 15, 5
GIA_USATI = {"167419bf4c", "1ff221627d", "deb51f0a6c", "b854c69cad"}   # i casi del dimezzamento e del compito 28: gia' guardati
KR = "https://kit-rifiuti.vercel.app/api/fogli"


def h(*parti):
    return int(hashlib.sha256("|".join([SEME] + [str(p) for p in parti]).encode("utf-8")).hexdigest(), 16)


def numero(kit):
    m = re.search(r"KIT[\s_-]*0*(\d+)", str(kit or ""), re.I)
    return int(m.group(1)) if m else None


def kit_zone(n):
    return "KIT%03d" % int(n)


def ora_nome(nome):
    m = re.search(r"(\d{2})(\d{2})(\d{2})\s*$", str(nome or ""))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59 or int(m.group(3)) > 59:
        return None
    return f"{m.group(1)}:{m.group(2)}:{m.group(3)}"


def notte(t):
    return t.hour >= 20 or t.hour < 6


# ------------------------------------------------------------------ funzioni pure: il registratore

def registratore(kit, righe_kit, oggi):
    """La riga di op=stato del kit se ha risposto al giro (stato «fatto» negli ultimi 2 giorni), o None."""
    c = [k for k in righe_kit if str(k.get("kit") or "").lstrip("0") == str(kit) and k.get("stato") == "fatto"]
    c = [k for k in c if str(k.get("finito_il") or "")[:10] >= (oggi - datetime.timedelta(days=2)).isoformat()]
    return max(c, key=lambda k: str(k.get("finito_il") or "")) if c else None


def archivio_di(archivio, uid, canale):
    return next((a for a in archivio if a.get("uid") == uid and a.get("canale") == canale and a.get("primo")), None)


def sul_disco(arch, da, a, oggi, margine=MARGINE_GIORNI):
    """L'ora [da, a) c'e' ancora sul registratore fra `margine` giorni? Il disco gira: la prima registrazione avanza di
    un giorno al giorno da quando l'archivio e' stato letto. Ritorna (si/no, perche')."""
    if not arch:
        return False, "archivio del canale non letto"
    try:
        primo = datetime.datetime.strptime(arch["primo"][:16], "%Y-%m-%d %H:%M")
        letto = datetime.date.fromisoformat(str(arch.get("letto_il") or oggi.isoformat())[:10])
    except ValueError:
        return False, "archivio illeggibile"
    soglia = primo + datetime.timedelta(days=(oggi - letto).days + margine)
    if da < soglia:
        return False, f"troppo vecchia: il registratore registra dal {arch['primo'][:16]}"
    g = (arch.get("giorni") or {}).get(da.date().isoformat())
    if g is not None and g < MINUTI_GIORNO_PIENO:
        return False, f"il {da.date()} il canale ha {g} minuti registrati"
    if a.date() != da.date():
        g2 = (arch.get("giorni") or {}).get(a.date().isoformat())
        if g2 is not None and g2 < MINUTI_GIORNO_PIENO:
            return False, f"il {a.date()} il canale ha {g2} minuti registrati"
    return True, "c'e'"


# ------------------------------------------------------------------ funzioni pure: le positive

def abbandono_atteso(righe):
    """Dal giudizio di Dario (righe di op=evento, tutti i giri): (telecamera da 1, momento, box) del primo riquadro
    d'abbandono, con l'ora della clip dal nome; None se manca qualcosa."""
    import banco_prova as bp
    v = bp.verita_di(righe)
    d = righe[0].get("dati") or {}
    o = ora_nome(d.get("nome"))
    if not v["riquadri"] or not o or not d.get("giorno"):
        return None
    cam, r = min(((c, r) for c, l in v["riquadri"].items() for r in l), key=lambda cr: cr[1]["inizio"])
    s = datetime.datetime.strptime(f"{d['giorno']} {o}", "%Y-%m-%d %H:%M:%S")
    return int(cam), s + datetime.timedelta(seconds=float(r["inizio"])), r["box"], s


def inizio_positiva(evento, atteso):
    """L'inizio dell'ora: atteso meno un numero di secondi sorteggiato fra 5 e 55 minuti (seme + evento)."""
    a, b = OFFSET_MIN
    off = a * 60 + h("offset", evento) % ((b - a) * 60 + 1)
    return (atteso - datetime.timedelta(seconds=off)).replace(microsecond=0), off


def scegli_positive(schede, quante=POSITIVE, notte_min=NOTTE_MIN):
    """Schede gia' controllate (una per evento, con «kit», «notte», «evento»): ordine per sha256(seme, evento), una per
    kit; prima le prime `notte_min` di notte, poi le altre nell'ordine. Funzione pura."""
    ordine = sorted(schede, key=lambda s: h("positive", s["evento"]))
    presi, kit = [], set()

    def prendi(s):
        if len(presi) < quante and s["kit"] not in kit and s not in presi:
            presi.append(s)
            kit.add(s["kit"])
    for s in [x for x in ordine if x["notte"]]:
        if sum(1 for x in presi if x["notte"]) < notte_min:
            prendi(s)
    for s in ordine:
        prendi(s)
    return sorted(presi, key=lambda s: h("positive", s["evento"]))


# ------------------------------------------------------------------ funzioni pure: le negative

def estrai_negative(pool, oggi, quante, giorni=GIORNI_NEGATIVE):
    """pool: [{"kit", "uid", "canali": [canale con zona], "archivio": {canale: riga}}], in ordine fisso. Sorteggio con
    il seme, senza guardare gli eventi: n pari di notte (20-6), dispari di giorno; kit, canale, giorno (fra gli ultimi
    `giorni` interi), ora e minuto di inizio dall'hash. Al massimo una per kit. Un'estrazione che il registratore non
    ha (archivio) si scrive e si passa alla successiva. Ritorna (estratte in ordine, non disponibili)."""
    fuori, presi, kit = [], [], set()
    n = 0
    while len(presi) < quante and n < 5000 and pool:
        x = pool[h("neg-kit", n) % len(pool)]
        c = x["canali"][h("neg-can", n) % len(x["canali"])]
        g = oggi - datetime.timedelta(days=1 + h("neg-giorno", n) % giorni)
        ora_ = (20 + h("neg-ora", n) % 10) % 24 if n % 2 == 0 else 6 + h("neg-ora", n) % 14
        da = datetime.datetime.combine(g, datetime.time(ora_, h("neg-min", n) % 60))
        n += 1
        if x["kit"] in kit:
            continue
        ok, perche = sul_disco(x["archivio"].get(c), da, da + datetime.timedelta(hours=1), oggi)
        voce = {"kit": x["kit"], "uid": x["uid"], "canale": c, "inizio": da.strftime("%Y-%m-%d %H:%M:%S"), "n": n - 1,
                "notte": notte(da)}
        if not ok:
            fuori.append(dict(voce, perche=perche))
            continue
        presi.append(voce)
        kit.add(x["kit"])
    return presi, fuori


def sovrapposto(voce, eventi_kit, prima_min=SCARTO_PRIMA_MIN, dopo_min=SCARTO_DOPO_MIN):
    """Il primo evento segnalato (datetime) del kit fra `prima_min` prima dell'ora e `dopo_min` dopo la fine, o None."""
    da = datetime.datetime.strptime(voce["inizio"], "%Y-%m-%d %H:%M:%S")
    a, b = da - datetime.timedelta(minutes=prima_min), da + datetime.timedelta(minutes=60 + dopo_min)
    for t in sorted(eventi_kit):
        if a <= t <= b:
            return t
    return None


def eventi_per_kit(video, elenco_nas):
    """{numero del kit: [datetime degli eventi]} dagli eventi del sito (giorno + ora del nome) e dall'elenco del NAS
    (data della cartella + ora del nome). EX KIT conta per il suo numero (il registratore si sposta col kit)."""
    out = {}
    for y in video:
        d = y.get("dati") or {}
        k, o = numero(d.get("kit")), ora_nome(d.get("nome"))
        if k and o and d.get("giorno"):
            out.setdefault(k, set()).add(datetime.datetime.strptime(f"{d['giorno']} {o}", "%Y-%m-%d %H:%M:%S"))
    for e in elenco_nas:
        k, o, g = numero(e.get("kit")), ora_nome(e.get("nome")), str(e.get("quando") or "")[:10]
        if k and o and re.match(r"\d{4}-\d{2}-\d{2}$", g):
            out.setdefault(k, set()).add(datetime.datetime.strptime(f"{g} {o}", "%Y-%m-%d %H:%M:%S"))
    return out


# ------------------------------------------------------------------ la rete (sola lettura) e il file

def leggi(url, tok, timeout=180):
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=timeout) as r:
        return json.load(r)


def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    sys.path.insert(0, ANALISI)
    sys.path.insert(0, SCRIPTS)
    import gzip
    import banco_prova as bp
    import archivio_kit as ak
    from prepara_allunga import biglietto
    video = json.load(open(sys.argv[1], encoding="utf-8"))
    stato = json.load(open(sys.argv[2], encoding="utf-8"))
    righe = [r.rstrip("\n").split("\t") for r in gzip.open(sys.argv[3], "rt", encoding="utf-8", errors="replace")]
    elenco = ak.indice_da_elenco(righe)
    uscita = sys.argv[5] if len(sys.argv) > 5 else "pilota.json"
    zone = json.load(open(os.path.join(SCRIPTS, "zone_cassonetti.json"), encoding="utf-8"))["zone"]
    parti = bp.Parti(bp.carica_banco())
    oggi = datetime.date.today()
    archivio = stato.get("archivio") or []
    comune_di = {}
    for e in elenco:
        if numero(e.get("kit")):
            comune_di.setdefault(numero(e["kit"]), str(e.get("comune") or "").upper())
    for y in video:
        d = y.get("dati") or {}
        if numero(d.get("kit")) and d.get("comune"):
            comune_di[numero(d["kit"])] = str(d["comune"]).upper()

    def parte(n, comune=None):
        c = comune or comune_di.get(n)
        return parti.di_kit(f"{c}|{kit_zone(n)}") if c else None

    def zona(n, cam):
        z = (zone.get(kit_zone(n)) or {}).get(str(cam)) or {}
        r = ([z["zona"]] if z.get("zona") else []) + [b for b in z.get("altre") or [] if b]
        return {"riquadri": r, "escludi": [b for b in z.get("escludi") or [] if b]} if r else None

    # ---- positive
    tk = biglietto(sys.argv[4], "https://mappakit.alma/kit-rifiuti")
    per_ev = {}
    for y in video:
        per_ev.setdefault(y["evento"], []).append(y)
    ignora = bp.da_ignorare()
    schede, scartate = [], {}
    cutoff = min((a["primo"][:10] for a in archivio if a.get("primo")), default="2026-10-20")
    for e, l in sorted(per_ev.items()):
        d = l[0].get("dati") or {}
        if e in GIA_USATI or e in bp.ESCLUSI or e in ignora or bp.esito_di(l) != "ok" or any(y.get("bizzarro") for y in l):
            continue
        if not any(y.get("corrette") for y in l) or str(d.get("giorno") or "") < cutoff:
            continue
        n = numero(d.get("kit"))
        if not n:
            continue
        p = parte(n, str(d.get("comune") or "").upper())
        if p == "cieco":
            scartate[e] = "kit nella parte cieca"
            continue
        full = leggi(f"{KR}?op=evento&evento={e}", tk).get("video") or []
        if any(y.get("bizzarro") for y in full):
            continue
        aa = abbandono_atteso(full)
        if not aa:
            scartate[e] = "nessun riquadro d'abbandono di Dario"
            continue
        cam, atteso, box, s_clip = aa
        z = zona(n, cam)
        if not z:
            scartate[e] = f"la telecamera {cam} del kit non ha la zona dei cassonetti"
            continue
        reg = registratore(n, stato.get("kit") or [], oggi)
        if not reg:
            scartate[e] = "il registratore non ha risposto al giro di oggi"
            continue
        inizio, off = inizio_positiva(e, atteso)
        ok_, perche = sul_disco(archivio_di(archivio, reg["uid"], cam - 1), inizio, inizio + datetime.timedelta(hours=1), oggi)
        if not ok_:
            scartate[e] = perche
            continue
        schede.append({"evento": e, "kit": n, "notte": notte(atteso), "uid": reg["uid"], "canale": cam - 1,
                       "inizio": inizio.strftime("%Y-%m-%d %H:%M:%S"), "atteso": atteso.strftime("%Y-%m-%d %H:%M:%S"),
                       "atteso_s": off, "box_dario": box, "zona": z, "parte": p,
                       "misura": f"{d.get('W')}x{d.get('H')}", "clip": s_clip.strftime("%H:%M:%S"),
                       "come_atteso": f"clip delle {s_clip:%H:%M:%S} + riquadro d'abbandono di Dario sulla telecamera {cam}"})
    positive = scegli_positive(schede)
    # ---- negative: il pool dei kit che hanno risposto oggi, fuori dal cieco, con almeno una zona
    pool = []
    for k in sorted({str(x.get("kit") or "").lstrip("0") for x in stato.get("kit") or []}, key=lambda s: (len(s), s)):
        if not k.isdigit():
            continue
        n = int(k)
        reg = registratore(n, stato.get("kit") or [], oggi)
        if not reg or parte(n) in (None, "cieco"):
            continue
        canali = [c for c in range(8) if zona(n, c + 1) and archivio_di(archivio, reg["uid"], c)]
        if canali:
            pool.append({"kit": n, "uid": reg["uid"], "canali": canali,
                         "archivio": {c: archivio_di(archivio, reg["uid"], c) for c in canali}})
    estratte, non_disp = estrai_negative(pool, oggi, NEGATIVE * 3)
    ev_kit = eventi_per_kit(video, elenco)
    negative, scartate_neg = [], []
    for v in estratte:
        t = sovrapposto(v, ev_kit.get(v["kit"], ()))
        if t:
            scartate_neg.append(dict(v, perche=f"evento segnalato alle {t:%Y-%m-%d %H:%M:%S}"))
            continue
        v["zona"] = zona(v["kit"], v["canale"] + 1)
        v["parte"] = parte(v["kit"])
        negative.append(v)
    ore = []
    for i, s in enumerate(positive):
        ore.append(dict(s, nome=f"pos{i + 1:02d}_kit{s['kit']}", tipo="positiva"))
    for i, v in enumerate(negative[:NEGATIVE + RISERVE]):
        ore.append(dict(v, nome=f"neg{i + 1:02d}_kit{v['kit']}", tipo="negativa", riserva=i >= NEGATIVE))
    cfg = {"pc": "COMPUTERONE", "preparato_il": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "prepara": VERSIONE,
           "seme": SEME,
           "come": ("pilota.py: per ogni ora (a) dimezza.py sui campioni da 3 s e (b) una miniatura al minuto con il "
                    "confronto della zona a piena risoluzione col riferimento dei minuti prima, candidato se il cambio "
                    "resta 5 minuti; per ogni candidato prima, dopo, ritaglio, serie dei minuti e miniature ogni 2 s da "
                    "3 minuti prima a 1 dopo. Un processo a parte per ora. Positive e negative non si sommano."),
           "negative_quante": NEGATIVE, "ore": ore,
           "scelta": {"positive_possibili": len(schede), "positive_notte_possibili": sum(1 for s in schede if s["notte"]),
                      "positive_scartate": scartate, "negative_estratte": len(estratte),
                      "negative_scartate_per_evento": scartate_neg, "negative_non_disponibili": non_disp[:50],
                      "kit_nel_pool_negative": len(pool),
                      "regola_scarto": f"evento del sito o del NAS dello stesso kit fra {SCARTO_PRIMA_MIN} min prima e "
                                       f"{SCARTO_DOPO_MIN} min dopo l'ora (Dario 12/11)",
                      "elenco_nas_letto": len(elenco)}}
    with open(uscita, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=1)
    print(f"positive {len(positive)} (possibili {len(schede)}), negative {len(negative[:NEGATIVE])} + riserve "
          f"{len(negative[NEGATIVE:NEGATIVE + RISERVE])}, scartate per evento {len(scartate_neg)}")
    for o in ore:
        print(o["nome"], o["tipo"], "riserva" if o.get("riserva") else "", o["inizio"], "CH%d" % (o["canale"] + 1),
              "notte" if o["notte"] else "giorno", o.get("atteso", ""), o.get("parte"))


if __name__ == "__main__":
    main()
