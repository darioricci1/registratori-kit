"""Compito p2p_ponte5 (10/11/2026): come p2p_ponte4, piu' gli ODM aperti di ogni kit (scheda ODM dell'Elenco KIT, righe
senza data di chiusura) mandati alla pagina con l'anagrafica, una volta al giorno: le «cose che non tornano» dicono
quando c'e' gia' un ODM aperto (Barbara, 10/11: «e' aperto odm n° 1686 per CH3 non funzionante»).
Prima, p2p_ponte4 (10/11/2026): come p2p_ponte3, ma un giorno che il registratore non dice (domanda senza risposta, per
esempio perche' il collegamento P2P «relay» si chiude dopo 5 minuti) va come «non letto» (null), non come 0; l'archivio
si legge solo dal 27/10 (Dario: «limita al 27/10») e prima delle foto, quando il collegamento e'
fresco. Gira 24 ore su qualunque PC libero.
Prima, p2p_ponte3 (10/11/2026, Dario: «ogni ora una foto di ogni kit e di ogni telecamera, e se si vede o no un'immagine;
e una volta sola, per ogni telecamera di ogni registratore, da che data ha iniziato a registrare e in quali giorni c'e'
contenuto»). Come p2p_ponte2, piu': nel giro, per ogni telecamera che ha registrato oggi, 3 secondi dall'ultimo minuto
registrato, una foto piccola e il giudizio «si vede» / «nera» / «tutta uguale» / «niente»; la prima volta che vede un
registratore legge anche il suo archivio (prima e ultima registrazione di ogni canale e i giorni con registrazioni, mese
per mese). Gira 24 ore.
Prima, p2p_ponte2 (10/11/2026, Dario: «un controllo ogni ora su ogni kit, nelle ultime 24 ore per quanto tempo è stato
online»). Come p2p_ponte1, piu': le prove del giro (priorita 0) sono leggere (collegamento, canali, minuti registrati
di oggi e di ieri, quanti minuti nelle ultime 24 ore per telecamera; niente video), e per il giro si aspetta al massimo
20 secondi la risposta del registratore. Le prove chieste a mano scaricano ancora 15 secondi e fanno la foto.
Gira 24 ore.
Prima, p2p_ponte1 (10/11/2026, Dario: «voglio provare il P2P dal PC dell'ufficio, in una pagina online»).
Il PC fa da ponte fra la pagina https://prova-nvr-remoto.vercel.app e i registratori Focus dei kit, col P2P della libreria
FocusNetSDK (gratis, niente traffico RMS). Ogni 15 secondi chiede alla pagina se c'e' una prova da fare; per ogni prova:
collegamento P2P con l'UID, modello, canali, ore registrate oggi, 15 secondi scaricati dall'ultimo minuto registrato e
un fotogramma JPEG; rimanda tutto alla pagina. Gira 10 ore, poi si chiude da solo.
Le credenziali: focus_accesso.txt (righe indirizzo;utente;password, «*» vale per tutti) nella cartella del compito o
accanto a Kit_Rifiuti. Non escono dal PC: alla pagina arriva solo l'esito.
version: 0.5.0"""
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
VERSIONE = "p2p_ponte 0.5.0"
DURATA = 24 * 3600
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


def credenziali(uid, kit=None):
    """Le (utente, password) da provare per quell'UID, in ordine: la riga con l'UID; poi le righe «*» (per tutti) e «*<200»
    (0.3.4, Dario: «i kit fino a 199 hanno un'altra password»): per un kit sotto il 200 prima quella, per gli altri prima
    quella comune. Le password stanno solo in focus_accesso.txt, accanto al compito o a Kit_Rifiuti."""
    tutte, generiche, vecchie = {}, [], []
    for d in (C, os.path.dirname(sys.executable), os.path.dirname(os.path.dirname(sys.executable)), os.path.expanduser("~")):
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
    lista = ([tutte[uid.upper()]] if uid.upper() in tutte else []) + ordine
    visti, out = set(), []
    for c in lista:
        if c not in visti:
            visti.add(c)
            out.append(c)
    return out


def numero_kit(r):
    """Il numero del kit dalla richiesta («ALEA-Civitella · 136 - Via ...» -> 136), o None."""
    import re
    m = re.search(r"(?:^|·)\s*(\d{1,4})\b", str(r.get("kit") or ""))
    return int(m.group(1)) if m else None


