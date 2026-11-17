"""
prova_fps1 - le prove a tavolino del compito fps1, senza rete e senza la libreria Focus.
VERSION 0.1.0 (17/11/2026)

Uso: python3 prova_fps1.py [cartella con focus_nvr.py]
(di difetto ../../../kit-rifiuti-programma/scripts, o la variabile FOCUS_NVR).

Prove:
  1. funzioni pure: credenziali, scelta dei kit, scelta dell'ora (di giorno, il margine, ieri, la notte, i buchi),
     unita' NAL e conteggio delle immagini (H.264 e H.265), SPS (risoluzione, tagli, fps dichiarati), calcolo degli fps
     con i tempi al millesimo come li da' il registratore, classi, unione delle prove di un kit, canali da saltare,
     foto una volta al giorno, versione per il sito, riassunto;
  2. con ffmpeg (se c'e'): un H.264 vero a 125/7 fps 640x360 letto da leggi_grezzo;
  3. il compito intero (compito.py -> lavoro.py in processi a parte) con un sito finto (op=prendi a giri, op=esito) e
     un Registratore finto: un kit a 25, uno con una telecamera a 17,857, uno che risponde solo dal secondo giro, uno
     con la seconda password, uno che fa cadere il processo, uno che si pianta; i canali misurati non si riscaricano,
     l'esito arriva al sito per ogni richiesta, archivio e foto come il ponte, niente UID in uscita, video cancellati;
  4. la ripresa: il compito ucciso a meta' riparte dallo stato salvato;
  5. senza sito: il giro ogni ora sui soli kit non ancora misurati.
"""
import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

QUI = os.path.dirname(os.path.abspath(__file__))
VERSION = "0.1.0"


