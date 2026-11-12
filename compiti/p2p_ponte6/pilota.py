"""La prova pilota del registratore: il programma trova da solo un abbandono in un'ora di registrazione? (backlog-ridotto
2026-11-11, intervento 5; decisione-p2p-2026-11-11.md, sezione 4; protocollo-valutazione, Scorecard B. Dario, 12/11:
«dobbiamo comunque andare sulla seconda strada, quello e' l'obiettivo»).

Per ogni ora di pilota.json (positiva: c'e' un abbandono noto in un punto sorteggiato; negativa: sorteggiata senza
guardare gli eventi), sul canale della zona dei cassonetti, due metodi sugli stessi campioni:
  (a) dimezza.py 0.1.0 cosi' com'e': 3 s all'inizio e alla fine, poi a meta' finche' l'intervallo e' sotto 60 s
      (campioni video veri, 1280 pixel); a parte, gratis, lo stesso dimezzamento sulle miniature del metodo (b)
      («a_miniature»: il campione e' la miniatura del minuto piu' vicino);
  (b) scansione: una miniatura del registratore ogni minuto (GetThumbImage, 704x576, ~47 kB, 0,1-0,2 s; compito 28) da
      4 minuti prima a 5 dopo l'ora; per ogni minuto t il riferimento di scena e' la mediana dei 3 minuti prima, il dopo
      le miniature dei 5 minuti da t; pezzi_zona di kit_rifiuti (stessa luce in Lab, deltaE, «se n'e' andato
      qualcosa») a piena risoluzione della miniatura, con resta = 1: il pezzo e' diverso dal riferimento in TUTTI e
      5 i minuti (= il cambiamento resta almeno 5 minuti e all'inizio non c'era). Le rilevazioni dello stesso pezzo in
      minuti vicini diventano un candidato solo (comparsa = il primo minuto); la durata si misura in minuti finche' il
      pezzo c'e'.
Per i candidati (Claude li giudica da qui, e servono le quattro prove decise da Dario il 12/11: filtro di persistenza,
«compare dopo un passaggio o una sosta», Claude giudice, rigetto riaddestrato con le ore vuote), senza riscaricare:
  - il momento si stringe a 2 s con le miniature (dimezzamento sul pezzo fra il minuto prima e quello della comparsa);
  - miniature ogni 2 s da 3 minuti prima a 1 dopo il momento («fitte»: i fotogrammi chiave di chi si e' fermato),
    con il movimento vicino al pezzo e se il pezzo c'e', secondo per secondo;
  - prima.jpg, dopo.jpg, ritaglio.jpg (prima | dopo, ingranditi), serie.jpg (la zona minuto per minuto),
    intorno.jpg (il pezzo e i dintorni ogni 2 s) e scena.jpg (la scena ogni 6 s);
  - in uscita anche tutte le miniature dei minuti dell'ora (minuti/), per rifare i metodi a tavolino.
Le miniature grezze restano sul PC (cartella di lavoro). Si scrivono sempre MB, chiamate e secondi per metodo, per ora,
per kit e in tutto (Dario: niente tetti di banda, ma i MB sempre scritti); ogni chiamata ha un tempo massimo e ogni ora
un processo suo che si uccide (pilota_lavoro.py, come allunga_lavoro.py).
Tutto il lavoro vero (registratore, decodifica, kit_rifiuti) arriva da fuori: prove a tavolino in prova_pilota.py.
version: 0.2.0 (12/11/2026): cfg["solo_minuti"] per la prova grande (prepara_grande.py, compito p2p_ponte 0.15.0): per
  ogni ora solo le miniature dei minuti (minuti/ e ora.json, come la pilota), niente candidati, niente metodo (a),
  niente fitte; la misura del metodo «insieme» si fa a tavolino (b_tavolino.py, misura_b_tavolino.py). In ora.json
  delle positive anche dentro_zona, altri_noti, fonte, ora_del_kit e resta_giorni.
0.1.0 (12/11/2026): prima versione, per il compito p2p_ponte 0.14.0.
"""
import datetime
import os
import time

import numpy as np

VERSIONE = "0.2.0"
PASSO_S = 60              # una miniatura al minuto
PRIMA_MIN, DOPO_MIN = 6, 5  # la scansione comincia 6 minuti prima dell'ora (riferimento) e finisce 5 dopo (persistenza)
RIF_N = 5                 # il riferimento di scena: la mediana dei 5 minuti prima (un'auto di 2 minuti non lo sporca)
RESTA_N = 5               # il cambiamento deve restare 5 minuti
IOU_STESSO = 0.3          # due rilevazioni in minuti vicini con IoU >= 0,3 sono lo stesso pezzo
MASSIMI_MINUTO = 3        # pezzi tenuti per minuto
FITTA_PRIMA_S, FITTA_DOPO_S, FITTA_PASSO_S = 180, 60, 2
FITTE_MAX = 4             # candidati di (b) con le miniature fitte (i primi per punteggio), piu' quello di (a)
IMMAGINI_MAX = 8          # candidati di (b) con le immagini in uscita
CANDIDATI_MAX = 30        # candidati di (b) scritti nel json
ATTESA_MINIATURA = 12
RITENTATIVI_MAX = 12      # miniature richieste una seconda volta su un collegamento nuovo, per ora
TEMPI = {"nuovo": 30, "collega": 75, "canali": 20, "intervallo": 20, "miniatura": 20, "chiudi": 20,
         "scarica_fisso": 60, "scarica_per_secondo": 1.5}
LIMITI = {"minuti_per_ora": 25.0,          # poi il processo dell'ora si uccide
          "ore_in_tutto": 14.0,            # poi le ore dopo non si fanno
          "ritenta_errore_memoria": 1,
          "secondi_fitte_per_ora": 600.0}  # oltre, le miniature fitte dei candidati dopo non si chiedono (si scrive)
CODICI = {3221225477: "errore di memoria della libreria (0xC0000005)", 1: "errore in Python (vedi registro)",
          3: "una chiamata alla libreria non e' tornata in tempo: il processo si e' chiuso da solo"}
MEMORIA = 3221225477


