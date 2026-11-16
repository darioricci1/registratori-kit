"""
Compito fuoco5 - RIPRISTINO del fuoco di UNA telecamera: KIT249 SP7 (Viano), cam 3 del sito, canale 2 del registratore
Focus (contando da 0). Per Alma Sicurezza.

VERSION 0.5.0 (16/11/2026) - nasce dal guasto di fuoco4 (compito 0.4.0, 16/11 9:31-9:37): la telecamera e' rimasta
  sfocata (nitidezza 23.384 -> 135, Laplaciano sulle foto 960x540). Autorizzazione di Dario del 15/11: «solo KIT249,
  solo zoom e fuoco, rimettere com'era». Questo compito fa UNA cosa sola: riporta il fuoco alla foto di partenza di
  fuoco4 (riferimento/partenza.npy e partenza.jpg, 16/11 alle 9:31).

Cosa ha insegnato fuoco4 (i 64 impulsi in uscita/fuoco.json di quella prova):
  - l'ottica NON e' simmetrica: un impulso «vicino» (E_PTZ_CTRL_FOCUS_IN, 10) puo' fare un salto enorme (37 ms:
    nitidezza da 20.000 a 780), un impulso «lontano» (FOCUS_OUT, 11) fa passi piccoli e regolari (75 ms: 1.540 ->
    7.576 -> 14.822 -> 21.282 -> 24.180). Contare gli impulsi non dice dov'e' la lente: 5 impulsi «vicino» mandati
    alla cieca per pareggiare il conto (rimetti) l'hanno portata in fondo alla sfocatura;
  - la guida «distanza dalla partenza» si satura: oltre una certa sfocatura vale sempre ~31 (1 - correlazione dei
    dettagli non supera 1) e non dice piu' da che parte andare. La nitidezza (varianza del Laplaciano) invece cresce
    in modo regolare da 18 fino al picco: e' quella che guida qui;
  - lo zoom non e' stato comandato (0 impulsi di zoom): il leggero ingrandimento (scala 1,02-1,04, stimata) va e torna
    con la sfocatura (la lente «respira» mettendo a fuoco) e a fuoco ritrovato era tornato 1,000 (foto 021 di fuoco4).

Come lavora:
  0. aspetta la luce (finestra 9:30-15:00 sull'ora del PC) e controlla che la foto del canale sia di giorno (se la sua
     foto non lo dice, basta la luce 45-215 e un altro canale dello stesso registratore a colori, come la 0.4.0);
  1. una foto: se non e' la stessa inquadratura della partenza (correlazione delle foto molto sfocate) si ferma senza
     mandare niente; se e' gia' a fuoco e combacia, non manda niente;
  2. messa a fuoco automatica: la libreria FocusNetSDK 1.0.0.3 NON ce l'ha (E_PTZ_CTRL: solo direzioni, zoom, fuoco,
     iride, giro, menu OSD, preset; nessun «one-key focus» ne' autofocus). Si scrive e si va avanti a impulsi;
  3. UN impulso alla volta, sempre seguito da una foto (mai due impulsi senza una foto in mezzo): si parte da
     «lontano» (11), il verso che in fuoco4 ha sempre recuperato. Dopo ogni passo nitidezza e corrispondenza con la
     partenza. Due passi di fila peggiori del migliore = si e' passato il picco: si inverte e si dimezza l'impulso;
     dieci passi senza cambiare niente = verso sbagliato o fine corsa: si inverte. Vicino al picco (oltre il 30%)
     impulsi corti;
  4. si ferma appena la nitidezza e' almeno il 70% di quella di partenza E l'inquadratura combacia (stessa scena,
     spostamento <= 4 px a 1280, scala entro l'1,5%). Se dopo piu' inversioni con l'impulso minimo si e' sul picco ma
     sotto il 70% (luce diversa da quella delle 9:31), si ferma al picco (almeno l'85% del massimo visto);
  5. sempre, anche dopo un errore: «lascia» su fuoco vicino e lontano (due volte). Niente comandi di zoom, mai.
Tetti: 150 impulsi, 45 minuti dal primo comando, 8 inversioni. Nessun'altra telecamera e nessun altro kit: gli altri
canali si leggono soltanto (una foto) e solo se serve il controllo della luce.

Uscita: uscita/ripristino.json (ogni passo: verso, ms, foto prima e dopo, nitidezza, rapporto con la partenza,
somiglianza, spostamento, scala), uscita/foto/NNN_*.jpg (la foto dopo il passo N e' la foto prima del passo N+1),
uscita/confronto_fine.jpg (partenza a sinistra, fine a destra), avanzamento.txt, stato.json.
Le credenziali: focus_accesso.txt nella cartella del compito (uid;utente;password, «*» e «*<200»).
"""
import ctypes
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

VERSION = "0.5.0"
C = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, C)
U = os.path.join(C, "uscita")

