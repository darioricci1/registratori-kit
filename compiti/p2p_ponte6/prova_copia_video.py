"""Prove a tavolino della copia dei video nell'uscita (ponte 0.24.0, allunga.py 0.2.0): le 7 «ore da guardare» di
video.html con "copia_video": true. Il lavoro_allunga vero del ponte (le definizioni fino all'ascolto, come
allunga_lavoro.py), nel filo del ponte, con lavora_evento finto che fa mp4 veri con ffmpeg; la compressione e' quella
vera del ponte. Poi il ponte rilanciato non rifa' gli eventi gia' finiti. Niente rete, niente DLL.
Uso: python3 prova_copia_video.py
version: 0.1.0 (19/11/2026)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import allunga as al   # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


# --- gia_fatto (pura)
ok(not al.gia_fatto({"copia_video": True}, None), "gia_fatto: niente di prima, si fa")
ok(not al.gia_fatto({"copia_video": True}, {"esito": "fatto"}, 0), "gia_fatto: fatto ma senza video in uscita, si rifa'")
ok(al.gia_fatto({"copia_video": True}, {"esito": "fatto"}, 2), "gia_fatto: fatto coi video, non si rifa'")
ok(al.gia_fatto({}, {"esito": "parziale"}), "gia_fatto: senza copia_video basta l'esito")
ok(al.gia_fatto({"copia_video": True}, {"esito": "non piu' sul registratore"}), "gia_fatto: non piu' sul registratore")
ok(not al.gia_fatto({}, {"esito": "fatto", "in_corso": True}), "gia_fatto: in corso, si rifa'")
ok(not al.gia_fatto({}, {"esito": "errore di memoria della libreria"}), "gia_fatto: morto, si rifa'")

# --- le 7 richieste dello scratchpad, se ci sono: il segno c'e' e i tratti sono di 10 minuti su un canale
f7 = os.environ.get("ORE_VERE", "")
if f7 and os.path.exists(f7):
    cfg7 = json.load(open(f7, encoding="utf-8"))
    ev7 = cfg7.get("eventi") or []
    ok(len(ev7) == 7 and all(e.get("copia_video") is True for e in ev7), "le 7 ore da guardare hanno copia_video")
    tr = [al.tratti(e, cfg7.get("prima_s", 300), cfg7.get("dopo_s", 300)) for e in ev7]
    ok(all(tr), "le 7 ore danno dei tratti")

if not shutil.which("ffmpeg"):
    print("--   ffmpeg non c'e': salto le prove coi video")
    sys.exit(1 if fallite else 0)

tmp = tempfile.mkdtemp(prefix="prova_copia_video_")
casa, comp = os.path.join(tmp, "casa"), os.path.join(tmp, "p2p_ponte42")
os.makedirs(casa)
os.makedirs(comp)
json.dump({"durata_ore": 72}, open(os.path.join(comp, "ponte.json"), "w"))
os.environ.update(HOME=casa, USERPROFILE=casa, COMPUTERNAME="COMPUTERONE")
sys.argv[:] = ["compito.py", comp]
src = open(os.path.join(QUI, "compito.py"), encoding="utf-8").read()
pre = src[:src.index("\nt_fine = time.time() + DURATA")]
gp = {"__name__": "ponte", "__file__": os.path.join(comp, "compito.py")}
exec(compile(pre, "compito.py", "exec"), gp)   # noqa: S102 - il nostro codice
ok(gp["VERSIONE"] == "p2p_ponte 0.24.0", f"ponte 0.24.0 ({gp['VERSIONE']})")

fatti = []


def lavora_finto(ev, cfg, mezzi, scrivi, av):
    """Come lavora_evento: gli mp4 in cartella_video (qui ffmpeg testsrc, 20 s a 1920x1080 in mpeg4 grosso)."""
    fatti.append(ev["evento"])
    os.makedirs(mezzi["cartella_video"], exist_ok=True)
    mp4 = os.path.join(mezzi["cartella_video"], f"CH1_intera_{ev['evento']}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=25", "-t", "20",
                    "-c:v", "mpeg4", "-q:v", "2", mp4], check=True)
    os.makedirs(os.path.join(mezzi["cartella_video"], "tmp"), exist_ok=True)
    open(os.path.join(mezzi["cartella_video"], "tmp", "pezzo.mp4"), "w").write("a meta'")
    return {"evento": ev["evento"], "kit": ev.get("kit"), "esito": "fatto" if ev["evento"] != "e3" else "parziale"}


al.lavora_evento = lavora_finto
al.mezzi_veri = lambda sdk, collega, ff, ev, cartella, cim, nofin=0: {"cartella_video": os.path.join(cartella, "video")}
cfg = {"processo_a_parte": False, "pc": "COMPUTERONE",
       "eventi": [{"evento": "e1", "kit": 1, "uid": "U1", "copia_video": True},
                  {"evento": "e2", "kit": 2, "uid": "U2"},
                  {"evento": "e3", "kit": 3, "uid": "U3", "copia_video": True}]}
out = gp["lavoro_allunga"](json.loads(json.dumps(cfg)))
U = os.path.join(comp, "uscita")
ok(fatti == ["e1", "e2", "e3"] and len(out["eventi"]) == 3, f"tre eventi fatti ({fatti})")
for e in ("e1", "e3"):
    v = os.path.join(U, "allunga", e, "video")
    fs = sorted(os.listdir(v)) if os.path.isdir(v) else []
    ok(fs == [f"CH1_intera_{e}.mp4"], f"{e}: l'mp4 nell'uscita, senza quelli a meta' ({fs})")
    j = json.load(open(os.path.join(U, "allunga", e, "video.json")))
    f0 = j["file"][0]
    ok(f0["compresso"] and f0["mb"] < f0["mb_originale"], f"{e}: compresso ({f0['mb_originale']} -> {f0['mb']} MB)")
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width",
                        "-of", "csv=p=0", os.path.join(v, fs[0])], capture_output=True, text=True) if shutil.which("ffprobe") else None
    ok(p is None or p.stdout.strip() == "h264,1280", f"{e}: H.264 a 1280 pixel ({p.stdout.strip() if p else '-'})")
    orig = os.path.join(casa, "kr_lavori", "allunga", "p2p_ponte42", e, "video", f"CH1_intera_{e}.mp4")
    ok(os.path.exists(orig), f"{e}: l'originale resta sul PC")
ok(not os.path.isdir(os.path.join(U, "allunga", "e2", "video")), "e2 senza copia_video: niente video in uscita")
av = open(os.path.join(U, "avanzamento.txt"), encoding="utf-8").read()
ok("e1: 1 video nell'uscita" in av, "una riga nell'avanzamento per i video")

# --- la copia senza compressione quando ffmpeg fallisce
d2 = os.path.join(tmp, "senza")
c = al.copia_video(os.path.join(casa, "kr_lavori", "allunga", "p2p_ponte42", "e1", "video"), d2, lambda a, b: False)
ok(len(c["file"]) == 1 and not c["file"][0]["compresso"] and c["file"][0]["mb"] == c["file"][0]["mb_originale"],
   "comprimi che non riesce: si copia l'originale")

# --- il ponte rilanciato (guardiano): gli eventi finiti non si rifanno, e2 si' (senza video da controllare: fatto)
fatti.clear()
shutil.rmtree(os.path.join(U, "allunga", "e3", "video"))
out2 = gp["lavoro_allunga"](json.loads(json.dumps(cfg)))
ok(fatti == ["e3"], f"rilancio: si rifa' solo e3, che ha perso i video ({fatti})")
ok([x.get("esito") for x in out2["eventi"]] == ["fatto", "fatto", "parziale"], "rilancio: gli esiti di prima restano")
fatti.clear()
gp["lavoro_allunga"](json.loads(json.dumps(cfg)), base=os.path.join(casa, "coda"), nome_uscita="allunga_coda.json")
ok(fatti == ["e1", "e2", "e3"], "la coda di Dario non salta niente (decide lei cosa rifare)")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{'TUTTE VERDI' if not fallite else str(len(fallite)) + ' ROSSE: ' + ', '.join(fallite)}")
sys.exit(1 if fallite else 0)