def prova(r):
    """Prova le credenziali in ordine: se il registratore dice «password sbagliata», la prossima."""
    lista = credenziali(r["uid"], numero_kit(r))
    if not lista:
        return False, {"errore": "sul PC manca focus_accesso.txt con utente e password dei registratori"}, None
    for i, cr in enumerate(lista):
        ok, es, foto = prova_con(r, cr)
        if ok or "password" not in str(es.get("collegamento", "")) or i == len(lista) - 1:
            if i:
                es["credenziali"] = f"entrato con la {i + 1}a password provata" if ok else "nessuna password giusta"
            return ok, es, foto
    return False, {"errore": "nessuna credenziale"}, None


def ffmpeg():
    return shutil.which("ffmpeg") or os.path.join(getattr(sys, "_MEIPASS", ""), "ffmpeg.exe")


def prova_con(r, cr):
    import focus_nvr as fn
    uid = r["uid"]
    es = {"pc": PC}
    foto = None
    with fn.Registratore(os.path.join(C, "FocusNetSDK"), log=lambda *_: None) as reg:
        t0 = time.time()
        leggera = r.get("priorita") == 0
        ok, testo = reg.collega(uid, cr[0], cr[1], 9010, True, attesa=12 if leggera else 40)
        es["collegamento"] = testo
        es["secondi_collegamento"] = round(time.time() - t0, 1)
        if "(" in testo:
            es["modo"] = testo.split("(", 1)[1].rstrip(")")
        if not ok:
            return False, es, None
        es["registratore"] = reg.info()
        oggi = datetime.datetime.combine(datetime.date.today(), datetime.time())
        adesso = datetime.datetime.now()
        min_ora = adesso.hour * 60 + adesso.minute
        canali, scelta = [], None
        for num, h, tit in reg.canali():
            tr = reg.minuti_registrati(h, oggi) or []
            ieri = reg.minuti_registrati(h, oggi - datetime.timedelta(days=1)) or []
            ultimo = max((t[1] for t in tr), default=None)
            # minuti registrati nelle ultime 24 ore: oggi fino ad adesso, ieri da quest'ora in poi
            m24 = sum(min(b, min_ora) - a for a, b, _ in tr if a < min_ora) + sum(b - max(a, min_ora) for a, b, _ in ieri if b > min_ora)
            canali.append({"numero": num, "titolo": tit, "registrato_oggi": fn.descrivi_tratti(tr)[:200] if tr else "niente oggi",
                           "ultimo_minuto": ultimo, "minuti_24h": m24})
        es["ora_pc"] = adesso.strftime("%Y-%m-%d %H:%M")
        if leggera:
            es["canali"] = canali
            if r.get("serve_archivio"):   # prima delle foto: il collegamento e' fresco
                es["archivio"] = archivio(reg)
            es["camere"] = foto_camere(reg, oggi, canali, r["id"])
            return True, es, None
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


def giudica_immagine(jpg):
    """(vista, luce, contrasto) di una foto: «nera» se e' quasi tutta scura, «tutta uguale» se non ha dettagli (telecamera
    coperta, appannata, segnale perso), se no «si vede»."""
    import cv2
    import numpy as np
    im = cv2.imdecode(np.frombuffer(open(jpg, "rb").read(), np.uint8), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return "niente", None, None
    luce, contrasto = float(im.mean()), float(im.std())
    if luce < 12:
        return "nera", round(luce, 1), round(contrasto, 1)
    if contrasto < 6:
        return "tutta uguale", round(luce, 1), round(contrasto, 1)
    return "si vede", round(luce, 1), round(contrasto, 1)


def foto_camere(reg, oggi, canali, rid):
    """Per ogni canale: 3 secondi dall'ultimo minuto registrato oggi, una foto da 480 pixel e il giudizio."""
    out = []
    per_num = {num: h for num, h, _ in reg.canali()}
    for c in canali[:9]:
        num, ultimo = c["numero"], c.get("ultimo_minuto")
        if ultimo is None:
            out.append({"canale": num, "vista": "niente", "dalle": "niente registrato oggi"})
            continue
        inizio = oggi + datetime.timedelta(minutes=max(0, ultimo - 2))
        try:
            res = reg.scarica(num, per_num[num], inizio, 3, os.path.join(U, "foto"), attesa_vuoto=15, ffmpeg=ffmpeg())
            f = res.get("file")
            jpg = os.path.join(U, f"cam_{rid}_{num}.jpg")
            if f and os.path.exists(f):
                subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", f, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "6", jpg],
                               capture_output=True, timeout=60, creationflags=0x08000000)
                try:
                    os.remove(f)
                except OSError:
                    pass
            if os.path.exists(jpg):
                vista, luce, contrasto = giudica_immagine(jpg)
                out.append({"canale": num, "vista": vista, "luce": luce, "contrasto": contrasto, "dalle": f"{inizio:%H:%M}",
                            "foto": base64.b64encode(open(jpg, "rb").read()).decode()})
                os.remove(jpg)
            else:
                out.append({"canale": num, "vista": "niente", "dalle": f"{inizio:%H:%M}: scarico non riuscito {res.get('errore') or ''}"[:120]})
        except Exception as ex:   # noqa: BLE001
            out.append({"canale": num, "vista": "niente", "dalle": f"errore {type(ex).__name__}"})
    return out