E_PTZ_CTRL_FOCUS_IN, E_PTZ_CTRL_FOCUS_OUT = 10, 11    # FNSCommons.h; lo zoom (8, 9) non si usa mai qui
COMANDO = {+1: E_PTZ_CTRL_FOCUS_IN, -1: E_PTZ_CTRL_FOCUS_OUT}
SOLO_FUOCO = (E_PTZ_CTRL_FOCUS_IN, E_PTZ_CTRL_FOCUS_OUT)
NOMI_PTZ = {
    "IsPTZ": "?IsPTZ@IFocusNetSDK@@UEAA_N_K0@Z",
    "PTZControl": "?PTZControl@IFocusNetSDK@@UEAA_N_K0Utag_ST_VM_PTZ_CTRL@@@Z",
}
DIFETTI = {
    "canale": 2,                 # da 0: CH3 = cam 3 del sito (come fuoco4)
    "verso_iniziale": -1,        # -1 = «lontano» (FOCUS_OUT): in fuoco4 ha sempre riavvicinato il fuoco
    "ms": 75,                    # impulso dei passi lontani dal picco
    "ms_vicino": 37,             # impulso quando la nitidezza ha passato «vicino» della partenza
    "ms_minimo": 20,
    "vicino": 0.30,
    "obiettivo": 0.70,           # nitidezza / nitidezza di partenza per dire «tornata»
    "picco_relativo": 0.85,      # sul picco ritrovato: almeno questa parte del massimo visto
    "picco_minimo": 0.45,        # ...e almeno questa parte della partenza
    "stessa_scena": 0.50,        # correlazione delle foto molto sfocate: sotto, non e' la stessa inquadratura
    "combacia_scena": 0.90,
    "spostamento_max": 4.0,      # pixel a 1280
    "scala_max": 0.015,
    "migliora": 0.03,            # vicino al picco: un passo migliora se la nitidezza supera la migliore di questo
    "peggiora": 0.08,            # ...e peggiora se scende sotto la migliore di questo
    "migliora_forma": 0.05,      # lontano dal picco: un passo migliora se la distanza di forma scende di questo
    "peggiora_forma": 0.10,      # ...e peggiora se sale di questo
    "scena_cambiata": 0.98,      # somiglianza grossolana con la foto di prima: sotto, e' passato qualcuno
    "peggiori_di_fila": 2,
    "fermi_max": 10,
    "inversioni_max": 8,
    "impulsi_max": 150,
    "minuti_max": 45,
    "assestamento": 3.0,         # secondi dopo un impulso prima della foto (in fuoco4 1,5: l'ottica poteva muoversi ancora)
    "velocita": 1,
    "finestra": [9.5, 15.0],
    "aspetta_giorno": True,
    "attesa_max_ore": 20,
}
FRESCO = 240                     # il relay si chiude dopo 5 minuti: dopo 4 si ricollega (come il ponte)
CIMITERO = []                    # i Registratori chiusi non si liberano (la libreria chiama dai suoi fili)


class Fermo(Exception):
    """Una ragione per non mandare altri comandi."""


class ST_VM_PTZ_CTRL(ctypes.Structure):
    _fields_ = [("ePtzCtrl", ctypes.c_int), ("bStart", ctypes.c_bool), ("ucSpeed", ctypes.c_ubyte),
                ("uiReserved", ctypes.c_uint * 4)]


# ------------------------------------------------------------------ misure delle foto (pure: numpy e cv2)

def maschera(h, w):
    import numpy as np
    m = np.ones((h, w), bool)
    m[: int(0.07 * h), :] = False                       # data e ora in alto
    m[int(0.86 * h):, : int(0.25 * w)] = False          # nome del canale in basso a sinistra
    return m


def piccola(bgr_o_grigio, w=640, h=360):
    import cv2
    import numpy as np
    g = bgr_o_grigio if bgr_o_grigio.ndim == 2 else cv2.cvtColor(bgr_o_grigio, cv2.COLOR_BGR2GRAY)
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)


def nitidezza(g):
    """Varianza del Laplaciano sulla foto grigia piccola (640x360), senza le scritte. Partenza di fuoco4: 5.499,
    fine: ~45, picco ritrovato a meta' prova: ~6.500. Cresce in modo regolare con il fuoco anche molto sfocato."""
    import cv2
    m = maschera(*g.shape)
    return float(cv2.Laplacian(g.astype("float32"), cv2.CV_32F)[m].var())


def somiglianza(a, b, sigma=6.0):
    """Correlazione delle due foto molto sfocate: dice se e' la stessa inquadratura anche quando una e' fuori fuoco
    (fuoco4: 0,95-0,99 sfocata, 0,76 con un'auto parcheggiata davanti; gli altri canali 0,04 e 0,16)."""
    import cv2
    import numpy as np
    m = maschera(*a.shape)
    x = cv2.GaussianBlur(a.astype(np.float32), (0, 0), sigma)[m]
    y = cv2.GaussianBlur(b.astype(np.float32), (0, 0), sigma)[m]
    x, y = x - x.mean(), y - y.mean()
    d = float((x * x).sum() * (y * y).sum()) ** 0.5
    return float((x * y).sum()) / d if d > 0 else 0.0


def spostamento(a, b):
    """Spostamento dell'inquadratura in pixel a 1280 (correlazione di fase sulla striscia senza scritte, foto un po'
    sfocate). Vale sulle foto a fuoco, dove si usa (per dire «combacia»); sulle foto molto sfocate non e' affidabile."""
    import cv2
    import numpy as np
    h, w = a.shape
    y0, y1 = int(0.08 * h), int(0.85 * h)
    aa = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 2.0)[y0:y1]
    bb = cv2.GaussianBlur(b.astype(np.float32), (0, 0), 2.0)[y0:y1]
    (dx, dy), _ = cv2.phaseCorrelate(aa, bb, cv2.createHanningWindow((w, y1 - y0), cv2.CV_32F))
    return float(np.hypot(dx, dy)) * 1280.0 / w