def trova_focus_nvr():
    for d in [sys.argv[1] if len(sys.argv) > 1 else None, os.environ.get("FOCUS_NVR"), QUI,
              os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")]:
        if d and os.path.exists(os.path.join(d, "focus_nvr.py")):
            return os.path.abspath(d)
    raise SystemExit("manca focus_nvr.py (kit-rifiuti-programma/scripts): passalo come argomento")


# ------------------------------------------------------------------ un flusso H.264 finto

class Scrivi:
    def __init__(self):
        self.b = []

    def u(self, n, v):
        self.b += [(v >> (n - 1 - i)) & 1 for i in range(n)]

    def ue(self, v):
        v += 1
        n = v.bit_length()
        self.b += [0] * (n - 1)
        self.u(n, v)

    def byte(self):
        b = self.b + [1]                     # rbsp_stop_one_bit
        b += [0] * (-len(b) % 8)
        out = bytes(int("".join(map(str, b[i:i + 8])), 2) for i in range(0, len(b), 8))
        return re.sub(b"\x00\x00([\x00-\x03])", b"\x00\x00\x03\\1", out)   # emulazione


def sps_finto(larghezza=1920, altezza=1080, fps=25.0, alto=True, vui=True):
    w = Scrivi()
    w.u(8, 100 if alto else 66)
    w.u(8, 0)
    w.u(8, 40)
    w.ue(0)
    if alto:
        w.ue(1)                               # 4:2:0
        w.ue(0)
        w.ue(0)
        w.u(1, 0)
        w.u(1, 0)                             # niente matrici
    w.ue(0)                                   # log2_max_frame_num_minus4
    w.ue(0)                                   # poc tipo 0
    w.ue(2)
    w.ue(1)
    w.u(1, 0)
    mb_w, mb_h = (larghezza + 15) // 16, (altezza + 15) // 16
    w.ue(mb_w - 1)
    w.ue(mb_h - 1)
    w.u(1, 1)                                 # frame_mbs_only
    w.u(1, 1)
    taglio_b = (mb_h * 16 - altezza) // 2
    taglio_d = (mb_w * 16 - larghezza) // 2
    if taglio_b or taglio_d:
        w.u(1, 1)
        w.ue(0)
        w.ue(taglio_d)
        w.ue(0)
        w.ue(taglio_b)
    else:
        w.u(1, 0)
    w.u(1, 1 if vui else 0)
    if vui:
        w.u(1, 0)
        w.u(1, 0)
        w.u(1, 0)
        w.u(1, 0)
        w.u(1, 1)                             # timing_info_present
        tick, scala = 1000, int(round(2000 * fps))
        w.u(32, tick)
        w.u(32, scala)
        w.u(1, 1)
        w.u(1, 0)
        w.u(1, 0)
        w.u(1, 0)
        w.u(1, 0)
    return b"\x67" + w.byte()


def flusso_finto(n, gop=50, fps_sps=25.0, larghezza=1920, altezza=1080, quattro=True):
    sc = b"\x00\x00\x00\x01" if quattro else b"\x00\x00\x01"
    out = b""
    for i in range(n):
        if i % gop == 0:
            out += sc + sps_finto(larghezza, altezza, fps_sps) + sc + b"\x68\xce\x38\x80"
            out += sc + b"\x65\x88" + bytes(range(1, 40))            # IDR, first_mb = 0
        else:
            out += b"\x00\x00\x01" + b"\x41\x9a" + bytes(range(1, 20))  # P, first_mb = 0
            if i % 7 == 0:   # una seconda fetta della stessa immagine (first_mb != 0): non conta
                out += b"\x00\x00\x01" + b"\x41\x30" + bytes(range(1, 10))
    return out


# ------------------------------------------------------------------ il Registratore finto (per lavoro.py)

class RegistratoreFinto:
    """Le stesse funzioni di focus_nvr.Registratore che usano fps e ponte_pezzi. opz: {"kit": {UID: {...}},
    "conti": cartella dei contatori}. Per UID: fps (per canale), risponde_dal (numero della prova da cui risponde),
    password (quale delle credenziali e' giusta, da 0), crash, pianta, codec."""

    def __init__(self, opz):
        self.o = opz
        self.server, self.this, self.k, self.uid = 0, 1, {}, None
        self.f = {"Disconnect": lambda *_: None}

    def _conta(self, nome):
        p = os.path.join(self.o["conti"], nome)
        n = int(open(p).read()) + 1 if os.path.exists(p) else 1
        open(p, "w").write(str(n))
        return n

    def collega(self, uid, utente, password, porta=9010, p2p=True, attesa=25):
        self.uid, self.k = uid, self.o["kit"].get(uid, {})
        prova = self._conta(f"collega_{uid}_{utente}")
        if self.k.get("crash"):
            os.abort()
        if prova < int(self.k.get("risponde_dal", 1)) or self.k.get("muto"):
            return False, f"nessuna risposta in {attesa} s"
        if utente != self.k.get("utente", "u1"):
            return False, "password sbagliata"
        self.server = 7
        return True, "collegato (" + self.k.get("modo", "P2P diretto") + ")"

    def info(self):
        return {"modello": "FNR-3004", "telecamere": len(self.k.get("fps", [])), "permessi": "riproduzione"}

    def canali(self):
        return [(i + 1, 100 + i, f"CH{i + 1}") for i in range(len(self.k.get("fps", [])))]

    def minuti_registrati(self, h, giorno):
        return [] if (h - 100) in self.k.get("vuoti", []) else [(0, 1440, 1)]

    def giorni_registrati(self, h, mese):
        return [1, 2, 3]

    def intervallo(self, h):
        return datetime.datetime(2026, 10, 1), datetime.datetime(2026, 11, 17, 10)

    def scarica(self, num, h, inizio, secondi, cartella, attesa_vuoto=30, ffmpeg="ffmpeg"):
        import focus_nvr as fn
        self._conta(f"{'foto' if secondi == 3 else 'scarica'}_{self.uid}")   # le foto del ponte sono di 3 secondi
        if self.k.get("pianta"):
            time.sleep(3600)
        f = self.k["fps"][num - 1]
        os.makedirs(cartella, exist_ok=True)
        n = int(f * secondi)
        tempi = [inizio + datetime.timedelta(milliseconds=int(1000 * i / f)) for i in range(n)]
        g = os.path.join(cartella, fn.nome_per_kit_rifiuti(inizio, num) + ".grezzo")
        with open(g, "wb") as fh:
            fh.write(flusso_finto(n, fps_sps=25.0))
        try:   # come il vero: il .mp4 con un ffmpeg che non c'e' non si fa, resta il grezzo
            subprocess.run([ffmpeg, "-version"], capture_output=True)
        except OSError:
            pass
        return {"canale": num, "codec": "H.264", "misura": "1920x1080", "fotogrammi": n, "mb": 1.0, "attesa_s": 2.0,
                "fps": fn.fps_da_tempi(tempi), "primo": tempi[0].isoformat(sep=" "), "ultimo": tempi[-1].isoformat(sep=" "),
                "velocita": 5.0, "file": g}

    def chiudi(self):
        pass


# ------------------------------------------------------------------ il sito finto (per compito.py)

def sito_finto(cartella, op, dati):
    """op=prendi: le richieste del giro una alla volta; finiti i giri, scrive ferma.txt nella cartella del compito.
    op=esito: in esiti.jsonl. op=stato: i kit."""
    s = json.load(open(os.path.join(cartella, "sito.json")))
    if op == "prendi":
        if not s["coda"] and s["giri"] > 0:
            s["giri"] -= 1
            s["coda"] = [{"id": s["prossimo"] + i, "kit": f"Prova · {n} - Via", "uid": u, "priorita": 0,
                          "serve_archivio": s["giri"] == s["giri_tot"] - 1}
                         for i, (u, n) in enumerate(s["registratori"])]
            s["prossimo"] += len(s["registratori"])
        rq = s["coda"].pop(0) if s["coda"] else None
        if rq is None and s["giri"] == 0:
            open(os.path.join(s["compito"], "ferma.txt"), "w").write("fine dei giri")
        json.dump(s, open(os.path.join(cartella, "sito.json"), "w"))
        return {"richiesta": rq}
    if op == "esito":
        with open(os.path.join(cartella, "esiti.jsonl"), "a") as fh:
            fh.write(json.dumps(dati) + "\n")
        return {"ok": True}
    if op == "stato":
        return {"kit": [{"uid": u, "kit": str(n), "stato": "fatto", "risposte_24h": 1} for u, n in s["registratori"]]}
    raise ValueError(op)


# ------------------------------------------------------------------ prove

def controlla(cond, testo):
    if not cond:
        raise AssertionError(testo)
    print("  ok:", testo)


def prove_pure():
    import fps
    import focus_nvr as fn
    print("1. funzioni pure")
    acc = fps.leggi_accesso([])
    controlla(fps.credenziali("AB", 300, acc) == [], "senza focus_accesso.txt nessuna credenziale")
    acc = ({"AB": ("x", "y")}, [("u1", "p1")], [("u0", "p0")])
    controlla(fps.credenziali("ab", 150, acc) == [("x", "y"), ("u0", "p0"), ("u1", "p1")], "kit sotto 200: prima «*<200»")
    controlla(fps.credenziali("cd", 300, acc) == [("u1", "p1"), ("u0", "p0")], "kit dal 200: prima «*»")
    st = {"kit": [{"uid": "A", "kit": "252", "risposte_24h": 3}, {"uid": "B", "kit": "261", "risposte_24h": 0, "stato": "fatto"},
                  {"uid": "C", "kit": "300", "risposte_24h": 0, "stato": "fallito"}, {"uid": "a", "kit": "252"},
                  {"uid": "D", "kit": "998", "risposte_24h": 5}]}
    sc, sa = fps.scegli_kit(st)
    controlla([k["etichetta"] for k in sc] == ["KIT252", "KIT261"] and sa[0]["etichetta"] == "KIT300",
              "scelta dei kit: chi risponde prima, i muti saltati, doppioni e 998 fuori")
    sc, _ = fps.scegli_kit(st, anche_muti=True)
    controlla(len(sc) == 3, "con anche_muti ci sono tutti")
    sc, _ = fps.kit_da_registratori({"341": {"uid": "X"}, "52": {"uid": "Y"}})
    controlla([k["etichetta"] for k in sc] == ["KIT52", "KIT341"], "registratori.json in ordine di numero")

    adesso = datetime.datetime(2026, 11, 17, 14, 0)
    tutto = [(0, 1440, 1)]
    t, p = fps.scegli_inizio([(0, 14 * 60, 1)], tutto, adesso)
    controlla(t == datetime.datetime(2026, 11, 17, 13, 48, 20) and "di giorno, oggi" in p,
              f"di giorno oggi, il piu' recente con 10 minuti di margine ({t}, {p})")
    t, p = fps.scegli_inizio([(0, 8 * 60, 1)], [(9 * 60, 12 * 60, 2)], adesso)
    controlla(t == datetime.datetime(2026, 11, 16, 11, 58, 20) and "ieri" in p and "movimento" in p,
              f"oggi solo di notte: di giorno ieri ({p})")
    t, p = fps.scegli_inizio([(0, 8 * 60, 1)], [(20 * 60, 22 * 60, 1)], adesso)
    controlla(t == datetime.datetime(2026, 11, 17, 7, 58, 20) and "non di giorno" in p, f"niente di giorno: la notte ({p})")
    t, p = fps.scegli_inizio([(600, 601, 1), (700, 701, 1)], [], adesso)
    controlla(t == datetime.datetime(2026, 11, 17, 11, 40, 20) and "buco" in p, f"solo minuti isolati ({p})")
    t, p = fps.scegli_inizio([(835, 845, 1)], [], adesso)
    controlla(t is None, "solo gli ultimi minuti, ancora in scrittura: niente")
    controlla(fps.scegli_inizio(None, None, adesso)[0] is None, "niente registrato")
    adesso2 = datetime.datetime(2026, 11, 17, 0, 5)
    t, p = fps.scegli_inizio(tutto, tutto, adesso2)
    controlla(t.date() == datetime.date(2026, 11, 16) and t.hour == 16 and t.minute == 59, f"appena dopo mezzanotte: ieri ({t})")

    dati = flusso_finto(120, gop=50)
    nal = fps.unita_nal(dati)
    controlla(fps.conta_fotogrammi(nal) == (120, 3), "H.264: 120 immagini, 3 chiave, le seconde fette non contano")
    controlla(fps.conta_fotogrammi(fps.unita_nal(flusso_finto(30, quattro=False))) == (30, 1), "codici d'inizio a 3 byte")
    h265 = b"".join(b"\x00\x00\x01" + bytes([(19 if i == 0 else 1) << 1, 1, 0x80 if j == 0 else 0x40]) + b"\x11\x22"
                    for i in range(40) for j in range(2))
    controlla(fps.conta_fotogrammi(fps.unita_nal(h265), "H.265") == (40, 1), "H.265: 40 immagini da due fette, 1 chiave")
    s = fps.leggi_sps_h264(sps_finto(1920, 1080, 17.857))
    controlla((s["larghezza"], s["altezza"], s["fps_sps"], s["profilo"]) == (1920, 1080, 17.857, 100),
              f"SPS High 1920x1080 tagliato, 17.857 dichiarati ({s})")
    s = fps.leggi_sps_h264(sps_finto(704, 576, 25, alto=False))
    controlla((s["larghezza"], s["altezza"], s["fps_sps"]) == (704, 576, 25.0), "SPS Baseline 704x576 a 25")
    s = fps.leggi_sps_h264(sps_finto(640, 360, vui=False))
    controlla(s["fps_sps"] is None and s["altezza"] == 360, "SPS senza tempi: fps_sps None")

    inizio = datetime.datetime(2026, 11, 17, 13, 0, 20)
    for f in (25.0, 17.857, 12.5):
        n = int(f * 10)
        tempi = [inizio + datetime.timedelta(milliseconds=int(1000 * i / f)) for i in range(n)]
        res = {"codec": "H.264", "misura": "1920x1080", "fotogrammi": n, "fps": fn.fps_da_tempi(tempi),
               "primo": tempi[0].isoformat(sep=" "), "ultimo": tempi[-1].isoformat(sep=" ")}
        m = fps.misura_canale(res, {"fotogrammi_grezzo": n, "chiave": 4, "sps": {"larghezza": 1920, "altezza": 1080,
                                                                                 "fps_sps": 25.0}}, inizio, 10)
        controlla(abs(m["fps"] - f) / f < 0.03 and abs(m["fps_grezzo"] - f) / f < 0.03 and abs(m["fps_conteggio"] - f) / f < 0.03
                  and not m["discordanti"] and abs(m["accelerazione_se_letto_a_25"] - 25 / f) < 0.05,
                  f"{f} fps: tempi {m['fps_tempi']}, conteggio {m['fps_conteggio']}, grezzo {m['fps_grezzo']}, "
                  f"accelerazione {m['accelerazione_se_letto_a_25']}")
    m = fps.misura_canale({"fotogrammi": 0, "errore": "nessun fotogramma per 20 s"}, None, inizio, 10)
    controlla(m["fps"] is None and m["esito"].startswith("nessun fotogramma"), "scarico vuoto: niente fps")
    tempi = [inizio + datetime.timedelta(milliseconds=56 * i) for i in range(100)]
    m = fps.misura_canale({"fotogrammi": 100, "fps": fn.fps_da_tempi(tempi), "primo": str(tempi[0]), "ultimo": str(tempi[-1])},
                          {"fotogrammi_grezzo": 250}, inizio, 10)
    controlla(m["discordanti"], "tempi a 17,857 ma 250 immagini nel file: discordanti")
    controlla(fps.classe_fps(17.86) == "17.857" and fps.classe_fps(24.9) == "25.0" and fps.classe_fps(22).startswith("altro"),
              "classi di frequenza")

    q = datetime.datetime(2026, 11, 17, 13, 5)
    k = fps.unisci(None, {"collegato": False, "esito": "non collegato: nessuna risposta in 20 s"}, q)
    controlla(k["non_risposto"] == 1 and not k["risposte"] and not k["misurato"], "una prova senza risposta")
    lav = {"collegato": True, "canali_n": 2, "modello": "FNR", "foto_fatte": True,
           "canali": [{"canale": 1, "fps": 17.857}, {"canale": 2, "esito": "nessun fotogramma: x"}]}
    k = fps.unisci(k, lav, q.replace(hour=21))
    controlla(k["ore_risposta"] == [21] and k["risposte_n"] == 1 and k["non_risposto"] == 1 and k["foto_il"] == "2026-11-17",
              "poi risponde alle 21: ora, conti, foto del giorno")
    controlla(fps.canali_da_saltare(k) == [1] and not k["misurato"], "il canale 1 misurato si salta, il 2 no")
    controlla(not fps.serve_foto(k, datetime.date(2026, 11, 17)) and fps.serve_foto(k, datetime.date(2026, 11, 18)),
              "foto una volta al giorno")
    k = fps.unisci(k, {"collegato": True, "canali_n": 2, "canali": [{"canale": 1, "esito": "errore"}, {"canale": 2, "fps": 25.0}]},
                   q.replace(hour=22))
    controlla(k["canali"][0]["fps"] == 17.857 and k["canali"][1]["fps"] == 25.0 and k["misurato"],
              "una prova andata male non toglie una misura; ora il kit e' misurato")
    k2 = {"risposte": ["x"], "canali_n": 1, "canali": [{"canale": 1, "tentativi": 6}]}
    controlla(fps.kit_misurato(k2), "un canale senza misura dopo 6 prove si chiude")
    mappa = {}
    controlla(fps.etichetta_per_uid("aa", "ALEA · 136 - Via", mappa) == "KIT136"
              and fps.etichetta_per_uid("bb", "ALEA · 136 - Via", mappa) == "KIT136#2"
              and fps.etichetta_per_uid("AA", "x", mappa) == "KIT136", "etichette: stesso UID stessa etichetta, doppioni #2")
    v = fps.versione_per_il_sito("p2p_ponte 0.20.1")
    controlla(len(v) <= 20 and not re.search(r" 0\.[0-6]\.", v) and not re.search(r"0\.1\.", v),
              f"la versione per il sito «{v}» non cade nelle regole vecchie del sito")
    controlla(fps.prossimo_giro(0, 100.0) == 100.0 and fps.prossimo_giro(50.0, 100.0, 3600) == 3650.0, "giro ogni ora")
    r = fps.riassunto({"KIT2": k, "KIT10": {"collegato": False, "non_risposto": 3, "esito": "mai"}})
    controlla(r["telecamere_sotto_soglia"] == 1 and r["telecamere_sotto_24_fps"][0]["kit"] == "KIT2"
              and r["kit_non_collegati"][0]["kit"] == "KIT10" and r["per_kit"][0]["ore_risposta"] == [21, 22],
              "riassunto: sotto 24 fps, non collegati, ore di risposta per kit")


def prova_ffmpeg():
    import fps
    print("2. un H.264 vero fatto da ffmpeg")
    if not shutil.which("ffmpeg"):
        print("  (ffmpeg non c'e': saltata)")
        return
    d = tempfile.mkdtemp()
    f = os.path.join(d, "x.h264")
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=125/7", "-t", "4",
                        "-c:v", "libx264", "-g", "36", "-bsf:v", "h264_metadata=tick_rate=250/7", "-f", "h264", f],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("  (ffmpeg senza libx264: saltata)", r.stderr[-200:])
        return
    n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", f], capture_output=True, text=True).stdout.strip())
    g = fps.leggi_grezzo(f)
    controlla(g["fotogrammi_grezzo"] == n, f"immagini contate {g['fotogrammi_grezzo']} = ffprobe {n}")
    controlla(g["sps"]["larghezza"] == 640 and g["sps"]["altezza"] == 360, f"risoluzione dall'SPS {g['sps']}")
    controlla(g["sps"]["fps_sps"] and abs(g["sps"]["fps_sps"] - 17.857) < 0.01, f"fps dichiarati {g['sps']['fps_sps']}")
    shutil.rmtree(d, ignore_errors=True)


