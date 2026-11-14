"""Prove a tavolino di scorta.py (compito 35) e delle funzioni pure di prepara_scorta.py: niente rete, niente DLL.
Un registratore finto da' le miniature di una scena (un sacco che compare a un minuto dato e resta, un'auto che passa)
e i pezzi «a piena risoluzione» (file finti da cui il fotogramma si ricava dalla stessa scena, ingrandita). Il giro di
tutte le ore con un lancio finto: finestra serale, tetti di MB, ore di lavoro, parti per Drive, ripresa.
Uso: python3 prova_scorta.py   (kit_rifiuti.py da KR_SCRIPTS, se no da ../../../kit-rifiuti-programma/scripts)
version: 0.1.0 (14/11/2026)
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import zipfile

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get("KR_SCRIPTS") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")
sys.path.insert(0, QUI)
sys.path.insert(0, SCRIPTS)
import cv2                    # noqa: E402
import kit_rifiuti as kr      # noqa: E402
import pilota as pl           # noqa: E402
import prepara_scorta as ps   # noqa: E402
import scorta as sc           # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


D = datetime.datetime


def sec(x):
    return datetime.timedelta(seconds=x)


# ------------------------------------------------------------------ funzioni pure: finestra, coda, pezzi, carte
ok(sc.in_finestra(D(2026, 11, 14, 19, 0), "19:00", "07:00") and sc.in_finestra(D(2026, 11, 15, 3, 0), "19:00", "07:00")
   and not sc.in_finestra(D(2026, 11, 14, 7, 0), "19:00", "07:00")
   and not sc.in_finestra(D(2026, 11, 14, 15, 0), "19:00", "07:00"), "finestra che passa la mezzanotte")
ok(sc.in_finestra(D(2026, 11, 14, 10, 0), "09:00", "12:00") and not sc.in_finestra(D(2026, 11, 14, 12, 0), "09:00", "12:00"),
   "finestra nello stesso giorno")
ok(sc.secondi_alla_finestra(D(2026, 11, 14, 18, 30), "19:00", "07:00") == 1800
   and sc.secondi_alla_finestra(D(2026, 11, 14, 23, 0), "19:00", "07:00") == 0
   and sc.secondi_alla_finestra(D(2026, 11, 14, 8, 0), "07:00", "07:30") == 23 * 3600, "secondi all'apertura della finestra")
ore_c = [{"nome": "p1", "tipo": "positiva", "catena": True}, {"nome": "p2", "tipo": "positiva", "catena": False},
         {"nome": "p3", "tipo": "positiva", "catena": True}, {"nome": "n1", "tipo": "negativa"},
         {"nome": "n2", "tipo": "negativa"}, {"nome": "n3", "tipo": "negativa"}]
ok([o["nome"] for o in sc.coda(ore_c)] == ["p1", "n1", "p2", "p3", "n2", "n3"],
   "coda: una negativa dopo ogni positiva della catena, le altre in fondo")
T = D(2026, 11, 13, 21, 10)
cc = [{"comparsa_prima": T, "comparsa": T + sec(60)}, {"comparsa_prima": T + sec(60), "comparsa": T + sec(120)},
      {"comparsa_prima": T + sec(900), "comparsa": T + sec(960)}]
f = sc.finestre(cc, 12, 30)
ok(f == [(T - sec(12), T + sec(150), [1, 2]), (T + sec(888), T + sec(990), [3])],
   f"pezzi: dal minuto prima - 12 s alla comparsa + 30 s, quelli che si toccano uniti ({f})")
ok(sc.tempi_carta(cc[0], -3, 25) == (T - sec(3), T + sec(85)), "carta: 3 s prima del minuto «prima», 25 s dopo la comparsa")
pz = [(T, T + sec(100), "a.mp4"), (T + sec(200), T + sec(300), "b.mp4")]
ok(sc.pezzo_per(T + sec(50), pz) == ("a.mp4", 50.0) and sc.pezzo_per(T + sec(100.5), pz) == ("a.mp4", 100.0)
   and sc.pezzo_per(T + sec(150), pz) == (None, None) and sc.pezzo_per(T + sec(250), pz) == ("b.mp4", 50.0),
   "il pezzo che contiene un momento, coi secondi dal suo inizio")
q, r = sc.quadro_carta(1000, 2000, [0.5, 0.5, 0.01, 0.01])
ok(q == (920, 415, 1100, 595) and r == (1000, 500, 1020, 510), f"ritaglio della carta: almeno il 18% del lato corto ({q})")
q, r = sc.quadro_carta(1000, 2000, [0.0, 0.0, 0.1, 0.1])
ok(q == (0, 0, 400, 350), f"ritaglio della carta: tagliato ai bordi ({q})")
POS = {"tipo": "positiva", "atteso": "2026-11-13 21:10:30", "box_dario": [0.5, 0.5, 0.05, 0.05], "evento": "e1",
       "altri_noti": [{"evento": "e2", "box": [0.1, 0.1, 0.05, 0.05]}],
       "eventi": [{"evento": "e1", "box": [0.5, 0.5, 0.05, 0.05]}, {"evento": "e3", "box": [0.8, 0.8, 0.05, 0.05]}]}
c1 = {"box": [0.5, 0.5, 0.05, 0.05], "comparsa_prima": T, "comparsa": T + sec(60)}
ok(sc.verita(c1, POS) == {"vero": True, "tocca_vero": True, "altro_noto": False}, "verita': il candidato e' l'abbandono")
c2 = dict(c1, comparsa_prima=T + sec(1800), comparsa=T + sec(1860))
ok(sc.verita(c2, POS) == {"vero": False, "tocca_vero": True, "altro_noto": False}, "verita': stesso posto, momento sbagliato")
ok(sc.verita(dict(c1, box=[0.1, 0.1, 0.05, 0.05]), POS)["altro_noto"]
   and sc.verita(dict(c1, box=[0.8, 0.8, 0.05, 0.05]), POS)["altro_noto"], "verita': un altro abbandono noto non e' un falso")
ok(sc.verita(c1, {"tipo": "negativa"}) == {"vero": False, "tocca_vero": False, "altro_noto": False}, "verita': negativa")
ok(sc.gruppi_zip([("a", 60), ("b", 60), ("c", 60), ("d", 300), ("e", 10)], 180) == [["a", "b", "c"], ["d"], ["e"]],
   "parti per Drive: mai sopra il tetto (una voce piu' grande sta da sola)")
LIM = sc.limiti_da({})
ok(sc.tetto({"kit": 1, "catena": True, "video": [1]}, 0, 0, LIM)[0] == "tutto", "tetto: un'ora nuova si fa tutta")
ok(sc.tetto({"kit": 1, "catena": True, "video": [1]}, 900, 0, LIM)[0] == "senza_catena", "tetto: vicino al tetto del kit, senza catena")
ok(sc.tetto({"kit": 1, "catena": False, "video": [1]}, 900, 0, LIM)[0] == "tutto", "tetto: senza catena la scorta ci sta")
ok(sc.tetto({"kit": 1, "catena": True, "video": [1]}, 990, 0, LIM)[0] == "niente", "tetto del kit passato: niente")
ok(sc.tetto({"kit": 1, "video": []}, 0, 29999, LIM)[0] == "niente", "tetto in tutto passato: niente")
lim2 = sc.limiti_da({"limiti": {"mb_per_kit": 500, "ore_di_lavoro": 99}})
ok(lim2["mb_per_kit"] == 500 and lim2["ore_di_lavoro"] == sc.LIMITI["ore_di_lavoro"], "i limiti si abbassano, non si alzano")
ok(sc.catena_da({"catena": {"candidati": 2, "ignota": 1}})["candidati"] == 2 and "ignota" not in sc.catena_da({"catena": {"ignota": 1}}),
   "catena: le chiavi conosciute dal file, le altre no")
ok(sc.nome_giudizi(["Qwen/Qwen3-VL-4B-Instruct", "nf4", "v3", "c35"]) == "giudizi_Qwen3-VL-4B-Instruct_v3_c35.json"
   and sc.nome_giudizi(["Qwen/Qwen3-VL-4B-Instruct", "nf4", "v3"]) == "giudizi_Qwen3-VL-4B-Instruct_v3.json",
   "il nome del file dei giudizi (vlm.py 0.5.0)")
ok(sc.risposta_qwen({"testo": '{"prima": "empty ground", "dopo": "black bag near bin", "risposta": "already", "sicuro": true}',
                     "risposta": "cassonetto"}) == "already", "Qwen: «already» letto dal json, non da «bin» nel testo")
ok(sc.risposta_qwen({"testo": '{"prima": "x", "dopo": "y", "risposta": "waste", "sicuro": tru', "risposta": "giusto"}) == "waste",
   "Qwen: json tagliato, la risposta si legge lo stesso")
ok(sc.risposta_qwen({"testo": "boh", "risposta": "veicolo"}) == "vehicle", "Qwen: senza json, dalla risposta in italiano")

# conti della catena su ore finte
ORE_X = [
    {"nome": "pos001", "tipo": "positiva", "vista": None, "catena": {"fatta": True, "candidati": [
        {"rango": 1, "vero": False, "altro_noto": False, "carta": "pos001_1"},
        {"rango": 2, "vero": True, "altro_noto": False, "carta": "pos001_2"},
        {"rango": 3, "vero": False, "altro_noto": True, "carta": "pos001_3"}]}},
    {"nome": "pos002", "tipo": "positiva", "vista": "grande", "catena": {"fatta": True, "candidati": [
        {"rango": 1, "vero": True, "altro_noto": False, "carta": "pos002_1"}]}},
    {"nome": "neg001", "tipo": "negativa", "catena": {"fatta": True, "candidati": [
        {"rango": 1, "vero": False, "altro_noto": False, "carta": "neg001_1"},
        {"rango": 2, "vero": False, "altro_noto": False, "carta": "neg001_2"}]}},
    {"nome": "pos003", "tipo": "positiva", "catena": {"fatta": False, "esito": "saltata"}}]
G = [{"id": "pos001_1", "testo": '{"risposta": "vehicle"}'}, {"id": "pos001_2", "testo": '{"risposta": "waste"}'},
     {"id": "pos001_3", "testo": '{"risposta": "waste"}'}, {"id": "pos002_1", "testo": '{"risposta": "waste"}'},
     {"id": "neg001_1", "testo": '{"risposta": "waste"}'}, {"id": "neg001_2", "testo": '{"risposta": "nothing"}'}]
ok(len(sc.carte_per_qwen(ORE_X)) == 6 and sc.carte_per_qwen(ORE_X)[1] == {"id": "pos001_2", "file": "pos001_2.jpg",
   "vero": True, "rango": 2, "ora": "pos001", "tipo": "positiva"}, "carte per Qwen: tutte, con la verita' per chi misura")
fin = sc.catena_finale(json.loads(json.dumps(ORE_X)), G, "fatto", sc.CATENA)
k = fin["conti"]
ok(fin["carte_giudicate"] == 6 and k["positive"]["ore"] == 2 and k["negative"]["ore"] == 1, "conti: ore con la catena fatta")
ok(k["positive"]["primo"] == 1 and k["positive"]["nei_primi"] == 2 and k["positive"]["primo_dopo_qwen"] == 2
   and k["positive"]["nei_primi_dopo_qwen"] == 2, f"conti: l'abbandono prima e dopo Qwen ({k['positive']})")
ok(k["positive"]["falsi"] == 1 and k["positive"]["falsi_dopo_qwen"] == 0 and k["negative"]["falsi"] == 2
   and k["negative"]["falsi_dopo_qwen"] == 1, "conti: i falsi prima e dopo Qwen (l'altro noto non e' un falso)")
ok(k["positive_mai_viste"]["ore"] == 1, "conti: le positive mai viste a parte")
c = fin["ore"][0]["catena"]["candidati"][0]
ok(c["qwen"]["risposta"] == "vehicle" and c["tiene"] is False and fin["ore"][0]["catena"]["candidati"][1]["tiene"],
   "catena.json: per ogni candidato il giudizio di Qwen e se lo tiene")
fin0 = sc.catena_finale(json.loads(json.dumps(ORE_X)), None, "Qwen si e' fermato", sc.CATENA)
ok(fin0["carte_giudicate"] == 0 and fin0["conti"]["positive"]["senza_giudizio"] == 4 and fin0["qwen_esito"].startswith("Qwen"),
   "catena.json anche senza Qwen: le ore e i candidati ci sono, il perche' e' scritto")

# ------------------------------------------------------------------ prepara_scorta: funzioni pure
righe = {"ev1": [{"esito": "ok", "cam": 2, "corrette": [1]}], "ev2": [{"esito": "no", "cam": 1}],
         "ev3": [{"esito": "ok", "cam": 1, "bizzarro": True}]}


def verita_finta(r):
    return {"riquadri": {"2": [{"inizio": 12.5, "box": [0.1, 0.2, 0.05, 0.05]}, {"inizio": 30.0, "box": [0, 0, .1, .1]}]}}


def esito_finto(r):
    return next((y.get("esito") for y in r if y.get("esito")), None)


gd = ps.giudizi_dario(righe, verita_finta, esito_finto)
ok(gd == [{"evento": "ev1", "cam": 2, "t": 12.5, "box": [0.1, 0.2, 0.05, 0.05], "fonte": "dario"}],
   "giudizi di Dario: solo gli «ok» non bizzarri, il primo riquadro per telecamera")
pr = ps.primo_per_evento([{"evento": "a", "t": 20, "fonte": "etichette_claude"}, {"evento": "a", "t": 20, "fonte": "dario"},
                          {"evento": "a", "t": 30, "fonte": "dario"}, {"evento": "b", "t": 5, "fonte": "giri"}])
ok(pr["a"]["fonte"] == "dario" and pr["a"]["t"] == 20 and pr["b"]["t"] == 5, "il primo giudizio per evento, a parita' vince Dario")
at = D(2026, 11, 1, 10, 30)
i1, off = ps.inizio_ora("ev1", at)
ok(300 <= off <= 3300 and i1 == at - sec(off) and ps.inizio_ora("ev1", at) == (i1, off), "inizio dell'ora: 5-55 minuti prima, sempre uguale")
ok(ps.video_di(at) == (at - sec(30), 90), "video: da 30 s prima a 60 s dopo")


def scheda(e, kit, can, atteso, resta, inizio_min=20):
    a = D.strptime(atteso, "%Y-%m-%d %H:%M:%S")
    return {"evento": e, "kit": kit, "canale": can, "atteso": atteso, "resta_giorni": resta,
            "inizio": (a - datetime.timedelta(minutes=inizio_min)).strftime("%Y-%m-%d %H:%M:%S")}


sch = [scheda("a", 1, 0, "2026-11-01 10:30:00", 3), scheda("b", 1, 0, "2026-11-01 10:50:00", 5),
       scheda("c", 1, 1, "2026-11-01 10:40:00", 5), scheda("d", 2, 0, "2026-11-01 10:30:00", 0),
       scheda("e", 1, 0, "2026-11-01 12:30:00", 4)]
g = ps.raggruppa_ore(sch)
ok([x["scheda"]["evento"] for x in g] == ["d", "a", "e", "c"] and [s["evento"] for s in g[1]["eventi"]] == ["a", "b"],
   "ore: prima le piu' urgenti; un abbandono dentro un'ora gia' presa (stesso kit e telecamera) entra in quella")
oggi = datetime.date(2026, 11, 14)
arch = {("U1", 0): {"primo": "2026-10-25 00:00", "letto_il": "2026-11-14", "giorni": {}}}
ore_pos = [{"nome": "pos001_kit1", "kit": 1, "uid": "U1", "canale": 0, "inizio": "2026-11-10 10:00:00"},
           {"nome": "pos002_kit1", "kit": 1, "uid": "U1", "canale": 0, "inizio": "2026-11-11 10:00:00"},
           {"nome": "pos003_kit1", "kit": 1, "uid": "U1", "canale": 0, "inizio": "2026-11-12 10:00:00"}]
neg, scart = ps.negative_per(ore_pos, arch, {1: {D(2026, 11, 9, 12, 0)}}, oggi)
ok(len(neg) == 2 and len({n["inizio"][:10] for n in neg}) == 2, f"negative: al massimo 2 per kit, giorni diversi ({len(neg)})")
ok(all(n["kit"] == 1 and n["canale"] == 0 and n["uid"] == "U1" for n in neg), "negative: stesso kit e stessa telecamera")
ok(all(abs(D.strptime(n["inizio"], "%Y-%m-%d %H:%M:%S") - D.strptime(p["inizio"], "%Y-%m-%d %H:%M:%S"))
       >= datetime.timedelta(hours=1) for n in neg for p in ore_pos), "negative: mai sopra un'ora positiva")
ok(all(not (D(2026, 11, 9, 10, 0) <= D.strptime(n["inizio"], "%Y-%m-%d %H:%M:%S") <= D(2026, 11, 9, 14, 0)) for n in neg),
   "negative: lontane 2 ore da un evento noto")
molte = [dict(ore_pos[0], nome=f"pos{k:03d}_kit{k}", kit=k, uid="U1") for k in range(40)]
nn, _ = ps.negative_per(molte, arch, {}, oggi)
ok(12 <= sum(n["notte"] for n in nn) <= 28, f"negative: circa meta' di notte ({sum(n['notte'] for n in nn)} su {len(nn)})")
ok(ps.negative_per(ore_pos, {}, {}, oggi)[0] == [], "negative: archivio non letto, niente")

# ------------------------------------------------------------------ il giro con un lancio finto
ORE_G = [{"nome": f"pos{k}", "tipo": "positiva", "kit": 1 if k <= 3 else k, "catena": True, "video": [1]}
         for k in range(1, 6)] + [{"nome": f"neg{k}", "tipo": "negativa", "kit": 10 + k, "catena": True} for k in range(1, 4)]


class Orologio:
    def __init__(self, t):
        self.t = t

    def adesso(self):
        return self.t

    def secondi(self):
        return (self.t - D(2026, 11, 14)).total_seconds()

    def dorme(self, s):
        self.t += sec(s)


def giro(cfg, t0, mb_ora=450.0, codici=None, gia=None, prima=None, gb=999.0, chiudi=None):
    o = Orologio(t0)
    lanciate, scritti, parti = [], [], []
    codici = dict(codici or {})

    def lancia(ora, smax):
        lanciate.append((ora["nome"], ora["budget"]))
        o.dorme(1800)
        cod = codici.pop(ora["nome"], 0)
        return cod, {"nome": ora["nome"], "tipo": ora["tipo"], "kit": ora["kit"], "esito": "fatto", "valutabile": True,
                     "conti": {"mb": mb_ora if ora["budget"] == "tutto" else 50.0},
                     "catena": {"esito": "fatta" if ora["budget"] == "tutto" else "saltata"}}

    def manda(ore, k):
        parti.append(list(ore))
        return {"parte": k, "ore": list(ore), "ok": True, "mb": 3.4 * len(ore)}
    out = sc.giro(cfg, lancia, manda, lambda n: 3.4, lambda x: scritti.append(json.dumps(x)), adesso=o.adesso,
                  orologio=o.secondi, dorme=o.dorme, gb_liberi=lambda: gb, perche_chiudere=lambda: chiudi(o) if chiudi else None,
                  gia=gia, prima=prima)
    return out, lanciate, parti, o


out, lan, parti, o = giro({"ore": ORE_G}, D(2026, 11, 14, 15, 0))
ok(lan and lan[0][0] == "pos1" and o.t >= D(2026, 11, 14, 19, 0), "giro: aspetta la finestra serale prima della prima ora")
ok(out["ore"][2]["esito"].startswith("saltata") is False and [x for x in lan if x[0] == "pos2"][0][1] == "tutto"
   and [x for x in lan if x[0] == "pos3"][0][1] == "senza_catena", f"giro: il tetto del kit toglie la catena alla terza ora ({lan})")
ok(sum(1 for x in out["ore"] if x["nome"].startswith("pos") and x["kit"] == 1) == 3, "giro: le ore del kit 1 tutte scritte")
ok(out["mb_per_kit"]["1"] == 950.0 and out["mb_in_tutto"] > 950, f"giro: MB per kit e in tutto ({out['mb_per_kit']})")
ok(sum(len(p) for p in parti) == 8 and all(len(p) * 3.4 <= 180 for p in parti), "giro: tutte le miniature in parti sotto il tetto")
ok(not out.get("fermato") and out["secondi_di_lavoro"] == 8 * 1800, "giro: tutte fatte, ore di lavoro contate")
ok(bool(out["fine_ore"]), "giro: fine scritta")
# ore di lavoro finite
out, lan, parti, o = giro({"ore": ORE_G, "limiti": {"ore_di_lavoro": 2.0}}, D(2026, 11, 14, 20, 0))
ok(len(lan) == 5 and out["fermato"].startswith("passate 2 ore") and len(out["non_fatte"]) == 3,
   f"giro: dopo le ore di lavoro si ferma e scrive cosa resta ({out.get('fermato')})")
# la finestra si chiude a meta': aspetta la sera dopo (se il ponte non chiude)
out, lan, parti, o = giro({"ore": ORE_G}, D(2026, 11, 15, 5, 0))
ok(len(lan) == 8 and o.t > D(2026, 11, 15, 19, 0), "giro: la finestra si chiude, riprende la sera dopo")
out, lan, parti, o = giro({"ore": ORE_G}, D(2026, 11, 15, 5, 0), chiudi=lambda oo: "il ponte chiude" if oo.t.hour >= 8 else None)
ok(len(lan) == 4 and out["fermato"].startswith("il ponte chiude"), f"giro: se il ponte chiude non aspetta ({len(lan)})")
# disco pieno
out, lan, parti, o = giro({"ore": ORE_G}, D(2026, 11, 14, 20, 0), gb=5.0)
ok(lan == [] and out["fermato"].startswith("disco quasi pieno"), "giro: col disco quasi pieno non comincia")
# errore di memoria: si rifa' una volta in fondo
out, lan, parti, o = giro({"ore": ORE_G}, D(2026, 11, 14, 20, 0), codici={"neg2": sc.MEMORIA})
ok([x[0] for x in lan].count("neg2") == 2 and lan[-1][0] == "neg2", "giro: un'ora morta di memoria si rifa' in fondo")
ok(sum(len(p) for p in parti) == 8, "giro: l'ora rifatta va in una parte sola")
# ripresa: le ore finite non si rifanno, le parti gia' mandate restano
gia = {"pos1": {"nome": "pos1", "tipo": "positiva", "kit": 1, "esito": "fatto", "conti": {"mb": 200}}}
prima = {"parti": [{"parte": 1, "ore": ["pos1"], "ok": True}], "secondi_di_lavoro": 1800}
out, lan, parti, o = giro({"ore": ORE_G}, D(2026, 11, 14, 20, 0), gia=gia, prima=prima)
ok("pos1" not in [x[0] for x in lan] and out["ore"][0]["nome"] == "pos1" and out["parti"][0]["ore"] == ["pos1"]
   and all("pos1" not in p for p in parti) and out["secondi_di_lavoro"] == 8 * 1800,
   "giro ripreso: le ore finite e le parti mandate restano, il resto si fa")

# ------------------------------------------------------------------ un'ora con il registratore finto
INIZIO = D(2026, 11, 13, 21, 0, 0)
SACCO = INIZIO + datetime.timedelta(minutes=23, seconds=17)
H, W = 576, 704
ZONA = {"riquadri": [[0.5, 0.3, 0.4, 0.5]], "escludi": []}
BOX_SACCO = [460 / W, 330 / H, 36 / W, 36 / H]
rnd = np.random.default_rng(5)
SFONDO = np.clip(rnd.normal(120, 25, (H // 8, W // 8, 3)), 0, 255).astype(np.uint8).repeat(8, 0).repeat(8, 1)
TEX = np.clip(rnd.normal(0, 30, (36, 36, 3)), -60, 60).astype(np.int16)


def scena(t, sacco=SACCO, largo=W):
    """La miniatura all'ora t: sfondo, un sacco scuro da `sacco` che resta, un'auto chiara che passa al minuto 40."""
    f = SFONDO.astype(np.int16)
    if sacco is not None and t >= sacco:
        f[330:366, 460:496] = np.array([30, 35, 40], np.int16) + TEX
    if INIZIO + datetime.timedelta(minutes=40) <= t < INIZIO + datetime.timedelta(minutes=42):
        f[200:300, 380:560] = np.array([210, 205, 200], np.int16)
    f = np.clip(f + rnd.integers(-3, 4, f.shape), 0, 255).astype(np.uint8)
    return f if largo == W else cv2.resize(f, (largo, int(round(H * largo / W))), interpolation=cv2.INTER_LINEAR)


class Finto:
    """Registratore finto: canali 0 e 1, miniature della scena, scarico a 10 fotogrammi al secondo (file finti con
    l'ora del primo fotogramma)."""

    def __init__(self, sacco=SACCO, primo=D(2026, 10, 30)):
        self.sacco, self.primo = sacco, primo
        self.miniature = self.scarichi = 0

    def canali(self):
        return [(0, 100, "CH1"), (1, 101, "CH2")]

    def intervallo(self, h):
        return self.primo, D(2026, 11, 14, 4)

    def miniatura(self, h, t, attesa=12):
        self.miniature += 1
        return {"dati": t.isoformat().encode() + b"\0" * 47000, "formato": "H.264", "misura": "704x576",
                "ora_video": str(t)}

    def scarica(self, canale, h, da, secondi, cartella, ffmpeg="ffmpeg"):
        self.scarichi += 1
        tempi = [da + sec(k / 10) for k in range(int(secondi * 10))]
        os.makedirs(cartella, exist_ok=True)
        f = os.path.join(cartella, f"{da:%H%M%S}{canale:02d}S.mp4")
        open(f, "w").write(da.isoformat())
        return {"file": f, "tempi": tempi, "mb": round(secondi * 0.38, 2), "fps": 10.0, "codec": "H.264",
                "misura": "1408x1152"}

    def chiudi(self):
        pass


def mezzi_finti(fin, cartella):
    def decodifica(dati, formato, grezzo):
        return scena(D.fromisoformat(dati.split(b"\0")[0].decode()), sacco=fin.sacco)

    def fotogramma(mp4, s):
        return scena(D.fromisoformat(open(mp4).read()[:19]) + sec(s), sacco=fin.sacco, largo=1408)

    def taglia(file, n, dest):
        shutil.copy(file, dest)
        return True
    return {"nuovo": lambda: fin, "collega": lambda reg: (True, "collegato (finto)"), "kr": kr, "cv2": cv2,
            "decodifica": decodifica, "fotogrammi": lambda mp4: [], "uscita": os.path.join(cartella, "pc"),
            "drive": os.path.join(cartella, "drive"), "grezzi": os.path.join(cartella, "grezzi"), "cimitero": [],
            "sposta": shutil.move, "taglia": taglia, "foglio": lambda mp4, jpg: None, "fotogramma": fotogramma,
            "ffmpeg": "ffmpeg"}


ORA = {"nome": "pos001_kit581", "tipo": "positiva", "kit": 581, "uid": "X" * 20, "canale": 0,
       "inizio": INIZIO.strftime("%Y-%m-%d %H:%M:%S"), "atteso": SACCO.strftime("%Y-%m-%d %H:%M:%S"),
       "box_dario": BOX_SACCO, "zona": ZONA, "notte": True, "evento": "e581", "catena": True, "budget": "tutto",
       "eventi": [{"evento": "e581", "atteso": SACCO.strftime("%Y-%m-%d %H:%M:%S"), "box": BOX_SACCO}],
       "video": [{"evento": "e581", "canale": 0, "inizio": (SACCO - sec(30)).strftime("%Y-%m-%d %H:%M:%S"), "secondi": 90}],
       "altri_noti": [], "vista": None}
tmp = tempfile.mkdtemp(prefix="prova_scorta_")
try:
    scritti = []
    fin = Finto()
    mz = mezzi_finti(fin, os.path.join(tmp, "a"))
    x = sc.lavora_ora(ORA, {}, mz, lambda r: scritti.append(json.dumps(r, default=str)))
    ok(x["esito"] == "fatto" and x["valutabile"] and not x["in_corso"], f"ora positiva: fatta ({x.get('esito')})")
    ok(len(os.listdir(os.path.join(mz["uscita"], "minuti"))) == 72 and x["minuti"]["b"]["arrivate"] == 72,
       "le 72 miniature dei minuti restano sul PC")
    v = x["video"][0]
    ok(v["esito"] == "fatto" and v["coperti_s"] >= 89 and v["buchi_s"] == 0 and len([f for f in os.listdir(os.path.join(mz["uscita"], "video")) if f.endswith(".mp4")]) == 1,
       f"il video dell'abbandono: 90 s sul PC ({v})")
    ok(sorted(v["fotogrammi"].values()) == ["e581_dopo.jpg", "e581_prima.jpg"]
       and all(os.path.exists(os.path.join(mz["drive"], f)) for f in v["fotogrammi"].values()),
       "due fotogrammi dell'abbandono nell'uscita")
    ct = x["catena"]
    ok(ct["fatta"] and ct["candidati_tutti"] >= 1 and ct["candidati"][0]["vero"] and ct["candidati"][0]["rango"] == 1,
       f"catena: «insieme» mette l'abbandono primo ({ct.get('esito')})")
    ok(len(ct["pezzi"]) == len(sc.finestre([dict(comparsa=D.strptime(c["comparsa"], "%Y-%m-%d %H:%M:%S"),
                                                comparsa_prima=D.strptime(c["comparsa_prima"], "%Y-%m-%d %H:%M:%S"))
                                           for c in ct["candidati"][:3]], 12, 30)), "catena: un pezzo per finestra")
    carta = ct["candidati"][0]["carta"]
    ok(carta == "pos001_kit581_1" and all(os.path.exists(os.path.join(mz["uscita"], "carte", carta + s))
                                          for s in ("_prima.jpg", "_dopo.jpg", ".jpg")), "catena: la carta per Qwen sul PC")
    im = cv2.imread(os.path.join(mz["uscita"], "carte", carta + ".jpg"))
    ok(im is not None and im.shape[1] == 1280 and max(cv2.imread(os.path.join(mz["uscita"], "carte", carta + "_dopo.jpg")).shape[:2]) == 640,
       "carta come il compito 34: scena larga 1280, ritagli da 640")
    ok(all(os.path.exists(os.path.join(mz["drive"], "carte", carta + s)) for s in ("_prima.jpg", "_dopo.jpg", ".jpg"))
       and cv2.imread(os.path.join(mz["drive"], "carte", carta + ".jpg")).shape[1] == 640, "copie piccole della carta nell'uscita")
    pr = cv2.imread(os.path.join(mz["uscita"], "carte", carta + "_prima.jpg")).astype(int)
    do = cv2.imread(os.path.join(mz["uscita"], "carte", carta + "_dopo.jpg")).astype(int)
    ok(np.abs(pr - do).mean() > 5, "la carta: prima senza il sacco, dopo col sacco")
    ok(x["conti"]["mb"] > x["conti"]["mb_minuti"] > 0 and x["conti"]["mb_video"] > 0 and x["conti"]["mb_catena"] > 0,
       f"MB scritti per parte ({x['conti']})")
    uscita_mb = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(mz["drive"]) for f in fs) / 1e6
    ok(uscita_mb < 1.5, f"l'uscita dell'ora resta piccola ({uscita_mb:.2f} MB)")
    ok(len(scritti) >= 4 and json.loads(scritti[-1])["esito"] == "fatto", "il json dell'ora scritto man mano")
    # negativa vuota: la catena gira ma non trova niente
    fin = Finto(sacco=None)
    mz = mezzi_finti(fin, os.path.join(tmp, "b"))
    x = sc.lavora_ora(dict(ORA, nome="neg001_kit581", tipo="negativa", video=[], eventi=[], box_dario=None, atteso=None),
                      {}, mz)
    ok(x["catena"]["fatta"] and x["catena"]["candidati_tutti"] == 0 and fin.scarichi == 0,
       "negativa vuota: zero candidati, niente scaricato a piena risoluzione")
    # tetto del kit: niente catena, la scorta si'
    fin = Finto()
    mz = mezzi_finti(fin, os.path.join(tmp, "c"))
    x = sc.lavora_ora(dict(ORA, budget="senza_catena"), {}, mz)
    ok(x["catena"]["esito"].startswith("saltata") and x["video"][0]["esito"] == "fatto" and fin.scarichi == 1,
       "con il tetto del kit vicino: video si', pezzi della catena no")
    # ora fuori dalla catena (parte cieca): solo la scorta
    fin = Finto()
    x = sc.lavora_ora(dict(ORA, catena=False, fuori_catena="parte cieca"), {}, mezzi_finti(fin, os.path.join(tmp, "d")))
    ok(not x["catena"]["chiesta"] and not x["catena"]["fatta"] and x["video"][0]["esito"] == "fatto",
       "ora fuori catena: miniature e video, niente catena")
    # il registratore non l'ha piu'
    fin = Finto(primo=D(2026, 11, 14))
    x = sc.lavora_ora(ORA, {}, mezzi_finti(fin, os.path.join(tmp, "e")))
    ok(not x["valutabile"] and fin.miniature == 0 and fin.scarichi == 0 and x["video"][0]["esito"].startswith("non piu'"),
       f"ora non piu' sul registratore: niente chiesto ({x['video'][0].get('esito')})")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ------------------------------------------------------------------ il ponte vero con un registratore finto (processi a parte)
