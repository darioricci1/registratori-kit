"""
ponte_pezzi - i pezzi del ponte che il compito fps1 rifa' nello stesso collegamento, COPIATI dal ponte piu' recente
(compiti/p2p_ponte6/compito.py, VERSIONE «p2p_ponte 0.20.1»), cosi' la pagina «Registrazioni dei kit»
(https://prova-nvr-remoto.vercel.app/stato.html) riceve le stesse cose che le manda il ponte (op=esito di api/p2p.js):
  - stato_leggero(): la parte «leggera» di prova_con (priorita 0): registratore, canali, minuti di oggi e delle ultime
    24 ore, le 24 ore in lettere; ogni volta;
  - archivio(): prima e ultima registrazione e minuti di ogni giorno dal 27/10, quando il sito lo chiede
    (serve_archivio: una volta ogni 24 ore per registratore);
  - foto_camere(): 3 secondi dall'ultimo minuto registrato, una foto da 480 pixel e il giudizio; qui una volta al
    giorno per kit (il ponte la fa a ogni giro).
VERSION 0.1.0 (17/11/2026)

Le funzioni sono quelle del ponte riga per riga; cambiano solo: U (la cartella dove il ponte scrive foto e video, qui
quella del processo del kit, la mette lavoro.py) e stato_leggero, che e' il pezzo di prova_con prima del «return» del
giro leggero, senza il collegamento (fatto da fps.collega) e senza le foto (le chiama lavoro.py, una volta al giorno).
Se il ponte cambia queste funzioni, vanno ricopiate qui.
"""
import base64
import datetime
import os
import shutil
import subprocess
import sys

VERSION = "0.1.0"
VERSIONE_PONTE = "p2p_ponte 0.20.1"   # da dove vengono le funzioni qui sotto
U = os.getcwd()                        # la mette lavoro.py


def stato_leggero(reg, fn):
    """Dal ponte, prova_con con r['priorita'] == 0, dopo il collegamento: registratore e canali come li vuole il sito."""
    es = {}
    es["registratore"] = reg.info()
    oggi = datetime.datetime.combine(datetime.date.today(), datetime.time())
    adesso = datetime.datetime.now()
    min_ora = adesso.hour * 60 + adesso.minute
    canali = []
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
    es["canali"] = canali
    return es, oggi


# ------------------------------------------------------------------ copiate dal ponte (p2p_ponte 0.20.1)

def ffmpeg():
    return shutil.which("ffmpeg") or os.path.join(getattr(sys, "_MEIPASS", ""), "ffmpeg.exe")


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