KIT_FINTI = {
    "UIDA00000001": {"n": 252, "fps": [25.0, 25.0, 25.0, 25.0]},
    "UIDB00000002": {"n": 261, "fps": [25.0, 17.857, 25.0], "modo": "relay (5 minuti al massimo)"},
    "UIDC00000003": {"n": 341, "fps": [17.857, 17.857], "risponde_dal": 2},
    "UIDD00000004": {"n": 150, "fps": [12.5], "utente": "u0"},
    "UIDE00000005": {"n": 373, "fps": [25.0], "crash": True},
    "UIDF00000006": {"n": 461, "fps": [25.0, 25.0], "pianta": True},
    "UIDG00000007": {"n": 506, "fps": [25.0, 20.0], "vuoti": [0]},
}


def prepara(fnvr, giri=3, cfg_in_piu=None):
    base = tempfile.mkdtemp(prefix="fps1_")
    c = os.path.join(base, "fps1")
    os.makedirs(c)
    for f in ("compito.py", "lavoro.py", "fps.py", "ponte_pezzi.py", "fps.json", "prova_fps1.py"):
        shutil.copy2(os.path.join(QUI, f), c)
    shutil.copy2(os.path.join(fnvr, "focus_nvr.py"), c)
    open(os.path.join(c, "focus_accesso.txt"), "w").write("*;u1;p1\n*<200;u0;p0\n")
    cfg = json.load(open(os.path.join(c, "fps.json")))
    cfg.update({"controlla_drive": False, "tetto_kit_min": 0.1, "margine_kit_s": 1, "grazia_s": 2,
                "pausa_coda_vuota_s": 0.2, "attesa": 1})
    cfg.update(cfg_in_piu or {})
    json.dump(cfg, open(os.path.join(c, "fps.json"), "w"))
    sito = os.path.join(base, "sito")
    conti = os.path.join(base, "conti")
    os.makedirs(sito)
    os.makedirs(conti)
    json.dump({"coda": [], "giri": giri, "giri_tot": giri, "prossimo": 1, "compito": c,
               "registratori": [[u, v["n"]] for u, v in KIT_FINTI.items()]}, open(os.path.join(sito, "sito.json"), "w"))
    env = dict(os.environ, FPS1_SITO_FINTO=sito, PYTHONPATH=c,
               FPS1_FINTA=json.dumps({"kit": {u: v for u, v in KIT_FINTI.items()}, "conti": conti}))
    return base, c, sito, conti, env


