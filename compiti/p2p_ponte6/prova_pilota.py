"""Prove a tavolino di pilota.py, pilota_lavoro.py e prepara_pilota.py: libreria finta (un registratore che risponde con
miniature di una scena finta: un sacco che compare a un minuto dato, un'auto che passa, la luce che cambia), niente
rete, niente DLL. In fondo un'ora intera in un processo a parte, come sul PC (compito.py del ponte, pilota_lavoro.py,
un focus_nvr finto che fa miniature H.264 vere con ffmpeg), e un processo che cade con un errore di memoria.
Uso: python3 prova_pilota.py   (kit_rifiuti.py da KR_SCRIPTS, se no da ../../../kit-rifiuti-programma/scripts)
version: 0.1.0 (12/11/2026)
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get("KR_SCRIPTS") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")
sys.path.insert(0, QUI)
sys.path.insert(0, SCRIPTS)
import kit_rifiuti as kr     # noqa: E402
import pilota as pl          # noqa: E402
import prepara_pilota as pp  # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


D = datetime.datetime
INIZIO = D(2026, 11, 3, 13, 0, 0)
SACCO = INIZIO + datetime.timedelta(minutes=23, seconds=17)
H, W = 576, 704
ZONA = {"riquadri": [[0.5, 0.3, 0.4, 0.5]], "escludi": []}
BOX_SACCO = [460 / W, 330 / H, 36 / W, 36 / H]
rnd = np.random.default_rng(5)
SFONDO = np.clip(rnd.normal(120, 25, (H // 8, W // 8, 3)), 0, 255).astype(np.uint8).repeat(8, 0).repeat(8, 1)
TEX = np.clip(rnd.normal(0, 30, (36, 36, 3)), -60, 60).astype(np.int16)


def scena(t, sacco=SACCO, auto=(INIZIO + datetime.timedelta(minutes=40), 2), luce=40.0, largo=W):
    """La miniatura all'ora t: sfondo, luce che cresce di `luce` in un'ora, un sacco scuro da `sacco`, un'auto chiara
    nella zona per `auto[1]` minuti da auto[0] (passa: non resta 5 minuti)."""
    s = (t - INIZIO).total_seconds()
    f = SFONDO.astype(np.int16) + int(round(luce * s / 3600.0))
    if sacco is not None and t >= sacco:
        f[330:366, 460:496] = np.array([30, 35, 40], np.int16) + TEX
    if auto and auto[0] <= t < auto[0] + datetime.timedelta(minutes=auto[1]):
        f[200:300, 380:560] = np.array([210, 205, 200], np.int16)
    f = f + rnd.integers(-3, 4, f.shape)
    f = np.clip(f, 0, 255).astype(np.uint8)
    if largo != W:
        import cv2
        f = cv2.resize(f, (largo, int(round(H * largo / W))), interpolation=cv2.INTER_AREA)
    return f


def sec(x):
    return datetime.timedelta(seconds=x)


# ------------------------------------------------------------------ funzioni pure
ts = pl.tempi_scansione(INIZIO)
ok(len(ts) == 72 and ts[0] == INIZIO - sec(360) and ts[-1] == INIZIO + sec(3900), "72 miniature: da 6 min prima a 5 dopo")
tf = pl.tempi_fitti(SACCO)
ok(len(tf) == 121 and tf[0] == SACCO - sec(180) and tf[-1] == SACCO + sec(60), "miniature fitte: 121, da 3 min prima a 1 dopo")
ok(abs(pl.iou([0, 0, 1, 1], [0, 0, 1, 1]) - 1) < 1e-9 and pl.iou([0, 0, .1, .1], [.5, .5, .1, .1]) == 0, "IoU")
ok(pl.area_min_per(1280) == 150 and pl.area_min_per(704) == 45, "area minima riportata alla miniatura")
ok(pl.coperto(None, INIZIO, INIZIO)[0] and not pl.coperto((INIZIO, INIZIO + sec(10)), INIZIO - sec(1), INIZIO)[0],
   "coperto: non detto si prova, tratto sovrascritto no")
ok(pl.coperto((INIZIO - sec(99), INIZIO + sec(10)), INIZIO, INIZIO + sec(60))[1].startswith("non ancora"), "coperto: non ancora")
lim, tempi = pl.limiti_da({"limiti": {"minuti_per_ora": 5, "ore_in_tutto": 99}, "tempi": {"miniatura": 3, "collega": 999}})
ok(lim["minuti_per_ora"] == 5 and lim["ore_in_tutto"] == pl.LIMITI["ore_in_tutto"], "i limiti si abbassano, non si alzano")
ok(tempi["miniatura"] == 3 and tempi["collega"] == pl.TEMPI["collega"], "i tempi per chiamata si abbassano, non si alzano")
c = pl.confronto([{"momento": SACCO + sec(400), "box": BOX_SACCO}, {"momento": SACCO - sec(20), "box": BOX_SACCO}],
                 SACCO, BOX_SACCO)
ok(c == {"posto": 2, "scarto_s": -20.0, "posto_senza_tempo": 1}, "confronto: posto col tempo e senza")
ok(pl.confronto([{"momento": SACCO, "box": [0, 0, .05, .05]}], SACCO, BOX_SACCO)["posto"] is None, "confronto: altro posto")
lo, hi, passi = pl.affina(lambda t: t, SACCO - sec(60), SACCO + sec(1), lambda t: t >= SACCO)
ok((hi - lo).total_seconds() <= 2 and lo < SACCO <= hi and len(passi) <= 8, "affina: il momento a 2 s")
mv = pl.movimento_vicino([np.zeros((10, 10, 3), np.uint8), None, np.zeros((10, 10, 3), np.uint8),
                          np.full((10, 10, 3), 50, np.uint8)], [0.4, 0.4, 0.2, 0.2])
ok(mv[0] is None and mv[1] is None and mv[3] == 0.0, "movimento vicino: un cambio di luce uniforme non e' movimento")

# ------------------------------------------------------------------ il metodo (b) a tavolino
fot = [scena(t) for t in ts]
ril = pl.rilevazioni(kr, fot, ZONA["riquadri"])
cand = pl.unisci(ril)
primo = cand[0] if cand else {}
ok(len(cand) == 1, f"(b): un candidato solo (il sacco; l'auto passa in 2 minuti, la luce cambia piano) ({len(cand)})")
ok(primo and ts[primo["i"] - 1] < SACCO <= ts[primo["i"]] and pl.iou(primo["box"], BOX_SACCO) > 0.5,
   "(b): il candidato e' il sacco, al minuto giusto")
m, fino, stati, _ = pl.durata(kr, fot, primo["i"], ZONA["riquadri"], box=primo["box"])
ok(fino and m >= 40, f"(b): il sacco resta fino alla fine ({m} min)")
fot2 = [scena(t, auto=(INIZIO + datetime.timedelta(minutes=10), 8)) for t in ts]
c2 = pl.unisci(pl.rilevazioni(kr, fot2, ZONA["riquadri"]))
ok(len(c2) == 2 and any(pl.iou(x["box"], BOX_SACCO) > 0.5 for x in c2), "(b): un'auto ferma 8 minuti e' un candidato in piu' (la giudica Claude)")
fot3 = [scena(t, sacco=None) for t in ts]
ok(pl.unisci(pl.rilevazioni(kr, fot3, ZONA["riquadri"])) == [], "(b): ora vuota con la luce che cambia: nessun candidato")
fot4 = list(fot)
fot4[primo["i"] + 1] = None
ok(len(pl.unisci(pl.rilevazioni(kr, fot4, ZONA["riquadri"]))) == 1, "(b): una miniatura che manca non fa perdere il sacco")

# ------------------------------------------------------------------ prepara_pilota
oggi = datetime.date(2026, 11, 12)
arch = {"primo": "2026-10-25 08:00", "letto_il": "2026-11-11T20:00:00Z", "giorni": {"2026-11-05": 1440, "2026-11-06": 900}}
ok(pp.sul_disco(arch, D(2026, 11, 5, 3), D(2026, 11, 5, 4), oggi)[0], "sul disco: si")
ok(not pp.sul_disco(arch, D(2026, 10, 27, 3), D(2026, 10, 27, 4), oggi)[0], "sul disco: troppo vecchia col margine")
ok("900 minuti" in pp.sul_disco(arch, D(2026, 11, 6, 3), D(2026, 11, 6, 4), oggi)[1], "sul disco: giorno non intero")
ok(not pp.sul_disco(None, D(2026, 11, 6, 3), D(2026, 11, 6, 4), oggi)[0], "sul disco: archivio non letto")
for e in ("ev1", "ev2", "ev3"):
    i0, off = pp.inizio_positiva(e, SACCO)
    ok(300 <= off <= 3300 and i0 == SACCO - sec(off), f"inizio della positiva sorteggiato fra 5 e 55 minuti ({e}: {off} s)")
ok(len({pp.inizio_positiva(e, SACCO)[1] for e in ("a", "b", "c", "d")}) > 1, "l'offset cambia da evento a evento")
sch = [{"evento": f"e{i}", "kit": i % 7, "notte": i in (3, 5, 11)} for i in range(14)]
sc = pp.scegli_positive(sch, quante=5)
ok(len(sc) == 5 and len({s["kit"] for s in sc}) == 5, "positive: un kit per ora")
ok(sum(1 for s in sc if s["notte"]) >= 2, "positive: prima le notti (fino a 3 se ci sono)")
ok(pp.scegli_positive(sch, quante=5) == sc, "positive: la scelta e' riproducibile")
pool = [{"kit": k, "uid": f"U{k}", "canali": [0, 2],
         "archivio": {0: dict(arch, giorni={}), 2: dict(arch, giorni={})}} for k in range(100, 140)]
neg, nd = pp.estrai_negative(pool, oggi, 20)
ok(len(neg) == 20 and len({n["kit"] for n in neg}) == 20, "negative: 20, kit diversi")
ok(sum(1 for n in neg if n["notte"]) == 10 or abs(sum(1 for n in neg if n["notte"]) - 10) <= 2, "negative: meta' di notte")
ok(all(D(2026, 11, 5) <= pl.dt(n["inizio"]) < D(2026, 11, 12) for n in neg), "negative: negli ultimi 7 giorni")
ok(pp.estrai_negative(pool, oggi, 20)[0] == neg, "negative: il sorteggio e' riproducibile")
v = {"kit": 1, "inizio": "2026-11-05 13:00:00"}
ok(pp.sovrapposto(v, {D(2026, 11, 5, 12, 50)}) == D(2026, 11, 5, 12, 50), "scarto: evento 10 min prima dell'ora")
ok(pp.sovrapposto(v, {D(2026, 11, 5, 14, 4)}) == D(2026, 11, 5, 14, 4) and pp.sovrapposto(v, {D(2026, 11, 5, 14, 6)}) is None,
   "scarto: fino a 5 min dopo la fine, non oltre")
ek = pp.eventi_per_kit([{"dati": {"kit": "KIT581 Via", "nome": "a mano 130000", "giorno": "2026-11-05"}}],
                       [{"kit": "EX KIT581 SP", "nome": "targa AB 091500", "quando": "2026-11-06"}])
ok(ek == {581: {D(2026, 11, 5, 13), D(2026, 11, 6, 9, 15)}}, "eventi per kit: sito e NAS, EX KIT compreso")


# ------------------------------------------------------------------ un'ora con la libreria finta
class Finto:
    """Registratore finto: canali 0 e 1; miniature della scena (i «dati» portano l'ora), 47 kB l'una; scarica fa un
    file finto da cui `fotogrammi` legge la scena a 1280 pixel."""

    def __init__(self, primo=D(2026, 10, 25), sacco=SACCO, blocca=None, buche=(), collega_ok=True):
        self.primo, self.sacco, self.blocca, self.buche, self.collega_ok = primo, sacco, blocca, set(buche), collega_ok
        self.miniature = 0
        self.scarichi = 0

    def canali(self):
        return [(0, 100, "CH1"), (1, 101, "CH2")]

    def intervallo(self, h):
        return self.primo, D(2026, 11, 12)

    def miniatura(self, h, t, attesa=12):
        if self.blocca == "miniatura":
            time.sleep(3)
        self.miniature += 1
        if t in self.buche:
            return {"errore": "nessuna miniatura in 12 s"}
        return {"dati": t.isoformat().encode() + b"\0" * 47000, "formato": "H.264", "misura": "704x576",
                "ora_video": str(t)}

    def scarica(self, canale, h, da, secondi, cartella, ffmpeg="ffmpeg"):
        self.scarichi += 1
        os.makedirs(cartella, exist_ok=True)
        f = os.path.join(cartella, f"{da:%H%M%S}.mp4")
        open(f, "w").write(da.isoformat())
        return {"file": f, "mb": 1.8, "attesa_s": 1.0, "fps": 12}

    def chiudi(self):
        pass


def mezzi_finti(fin, cartella):
    def decodifica(dati, formato, grezzo):
        t = D.fromisoformat(dati.split(b"\0")[0].decode())
        return scena(t, sacco=fin.sacco)

    def fotogrammi(mp4):
        t = D.fromisoformat(open(mp4).read())
        return [scena(t + sec(s), sacco=fin.sacco, largo=1280) for s in (0.4, 1.2, 2.0)]
    return {"nuovo": lambda: fin, "collega": lambda reg: (fin.collega_ok, "collegato (finto)" if fin.collega_ok else "non e' l'host"),
            "kr": kr, "decodifica": decodifica, "fotogrammi": fotogrammi, "uscita": os.path.join(cartella, "uscita"),
            "grezzi": os.path.join(cartella, "grezzi"), "cimitero": []}


ORA = {"nome": "pos01_kit581", "tipo": "positiva", "kit": 581, "uid": "X" * 20, "canale": 0,
       "inizio": INIZIO.strftime("%Y-%m-%d %H:%M:%S"), "atteso": SACCO.strftime("%Y-%m-%d %H:%M:%S"),
       "box_dario": BOX_SACCO, "zona": ZONA, "notte": False}
tmp = tempfile.mkdtemp(prefix="prova_pilota_")
scritti = []
fin = Finto()
x = pl.lavora_ora(ORA, {}, mezzi_finti(fin, os.path.join(tmp, "a")), lambda r: scritti.append(json.dumps(r, default=str)))
ok(x["esito"] == "fatto" and x["valutabile"] and not x["in_corso"], f"ora positiva: fatta ({x.get('esito')})")
cb = (x.get("b") or {}).get("candidati") or []
ok(len(cb) == 1 and cb[0]["durata_min"] >= 40 and cb[0]["fino_alla_fine"], "(b): un candidato, resta fino alla fine")
ok(x["confronto"]["b"]["posto"] == 1 and abs(x["confronto"]["b"]["scarto_s"]) <= 2, f"(b): trovato entro 2 s ({x['confronto']['b']})")
ok(cb and cb[0]["fitte"]["chieste"] == 121 and cb[0]["fitte"]["arrivate"] == 121, "miniature fitte: 121 arrivate")
pres = cb[0]["fitte"].get("pezzo_presente") or []
ok(pres[:85] == [0] * 85 and all(pres[95:]), "miniature fitte: il pezzo non c'e' prima del momento, c'e' dopo")
ok(x["a"]["esito"] == "cambio" and x["confronto"]["a"]["posto"] == 1, f"(a) dimezza: trova il sacco ({x['confronto']['a']})")
ok(x["a_miniature"]["esito"] == "cambio" and x["confronto"]["a_miniature"]["posto_senza_tempo"] == 1,
   f"(a) sulle miniature: il sacco, al minuto ({x['confronto']['a_miniature']})")
ok(x["a"]["candidati"][0].get("come_candidato_b") == "b01", "il candidato di (a) uguale a quello di (b) non riscarica le fitte")
pm = x["conti"]["per_metodo"]
ok(pm["b"]["richieste"] == 72 and abs(pm["b"]["mb"] - 72 * 0.047) < 0.1 and pm["a"]["mb"] > 0 and pm["fitte"]["mb"] > 0,
   f"MB per metodo: b {pm['b']['mb']}, a {pm['a']['mb']}, fitte {pm['fitte']['mb']}")
ok(abs(x["conti"]["mb"] - (pm["b"]["mb"] + pm["a"]["mb"] + pm["fitte"]["mb"])) < 0.01, "MB in tutto = somma dei metodi")
U = os.path.join(tmp, "a", "uscita")
ok(len(os.listdir(os.path.join(U, "minuti"))) == 72, "in uscita le 72 miniature dei minuti")
ok(sorted(os.listdir(os.path.join(U, "b01"))) == ["dopo.jpg", "intorno.jpg", "prima.jpg", "ritaglio.jpg", "scena.jpg", "serie.jpg"],
   "per il candidato: prima, dopo, ritaglio, serie, intorno, scena")
ok(os.path.exists(os.path.join(U, "a01", "ritaglio.jpg")), "per il candidato di (a): prima, dopo, ritaglio")
grossi = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(U) for f in fs)
ok(grossi < 6e6, f"l'uscita dell'ora resta piccola ({round(grossi / 1e6, 2)} MB)")
ok(len(os.listdir(os.path.join(tmp, "a", "grezzi"))) >= 190, "le miniature grezze restano sul PC")
ok(len(scritti) >= 5 and json.loads(scritti[-1])["esito"] == "fatto", "il json dell'ora scritto man mano")
ok("box_dario" in x and "atteso" in x, "per le positive l'atteso e il riquadro di Dario stanno nel json (il metodo non li usa)")

# negativa vuota: niente candidati, niente fitte
fin = Finto(sacco=None)
x = pl.lavora_ora(dict(ORA, nome="neg01", tipo="negativa"), {}, mezzi_finti(fin, os.path.join(tmp, "b")))
ok(x["esito"] == "fatto" and x["b"]["candidati"] == [] and "confronto" not in x, "ora negativa vuota: zero candidati")
ok(x["conti"]["per_metodo"].get("fitte") is None or x["conti"]["per_metodo"]["fitte"]["mb"] == 0
   or x["a"]["esito"] == "cambio", "ora vuota: miniature fitte solo per i candidati")
# il registratore non l'ha piu'
fin = Finto(primo=D(2026, 11, 5))
x = pl.lavora_ora(ORA, {}, mezzi_finti(fin, os.path.join(tmp, "c")))
ok(not x["valutabile"] and x["esito"].startswith("non piu'") and fin.miniature == 0 and fin.scarichi == 0,
   "ora non piu' sul registratore: non valutabile, niente chiesto")
# miniature che mancano: 3 su 72, una seconda richiesta ciascuna
fin = Finto(buche={ts[5], ts[30], ts[60]})
x = pl.lavora_ora(ORA, {}, mezzi_finti(fin, os.path.join(tmp, "d")))
ok(x["valutabile"] and x["b"]["arrivate"] == 69 and x["conti"]["per_metodo"]["b"]["richieste"] == 75,
   "miniature che mancano: riprovate una volta, l'ora resta valutabile")
# chiamata che non torna; collegamento rifiutato; kit senza registratore
fin = Finto(blocca="miniatura")
t0 = time.time()
x = pl.lavora_ora(ORA, {"tempi": {"miniatura": 0.3}}, mezzi_finti(fin, os.path.join(tmp, "e")))
ok(x["esito"].startswith("bloccato") and x["bloccato"] and not x["valutabile"] and time.time() - t0 < 5, "chiamata che non torna: bloccato")
x = pl.lavora_ora(ORA, {}, mezzi_finti(Finto(collega_ok=False), os.path.join(tmp, "f")))
ok(x["esito"].startswith("registratore non raggiunto") and not x["valutabile"], "collegamento rifiutato")
x = pl.lavora_ora(dict(ORA, uid=None), {}, mezzi_finti(Finto(), os.path.join(tmp, "g")))
ok(x["esito"] == "registratore sconosciuto", "kit senza registratore")
x = pl.lavora_ora(dict(ORA, canale=3), {}, mezzi_finti(Finto(), os.path.join(tmp, "h")))
ok(x["esito"] == "canale assente sul registratore" and not x["valutabile"], "canale assente")

# ------------------------------------------------------------------ il giro delle ore (il ponte)
ore = ([{"nome": f"pos{i}", "tipo": "positiva", "kit": i} for i in range(3)]
       + [{"nome": f"neg{i}", "tipo": "negativa", "kit": 100 + i} for i in range(5)]
       + [{"nome": f"ris{i}", "tipo": "negativa", "kit": 200 + i, "riserva": True} for i in range(3)])
q, ris = pl.coda(ore, 4)
ok([o["nome"] for o in q] == ["pos0", "neg0", "neg1", "pos1", "neg2", "neg3", "pos2"] and len(ris) == 3,
   "coda: una positiva e due negative alternate, le negative oltre il numero voluto e le riserve fuori")
chiamate = []


def lancia(ora, secondi_max):
    chiamate.append(ora["nome"])
    r = {"nome": ora["nome"], "tipo": ora["tipo"], "kit": ora["kit"], "esito": "fatto", "valutabile": True, "in_corso": False,
         "conti": {"mb": 10.0, "chiamate": 90, "secondi": 300, "per_metodo": {"b": {"mb": 3.3}, "a": {"mb": 6.0}, "fitte": {"mb": 0.7}}}}
    if ora["nome"] == "neg1":
        return 0, dict(r, esito="non piu' sul registratore", valutabile=False, conti={"mb": 0, "chiamate": 3})
    if ora["nome"] == "pos1" and chiamate.count("pos1") == 1:
        return pl.MEMORIA, dict(r, in_corso=True, esito=None)
    if ora["nome"] == "neg2":
        return "fermato dopo 25 minuti", dict(r, in_corso=True, esito=None, b={"candidati_tutti": 2})
    return 0, r


uscite = []
out = pl.lavoro({"ore": ore, "negative_quante": 4}, lancia, lambda o: uscite.append(json.dumps(o, default=str)),
                gia={"pos2": {"nome": "pos2", "tipo": "positiva", "kit": 2, "esito": "fatto", "valutabile": True}})
es = {o["nome"]: o for o in out["ore"]}
ok("ris0" in es and es["neg1"]["sostituita_da"] == "ris0" and "ris1" not in es, "negativa non valutabile: al suo posto la prima riserva")
ok(chiamate.count("pos1") == 2 and es["pos1"]["esito"] == "fatto" and "memoria" in es["pos1"]["tentativo_prima"]["esito"],
   "ora morta di memoria: si rifa' una volta")
ok(es["neg2"]["esito"].startswith("fermato") and es["neg2"]["valutabile"], "ora fermata a tempo con (b) gia' fatto: valutabile per (b)")
ok("pos2" not in chiamate and es["pos2"]["ripreso"], "ripresa del compito: le ore finite non si rifanno")
ct = out["conti"]
ok(ct["per_tipo"]["positiva"]["ore"] == 3 and ct["per_kit"]["100"]["mb"] == 10.0 and ct["in_tutto"]["mb_b"] > 0,
   "conti: per tipo, per kit, per metodo")
out = pl.lavoro({"ore": ore, "limiti": {"ore_in_tutto": 0}}, lancia, lambda o: None, adesso=iter([0, 1, 1, 1]).__next__)
ok(out.get("fermato", "").startswith("passate 0") and not out["ore"], "tempo totale finito: le ore dopo non si fanno")

# ------------------------------------------------------------------ un'ora in un processo a parte, come sul PC
FINTO_NVR = r'''
"""focus_nvr finto per prova_pilota.py: miniature H.264 vere (ffmpeg) di una scena finta; FINTO_CADE=1: errore di memoria."""
import ctypes, datetime, os, subprocess, sys, tempfile
sys.path.insert(0, os.environ["PROVA_QUI"])
import numpy as np


def fps_da_tempi(tempi):
    return 12.0


def nome_per_kit_rifiuti(inizio, canale):
    return f"{inizio:%H%M%S}{canale:02d}S"


def immagine(t):
    import prova_pilota_scena as ps
    return ps.scena(t)


class Registratore:
    def __init__(self, cartella=None, log=print):
        self.cartella = cartella

    def collega(self, uid, utente, password, porta=9010, p2p=False, attesa=25):
        return (password == "finta"), "collegato (finto)" if password == "finta" else "password sbagliata"

    def canali(self):
        return [(0, 100, "CH1"), (1, 101, "CH2")]

    def intervallo(self, h):
        return datetime.datetime(2026, 10, 1), datetime.datetime(2026, 11, 12)

    def _png(self, t, d):
        import cv2
        p = os.path.join(d, f"{t:%H%M%S}.png")
        cv2.imwrite(p, immagine(t))
        return p

    def miniatura(self, h, t, attesa=12):
        if os.environ.get("FINTO_CADE"):
            ctypes.string_at(0)
        d = tempfile.mkdtemp()
        p, out = self._png(t, d), os.path.join(d, "m.h264")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-frames:v", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-f", "h264", out], check=True)
        return {"dati": open(out, "rb").read(), "formato": "H.264", "misura": "704x576", "ora_video": str(t)}

    def scarica(self, canale_num, canale_h, inizio, secondi, cartella, attesa_vuoto=30, ffmpeg="ffmpeg"):
        os.makedirs(cartella, exist_ok=True)
        p = self._png(inizio, cartella)
        f = os.path.join(cartella, nome_per_kit_rifiuti(inizio, canale_num) + ".mp4")
        subprocess.run([ffmpeg, "-v", "error", "-y", "-loop", "1", "-i", p, "-t", str(secondi), "-r", "12", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-vf", "scale=1280:-2", f], check=True)
        os.remove(p)
        return {"file": f, "mb": round(os.path.getsize(f) / 1e6, 3), "fps": 12.0, "attesa_s": 0.5}

    def chiudi(self):
        pass
'''
SCENA = r'''
import datetime, numpy as np
INIZIO = datetime.datetime(2026, 11, 3, 13, 0, 0)
SACCO = INIZIO + datetime.timedelta(minutes=13, seconds=17)
H, W = 576, 704
rnd = np.random.default_rng(5)
SFONDO = np.clip(rnd.normal(120, 25, (H // 8, W // 8, 3)), 0, 255).astype(np.uint8).repeat(8, 0).repeat(8, 1)
TEX = np.clip(rnd.normal(0, 30, (36, 36, 3)), -60, 60).astype(np.int16)


def scena(t):
    f = SFONDO.astype(np.int16)
    if t >= SACCO:
        f[330:366, 460:496] = np.array([30, 35, 40], np.int16) + TEX
    return np.clip(f, 0, 255).astype(np.uint8)
'''
MOV_FINTO = '''

def classe_registratore():   # prova_pilota.py: il registratore finto al posto della DLL
    import focus_nvr
    return focus_nvr.Registratore
'''


def processo_a_parte(cade=False):
    base = tempfile.mkdtemp(prefix="prova_pilota_processo_")
    comp = os.path.join(base, "p2p_ponte31")
    os.makedirs(os.path.join(comp, "FocusNetSDK"))
    for f in ("compito.py", "pilota.py", "pilota_lavoro.py", "dimezza.py", "allunga.py"):
        shutil.copy2(os.path.join(QUI, f), comp)
    open(os.path.join(comp, "movimento.py"), "w").write(open(os.path.join(QUI, "movimento.py")).read() + MOV_FINTO)
    open(os.path.join(comp, "focus_nvr.py"), "w").write(FINTO_NVR)
    open(os.path.join(base, "prova_pilota_scena.py"), "w").write(SCENA)
    open(os.path.join(comp, "focus_accesso.txt"), "w").write("*;utente;finta\n")   # password finta della prova
    d = os.path.join(base, "ora")
    os.makedirs(d)
    shutil.copy2(os.path.join(comp, "compito.py"), os.path.join(d, "ponte.py"))
    shutil.copy2(os.path.join(comp, "pilota_lavoro.py"), os.path.join(d, "compito.py"))
    ora = dict(ORA, minuti=20, atteso="2026-11-03 13:13:17")
    u = os.path.join(base, "uscita_ora")
    json.dump({"ora": ora, "cfg": {"fitte_passo_s": 20}, "compito": comp, "uscita": u}, open(os.path.join(d, "ora.json"), "w"))
    env = dict(os.environ, FINTO_CADE="1" if cade else "", PROVA_QUI=base,
               PYTHONPATH=os.pathsep.join([os.path.abspath(SCRIPTS), base]))
    r = subprocess.run([sys.executable, os.path.join(d, "compito.py"), d], cwd=d, env=env, capture_output=True, text=True,
                       timeout=600)
    return r, d, u, base


if shutil.which("ffmpeg"):
    r, d, u, base = processo_a_parte()
    ok(r.returncode == 0, f"processo a parte: finito con 0 ({r.returncode} {r.stderr[-300:]})")
    try:
        x = json.load(open(os.path.join(u, "ora.json")))
    except (OSError, ValueError):
        x = {}
    ok(x.get("esito") == "fatto" and x.get("valutabile"), f"processo a parte: ora fatta ({x.get('esito')})")
    cb = (x.get("b") or {}).get("candidati") or []
    ok(len(cb) == 1 and (x.get("confronto") or {}).get("b", {}).get("posto") == 1,
       f"processo a parte: miniature H.264 vere decodificate, il sacco trovato ({x.get('confronto')})")
    ok(len(os.listdir(os.path.join(u, "minuti"))) == 32 and os.path.exists(os.path.join(u, "b01", "intorno.jpg")),
       "processo a parte: miniature e fogli in uscita")
    ok(any(f.endswith(".h264") for f in os.listdir(os.path.join(d, "grezzi"))), "processo a parte: i grezzi restano sul PC")
    shutil.rmtree(base, ignore_errors=True)
    r, d, u, base = processo_a_parte(cade=True)
    ok(r.returncode not in (0, 1, 3), f"processo che cade: muore lui ({r.returncode})")
    g = open(os.path.join(d, "uscita", "guasto_memoria.txt")).read()
    ok("Fatal Python error" in g and "miniatura" in g, "processo che cade: le pile di Python in guasto_memoria.txt")
    shutil.rmtree(base, ignore_errors=True)
else:
    print("--   ffmpeg non c'e': salto le prove col processo a parte")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{'TUTTE VERDI' if not fallite else str(len(fallite)) + ' ROSSE: ' + ', '.join(fallite)}")
sys.exit(1 if fallite else 0)
