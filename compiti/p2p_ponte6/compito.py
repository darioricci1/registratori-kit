"""0.8.0 (10/11/2026, sera): sul COMPUTERONE fa partire anche Qwen3-VL (vlm.py 0.2.0, staccato, in ~/kr_vlm) che giudica
le 173 carte di Scorri per il confronto con Claude e con Dario (Dario: «perche' non partiamo da qwen3-vl?»).
Compito p2p_ponte6 (10/11/2026): come p2p_ponte5, piu' due cose.
1) La prova dei video lunghi (Dario: «scaricare un video lungo un'ora da un NVR, in un'ora in cui c'e' stato un abbandono
   e lo sappiamo gia', e vedere se quell'abbandono viene trovato»): sul COMPUTERONE, una volta, per ogni prova di lungo.json
   scarica in P2P i minuti chiesti di ogni telecamera a pezzi di 3 minuti (il relay si chiude dopo 5), li unisce, e li fa
   analizzare a Kit_Rifiuti da riga di comando; in uscita/lungo_<nome>/ i tempi dello scarico e il report (i video no).
2) Si chiude da solo quando su Drive c'e' un compito con un altro nome, cosi' un compito nuovo non aspetta 24 ore.
Prima, p2p_ponte5 (10/11/2026): come p2p_ponte4, piu' gli ODM aperti di ogni kit (scheda ODM dell'Elenco KIT, righe
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
version: 0.9.6 (10/11/2026): nella prova dei video lunghi la CH1 non si chiama più come la CH2 (il file della CH2 la copriva).
0.9.5 (10/11/2026): l'anagrafica porta anche la colonna BATT (come è alimentato il kit: solare, 220 V, batteria).
0.9.4 (10/11/2026): la prova dei video lunghi scarica CH1, CH2, CH3 (canali 0, 1, 2): prima prendeva CH2, CH3 e la CH4
  vuota, e l'abbandono di Dario sulla CH1 del KIT581 non c'era.
0.9.3 (10/11/2026): un canale che oggi non ha registrato manda la foto dell'ultima registrazione dei giorni prima
  (kit 580, CH3 ferma dal 2/11), con giorno e ora.
0.9.2 (10/11/2026): «N. TELECAMERE» scritto «2+SAT», «2+2SAT» si legge come numero (3, 4): prima 228 kit
  installati risultavano senza numero.
0.9.1 (10/11/2026): un giorno impossibile nell archivio di un registratore (kit 544) non ferma piu tutto il kit;
  la prova dei video lunghi manda anche le clip annotate degli abbandoni
0.9.0"""
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
VERSIONE = "p2p_ponte 0.9.6"
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
        # 0.6.2: anche «motivo sconosciuto» prova la password dopo (kit 136, 10/11: con la prima rispondeva cosi' e la
        # seconda non veniva mai provata)
        if ok or not any(w in str(es.get("collegamento", "")) for w in ("password", "sconosciuto", "utente")) or i == len(lista) - 1:
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
            canali.append({"numero": num, "titolo": tit, "registrato_oggi": fn.descrivi_tratti(tr)[:600] if tr else "niente oggi",
                           "minuti_oggi": sum(b - a for a, b, _ in tr), "ore_oggi": ore_del_giorno(tr) if tr else "",
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


def ultima_registrazione(reg, h, oggi, mesi=2):
    """0.9.3: per un canale che oggi non ha registrato, il momento in cui finisce l'ultima registrazione dei giorni prima
    (al massimo nei 2 mesi indietro), o None. Una domanda al registratore per mese e una per il giorno trovato."""
    if h is None:
        return None
    m = datetime.date(oggi.year, oggi.month, 1)
    for _ in range(mesi):
        gg = reg.giorni_registrati(h, datetime.datetime(m.year, m.month, 1)) or []
        giorni = []
        for g in gg:
            try:
                d = datetime.date(m.year, m.month, g)
            except (ValueError, TypeError):
                continue
            if d < oggi.date():
                giorni.append(d)
        for d in sorted(giorni, reverse=True)[:3]:
            tr = reg.minuti_registrati(h, datetime.datetime(d.year, d.month, d.day)) or []
            if tr:
                return datetime.datetime(d.year, d.month, d.day) + datetime.timedelta(minutes=max(b for _, b, _ in tr))
        m = (m - datetime.timedelta(days=1)).replace(day=1)
    return None


def foto_camere(reg, oggi, canali, rid):
    """Per ogni canale: 3 secondi dall'ultimo minuto registrato oggi, una foto da 480 pixel e il giudizio."""
    out = []
    per_num = {num: h for num, h, _ in reg.canali()}
    for c in canali[:9]:
        num, ultimo = c["numero"], c.get("ultimo_minuto")
        vecchia = None
        if ultimo is None:
            vecchia = ultima_registrazione(reg, per_num.get(num), oggi)   # 0.9.3: l'ultima immagine che c'e' (Dario, kit 580)
            if vecchia is None:
                out.append({"canale": num, "vista": "niente", "dalle": "niente registrato oggi"})
                continue
        inizio = vecchia - datetime.timedelta(minutes=2) if vecchia else oggi + datetime.timedelta(minutes=max(0, ultimo - 2))
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
                out.append({"canale": num, "vista": vista, "luce": luce, "contrasto": contrasto,
                            "dalle": f"{inizio:%d/%m %H:%M}" if vecchia else f"{inizio:%H:%M}",
                            "foto": base64.b64encode(open(jpg, "rb").read()).decode()})
                os.remove(jpg)
            else:
                out.append({"canale": num, "vista": "niente", "dalle": f"{inizio:%H:%M}: scarico non riuscito {res.get('errore') or ''}"[:120]})
        except Exception as ex:   # noqa: BLE001
            out.append({"canale": num, "vista": "niente", "dalle": f"errore {type(ex).__name__}"})
    return out


DAL_ARCHIVIO = datetime.date(2026, 10, 27)   # come la pagina (Dario: «limita al 27/10»)


def ore_del_giorno(tr):
    """0.7.0: i minuti registrati in ognuna delle 24 ore, scritti in 24 lettere: «0» niente, «A» tutta l'ora (un passo ogni
    6 minuti). Funzione pura: [(0, 90, 1)] -> «A50000000000000000000000»."""
    m = [0] * 24
    for a, b, _ in tr:
        for o in range(max(0, a // 60), min(24, (b - 1) // 60 + 1)):
            m[o] += max(0, min(b, (o + 1) * 60) - max(a, o * 60))
    return "".join("0123456789A"[min(10, round(min(60, x) / 6))] for x in m)


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
                try:   # 0.9.1: il kit 544 dice di avere registrazioni in un giorno che il mese non ha (ValueError)
                    date.append(datetime.date(m.year, m.month, g))
                except (ValueError, TypeError):
                    continue
            m = datetime.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        giorni, ore = {}, {}
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
            if tr is not None:   # 0.7.0 (Dario: «le 24 ore, in verde dove ha funzionato»): i minuti di ogni ora
                ore[d.isoformat()] = ore_del_giorno(tr)
        out.append({"canale": num, "primo": f"{primo:%Y-%m-%d %H:%M}", "ultimo": f"{ultimo:%Y-%m-%d %H:%M}",
                    "giorni": giorni, "giorni_totali": len(date), "ore": ore})
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


def telecamere_da_testo(t):
    """0.9.2: «N. TELECAMERE» dell'ANAGRAFICA KIT come numero. «3» = 3; «2+SAT» = 3 (la satellite e' una telecamera in
    piu'); «2+2SAT» o «2+2 SAT» = 4; «3 ?» = 3; vuoto o senza cifre = None. Funzione pura."""
    import re
    s = str(t or "").upper().replace(" ", "")
    if not s:
        return None
    tot, trovato = 0, False
    for parte in s.split("+"):
        m = re.match(r"(\d+)?(SAT)?", parte)
        if m.group(1):
            tot += int(m.group(1)); trovato = True
        elif m.group(2):
            tot += 1; trovato = True
    return tot if trovato and tot > 0 else None


def righe_anagrafica(testo):
    """Dal CSV della scheda ANAGRAFICA KIT: una riga per kit, quella «INSTALLATO» se c'e', se no l'ultima."""
    import csv
    import io
    righe = list(csv.reader(io.StringIO(testo)))
    h = [x.strip().upper() for x in righe[0]]
    i = {n: h.index(n) for n in ("STATO", "KIT", "INDIRIZZO", "CLOUD", "CLIENTE", "N. TELECAMERE", "DATA INSTALLAZIONE", "BATT") if n in h}
    per = {}
    for x in righe[1:]:
        k = x[i["KIT"]].strip() if len(x) > i["KIT"] else ""
        if not k.isdigit():
            continue
        r = {"kit": int(k), "stato": x[i["STATO"]].strip(), "indirizzo": x[i["INDIRIZZO"]].strip(), "cloud": x[i["CLOUD"]].strip(),
             "cliente": x[i["CLIENTE"]].strip(), "installato_il": x[i.get("DATA INSTALLAZIONE", 0)].strip()}
        t = x[i["N. TELECAMERE"]].strip() if "N. TELECAMERE" in i else ""
        r["telecamere"] = telecamere_da_testo(t)   # 0.9.2: «2+SAT» sono 3 telecamere (prima valeva vuoto: 228 kit)
        r["telecamere_testo"] = t
        r["batt"] = x[i["BATT"]].strip() if "BATT" in i and len(x) > i["BATT"] else ""   # 0.9.5: solare, 220 V o batteria
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
        # 0.9.0 (Dario: «le info che sono in colonna nella scheda ODM devono restare in colonna»): i campi separati
        per.setdefault(int(k), []).append({"n": n if n.isdigit() else "", "aperto": v(r, i_ap), "tipo": v(r, i_tipo),
                                           "stato": v(r, i_stato), "note": v(r, i_note)[:400]})
    return {k: json.dumps(x, ensure_ascii=False) for k, x in per.items()}


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


def collega_con(reg, uid, kit):
    """Il primo collegamento che entra, provando le credenziali in ordine. Ritorna (ok, testo)."""
    testo = "nessuna credenziale"
    for cr in credenziali(uid, kit):
        ok, testo = reg.collega(uid, cr[0], cr[1], 9010, True, attesa=40)
        if ok or not any(w in testo for w in ("password", "sconosciuto", "utente")):
            return ok, testo
    return False, testo


def scarico_lungo(p):
    """Una prova di lungo.json: scarico a pezzi di 3 minuti, unione per telecamera, analisi di Kit_Rifiuti in sottofondo.
    I canali si contano da 0 come in reg.canali() (CH1 = 0): fino al 0.9.3 lungo.json diceva 1, 2, 3 e la CH1 non si scaricava."""
    import focus_nvr as fn
    nome = p["nome"]
    dove = os.path.join(C, "lungo", nome)
    pezzi_dir = os.path.join(dove, "pezzi")
    os.makedirs(pezzi_dir, exist_ok=True)
    rap = {"prova": p, "pc": PC, "pezzi": [], "inizio_scarico": time.strftime("%Y-%m-%d %H:%M:%S")}
    inizio = datetime.datetime.strptime(p["inizio"], "%Y-%m-%d %H:%M:%S")
    fine = inizio + datetime.timedelta(minutes=p["minuti"])
    PEZZO = 180
    file_per = {c: [] for c in p["canali"]}
    t0 = time.time()
    t = inizio
    while t < fine:
        sec = int(min(PEZZO, (fine - t).total_seconds()))
        cart = os.path.join(pezzi_dir, t.strftime("%H%M%S"))
        with fn.Registratore(os.path.join(C, "FocusNetSDK"), log=lambda *_: None) as reg:
            ok, testo = collega_con(reg, p["uid"], p.get("kit"))
            voce = {"da": t.strftime("%H:%M:%S"), "secondi": sec, "collegamento": testo}
            if ok:
                per = {num: h for num, h, _ in reg.canali()}
                for c in p["canali"]:
                    if c not in per:
                        voce[f"ch{c}"] = "canale assente"
                        continue
                    t1 = time.time()
                    res = reg.scarica(c, per[c], t, sec, cart, ffmpeg=ffmpeg())
                    voce[f"ch{c}"] = {k: res.get(k) for k in ("mb", "velocita", "fotogrammi", "fps", "errore", "primo", "ultimo")}
                    voce[f"ch{c}"]["secondi_scarico"] = round(time.time() - t1, 1)
                    if res.get("file", "").endswith(".mp4"):
                        file_per[c].append(res["file"])
        rap["pezzi"].append(voce)
        av(f"lungo {nome}: pezzo {voce['da']} - {voce['collegamento']}")
        t += datetime.timedelta(seconds=sec)
    rap["secondi_scarico"] = round(time.time() - t0)
    # un file per telecamera, col nome che Kit_Rifiuti divide per fascia e telecamera
    video = os.path.join(dove, "video")
    os.makedirs(video, exist_ok=True)
    finali = []
    for c, fs in file_per.items():
        if not fs:
            continue
        lista = os.path.join(dove, f"lista_ch{c}.txt")
        with open(lista, "w", encoding="utf-8") as fh:
            for f in fs:
                fh.write("file '" + f.replace("\\", "/").replace("'", "") + "'\n")
        # 0.9.6: nome_per_kit_rifiuti conta da 1 (CH1 = 1): col canale da 0 la CH1 e la CH2 prendevano lo stesso nome «...00S»
        # e la CH2 copriva la CH1 (prova del KIT581, 10/11 sera)
        out = os.path.join(video, fn.nome_per_kit_rifiuti(inizio, c + 1) + ".mp4")
        r = subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", out],
                           capture_output=True, text=True, timeout=1800, creationflags=0x08000000)
        if r.returncode == 0 and os.path.exists(out):
            finali.append(out)
            rap[f"ch{c}_mb"] = round(os.path.getsize(out) / 1e6, 1)
        else:
            rap[f"ch{c}_unione"] = (r.stderr or "")[-300:]
    shutil.rmtree(pezzi_dir, ignore_errors=True)
    rap["video"] = [os.path.basename(f) for f in finali]
    u = os.path.join(U, "lungo_" + nome)
    os.makedirs(u, exist_ok=True)
    json.dump(rap, open(os.path.join(u, "scarico.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not finali:
        return None
    risultati = os.path.join(dove, "risultati")
    env = dict(os.environ)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    for k in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL", "TCL_LIBRARY", "TK_LIBRARY"):
        env.pop(k, None)
    cmd = [sys.executable] + finali + ["--out", risultati, "--riga-di-comando"]
    log = open(os.path.join(u, "analisi.txt"), "w", encoding="utf-8")
    av(f"lungo {nome}: scaricati {len(finali)} video in {rap['secondi_scarico']} s, parte l'analisi")
    return subprocess.Popen(cmd, cwd=os.path.dirname(sys.executable), env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=0x00004000 | 0x08000000), risultati, u, time.time()


def copia_risultati(risultati, u, t0, codice):
    """Del risultato dell'analisi vanno su Drive il report, i dati, poche immagini e (0.9.1) le clip annotate degli abbandoni."""
    n_img, n_clip = 0, [0]
    for radice, _, files in os.walk(risultati):
        for f in files:
            p = os.path.join(radice, f)
            est = f.lower().rsplit(".", 1)[-1]
            if est in ("md", "json", "csv", "txt") and os.path.getsize(p) < 3e6:
                shutil.copy(p, os.path.join(u, f))
            elif est in ("jpg", "png") and n_img < 40 and os.path.getsize(p) < 400e3:
                shutil.copy(p, os.path.join(u, f)); n_img += 1
            elif est == "mp4" and "abbandono" in f and f.endswith("_annotata.mp4") and n_clip[0] < 6 and os.path.getsize(p) < 15e6:
                shutil.copy(p, os.path.join(u, f)); n_clip[0] += 1   # 0.9.1: per vedere l'abbandono trovato (e l'orologio)
    with open(os.path.join(u, "fine.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"analisi finita con codice {codice} in {round(time.time() - t0)} s\n")


def compito_nuovo_su_drive():
    """0.6.0: su Drive c'e' un compito con un altro nome? Allora questo si chiude e lascia il posto."""
    try:
        import drive_alma
        f = drive_alma.trova("compito.zip", (C, os.path.dirname(sys.executable)))
        nome = ((f or {}).get("appProperties") or {}).get("compito", "")
        return bool(nome) and nome != os.path.basename(os.path.normpath(C))
    except Exception:   # noqa: BLE001
        return False


t_fine = time.time() + DURATA
ultimo_uvms = 0.0
ultimo_elenco = time.time() - 23 * 3600   # la prima volta dopo un'ora: prima il giro aggiorna lo stato
av(f"parto: {VERSIONE} sul PC {PC}, ascolto fino alle {time.strftime('%H:%M', time.localtime(t_fine))}")
def parti_qwen():
    """0.8.0: Qwen3-VL in un processo staccato (come il compito vlm1), se non gira gia'."""
    casa = os.path.expanduser("~")
    viv = os.path.join(casa, "kr_vlm", "vivo.txt")
    try:
        if time.time() - float(open(viv).read().strip()) < 15 * 60:
            av("qwen: gira gia'"); return
    except (OSError, ValueError):
        pass
    d = os.path.join(casa, "kr_lavori", "vlm2")
    os.makedirs(d, exist_ok=True)
    shutil.copy2(os.path.join(C, "vlm.py"), os.path.join(d, "compito.py"))
    for f in ("vlm_giudica.py", "carte.zip"):
        shutil.copy2(os.path.join(C, f), os.path.join(d, f))
    env = dict(os.environ)
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "KR_PROCESSORI_COMPITO"):
        env.pop(k, None)
    p = subprocess.Popen([sys.executable, "--compito", d], cwd=d, env=env, stdin=subprocess.DEVNULL,
                         stdout=open(os.path.join(d, "uscita_processo.txt"), "a"), stderr=subprocess.STDOUT,
                         creationflags=0x00000008 | 0x00000200 | 0x00004000, close_fds=True)
    av(f"qwen: partito (pid {p.pid}) in {d}")


if PC.upper() == "COMPUTERONE" and os.path.exists(os.path.join(C, "vlm.py")):
    try:
        parti_qwen()
    except Exception as ex:   # noqa: BLE001
        av(f"qwen: {type(ex).__name__}: {str(ex)[:300]}")
errori = 0
analisi_lunghe = []    # (processo, risultati, uscita, partenza) in corso
da_scaricare = []
f_lungo = os.path.join(C, "lungo.json")
if PC.upper() == "COMPUTERONE" and os.path.exists(f_lungo) and not os.path.exists(os.path.join(U, "lungo_fatto.txt")):
    da_scaricare = json.load(open(f_lungo, encoding="utf-8"))
ultimo_guardato = time.time()
while time.time() < t_fine:
    if da_scaricare:
        p = da_scaricare.pop(0)
        try:
            a = scarico_lungo(p)
            if a:
                analisi_lunghe.append(a)
        except Exception as ex:   # noqa: BLE001
            av(f"lungo {p.get('nome')}: {type(ex).__name__}: {str(ex)[:300]}")
            av(traceback.format_exc()[-1500:])
        if not da_scaricare:
            open(os.path.join(U, "lungo_fatto.txt"), "w").write(time.strftime("%Y-%m-%d %H:%M"))
        continue
    for a in list(analisi_lunghe):
        if a[0].poll() is not None:
            analisi_lunghe.remove(a)
            copia_risultati(a[1], a[2], a[3], a[0].returncode)
            av(f"lungo: analisi finita ({a[0].returncode}) in {round(time.time() - a[3])} s")
    if time.time() - ultimo_guardato > 600:
        ultimo_guardato = time.time()
        if not analisi_lunghe and compito_nuovo_su_drive():
            av("su Drive c'e' un compito nuovo: chiudo questo")
            break
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
