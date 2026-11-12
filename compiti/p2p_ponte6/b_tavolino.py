"""Il metodo (b) della prova pilota rifatto a tavolino: dalle miniature di un minuto (704x576) salvate da pilota.py ai
candidati in ordine, senza registratore e senza PC (analisi-abbandono-in-un-ora.md).

Una funzione pura, `scansione(fot, ts, inizio, fine, riquadri, escludi, opz)`, con le stesse regole di pilota.py 0.1.0
quando `opz` e' quello di partenza (BASE) e, una alla volta, le varianti misurate sulle 30 ore della prova:
  - zona:      "maschera" (si guarda solo la zona dei cassonetti, come oggi) o "pesata" (si guarda tutta l'inquadratura
               e quello che cade fuori dalla zona vale `peso_fuori` volte);
  - punteggio: "dE_area" (oggi: deltaE x area, vince il pezzo grande) o "dE_radice" (deltaE x radice dell'area, con
               l'area tagliata a `area_tetto`: un sacco piccolo non perde contro un'ombra larga);
  - ombra:     scarta il pezzo se la tessitura (gradienti in grigi, normalizzati) e' la stessa di prima: e' la stessa
               superficie con un'altra luce (ombre, sole, fari), non una cosa nuova;
  - fermo:     scarta il pezzo se nei minuti del dopo cambia ancora (chi resta e' fermo: un sacco; chi si muove no);
  - memoria:   scarta il pezzo se com'e' adesso c'era gia' in uno dei `memoria` minuti prima (non solo nei 5 del
               riferimento): un'auto che riparte dopo una sosta lunga lascia vedere il fondo di prima, non una cosa
               nuova;
  - mosso_max: come fermo, con una soglia fissa in deltaE (la distanza mediana dei minuti del dopo dalla loro mediana);
  - solo_fino: tiene solo i pezzi che restano fino alla fine della scansione (l'ora piu' 5 minuti): chi abbandona un
               sacco non torna a prenderlo, un'auto in sosta e un'ombra se ne vanno;
  - fuori:     "dopo" = una seconda passata su tutta l'inquadratura, con le opzioni `fuori_opz` in piu', mette in coda i
               pezzi fuori dalla zona (abbandoni accanto a un cestino o a un cancello, non ai cassonetti disegnati);
  - durata:    scarta il pezzo se sparisce prima di `durata_min` minuti senza arrivare alla fine (auto in sosta);
  - base:      un pezzo piccolo vicino alla base dei cassonetti (dentro la zona allargata, nella meta' bassa) vale di
               piu' (`peso_base`).
Le funzioni di kit_rifiuti (lab_cie, energia_bordi, maschera_zone, pixel_pezzo, presente_pezzo) arrivano da fuori
(`kr`), come in pilota.py. Prove in prova_b_tavolino.py; la misura sulle 30 ore in misura_b_tavolino.py.
version: 0.1.0 (12/11/2026): prima versione.
"""
import datetime
import os

import numpy as np

VERSIONE = "0.1.0"

BASE = {"rif_n": 5, "resta_n": 5, "soglia": 14.0, "area_min": None, "area_max": 0.15, "via": 1.5, "massimi": 3,
        "zona": "maschera", "peso_fuori": 1.0, "punteggio": "dE_area", "area_tetto": None,
        "ombra": None, "fermo": None, "durata_min": None, "memoria": None, "mosso_max": None,
        "solo_fino": False, "fuori": None, "fuori_opz": None, "peso_base": 1.0, "salto": 2, "iou_stesso": 0.3}


def opzioni(**k):
    o = dict(BASE)
    for c, v in k.items():
        if c not in o:
            raise KeyError(f"opzione sconosciuta: {c}")
        o[c] = v
    return o


def area_min_per(largo):
    return max(30, int(round(150 * (float(largo) / 1280.0) ** 2)))


def iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0.0, min(ax2, bx2) - max(a[0], b[0])), max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def mediana(f):
    f = [x for x in f if x is not None]
    if not f:
        return None
    return f[0] if len(f) == 1 else np.median(np.stack(f), axis=0).astype(np.uint8)