DAL_ARCHIVIO = datetime.date(2026, 10, 27)   # come la pagina (Dario: «limita al 27/10»)


def archivio(reg):
    """Per ogni canale: la prima e l'ultima registrazione sul disco e, per ogni giorno con registrazioni (dal piu' recente,
    al massimo 90: di piu' il primo giro durerebbe un giorno), i minuti registrati su 1440 (0.3.1, Dario: «una percentuale di completamento per ogni giorno»)."""
    out = []
    oggi = datetime.date.today()
    for num, h, _ in reg.canali():
        rng = reg.intervallo(h)
        if not rng or not rng[0]:
            out.append({"canale": num, "primo": "", "ultimo": "", "giorni": {}})
            continue
        primo, ultimo = rng
        date = []
        m = datetime.date(primo.year, primo.month, 1) if primo.date() > oggi - datetime.timedelta(days=1100) else \
            datetime.date(oggi.year - 3, oggi.month, 1)
        mesi_muti = []   # mesi per cui il registratore non ha risposto: i loro giorni sono «non letti», non vuoti
        while m <= oggi:
            gg = reg.giorni_registrati(h, datetime.datetime(m.year, m.month, 1))
            if gg is None and m >= DAL_ARCHIVIO.replace(day=1):
                mesi_muti.append(m)
            for g in gg or []:
                date.append(datetime.date(m.year, m.month, g))
            m = datetime.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        giorni = {}
        for mm in mesi_muti:
            d = max(mm, DAL_ARCHIVIO)
            while d.month == mm.month and d <= oggi:
                giorni[d.isoformat()] = None
                d += datetime.timedelta(days=1)
        for d in sorted(date, reverse=True):
            if d < DAL_ARCHIVIO:
                break
            tr = reg.minuti_registrati(h, datetime.datetime(d.year, d.month, d.day))
            giorni[d.isoformat()] = None if tr is None else sum(b - a for a, b, _ in tr)   # None = il registratore non ha risposto
        out.append({"canale": num, "primo": f"{primo:%Y-%m-%d %H:%M}", "ultimo": f"{ultimo:%Y-%m-%d %H:%M}",
                    "giorni": giorni, "giorni_totali": len(date)})
    return out


def database_uvms():
    """Il database UVMS piu' recente: nella cartella del NAS «PROGRAMMA Uvms e database» (le copie datate che Barbara
    aggiorna) o nelle cartelle uvms degli utenti di questo PC. Il percorso, o None. Cerca al massimo 5 minuti."""
    import glob
    import string
    t0, trovati = time.time(), []
    radici = [f"{l}:\\" for l in string.ascii_uppercase if l not in "AC" and os.path.isdir(f"{l}:\\")]
    for nas in ("\\\\NAS-VIDEO", "\\\\192.168.100.253"):
        for nome in ("Alma", "ALMA", "Alma_Video", "Dati", "Condivisa", "Comune", "Ufficio"):
            if os.path.isdir(f"{nas}\\{nome}"):
                radici.append(f"{nas}\\{nome}")
    for r in radici:
        for cart, sotto, files in os.walk(r):
            if time.time() - t0 > 300:
                break
            sotto[:] = [x for x in sotto if x.lower() not in ("archivedata", "riprese", "video", "$recycle.bin", "#recycle")]
            if cart.count(os.sep) - r.count(os.sep) > 5:
                sotto[:] = []
            if "uvms" in cart.lower():
                trovati += [os.path.join(cart, f) for f in files if f.lower().endswith(".db") and "uvms" in f.lower()]
    trovati += glob.glob("C:\\Users\\*\\uvms\\*.db")
    buoni = []
    for f in trovati:
        try:
            if open(f, "rb").read(16).startswith(b"SQLite format 3"):
                buoni.append((os.path.getmtime(f), f))
        except OSError:
            pass
    return max(buoni)[1] if buoni else None