def riscala(g, sc):
    import cv2
    import numpy as np
    h, w = g.shape
    M = np.float32([[sc, 0, (1 - sc) * w / 2], [0, sc, (1 - sc) * h / 2]])
    return cv2.warpAffine(g.astype(np.float32), M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _ncc(a, b, m):
    x, y = a[m], b[m]
    x, y = x - x.mean(), y - y.mean()
    d = float((x * x).sum() * (y * y).sum()) ** 0.5
    return float((x * y).sum()) / d if d > 0 else 0.0


def scala_per_correlazione(a, b, lim=0.10):
    """Il fattore di scala di b rispetto ad a cercando la scala che rende b piu' simile ad a (da fuoco4)."""
    import cv2
    import numpy as np
    h, w = a.shape
    m = maschera(h, w)
    m[: int(0.15 * h), :] = m[int(0.85 * h):, :] = False
    m[:, : int(0.15 * w)] = m[:, int(0.85 * w):] = False
    aa = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 1.0)
    bb = cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.0)

    def punteggio(ll):
        return _ncc(aa, riscala(bb, float(np.exp(-ll))), m)
    grezzi = np.arange(-lim, lim + 1e-9, 0.01)
    l0 = float(grezzi[int(np.argmax([punteggio(x) for x in grezzi]))])
    fini = np.arange(l0 - 0.012, l0 + 0.012 + 1e-9, 0.001)
    pf = [punteggio(x) for x in fini]
    return float(np.exp(fini[int(np.argmax(pf))])), float(max(pf))


def stima_scala(a, b, minimo_punti=25):
    """Il fattore di scala di b rispetto ad a (>1: b ingrandita): punti ORB e similitudine RANSAC, o la correlazione a
    scale diverse se i punti sono pochi (da fuoco4)."""
    import cv2
    import numpy as np
    h, w = a.shape
    mm = maschera(h, w).astype(np.uint8) * 255
    orb = cv2.ORB_create(2000, fastThreshold=10)
    ka, da = orb.detectAndCompute(np.clip(a, 0, 255).astype(np.uint8), mm)
    kb, db = orb.detectAndCompute(np.clip(b, 0, 255).astype(np.uint8), mm)
    n = 0
    if da is not None and db is not None and len(ka) >= 8 and len(kb) >= 8:
        coppie = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
        buone = [p[0] for p in coppie if len(p) == 2 and p[0].distance < 0.8 * p[1].distance]
        if len(buone) >= 8:
            pa = np.float32([ka[x.queryIdx].pt for x in buone])
            pb = np.float32([kb[x.trainIdx].pt for x in buone])
            M, msk = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=2.0,
                                                 maxIters=3000, confidence=0.995)
            n = int(msk.sum()) if msk is not None else 0
            if M is not None and n >= minimo_punti:
                return {"scala": float(np.hypot(M[0, 0], M[1, 0])), "metodo": "punti", "punti": n}
    sc, q = scala_per_correlazione(a, b)
    return {"scala": sc, "metodo": "correlazione", "punti": n, "correlazione": round(q, 4)}