def leggi_minuti(cartella, minuti, cv2):
    """Le miniature salvate (minuti/HHMMSS.jpg) nell'ordine di ora["minuti"] (chi passa la mezzanotte resta in ordine):
    (immagini o None, momenti datetime)."""
    ts, fot = [], []
    for m in minuti:
        t = datetime.datetime.strptime(m["ora_video"], "%Y-%m-%d %H:%M:%S")
        ts.append(t)
        p = os.path.join(cartella, f"{t:%H%M%S}.jpg")
        fot.append(cv2.imread(p) if os.path.exists(p) else None)
    return fot, ts


def _grad(g, cv2):
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    return np.concatenate([gx.ravel(), gy.ravel()])


def stessa_tessitura(a, b, cv2):
    """Correlazione (0-1) dei gradienti di due ritagli in grigi: vicino a 1 = la stessa superficie con un'altra luce."""
    ga, gb = _grad(a, cv2), _grad(b, cv2)
    ga, gb = ga - ga.mean(), gb - gb.mean()
    n = float(np.sqrt((ga ** 2).sum() * (gb ** 2).sum()))
    return float((ga * gb).sum() / n) if n > 1e-6 else 1.0


def vicino_base(box, riquadri, margine=0.03):
    """Il centro del pezzo e' dentro la zona allargata e nella sua meta' bassa (la base dei cassonetti, dove si lascia
    un sacco)."""
    cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
    for x, y, w, h in riquadri:
        if x - margine <= cx <= x + w + margine and y + h * 0.5 <= cy <= y + h + 2 * margine + box[3]:
            return True
    return False


def nella_zona(box, riquadri, margine=0.03):
    cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
    return any(x - margine <= cx <= x + w + margine and y - margine <= cy <= y + h + margine for x, y, w, h in riquadri)


