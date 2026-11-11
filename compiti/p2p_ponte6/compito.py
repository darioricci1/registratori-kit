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
version: 0.11.0 (11/11/2026): dimezza.json, una volta sola sul COMPUTERONE (segno dimezza_fatto.txt in uscita), in un filo
  suo (Dario: «trova un video lungo e vedi se li' dentro trovi il video rilevato dalla videoanalisi; anche con la tecnica
  del dimezzamento, cosi' risparmiamo banda»): per ogni caso 3 s all'inizio e 3 s alla fine di un'ora, la zona dei
  cassonetti (pezzi_zona) dice se e' cambiato qualcosa; se si', 3 s a meta' e presente_pezzo dice da che parte, finche'
  l'intervallo e' sotto 60 s (dimezza.py 0.1.0, provato in prova_dimezza.py); poi l'ultimo tratto intero di tutte le
  telecamere va a Kit_Rifiuti. Conta MB, richieste, secondi, e confronta con l'ora attesa -> uscita/dimezza.json. Nello
  stesso filo gli «spezzoni» (KIT355: i 2 minuti prima dello spezzone del 27/09, se il registratore li ha ancora).
  nas_extra.json (segno nas_extra_fatto.txt): la misura degli originali sul NAS di misure.json per altri eventi
  (776eb78a95, KIT355 Foggia) -> video_nas_extra.json. La libreria Focus si usa da un filo alla volta (SDK).
0.10.0 (11/11/2026): misure.json, una volta sola per compito sul COMPUTERONE (segno misure_fatte.txt in uscita), in un
  filo suo mentre il ponte risponde: 1) OWLv2 in ONNX (owlv2_fp32.onnx, scaricato da Drive in ~/kr_lavori/owl) con
  onnxruntime su DirectML e sul processore, e in fp16 se onnx c'e' sul PC: apertura, prima inferenza e tempo per
  ritaglio su 20 ritagli dalla scorta video (o finti 960x960) -> owl_tempi.json; 2) gli originali sul NAS dei video
  di 1-2 secondi (998779f7c3, aedb97d080, ebe9f00cef, 2f582c2aa9): byte, pacchetti, durata e decodifica completa
  con ffmpeg, per telecamera -> video_nas.json.
0.9.7 (11/11/2026): i pezzi di ogni canale in una cartella sua (la CH2 copriva ancora la CH1 nei pezzi).
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
import threading
import time
import traceback
import urllib.request

C = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
sys.path.insert(0, C)
U = os.path.join(C, "uscita"); os.makedirs(U, exist_ok=True)
AV = open(os.path.join(U, "avanzamento.txt"), "a", encoding="utf-8")
API = "https://prova-nvr-remoto.vercel.app/api/p2p"
DESTINATARIO = "https://mappakit.alma/nvr-remoto"
VERSIONE = "p2p_ponte 0.11.0"
DURATA = 24 * 3600
PC = os.environ.get("COMPUTERNAME", "PC")[:40]
SDK = threading.Lock()   # 0.11.0: la libreria Focus da un filo alla volta (il ponte e il dimezzamento)


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
        with SDK, fn.Registratore(os.path.join(C, "FocusNetSDK"), log=lambda *_: None) as reg:   # 0.11.0: SDK
            ok, testo = collega_con(reg, p["uid"], p.get("kit"))
            voce = {"da": t.strftime("%H:%M:%S"), "secondi": sec, "collegamento": testo}
            if ok:
                per = {num: h for num, h, _ in reg.canali()}
                for c in p["canali"]:
                    if c not in per:
                        voce[f"ch{c}"] = "canale assente"
                        continue
                    t1 = time.time()
                    # 0.9.7: una cartella per canale: scarica chiama il pezzo nome_per_kit_rifiuti(inizio, c) col canale da 0,
                    # quindi CH1 e CH2 avevano lo stesso nome e la CH2 copriva la CH1 gia' nei pezzi (prova del KIT581, 11/11)
                    cart_c = os.path.join(cart, f"ch{c}")
                    os.makedirs(cart_c, exist_ok=True)
                    res = reg.scarica(c, per[c], t, sec, cart_c, ffmpeg=ffmpeg())
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
    av(f"lungo {nome}: scaricati {len(finali)} video in {rap['secondi_scarico']} s, parte l'analisi")
    return analisi_kit_rifiuti(finali, risultati, os.path.join(u, "analisi.txt")), risultati, u, time.time()


def analisi_kit_rifiuti(finali, risultati, registro, kit=None):
    """Kit_Rifiuti da riga di comando sui video `finali`, in sottofondo (priorita' bassa, niente finestra): il processo.
    0.11.0: una funzione sola per la prova lunga e per il dimezzamento; `kit` (KIT581) per la zona dei cassonetti."""
    env = dict(os.environ)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    for k in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL", "TCL_LIBRARY", "TK_LIBRARY"):
        env.pop(k, None)
    cmd = [sys.executable] + finali + ["--out", risultati, "--riga-di-comando"] + (["--kit", kit] if kit else [])
    log = open(registro, "w", encoding="utf-8")
    return subprocess.Popen(cmd, cwd=os.path.dirname(sys.executable), env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=0x00004000 | NOFIN)


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


# ------------------------------------------------------------------ 0.10.0: misure.json (una volta sola per compito)
# Due misure per decidere, sul COMPUTERONE (Dario, 11/11): 1) quanto costa OWLv2 in ONNX sulla scheda grafica
# (DirectML) e sul processore, per ritaglio, per il verificatore dei candidati (analisi/owlv2-onnx-2026-11-11.md);
# 2) se i video di 1-2 secondi di 998779f7c3, aedb97d080, ebe9f00cef, 2f582c2aa9 sono corti gia' sul NAS o li taglia
# la conversione (analisi/video-rotti-2026-11-11.md, causa 3). Gira in un filo suo: il ponte risponde intanto.
NOFIN = 0x08000000 if os.name == "nt" else 0   # niente finestra nera (su Windows); altrove creationflags deve essere 0
ESTENSIONI_VIDEO = (".ssf", ".dav", ".mp4", ".ts", ".avi", ".mkv")
OWL_LATO = 960
OWL_MEDIA = [0.48145466, 0.4578275, 0.40821073]
OWL_DEVIAZIONE = [0.26862954, 0.26130258, 0.27577711]
ARCHIVI_NAS = [r"Z:\ArchiveData", r"\\192.168.100.253\Alma_Video\ArchiveData", r"\\NAS-VIDEO\Alma_Video\ArchiveData"]


