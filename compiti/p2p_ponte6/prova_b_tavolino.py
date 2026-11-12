"""Prove a tavolino di b_tavolino.py su una scena finta (niente rete, niente registratore): un sacco che compare, un
sacco fuori dalla zona, un'ombra che cambia la luce di un pezzo di strada senza cambiarne la tessitura, un'auto che
arriva, sta 15 minuti e riparte.
Uso: python3 prova_b_tavolino.py   (kit_rifiuti.py da KR_SCRIPTS, se no da ../../../kit-rifiuti-programma/scripts)
version: 0.1.0 (12/11/2026)
"""
import datetime
import os
import sys

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get("KR_SCRIPTS") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")
sys.path.insert(0, QUI)
sys.path.insert(0, SCRIPTS)
import cv2                   # noqa: E402
import kit_rifiuti as kr     # noqa: E402
import b_tavolino as bt      # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


D = datetime.datetime
INIZIO = D(2026, 11, 3, 13, 0, 0)
H, W = 576, 704
ZONA = [[0.5, 0.3, 0.4, 0.5]]
rnd = np.random.default_rng(7)
SFONDO = np.clip(rnd.normal(120, 25, (H // 4, W // 4, 3)), 0, 255).astype(np.uint8).repeat(4, 0).repeat(4, 1)
TEX = np.clip(rnd.normal(0, 30, (36, 36, 3)), -60, 60).astype(np.int16)


def scena(k, sacco=23, fuori=None, ombra=None, auto=None, liscia=None):
    """La miniatura del minuto k (da INIZIO - 6 minuti): un sacco scuro nella zona dal minuto `sacco`, uno fuori dalla
    zona dal minuto `fuori`, il sole (la strada piu' chiara, stessa tessitura) dal minuto `ombra`, un'auto
    chiara con i suoi bordi (minuto, durata) nella zona, un furgone liscio senza bordi (minuto, durata) nello stesso
    posto."""
    m = k - 6
    f = SFONDO.astype(np.float32)
    if ombra is not None and m >= ombra:
        f[380:440, 380:470] = f[380:440, 380:470] * 1.5 + 20
    f = f.astype(np.int16)
    if sacco is not None and m >= sacco:
        f[330:366, 460:496] = np.array([30, 35, 40], np.int16) + TEX
    if fuori is not None and m >= fuori:
        f[100:130, 60:90] = np.array([200, 60, 60], np.int16) + TEX[:30, :30]
    if auto and auto[0] <= m < auto[0] + auto[1]:
        f[200:300, 560:690] = np.array([210, 205, 200], np.int16) + np.tile(TEX, (3, 4, 1))[:100, :130]   # coi bordi
    if liscia and liscia[0] <= m < liscia[0] + liscia[1]:
        f[200:300, 560:690] = np.array([210, 205, 200], np.int16)
    f = f + rnd.integers(-3, 4, f.shape)
    return np.clip(f, 0, 255).astype(np.uint8)


def ora(**k):
    ts = [INIZIO + datetime.timedelta(minutes=j - 6) for j in range(72)]
    return [scena(j, **k) for j in range(72)], ts


def corre(fot, ts, **o):
    return bt.scansione(kr, cv2, fot, ts, INIZIO, INIZIO + datetime.timedelta(hours=1), ZONA, [], bt.opzioni(**o))


BOX_SACCO = [460 / W, 330 / H, 36 / W, 36 / H]
BOX_FUORI = [60 / W, 100 / H, 30 / W, 30 / H]
BOX_OMBRA = [380 / W, 380 / H, 90 / W, 60 / H]

# 1) come oggi: il sacco nella zona si trova al primo posto, al minuto giusto
fot, ts = ora()
c = corre(fot, ts)
ok(len(c) >= 1 and bt.iou(c[0]["box"], BOX_SACCO) > 0.5, "oggi: il sacco e' il primo candidato")
ok(c and c[0]["comparsa"] == INIZIO + datetime.timedelta(minutes=23), "oggi: compare al minuto 23")
ok(bt.trovato(c[0], INIZIO + datetime.timedelta(minutes=22, seconds=40), BOX_SACCO), "trovato: atteso nel minuto prima")
ok(not bt.trovato(c[0], INIZIO + datetime.timedelta(minutes=40), BOX_SACCO), "trovato: atteso 17 minuti dopo, no")

# 2) il sacco fuori dalla zona: con la maschera non c'e', con la zona pesata si'
fot, ts = ora(sacco=None, fuori=30)
ok(not any(bt.iou(x["box"], BOX_FUORI) > 0.3 for x in corre(fot, ts)), "maschera: il sacco fuori zona non si vede")
c = corre(fot, ts, zona="pesata", peso_fuori=0.5)
ok(any(bt.iou(x["box"], BOX_FUORI) > 0.3 for x in c), "pesata: il sacco fuori zona si vede")
fot, ts = ora(sacco=23, fuori=30)
c = corre(fot, ts, zona="pesata", peso_fuori=0.1)
ok(c and bt.iou(c[0]["box"], BOX_SACCO) > 0.5, "pesata: quello nella zona resta davanti")

# 3) il sole su un pezzo di strada: stessa tessitura, altra luce. Oggi diventa un candidato; col controllo della
#    tessitura no
fot, ts = ora(sacco=None, ombra=35)
ok(any(bt.iou(x["box"], BOX_OMBRA) > 0.3 for x in corre(fot, ts)), "oggi: il sole e' un falso allarme")
ok(not any(bt.iou(x["box"], BOX_OMBRA) > 0.3 for x in corre(fot, ts, ombra=0.6)), "ombra: il sole si scarta")
fot, ts = ora(sacco=23, ombra=35)
ok(any(bt.iou(x["box"], BOX_SACCO) > 0.5 for x in corre(fot, ts, ombra=0.6)), "ombra: il sacco resta")

# 4) l'auto che sta 15 minuti e riparte: con la durata minima di 20 minuti e la memoria di 30 si scarta, il sacco resta
fot, ts = ora(sacco=23, auto=(40, 15))
BOX_AUTO = [560 / W, 200 / H, 130 / W, 100 / H]


def al_minuto(c, m):
    t = INIZIO + datetime.timedelta(minutes=m)
    return [x for x in c if bt.iou(x["box"], BOX_AUTO) > 0.3 and x["comparsa"] == t]


arriva = lambda c: al_minuto(c, 40)    # noqa: E731
riparte = lambda c: al_minuto(c, 55)   # noqa: E731
ok(arriva(corre(fot, ts)), "oggi: l'auto che arriva e sta 15 minuti e' un candidato")
c = corre(fot, ts, durata_min=20)
ok(not arriva(c), "durata: l'auto che arriva e sta 15 minuti si scarta")
ok(any(bt.iou(x["box"], BOX_SACCO) > 0.5 for x in c), "durata: il sacco (fino alla fine) resta")
c = corre(fot, ts, solo_fino=True)
ok(not arriva(c) and c and bt.iou(c[0]["box"], BOX_SACCO) > 0.5,
   "solo_fino: l'auto che riparte si scarta, il sacco resta")
c = corre(fot, ts, mosso_max=4.0)
ok(any(bt.iou(x["box"], BOX_SACCO) > 0.5 and x["mosso"] < 4.0 for x in c), "mosso_max: il sacco fermo resta")
# il furgone liscio: quando arriva sembra «se n'e' andato qualcosa» (meno bordi), quando riparte torna il fondo con i
# suoi bordi e oggi diventa un candidato; con la memoria di 30 minuti il fondo era gia' cosi' prima, e si scarta
fot, ts = ora(sacco=23, liscia=(40, 15))
ok(riparte(corre(fot, ts)), "oggi: il fondo che torna quando il furgone riparte e' un candidato")
c = corre(fot, ts, memoria=30)
ok(not riparte(c), "memoria: il fondo che torna si scarta")
ok(any(bt.iou(x["box"], BOX_SACCO) > 0.5 for x in c), "memoria: il sacco resta")

# 5) la seconda passata fuori dalla zona: prima quelli della zona, poi quelli fuori, segnati
fot, ts = ora(sacco=23, fuori=30)
c = corre(fot, ts, fuori="dopo")
ok(c and bt.iou(c[0]["box"], BOX_SACCO) > 0.5 and not c[0]["fuori"], "fuori: il sacco nella zona resta primo")
ok(any(bt.iou(x["box"], BOX_FUORI) > 0.3 and x["fuori"] for x in c[1:]), "fuori: il sacco fuori zona arriva in coda")

# 6) funzioni piccole
ok(bt.vicino_base([0.6, 0.7, 0.02, 0.02], ZONA) and not bt.vicino_base([0.6, 0.32, 0.02, 0.02], ZONA),
   "vicino_base: la meta' bassa della zona si', la cima no")
g = SFONDO[:60, :60, 0].astype(np.float32)
ok(bt.stessa_tessitura(g, g * 0.5 + 10, cv2) > 0.95, "tessitura: la stessa superficie piu' scura e' la stessa")
ok(bt.stessa_tessitura(g, np.full_like(g, 30) + TEX[:30, :30, 0].repeat(2, 0).repeat(2, 1), cv2) < 0.3,
   "tessitura: un oggetto nuovo no")
try:
    bt.opzioni(nonesiste=1)
    ok(False, "opzioni: una chiave sconosciuta e' un errore")
except KeyError:
    ok(True, "opzioni: una chiave sconosciuta e' un errore")

print(f"\n{len(fallite)} prove fallite" if fallite else "\ntutte le prove passano")
sys.exit(1 if fallite else 0)