def aggiorna_registratori():
    """0.3.2 (Dario: «ogni giorno dovresti andare a vedere questo archivio»): l'elenco dei registratori del database
    UVMS piu' recente va alla pagina (gruppo, nome, UID, modello, canali, firmware; niente password)."""
    import re
    import sqlite3
    f = database_uvms()
    if not f:
        av("database UVMS non trovato")
        return
    con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
    reg = []
    for g, n, ip, mod, ver, tot in con.execute(
            "select g.name, s.name, s.ip, s.model, s.version, s.totalcamera from sites s left join groups g on g.id = s.group_id"):
        uid = (ip or "").strip().upper()
        if re.fullmatch(r"[A-Z0-9]{20}", uid):
            m = re.match(r"\s*(\d{2,4})\b", n or "")
            reg.append({"uid": uid, "gruppo": g or "", "nome": n or "", "kit": m.group(1) if m else "", "modello": mod or "",
                        "canali": tot, "firmware": ver or ""})
    con.close()
    r = chiama("registratori", {"registratori": reg})
    av(f"registratori da {f} ({time.strftime('%d/%m %H:%M', time.localtime(os.path.getmtime(f)))}): {r}")


FOGLIO_KIT = "1I3-xl5rlQu0xCUA9mj9c5BC_zR27Tioy0X6FRwXqKRw"   # «Elenco KIT Date Registrazioni», scheda ANAGRAFICA KIT


def righe_anagrafica(testo):
    """Dal CSV della scheda ANAGRAFICA KIT: una riga per kit, quella «INSTALLATO» se c'e', se no l'ultima."""
    import csv
    import io
    righe = list(csv.reader(io.StringIO(testo)))
    h = [x.strip().upper() for x in righe[0]]
    i = {n: h.index(n) for n in ("STATO", "KIT", "INDIRIZZO", "CLOUD", "CLIENTE", "N. TELECAMERE", "DATA INSTALLAZIONE") if n in h}
    per = {}
    for x in righe[1:]:
        k = x[i["KIT"]].strip() if len(x) > i["KIT"] else ""
        if not k.isdigit():
            continue
        r = {"kit": int(k), "stato": x[i["STATO"]].strip(), "indirizzo": x[i["INDIRIZZO"]].strip(), "cloud": x[i["CLOUD"]].strip(),
             "cliente": x[i["CLIENTE"]].strip(), "installato_il": x[i.get("DATA INSTALLAZIONE", 0)].strip()}
        t = x[i["N. TELECAMERE"]].strip() if "N. TELECAMERE" in i else ""
        r["telecamere"] = int(t) if t.isdigit() else None
        if r["kit"] not in per or per[r["kit"]]["stato"] != "INSTALLATO":
            per[r["kit"]] = r
    return list(per.values())