def pezzi(kr, cv2, A, B, dopo, zm, o):
    """pezzi_zona di kit_rifiuti 0.94.0 con le varianti di `o`. Ritorna [{"box", "area", "dE", "via", "tess", "mosso"}]
    in ordine di deltaE x area (l'ordine finale lo fa il punteggio)."""
    H, W = zm.shape
    ys, xs = np.nonzero(zm)
    if not len(xs):
        return []
    bordo = 8
    y0, y1 = max(0, int(ys.min()) - bordo), min(H, int(ys.max()) + bordo + 1)
    x0, x1 = max(0, int(xs.min()) - bordo), min(W, int(xs.max()) + bordo + 1)
    taglia = lambda im: im[y0:y1, x0:x1]   # noqa: E731
    zc = taglia(zm)
    sel = zc > 0
    La, Lb = kr.lab_cie(cv2.GaussianBlur(taglia(A), (5, 5), 0)), kr.lab_cie(cv2.GaussianBlur(taglia(B), (5, 5), 0))
    rif = np.median(La[sel], axis=0)
    Lb = Lb - (np.median(Lb[sel], axis=0) - rif)
    dE = np.sqrt(((Lb - La) ** 2).sum(axis=2)) * zc
    m = (dE > o["soglia"]).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    amin = o["area_min"] or area_min_per(W)
    lista = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in st[i])
        if area < amin or area > o["area_max"] * H * W:
            continue
        pz = lb[y:y + h, x:x + w] == i
        de = float(dE[y:y + h, x:x + w][pz].mean())
        lista.append((de * area, de, i, x, y, w, h, area))
    lista.sort(key=lambda p: -p[0])
    if not lista:
        return []
    ga = cv2.cvtColor(taglia(A), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(taglia(B), cv2.COLOR_BGR2GRAY).astype(np.float32)
    dopo_lab = []
    for f in dopo:
        fl = kr.lab_cie(cv2.GaussianBlur(taglia(f), (5, 5), 0))
        dopo_lab.append(fl - (np.median(fl[sel], axis=0) - rif))
    out = []
    for punti, de, i, x, y, w, h, area in lista:
        pz = lb[y:y + h, x:x + w] == i
        rapporto = kr.energia_bordi(ga[y:y + h, x:x + w]) / max(kr.energia_bordi(gb[y:y + h, x:x + w]), 1e-6)
        if rapporto > o["via"]:
            continue
        d_dopo = [float(np.sqrt(((fl[y:y + h, x:x + w] - La[y:y + h, x:x + w]) ** 2).sum(axis=2))[pz].mean())
                  for fl in dopo_lab]
        if sum(v > o["soglia"] for v in d_dopo) < len(dopo_lab):
            continue
        tess = mosso = None
        if o["ombra"] is not None:
            p = 2   # un filo di bordo: la tessitura si misura anche sul contorno del pezzo
            ya, yb, xa, xb = max(0, y - p), min(ga.shape[0], y + h + p), max(0, x - p), min(ga.shape[1], x + w + p)
            tess = stessa_tessitura(ga[ya:yb, xa:xb], gb[ya:yb, xa:xb], cv2)
            if tess >= o["ombra"]:
                continue
        if o["fermo"] is not None or o["mosso_max"] is not None:
            Lbp = Lb[y:y + h, x:x + w]
            mosso = float(np.median([np.sqrt(((fl[y:y + h, x:x + w] - Lbp) ** 2).sum(axis=2))[pz].mean()
                                     for fl in dopo_lab]))
            if ((o["fermo"] is not None and mosso > o["fermo"] * de)
                    or (o["mosso_max"] is not None and mosso > o["mosso_max"])):
                continue
        out.append({"box": [(x0 + x) / W, (y0 + y) / H, w / W, h / H], "area": area, "dE": round(de, 2),
                    "via": round(rapporto, 3), "tess": tess, "mosso": mosso})
        if len(out) >= o["massimi"]:
            break
    return out


def punteggio(c, riquadri, o):
    a = c["area"] if not o["area_tetto"] else min(c["area"], o["area_tetto"])
    s = c["dE"] * (a if o["punteggio"] == "dE_area" else np.sqrt(a))
    if o["zona"] == "pesata" and not nella_zona(c["box"], riquadri):
        s *= o["peso_fuori"]
    if o["peso_base"] != 1.0 and vicino_base(c["box"], riquadri) and c["area"] <= 0.01 * 704 * 576:
        s *= o["peso_base"]
    return round(float(s), 1)


def unisci(ril, iou_min=0.3, salto=2):
    tracce = []
    for r in sorted(ril, key=lambda r: (r["i"], -r["punteggio"])):
        t = next((t for t in tracce
                  if 0 < r["i"] - t["ultimo_i"] <= salto and iou(t["ultimo_box"], r["box"]) >= iou_min), None)
        if t is None:
            tracce.append(dict(r, minuti_rilevato=1, ultimo_i=r["i"], ultimo_box=r["box"]))
        elif t["ultimo_i"] != r["i"]:
            t.update(minuti_rilevato=t["minuti_rilevato"] + 1, ultimo_i=r["i"], ultimo_box=r["box"],
                     punteggio=max(t["punteggio"], r["punteggio"]))
    for t in tracce:
        t.pop("ultimo_box")
    return sorted(tracce, key=lambda t: -t["punteggio"])


def durata(kr, fot, i, zm, box, rif_n, resta_n, buchi=1):
    A = mediana(fot[max(0, i - rif_n):i])
    B = mediana(fot[i:i + resta_n])
    pp = kr.pixel_pezzo(A, B, zm, box)
    ultimo, vuoti = i, 0
    for j in range(i, len(fot)):
        if fot[j] is None:
            continue
        if kr.presente_pezzo(fot[j], pp)[0]:
            ultimo, vuoti = j, 0
        else:
            vuoti += 1
            if vuoti > buchi:
                break
    return ultimo - i + 1, ultimo >= len(fot) - 1 - buchi


def _passata(kr, fot, ts, inizio, fine, zm, riquadri, o):
    """Una passata sui minuti con la maschera zm: i candidati dopo tutti i filtri, in ordine di punteggio."""
    rif_n, resta_n = o["rif_n"], o["resta_n"]
    ril = []
    for i in range(rif_n, len(fot) - resta_n + 1):
        if fot[i] is None:
            continue
        rif = [f for f in fot[i - rif_n:i] if f is not None and f.shape == fot[i].shape]
        dopo = [f for f in fot[i:i + resta_n] if f is not None and f.shape == fot[i].shape]
        if len(rif) < 2 or len(dopo) < resta_n - 1:
            continue
        A, B = mediana(rif), mediana(dopo)
        for c in pezzi(kr, _CV2[0], A, B, dopo, zm, o):
            pp = kr.pixel_pezzo(A, B, zm, c["box"])
            if any(kr.presente_pezzo(f, pp)[0] for f in rif):
                continue
            if o["memoria"] and any(kr.presente_pezzo(f, pp)[0] for f in fot[max(0, i - o["memoria"]):i - rif_n]
                                    if f is not None and f.shape == fot[i].shape):
                continue   # com'e' adesso era gia' stato nella mezz'ora prima: un'auto che riparte, un'ombra che torna
            c["i"] = i
            c["punteggio"] = punteggio(c, riquadri, o)
            ril.append(c)
    fine1 = fine + datetime.timedelta(seconds=60)
    cand = [c for c in unisci(ril, o["iou_stesso"], o["salto"]) if inizio <= ts[c["i"]] < fine1]
    out = []
    for c in cand:
        m, fino = durata(kr, fot, c["i"], zm, c["box"], rif_n, resta_n)
        if o["durata_min"] and m < o["durata_min"] and not fino:
            continue
        if o["solo_fino"] and not fino:
            continue   # se ne va prima della fine dell'ora (piu' 5 minuti): un'auto in sosta, un'ombra, chi aspetta
        c.update(comparsa=ts[c["i"]], comparsa_prima=ts[c["i"] - 1], durata_min=m, fino_alla_fine=fino,
                 box=[round(v, 4) for v in c["box"]])
        out.append(c)
    return out


_CV2 = [None]


def scansione(kr, cv2, fot, ts, inizio, fine, riquadri, escludi=(), o=None):
    """I candidati dell'ora in ordine: [{"i", "comparsa" (datetime), "comparsa_prima", "box", "area", "dE",
    "punteggio", "minuti_rilevato", "durata_min", "fino_alla_fine", "fuori"}]. fot/ts come leggi_minuti; un candidato
    conta se compare fra inizio e fine (piu' un minuto), come in pilota.py. Con o["fuori"] = "dopo" una seconda
    passata su tutta l'inquadratura aggiunge in coda (dopo quelli della zona) i pezzi fuori dalla zona."""
    o = o or BASE
    _CV2[0] = cv2
    buone = [f for f in fot if f is not None]
    if not buone:
        return []
    H, W = buone[0].shape[:2]
    tutto = kr.maschera_zone([[0, 0, 1, 1]], escludi, H, W, margine=0.0)
    zm = kr.maschera_zone(riquadri, escludi, H, W) if o["zona"] == "maschera" else tutto
    out = _passata(kr, fot, ts, inizio, fine, zm, riquadri, o)
    for c in out:
        c["fuori"] = not nella_zona(c["box"], riquadri)
    if o["fuori"] == "dopo" and o["zona"] == "maschera":
        altri = [c for c in _passata(kr, fot, ts, inizio, fine, tutto, riquadri, dict(o, **(o["fuori_opz"] or {})))
                 if not nella_zona(c["box"], riquadri)]
        for c in altri:
            c["fuori"] = True
        out += altri
    return out


def trovato(c, atteso, box_dario, iou_min=0.1, margine_s=90):
    """Il candidato e' l'abbandono noto: tocca il riquadro di Dario (IoU >= iou_min) e l'atteso cade fra il minuto
    prima della comparsa e la comparsa, con `margine_s` di tolleranza (chi abbandona copre il pezzo per un po')."""
    return (iou(c["box"], box_dario) >= iou_min
            and (c["comparsa_prima"] - datetime.timedelta(seconds=margine_s)) <= atteso
            <= c["comparsa"] + datetime.timedelta(seconds=margine_s))
