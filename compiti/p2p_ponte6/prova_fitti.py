"""Prove a tavolino dei fotogrammi in più (compito p2p_ponte44, ponte 0.25.0): fitti.py 0.1.0, prepara_fitti.py 0.1.0,
scorta.py 0.2.0 (cfg["fitti"], ordine_dato) e giro_da di compito.py. Niente rete, niente DLL: un registratore finto
dà le miniature di una scena in cui al minuto 30 passa una persona davanti ai cassonetti (minuti agitati).
Uso: python3 prova_fitti.py   (kit_rifiuti.py da KR_SCRIPTS, se no da ../../../kit-rifiuti-programma/scripts)
version: 0.2.0 (20/11/2026): prepara_fitti 0.2.0 (l'elenco rifatto alla partenza: giorni_passati, margini di adesso,
fonte_da, cfg_da_fonte con op=stato e senza) e il ponte vero da fitti_fonte.json (lavoro_fitti_fresco, ponte 0.26.0).
0.1.0 (20/11/2026)
"""
import ast
import datetime
import json
import os
import shutil
import sys
import tempfile
import types

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get("KR_SCRIPTS") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")
sys.path.insert(0, QUI)
sys.path.insert(0, SCRIPTS)
import cv2                    # noqa: E402
import kit_rifiuti as kr      # noqa: E402
import fitti as ft            # noqa: E402
import prepara_fitti as pft   # noqa: E402
import scorta as sc           # noqa: E402

fallite = []
D = datetime.datetime


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


def sec(x):
    return datetime.timedelta(seconds=x)


# ------------------------------------------------------------------ funzioni pure
ok(ft.intervalli_agitati({5}, 72) == [4, 5] and ft.intervalli_agitati({0, 71}, 72) == [0, 70]
   and ft.intervalli_agitati(set(), 72) == [], "intervalli attorno ai minuti agitati, dentro la fila")
T = D(2026, 11, 3, 10, 0)
ts = [T + datetime.timedelta(minutes=k) for k in range(72)]
tt = ft.tempi_fitti(ts, [3], 6)
ok([t for _, t in tt] == [ts[3] + sec(10 * k) for k in range(1, 6)] and all(j == 3 for j, _ in tt),
   "6 al minuto: 5 in più ogni 10 s, esclusi i minuti")
ok([t for _, t in ft.tempi_fitti(ts, [0], 4)] == [ts[0] + sec(15), ts[0] + sec(30), ts[0] + sec(45)], "4 al minuto: ogni 15 s")
ok(ft.cfg_fitti({"per_minuto": 40, "modo": "x"}) == {"per_minuto": 6, "modo": "agitati"}
   and ft.cfg_fitti({"per_minuto": 4, "modo": "tutti"}) == {"per_minuto": 4, "modo": "tutti"}, "opzioni sbagliate: il difetto")
ok(ft.scarto_s(T + sec(10), "10:00:10") == 0 and ft.scarto_s(T + sec(10), "2026-11-03 10:00:00") == -10
   and ft.scarto_s(T, None) is None, "scarto fra l'ora chiesta e quella del fotogramma")
# prepara_fitti
ore = [{"nome": "a", "uid": "U1", "canale": 0, "inizio": "2026-11-07 17:10:36", "tipo": "positiva", "video": [1], "catena": True},
       {"nome": "b", "uid": "U1", "canale": 1, "inizio": "2026-11-03 10:00:00", "tipo": "negativa"},
       {"nome": "c", "uid": "U2", "canale": 0, "inizio": "2026-11-05 10:00:00", "tipo": "positiva"},
       {"nome": "d", "uid": "U3", "canale": 0, "inizio": "2026-11-05 10:00:00", "tipo": "positiva"}]
arch = [{"uid": "U1", "canale": 0, "primo": "2026-11-07 09:30"}, {"uid": "U1", "canale": 1, "primo": "2026-11-04 00:00"},
        {"uid": "U2", "canale": 0, "primo": "2026-11-04 10:00"}]