def allinea(ref, g, raggio=16):
    """g spostata per combaciare al meglio con ref (spostamento intero entro +-raggio pixel a 640, cercato su foto
    rimpicciolite e sfocate, quindi affidabile anche quando g e' fuori fuoco). Ritorna (g spostata, (dx, dy))."""
    import cv2
    import numpy as np

    def cerca(a, b, r, passo, centro=(0, 0)):
        m = maschera(*a.shape)
        meglio, dove = -2.0, centro
        for dy in range(centro[1] - r, centro[1] + r + 1, passo):
            for dx in range(centro[0] - r, centro[0] + r + 1, passo):
                bb = cv2.warpAffine(b, np.float32([[1, 0, -dx], [0, 1, -dy]]), b.shape[::-1],
                                    borderMode=cv2.BORDER_REFLECT)
                q = _ncc(a, bb, m)
                if q > meglio:
                    meglio, dove = q, (dx, dy)
        return dove
    a4 = cv2.GaussianBlur(cv2.resize(ref, (160, 90), interpolation=cv2.INTER_AREA), (0, 0), 1.5)
    b4 = cv2.GaussianBlur(cv2.resize(g, (160, 90), interpolation=cv2.INTER_AREA), (0, 0), 1.5)
    d4 = cerca(a4, b4, raggio // 4, 1)
    a2 = cv2.GaussianBlur(cv2.resize(ref, (320, 180), interpolation=cv2.INTER_AREA), (0, 0), 1.0)
    b2 = cv2.GaussianBlur(cv2.resize(g, (320, 180), interpolation=cv2.INTER_AREA), (0, 0), 1.0)
    d2 = cerca(a2, b2, 2, 1, (2 * d4[0], 2 * d4[1]))
    dx, dy = 2 * d2[0], 2 * d2[1]
    if not dx and not dy:
        return g, (0, 0)
    return cv2.warpAffine(g.astype(np.float32), np.float32([[1, 0, -dx], [0, 1, -dy]]), g.shape[::-1],
                          borderMode=cv2.BORDER_REFLECT), (dx, dy)


def forma(ref, g):
    """Somiglianza con la partenza a quattro scale (sfocature 1, 2, 4, 8), dopo aver tolto un eventuale spostamento:
    scende in modo regolare con la sfocatura anche dove la nitidezza e' ormai al fondo (fuoco4: 0,997 a fuoco, 0,95 a
    nitidezza 150, 0,84 a nitidezza 11). Lo spostamento lo giudica combacia(), non la guida."""
    g, _ = allinea(ref, g)
    return sum(somiglianza(ref, g, s) for s in (1.0, 2.0, 4.0, 8.0)) / 4


def misura(ref, g, nit_ref, con_scala=False):
    """Tutto quello che serve per decidere, di una foto rispetto alla partenza."""
    n = nitidezza(g)
    m = {"nit": round(n, 1), "rapporto": round(n / nit_ref, 4) if nit_ref else 0.0,
         "somiglianza": round(somiglianza(ref, g), 4), "forma": round(forma(ref, g), 5),
         "spostamento": round(spostamento(ref, g), 2)}
    if con_scala:
        s = stima_scala(ref, g)
        m["scala"] = round(s["scala"], 4)
        m["scala_metodo"] = s["metodo"]
    return m


def guida(m, cfg):
    """Il valore che dice se un passo ha migliorato: vicino al picco la nitidezza (piu' alta e' meglio), lontano la
    distanza di forma dalla partenza (piu' bassa e' meglio). In fuoco4 la nitidezza in fondo alla sfocatura cambiava
    di pochi punti (11-60) e confondeva il rumore col movimento; la «distanza dalla partenza» di fuoco4 invece si
    saturava a 31 e non diceva piu' niente."""
    if m["rapporto"] >= cfg["vicino"]:
        return ("nit", m["rapporto"])
    return ("forma", 1.0 - m["forma"])


def giudica(nuovo, migliore, cfg):
    """'meglio', 'peggio' o 'uguale' fra due valori di guida()."""
    if nuovo[0] != migliore[0]:
        return "meglio" if nuovo[0] == "nit" else "peggio"
    v, b = nuovo[1], migliore[1]
    if nuovo[0] == "nit":
        return "meglio" if v > b * (1 + cfg["migliora"]) else ("peggio" if v < b * (1 - cfg["peggiora"]) else "uguale")
    return ("meglio" if v < b * (1 - cfg["migliora_forma"]) else
            ("peggio" if v > b * (1 + cfg["peggiora_forma"]) else "uguale"))


def combacia(m, cfg):
    """L'inquadratura e' quella della partenza: stessa scena, non spostata, stessa scala (se misurata)."""
    return (m["somiglianza"] >= cfg["combacia_scena"] and m["spostamento"] <= cfg["spostamento_max"]
            and abs(m.get("scala", 1.0) - 1.0) <= cfg["scala_max"])


# ------------------------------------------------------------------ funzioni pure di contorno

def secondi_da_aspettare(ora, finestra):
    """ora: ore del giorno in decimali (9.5 = 9:30). 0 se si e' nella finestra, se no i secondi fino al suo inizio."""
    a, b = finestra
    if a <= ora < b:
        return 0
    return int(((a - ora) if ora < a else (24 - ora + a)) * 3600)


def e_giorno(bgr):
    """Fotogramma di giorno: a colori e ne' buio ne' bruciato (come nitidezza_telecamere)."""
    import cv2
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s, v = float(hsv[..., 1].mean()), float(hsv[..., 2].mean())
    return s > 18 and 45 < v < 215, s, v


def giorno_del_canale(scheda, altri):
    """Come la 0.4.0: e' giorno se lo dice la foto del canale, o se la sua luce e' da giorno (45-215) e almeno un
    altro canale dello stesso registratore, nello stesso momento, e' di giorno a colori."""
    if scheda.get("giorno"):
        return True
    luce = scheda.get("luce")
    return luce is not None and 45 < float(luce) < 215 and any(a.get("giorno") for a in altri)


# ------------------------------------------------------------------ il ripristino (puro: la telecamera e' passata)
#
# cam deve avere: scatta(nome) -> {"g": grigio 640x360, "file": nome della foto}, muovi(verso, ms) (UN impulso di
# fuoco: +1 vicino, -1 lontano), impulsi (quanti fatti). ora() -> secondi (monotono).

def ripristina(cam, ref, cfg, log=print, ora=time.monotonic, salva=lambda _: None):
    nit_ref = nitidezza(ref)
    es = {"nit_partenza": round(nit_ref, 1), "passi": [], "inversioni": [],
          "autofocus": "non c'e': FocusNetSDK 1.0.0.3 ha solo PTZControl (direzioni, zoom, fuoco vicino/lontano, iride, "
                       "giro, menu OSD) e i preset; nessun comando di messa a fuoco automatica. Si va a impulsi."}
    f = cam.scatta("inizio")
    m = misura(ref, f["g"], nit_ref, con_scala=True)
    es["inizio"] = dict(m, foto=f.get("file"))
    log(f"inizio: nitidezza {m['nit']} ({m['rapporto']:.1%} della partenza), somiglianza {m['somiglianza']}, "
        f"spostamento {m['spostamento']}, scala {m.get('scala')}")
    if m["somiglianza"] < cfg["stessa_scena"]:
        es["esito"] = (f"fermo senza comandi: la foto non e' l'inquadratura della partenza (somiglianza "
                       f"{m['somiglianza']})")
        return es
    if m["rapporto"] >= cfg["obiettivo"] and combacia(m, cfg):
        es["esito"] = "gia' tornata: nitidezza e inquadratura come la partenza, nessun comando"
        es["tornata"] = True
        es["fine"] = es["inizio"]
        return es
    verso, ms = int(cfg["verso_iniziale"]), int(cfg["ms"])
    migliore, massimo, peggiori, fermi = guida(m, cfg), m["rapporto"], 0, 0
    t0 = ora()
    try:
        while True:
            if cam.impulsi >= cfg["impulsi_max"]:
                raise Fermo(f"tetto di {cfg['impulsi_max']} impulsi")
            if ora() - t0 > cfg["minuti_max"] * 60:
                raise Fermo(f"passati {cfg['minuti_max']} minuti dal primo comando")
            if m["rapporto"] >= cfg["vicino"] and ms > cfg["ms_vicino"]:
                ms = int(cfg["ms_vicino"])
            prima = f
            cam.muovi(verso, ms)
            f = cam.scatta(f"passo{len(es['passi']) + 1:03d}_{'vicino' if verso > 0 else 'lontano'}{ms}")
            m = misura(ref, f["g"], nit_ref, con_scala=nit_ref > 0 and nitidezza(f["g"]) >= 0.5 * cfg["obiettivo"] * nit_ref)
            cambiata = somiglianza(prima["g"], f["g"], 8.0) < cfg["scena_cambiata"]
            p = dict(m, n=len(es["passi"]) + 1, verso=verso, ms=ms, foto_prima=prima.get("file"),
                     foto_dopo=f.get("file"), minuti=round((ora() - t0) / 60, 2))
            es["passi"].append(p)
            log(f"passo {p['n']}: {'vicino' if verso > 0 else 'lontano'} {ms} ms -> nitidezza {m['nit']} "
                f"({m['rapporto']:.1%}), somiglianza {m['somiglianza']}, spostamento {m['spostamento']}"
                + (f", scala {m['scala']}" if "scala" in m else ""))
            salva(es)
            if m["somiglianza"] < cfg["stessa_scena"]:
                raise Fermo(f"l'inquadratura non e' piu' quella della partenza (somiglianza {m['somiglianza']})")
            r = m["rapporto"]
            if r >= cfg["obiettivo"] and combacia(m, cfg):
                es["tornata"] = True
                es["esito"] = f"tornata: nitidezza al {r:.0%} della partenza e inquadratura che combacia"
                break
            if r >= cfg["obiettivo"] and "scala" in m and not combacia(m, cfg):
                raise Fermo(f"a fuoco ({r:.0%}) ma l'inquadratura non combacia (spostamento {m['spostamento']}, "
                            f"scala {m['scala']}): il fuoco non la cambia, si guarda a mano")
            massimo = max(massimo, r)
            if (len(es["inversioni"]) >= 2 and ms <= cfg["ms_minimo"] and r >= cfg["picco_minimo"]
                    and r >= cfg["picco_relativo"] * massimo and combacia(m, cfg)):
                es["tornata"] = True
                es["esito"] = (f"tornata sul picco ritrovato: nitidezza al {r:.0%} della partenza (il massimo visto e' "
                               f"il {massimo:.0%}: luce diversa da quella delle 9:31) e inquadratura che combacia")
                break
            v = guida(m, cfg)
            if cambiata:                                    # un'auto o una persona: non e' il fuoco, si riparte da qui
                p["scena_cambiata"] = True
                log("la scena e' cambiata fra le due foto (passa qualcuno): il confronto riparte da questa foto")
                migliore, peggiori, fermi = v, 0, 0
                continue
            giudizio = giudica(v, migliore, cfg)
            p["giudizio"] = giudizio
            if giudizio == "meglio":
                migliore, peggiori, fermi = v, 0, 0
            elif giudizio == "peggio":
                peggiori += 1
            else:
                fermi += 1
            motivo = None
            if peggiori >= cfg["peggiori_di_fila"]:
                motivo = f"{peggiori} passi peggiori del migliore ({migliore[0]} {migliore[1]:.4f}): passato il picco"
                ms = max(int(cfg["ms_minimo"]), ms // 2)
            elif fermi >= cfg["fermi_max"]:
                motivo = f"{fermi} passi senza cambiare: verso sbagliato o fine corsa"
            if motivo:
                verso = -verso
                es["inversioni"].append({"dopo_passo": p["n"], "motivo": motivo, "nuovo_verso": verso, "ms": ms})
                log(f"inverto: {motivo}; ora {'vicino' if verso > 0 else 'lontano'} a {ms} ms")
                if len(es["inversioni"]) > cfg["inversioni_max"]:
                    raise Fermo(f"piu' di {cfg['inversioni_max']} inversioni senza tornare")
                migliore, peggiori, fermi = v, 0, 0
    except Fermo as e:
        es["fermo"] = str(e)
        es["esito"] = "NON TORNATA: " + str(e)
        log("fermo: " + str(e))
    es["fine"] = dict(m, foto=f.get("file"))
    es["massimo"] = round(massimo, 4)
    return es


# ------------------------------------------------------------------ il registratore

def av(t):
    os.makedirs(U, exist_ok=True)
    with open(os.path.join(U, "avanzamento.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + t + "\n")
    print(t, flush=True)


def credenziali(uid, kit=None):
    tutte, generiche, vecchie = {}, [], []
    for d in (C, os.path.dirname(sys.executable), os.path.expanduser("~")):
        f = os.path.join(d, "focus_accesso.txt")
        if not os.path.exists(f):
            continue
        for riga in open(f, encoding="utf-8", errors="replace"):
            p = [x.strip() for x in riga.strip().split(";")]
            if len(p) >= 3 and p[0]:
                if p[0] == "*":
                    generiche.append((p[1], p[2]))
                elif p[0] == "*<200":
                    vecchie.append((p[1], p[2]))
                else:
                    tutte.setdefault(p[0].upper(), (p[1], p[2]))
    ordine = (vecchie + generiche) if (kit is not None and kit < 200) else (generiche + vecchie)
    return ([tutte[uid.upper()]] if uid.upper() in tutte else []) + ordine


def ffmpeg():
    return shutil.which("ffmpeg") or os.path.join(getattr(sys, "_MEIPASS", ""), "ffmpeg.exe")


class Comandi:
    """Premi e lascia del SOLO fuoco. ptz(h, comando, inizio, velocita) -> bool. Il «lascia» parte SEMPRE, anche se il
    «premi» o l'attesa si rompono, e si ripete una volta se non e' confermato."""

    def __init__(self, ptz, dormi=time.sleep):
        self.ptz, self.dormi = ptz, dormi
        self.durata = None

    def _lascia(self, h, comando, velocita):
        for _ in range(2):
            try:
                if self.ptz(h, comando, False, velocita):
                    return True
            except Exception:   # noqa: BLE001
                pass
        return False

    def impulso(self, h, verso, ms, velocita=1):
        comando = COMANDO[1 if verso > 0 else -1]
        ok = False
        t0 = time.perf_counter()
        try:
            ok = bool(self.ptz(h, comando, True, velocita))
            self.dormi(ms / 1000)
        finally:
            fermo = self._lascia(h, comando, velocita)
            self.durata = time.perf_counter() - t0
        return ok, fermo

    def ferma_tutto(self, h):
        esiti = []
        for _ in range(2):
            for cmd in SOLO_FUOCO:
                try:
                    esiti.append(bool(self.ptz(h, cmd, False, 1)))
                except Exception:   # noqa: BLE001
                    esiti.append(False)
        return esiti


class Fuoco:
    """Il Registratore di focus_nvr piu' IsPTZ, PTZControl e le istantanee dal vivo (da fuoco4)."""

    def __init__(self, reg, fn):
        self.reg, self.fn = reg, fn
        lib = ctypes.CDLL(os.path.join(fn.cartella_sdk(os.path.join(C, "FocusNetSDK")), "FocusNetSDK.dll"))
        P, H = ctypes.c_void_p, fn.c_handle
        self.is_ptz = getattr(lib, NOMI_PTZ["IsPTZ"])
        self.is_ptz.restype, self.is_ptz.argtypes = ctypes.c_uint8, [P, H, H]
        self.ptz = getattr(lib, NOMI_PTZ["PTZControl"])
        self.ptz.restype, self.ptz.argtypes = ctypes.c_uint8, [P, H, H, ctypes.POINTER(ST_VM_PTZ_CTRL)]
        self.buf, self.registra, self.lucchetto = None, threading.Event(), threading.Lock()
        self.comandi = Comandi(self._ptz)

    def comandabile(self, h):
        return bool(self.is_ptz(self.reg.this, self.reg.server, h))

    def _ptz(self, h, comando, inizio, velocita):
        if comando not in SOLO_FUOCO:
            raise Fermo("comando diverso dal fuoco: vietato in questo compito")
        c = ST_VM_PTZ_CTRL()
        c.ePtzCtrl, c.bStart, c.ucSpeed = comando, inizio, velocita
        return bool(self.ptz(self.reg.this, self.reg.server, h, ctypes.byref(c)))

    def apri_vivo(self, h):
        fn = self.fn

        def ricevi(hc, v):
            if hc != h or not self.registra.is_set():
                return
            with self.lucchetto:
                if self.buf is None:
                    if v.eFrameType != fn.E_FRAME_I:
                        return
                    self.buf = {"dati": [], "codec": "hevc" if v.eVideoFormat == fn.E_VIDEO_H265 else "h264"}
                d = ctypes.string_at(v.pData, v.uiDataSize) if v.pData and v.uiDataSize else b""
                if not self.buf["dati"] and not fn.ha_codice_inizio(d):
                    self.buf["dati"].append(b"\x00\x00\x00\x01")
                self.buf["dati"].append(d)

        a = fn.ST_VM_CHANNEL_OPEN()
        a.ePlayMode, a.eStreamType, a.bForward = fn.E_PLAY_LIVE, fn.E_STREAM_MAIN, True
        a.tRequestTime = fn.tempo_vm(datetime.datetime.now())
        self.reg.ricevi = ricevi
        if not self.reg.f["Open"](self.reg.this, self.reg.server, h, ctypes.byref(a)):
            raise RuntimeError("Open dal vivo rifiutato")
        self.reg.canali_aperti.add(h)

    def chiudi_vivo(self, h):
        self.reg.ricevi = None
        try:
            self.reg.f["Close"](self.reg.this, self.reg.server, h)
        finally:
            self.reg.canali_aperti.discard(h)

    def istantanea(self, secondi=3.0, attesa=15):
        """Gli ultimi fotogrammi di qualche secondo di flusso dal vivo (BGR), dal primo fotogramma chiave."""
        import cv2
        with self.lucchetto:
            self.buf = None
        self.registra.set()
        t0 = time.time()
        while time.time() - t0 < attesa:
            time.sleep(0.2)
            with self.lucchetto:
                if self.buf and time.time() - t0 > secondi and len(self.buf["dati"]) > 10:
                    break
        self.registra.clear()
        with self.lucchetto:
            b = self.buf
        if not b:
            return []
        d = tempfile.mkdtemp(dir=U)
        try:
            g = os.path.join(d, "v.grezzo")
            open(g, "wb").write(b"".join(b["dati"]))
            subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", b["codec"], "-i", g, "-vf", "fps=2",
                            os.path.join(d, "f%03d.png")], capture_output=True, timeout=120,
                           creationflags=0x08000000 if os.name == "nt" else 0)
            fot = sorted(f for f in os.listdir(d) if f.endswith(".png"))
            return [cv2.imread(os.path.join(d, f)) for f in fot[-3:]]
        finally:
            shutil.rmtree(d, ignore_errors=True)


def grigio_mediano(fot):
    """La mediana pixel per pixel dei fotogrammi, grigia, 640x360: come partenza.npy di fuoco4."""
    import numpy as np
    pp = [piccola(f) for f in fot if f is not None]
    return np.median(np.stack(pp), axis=0).astype(np.float32) if pp else None


class Telecamera:
    """La telecamera vera per ripristina(): collegamento (ricollegato quando serve, mai fra premi e lascia), foto dal
    vivo del canale scelto, impulsi del solo fuoco contati e registrati."""

    def __init__(self, fn, cfg, uid, kit_n, log=av):
        self.fn, self.cfg, self.uid, self.kit_n, self.log = fn, cfg, uid, kit_n, log
        self.reg, self.F, self.h, self.canale, self.per = None, None, None, None, {}
        self.t, self.relay, self.collegamenti = 0.0, True, []
        self.impulsi, self.k, self.comandi = 0, 0, []
        os.makedirs(os.path.join(U, "foto"), exist_ok=True)

    def collega(self):
        self.chiudi()
        t0 = time.time()
        reg = self.fn.Registratore(os.path.join(C, "FocusNetSDK"), log=lambda *_: None)
        CIMITERO.append(reg)
        ok, testo = False, "sul PC manca focus_accesso.txt con utente e password"
        for ut, pw in credenziali(self.uid, self.kit_n):
            ok, testo = reg.collega(self.uid, ut, pw, 9010, True, attesa=40)
            if ok or ("password" not in testo and "sconosciuto" not in testo):
                break
        self.collegamenti.append({"ora": time.strftime("%H:%M:%S"), "testo": testo, "secondi": round(time.time() - t0, 1)})
        if not ok:
            raise Fermo("collegamento: " + testo)
        self.reg, self.t = reg, time.time()
        self.relay = not ("diretto" in testo or "rete locale" in testo)
        self.F = Fuoco(reg, self.fn)
        self.per = {n: (hh, titolo) for n, hh, titolo in reg.canali()}
        if self.canale is not None:
            self.scegli(self.canale)
        return testo

    def fresco(self):
        if (self.reg is None or self.reg.stato.get("collegato") is False
                or (self.relay and time.time() - self.t > FRESCO)):
            self.log("ricollego (relay o collegamento caduto)")
            self.collega()

    def scegli(self, canale):
        self.canale = canale
        if canale not in self.per:
            raise Fermo(f"il canale {canale} non c'e'")
        self.h = self.per[canale][0]
        self.F.apri_vivo(self.h)
        time.sleep(2)

    def chiudi(self):
        if self.reg is not None:
            try:
                self.reg.chiudi()
            except Exception:   # noqa: BLE001
                pass
        self.reg, self.F, self.h = None, None, None

    def scatta(self, nome):
        import cv2
        self.fresco()
        fot = self.F.istantanea() or self.F.istantanea()
        if not fot or all(f is None for f in fot):
            raise Fermo("dal vivo non arrivano fotogrammi")
        self.k += 1
        f = f"{self.k:03d}_{nome}.jpg"
        cv2.imwrite(os.path.join(U, "foto", f), cv2.resize(fot[-1], (960, 540)), [cv2.IMWRITE_JPEG_QUALITY, 85])
        return {"g": grigio_mediano(fot), "bgr": fot[-1], "file": f}

    def muovi(self, verso, ms):
        if self.impulsi >= int(self.cfg["impulsi_max"]):
            raise Fermo("tetto di impulsi raggiunto")
        self.fresco()
        ok, fermo = self.F.comandi.impulso(self.h, verso, ms, int(self.cfg["velocita"]))
        self.impulsi += 1
        self.comandi.append({"verso": verso, "comando": COMANDO[verso], "ms": ms, "premuto": ok, "lasciato": fermo,
                             "durata_ms": round(1000 * (self.F.comandi.durata or 0)), "foto_prima": self.k,
                             "ora": time.strftime("%H:%M:%S")})
        if not fermo:
            self.F.comandi.ferma_tutto(self.h)
            raise Fermo("il «lascia» non e' stato confermato dal registratore: niente altri impulsi")
        if not ok:
            raise Fermo("il registratore ha rifiutato il comando del fuoco")
        time.sleep(float(self.cfg["assestamento"]))

    def ferma(self):
        if self.F is not None and self.h is not None:
            return self.F.comandi.ferma_tutto(self.h)
        return None

    def scheda_luce(self, numero, bgr):
        g, s, v = e_giorno(bgr)
        return {"numero": numero, "giorno": bool(g), "saturazione": round(s, 1), "luce": round(v, 1)}

    def luce_altri(self):
        """Solo lettura: una foto degli altri canali per il controllo della luce (0.4.0). Poi si riapre il canale."""
        out, prima = [], self.canale
        self.F.chiudi_vivo(self.h)
        self.canale = None
        try:
            for n in sorted(self.per):
                if n == prima:
                    continue
                self.fresco()
                hh = self.per[n][0]
                try:
                    self.F.apri_vivo(hh)
                    try:
                        time.sleep(1.5)
                        fot = [f for f in self.F.istantanea(secondi=3, attesa=10) if f is not None]
                    finally:
                        self.F.chiudi_vivo(hh)
                    if fot:
                        out.append(self.scheda_luce(n, fot[-1]))
                except Exception as e:   # noqa: BLE001
                    out.append({"numero": n, "errore": f"{type(e).__name__}: {e}"})
        finally:
            self.scegli(prima)
        return out


def alza_priorita():
    if os.name != "nt":
        return "non Windows"
    try:
        k = ctypes.windll.kernel32
        return "sopra il normale" if k.SetPriorityClass(k.GetCurrentProcess(), 0x8000) else "non cambiata"
    except Exception as e:   # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def carica_cfg():
    cfg = dict(DIFETTI)
    for nome in ("remoto.json", "fuoco.json"):
        f = os.path.join(C, nome)
        if os.path.exists(f):
            cfg.update(json.load(open(f, encoding="utf-8")))
    return cfg


def confronto_fine(ref_bgr, fine_bgr, file):
    import cv2
    import numpy as np
    a = cv2.resize(ref_bgr, (960, 540))
    b = cv2.resize(fine_bgr, (960, 540))
    cv2.putText(a, "partenza 16/11 9:31", (20, 520), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.putText(b, "fine ripristino " + time.strftime("%d/%m %H:%M"), (20, 520), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 255, 255), 2)
    cv2.imwrite(file, np.hstack([a, b]), [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    import cv2
    import numpy as np
    import focus_nvr as fn
    os.makedirs(U, exist_ok=True)
    try:
        import faulthandler
        faulthandler.enable(open(os.path.join(U, "guasto_memoria.txt"), "a", encoding="utf-8"), all_threads=True)
    except Exception:   # noqa: BLE001
        pass
    cfg = carica_cfg()
    f_es, f_stato = os.path.join(U, "ripristino.json"), os.path.join(U, "stato.json")
    stato = json.load(open(f_stato, encoding="utf-8")) if os.path.exists(f_stato) else {}
    if stato.get("fase") == "finito":
        av("compito gia' finito: non rifaccio niente")
        return
    # un compito interrotto (PC spento) riparte da capo: e' guidato dalle foto, non dal conto degli impulsi
    es = {"versione": VERSION, "kit": cfg.get("kit"), "inizio": time.strftime("%Y-%m-%d %H:%M:%S"),
          "parametri": {k: cfg[k] for k in DIFETTI}, "priorita": alza_priorita(),
          "ripartenza": bool(stato)}

    def salva(parziale=None):
        if parziale is not None:
            es["ripristino"] = parziale
        json.dump(es, open(f_es, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

    def segna(fase):
        stato.update(fase=fase, ora=time.strftime("%Y-%m-%d %H:%M:%S"))
        json.dump(stato, open(f_stato, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    ref = np.load(os.path.join(C, "riferimento", "partenza.npy")).astype(np.float32)
    ref_bgr = cv2.imread(os.path.join(C, "riferimento", "partenza.jpg"))
    if cfg.get("aspetta_giorno", True):
        t0 = time.time()
        while True:
            lt = time.localtime()
            sec = secondi_da_aspettare(lt.tm_hour + lt.tm_min / 60, cfg["finestra"])
            if not sec:
                break
            if time.time() - t0 + sec > float(cfg["attesa_max_ore"]) * 3600:
                es["esito"] = "fuori dalla finestra di luce e troppo da aspettare: niente"
                salva()
                return
            av(f"aspetto la luce: mancano {sec // 60} minuti alle {cfg['finestra'][0]}")
            time.sleep(min(sec, 600))
    segna("ripristino")
    kit_n = int(cfg["kit_numero"]) if cfg.get("kit_numero") else None
    cam = Telecamera(fn, cfg, cfg["uid"], kit_n)
    fine_bgr = None
    try:
        es["collegamento"] = cam.collega()
        av("collegamento: " + es["collegamento"])
        es["registratore"] = cam.reg.info()
        canale = int(cfg["canale"])
        if canale not in cam.per:
            raise Fermo(f"il canale {canale} non c'e'")
        if not cam.F.comandabile(cam.per[canale][0]):
            raise Fermo("il registratore dice che il canale non e' comandabile (IsPTZ falso)")
        cam.scegli(canale)
        prova = cam.F.istantanea() or cam.F.istantanea()
        prova = [x for x in prova if x is not None]
        if not prova:
            raise Fermo("dal vivo non arrivano fotogrammi")
        scheda = cam.scheda_luce(canale, prova[-1])
        es["luce"] = {"canale": scheda}
        if not scheda["giorno"]:
            es["luce"]["altri"] = cam.luce_altri()
        av(f"luce: {es['luce']}")
        if not giorno_del_canale(scheda, es["luce"].get("altri", [])):
            raise Fermo("la foto del canale non e' di giorno (infrarosso o buio): niente comandi")
        salva()
        es["ripristino"] = ripristina(cam, ref, cfg, av, salva=salva)
        es["esito"] = es["ripristino"].get("esito")
    except Fermo as e:
        es["esito"] = "fermo: " + str(e)
        av(es["esito"])
    except Exception as e:   # noqa: BLE001
        es["errore"] = f"{type(e).__name__}: {e}"
        av(es["errore"])
    finally:
        try:
            es["lascia_finale"] = cam.ferma()
        except Exception as e:   # noqa: BLE001
            es["lascia_finale"] = f"{type(e).__name__}: {e}"
        try:
            if cam.reg is not None and cam.h is not None:
                time.sleep(2)
                fot = [x for x in (cam.F.istantanea() or []) if x is not None]
                if fot:
                    fine_bgr = fot[-1]
                    g = grigio_mediano(fot)
                    es["foto_finale"] = misura(ref, g, nitidezza(ref), con_scala=True)
                    cv2.imwrite(os.path.join(U, "fine.jpg"), cv2.resize(fine_bgr, (1280, 720)),
                                [cv2.IMWRITE_JPEG_QUALITY, 90])
                    if ref_bgr is not None:
                        confronto_fine(ref_bgr, fine_bgr, os.path.join(U, "confronto_fine.jpg"))
        except Exception as e:   # noqa: BLE001
            es["foto_finale"] = f"{type(e).__name__}: {e}"
        es["comandi"] = {"impulsi": cam.impulsi, "zoom": 0, "elenco": cam.comandi}
        es["collegamenti"] = cam.collegamenti
        es["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
        salva()
        segna("finito")
        av(f"fine: {es.get('esito') or es.get('errore')} | impulsi {cam.impulsi} | foto finale {es.get('foto_finale')}")
        cam.chiudi()


if __name__ == "__main__":
    main()