def odm_aperti(righe):
    """0.5.0: dalla scheda ODM (righe con l'intestazione) gli ODM senza data di chiusura, per kit:
    {kit: "n° 1686 del 03/11/2026, GUASTO PARZIALE: CH3 non funzionante"}. Funzione pura."""
    if not righe:
        return {}
    h = [x.strip().upper() for x in righe[0]]
    col = lambda nome, dopo=-1: next((i for i, x in enumerate(h) if x == nome and i > dopo), None)
    i_kit, i_ap, i_tipo, i_chiusa, i_note = col("KIT"), col("DATA APERTURA"), col("TIPO"), col("DATA CHIUSURA"), col("NOTE")
    i_stato = col("STATO")
    if i_kit is None or i_chiusa is None:
        return {}
    v = lambda r, i: (r[i].strip() if i is not None and len(r) > i else "")
    per = {}
    for r in righe[1:]:
        k = v(r, i_kit)
        if not k.isdigit() or v(r, i_chiusa):
            continue
        n = v(r, 0)
        testo = (f"n° {n} " if n.isdigit() else "") + (f"del {v(r, i_ap)}" if v(r, i_ap) else "")
        tipo = " ".join(x for x in (v(r, i_tipo), v(r, i_stato)) if x)
        if tipo:
            testo += f", {tipo}"
        if v(r, i_note):
            testo += f": {v(r, i_note)[:120]}"
        per.setdefault(int(k), []).append(testo.strip())
    return {k: " · ".join(x) for k, x in per.items()}


def aggiorna_anagrafica():
    """0.3.3 (Dario: «combinala con l'anagrafica kit e dimmi se ci sono cose che non tornano»): una volta al giorno la
    scheda ANAGRAFICA KIT, letta con l'account di servizio, va alla pagina."""
    import drive_alma
    s = drive_alma.servizio((C, os.path.dirname(sys.executable)))
    testo = s.files().export(fileId=FOGLIO_KIT, mimeType="text/csv").execute().decode("utf-8", "replace")
    righe = righe_anagrafica(testo)
    try:   # 0.5.0: gli ODM aperti accanto a ogni kit
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        chiave = drive_alma.file_chiave((C, os.path.dirname(sys.executable)))
        ses = AuthorizedSession(service_account.Credentials.from_service_account_file(chiave, scopes=["https://www.googleapis.com/auth/drive"]))
        odm = odm_aperti(ses.get(f"https://sheets.googleapis.com/v4/spreadsheets/{FOGLIO_KIT}/values/ODM!A1:AC4000").json().get("values", []))
        for x in righe:
            x["odm"] = odm.get(x["kit"], "")
        av(f"ODM aperti: {len(odm)} kit")
    except Exception as ex:   # noqa: BLE001
        av(f"ODM non letti: {type(ex).__name__}: {str(ex)[:200]}")
    r = chiama("anagrafica", {"righe": righe})
    av(f"anagrafica: {r}")


def aggiorna_elenco_kit():
    """0.4.1 (Dario: «unisci queste info a Elenco KIT, almeno anagrafica e odm»): una volta al giorno lo stato dei
    registratori nelle colonne «REG» dell'ANAGRAFICA KIT e dell'ODM (elenco_kit.py, solo colonne sue)."""
    import elenco_kit
    import drive_alma
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    req = urllib.request.Request(f"{API}?op=stato", headers={"Authorization": "Bearer " + biglietto()})
    with urllib.request.urlopen(req, timeout=120) as r:
        stato = json.loads(r.read().decode())
    chiave = drive_alma.file_chiave((C, os.path.dirname(sys.executable)))
    s = AuthorizedSession(service_account.Credentials.from_service_account_file(chiave, scopes=["https://www.googleapis.com/auth/drive"]))
    elenco_kit.scrivi(s, stato, log=av)


t_fine = time.time() + DURATA
ultimo_uvms = 0.0
ultimo_elenco = time.time() - 23 * 3600   # la prima volta dopo un'ora: prima il giro aggiorna lo stato
av(f"parto: {VERSIONE} sul PC {PC}, ascolto fino alle {time.strftime('%H:%M', time.localtime(t_fine))}")
errori = 0
while time.time() < t_fine:
    if time.time() - ultimo_uvms > 24 * 3600:
        ultimo_uvms = time.time()
        try:
            aggiorna_registratori()
        except Exception as ex:   # noqa: BLE001
            av(f"registratori da UVMS: {type(ex).__name__}: {str(ex)[:200]}")
        try:
            aggiorna_anagrafica()
        except Exception as ex:   # noqa: BLE001
            av(f"anagrafica: {type(ex).__name__}: {str(ex)[:200]}")
    if time.time() - ultimo_elenco > 24 * 3600:
        ultimo_elenco = time.time()
        try:
            aggiorna_elenco_kit()
        except Exception as ex:   # noqa: BLE001
            av(f"Elenco KIT: {type(ex).__name__}: {str(ex)[:200]}")
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