m = dict((o["nome"], v) for o, v in pft.margini(ore, arch))
ok(m == {"a": 0.32, "b": -0.58, "c": 1.0, "d": None}, f"margini dall'archivio ({m})")
s = pft.scegli(ore, arch, perse=["c"])
ok([x["nome"] for x in s] == ["a", "c"] and s[0]["video"] == [] and s[0]["catena"] is False and s[1]["persa"],
   "scegli: solo le ore ancora sul disco, per margine, senza video ne' catena")
ok(pft.stima_mb(10, "tutti", 6) == 213.5 and pft.stima_mb(10, "agitati", 6, 12) == 66.0
   and pft.stima_mb(10, "agitati", 6, 12, minuti=False) == 30.0, "stima dei MB")
ok(s[1].get("fitti_modo") == "tutti" and "fitti_modo" not in s[0], "le ore perse: tutti gli intervalli")
# 0.2.0: l'elenco rifatto alla partenza
UTC = datetime.timezone.utc
ADESSO_U = D(2026, 11, 22, 23, 30, tzinfo=UTC)
ok(round(pft.giorni_passati("2026-11-20T23:30:00.000Z", ADESSO_U), 3) == 2.0 and pft.giorni_passati(None, ADESSO_U) == 0
   and pft.giorni_passati("2026-11-23T00:00:00Z", ADESSO_U) == 0 and pft.giorni_passati("x", ADESSO_U) == 0
   and pft.giorni_passati("2026-11-20T23:30:00Z", None) == 0, "giorni passati da letto_il, mai negativi")
arch2 = [dict(a, letto_il="2026-11-22T11:30:00Z") for a in arch]
m2 = dict((o["nome"], v) for o, v in pft.margini(ore, arch2, ADESSO_U))
ok(m2 == {"a": -0.18, "b": -1.08, "c": 0.5, "d": None}, f"margini di adesso: meno il mezzo giorno da letto_il ({m2})")
ok(dict((o["nome"], v) for o, v in pft.margini(ore, arch2)) == m, "senza adesso i margini di prima")
fo = pft.fonte_da([dict(o, persa=True, fitti_modo="tutti", margine_giorni=mg) for o, mg in zip(ore, (3.0, 0.4, 2.0, None))]
                  + [{"nome": "z", "uid": "U1", "canale": 0, "inizio": "2026-11-09 10:00:00", "tipo": "negativa"}],
                  ["z"], ["c"], nome="p2p_ponte45", parti=3, stato_letto="2026-11-20T10:28:00Z", adesso=D(2026, 11, 20, 19))
ok([o["nome"] for o in fo["ore"]] == ["a", "b", "c", "d"] and fo["gia_fatte"] == ["z"] and fo["perse"] == ["c"]
   and not any("persa" in o or "fitti_modo" in o for o in fo["ore"]) and fo["stato_letto"] == "2026-11-20T10:28:00Z",
   "fonte: le candidate senza le gia' fatte, coi margini di allora")
c1 = pft.cfg_da_fonte(fo, {"ora": "2026-11-22T22:00:00Z", "archivio": [dict(a, letto_il="2026-11-22T23:30:00Z") for a in arch]},
                      ADESSO_U)
ok([o["nome"] for o in c1["ore"]] == ["a", "c"] and c1["ore"][1]["persa"] and c1["ore"][1]["fitti_modo"] == "tutti"
   and c1["rifatto_con"].startswith("op=stato") and c1["stato_letto"] == "2026-11-22T22:00:00Z" and c1["candidate"] == 4
   and c1["posti_drive"] == ["fitti45_1.zip", "fitti45_2.zip", "fitti45_3.zip"] and c1["pc"] == "COMPUTERONE"
   and c1["ordine_dato"] and c1["fitti"] == {"modo": "agitati", "per_minuto": 6}, "cfg_da_fonte con op=stato fresco")
