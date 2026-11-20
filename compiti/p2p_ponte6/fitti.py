"""I fotogrammi in più dei minuti agitati (ponte p2p 0.25.0, compito p2p_ponte44). Kit_Rifiuti,
analisi/piu-fotogrammi-criterio-2026-11-20.md: Dario, su pos070, «con un fotogramma al minuto diventa difficile e
impossibile vedere abbandoni in cui il sacchetto non rimanga visibile».

Dentro un'ora della scorta (scorta.lavora_ora, quando cfg["fitti"] c'è), dopo le 72 miniature dei minuti: per gli
intervalli fra due minuti scelti, per_minuto - 1 miniature in più (GetThumbImage, ~50 kB l'una, la stessa chiamata
delle miniature dei minuti), in <cartella dell'ora sul PC>/fitti/HHMMSS.jpg. Gli intervalli:
  - «agitati»: quelli attorno a un minuto in cui la zona dei cassonetti si muove (kit_rifiuti.minuti_agitati della
    0.99.16 e dopo, sulle miniature appena scaricate; senza zona l'immagine intera), come farebbe il programma;
  - «tutti»: tutti i 71 intervalli dell'ora (per la misura: a tavolino si sceglie poi quali usare). ~18 MB per ora.
  ora["fitti_modo"] (prepara_fitti: «tutti» per le ore perse) vale più di cfg["modo"].
In x["fitti"]: modo, intervalli, richieste, arrivate, MB, secondi e lo scarto fra l'ora chiesta e quella vera del
fotogramma (ora_video del registratore: se il registratore dà solo i fotogrammi chiave, lo scarto lo dice).
Le funzioni pure (tempi, intervalli) sono copie di quelle di kit-rifiuti-programma scripts/fitti_ora.py 0.1.0: il PC
non le ha (non sono nell'exe). Prove a tavolino in prova_fitti.py.
version: 0.1.0 (20/11/2026)
"""
import datetime
import os
import time

VERSIONE = "0.1.0"
PER_MINUTO = 6
TETTO_RICHIESTE = 400        # miniature in più per ora al massimo (71 intervalli x 5 = 355)
SECONDI_MAX = 600.0          # oltre, le miniature in più di quell'ora si smettono (si scrive)


def cfg_fitti(c):
    """Le opzioni dei fitti dal compito: {"per_minuto": 4-6, "modo": "agitati" | "tutti"}."""
    c = dict(c or {})
    n = c.get("per_minuto", PER_MINUTO)
    n = int(n) if isinstance(n, (int, float)) and 2 <= n <= 12 else PER_MINUTO
    modo = c.get("modo") if c.get("modo") in ("agitati", "tutti") else "agitati"
    return {"per_minuto": n, "modo": modo}


def intervalli_agitati(agitati, n):
    """Come fitti_ora.intervalli_agitati: j (da ts[j] a ts[j+1]) se j o j+1 è agitato. Funzione pura."""
    out = set()
    for j in agitati:
        for k in (j - 1, j):
            if 0 <= k < n - 1:
                out.add(k)
    return sorted(out)


def tempi_fitti(ts, intervalli, per_minuto=PER_MINUTO):
    """Come fitti_ora.tempi_fitti: [(j, datetime)] spaziati fra ts[j] e ts[j+1], esclusi. Funzione pura."""
    out = []
    for j in intervalli:
        a, b = ts[j], ts[j + 1]
        passo = (b - a).total_seconds() / per_minuto
        out += [(j, a + datetime.timedelta(seconds=round(k * passo, 3))) for k in range(1, per_minuto)]
    return out