FINTO_NVR = r"""
import datetime, os, subprocess, sys, tempfile
sys.path.insert(0, os.environ["PROVA_QUI"])


def fps_da_tempi(tempi):
    return 1.0


def nome_per_kit_rifiuti(inizio, canale):
    return f"{inizio:%H%M%S}{canale:02d}S"


def _png(t, d, largo=None):
    import cv2
    import prova_scorta_scena as ps
    p = os.path.join(d, f"{t:%H%M%S}.png")
    f = ps.scena(t)
    if largo:
        f = cv2.resize(f, (largo, int(round(f.shape[0] * largo / f.shape[1]))))
    cv2.imwrite(p, f)
    return p


class Registratore:
    def __init__(self, cartella=None, log=print):
        pass

    def collega(self, uid, utente, password, porta=9010, p2p=False, attesa=25):
        return (password == "finta"), "collegato (finto)" if password == "finta" else "password sbagliata"

    def canali(self):
        return [(0, 100, "CH1"), (1, 101, "CH2")]

    def intervallo(self, h):
        return datetime.datetime(2026, 10, 30), datetime.datetime(2026, 11, 14, 4)

    def miniatura(self, h, t, attesa=12):
        d = tempfile.mkdtemp()
        p, out = _png(t, d), os.path.join(d, "m.h264")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-frames:v", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-f", "h264", out], check=True)
        return {"dati": open(out, "rb").read(), "formato": "H.264", "misura": "704x576", "ora_video": str(t)}

    def scarica(self, canale_num, canale_h, inizio, secondi, cartella, attesa_vuoto=30, ffmpeg="ffmpeg"):
        d = tempfile.mkdtemp()
        tempi = [inizio + datetime.timedelta(seconds=k) for k in range(int(secondi))]
        for k, t in enumerate(tempi):
            os.replace(_png(t, d, 1408), os.path.join(d, f"f{k:04d}.png"))
        os.makedirs(cartella, exist_ok=True)
        f = os.path.join(cartella, nome_per_kit_rifiuti(inizio, canale_num) + ".mp4")
        subprocess.run([ffmpeg, "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(d, "f%04d.png"), "-c:v",
                        "libx264", "-pix_fmt", "yuv420p", "-r", "1", "-g", "1", f], check=True)
        fps_da_tempi(tempi)
        return {"file": f, "mb": round(os.path.getsize(f) / 1e6, 3), "fps": 1.0, "codec": "H.264", "misura": "1408x1152"}

    def chiudi(self):
        pass
"""
SCENA = r"""
import datetime, numpy as np
INIZIO = datetime.datetime(2026, 11, 13, 21, 0, 0)
SACCO = INIZIO + datetime.timedelta(minutes=23, seconds=17)
H, W = 576, 704
rnd = np.random.default_rng(5)
SFONDO = np.clip(rnd.normal(120, 25, (H // 8, W // 8, 3)), 0, 255).astype(np.uint8).repeat(8, 0).repeat(8, 1)
TEX = np.clip(rnd.normal(0, 30, (36, 36, 3)), -60, 60).astype(np.int16)


def scena(t):
    f = SFONDO.astype(np.int16)
    if t >= SACCO:
        f[330:366, 460:496] = np.array([30, 35, 40], np.int16) + TEX
    return np.clip(f, 0, 255).astype(np.uint8)
"""
MOV_FINTO = """

def classe_registratore():   # prova_scorta.py: il registratore finto al posto della DLL
    import focus_nvr
    return focus_nvr.Registratore
"""
DRIVE_FINTO = r"""
import json, os, shutil
def carica(locale, nome, cartelle=(), proprieta=None):
    d = os.path.join(os.environ["PROVA_QUI"], "drive")
    os.makedirs(d, exist_ok=True)
    if not nome.startswith("scorta35_"):
        return False, "su Drive manca il segnaposto"
    shutil.copy(locale, os.path.join(d, nome))
    json.dump(proprieta, open(os.path.join(d, nome + ".json"), "w"))
    return True, f"{nome} caricato su Drive"
def trova(nome, cartelle=()):
    return None
"""