c2 = pft.cfg_da_fonte(dict(fo, gia_fatte=["z", "a"]), {"ora": "x", "archivio": arch2}, ADESSO_U)
ok([o["nome"] for o in c2["ore"]] == ["c"], "le gia' fatte non tornano, e un'ora uscita dal disco nel frattempo neanche")
c3 = pft.cfg_da_fonte(fo, None, ADESSO_U)
ok([(o["nome"], o["margine_giorni"]) for o in c3["ore"]] == [("a", 0.46)] and "meno 2.54 giorni" in c3["rifatto_con"],
   f"senza op=stato: i margini della fonte meno i giorni passati ({[(o['nome'], o['margine_giorni']) for o in c3['ore']]}, {c3['rifatto_con']})")
c4 = pft.cfg_da_fonte(dict(fo, gb_liberi_min=0.3, limiti={"ore_di_lavoro": 4}), {"archivio": []}, ADESSO_U)
ok(c4["gb_liberi_min"] == 0.3 and c4["limiti"]["ore_di_lavoro"] == 4 and c4["limiti"]["mb_parte_drive"] == 170.0
   and "non letto" in c4["rifatto_con"], "la fonte cambia disco e limiti; archivio vuoto = come senza stato")
# giro_da di compito.py (senza eseguire il compito)
src = open(os.path.join(QUI, "compito.py"), encoding="utf-8").read()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "giro_da")
g = {}
exec(compile(ast.Module([fn], []), "giro_da", "exec"), g)   # noqa: S102 - il nostro codice
ok(g["giro_da"]({"giro": False}) is False and g["giro_da"]({"durata_ore": 5}) is True and g["giro_da"](None) is True,
   "ponte.json «giro»: false spegne il giro, il difetto lo tiene")