def scrivi_json(nome, dati):
    """In uscita/, scritto prima in un .tmp: un json a meta' non arriva mai su Drive."""
    p = os.path.join(U, nome)
    with open(p + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(dati, fh, ensure_ascii=False, indent=1, default=str)
    os.replace(p + ".tmp", p)


def ffprobe():
    """ffprobe accanto a ffmpeg (o nel PATH); None se non c'e'."""
    f = shutil.which("ffprobe")
    if f:
        return f
    for d in (os.path.dirname(ffmpeg()), getattr(sys, "_MEIPASS", ""), os.path.dirname(sys.executable)):
        p = os.path.join(d, "ffprobe.exe")
        if d and os.path.exists(p):
            return p
    return None


def cartelle_lavoro(c, casa):
    """Le cartelle di lavoro di Kit_Rifiuti da guardare: quella che contiene il compito (<lavoro>\\_compiti\\<nome>) e le
    archivio_kit* della home. casa: (cartella home, nomi che ci sono dentro). Funzione pura."""
    out = []
    su = os.path.dirname(os.path.dirname(os.path.abspath(c)))
    if os.path.basename(os.path.dirname(os.path.abspath(c))).lower() == "_compiti":
        out.append(su)
    for d in sorted(casa[1]):
        if d.lower().startswith("archivio_kit"):
            p = os.path.join(casa[0], d)
            if p not in out:
                out.append(p)
    return out


def file_da_indice(righe, ids):
    """Dalle righe di indice_nas.jsonl, {id: file_rel} per gli id chiesti (l'ultima riga di un evento vale, come
    leggi_indice di archivio_kit). Funzione pura."""
    out = {}
    for r in righe:
        try:
            x = json.loads(r)
        except ValueError:
            continue
        if isinstance(x, dict) and x.get("id") in ids and x.get("file_rel"):
            out[x["id"]] = list(x["file_rel"])
    return out


def leggi_ffprobe(testo):
    """(pacchetti del primo video, durata del contenitore) dal json di ffprobe -count_packets; (0, 0.0) se non dice.
    Funzione pura."""
    try:
        j = json.loads(testo or "{}")
    except ValueError:
        return 0, 0.0
    try:
        pac = int(((j.get("streams") or [{}])[0] or {}).get("nb_read_packets") or 0)
    except (ValueError, TypeError, AttributeError):
        pac = 0
    try:
        dur = float((j.get("format") or {}).get("duration") or 0)
    except (ValueError, TypeError, AttributeError):
        dur = 0.0
    return pac, dur


def leggi_progress(testo):
    """I fotogrammi decodificati dall'ultima riga «frame=N» di ffmpeg -progress; None se non c'e'. Funzione pura."""
    n = None
    for riga in (testo or "").splitlines():
        if riga.startswith("frame="):
            try:
                n = int(riga.split("=", 1)[1].strip())
            except ValueError:
                pass
    return n


def canale_e_parte(nome):
    """«targa FF194DN 18091002S(3).ssf» -> ("02", 3); («», 1) se il nome non ha il canale. Funzione pura."""
    import re
    s = os.path.splitext(os.path.basename(nome.replace("\\", "/")))[0]
    m = re.match(r"^.*?\d{6}(\d{2})[A-Za-z]?\s*(?:\((\d+)\))?$", s)
    if not m:
        return "", 1
    return m.group(1), int(m.group(2) or 1)


def riassunto_evento(misure, fps=25.0, corto_s=3.0):
    """Per telecamera: parti, byte, pacchetti e fotogrammi decodificati sommati sulle parti, secondi a `fps`, errori;
    e il giudizio: «corto all'origine» se sul NAS la telecamera ha meno di `corto_s` secondi, «intero sul NAS» se no
    (allora a tagliare e' la conversione). misure: [{file, byte, pacchetti, decodificati, errori}]. Funzione pura."""
    per = {}
    for m in misure:
        ch, _ = canale_e_parte(m.get("file", ""))
        t = per.setdefault(ch or "?", {"parti": 0, "byte": 0, "pacchetti": 0, "decodificati": 0, "errori": 0})
        t["parti"] += 1
        t["byte"] += int(m.get("byte") or 0)
        t["pacchetti"] += int(m.get("pacchetti") or 0)
        t["decodificati"] += int(m.get("decodificati") or 0)
        t["errori"] += 0 if m.get("decodifica_ok") else 1
    for t in per.values():
        fot = max(t["pacchetti"], t["decodificati"])
        t["secondi_a_%d_fps" % int(fps)] = round(fot / fps, 1)
        t["giudizio"] = ("non misurato" if not t["byte"] else
                         "corto all'origine" if fot < corto_s * fps else "intero sul NAS")
    return per


def riassunto_tempi(sec):
    """Mediana, media, minimo e massimo di una lista di secondi (vuota: {}). Funzione pura."""
    s = sorted(float(x) for x in sec)
    if not s:
        return {}
    n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return {"n": n, "mediana": round(med, 3), "media": round(sum(s) / n, 3), "min": round(s[0], 3), "max": round(s[-1], 3)}


def scegli_video(elenco, n, seme=11):
    """Fino a `n` video della scorta, a caso ma ripetibile, al massimo 2 per cartella (eventi diversi), sopra 1 MB.
    elenco: [(percorso, byte)]. Funzione pura."""
    import random
    rnd = random.Random(seme)
    buoni = [(p, b) for p, b in elenco if b >= 1e6 and p.lower().endswith(ESTENSIONI_VIDEO)]
    rnd.shuffle(buoni)
    per, out = {}, []
    for p, _ in buoni:
        d = os.path.dirname(p)
        if per.get(d, 0) >= 2:
            continue
        per[d] = per.get(d, 0) + 1
        out.append(p)
        if len(out) >= n:
            break
    return out


def ritagli_da_fotogramma(h, w, quanti, rnd):
    """`quanti` riquadri (x, y, lato_x, lato_y) dentro un fotogramma h x w, lati fra 160 px e il lato corto (i
    candidati di Kit_Rifiuti vanno da poco a mezzo fotogramma). Funzione pura con il generatore dato."""
    out = []
    corto = min(h, w)
    for _ in range(quanti):
        lx = rnd.randint(min(160, corto), corto)
        ly = max(min(160, h), min(h, int(lx * rnd.uniform(0.7, 1.3))))
        out.append((rnd.randint(0, w - lx), rnd.randint(0, h - ly), lx, ly))
    return out


def owl_prepara(bgr):
    """Copiata da analisi/esporta_owl_onnx.py 0.1.0 (prepara): ritaglio BGR uint8 -> pixel_values 1x3x960x960 float32,
    come Owlv2ImageProcessor (0..1, quadrato riempito in basso a destra, sfocatura se si rimpicciolisce, bilineare, CLIP)."""
    import cv2
    import numpy as np
    h, w = bgr.shape[:2]
    im = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    L = max(h, w)
    if (h, w) != (L, L):
        im = cv2.copyMakeBorder(im, 0, L - h, 0, L - w, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    f = L / OWL_LATO
    if f > 1:
        s = (f - 1) / 2
        k = 2 * int(np.ceil(3 * s)) + 1
        im = cv2.GaussianBlur(im, (k, k), sigmaX=s, sigmaY=s, borderType=cv2.BORDER_REFLECT_101)
    if L != OWL_LATO:
        im = cv2.resize(im, (OWL_LATO, OWL_LATO), interpolation=cv2.INTER_LINEAR)
    im = (im - np.array(OWL_MEDIA, np.float32)) / np.array(OWL_DEVIAZIONE, np.float32)
    return np.ascontiguousarray(im.transpose(2, 0, 1)[None])


def fotogramma(video, n):
    """Il fotogramma numero `n` di un video come immagine BGR (ffmpeg, che legge anche gli .ssf), o None."""
    import cv2
    import numpy as np
    jpg = os.path.join(U, "_fotogramma.jpg")
    for forza in ([], ["-f", "h264"], ["-f", "hevc"]):
        try:
            if os.path.exists(jpg):
                os.remove(jpg)
            subprocess.run([ffmpeg(), "-v", "error", "-y", *forza, "-i", video, "-vf", f"select=gte(n\\,{n})",
                            "-frames:v", "1", "-q:v", "3", jpg], capture_output=True, timeout=180, creationflags=NOFIN)
            if os.path.exists(jpg):
                im = cv2.imdecode(np.frombuffer(open(jpg, "rb").read(), np.uint8), cv2.IMREAD_COLOR)
                os.remove(jpg)
                if im is not None and im.shape[0] >= 160 and im.shape[1] >= 160:
                    return im
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def ritagli_per_owl(quanti, lavori, seme=11):
    """`quanti` ritagli BGR: da fotogrammi a caso dei video della scorta (lavoro\\_scorta) o, se non ce ne sono, immagini
    finte 960x960. Ritorna (ritagli, da_dove)."""
    import random
    import numpy as np
    rnd = random.Random(seme)
    elenco = []
    for l in lavori:
        sc = os.path.join(l, "_scorta")
        try:
            for ev in os.listdir(sc)[:400]:
                d = os.path.join(sc, ev)
                if os.path.isdir(d):
                    for f in os.listdir(d):
                        p = os.path.join(d, f)
                        elenco.append((p, os.path.getsize(p)))
        except OSError:
            continue
    ritagli, usati = [], []
    for v in scegli_video(elenco, (quanti + 1) // 2, seme):
        im = fotogramma(v, rnd.randint(0, 200))
        if im is None:
            continue
        usati.append(os.path.basename(v))
        for x, y, lx, ly in ritagli_da_fotogramma(im.shape[0], im.shape[1], 2, rnd):
            ritagli.append(np.ascontiguousarray(im[y:y + ly, x:x + lx]))
        if len(ritagli) >= quanti:
            break
    da_dove = f"{len(ritagli)} ritagli da {len(usati)} video della scorta ({len(elenco)} file nella scorta)"
    if len(ritagli) < quanti:
        g = np.random.default_rng(seme)
        finti = quanti - len(ritagli)
        ritagli += [g.integers(0, 256, (OWL_LATO, OWL_LATO, 3), dtype=np.uint8) for _ in range(finti)]
        da_dove += f", piu' {finti} immagini finte 960x960"
    return ritagli[:quanti], da_dove


def owl_modello(nome, byte_atteso, dove):
    """Il modello in ~/kr_lavori/owl: se manca (o ha un'altra grandezza) si scarica da Drive. Ritorna (percorso, nota)."""
    import drive_alma
    os.makedirs(dove, exist_ok=True)
    p = os.path.join(dove, nome)
    if os.path.exists(p) and (not byte_atteso or os.path.getsize(p) == int(byte_atteso)):
        return p, "gia' sul PC"
    f = drive_alma.trova(nome, (C, os.path.dirname(sys.executable)))
    if not f:
        return None, f"su Drive manca {nome}"
    t0 = time.time()
    ok, msg = drive_alma.scarica(f["id"], p, (C, os.path.dirname(sys.executable)))
    if not ok:
        return None, msg
    if byte_atteso and os.path.getsize(p) != int(byte_atteso):
        return None, f"scaricato ma di {os.path.getsize(p)} byte invece di {byte_atteso} (segnaposto non ancora caricato?)"
    return p, f"scaricato da Drive in {time.time() - t0:.0f} s ({msg})"


def owl_misura(percorso, provider, ritagli, fili=4, device=0):
    """Una sessione onnxruntime: apertura (il primo caricamento), prima inferenza, poi ogni ritaglio (preparazione e
    modello separati). Ritorna (risultato, massimi per ritaglio delle 4 domande, per il confronto fra provider)."""
    import numpy as np
    import onnxruntime as ort
    o = ort.SessionOptions()
    o.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    if provider == "DmlExecutionProvider":
        o.enable_mem_pattern = False   # DirectML li vuole cosi'
        o.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        provs = [("DmlExecutionProvider", {"device_id": int(device)}), "CPUExecutionProvider"]
    else:
        o.intra_op_num_threads = int(fili)
        provs = ["CPUExecutionProvider"]
    r = {"provider": provider, "fili": fili if provider != "DmlExecutionProvider" else None,
         "device_id": device if provider == "DmlExecutionProvider" else None}
    t0 = time.time()
    s = ort.InferenceSession(percorso, o, providers=provs)
    r["apertura_s"] = round(time.time() - t0, 2)
    r["provider_usati"] = s.get_providers()
    t0 = time.time()
    s.run(None, {"pixel_values": owl_prepara(ritagli[0])})
    r["prima_inferenza_s"] = round(time.time() - t0, 2)
    prep, mod, massimi = [], [], []
    for im in ritagli:
        t0 = time.time()
        x = owl_prepara(im)
        t1 = time.time()
        p, _ = s.run(None, {"pixel_values": x})
        t2 = time.time()
        prep.append(t1 - t0)
        mod.append(t2 - t1)
        massimi.append([round(float(v), 5) for v in np.asarray(p, np.float32).max(0)])
    r["preparazione_s"] = riassunto_tempi(prep)
    r["modello_s"] = riassunto_tempi(mod)
    r["per_ritaglio_s"] = riassunto_tempi([a + b for a, b in zip(prep, mod)])
    r["ritagli_al_minuto"] = round(60 / max(1e-6, r["per_ritaglio_s"]["mediana"]), 1)
    del s
    return r, massimi


def differenza_massimi(a, b):
    """La differenza piu' grande fra i punteggi massimi di due provider sugli stessi ritagli. Funzione pura."""
    d = [abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra, rb)]
    return round(max(d), 5) if d else None


def priorita_normale():
    """Il compito gira a priorita' minima (IDLE): per misurare come girerebbe dentro Kit_Rifiuti la si alza a normale
    per il tempo della misura. Ritorna la funzione che la rimette com'era (o None)."""
    try:
        import psutil
        p = psutil.Process()
        prima = p.nice()
        p.nice(psutil.NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
        return lambda: p.nice(prima)
    except Exception:   # noqa: BLE001
        return None


def schede_grafiche():
    """I nomi delle schede grafiche di Windows (per sapere quale e' il device 0 di DirectML)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                           capture_output=True, text=True, timeout=60, creationflags=NOFIN)
        return [x.strip() for x in r.stdout.splitlines() if x.strip()]
    except Exception as ex:   # noqa: BLE001
        return [f"non lette: {type(ex).__name__}"]


def misura_owl(cfg, lavori):
    """owl_tempi.json: DirectML (uno o piu' device) e processore, su fp32 e, se si riesce a farlo qui, fp16."""
    out = {"pc": PC, "versione": VERSIONE, "inizio": time.strftime("%Y-%m-%d %H:%M:%S"), "schede": schede_grafiche(),
           "processori": os.cpu_count(), "fili_compito": os.environ.get("KR_PROCESSORI_COMPITO"), "prove": []}
    try:
        viv = os.path.join(os.path.expanduser("~"), "kr_vlm", "vivo.txt")
        out["qwen_vivo"] = time.time() - float(open(viv).read().strip()) < 15 * 60   # Qwen sulla stessa scheda?
    except (OSError, ValueError):
        out["qwen_vivo"] = False
    try:
        import onnxruntime as ort
        out["onnxruntime"] = ort.__version__
        out["provider_disponibili"] = ort.get_available_providers()
    except Exception as ex:   # noqa: BLE001
        out["errore"] = f"onnxruntime: {type(ex).__name__}: {ex}"
        scrivi_json("owl_tempi.json", out)
        return
    dove = os.path.join(os.path.expanduser("~"), "kr_lavori", "owl")
    os.makedirs(dove, exist_ok=True)
    p32, out["modello"] = owl_modello(cfg.get("nome_drive", "owlv2_fp32.onnx"), cfg.get("byte"), dove)
    scrivi_json("owl_tempi.json", out)
    if not p32:
        return
    ritagli, out["ritagli"] = ritagli_per_owl(int(cfg.get("ritagli", 20)), lavori)
    out["lati_ritagli"] = [list(r.shape[:2]) for r in ritagli]
    rimetti = priorita_normale() if cfg.get("priorita_normale", True) else None
    out["priorita_normale"] = bool(rimetti)
    modelli = [("fp32", p32)]
    if cfg.get("fp16", True):
        try:
            import onnx
            from onnxruntime.transformers.float16 import convert_float_to_float16
            p16 = os.path.join(dove, "owlv2_fp16.onnx")
            if not os.path.exists(p16):
                t0 = time.time()
                onnx.save(convert_float_to_float16(onnx.load(p32), keep_io_types=True), p16)
                out["fp16_creato_s"] = round(time.time() - t0, 1)
            modelli.append(("fp16", p16))
        except Exception as ex:   # noqa: BLE001
            out["fp16"] = f"saltato: {type(ex).__name__}: {str(ex)[:200]}"
    try:
        massimi_cpu = None   # i punteggi di fp32 sul processore: il riferimento per DirectML e per fp16
        for tipo, p in modelli:
            # fp16 solo sulla scheda grafica: sul processore e' piu' lento di fp32 (in prova qui: oltre 10 minuti a ritaglio)
            prove = ([("CPUExecutionProvider", 0)] if tipo == "fp32" else []) + \
                [("DmlExecutionProvider", d) for d in cfg.get("dml_device", [0])]
            for prov, dev in prove:
                if prov not in out["provider_disponibili"]:
                    out["prove"].append({"modello": tipo, "provider": prov, "errore": "provider non disponibile"})
                    continue
                try:
                    r, mx = owl_misura(p, prov, ritagli, int(cfg.get("fili_cpu", 4)), dev)
                    if prov == "CPUExecutionProvider":
                        massimi_cpu = mx
                    else:
                        r["diff_max_punteggi_con_fp32_cpu"] = differenza_massimi(mx, massimi_cpu or [])
                    r["modello"] = tipo
                    r["mb_modello"] = round(os.path.getsize(p) / 2**20, 1)
                    out["prove"].append(r)
                except Exception as ex:   # noqa: BLE001
                    out["prove"].append({"modello": tipo, "provider": prov, "device_id": dev,
                                         "errore": f"{type(ex).__name__}: {str(ex)[:300]}"})
                av(f"owl: {tipo} {prov} {dev}: {(out['prove'][-1].get('per_ritaglio_s') or {}).get('mediana', out['prove'][-1].get('errore'))}")
                scrivi_json("owl_tempi.json", out)
    finally:
        if rimetti:
            rimetti()
    out["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    scrivi_json("owl_tempi.json", out)


def misura_file(f):
    """Un originale del NAS: byte, pacchetti e durata (ffprobe -count_packets), e se ffmpeg lo decodifica tutto senza
    errori (ffmpeg -v error -i file -f null -), coi fotogrammi decodificati. Se il formato non si riconosce da solo
    (gli .ssf sono H.264 grezzo dietro un'intestazione) si riprova con -f h264 e -f hevc."""
    m = {"file": f, "byte": os.path.getsize(f)}
    fp, scelta = ffprobe(), []
    for forza in (([], ["-f", "h264"], ["-f", "hevc"]) if fp else ()):
        t0 = time.time()
        r = subprocess.run([fp, "-v", "error", *forza, "-select_streams", "v:0", "-count_packets", "-show_entries",
                            "stream=nb_read_packets,codec_name,width,height,r_frame_rate:format=duration,format_name",
                            "-of", "json", f], capture_output=True, text=True, timeout=900, creationflags=NOFIN)
        pac, dur = leggi_ffprobe(r.stdout)
        if forza and not pac:
            continue
        try:
            j = json.loads(r.stdout or "{}")
            st = (j.get("streams") or [{}])[0]
            m.update(codec=st.get("codec_name"), dimensioni=f"{st.get('width')}x{st.get('height')}",
                     fps_dichiarati=st.get("r_frame_rate"), formato=(j.get("format") or {}).get("format_name"))
        except (ValueError, IndexError, AttributeError):
            pass
        m.update(pacchetti=pac, durata=dur, ffprobe_s=round(time.time() - t0, 1),
                 ffprobe_errori=(r.stderr or "")[-400:], ffprobe_forzato=" ".join(forza))
        if pac:
            scelta = forza
            break
    for forza in ([scelta] + ([["-f", "h264"]] if not scelta else [])):
        t0 = time.time()
        r = subprocess.run([ffmpeg(), "-v", "error", "-nostats", "-progress", "pipe:1", *forza, "-i", f, "-f", "null", "-"],
                           capture_output=True, text=True, timeout=1800, creationflags=NOFIN)
        err = [x for x in (r.stderr or "").splitlines() if x.strip()]
        n = leggi_progress(r.stdout)
        if forza and m.get("decodificati") and (n or 0) <= m["decodificati"]:
            break   # il formato forzato non decodifica di piu': resta la prima lettura
        m.update(decodificati=n, codice_ffmpeg=r.returncode, righe_di_errore=len(err), primi_errori=err[:8],
                 decodifica_s=round(time.time() - t0, 1), decodifica_ok=r.returncode == 0 and not err and bool(n),
                 decodifica_forzato=" ".join(forza))
        if n:
            break
    return m


def percorso_nas(radice, rel):
    """radice + percorso relativo dell'elenco (scritto con «\\»), col separatore di questo sistema."""
    return os.path.join(radice, *rel.replace("\\", "/").split("/"))


def radice_con(file_rel, radici):
    """La prima radice del NAS in cui c'e' il primo file dell'evento, o None."""
    for r in radici:
        try:
            if os.path.exists(percorso_nas(r, file_rel[0])):
                return r
        except OSError:
            continue
    return None


def eventi_da_elenco_drive(ids, dove):
    """Dall'elenco di ArchiveData su Drive (elenco_archivedata.tsv.gz), con le regole di archivio_kit
    (indice_da_elenco): {id: file_rel}."""
    import gzip
    import drive_alma
    import archivio_kit as ak
    f = drive_alma.trova(ak.ELENCO_DRIVE, (C, os.path.dirname(sys.executable)))
    if not f:
        return {}
    z = os.path.join(dove, ak.ELENCO_DRIVE)
    ok, _ = drive_alma.scarica(f["id"], z, (C, os.path.dirname(sys.executable)))
    if not ok:
        return {}
    righe = []
    try:
        with gzip.open(z, "rt", encoding="utf-8", errors="replace") as fh:
            for r in fh:
                righe.append(r.rstrip("\n").split("\t"))
    except EOFError:
        righe = righe[:-1]
    return {e["id"]: e["file_rel"] for e in ak.indice_da_elenco(righe) if e["id"] in ids}


def eventi_dal_nas(ids, radice, comuni=(), limite_s=1800):
    """Ultima strada: si scorrono le cartelle del NAS (solo i comuni dati, se ce ne sono) e gli eventi si fanno con le
    regole di archivio_kit. Al massimo `limite_s` secondi. {id: file_rel}."""
    import archivio_kit as ak
    t0, righe = time.time(), []
    for c in (comuni or os.listdir(radice)):
        for cart, sotto, files in os.walk(os.path.join(radice, c)):
            if time.time() - t0 > limite_s:
                break
            rel = os.path.relpath(cart, radice)
            for x in files:
                if x.lower().endswith(ESTENSIONI_VIDEO + (".jpg", ".jpeg", ".png")):
                    try:
                        mb = os.path.getsize(os.path.join(cart, x)) / 1e6
                    except OSError:
                        mb = 0.0
                    righe.append([rel.replace("/", "\\"), x, f"{mb:.2f}", ""])
        trovati = {e["id"]: e["file_rel"] for e in ak.indice_da_elenco(righe) if e["id"] in ids}
        if len(trovati) == len(ids) or time.time() - t0 > limite_s:
            return trovati
    return {e["id"]: e["file_rel"] for e in ak.indice_da_elenco(righe) if e["id"] in ids}


def misura_video_nas(cfg, lavori, uscita="video_nas.json"):
    """video_nas.json (0.11.0: o `uscita`): per ogni evento i file originali sul NAS e le loro misure, per telecamera."""
    eventi = cfg.get("eventi") or []
    ids = {e["id"] for e in eventi}
    out = {"pc": PC, "versione": VERSIONE, "inizio": time.strftime("%Y-%m-%d %H:%M:%S"), "ffprobe": ffprobe(),
           "ffmpeg": ffmpeg(), "eventi": {}}
    radici = [r for r in (cfg.get("radici") or []) + ARCHIVI_NAS if os.path.isdir(r)]
    out["radici"] = radici
    trovati = {e["id"]: (e["file_rel"], "misure.json") for e in eventi if e.get("file_rel")}
    for l in lavori:   # l'elenco del NAS che Kit_Rifiuti tiene sul PC
        try:
            with open(os.path.join(l, "indice_nas.jsonl"), encoding="utf-8", errors="replace") as fh:
                for k, v in file_da_indice(fh, ids - set(trovati)).items():
                    trovati[k] = (v, os.path.join(l, "indice_nas.jsonl"))
        except OSError:
            continue
    if ids - set(trovati):
        try:
            d = os.path.join(os.path.expanduser("~"), "kr_lavori", "misure")
            os.makedirs(d, exist_ok=True)
            for k, v in eventi_da_elenco_drive(ids - set(trovati), d).items():
                trovati[k] = (v, "elenco di ArchiveData su Drive")
        except Exception as ex:   # noqa: BLE001
            out["elenco_drive"] = f"{type(ex).__name__}: {str(ex)[:200]}"
    if ids - set(trovati) and radici:
        try:
            comuni = sorted({e["comune"] for e in eventi if e["id"] in ids - set(trovati) and e.get("comune")})
            for k, v in eventi_dal_nas(ids - set(trovati), radici[0], comuni, int(cfg.get("limite_scorri_s", 1800))).items():
                trovati[k] = (v, "cartelle del NAS")
        except Exception as ex:   # noqa: BLE001
            out["scorri_nas"] = f"{type(ex).__name__}: {str(ex)[:200]}"
    scrivi_json(uscita, out)
    for e in eventi:
        x = {"nota": e.get("nota", "")}
        out["eventi"][e["id"]] = x
        if e["id"] not in trovati:
            x["errore"] = "evento non trovato (indice sul PC, elenco su Drive, cartelle del NAS)"
            continue
        file_rel, x["trovato_in"] = trovati[e["id"]]
        x["file_rel"] = file_rel
        r = radice_con(file_rel, radici)
        if not r:
            x["errore"] = f"i file non ci sono in nessuna radice del NAS ({', '.join(radici) or 'nessuna raggiungibile'})"
            continue
        x["radice"] = r
        cart = os.path.dirname(percorso_nas(r, file_rel[0]))
        try:   # i video della cartella del giorno: le parti «(2)» e i nomi vicini che l'indice non ha unito
            x["cartella"] = sorted([f, os.path.getsize(os.path.join(cart, f))] for f in os.listdir(cart)
                                   if f.lower().endswith(ESTENSIONI_VIDEO))[:150]
        except OSError as ex:
            x["cartella"] = f"non letta: {ex}"
        x["file"] = []
        for fr in file_rel:
            p = percorso_nas(r, fr)
            try:
                m = misura_file(p)
                m["file"] = fr
            except Exception as ex:   # noqa: BLE001
                m = {"file": fr, "errore": f"{type(ex).__name__}: {str(ex)[:300]}"}
            x["file"].append(m)
            scrivi_json(uscita, out)
        x["telecamere"] = riassunto_evento(x["file"])
        av(f"video nas {e['id']}: " + ", ".join(f"ch{k} {v['secondi_a_25_fps']} s {v['giudizio']}" for k, v in x["telecamere"].items()))
    out["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    scrivi_json(uscita, out)


MISURE_VIVE = []   # il filo delle misure, finche' gira


def parti_misure():
    """Se c'e' misure.json e il segno misure_fatte.txt non c'e', le due misure in un filo (prima i video, che non
    chiedono la scheda grafica, poi OWL); il segno si scrive alla fine, anche con un errore."""
    f = os.path.join(C, "misure.json")
    segno = os.path.join(U, "misure_fatte.txt")
    if not os.path.exists(f) or os.path.exists(segno):
        return
    cfg = json.load(open(f, encoding="utf-8"))
    if cfg.get("pc", "COMPUTERONE").upper() not in (PC.upper(), "*"):
        return
    casa = os.path.expanduser("~")
    try:
        nomi = os.listdir(casa)
    except OSError:
        nomi = []
    lavori = cartelle_lavoro(C, (casa, nomi))

    def gira():
        for nome, fun, parte in (("video_nas", misura_video_nas, cfg.get("video_nas")), ("owl", misura_owl, cfg.get("owl"))):
            if not parte:
                continue
            av(f"misure: parte {nome}")
            try:
                fun(parte, lavori)
            except Exception as ex:   # noqa: BLE001
                av(f"misure {nome}: {type(ex).__name__}: {str(ex)[:300]}")
                av(traceback.format_exc()[-1500:])
        open(segno, "w").write(time.strftime("%Y-%m-%d %H:%M"))
        av("misure: fatte")

    t = threading.Thread(target=gira, daemon=True)
    t.start()
    MISURE_VIVE.append(t)


def misure_in_corso():
    return any(t.is_alive() for t in MISURE_VIVE)


# ------------------------------------------------------------------ 0.11.0: dimezza.json e nas_extra.json (una volta sola)
def parti_filo(nome_json, segno_nome, lavoro, solo_computerone=True):
    """Se c'e' `nome_json` nella cartella del compito e il segno in uscita non c'e', lavoro(cfg) in un filo suo (il
    ponte risponde intanto); il segno si scrive alla fine, anche con un errore. Il filo va in MISURE_VIVE: il compito
    non si chiude e non lascia il posto a uno nuovo finche' gira."""
    f = os.path.join(C, nome_json)
    segno = os.path.join(U, segno_nome)
    if not os.path.exists(f) or os.path.exists(segno):
        return
    cfg = json.load(open(f, encoding="utf-8"))
    pc = (cfg.get("pc") if isinstance(cfg, dict) else None) or ("COMPUTERONE" if solo_computerone else "*")
    if pc.upper() not in (PC.upper(), "*"):
        return

    def gira():
        av(f"{nome_json}: parte")
        try:
            lavoro(cfg)
        except Exception as ex:   # noqa: BLE001
            av(f"{nome_json}: {type(ex).__name__}: {str(ex)[:300]}")
            av(traceback.format_exc()[-1500:])
        open(segno, "w").write(time.strftime("%Y-%m-%d %H:%M"))
        av(f"{nome_json}: fatto")

    t = threading.Thread(target=gira, daemon=True)
    t.start()
    MISURE_VIVE.append(t)


def nas_extra(cfg):
    """nas_extra.json: altri eventi per la misura degli originali sul NAS (misura_video_nas) -> video_nas_extra.json."""
    casa = os.path.expanduser("~")
    try:
        nomi = os.listdir(casa)
    except OSError:
        nomi = []
    misura_video_nas(cfg.get("video_nas") or {}, cartelle_lavoro(C, (casa, nomi)), "video_nas_extra.json")


class ScaricatoreP2P:
    """Un registratore in P2P per il dimezzamento: un collegamento solo finche' e' fresco (il relay si chiude dopo 5
    minuti: dopo 4 si ricollega), un nuovo tentativo su un collegamento nuovo se un pezzo non arriva. Va usato dentro
    `with SDK`."""
    FRESCO = 240

    def __init__(self, uid, kit):
        self.uid, self.kit = uid, kit
        self.reg, self.t, self.per, self.collegamenti = None, 0.0, {}, []

    def collegato(self):
        import focus_nvr as fn
        if self.reg is not None and time.time() - self.t < self.FRESCO:
            return True
        self.chiudi()
        t0 = time.time()
        self.reg = fn.Registratore(os.path.join(C, "FocusNetSDK"), log=lambda *_: None)
        ok, testo = collega_con(self.reg, self.uid, self.kit)
        self.collegamenti.append({"ok": ok, "testo": testo, "secondi": round(time.time() - t0, 1)})
        if not ok:
            self.chiudi()
            return False
        self.per = {num: h for num, h, _ in self.reg.canali()}
        self.t = time.time()
        return True

    def chiudi(self):
        if self.reg is not None:
            try:
                self.reg.chiudi()
            except Exception:   # noqa: BLE001
                pass
        self.reg = None

    def intervallo(self, canale):
        """(prima, ultima registrazione) del canale, o None se non si sa."""
        if not self.collegato() or canale not in self.per:
            return None
        try:
            return self.reg.intervallo(self.per[canale])
        except Exception:   # noqa: BLE001
            return None

    def scarica(self, canale, da, secondi, cartella):
        res = {"errore": "non provato"}
        for _ in range(2):
            if not self.collegato():
                res = {"errore": "collegamento: " + (self.collegamenti[-1]["testo"] if self.collegamenti else "?")}
                continue
            if canale not in self.per:
                return {"errore": "canale assente"}
            t0 = time.time()
            try:
                res = self.reg.scarica(canale, self.per[canale], da, secondi, cartella, ffmpeg=ffmpeg())
            except Exception as ex:   # noqa: BLE001
                res = {"errore": f"{type(ex).__name__}: {str(ex)[:200]}"}
            res["secondi_attesa"] = round(time.time() - t0, 1)
            if str(res.get("file", "")).endswith(".mp4"):
                return res
            self.chiudi()   # il prossimo tentativo su un collegamento nuovo
        return res


def secondi_video(res):
    """I secondi di video di un pezzo scaricato (dal primo all'ultimo fotogramma), o 0."""
    try:
        return (datetime.datetime.fromisoformat(res["ultimo"]) - datetime.datetime.fromisoformat(res["primo"])).total_seconds()
    except (KeyError, TypeError, ValueError):
        return 0.0


def leggi_campione(sc, canale, inizio, dove, u, kr, dz):
    """leggi(t) per dimezza.Campioni: 3 s del canale da inizio + t, i fotogrammi a 1280 pixel, il file si butta; in
    uscita una foto piccola del campione (per guardarlo). Ritorna (fotogrammi o None, info)."""
    import cv2
    cart = os.path.join(dove, "campioni")
    os.makedirs(cart, exist_ok=True)

    def leggi(t):
        da = inizio + datetime.timedelta(seconds=t)
        res = sc.scarica(canale, da, dz.CAMPIONE_S, cart)
        info = {"mb": res.get("mb") or 0.0, "secondi": res.get("secondi_attesa"), "secondi_video": secondi_video(res),
                "errore": res.get("errore")}
        f = str(res.get("file", ""))
        fot = None
        if f.endswith(".mp4"):
            fot = kr.fotogrammi_ai_tempi(f, dz.TEMPI_FOTOGRAMMI) or None
            if fot:
                m = dz.mediana(fot)
                cv2.imwrite(os.path.join(u, f"campione_{int(t):04d}s_{da:%H%M%S}.jpg"),
                            cv2.resize(m, (480, int(m.shape[0] * 480 / m.shape[1]))), [cv2.IMWRITE_JPEG_QUALITY, 70])
        if f and os.path.exists(f):
            os.remove(f)
        return fot, info
    return leggi


def scarica_tratto(sc, canali, da_dt, secondi, dove, kit):
    """Tutto il tratto [da_dt, +secondi) di ogni canale, ognuno nella sua cartella (scarica conta il canale da 0 e CH1 e
    CH2 avrebbero lo stesso nome), poi col nome che Kit_Rifiuti divide per telecamera in dove/KITnnn/. Ritorna
    (file, misure per canale)."""
    import focus_nvr as fn
    video = os.path.join(dove, kit)
    os.makedirs(video, exist_ok=True)
    finali, misure = [], {}
    for c in canali:
        cart = os.path.join(dove, f"ch{c}")
        res = sc.scarica(c, da_dt, secondi, cart)
        misure[f"ch{c}"] = {k: res.get(k) for k in ("mb", "fotogrammi", "fps", "errore", "primo", "ultimo", "secondi_attesa")}
        f = str(res.get("file", ""))
        if f.endswith(".mp4"):
            dest = os.path.join(video, fn.nome_per_kit_rifiuti(da_dt, c + 1) + ".mp4")
            shutil.move(f, dest)
            finali.append(dest)
        shutil.rmtree(cart, ignore_errors=True)
    return finali, misure


def tratti_da_analizzare(r, durata, dz):
    """Gli ultimi intervalli del dimezzamento da scaricare interi: quello scelto e quelli degli altri pezzi dimezzati.
    [(etichetta, da_s, secondi)]."""
    out = []
    if r.get("esito") != "cambio":
        return out
    out.append(("scelto",) + dz.finestra_finale(r["lo"], r["hi"], durata))
    for i, a in enumerate(r.get("altri") or []):
        if a.get("lo") is not None:
            out.append((f"altro{i + 1}",) + dz.finestra_finale(a["lo"], a["hi"], durata))
    return out


def un_caso(caso, kr, dz, out_tutto):
    """Un caso di dimezza.json: ricerca, tratti scaricati; ritorna le analisi da far partire [(etichetta, file,
    inizio del tratto, cartella in uscita)]."""
    nome = caso["nome"]
    inizio = datetime.datetime.strptime(caso["inizio"], "%Y-%m-%d %H:%M:%S")
    durata = float(caso.get("minuti", 60)) * 60
    canale = int(caso["canale"])
    kit = kr.kit_id(f"KIT{int(caso['kit'])}")
    u = os.path.join(U, "dimezza_" + nome)
    dove = os.path.join(os.path.expanduser("~"), "kr_lavori", "dimezza", nome)
    os.makedirs(u, exist_ok=True)
    x = {"caso": caso, "inizio_lavoro": time.strftime("%Y-%m-%d %H:%M:%S")}
    out_tutto["casi"].append(x)
    zz = kr.zone_di(kit, canale + 1)
    x["zona_da"] = "zone_cassonetti.json di Kit_Rifiuti"
    if not zz and caso.get("zona"):
        zz, x["zona_da"] = (caso["zona"]["riquadri"], caso["zona"].get("escludi") or []), "dimezza.json"
    if not zz:
        x["esito"] = f"la telecamera {canale + 1} del {kit} non ha una zona dei cassonetti"
        return []
    x["zona"] = {"riquadri": zz[0], "escludi": zz[1]}
    sc = ScaricatoreP2P(caso["uid"], int(caso["kit"]))
    analisi = []
    try:
        with SDK:
            t0 = time.time()
            iv = sc.intervallo(canale)
            x["registra"] = [str(v) for v in iv] if iv else None
            ok, perche = dz.coperto(iv, inizio, inizio + datetime.timedelta(seconds=durata))
            if not sc.collegamenti or not sc.collegamenti[-1]["ok"]:
                x["esito"] = "registratore non raggiunto: " + (sc.collegamenti[-1]["testo"] if sc.collegamenti else "?")
                return []
            if not ok:
                x["esito"] = perche
                return []
            cam = dz.Campioni(leggi_campione(sc, canale, inizio, dove, u, kr, dz))
            r = dz.cerca(kr, cam, durata, zz[0], zz[1], dimezza_altri=int(caso.get("dimezza_altri", 1)))
            x["ricerca"] = r
            x["esito"] = r["esito"]
            x["campioni"] = cam.registro
            x["conti_ricerca"] = dict(cam.conti, secondi_lavoro=round(time.time() - t0, 1))
            x["stima_ora_intera_mb"] = dz.stima_ora(cam.conti["mb"], cam.conti["secondi_video"], durata)
            atteso_s = dz.secondi_da(inizio, caso.get("atteso"))
            if r["esito"] == "cambio":
                x["trovato"] = (inizio + datetime.timedelta(seconds=r["momento"])).strftime("%H:%M:%S")
                x["confronto"] = dz.confronta(atteso_s, r["lo"], r["hi"])
                for a in r.get("altri") or []:
                    if a.get("lo") is not None:
                        a["trovato"] = (inizio + datetime.timedelta(seconds=a["momento"])).strftime("%H:%M:%S")
                        a["confronto"] = dz.confronta(atteso_s, a["lo"], a["hi"])
            scrivi_json("dimezza.json", out_tutto)
            av(f"dimezza {nome}: {r['esito']}, {cam.conti['richieste']} richieste, {cam.conti['mb']} MB"
               + (f", trovato {x.get('trovato')} (atteso {caso.get('atteso')})" if r["esito"] == "cambio" else ""))
            x["tratti"] = {}
            canali = [int(c) for c in caso.get("canali_analisi", [canale])]
            for etichetta, da_s, sec in tratti_da_analizzare(r, durata, dz):
                t1 = time.time()
                da_dt = inizio + datetime.timedelta(seconds=da_s)
                finali, misure = scarica_tratto(sc, canali, da_dt, sec, os.path.join(dove, etichetta), kit)
                mb = round(sum((m.get("mb") or 0) for m in misure.values()), 2)
                x["tratti"][etichetta] = {"da": da_dt.strftime("%H:%M:%S"), "secondi": sec, "canali": misure, "mb": mb,
                                          "richieste": len(canali), "secondi_scarico": round(time.time() - t1, 1),
                                          "atteso": caso.get("atteso")}
                if finali:
                    analisi.append((nome + " " + etichetta, finali, da_dt, os.path.join(u, etichetta), kit, x["tratti"][etichetta]))
            x["totale"] = {"mb": round(cam.conti["mb"] + sum(t["mb"] for t in x["tratti"].values()), 2),
                           "richieste": cam.conti["richieste"] + sum(t["richieste"] for t in x["tratti"].values()),
                           "collegamenti": len(sc.collegamenti), "secondi": round(time.time() - t0, 1)}
    finally:
        sc.chiudi()
        x["collegamenti"] = sc.collegamenti
        shutil.rmtree(os.path.join(dove, "campioni"), ignore_errors=True)
    return analisi


def uno_spezzone(sp, kr, out_tutto):
    """Uno «spezzone» di dimezza.json: un tratto di tutte le telecamere scaricato intero (se il registratore l'ha
    ancora) e dato a Kit_Rifiuti. Per il KIT355 del 27/09: i 2 minuti prima dello spezzone, per vedere lo scarico."""
    import dimezza as dz
    nome = sp["nome"]
    da_dt = datetime.datetime.strptime(sp["inizio"], "%Y-%m-%d %H:%M:%S")
    sec = int(sp.get("secondi", 120))
    kit = kr.kit_id(f"KIT{int(sp['kit'])}")
    u = os.path.join(U, "spezzone_" + nome)
    dove = os.path.join(os.path.expanduser("~"), "kr_lavori", "dimezza", "spezzone_" + nome)
    os.makedirs(u, exist_ok=True)
    x = {"spezzone": sp}
    out_tutto["spezzoni"].append(x)
    sc = ScaricatoreP2P(sp["uid"], int(sp["kit"]))
    try:
        with SDK:
            canali = [int(c) for c in sp.get("canali", [0])]
            iv = sc.intervallo(canali[0])
            if not sc.collegamenti or not sc.collegamenti[-1]["ok"]:
                x["esito"] = "registratore non raggiunto: " + (sc.collegamenti[-1]["testo"] if sc.collegamenti else "?")
                return []
            x["registra"] = [str(v) for v in iv] if iv else None
            ok, perche = dz.coperto(iv, da_dt, da_dt + datetime.timedelta(seconds=sec))
            if not ok:
                x["esito"] = perche
                return []
            t1 = time.time()
            finali, misure = scarica_tratto(sc, canali, da_dt, sec, dove, kit)
            x["tratto"] = {"da": da_dt.strftime("%H:%M:%S"), "secondi": sec, "canali": misure,
                           "mb": round(sum((m.get("mb") or 0) for m in misure.values()), 2),
                           "secondi_scarico": round(time.time() - t1, 1)}
            x["esito"] = f"scaricati {len(finali)} video" if finali else "niente scaricato"
            return [(nome, finali, da_dt, u, kit, x["tratto"])] if finali else []
    finally:
        sc.chiudi()
        x["collegamenti"] = sc.collegamenti


def lavoro_dimezza(cfg):
    """dimezza.json: prima tutti gli scarichi (la libreria Focus a pezzi, il ponte intanto risponde), poi le analisi di
    Kit_Rifiuti una alla volta, ognuna con le sue risposte attaccate al suo tratto. Scrive uscita/dimezza.json a ogni
    passo."""
    import kit_rifiuti as kr
    import dimezza as dz
    out = {"pc": PC, "versione": VERSIONE, "dimezza": dz.VERSIONE, "kit_rifiuti": getattr(kr, "VERSION", None) or "?",
           "inizio": time.strftime("%Y-%m-%d %H:%M:%S"), "casi": [], "spezzoni": []}
    da_fare = []
    for caso in cfg.get("casi") or []:
        try:
            da_fare += un_caso(caso, kr, dz, out)
        except Exception as ex:   # noqa: BLE001
            av(f"dimezza {caso.get('nome')}: {type(ex).__name__}: {str(ex)[:300]}")
            av(traceback.format_exc()[-1500:])
        scrivi_json("dimezza.json", out)
    for sp in cfg.get("spezzoni") or []:
        try:
            da_fare += uno_spezzone(sp, kr, out)
        except Exception as ex:   # noqa: BLE001
            av(f"spezzone {sp.get('nome')}: {type(ex).__name__}: {str(ex)[:300]}")
            av(traceback.format_exc()[-1500:])
        scrivi_json("dimezza.json", out)
    for etichetta, finali, da_dt, u, kit, dove_scrivo in da_fare:
        os.makedirs(u, exist_ok=True)
        risultati = os.path.join(os.path.dirname(finali[0]), "..", "risultati")
        t0 = time.time()
        av(f"dimezza {etichetta}: parte Kit_Rifiuti su {len(finali)} video")
        try:
            p = analisi_kit_rifiuti(finali, risultati, os.path.join(u, "analisi.txt"), kit)
            codice = p.wait(timeout=3 * 3600)
        except Exception as ex:   # noqa: BLE001
            dove_scrivo["kit_rifiuti"] = {"errore": f"{type(ex).__name__}: {str(ex)[:300]}"}
            scrivi_json("dimezza.json", out)
            continue
        copia_risultati(risultati, u, t0, codice)
        k = {"codice": codice, "secondi": round(time.time() - t0)}
        try:
            k["abbandoni"] = dz.abbandoni_csv(open(os.path.join(risultati, "eventi.csv"), encoding="utf-8").read(), da_dt)
        except OSError as ex:
            k["abbandoni"], k["nota"] = [], f"eventi.csv non letto: {ex}"
        k["piu_vicino_all_atteso"] = dz.piu_vicino(k["abbandoni"], da_dt.date(), dove_scrivo.get("atteso"))
        dove_scrivo["kit_rifiuti"] = k
        av(f"dimezza {etichetta}: Kit_Rifiuti finito ({codice}) in {k['secondi']} s, {len(k['abbandoni'])} abbandoni")
        scrivi_json("dimezza.json", out)
    out["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    scrivi_json("dimezza.json", out)


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
try:
    parti_misure()   # 0.10.0
except Exception as ex:   # noqa: BLE001
    av(f"misure: {type(ex).__name__}: {str(ex)[:300]}")
for _nome, _segno, _lavoro in (("nas_extra.json", "nas_extra_fatto.txt", nas_extra),
                               ("dimezza.json", "dimezza_fatto.txt", lavoro_dimezza)):   # 0.11.0
    try:
        parti_filo(_nome, _segno, _lavoro)
    except Exception as ex:   # noqa: BLE001
        av(f"{_nome}: {type(ex).__name__}: {str(ex)[:300]}")
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
        if not analisi_lunghe and not misure_in_corso() and compito_nuovo_su_drive():
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
            with SDK:   # 0.11.0: il dimezzamento usa la libreria nel suo filo
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
for t in MISURE_VIVE:   # 0.10.0: le misure (0.11.0: e il dimezzamento) finiscono prima di chiudere (al massimo 3 ore in piu')
    t.join(3 * 3600)
av("fatto")