class _Tempo:
    """time del ponte senza le attese (Qwen finto risponde subito)."""
    def __getattr__(self, k):
        import time
        return getattr(time, k)

    @staticmethod
    def sleep(s):
        pass


class _Sottoprocessi:
    """subprocess del ponte senza creationflags (solo Windows)."""
    def __getattr__(self, k):
        import subprocess
        return getattr(subprocess, k)

    @staticmethod
    def Popen(*a, **k):
        import subprocess
        k.pop("creationflags", None)
        return subprocess.Popen(*a, **k)


def ponte_finto():
    import time

    base = tempfile.mkdtemp(prefix="prova_scorta_ponte_")
    casa, comp = os.path.join(base, "casa"), os.path.join(base, "p2p_ponte35")
    os.makedirs(os.path.join(comp, "FocusNetSDK"))
    os.makedirs(casa)
    for f in ("compito.py", "scorta.py", "scorta_lavoro.py", "pilota.py", "dimezza.py", "allunga.py", "b_tavolino.py"):
        shutil.copy2(os.path.join(QUI, f), comp)
    open(os.path.join(comp, "movimento.py"), "w").write(open(os.path.join(QUI, "movimento.py")).read() + MOV_FINTO)
    open(os.path.join(comp, "focus_nvr.py"), "w").write(FINTO_NVR)
    open(os.path.join(base, "prova_scorta_scena.py"), "w").write(SCENA)
    open(os.path.join(base, "drive_alma.py"), "w").write(DRIVE_FINTO)
    open(os.path.join(comp, "focus_accesso.txt"), "w").write("*;utente;finta\n")   # password finta della prova
    exe = os.path.join(base, "exe.sh")   # l'exe di Kit_Rifiuti: «exe --compito <cartella>» fa girare <cartella>/compito.py
    open(exe, "w").write(f'#!/bin/sh\nexec "{sys.executable}" "$2/compito.py" "$2"\n')
    os.chmod(exe, 0o755)
    neg = dict(ORA, nome="neg001_kit581", tipo="negativa", video=[], eventi=[], box_dario=None, atteso=None,
               evento=None, inizio="2026-11-13 21:00:00")
    cieco = dict(ORA, nome="pos002_kit581", catena=False, fuori_catena="parte cieca", canale=1,
                 video=[dict(ORA["video"][0], canale=1)])
    cfg = {"pc": "*", "finestra": {"dalle": "00:00", "alle": "00:00"}, "posti_drive": ["scorta35_1.zip"], "gb_liberi_min": 0.3,
           "limiti": {"mb_parte_drive": 6.0}, "ore": [ORA, cieco, neg]}
    vecchie = {k: os.environ.get(k) for k in ("HOME", "PROVA_QUI", "PYTHONPATH")}
    os.environ.update(HOME=casa, PROVA_QUI=base, PYTHONPATH=os.pathsep.join([os.path.abspath(SCRIPTS), base]))
    vecchio_argv, vecchio_path = sys.argv, list(sys.path)
    try:
        sys.argv = ["compito.py", comp]
        sys.path.insert(0, base)
        src = open(os.path.join(comp, "compito.py"), encoding="utf-8").read()
        g = {"__name__": "ponte", "__file__": os.path.join(comp, "compito.py")}
        exec(compile(src[:src.index("\nt_fine = time.time() + DURATA")], "compito.py", "exec"), g)   # noqa: S102
        g["sys"] = type("S", (), {"executable": exe, "path": sys.path, "argv": sys.argv})
        g["t_fine"] = time.time() + 3600
        g["time"] = _Tempo()
        g["compito_nuovo_su_drive"] = lambda: False
        g["subprocess"] = _Sottoprocessi()   # creationflags c'e' solo su Windows

        def qwen_finto():
            with zipfile.ZipFile(os.path.join(comp, "carte.zip")) as zz:
                carte = json.loads(zz.read("carte.json"))
                nomi = zz.namelist()
            assert all(c["id"] + s in nomi for c in carte for s in ("_prima.jpg", "_dopo.jpg", ".jpg"))
            d = os.path.join(casa, "kr_vlm", "uscita")
            os.makedirs(d, exist_ok=True)
            gz = [{"id": c["id"], "risposta": "giusto", "testo": '{"prima": "asphalt", "dopo": "black bag", '
                   '"risposta": "waste", "sicuro": true}', "sicuro": True} for c in carte]
            json.dump({"giudizi": gz, "totale_s": 1.0}, open(os.path.join(d, "giudizi_Qwen3-VL-4B-Instruct_v3_c35.json"), "w"))
            json.dump(json.load(open(os.path.join(comp, "prove.json"))), open(os.path.join(base, "prove_viste.json"), "w"))
        g["parti_qwen"] = qwen_finto
        g["lavoro_scorta"](cfg)
    finally:
        sys.argv, sys.path[:] = vecchio_argv, vecchio_path
        for k, v in vecchie.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return base, casa, comp