# ------------------------------------------------------------------ un'ora col registratore finto
H, W = 576, 704
rnd = np.random.default_rng(3)
SFONDO = np.clip(rnd.normal(120, 20, (H // 8, W // 8, 3)), 0, 255).astype(np.uint8).repeat(8, 0).repeat(8, 1)
INIZIO = D(2026, 11, 3, 10, 0)
ZONA = {"riquadri": [[0.5, 0.4, 0.3, 0.3]], "escludi": []}


def scena(t):
    f = SFONDO.astype(np.int16).copy()
    if INIZIO + datetime.timedelta(minutes=30) <= t < INIZIO + datetime.timedelta(minutes=31, seconds=30):
        f[250:420, 380:440] = np.array([60, 60, 200], np.int16)   # una persona davanti ai cassonetti
    return np.clip(f + rnd.integers(-2, 3, f.shape), 0, 255).astype(np.uint8)


class Finto:
    def __init__(self, primo=D(2026, 10, 30)):
        self.primo, self.chieste = primo, []

    def canali(self):
        return [(0, 100, "CH1")]

    def intervallo(self, h):
        return self.primo, D(2026, 11, 20)

    def miniatura(self, h, t, attesa=12):
        self.chieste.append(t)
        return {"dati": t.isoformat().encode() + b"\0" * 49000, "formato": "H.264", "misura": "704x576",
                "ora_video": t.strftime("%H:%M:%S")}

    def chiudi(self):
        pass


def mezzi(fin, cartella, kr_=kr):
    return {"nuovo": lambda: fin, "collega": lambda reg: (True, "collegato (finto)"), "kr": kr_, "cv2": cv2,
            "decodifica": lambda dati, formato, grezzo: scena(D.fromisoformat(dati.split(b"\0")[0].decode())),
            "fotogrammi": lambda mp4: [], "uscita": os.path.join(cartella, "pc"), "drive": os.path.join(cartella, "drive"),
            "grezzi": os.path.join(cartella, "grezzi"), "cimitero": [], "sposta": shutil.move,
            "taglia": lambda *a: True, "foglio": lambda *a: None, "fotogramma": lambda *a: None, "ffmpeg": "ffmpeg"}


ORA = {"nome": "neg900_kit411", "tipo": "negativa", "kit": 411, "uid": "X" * 20, "canale": 0,
       "inizio": INIZIO.strftime("%Y-%m-%d %H:%M:%S"), "zona": ZONA, "notte": False, "video": [], "catena": False,
       "budget": "tutto"}
tmp = tempfile.mkdtemp(prefix="prova_fitti_")
try:
    fin = Finto()
    mz = mezzi(fin, os.path.join(tmp, "a"))
    x = sc.lavora_ora(ORA, {"fitti": {"modo": "agitati", "per_minuto": 6}}, mz, lambda r: None)
    f = x.get("fitti") or {}
    nf = len(os.listdir(os.path.join(mz["uscita"], "fitti")))
    ok(x["esito"] == "fatto" and len(os.listdir(os.path.join(mz["uscita"], "minuti"))) == 72, "le 72 miniature dei minuti")
    ok(f.get("esito") == "fatto" and 2 <= f["intervalli"] <= 8 and f["richieste"] == 5 * f["intervalli"]
       and f["arrivate"] == f["richieste"] == nf, f"agitati: in più solo attorno alla persona ({f.get('come')}, "
       f"{f.get('intervalli')} intervalli, {nf} file)")
    r5 = ft.fai(dict(ORA, fitti_modo="tutti"), {"modo": "agitati"}, mezzi(Finto(), os.path.join(tmp, "e")),
                mz["uscita"])
    ok(r5["modo"] == "tutti" and r5["richieste"] == 355, "fitti_modo dell'ora vale più di quello del compito")
    ok(abs(x["conti"]["mb_fitti"] - f["arrivate"] * 0.049) < 0.01 and x["conti"]["mb"] > x["conti"]["mb_fitti"] + 3,
       f"i MB dei fitti contati nell'ora ({x['conti']})")
    ok(f["scarti_s"]["zero"] == f["arrivate"], "lo scarto dall'ora vera del fotogramma: zero col finto")
    pers = [t for t in fin.chieste if t.second % 60 and INIZIO + datetime.timedelta(minutes=28) <= t <= INIZIO + datetime.timedelta(minutes=33)]
    ok(len(pers) == f["richieste"], "le miniature in più cadono tutte attorno al minuto 30")
    fin2 = Finto()
    mz2 = mezzi(fin2, os.path.join(tmp, "b"))
    x2 = sc.lavora_ora(ORA, {"fitti": {"modo": "tutti", "per_minuto": 6}}, mz2, lambda r: None)
    ok(x2["fitti"]["richieste"] == 71 * 5 == x2["fitti"]["arrivate"], "tutti: 71 intervalli x 5")
    vecchio = types.SimpleNamespace(**{k: getattr(kr, k) for k in ("maschera_zone", "lab_cie", "kit_id") if hasattr(kr, k)})
    fin3 = Finto()
    mz3 = mezzi(fin3, os.path.join(tmp, "c"), vecchio)
    r3 = ft.fai(ORA, {"modo": "agitati"}, dict(mz3, uscita=os.path.join(tmp, "c", "pc")), os.path.join(tmp, "c", "pc"))
    ok(r3.get("esito") == "miniature dei minuti troppo poche: niente fitti", "senza miniature dei minuti: niente fitti")
    shutil.copytree(os.path.join(mz["uscita"], "minuti"), os.path.join(tmp, "c", "pc", "minuti"))
    r3 = ft.fai(ORA, {"modo": "agitati"}, mz3, os.path.join(tmp, "c", "pc"))
    ok(r3["come"].startswith("tutti (minuti_agitati manca") and r3["richieste"] == 355,
       "un kit_rifiuti senza minuti_agitati: tutti, e si scrive")
    fin4 = Finto(primo=D(2026, 11, 10))
    x4 = sc.lavora_ora(ORA, {"fitti": {"modo": "tutti"}}, mezzi(fin4, os.path.join(tmp, "d")), lambda r: None)
    ok(not x4.get("fitti") and not x4["valutabile"] and len(fin4.chieste) == 0, "ora non più sul disco: niente richieste")
    # ordine dato nel giro della scorta
    ore_g = [{"nome": "n1", "tipo": "negativa", "kit": 1}, {"nome": "p1", "tipo": "positiva", "kit": 1}]
    fatte = []

    def lancia(o, s):
        fatte.append(o["nome"])
        return 0, {"nome": o["nome"], "tipo": o["tipo"], "kit": 1, "esito": "fatto", "conti": {"mb": 1}}
    cfg = {"ore": ore_g, "ordine_dato": True, "finestra": {"dalle": "00:00", "alle": "23:59"}}
    sc.giro(cfg, lancia, lambda ore, k: {"parte": k, "ok": True, "ore": ore}, lambda o: 0, lambda o: None,
            adesso=lambda: D(2026, 11, 20, 12))
    ok(fatte == ["n1", "p1"], "ordine_dato: le ore nell'ordine di fitti.json, negative comprese")
    fatte.clear()
    sc.giro(dict(cfg, ordine_dato=False), lancia, lambda ore, k: {"parte": k, "ok": True, "ore": ore}, lambda o: 0,
            lambda o: None, adesso=lambda: D(2026, 11, 20, 12))
    ok(fatte == ["p1", "n1"], "senza ordine_dato: positive prima, come la scorta 35")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ------------------------------------------------------------------ il ponte vero (lavoro_scorta «fitti») col registratore finto
def _da_prova_scorta():
    """Il registratore, la scena, Drive e i tempi finti di prova_scorta.py, senza farne girare le prove."""
    src = open(os.path.join(QUI, "prova_scorta.py"), encoding="utf-8").read()
    nomi = {"FINTO_NVR", "SCENA", "MOV_FINTO", "DRIVE_FINTO", "_Tempo", "_Sottoprocessi"}
    corpo = [n for n in ast.parse(src).body
             if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in nomi for t in n.targets))
             or (isinstance(n, ast.ClassDef) and n.name in nomi)]
    g = {}
    exec(compile(ast.Module(corpo, []), "prova_scorta", "exec"), g)   # noqa: S102 - il nostro codice
    return g


def ponte_finto_fitti():
    import time
    ps = _da_prova_scorta()
    base = tempfile.mkdtemp(prefix="prova_fitti_ponte_")
    casa, comp = os.path.join(base, "casa"), os.path.join(base, "p2p_ponte44")
    os.makedirs(os.path.join(comp, "FocusNetSDK"))
    os.makedirs(casa)
    for f in ("compito.py", "scorta.py", "scorta_lavoro.py", "pilota.py", "dimezza.py", "allunga.py", "fitti.py",
              "prepara_fitti.py"):
        shutil.copy2(os.path.join(QUI, f), comp)
    open(os.path.join(comp, "movimento.py"), "w").write(open(os.path.join(QUI, "movimento.py")).read() + ps["MOV_FINTO"])
    open(os.path.join(comp, "focus_nvr.py"), "w").write(ps["FINTO_NVR"])
    open(os.path.join(base, "prova_scorta_scena.py"), "w").write(ps["SCENA"])
    open(os.path.join(base, "drive_alma.py"), "w").write(ps["DRIVE_FINTO"].replace('"scorta35_"', '"fitti44_"'))
    open(os.path.join(comp, "focus_accesso.txt"), "w").write("*;utente;finta\n")   # password finta della prova
    exe = os.path.join(base, "exe.sh")
    open(exe, "w").write(f'#!/bin/sh\nexec "{sys.executable}" "$2/compito.py" "$2"\n')
    os.chmod(exe, 0o755)
    ora = {"nome": "neg901_kit581", "tipo": "negativa", "kit": 581, "uid": "X" * 20, "canale": 0,
           "inizio": "2026-11-13 21:00:00", "zona": {"riquadri": [[0.6, 0.5, 0.15, 0.15]], "escludi": []},
           "notte": True, "video": [], "catena": False}
    # 0.26.0: da fitti_fonte.json, con op=stato letto alla partenza: neg903 gia' fatta, neg904 uscita dal disco
    fonte = {"pc": "*", "nome": "p2p_ponte44", "parti": 1, "gb_liberi_min": 0.3, "perse": ["neg901_kit581"],
             "gia_fatte": ["neg903_kit581"], "stato_letto": "2026-11-14T10:00:00Z",
             "ore": [dict(ora, nome="neg902_kit581"), ora, dict(ora, nome="neg903_kit581"),
                     dict(ora, nome="neg904_kit581", canale=1)]}
    adesso_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    stato_finto = {"ora": adesso_iso, "archivio": [{"uid": "X" * 20, "canale": 0, "primo": "2026-11-01 00:00", "letto_il": adesso_iso},
                                                   {"uid": "X" * 20, "canale": 1, "primo": "2026-11-14 00:00", "letto_il": adesso_iso}]}
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
        g["time"] = ps["_Tempo"]()
        g["compito_nuovo_su_drive"] = lambda: False
        g["subprocess"] = ps["_Sottoprocessi"]()
        g["leggi_stato"] = lambda: stato_finto
        g["lavoro_fitti_fresco"](fonte)
    finally:
        sys.argv, sys.path[:] = vecchio_argv, vecchio_path
        for k, v in vecchie.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return base, casa, comp


if shutil.which("ffmpeg") and os.path.exists(os.path.join(QUI, "prova_scorta.py")):
    import zipfile
    base, casa, comp = ponte_finto_fitti()
    try:
        U = os.path.join(comp, "uscita")
        sce = json.load(open(os.path.join(U, "fitti_scelte.json")))
        ok([o["nome"] for o in sce["ore"]] == ["neg901_kit581", "neg902_kit581"] and sce["rifatto_con"].startswith("op=stato")
           and sce["candidate"] == 3 and sce["ore"][0]["persa"], f"ponte: l'elenco rifatto alla partenza ({sce['ore']})")
        out = json.load(open(os.path.join(U, "fitti.json")))
        es = {x["nome"]: x for x in out["ore"]}
        ok(list(es) == ["neg901_kit581", "neg902_kit581"] and all(x["esito"] == "fatto" for x in es.values()),
           f"ponte: le due ore fatte nei processi a parte, nell'ordine dato ({ {k: v['esito'] for k, v in es.items()} })")
        x1 = json.load(open(os.path.join(U, "fitti", "neg901_kit581", "ora.json")))
        x2 = json.load(open(os.path.join(U, "fitti", "neg902_kit581", "ora.json")))
        ok(x1["fitti"]["richieste"] == 355 == x1["fitti"]["arrivate"] and x1["fitti"]["modo"] == "tutti",
           f"ponte: l'ora persa con tutti gli intervalli ({x1['fitti'].get('arrivate')})")
        ok(x2["fitti"]["modo"] == "agitati" and x2["fitti"]["richieste"] == 5 * x2["fitti"]["intervalli"]
           and x2["fitti"]["intervalli"] <= 6, f"ponte: l'altra solo attorno ai minuti agitati ({x2['fitti'].get('come')})")
        pc = os.path.join(casa, "kr_lavori", "fitti", "p2p_ponte44")
        ok(len(os.listdir(os.path.join(pc, "neg901_kit581", "fitti"))) == 355, "ponte: le miniature in più restano sul PC")
        with zipfile.ZipFile(os.path.join(base, "drive", "fitti44_1.zip")) as zz:
            nomi = zz.namelist()
        ok(sum(1 for n in nomi if "/fitti/" in n) == 355 + x2["fitti"]["arrivate"] and not any("/minuti/" in n for n in nomi)
           and "neg901_kit581/ora.json" in nomi, "ponte: su Drive le miniature in più e ora.json, non quelle dei minuti")
        ok(not os.path.exists(os.path.join(U, "catena.json")), "ponte: i fitti non fanno catena ne' Qwen")
    finally:
        shutil.rmtree(base, ignore_errors=True)
else:
    print("--   ffmpeg o prova_scorta.py mancano: salto la prova del ponte")

print(f"\n{'TUTTE LE PROVE PASSATE' if not fallite else str(len(fallite)) + ' PROVE FALLITE'}")
sys.exit(1 if fallite else 0)
