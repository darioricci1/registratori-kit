"""Compito vlm (10/11/2026), processo staccato sul COMPUTERONE: aspetta che la RTX 3070 sia libera (l'addestramento dei
sacchi di gpu2 non scrive piu' ~\\kr_gpu\\vivo.txt da 20 minuti), prepara un Python suo (~\\kr_vlm, uv), scarica
Qwen3-VL (Apache 2.0) e fa giudicare le carte di Scorri (carte/): prima 8B in 4 bit, poi 4B in 4 bit, poi 2B.
Risultati su Drive in vlm_pcN.zip ogni 30 minuti e alla fine.
version: 0.3.0 (11/11/2026) - solo il 4B in 4 bit, con la domanda nuova (v2, v2d col primo piano del riquadro) e con
quella del 10/11 (v1) sulle stesse 173 carte: giudizi_Qwen3-VL-4B-Instruct_<v>.json. Niente 2B (risponde fuori elenco)
e niente 8B (sul si'/no come il 4B, a tre volte il tempo). Prima le domande nuove, cosi' se si ferma a meta' il
confronto con la v1 del 10/11 c'e' gia'.
0.2.1 (10/11/2026, sera) - torch 2.6 (transformers 5 non parte con la 2.5: «PyTorch >= 2.6 is required»).
0.2.0 (10/11/2026, sera) - non aspetta piu' la scheda libera: la RTX 3070 da 8 GB la divide con Kit_Rifiuti
(RF-DETR in DirectML usa poco); parte dal 4B in 4 bit (circa 3 GB), poi l'8B; se manca uv lo scarica da GitHub.
Stamattina la 0.1.0 aspettava una scheda che non si liberava mai (Dario: «perche' non partiamo da qwen3-vl?»)."""
import glob
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
import zipfile

C = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
CASA = os.path.expanduser("~")
G = os.path.join(CASA, "kr_vlm")
os.makedirs(G, exist_ok=True)
U = os.path.join(G, "uscita")
os.makedirs(U, exist_ok=True)
REG = os.path.join(U, "vlm.txt")
PY = os.path.join(G, "venv", "Scripts", "python.exe")
UV = os.path.join(CASA, "kr_gpu", "uv.exe")
FINE = [False]
NASCOSTO = 0x08000000 if os.name == "nt" else 0
PROVE = [("Qwen/Qwen3-VL-4B-Instruct", "nf4", "v2"), ("Qwen/Qwen3-VL-4B-Instruct", "nf4", "v2d"),
         ("Qwen/Qwen3-VL-4B-Instruct", "nf4", "v1")]


def scrivi(t):
    with open(REG, "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%d/%m %H:%M:%S ") + str(t) + "\n")
    open(os.path.join(G, "vivo.txt"), "w").write(str(time.time()))


def esegui(cmd, log, env=None, cwd=None):
    scrivi("> " + " ".join(cmd)[:300])
    with open(os.path.join(U, log), "a", encoding="utf-8", errors="replace") as fh:
        p = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=cwd, creationflags=NASCOSTO)
    scrivi(f"  esito {p.returncode}")
    return p.returncode


def manda():
    try:
        import drive_alma
        z = os.path.join(G, "vlm_risultato.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zz:
            for f in glob.glob(os.path.join(U, "*")):
                if os.path.isfile(f) and os.path.getsize(f) < 50e6:
                    zz.write(f, os.path.basename(f))
        scrivi(f"Drive: {drive_alma.carica_del_pc(z, 'vlm')}")
    except Exception as ex:   # noqa: BLE001
        scrivi(f"Drive: {type(ex).__name__}: {ex}")


def ogni_mezzora():
    while not FINE[0]:
        for _ in range(180):
            if FINE[0]:
                return
            open(os.path.join(G, "vivo.txt"), "w").write(str(time.time()))
            time.sleep(10)
        manda()


def gpu_libera():
    return True   # 0.2.0: si divide la scheda


def gpu_libera_vecchia():
    f = os.path.join(CASA, "kr_gpu", "vivo.txt")
    try:
        return time.time() - float(open(f).read().strip()) > 20 * 60
    except (OSError, ValueError):
        return True


try:
    threading.Thread(target=ogni_mezzora, daemon=True).start()
    scrivi("parto: " + C)
    t0 = time.time()
    while not gpu_libera() and time.time() - t0 < 8 * 3600:
        time.sleep(120)
    scrivi(f"scheda libera dopo {(time.time() - t0) / 60:.0f} minuti")
    env = {**os.environ, "UV_PYTHON_INSTALL_DIR": os.path.join(CASA, "kr_gpu", "python"),
           "UV_CACHE_DIR": os.path.join(CASA, "kr_gpu", "cache"), "HF_HOME": os.path.join(G, "hf"),
           "PYTHONIOENCODING": "utf-8", "HF_HUB_DISABLE_SYMLINKS_WARNING": "1"}
    if not os.path.exists(UV):   # 0.2.0: uv da GitHub se il compito gpu2 non l'ha lasciato
        import io
        import urllib.request
        os.makedirs(os.path.dirname(UV), exist_ok=True)
        dati = urllib.request.urlopen("https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip", timeout=300).read()
        with zipfile.ZipFile(io.BytesIO(dati)) as zz:
            for n in zz.namelist():
                if n.endswith("uv.exe"):
                    open(UV, "wb").write(zz.read(n))
        scrivi(f"uv scaricato: {os.path.exists(UV)}")
    if not os.path.exists(PY):
        esegui([UV, "venv", os.path.join(G, "venv"), "--python", "3.11"], "installa.txt", env)
    esegui([UV, "pip", "install", "--python", PY, "torch==2.6.0", "torchvision==0.21.0",
            "--index-url", "https://download.pytorch.org/whl/cu124"], "installa.txt", env)
    esegui([UV, "pip", "install", "--python", PY, "transformers>=4.57.1", "accelerate", "bitsandbytes>=0.45",
            "pillow", "huggingface_hub"], "installa.txt", env)
    out = subprocess.run([PY, "-c", "import torch,transformers;print(torch.__version__, transformers.__version__, "
                          "torch.cuda.is_available())"], capture_output=True, text=True, creationflags=NASCOSTO, env=env)
    scrivi("Python: " + (out.stdout + out.stderr).strip()[-400:])
    carte = os.path.join(C, "carte")
    if not os.path.isdir(carte):
        with zipfile.ZipFile(os.path.join(C, "carte.zip")) as zz:
            zz.extractall(carte)
    for nome, modo, domanda in PROVE:
        corto = nome.split("/")[-1] + "_" + domanda
        esegui([PY, os.path.join(C, "vlm_giudica.py"), carte, os.path.join(U, f"giudizi_{corto}.json"), nome, modo,
                "--prompt", domanda], f"giudica_{corto}.txt", env)
        manda()
    scrivi("fatto")
except BaseException:   # noqa: BLE001
    scrivi("ERRORE:\n" + traceback.format_exc()[-2500:])
finally:
    FINE[0] = True
    manda()