def limiti_da(cfg):
    """LIMITI e TEMPI abbassati (mai alzati) da cfg["limiti"] e cfg["tempi"]."""
    lim, tempi = dict(LIMITI), dict(TEMPI)
    for k, v in ((cfg or {}).get("limiti") or {}).items():
        if k in lim and isinstance(v, (int, float)) and 0 <= v < lim[k]:
            lim[k] = type(lim[k])(v)
    for k, v in ((cfg or {}).get("tempi") or {}).items():
        if k in tempi and isinstance(v, (int, float)) and 0 < v < tempi[k]:
            tempi[k] = v
    return lim, tempi


def esito_processo(codice):
    if codice == 0:
        return "finito"
    if isinstance(codice, str):
        return codice
    return CODICI.get(codice, f"uscito con il codice {codice}")


# ------------------------------------------------------------------ funzioni pure

def dt(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def hms(t):
    return t.strftime("%H:%M:%S") if t else None


def tempi_scansione(inizio, minuti=60, prima_min=PRIMA_MIN, dopo_min=DOPO_MIN, passo_s=PASSO_S):
    """I momenti delle miniature dei minuti: da inizio - prima_min a inizio + minuti + dopo_min compresi."""
    t, fine, out = inizio - datetime.timedelta(minutes=prima_min), inizio + datetime.timedelta(minutes=minuti + dopo_min), []
    while t <= fine:
        out.append(t)
        t += datetime.timedelta(seconds=passo_s)
    return out


def tempi_fitti(momento, prima_s=FITTA_PRIMA_S, dopo_s=FITTA_DOPO_S, passo_s=FITTA_PASSO_S):
    m = momento.replace(microsecond=0)
    return [m + datetime.timedelta(seconds=s) for s in range(-int(prima_s), int(dopo_s) + 1, int(passo_s))]


def iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0.0, min(ax2, bx2) - max(a[0], b[0])), max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def area_min_per(largo):
    """pezzi_zona e' tarato a 1280 pixel (area minima 150): alla larghezza della miniatura, in proporzione."""
    return max(30, int(round(150 * (float(largo) / 1280.0) ** 2)))


def mediana(f):
    f = [x for x in f if x is not None]
    if not f:
        return None
    return f[0] if len(f) == 1 else np.median(np.stack(f), axis=0).astype(np.uint8)


def rilevazioni(kr, fot, riquadri, escludi=(), rif_n=RIF_N, resta_n=RESTA_N, massimi=MASSIMI_MINUTO):
    """fot: le immagini dei minuti in ordine (None se manca). Per ogni minuto i con almeno 2 riferimenti fra i rif_n
    prima e almeno resta_n - 1 miniature fra le resta_n da i (la i compresa): i pezzi cambiati che restano in tutte e
    che non erano gia' cosi' in nessuno dei minuti di riferimento.
    [{"i", "box", "area", "dE", "punteggio", "via"}]."""
    buone = [f for f in fot if f is not None]
    if not buone:
        return []
    H, W = buone[0].shape[:2]
    zm = kr.maschera_zone(riquadri, escludi, H, W)
    amin = area_min_per(W)
    out = []
    for i in range(rif_n, len(fot) - resta_n + 1):
        if fot[i] is None:
            continue
        rif = [f for f in fot[i - rif_n:i] if f is not None and f.shape == fot[i].shape]
        dopo = [f for f in fot[i:i + resta_n] if f is not None and f.shape == fot[i].shape]
        if len(rif) < 2 or len(dopo) < resta_n - 1:
            continue
        A, B = mediana(rif), mediana(dopo)
        cand, _ = kr.pezzi_zona(A, B, dopo, zm, area_min=amin, resta=1.0, massimi=massimi)
        for c in cand:
            # «all'inizio non c'era»: se in uno dei minuti di riferimento il pezzo era gia' come dopo, non e' una cosa
            # nuova (un'auto che se ne va e lascia vedere il fondo, un sacco gia' li' che qualcuno copriva)
            pp = kr.pixel_pezzo(A, B, zm, c["box"])
            if any(kr.presente_pezzo(f, pp)[0] for f in rif):
                continue
            out.append({"i": i, **{k: c.get(k) for k in ("box", "area", "dE", "punteggio", "via")}})
    return out


def unisci(ril, iou_min=IOU_STESSO, salto=2):
    """Le rilevazioni dello stesso pezzo in minuti vicini (al massimo `salto` minuti dopo l'ultima, IoU >= iou_min)
    in un candidato: [{"i" (primo minuto), "box" (del primo), "punteggio" (il massimo), "minuti_rilevato", "ultimo_i"}]
    in ordine di punteggio."""
    tracce = []
    for r in sorted(ril, key=lambda r: (r["i"], -r["punteggio"])):
        t = next((t for t in tracce if 0 < r["i"] - t["ultimo_i"] <= salto and iou(t["ultimo_box"], r["box"]) >= iou_min), None)
        if t is None:
            tracce.append({"i": r["i"], "box": [round(v, 4) for v in r["box"]], "area": r["area"], "dE": r["dE"],
                           "punteggio": r["punteggio"], "via": r["via"], "minuti_rilevato": 1, "ultimo_i": r["i"],
                           "ultimo_box": r["box"]})
        elif t["ultimo_i"] != r["i"]:
            t.update(minuti_rilevato=t["minuti_rilevato"] + 1, ultimo_i=r["i"], ultimo_box=r["box"],
                     punteggio=max(t["punteggio"], r["punteggio"]))
    for t in tracce:
        t.pop("ultimo_box")
    return sorted(tracce, key=lambda t: -t["punteggio"])