def leggi_conto(conti, nome):
    p = os.path.join(conti, nome)
    return int(open(p).read()) if os.path.exists(p) else 0


def prova_compito(fnvr):
    print("3. il compito intero, sito e libreria finti, tre giri")
    base, c, sito, conti, env = prepara(fnvr)
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(c, "compito.py"), c], env=env, capture_output=True, text=True,
                       timeout=600)
    av = open(os.path.join(c, "uscita", "avanzamento.txt"), encoding="utf-8").read()
    if r.returncode != 0 or not av.rstrip().endswith("fatto"):
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise AssertionError("il compito non e' finito")
    print(f"  ({round(time.time() - t0)} s)")
    ris = json.load(open(os.path.join(c, "uscita", "risultato.json"), encoding="utf-8"))
    kit, rs = ris["kit"], ris["riassunto"]
    controlla(sorted(kit) == sorted(f"KIT{v['n']}" for v in KIT_FINTI.values()), "un risultato per ogni kit")
    sotto = {(x["kit"], x["canale"]) for x in rs["telecamere_sotto_24_fps"]}
    controlla(sotto == {("KIT261", 2), ("KIT341", 1), ("KIT341", 2), ("KIT150", 1), ("KIT506", 2)},
              f"telecamere sotto 24 fps: {sorted(sotto)}")
    b = kit["KIT261"]["canali"][1]
    controlla(abs(b["fps"] - 17.857) < 0.05 and abs(b["fps_grezzo"] - 17.857) < 0.5 and b["fps_sps"] == 25.0
              and b["risoluzione_sps"] == "1920x1080" and abs(b["accelerazione_se_letto_a_25"] - 1.4) < 0.01,
              f"KIT261 CH2: {b['fps']} fps dai tempi, {b['fps_grezzo']} dal file, il flusso dichiara {b['fps_sps']}")
    controlla(kit["KIT341"]["non_risposto"] == 1 and kit["KIT341"]["risposte_n"] == 2 and kit["KIT341"]["misurato"],
              "KIT341 muto al primo giro, misurato dopo: 1 non risposto, 2 risposte")
    controlla(kit["KIT150"]["misurato"], "KIT150 entra con la seconda password («*<200» prima per i kit sotto 200)")
    controlla(kit["KIT373"]["non_risposto"] == 3 and "caduto" in str(kit["KIT373"].get("ultimo_errore")),
              f"KIT373 fa cadere il processo a ogni giro: {kit['KIT373'].get('ultimo_errore')}")
    controlla(kit["KIT461"]["risposte_n"] == 3 and not kit["KIT461"]["misurato"]
              and kit["KIT461"]["canali"] and kit["KIT461"]["canali"][0]["tentativi"] == 2
              and "durante lo scarico" in kit["KIT461"]["canali"][0]["esito"],
              "KIT461 si pianta allo scarico: foto tentate solo al 1o giro, poi CH1 ucciso al tetto e contato")
    controlla(kit["KIT506"]["canali"][0]["tentativi"] == 3 and not kit["KIT506"]["canali"][0].get("fps"),
              "KIT506 CH1 senza registrazioni: riprovato a ogni giro")
    controlla(leggi_conto(conti, "scarica_UIDA00000001") == 4 and leggi_conto(conti, "scarica_UIDB00000002") == 3,
              "i canali misurati non si riscaricano nei giri dopo")
    esiti = [json.loads(x) for x in open(os.path.join(sito, "esiti.jsonl"))]
    controlla(len(esiti) == 3 * len(KIT_FINTI) and len({e["id"] for e in esiti}) == len(esiti),
              f"un esito al sito per ogni richiesta ({len(esiti)})")
    controlla(all(e["versione"] == "p2p_ponte 0.20.1+fps" for e in esiti), "con la versione del ponte")
    ok = [e for e in esiti if e["ok"]]
    controlla(all(e["esito"].get("canali") and "minuti_24h" in e["esito"]["canali"][0] for e in ok),
              "gli esiti riusciti hanno i canali come il ponte (minuti_24h, ore_oggi...)")
    con_archivio = [e for e in ok if "archivio" in e["esito"]]
    controlla(con_archivio and all(e["id"] <= len(KIT_FINTI) for e in con_archivio)
              and con_archivio[0]["esito"]["archivio"][0]["giorni"], "l'archivio solo quando il sito lo chiede (1o giro)")
    controlla(leggi_conto(conti, "foto_UIDA00000001") == 4 and leggi_conto(conti, "foto_UIDC00000003") == 2
              and sum(1 for e in ok if "camere" in e["esito"]) == 5,
              "le foto una volta al giorno per kit (KIT341 al 2o giro, quando risponde)")
    crash = [e for e in esiti if not e["ok"] and "caduto" in str(e["esito"].get("errore"))]
    controlla(len(crash) == 3, "anche il kit caduto manda l'esito al sito (la richiesta non resta «in corso»)")
    testo = open(os.path.join(c, "uscita", "risultato.json"), encoding="utf-8").read()
    controlla(not any(u in testo or u.lower() in testo for u in KIT_FINTI) and "p1" not in testo.split('"parametri"')[0],
              "niente UID ne' password nel risultato")
    controlla(not os.path.exists(os.path.join(c, "lavori")), "lavori/ cancellata (UID e video)")
    controlla(not [f for _r, _d, fs in os.walk(c) for f in fs if f.endswith((".grezzo", ".mp4"))], "nessun video rimasto")
    controlla(os.path.isdir(os.path.join(c, "uscita", "guasti")), "il guasto del processo caduto in uscita/guasti")
    controlla("mi fermo: ferma.txt" in av, "si ferma con ferma.txt")
    shutil.rmtree(base, ignore_errors=True)