if shutil.which("ffmpeg"):
    base, casa, comp = ponte_finto()
    try:
        assert os.path.isdir(comp)
        U = os.path.join(comp, "uscita")
        out = json.load(open(os.path.join(U, "scorta.json")))
        es = {x["nome"]: x for x in out["ore"]}
        ok(set(es) == {"pos001_kit581", "pos002_kit581", "neg001_kit581"} and all(x["esito"] == "fatto" for x in es.values()),
           f"ponte: tre ore fatte nei processi a parte ({ {k: v['esito'] for k, v in es.items()} })")
        pc = os.path.join(casa, "kr_lavori", "scorta", "p2p_ponte35")
        ok(len(os.listdir(os.path.join(pc, "pos001_kit581", "minuti"))) == 72
           and any(f.endswith(".mp4") for f in os.listdir(os.path.join(pc, "pos001_kit581", "video"))),
           "ponte: miniature e video restano sul PC, nella cartella della scorta")
        x = json.load(open(os.path.join(U, "scorta", "pos001_kit581", "ora.json")))
        ok(x["catena"]["fatta"] and x["catena"]["candidati"] and x["catena"]["candidati"][0]["vero"],
           f"ponte: la catena trova l'abbandono con miniature H.264 vere ({x['catena'].get('esito')})")
        ok(set(x["video"][0]["fotogrammi"].values()) == {"e581_prima.jpg", "e581_dopo.jpg"}, "ponte: i due fotogrammi dal video")
        x2 = json.load(open(os.path.join(U, "scorta", "pos002_kit581", "ora.json")))
        ok(not x2["catena"]["fatta"] and x2["video"][0]["esito"] == "fatto", "ponte: l'ora fuori catena salva solo la scorta")
        ok(len(out["parti"]) == 2 and all(p["ok"] for p in out["parti"][:1]) and not out["parti"][1]["ok"]
           and sorted(o for p in out["parti"] for o in p["ore"]) == sorted(es)
           and os.path.exists(os.path.join(base, "drive", "scorta35_1.zip")),
           f"ponte: le miniature in parti; la parte senza segnaposto resta sul PC ({[(p['posto'], p['ok']) for p in out['parti']]})")
        with zipfile.ZipFile(os.path.join(base, "drive", "scorta35_1.zip")) as zz:
            nomi = zz.namelist()
        ok(sum(1 for n in nomi if "/minuti/" in n) == 72 * len(out["parti"][0]["ore"])
           and all(f"{o}/ora.json" in nomi for o in out["parti"][0]["ore"]), "ponte: nella parte miniature e ora.json")
        ok(os.path.getsize(os.path.join(base, "drive", "scorta35_1.zip")) < 6.2e6, "ponte: la parte non passa il tetto")
        cat = json.load(open(os.path.join(U, "catena.json")))
        ok(cat["qwen_esito"] == "fatto" and cat["carte_giudicate"] >= 1 and cat["conti"]["positive"]["primo_dopo_qwen"] == 1,
           f"ponte: Qwen sulle carte e catena.json ({cat['qwen_esito']}, {cat['carte_giudicate']} carte)")
        ok(json.load(open(os.path.join(base, "prove_viste.json"))) == [list(p) for p in sc.CATENA["qwen"]],
           "ponte: prove.json per vlm.py con l'etichetta c35")
        ok(os.path.exists(os.path.join(U, "catena_giudizi_Qwen3-VL-4B-Instruct_v3_c35.json")),
           "ponte: i giudizi di Qwen anche nell'uscita")
        grosso = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(U) for f in fs) / 1e6
        ok(grosso < 3, f"ponte: l'uscita del compito resta piccola ({grosso:.2f} MB)")
    finally:
        shutil.rmtree(base, ignore_errors=True)
else:
    print("--   ffmpeg non c'e': salto la prova del ponte")

print("TUTTE VERDI" if not fallite else f"{len(fallite)} FALLITE: " + "; ".join(fallite))
sys.exit(1 if fallite else 0)
