"""Compito p2p_ponte1 (10/11/2026, Dario: «voglio provare il P2P dal PC dell'ufficio, in una pagina online»).
Il PC fa da ponte fra la pagina https://prova-nvr-remoto.vercel.app e i registratori Focus dei kit, col P2P della libreria
FocusNetSDK (gratis, niente traffico RMS). Ogni 15 secondi chiede alla pagina se c'e' una prova da fare; per ogni prova:
collegamento P2P con l'UID, modello, canali, ore registrate oggi, 15 secondi scaricati dall'ultimo minuto registrato e
un fotogramma JPEG; rimanda tutto alla pagina. Gira 10 ore, poi si chiude da solo.
Le credenziali: focus_accesso.txt (righe indirizzo;utente;password, «*» vale per tutti) nella cartella del compito o
accanto a Kit_Rifiuti. Non escono dal PC: alla pagina arriva solo l'esito.
version: 0.1.0"""
import base64
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request

C = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
sys.path.insert(0, C)
U = os.path.join(C, "uscita"); os.makedirs(U, exist_ok=True)
AV = open(os.path.join(U, "avanzamento.txt"), "a", encoding="utf-8")
API = "https://prova-nvr-remoto.vercel.app/api/p2p"
DESTINATARIO = "https://mappakit.alma/nvr-remoto"
VERSIONE = "p2p_ponte 0.1.0"
DURATA = 10 * 3600
PC = os.environ.get("COMPUTERNAME", "PC")[:40]


def av(t):
    AV.write(time.strftime("%H:%M:%S ") + t + "\n"); AV.flush()


_big = {"t": "", "fino": 0}


def biglietto():
    if _big["t"] and time.time() < _big["fino"]:
        return _big["t"]
    import drive_alma
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    chiave = drive_alma.file_chiave((C, os.path.dirname(sys.executable)))
    cred = service_account.IDTokenCredentials.from_service_account_file(chiave, target_audience=DESTINATARIO)
    cred.refresh(Request())
    _big.update(t=cred.token, fino=time.time() + 45 * 60)
    return cred.token


def chiama(op, dati):
    req = urllib.request.Request(f"{API}?op={op}", data=json.dumps(dati).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + biglietto(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def credenziali(uid):
    """(utente, password) per quell'UID: la riga con l'UID, se no la riga «*»."""
    tutte, generica = {}, None
    for d in (C, os.path.dirname(sys.executable), os.path.dirname(os.path.dirname(sys.executable)), os.path.expanduser("~")):
        f = os.path.join(d, "focus_accesso.txt")
        if not os.path.exists(f):
            continue
        for riga in open(f, encoding="utf-8", errors="replace"):
            p = [x.strip() for x in riga.strip().split(";")]
            if len(p) >= 3 and p[0]:
                if p[0] == "*":
                    generica = generica or (p[1], p[2])
                else:
                    tutte.setdefault(p[0].upper(), (p[1], p[2]))
    return tutte.get(uid.upper()) or generica


def ffmpeg():
    return shutil.which("ffmpeg") or os.path.join(getattr(sys, "_MEIPASS", ""), "ffmpeg.exe")


def prova(r):
    import focus_nvr as fn
    uid = r["uid"]
    es = {"pc": PC}
    cr = credenziali(uid)
    if not cr:
        return False, {"errore": "sul PC manca focus_accesso.txt con utente e password dei registratori"}, None
    foto = None
    with fn.Registratore(os.path.join(C, "FocusNetSDK"), log=lambda *_: None) as reg:
        t0 = time.time()
        ok, testo = reg.collega(uid, cr[0], cr[1], 9010, True, attesa=40)
        es["collegamento"] = testo
        es["secondi_collegamento"] = round(time.time() - t0, 1)
        if "(" in testo:
            es["modo"] = testo.split("(", 1)[1].rstrip(")")
        if not ok:
            return False, es, None
        es["registratore"] = reg.info()
        oggi = datetime.datetime.combine(datetime.date.today(), datetime.time())
        canali, scelta = [], None
        for num, h, tit in reg.canali():
            tr = reg.minuti_registrati(h, oggi) or []
            ultimo = max((t[1] for t in tr), default=None)
            canali.append({"numero": num, "titolo": tit, "registrato_oggi": fn.descrivi_tratti(tr)[:200] if tr else "niente oggi"})
            if (r.get("canale") in (None, num)) and ultimo is not None and (scelta is None or ultimo > scelta[2]):
                scelta = (num, h, ultimo)
        es["canali"] = canali
        if scelta is None:
            es["nota"] = "nessuna registrazione di oggi da scaricare"
            return True, es, None
        num, h, ultimo = scelta
        inizio = oggi + datetime.timedelta(minutes=max(0, ultimo - 2))   # il minuto prima dell'ultimo, che puo' essere ancora in scrittura
        t1 = time.time()
        res = reg.scarica(num, h, inizio, 15, os.path.join(U, "video"), ffmpeg=ffmpeg())
        mb = res.get("mb")
        es["scarico"] = (f"canale {num}, 15 s dalle {inizio:%H:%M}: {mb} MB in {time.time() - t1:.0f} s"
                         + (f" ({res['errore']})" if res.get("errore") else ""))
        f = res.get("file")
        if f and os.path.exists(f):
            jpg = os.path.join(U, f"foto_{r['id']}.jpg")
            subprocess.run([ffmpeg(), "-v", "error", "-y", "-ss", "2", "-i", f, "-frames:v", "1", "-vf", "scale=960:-2",
                            "-q:v", "4", jpg], capture_output=True, timeout=120, creationflags=0x08000000)
            if os.path.exists(jpg):
                foto = base64.b64encode(open(jpg, "rb").read()).decode()
            try:
                os.remove(f)
            except OSError:
                pass
    return True, es, foto


t_fine = time.time() + DURATA
av(f"parto: {VERSIONE} sul PC {PC}, ascolto fino alle {time.strftime('%H:%M', time.localtime(t_fine))}")
errori = 0
while time.time() < t_fine:
    try:
        d = chiama("prendi", {"pc": PC, "versione": VERSIONE})
        errori = 0
        r = d.get("richiesta")
        if not r:
            time.sleep(15)
            continue
        av(f"prova {r['id']} ({r.get('kit') or '-'})")
        try:
            ok, es, foto = prova(r)
        except Exception as ex:   # noqa: BLE001
            ok, es, foto = False, {"errore": f"{type(ex).__name__}: {str(ex)[:300]}"}, None
            av(traceback.format_exc()[-1500:])
        chiama("esito", {"pc": PC, "versione": VERSIONE, "id": r["id"], "ok": ok, "esito": es, "foto": foto})
        av(f"prova {r['id']}: {'ok' if ok else 'fallita'} - {es.get('collegamento') or es.get('errore')}")
    except Exception as ex:   # noqa: BLE001
        errori += 1
        if errori in (1, 10, 100):
            av(f"pagina non raggiunta ({errori}): {type(ex).__name__}: {str(ex)[:200]}")
        time.sleep(min(300, 15 * errori))
av("fatto")