def prova_ripresa(fnvr):
    print("4. la ripresa dopo una caduta del compito")
    base, c, sito, conti, env = prepara(fnvr, giri=2)
    p = subprocess.Popen([sys.executable, os.path.join(c, "compito.py"), c], env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    f = os.path.join(c, "uscita", "risultato.json")
    t0 = time.time()
    while time.time() - t0 < 120:
        r = json.load(open(f)) if os.path.exists(f) else {}
        if len(r.get("kit") or {}) >= 2:
            break
        time.sleep(0.2)
    p.send_signal(signal.SIGKILL)
    p.wait()
    prima = json.load(open(f))
    stato = json.load(open(os.path.join(c, "uscita", "stato.json")))
    controlla(stato["fase"] == "in corso" and len(prima["kit"]) >= 2, f"ucciso dopo {len(prima['kit'])} kit")
    scariche_a = leggi_conto(conti, "scarica_UIDA00000001")
    r = subprocess.run([sys.executable, os.path.join(c, "compito.py"), c], env=env, capture_output=True, text=True,
                       timeout=600)
    dopo = json.load(open(f))
    controlla(dopo["ripreso"] and dopo["riavvii"] == 1 and dopo["primo_avvio"] == prima["primo_avvio"],
              "ripreso: stesso primo avvio (le 24 ore contano da li'), un riavvio")
    controlla(dopo["kit"]["KIT252"]["misurato"] and leggi_conto(conti, "scarica_UIDA00000001") == max(4, scariche_a),
              "KIT252 misurato prima della caduta non si riscarica")
    controlla(json.load(open(os.path.join(c, "uscita", "stato.json")))["fase"] == "finito", "poi finisce")
    shutil.rmtree(base, ignore_errors=True)


def prova_da_solo(fnvr):
    print("5. senza sito: un giro ogni ora (qui ogni 6 secondi) sui kit non ancora misurati")
    base, c, sito, conti, env = prepara(fnvr, cfg_in_piu={"fonte": "da_solo", "giro_ogni_min": 0.1, "durata_ore": 0.006})
    scelti = [{"uid": u, "numero": v["n"], "etichetta": f"KIT{v['n']}"} for u, v in KIT_FINTI.items()
              if not v.get("crash") and not v.get("pianta")]
    json.dump(scelti, open(os.path.join(c, "kit.json"), "w"))
    r = subprocess.run([sys.executable, os.path.join(c, "compito.py"), c], env=env, capture_output=True, text=True,
                       timeout=300)
    av = open(os.path.join(c, "uscita", "avanzamento.txt"), encoding="utf-8").read()
    ris = json.load(open(os.path.join(c, "uscita", "risultato.json"), encoding="utf-8"))
    giri = re.findall(r"giro da solo: (\d+) kit da misurare su (\d+)", av)
    controlla(len(giri) >= 2 and giri[0] == ("5", "5") and int(giri[1][0]) < 5,
              f"il secondo giro prende solo i non misurati: {giri}")
    controlla(ris["kit"]["KIT341"]["misurato"] and ris["kit"]["KIT341"]["non_risposto"] == 1, "KIT341 preso al 2o giro")
    controlla(not os.path.exists(os.path.join(sito, "esiti.jsonl")), "niente al sito")
    controlla("ore finite" in av and av.rstrip().endswith("fatto"), "si ferma a fine tempo")
    shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    fnvr = trova_focus_nvr()
    sys.path.insert(0, QUI)
    sys.path.insert(0, fnvr)
    prove_pure()
    prova_ffmpeg()
    prova_compito(fnvr)
    prova_ripresa(fnvr)
    prova_da_solo(fnvr)
    print("prove passate")