def scarto_s(chiesta, ora_video):
    """I secondi fra l'ora chiesta e quella vera del fotogramma («2026-11-03 10:23:05» o «10:23:05»), o None."""
    if not ora_video:
        return None
    s = str(ora_video)
    try:
        if len(s) >= 19:
            v = datetime.datetime.strptime(s[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
        else:
            h = datetime.datetime.strptime(s[:8], "%H:%M:%S")
            v = chiesta.replace(hour=h.hour, minute=h.minute, second=h.second, microsecond=0)
    except ValueError:
        return None
    return round((v - chiesta.replace(microsecond=0)).total_seconds(), 1)


def scegli(kr, fot, zona, modo):
    """Gli intervalli da chiedere: tutti, o quelli attorno ai minuti agitati (kr.minuti_agitati, se il kit_rifiuti del PC
    ce l'ha; se no tutti, e si scrive). Ritorna (intervalli, come)."""
    n = len(fot)
    if modo == "tutti":
        return list(range(n - 1)), "tutti"
    if not hasattr(kr, "minuti_agitati"):
        return list(range(n - 1)), "tutti (minuti_agitati manca nel kit_rifiuti del PC)"
    buone = [f for f in fot if f is not None]
    if not buone:
        return [], "nessuna miniatura"
    H, W = buone[0].shape[:2]
    riq = (zona or {}).get("riquadri") or [[0.0, 0.0, 1.0, 1.0]]
    zm = kr.maschera_zone(riq, (zona or {}).get("escludi") or [], H, W)
    ag = kr.minuti_agitati(fot, zm)
    return intervalli_agitati(ag, n), f"agitati ({len(ag)} minuti)"


def fai(ora, cfg, mezzi, cartella, av=lambda t: None, salva=lambda r: None):
    """Le miniature in più di un'ora. mezzi: quelli di pilota.lavora_ora (nuovo, collega, kr, decodifica, grezzi, cv2...);
    cartella: la cartella dell'ora sul PC (minuti/ già scaricati da pilota). Ritorna il registro (x["fitti"])."""
    import pilota as pl
    cv2 = mezzi.get("cv2")
    if cv2 is None:
        import cv2
    c = cfg_fitti(dict(cfg or {}, **({"modo": ora["fitti_modo"]} if ora.get("fitti_modo") else {})))   # l'ora decide
    t0 = time.time()
    inizio = pl.dt(ora["inizio"])
    ts = pl.tempi_scansione(inizio, int(float(ora.get("minuti", 60))))
    fot = []
    for t in ts:
        p = os.path.join(cartella, "minuti", f"{t:%H%M%S}.jpg")
        fot.append(cv2.imread(p) if os.path.exists(p) else None)
    r = {"fitti": VERSIONE, "per_minuto": c["per_minuto"], "modo": c["modo"]}
    if sum(f is not None for f in fot) < len(ts) * 0.8:
        r.update(esito="miniature dei minuti troppo poche: niente fitti")
        return r
    intervalli, come = scegli(mezzi["kr"], fot, ora.get("zona"), c["modo"])
    tempi = tempi_fitti(ts, intervalli, c["per_minuto"])[:TETTO_RICHIESTE]
    r.update(come=come, intervalli=len(intervalli), richieste=len(tempi), arrivate=0, mb=0.0, scarti_s=[])
    mezzi = dict(mezzi, tempi=dict(pl.TEMPI, **(mezzi.get("tempi") or {})))
    mezzi.setdefault("cimitero", [])
    lav = pl.Lavoro(mezzi, int(ora["canale"]), mezzi["grezzi"])
    os.makedirs(os.path.join(cartella, "fitti"), exist_ok=True)
    try:
        for k, (j, t) in enumerate(tempi):
            if time.time() - t0 > SECONDI_MAX:
                r["fermato"] = f"passati {SECONDI_MAX:g} s: {len(tempi) - k} miniature non chieste"
                break
            img = lav.miniatura(t, "fitti")
            if img is not None:
                pl.salva(img, os.path.join(cartella, "fitti", f"{t:%H%M%S}.jpg"), q=60)
                r["arrivate"] += 1
            if k % 50 == 49:
                r.update(mb=round(lav.conti["mb"], 2), secondi=round(time.time() - t0, 1))
                salva(r)
        reg = lav.registro([t for _, t in tempi])
        sc = [scarto_s(t, x.get("ora_video")) for (_, t), x in zip(tempi, reg)]
        sc = [s for s in sc if s is not None]
        r["scarti_s"] = {"n": len(sc), "zero": sum(1 for s in sc if abs(s) < 1),
                         "fino_a_5": sum(1 for s in sc if 1 <= abs(s) <= 5), "oltre_5": sum(1 for s in sc if abs(s) > 5),
                         "uguali_al_minuto": sum(1 for s in sc if abs(s) >= 9)} if sc else None
    except ConnectionError as ex:
        r["esito"] = f"collegamento perso: {str(ex)[:150]}"
    finally:
        try:
            lav.col.chiudi()
        except Exception:   # noqa: BLE001
            pass
    r.update(mb=round(lav.conti["mb"], 3), chiamate=lav.conti["chiamate"], secondi=round(time.time() - t0, 1))
    r.setdefault("esito", "fatto")
    av(f"fitti {ora['nome']}: {r['arrivate']}/{r['richieste']} miniature in più ({r['come']}), {r['mb']} MB, "
       f"{r['secondi']} s")
    return r