def durata(kr, fot, i, riquadri, escludi=(), box=None, rif_n=RIF_N, resta_n=RESTA_N, buchi=1):
    """Per quanti minuti, dalla comparsa i, il pezzo c'e' (presente_pezzo sui suoi pixel cambiati, riferimento e dopo
    come in rilevazioni), tollerando `buchi` minuti di fila senza (qualcuno davanti). Ritorna (minuti, fino_alla_fine,
    stati [0/1/None per minuto da i])."""
    H, W = fot[i].shape[:2]
    zm = kr.maschera_zone(riquadri, escludi, H, W)
    A = mediana([f for f in fot[max(0, i - rif_n):i] if f is not None])
    B = mediana([f for f in fot[i:i + resta_n] if f is not None])
    pp = kr.pixel_pezzo(A, B, zm, box)
    stati, ultimo, vuoti = [], i, 0
    for j in range(i, len(fot)):
        if fot[j] is None:
            stati.append(None)
            continue
        si = bool(kr.presente_pezzo(fot[j], pp)[0])
        stati.append(1 if si else 0)
        if si:
            ultimo, vuoti = j, 0
        else:
            vuoti += 1
            if vuoti > buchi:
                break
    fino = ultimo >= len(fot) - 1 - buchi
    return ultimo - i + 1, fino, stati, (A, B, zm, pp)


def presente_fn(kr, pp):
    return lambda F: bool(kr.presente_pezzo(F, pp)[0])


def affina(campione, lo, hi, presente, soglia_s=FITTA_PASSO_S, passi_max=8):
    """Il momento in cui il pezzo compare fra lo (non c'e') e hi (c'e'), datetime, a meta' finche' l'intervallo e'
    sotto soglia_s; campione(t) -> immagine o None. Ritorna (lo, hi, passi)."""
    passi = []
    while (hi - lo).total_seconds() > soglia_s and len(passi) < passi_max:
        m = lo + (hi - lo) / 2
        m = m.replace(microsecond=0)
        if m <= lo or m >= hi:
            break
        F = campione(m)
        if F is None:
            passi.append([hms(m), None])
            break
        si = presente(F)
        passi.append([hms(m), si])
        if si:
            hi = m
        else:
            lo = m
    return lo, hi, passi


def movimento_vicino(fitte, box, margine=1.0):
    """Per le immagini fitte (in ordine, None se manca) il cambiamento medio in grigi, tolta la luce, nei dintorni del
    pezzo (il riquadro allargato di `margine` per lato) rispetto all'immagine prima: chi passa o si ferma li' vicino.
    [valore o None]."""
    out, prima = [], None
    for f in fitte:
        if f is None:
            out.append(None)
            continue
        H, W = f.shape[:2]
        x, y, w, h = box
        x0, y0 = max(0, int((x - margine * w) * W)), max(0, int((y - margine * h) * H))
        x1, y1 = min(W, int((x + w + margine * w) * W) + 1), min(H, int((y + h + margine * h) * H) + 1)
        g = f[y0:y1, x0:x1].astype(np.float32).mean(axis=2)
        if prima is None or prima.shape != g.shape:
            out.append(None)
        else:
            d = g - prima
            out.append(round(float(np.abs(d - np.median(d)).mean()), 2))
        prima = g
    return out


def confronto(candidati, atteso, box_dario, finestra_s=60, iou_min=0.1):
    """Per una positiva: il primo candidato (in ordine) che tocca il riquadro di Dario (IoU >= iou_min) con il momento
    entro finestra_s dall'atteso, e il primo che lo tocca a qualunque ora. candidati: [{"momento": datetime o None,
    "box"}]. Ritorna {"posto", "scarto_s", "posto_senza_tempo"} (posti da 1, None se nessuno)."""
    out = {"posto": None, "scarto_s": None, "posto_senza_tempo": None}
    for k, c in enumerate(candidati):
        if not c.get("box") or iou(c["box"], box_dario) < iou_min:
            continue
        if out["posto_senza_tempo"] is None:
            out["posto_senza_tempo"] = k + 1
        if c.get("momento") is not None and abs((c["momento"] - atteso).total_seconds()) <= finestra_s and out["posto"] is None:
            out["posto"], out["scarto_s"] = k + 1, round((c["momento"] - atteso).total_seconds(), 1)
    return out


def coperto(iv, da, a):
    """Il registratore ha [da, a)? (si/no, perche'); iv None = non detto, si prova."""
    if not iv or not iv[0] or not iv[1]:
        return True, "intervallo non detto dal registratore: si prova"
    if da < iv[0]:
        return False, f"non piu' sul registratore (registra dal {iv[0]:%d/%m/%Y %H:%M})"
    if a > iv[1]:
        return False, f"non ancora sul registratore (ultima registrazione {iv[1]:%d/%m/%Y %H:%M})"
    return True, "c'e'"


# ------------------------------------------------------------------ immagini (cv2, solo quando serve)

def _cv2():
    import cv2
    return cv2


def salva(img, percorso, largo=None, q=70):
    cv2 = _cv2()
    if img is None:
        return None
    if largo and img.shape[1] != largo:
        img = cv2.resize(img, (largo, max(1, int(round(img.shape[0] * largo / img.shape[1])))), interpolation=cv2.INTER_AREA)
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    cv2.imwrite(percorso, img, [cv2.IMWRITE_JPEG_QUALITY, int(q)])
    return os.path.basename(percorso)


def ritaglia(img, box, margine=1.0):
    H, W = img.shape[:2]
    x, y, w, h = box
    x0, y0 = max(0, int((x - margine * w) * W)), max(0, int((y - margine * h) * H))
    x1, y1 = min(W, int((x + w + margine * w) * W) + 1), min(H, int((y + h + margine * h) * H) + 1)
    return img[y0:max(y0 + 1, y1), x0:max(x0 + 1, x1)]


def zona_box(riquadri):
    x0, y0 = min(r[0] for r in riquadri), min(r[1] for r in riquadri)
    x1, y1 = max(r[0] + r[2] for r in riquadri), max(r[1] + r[3] for r in riquadri)
    return [max(0.0, x0), max(0.0, y0), min(1.0, x1) - max(0.0, x0), min(1.0, y1) - max(0.0, y0)]


def foglio(immagini, etichette, colonne, lato):
    """Le immagini (BGR o None) in una griglia di `colonne`, ognuna larga `lato`, con l'etichetta in alto."""
    cv2 = _cv2()
    buone = [f for f in immagini if f is not None]
    if not buone:
        return None
    hh = max(1, int(round(lato * buone[0].shape[0] / buone[0].shape[1])))
    righe = -(-len(immagini) // colonne)
    out = np.zeros((righe * hh, colonne * lato, 3), np.uint8)
    for k, (f, e) in enumerate(zip(immagini, etichette)):
        r, c = divmod(k, colonne)
        if f is not None:
            out[r * hh:(r + 1) * hh, c * lato:(c + 1) * lato] = cv2.resize(f, (lato, hh), interpolation=cv2.INTER_AREA)
        cv2.putText(out, str(e), (c * lato + 3, r * hh + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
    return out


def ingrandito(prima, dopo, box, lato=320):
    """Prima | dopo del pezzo con i dintorni (meta' del suo lato per parte), ognuno largo `lato`."""
    cv2 = _cv2()
    a, b = ritaglia(prima, box, 0.5), ritaglia(dopo, box, 0.5)
    hh = max(1, int(round(lato * a.shape[0] / max(1, a.shape[1]))))
    a = cv2.resize(a, (lato, hh), interpolation=cv2.INTER_CUBIC)
    b = cv2.resize(b, (lato, hh), interpolation=cv2.INTER_CUBIC)
    return np.concatenate([a, np.full((hh, 4, 3), 255, np.uint8), b], axis=1)


# ------------------------------------------------------------------ il lavoro di un'ora (registratore dato da fuori)

class _Fine(Exception):
    """L'ora finisce qui (non valutabile): l'esito e' gia' scritto."""


class Lavoro:
    """Il collegamento (allunga.Collegamento: fresco 200 s, chiamate sotto tempo massimo, cimitero) con le miniature, e
    i conti per voce («b», «fitte», «a»)."""

    def __init__(self, mezzi, canale, cartella_grezzi):
        import allunga as al
        self.al = al
        self.conti = {"chiamate": 0, "collegamenti": 0, "mb": 0.0}
        self.col = al.Collegamento(mezzi, self.conti)
        self.m, self.canale, self.grezzi = mezzi, canale, cartella_grezzi
        self.voci = {}
        self.cache = {}
        self.ritentativi = 0
        self.persi = 0

    def voce(self, v):
        return self.voci.setdefault(v, {"chiamate": 0, "mb": 0.0, "secondi": 0.0, "richieste": 0, "arrivate": 0, "errori": 0})

    def miniatura(self, t, voce):
        """L'immagine BGR della miniatura all'ora t (datetime), o None; una volta sola per momento."""
        k = t.replace(microsecond=0)
        if k in self.cache:
            return self.cache[k]["img"]
        v = self.voce(voce)
        r, err = None, None
        for prova in range(2):
            t0 = time.time()
            c0 = self.conti["chiamate"]
            try:
                try:
                    self.col.apri()
                    self.persi = 0
                except ConnectionError as ex:   # un collegamento perso a meta': si scrive, al terzo di fila si smette
                    self.persi += 1
                    if self.persi >= 3:
                        raise
                    err = f"collegamento: {str(ex)[:80]}"
                    break
                h = self.col.per.get(self.canale)
                if h is None:
                    err = "canale assente"
                    break
                r = self.col.chiama("miniatura", lambda: self.col.reg.miniatura(h, k, ATTESA_MINIATURA))
            finally:
                v["secondi"] = round(v["secondi"] + time.time() - t0, 2)
                v["chiamate"] += self.conti["chiamate"] - c0
            v["richieste"] += 1
            if r and r.get("dati"):
                break
            err = (r or {}).get("errore") or "nessuna miniatura"
            if prova == 0 and self.ritentativi < RITENTATIVI_MAX:
                self.ritentativi += 1
                self.col.chiudi()
                continue
            break
        x = {"t": hms(k), "img": None}
        if r and r.get("dati"):
            n = len(r["dati"])
            self.conti["mb"] += n / 1e6
            v["mb"] = round(v["mb"] + n / 1e6, 3)
            v["arrivate"] += 1
            x.update(byte=n, ora_video=r.get("ora_video"), misura=r.get("misura"))
            grezzo = os.path.join(self.grezzi, f"{k:%Y%m%d_%H%M%S}" + (".hevc" if r.get("formato") == "H.265" else ".h264"))
            try:   # il grezzo resta sul PC: si puo' rifare tutto senza il registratore
                with open(grezzo, "wb") as fh:
                    if r["dati"][:3] != b"\x00\x00\x01" and r["dati"][:4] != b"\x00\x00\x00\x01":
                        fh.write(b"\x00\x00\x00\x01")
                    fh.write(r["dati"])
            except OSError:
                pass
            try:
                x["img"] = self.m["decodifica"](r["dati"], r.get("formato"), grezzo)
            except Exception as ex:   # noqa: BLE001
                x["errore"] = f"decodifica: {type(ex).__name__}: {str(ex)[:100]}"
            if x["img"] is None and "errore" not in x:
                x["errore"] = "decodifica: niente"
        else:
            v["errori"] += 1
            x["errore"] = err
        self.cache[k] = x
        return x["img"]

    def registro(self, tempi):
        return [{k: v for k, v in self.cache[t.replace(microsecond=0)].items() if k != "img"}
                for t in tempi if t.replace(microsecond=0) in self.cache]


def lavora_ora(ora, cfg, mezzi, scrivi=lambda x: None, av=lambda t: None):
    """Un'ora di pilota.json. mezzi: nuovo, collega(reg) -> (ok, testo), tempi, cimitero, ffmpeg, kr (kit_rifiuti),
    decodifica(dati, formato, grezzo) -> BGR o None, fotogrammi(mp4) -> [BGR] (i campioni di dimezza), uscita (la
    cartella in uscita dell'ora), grezzi (la cartella sul PC). Ritorna il dict dell'ora, scritto anche man mano."""
    import dimezza as dz
    kr = mezzi["kr"]
    lim, tempi_ = limiti_da(cfg)
    mezzi = dict(mezzi, tempi=dict(tempi_, **(mezzi.get("tempi") or {})))
    mezzi.setdefault("cimitero", [])
    U = mezzi["uscita"]
    os.makedirs(U, exist_ok=True)
    os.makedirs(mezzi["grezzi"], exist_ok=True)
    t0 = time.time()
    inizio = dt(ora["inizio"])
    durata_s = float(ora.get("minuti", 60)) * 60
    fine = inizio + datetime.timedelta(seconds=durata_s)
    canale = int(ora["canale"])
    riq, esc = ora["zona"]["riquadri"], ora["zona"].get("escludi") or []
    x = {"nome": ora["nome"], "tipo": ora["tipo"], "kit": ora["kit"], "canale": canale, "telecamera": canale + 1,
         "inizio": ora["inizio"], "fine": fine.strftime("%Y-%m-%d %H:%M:%S"), "notte": ora.get("notte"),
         "riserva": bool(ora.get("riserva")), "pilota": VERSIONE, "dimezza": dz.VERSIONE, "in_corso": True,
         "inizio_lavoro": time.strftime("%Y-%m-%d %H:%M:%S"), "zona": ora["zona"]}
    if ora["tipo"] == "positiva":
        x.update(atteso=ora.get("atteso"), box_dario=ora.get("box_dario"), evento=ora.get("evento"))
        for k in ("box_da", "fonte", "dentro_zona", "altri_noti", "ora_del_kit", "resta_giorni"):   # 0.2.0
            if k in ora:
                x[k] = ora[k]
    solo_minuti = bool((cfg or {}).get("solo_minuti"))   # 0.2.0: la prova grande
    if solo_minuti:
        x["solo_minuti"] = True
    lav = Lavoro(mezzi, canale, mezzi["grezzi"])

    def salva_x():
        x["conti"] = {"chiamate": lav.conti["chiamate"], "collegamenti": lav.conti["collegamenti"],
                      "mb": round(lav.conti["mb"], 3), "secondi": round(time.time() - t0, 1), "per_metodo": lav.voci}
        scrivi(x)

    if not ora.get("uid"):
        x.update(esito="registratore sconosciuto", valutabile=False, in_corso=False)
        salva_x()
        return x
    try:
        # 0) il registratore ha l'ora?
        iv = lav.col.intervallo(canale)
        x["registrazione"] = [str(v) for v in iv] if iv else None
        if canale not in lav.col.per:
            x.update(esito="canale assente sul registratore", valutabile=False)
            raise _Fine
        ts = tempi_scansione(inizio, int(durata_s // 60))
        ok, perche = coperto(iv, ts[0], ts[-1])
        if not ok:
            x.update(esito=perche, valutabile=False)
            raise _Fine
        # 1) metodo (b): una miniatura al minuto
        t1 = time.time()
        fot = [lav.miniatura(t, "b") for t in ts]
        x["minuti"] = lav.registro(ts)
        for t, f in zip(ts, fot):
            if f is not None:
                salva(f, os.path.join(U, "minuti", f"{t:%H%M%S}.jpg"), q=60)
        arrivate = sum(1 for f in fot if f is not None)
        x["b"] = {"miniature": len(ts), "arrivate": arrivate, "secondi_scarico": round(time.time() - t1, 1)}
        salva_x()
        if arrivate < len(ts) * 0.8:
            x.update(esito=f"miniature arrivate {arrivate} su {len(ts)}: ora non valutabile", valutabile=False)
            raise _Fine
        if solo_minuti:   # 0.2.0: il resto si fa a tavolino
            x.update(esito="fatto", valutabile=True)
            raise _Fine
        t2 = time.time()
        ril = rilevazioni(kr, fot, riq, esc)
        cand = [c for c in unisci(ril) if inizio <= ts[c["i"]] < fine + datetime.timedelta(seconds=PASSO_S)]
        for k, c in enumerate(cand[:CANDIDATI_MAX]):
            m, fino, stati, (A, B, zm, pp) = durata(kr, fot, c["i"], riq, esc, c["box"])
            c.update(id=f"b{k + 1:02d}", comparsa_fra=[hms(ts[c["i"] - 1]), hms(ts[c["i"]])], durata_min=m,
                     fino_alla_fine=fino, stati=stati, _pp=pp, _A=A, _B=B)
        x["b"].update(rilevazioni=len(ril), candidati_tutti=len(cand), secondi_calcolo=round(time.time() - t2, 1))
        cand = cand[:CANDIDATI_MAX]
        # 2) (a) sulle miniature, gratis: il campione e' la miniatura del minuto piu' vicino
        idx = {round((t - inizio).total_seconds()): f for t, f in zip(ts, fot)}

        def da_miniature(t):
            k = int(round(t / PASSO_S)) * PASSO_S
            f = idx.get(k)
            return ([f], {"mb": 0.0, "secondi": 0.0, "secondi_video": 0.0}) if f is not None else (None, {"errore": "manca"})
        cm = dz.Campioni(da_miniature)
        try:
            x["a_miniature"] = dz.cerca(_KrMini(kr), cm, durata_s, riq, esc, dimezza_altri=1)
        except Exception as ex:   # noqa: BLE001
            x["a_miniature"] = {"esito": f"errore {type(ex).__name__}: {str(ex)[:150]}"}
        _momenti_a(x["a_miniature"], inizio)
        salva_x()
        # 3) metodo (a): dimezza.py cosi' com'e', campioni video veri da 3 s
        t3 = time.time()
        va = lav.voce("a")
        tmp = os.path.join(mezzi["grezzi"], "campioni")

        def leggi(t):
            da = inizio + datetime.timedelta(seconds=t)
            c0, m0 = lav.conti["chiamate"], lav.conti["mb"]
            q0 = time.time()
            res = lav.col.scarica(canale, da, dz.CAMPIONE_S, tmp)
            mb = float(res.get("mb") or 0)
            lav.conti["mb"] = m0 + mb
            va["chiamate"] += lav.conti["chiamate"] - c0
            va["mb"] = round(va["mb"] + mb, 3)
            va["secondi"] = round(va["secondi"] + time.time() - q0, 2)
            va["richieste"] += 1
            f = str(res.get("file") or "")
            F = None
            if f.endswith(".mp4"):
                try:
                    F = mezzi["fotogrammi"](f) or None
                finally:
                    _togli(f)
            else:
                _togli(f)
            if F:
                va["arrivate"] += 1
            else:
                va["errori"] += 1
            return F, {"mb": mb, "secondi": res.get("attesa_s"), "secondi_video": dz.CAMPIONE_S if F else 0,
                       "errore": res.get("errore")}
        ca = dz.Campioni(leggi)
        try:
            x["a"] = dz.cerca(kr, ca, durata_s, riq, esc, dimezza_altri=1)
        except lav.al.Bloccata:
            raise
        except ConnectionError as ex:   # (b) e' gia' fatto: l'ora resta valutabile per (b)
            x["a"] = {"esito": f"registratore non raggiunto: {str(ex)[:150]}"}
        except Exception as ex:   # noqa: BLE001
            x["a"] = {"esito": f"errore {type(ex).__name__}: {str(ex)[:150]}"}
        x["a"]["campioni"] = ca.registro
        x["a"]["conti"] = dict(ca.conti, secondi_lavoro=round(time.time() - t3, 1))
        _momenti_a(x["a"], inizio)
        salva_x()
        # 4) i candidati: momento a 2 s, miniature fitte, immagini
        candidati_a = _candidati_a(x["a"], ca, inizio)
        passo = int(cfg.get("fitte_passo_s") or FITTA_PASSO_S)   # le prove a tavolino lo allargano
        x["b"]["candidati"] = []
        t4 = time.time()
        for k, c in enumerate(cand):
            i = c["i"]
            y = {kk: c[kk] for kk in ("id", "box", "area", "dE", "punteggio", "via", "minuti_rilevato", "comparsa_fra",
                                      "durata_min", "fino_alla_fine", "stati")}
            y["comparsa_minuto"] = hms(ts[i])
            pres = presente_fn(kr, c["_pp"])
            if k < FITTE_MAX and time.time() - t4 < lim["secondi_fitte_per_ora"]:
                lo, hi, passi = affina(lambda t: lav.miniatura(t, "fitte"), ts[i - 1], ts[i], pres)
                y.update(momento=hms(lo + (hi - lo) / 2), momento_fra=[hms(lo), hms(hi)], passi_momento=passi)
                c["momento"] = lo + (hi - lo) / 2
                y["fitte"] = _fitte(lav, c["momento"], c["box"], pres, os.path.join(U, y["id"]), passo)
            else:
                c["momento"] = ts[i] - datetime.timedelta(seconds=PASSO_S / 2)
                y["momento"] = hms(c["momento"])
                y["momento_fra"] = y["comparsa_fra"]
                if k < FITTE_MAX:
                    y["fitte"] = {"nota": f"tempo delle miniature fitte finito ({lim['secondi_fitte_per_ora']} s)"}
            if k < IMMAGINI_MAX:
                y["immagini"] = _immagini(c["_A"], fot[i + RESTA_N - 1] if i + RESTA_N - 1 < len(fot) and fot[i + RESTA_N - 1] is not None else c["_B"],
                                          c["box"], fot, ts, i, c["durata_min"], riq, os.path.join(U, y["id"]))
            x["b"]["candidati"].append(y)
            salva_x()
        for y in candidati_a:
            A, B = mediana(y.get("_lo") or []), mediana(y.get("_hi") or [])
            if A is not None and B is not None:
                y["immagini"] = {}
                try:
                    cy = os.path.join(U, y["id"])
                    y["immagini"] = {"prima": salva(A, os.path.join(cy, "prima.jpg"), largo=704, q=75),
                                     "dopo": salva(B, os.path.join(cy, "dopo.jpg"), largo=704, q=75),
                                     "ritaglio": salva(ingrandito(A, B, y["box"]), os.path.join(cy, "ritaglio.jpg"), q=80)}
                except Exception as ex:   # noqa: BLE001
                    y["immagini"]["errore"] = f"{type(ex).__name__}: {str(ex)[:120]}"
            dup = next((c["id"] for c in cand if c.get("momento") and abs((c["momento"] - y["_momento"]).total_seconds()) <= 120
                        and iou(c["box"], y["box"]) >= 0.1), None)
            if dup:
                y["come_candidato_b"] = dup
            elif time.time() - t4 < lim["secondi_fitte_per_ora"]:
                y["fitte"] = _fitte(lav, y["_momento"], y["box"], None, os.path.join(U, y["id"]), passo)
        x["a"]["candidati"] = [{k: v for k, v in y.items() if not k.startswith("_")} for y in candidati_a]
        x["fitte_secondi"] = round(time.time() - t4, 1)
        # 5) per le positive, il confronto con il riquadro di Dario (solo per leggere: il metodo non lo vede)
        if ora["tipo"] == "positiva" and ora.get("atteso") and ora.get("box_dario"):
            at, bd = dt(ora["atteso"]), ora["box_dario"]
            x["confronto"] = {
                "b": confronto([{"momento": c.get("momento"), "box": c["box"]} for c in cand], at, bd),
                "a": confronto([{"momento": y["_momento"], "box": y["box"]} for y in candidati_a], at, bd),
                "a_miniature": confronto([{"momento": _momento_di(x["a_miniature"], inizio), "box": (x["a_miniature"].get("scelto") or {}).get("box")}], at, bd)}
        x["esito"], x["valutabile"] = "fatto", True
    except _Fine:
        pass
    except lav.al.Bloccata as ex:   # se (b) era gia' calcolato l'ora resta valutabile per (b): si dice cosa manca
        x.update(esito=f"bloccato: {ex}", bloccato=True, valutabile=(x.get("b") or {}).get("candidati_tutti") is not None)
    except ConnectionError as ex:
        x.update(esito=f"registratore non raggiunto: {ex}", valutabile=(x.get("b") or {}).get("candidati_tutti") is not None)
    except (OSError, RuntimeError) as ex:
        x.update(esito=("libreria non caricata: " if not lav.col.storia else "errore: ") + f"{type(ex).__name__}: {str(ex)[:200]}",
                 valutabile=False)
    finally:
        if not x.get("bloccato"):
            lav.col.chiudi()
    x["collegamenti"] = lav.col.storia
    x["in_corso"] = False
    x["fine_lavoro"] = time.strftime("%Y-%m-%d %H:%M:%S")
    salva_x()
    av(f"pilota {ora['nome']}: {x.get('esito')}, {x['conti']['mb']} MB, {x['conti']['chiamate']} chiamate, "
       f"{len((x.get('b') or {}).get('candidati') or [])} candidati (b)")
    return x


class _KrMini:
    """kit_rifiuti per (a) sulle miniature: pezzi_zona con l'area minima della miniatura."""

    def __init__(self, kr):
        self.kr = kr

    def __getattr__(self, k):
        return getattr(self.kr, k)

    def pezzi_zona(self, A, B, dopo, zm, **k):
        k.setdefault("area_min", area_min_per(A.shape[1]))
        return self.kr.pezzi_zona(A, B, dopo, zm, **k)


def _momento_di(r, inizio):
    if not r or r.get("esito") != "cambio" or r.get("momento") is None:
        return None
    return inizio + datetime.timedelta(seconds=float(r["momento"]))


def _momenti_a(r, inizio):
    if r and r.get("esito") == "cambio":
        r["momento_ora"] = hms(_momento_di(r, inizio))
        for a in r.get("altri") or []:
            if a.get("momento") is not None:
                a["momento_ora"] = hms(inizio + datetime.timedelta(seconds=float(a["momento"])))


def _candidati_a(r, ca, inizio):
    """I candidati di (a): lo scelto e gli altri dimezzati, con prima e dopo (i campioni a lo e hi) in uscita."""
    out = []
    if not r or r.get("esito") != "cambio":
        return out
    voci = [("a01", r.get("scelto") or {}, r.get("lo"), r.get("hi"), r.get("momento"))]
    for k, a in enumerate(r.get("altri") or []):
        if a.get("lo") is not None:
            voci.append((f"a{k + 2:02d}", a, a["lo"], a["hi"], a.get("momento")))
    for idv, p, lo, hi, m in voci:
        if not p.get("box") or m is None:
            continue
        out.append({"id": idv, "box": p["box"], "momento": hms(inizio + datetime.timedelta(seconds=float(m))),
                    "_momento": inizio + datetime.timedelta(seconds=float(m)), "_lo": ca.visti.get(round(float(lo), 1)),
                    "_hi": ca.visti.get(round(float(hi), 1))})
    return out


def _fitte(lav, momento, box, pres, cartella, passo_s=FITTA_PASSO_S):
    """Le miniature ogni 2 s da 3 minuti prima a 1 dopo il momento: movimento nei dintorni, il pezzo c'e' o no, i fogli
    intorno.jpg e scena.jpg. Ritorna il riassunto (MB e secondi per conto proprio)."""
    v0 = dict(lav.voce("fitte"))
    t0 = time.time()
    ts = tempi_fitti(momento, passo_s=passo_s)
    fot = [lav.miniatura(t, "fitte") for t in ts]
    v1 = lav.voce("fitte")
    out = {"da": hms(ts[0]), "a": hms(ts[-1]), "passo_s": passo_s, "chieste": len(ts),
           "arrivate": sum(1 for f in fot if f is not None), "mb": round(v1["mb"] - v0["mb"], 3),
           "secondi": round(time.time() - t0, 1), "movimento_vicino": movimento_vicino(fot, box)}
    if pres is not None:
        out["pezzo_presente"] = [None if f is None else int(pres(f)) for f in fot]
    et = [hms(t) for t in ts]
    try:
        out["intorno"] = salva(foglio([None if f is None else ritaglia(f, box, 1.5) for f in fot], et, 11, 160),
                               os.path.join(cartella, "intorno.jpg"), q=60)
        out["scena"] = salva(foglio(fot[::3], et[::3], 8, 240), os.path.join(cartella, "scena.jpg"), q=60)
    except Exception as ex:   # noqa: BLE001
        out["errore_immagini"] = f"{type(ex).__name__}: {str(ex)[:120]}"
    return out


def _immagini(A, B, box, fot, ts, i, durata_min, riquadri, cartella):
    """prima.jpg (il riferimento), dopo.jpg, ritaglio.jpg (prima | dopo ingranditi), serie.jpg (la zona dei minuti da 5
    prima a 2 dopo la fine del pezzo, al massimo 24)."""
    out = {}
    try:
        out["prima"] = salva(A, os.path.join(cartella, "prima.jpg"), q=75)
        out["dopo"] = salva(B, os.path.join(cartella, "dopo.jpg"), q=75)
        out["ritaglio"] = salva(ingrandito(A, B, box), os.path.join(cartella, "ritaglio.jpg"), q=80)
        a, b = max(0, i - 5), min(len(fot), i + int(durata_min) + 2)
        b = min(b, a + 24)
        zb = zona_box(riquadri)
        out["serie"] = salva(foglio([None if f is None else ritaglia(f, zb, 0.1) for f in fot[a:b]],
                                    [hms(t)[:5] for t in ts[a:b]], 8, 200), os.path.join(cartella, "serie.jpg"), q=65)
    except Exception as ex:   # noqa: BLE001
        out["errore"] = f"{type(ex).__name__}: {str(ex)[:120]}"
    return out


def _togli(f):
    try:
        if f and os.path.exists(f):
            os.remove(f)
    except OSError:
        pass


# ------------------------------------------------------------------ il giro di tutte le ore (nel ponte)

def coda(ore, negative_quante):
    """L'ordine delle ore: una positiva e due negative alternate (se il tempo finisce restano tutte e due le
    popolazioni), le riserve in fondo. Ritorna (coda, riserve)."""
    pos = [o for o in ore if o["tipo"] == "positiva"]
    neg = [o for o in ore if o["tipo"] == "negativa" and not o.get("riserva")][:negative_quante]
    ris = [o for o in ore if o["tipo"] == "negativa" and o.get("riserva")]
    out = []
    while pos or neg:
        if pos:
            out.append(pos.pop(0))
        for _ in range(2):
            if neg:
                out.append(neg.pop(0))
    return out, ris


def conti_di(ore):
    """MB, chiamate, secondi: in tutto, per tipo, per kit e per metodo; esiti; ore valutabili."""
    def vuoto():
        return {"ore": 0, "valutabili": 0, "mb": 0.0, "chiamate": 0, "secondi": 0.0,
                "mb_b": 0.0, "mb_fitte": 0.0, "mb_a": 0.0}
    tot, tipo, kit, esiti = vuoto(), {}, {}, {}
    for x in ore:
        c = x.get("conti") or {}
        pm = c.get("per_metodo") or {}
        for d in (tot, tipo.setdefault(x.get("tipo", "?"), vuoto()), kit.setdefault(str(x.get("kit")), vuoto())):
            d["ore"] += 1
            d["valutabili"] += 1 if x.get("valutabile") else 0
            d["mb"] = round(d["mb"] + (c.get("mb") or 0), 3)
            d["chiamate"] += c.get("chiamate") or 0
            d["secondi"] = round(d["secondi"] + (c.get("secondi") or 0), 1)
            for m in ("b", "fitte", "a"):
                d["mb_" + m] = round(d["mb_" + m] + ((pm.get(m) or {}).get("mb") or 0), 3)
        e = str(x.get("esito") or "?").split(":")[0][:60]
        esiti[e] = esiti.get(e, 0) + 1
    return {"in_tutto": tot, "per_tipo": tipo, "per_kit": kit, "esiti": esiti}


def lavoro(cfg, lancia, scrivi_out, av=lambda t: None, adesso=time.time, gia=None):
    """Tutte le ore di pilota.json, una alla volta: lancia(ora, secondi_max) -> (codice, dict dell'ora o None). Una
    negativa non valutabile si sostituisce con la prima riserva; una positiva no. Un'ora morta con l'errore di memoria
    si rifa' una volta, in fondo. gia: {nome: dict} delle ore gia' finite (ripresa del compito): non si rifanno."""
    lim, tempi = limiti_da(cfg)
    t0 = adesso()
    q, riserve = coda(cfg.get("ore") or [], int(cfg.get("negative_quante", 20)))
    out = {"pilota": VERSIONE, "limiti": lim, "tempi_per_chiamata_s": tempi, "inizio": time.strftime("%Y-%m-%d %H:%M:%S"),
           "seme": cfg.get("seme"), "ore": []}
    rifatte = {}
    gia = gia or {}
    while q:
        ora = q.pop(0)
        if adesso() - t0 > lim["ore_in_tutto"] * 3600:
            out["fermato"] = f"passate {lim['ore_in_tutto']} ore: {len(q) + 1} ore non fatte"
            break
        if ora["nome"] in gia:
            x = dict(gia[ora["nome"]], ripreso="finita prima della ripresa del compito")
        else:
            av(f"pilota {ora['nome']} ({ora['tipo']}, kit {ora.get('kit')}): parte")
            try:
                codice, r = lancia(ora, lim["minuti_per_ora"] * 60)
            except Exception as ex:   # noqa: BLE001
                codice, r = f"non partito: {type(ex).__name__}: {str(ex)[:200]}", None
            x = dict(r) if r else {"nome": ora["nome"], "tipo": ora["tipo"], "kit": ora.get("kit")}
            x["processo"] = {"codice": codice, "esito": esito_processo(codice)}
            if codice != 0 and (r is None or r.get("in_corso") or not r.get("esito")):
                x["esito"] = esito_processo(codice) + (" (a meta')" if r else "")
                x["valutabile"] = bool(r and (r.get("b") or {}).get("candidati_tutti") is not None)   # (b) gia' calcolato
                x.pop("in_corso", None)
            if codice == MEMORIA and rifatte.get(ora["nome"], 0) < lim["ritenta_errore_memoria"]:
                rifatte[ora["nome"]] = rifatte.get(ora["nome"], 0) + 1
                q.append(ora)
                x["si_rifa"] = True
        prima = next((i for i, y in enumerate(out["ore"]) if y.get("nome") == ora["nome"]), None)
        if prima is not None:
            x["tentativo_prima"] = {k: out["ore"][prima].get(k) for k in ("esito", "processo", "conti")}
            out["ore"][prima] = x
        else:
            out["ore"].append(x)
        if ora["tipo"] == "negativa" and not x.get("valutabile") and not x.get("si_rifa") and riserve:
            r = riserve.pop(0)
            av(f"pilota {ora['nome']} non valutabile: al suo posto la riserva {r['nome']}")
            x["sostituita_da"] = r["nome"]
            q.append(r)
        out["conti"] = conti_di(out["ore"])
        scrivi_out(out)
    out["conti"] = conti_di(out["ore"])
    out["minuti"] = round((adesso() - t0) / 60, 1)
    out["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    scrivi_out(out)
    return out


# ------------------------------------------------------------------ la DLL vera e la decodifica (solo sul PC)

def mezzi_veri(cartella_sdk, collega_con, ffmpeg, ora, uscita, grezzi, cimitero, nofin=0):
    """I mezzi di lavora_ora sul PC: la DLL vera con le miniature (movimento.classe_registratore, che e'
    focus_nvr.Registratore con GetThumbImage), kit_rifiuti, la decodifica delle miniature (OpenCV, se no ffmpeg)."""
    import subprocess
    import cv2
    import kit_rifiuti as kr
    import dimezza as dz
    import movimento as mv
    classe = mv.classe_registratore()

    def decodifica(dati, formato, grezzo):
        """grezzo: il file che Lavoro.miniatura ha gia' scritto con questi dati."""
        cap = cv2.VideoCapture(grezzo)
        try:
            ok, f = cap.read()
        finally:
            cap.release()
        if ok and f is not None:
            return f
        png = grezzo + ".png"
        subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "hevc" if formato == "H.265" else "h264", "-i", grezzo,
                        "-frames:v", "1", png], capture_output=True, timeout=60, creationflags=nofin)
        f = cv2.imread(png) if os.path.exists(png) else None
        _togli(png)
        return f

    return {"nuovo": lambda: classe(cartella_sdk, log=lambda *_: None),
            "collega": lambda reg: collega_con(reg, ora["uid"], ora.get("kit")), "ffmpeg": ffmpeg, "kr": kr,
            "decodifica": decodifica, "fotogrammi": lambda mp4: kr.fotogrammi_ai_tempi(mp4, dz.TEMPI_FOTOGRAMMI),
            "uscita": uscita, "grezzi": grezzi, "cimitero": cimitero}
