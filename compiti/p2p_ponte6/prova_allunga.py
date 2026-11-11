"""Prove a tavolino di allunga.py, allunga_lavoro.py e prepara_allunga.py: libreria finta (un registratore che risponde
da una tabella di registrazioni, con perdite e buchi a comando), niente rete, niente DLL. In fondo un evento intero in un
processo a parte, come sul PC: compito.py del ponte, allunga_lavoro.py e un focus_nvr finto che fa mp4 veri con ffmpeg
(se ffmpeg c'e'), e un processo che cade con un errore di memoria.
Uso: python3 prova_allunga.py
version: 0.1.0 (11/11/2026)
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import allunga as al   # noqa: E402
import prepara_allunga as pa   # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


D = datetime.datetime
S = D(2026, 11, 1, 13, 0, 0)          # inizio della clip
EV = {"evento": "abcdef0123", "kit": 581, "uid": "X" * 20, "giorno": "2026-11-01", "ora_inizio_clip": "13:00:00",
      "durata_clip": 30, "canali": [0, 1, 2], "prima_s": 60, "dopo_s": 120, "durate_canali": {"0": 30, "1": 30, "2": 30}}


def sec(x):
    return datetime.timedelta(seconds=x)


# ------------------------------------------------------------------ funzioni pure
tr = al.tratti(dict(EV, canali=[0, 2, 3], durate_canali={"0": 30, "2": 10}))
ok([t[0] for t in tr[0]] == ["prima", "dopo"] and tr[0][0][1] == S - sec(60) and tr[0][1][2] == S + sec(150), "tratti: prima e dopo")
ok([t[0] for t in tr[2]] == ["prima", "buco", "dopo"] and tr[2][1][1:] == (S + sec(10), S + sec(30)), "tratti: il buco della telecamera corta")
ok(tr[3] == [("intera", S - sec(60), S + sec(150))], "tratti: un canale che la clip non ha si chiede intero")
ok(al.tratti(dict(EV, prima_s=0))[0][0][0] == "dopo", "tratti: prima_s 0, niente prima")

t = ("prima", S - sec(60), S)
ok(al.dentro_registrazione(t, None) == (t, None), "registrazione non detta: si prova")
g, n = al.dentro_registrazione(t, (S + sec(5), S + sec(999)))
ok(g is None and n.startswith("non piu'"), "registrazione: tratto gia' sovrascritto")
g, n = al.dentro_registrazione(t, (S - sec(20), S + sec(999)))
ok(g == ("prima", S - sec(20), S) and "40 s" in n, "registrazione: tratto a meta'")
g, n = al.dentro_registrazione(t, (S - sec(999), S - sec(100)))
ok(g is None and n.startswith("non ancora"), "registrazione: tratto dopo l'ultima")

tt = [S + sec(i / 10) for i in range(50)] + [S + sec(8 + i / 10) for i in range(20)]
ok(al.primo_salto(tt) == 49 and al.primo_salto(tt[:50]) is None, "primo salto fra due fotogrammi")
b = al.buchi_di([(S + sec(3), S + sec(20)), (S + sec(25), S + sec(59.95))], S, S + sec(60))
ok(b == [(S + sec(20), S + sec(25))], "buchi: il fotogramma chiave all'inizio si tollera, il salto in mezzo no")
b = al.buchi_di([(S + sec(8), S + sec(40))], S, S + sec(60))
ok(b == [(S, S + sec(8)), (S + sec(40), S + sec(60))], "buchi: inizio oltre 6 s e fine anticipata")
ok(al.buchi_di([], S, S + sec(60)) == [(S, S + sec(60))], "buchi: niente scaricato")

pc = {0: {"prima": {"pezzi": [(S, S + sec(60))], "buchi": []}},
      1: {"prima": {"pezzi": [(S + sec(0.5), S + sec(60))], "buchi": []}}}
ok(al.sincronia(pc)["prima"]["esito"] == "sincroni", "sincronia: sincroni")
pc[1]["prima"]["pezzi"] = [(S + sec(4), S + sec(60))]
ok(al.sincronia(pc)["prima"]["esito"].startswith("sfasati"), "sincronia: sfasati")
pc[1]["prima"]["buchi"] = [(S, S + sec(4))]
x = al.sincronia(pc)["prima"]
ok(x["esito"].startswith("con buchi") and x["mancanti_s"]["1"] == 4, "sincronia: con buchi, i secondi mancanti per canale")
ok(al.sincronia({0: pc[0]})["prima"]["esito"] == "un canale solo", "sincronia: un canale solo")

ok("memoria" in al.esito_processo(3221225477) and al.esito_processo(0) == "finito", "codice d'uscita in parole")
lim, tempi = al.limiti_da({"limiti": {"minuti_per_caso": 5, "ore_in_tutto": 99}, "tempi": {"collega": 10, "nuovo": 999}})
ok(lim["minuti_per_caso"] == 5 and lim["ore_in_tutto"] == al.LIMITI["ore_in_tutto"], "i limiti si abbassano, non si alzano")
ok(tempi["collega"] == 10 and tempi["nuovo"] == al.TEMPI["nuovo"], "i tempi per chiamata si abbassano, non si alzano")
ok(al.nome_pezzo(0, "prima", D(2026, 10, 21, 16, 3, 58), D(2026, 10, 21, 16, 4, 57)) == "CH1_prima_20261021-160358_160457",
   "nome del pezzo con l'ora vera")

# ------------------------------------------------------------------ prepara_allunga
ok(pa.numero_kit("KIT560 Zona") == (560, False) and pa.numero_kit("KIT 452 x") == (452, False), "numero del kit")
ok(pa.numero_kit("EX KIT450 SP325") == (450, True) and pa.numero_kit("EXKIT666 Corso") == (666, True), "kit spostato")
ok(pa.numero_kit("Via Roma") == (None, False), "niente kit")
ok(pa.ora_dal_nome("a mano 160458") == "16:04:58" and pa.ora_dal_nome("targa AB123CD 083338") == "08:33:38", "ora dal nome")
ok(pa.ora_dal_nome("a mano 20250101S(1)") is None and pa.ora_dal_nome("a mano 256000") is None, "nome senza ora")
righe = [{"evento": "7b56bc2ce8", "cam": 3, "nota": "", "dati": {"durata": 218.6, "durata_nas": 218.6, "completo": "true"}},
         {"evento": "7b56bc2ce8", "cam": 1, "nota": "", "dati": {"durata": 218.2, "durata_nas": None}},
         {"evento": "7b56bc2ce8", "cam": 2, "nota": "", "dati": {"durata": 3.1, "durata_nas": 3.0}}]
ok(pa.motivi(righe)[0].startswith("Dario in Guarda") and any("sotto 5 s: 2" in m for m in pa.motivi(righe)), "motivi")
ok(pa.motivi([dict(r, evento="0000000000", dati={"durata": 50}) for r in righe]) == [], "nessun motivo")
ok(pa.motivi([dict(righe[0], evento="0000000000", dati={"durata": 50, "non_intero": "cartella «targa AB123CD 071433»"})])
   == ["non intero: cartella «targa [targa] 071433»"], "le targhe non vanno nel json")
ok(any(m.startswith("nota di Dario") for m in pa.motivi([dict(righe[0], evento="0000000000", nota="SEMBRA TAGLIATO")])),
   "motivo: nota di Dario")
ok(pa.durate_per_canale(righe) == {2: 218.6, 0: 218.2, 1: 3.0} and pa.durata_clip(righe) == 218.6, "durate per canale e clip")
stato = {"kit": [{"kit": "581", "uid": "A" * 20, "stato": "fallito", "finito_il": "2026-11-11", "gruppo": "G", "nome": "581"},
                 {"kit": "581", "uid": "B" * 20, "stato": "fatto", "finito_il": "2026-11-10", "gruppo": "G", "nome": "581 b",
                  "canali_uvms": "4"}],
         "archivio": [{"uid": "B" * 20, "canale": c, "primo": "2026-10-23 09:30", "letto_il": "2026-11-10T20:30:00Z"} for c in range(3)],
         "anagrafica": [{"kit": 581, "telecamere": 3}]}
ok(pa.registratore_del_kit(581, stato["kit"])[0] == "B" * 20, "registratore: quello che ha risposto")
ok(pa.registratore_del_kit(999, stato["kit"]) == (None, None, None), "registratore: kit sconosciuto")
ok(pa.disponibile(stato["archivio"], "B" * 20, [0, 1], D(2026, 10, 21, 16, 0))["stima"] == "no", "sul registratore: no")
ok(pa.disponibile(stato["archivio"], "B" * 20, [0], D(2026, 11, 5))["stima"] == "si", "sul registratore: si")
ok(pa.disponibile([], "B" * 20, [0], D(2026, 11, 5))["stima"] == "non so", "sul registratore: non so")
r2 = [dict(r, dati=dict(r["dati"], kit="KIT581 Via", giorno="2026-11-01", nome="a mano 130000", W=2688, H=1520)) for r in righe]
e = pa.evento_da_righe([dict(r, evento="1234567890") for r in r2[:2]], stato)
ok(e["kit"] == 581 and e["ora_inizio_clip"] == "13:00:00" and e["canali"] == [0, 1, 2] and e["uid"] == "B" * 20,
   "evento: l'anagrafica dice 3 telecamere, la clip ne ha 2: si chiedono tutte e 3")
ok(e["durate_canali"] == {"0": 218.2, "2": 218.6} and e["sul_registratore"]["stima"] == "si", "evento: durate e registrazione")
lo, hi = pa.stima_mb(e)
ok(0 < lo < hi, "stima dei MB")
v = [{"evento": "7b56bc2ce8", "giorno": "2026-10-21", "sul_registratore": {"stima": "no"}},
     {"evento": "aaaaaaaaaa", "giorno": "2026-10-01", "sul_registratore": {"stima": "no"}},
     {"evento": "bbbbbbbbbb", "giorno": "2026-11-02", "sul_registratore": {"stima": "si"}},
     {"evento": "cccccccccc", "giorno": "2026-10-20", "sul_registratore": {"stima": "si"}}]
ok([x["evento"][0] for x in sorted(v, key=pa.ordine)] == ["c", "b", "7", "a"],
   "ordine: prima quelli ancora sul registratore, i piu' vecchi prima; fra i sovrascritti quelli di Dario")

# ------------------------------------------------------------------ il lavoro con la libreria finta


class Finto:
    """Registratore finto. registrato: {canale: [(da, a)]} dove c'e' registrazione; 10 fotogrammi al secondo, un
    fotogramma chiave ogni 2 s. perdite: {(canale, numero della richiesta di quel canale): (da_s, a_s)} fotogrammi persi
    nel viaggio (relativi all'inizio chiesto). blocca: nome della chiamata che non torna."""

    def __init__(self, registrato, perdite=None, blocca=None, collega_ok=True, primo=None):
        self.reg, self.perdite, self.blocca = registrato, perdite or {}, blocca
        self.collega_ok, self.primo = collega_ok, primo
        self.richieste = {}
        self.chiuso = 0

    def canali(self):
        return [(c, 100 + c, f"CH{c + 1}") for c in sorted(self.reg)]

    def intervallo(self, h):
        c = h - 100
        return (self.primo or min(a for a, _ in self.reg[c]), max(b for _, b in self.reg[c]))

    def scarica(self, canale, h, da, secondi, cartella, ffmpeg="ffmpeg"):
        if self.blocca == "scarica":
            time.sleep(3)
        n = self.richieste[canale] = self.richieste.get(canale, 0) + 1
        fine = da + sec(secondi)
        tempi = []
        for a, b in self.reg[canale]:
            x = max(a, da - sec(2))
            x = a + sec(2 * -(-int((x - a).total_seconds() * 10) // 20))   # il primo fotogramma chiave
            while x < min(b, fine):
                tempi.append(x)
                x += sec(0.1)
        p = self.perdite.get((canale, n))
        if p:
            tempi = [t for t in tempi if not (da + sec(p[0]) <= t < da + sec(p[1]))]
        if not tempi:
            return {"errore": "nessun fotogramma nel tratto chiesto", "tempi": []}
        os.makedirs(cartella, exist_ok=True)
        f = os.path.join(cartella, f"{tempi[0]:%H%M%S}{canale:02d}S.mp4")
        open(f, "w").write(str(len(tempi)))
        return {"file": f, "tempi": tempi, "mb": round(len(tempi) * 0.01, 2), "fps": 10.0, "codec": "H.264",
                "misura": "1920x1080", "primo": str(tempi[0]), "ultimo": str(tempi[-1])}

    def chiudi(self):
        self.chiuso += 1


def mezzi_finti(fin, cartella):
    def taglia(file, n, dest):
        open(dest, "w").write(f"{n} di {open(file).read()}")
        return True

    def foglio(mp4, jpg):
        open(jpg, "w").write("jpg")
        return jpg
    return {"nuovo": lambda: fin, "collega": lambda reg: (fin.collega_ok, "collegato (finto)" if fin.collega_ok else "non e' l'host"),
            "sposta": shutil.move, "taglia": taglia, "foglio": foglio, "cartella_video": os.path.join(cartella, "video"),
            "cartella_fogli": os.path.join(cartella, "uscita", "fogli"), "cimitero": []}


def tutto(c_da=S - sec(3600), c_a=S + sec(3600)):
    return {c: [(c_da, c_a)] for c in range(3)}


tmp = tempfile.mkdtemp(prefix="prova_allunga_")
scritti = []
fin = Finto(tutto())
x = al.lavora_evento(EV, {}, mezzi_finti(fin, os.path.join(tmp, "a")), lambda r: scritti.append(1))
ok(x["esito"] == "fatto" and not x["in_corso"], "evento intero: fatto")
p0 = x["canali"]["0"]["tratti"]["prima"]["pezzi"]
# lo scarico parte dal fotogramma chiave fino a 2 s prima dell'ora chiesta: l'ora vera e' quella
ok(len(p0) == 1 and p0[0]["inizio"].startswith("2026-11-01 12:58:58") and p0[0]["fine"].startswith("2026-11-01 12:59:59.9"),
   "il pezzo «prima» ha l'ora vera di inizio e di fine")
ok(os.path.exists(os.path.join(tmp, "a", "video", p0[0]["file"])) and p0[0]["file"].startswith("CH1_prima_20261101-125858"),
   "l'mp4 si chiama con l'ora vera")
ok(all(x["sincronia"][k]["esito"] == "sincroni" for k in ("prima", "dopo")), "evento intero: canali sincroni")
ok(x["conti"]["mb"] > 0 and x["conti"]["chiamate"] > 0 and x["conti"]["collegamenti"] >= 1 and scritti, "conti e scritture")
ok(fin.richieste == {0: 2, 1: 2, 2: 2}, "due richieste per canale (prima, dopo)")

# una perdita nel viaggio: il pezzo si taglia al salto, il resto da un collegamento nuovo
fin = Finto(tutto(), perdite={(1, 2): (20, 25)})
x = al.lavora_evento(EV, {}, mezzi_finti(fin, os.path.join(tmp, "b")))
d1 = x["canali"]["1"]["tratti"]["dopo"]
ok(d1["buchi_s"] == 0 and len(d1["pezzi"]) == 2 and d1["pezzi"][0]["salto_dopo_s"] > 5, "perdita nel viaggio: ripresa, niente buchi")
ok(x["esito"] == "fatto" and x["sincronia"]["dopo"]["esito"] == "sincroni", "perdita nel viaggio: alla fine sincroni")
ok(d1["pezzi"][0]["fotogrammi"] == 220 and open(os.path.join(tmp, "b", "video", d1["pezzi"][0]["file"])).read().startswith("220 di"),
   "il pezzo e' tagliato al salto (dal fotogramma chiave 2 s prima a 20 s dopo)")
ok(d1["pezzi"][1].get("sovrapposto_s") == 1.9, "il pezzo dopo il salto si sovrappone (fotogramma chiave prima), e lo dice")
ok(x["conti"]["collegamenti"] >= 2, "dopo il salto un collegamento nuovo")

# un buco vero nella registrazione del canale 2 (dalle 13:01:00 alle 13:01:10)
reg = tutto()
reg[2] = [(S - sec(3600), S + sec(60)), (S + sec(70), S + sec(3600))]
fin = Finto(reg)
x = al.lavora_evento(EV, {}, mezzi_finti(fin, os.path.join(tmp, "c")))
d2 = x["canali"]["2"]["tratti"]["dopo"]
ok(9 <= d2["buchi_s"] <= 11 and x["esito"] == "parziale", "buco vero: segnato, evento parziale")
ok(len(d2["pezzi"]) == 2 and d2["pezzi"][1]["inizio"].startswith("2026-11-01 13:01:10") and d2["richieste"] == 3,
   "buco vero: confermato da una seconda richiesta, poi si riparte dopo il buco")
ok(x["sincronia"]["dopo"]["esito"].startswith("con buchi"), "buco vero: i canali non si uniscono")

# il registratore non l'ha piu'
fin = Finto(tutto(S + sec(86400), S + sec(99999)))
x = al.lavora_evento(EV, {}, mezzi_finti(fin, os.path.join(tmp, "d")))
ok(x["esito"] == "non piu' sul registratore" and fin.richieste == {} and x["conti"]["mb"] == 0, "non piu' sul registratore: niente scarichi")

# solo in parte: il registratore comincia 20 s prima della clip
fin = Finto(tutto(S - sec(20)))
x = al.lavora_evento(EV, {}, mezzi_finti(fin, os.path.join(tmp, "e")))
ok(x["esito"] == "parziale" and "40 s" in x["canali"]["0"]["tratti"]["prima"]["nota"], "in parte sovrascritto: parziale con nota")

# collegamento che non entra; chiamata che non torna; canale che non c'e'; kit senza registratore
fin = Finto(tutto(), collega_ok=False)
x = al.lavora_evento(EV, {}, mezzi_finti(fin, os.path.join(tmp, "f")))
ok(x["esito"].startswith("registratore non raggiunto") and x["collegamenti"][0]["ok"] is False, "collegamento rifiutato")
fin = Finto(tutto(), blocca="scarica")
t0 = time.time()
x = al.lavora_evento(EV, {"tempi": {"scarica_fisso": 0.3, "scarica_per_secondo": 0.001}}, mezzi_finti(fin, os.path.join(tmp, "g")))
ok(x["esito"].startswith("bloccato") and x["bloccato"] and time.time() - t0 < 3, "chiamata che non torna: bloccato, subito")
fin = Finto({0: tutto()[0], 1: tutto()[1]})
x = al.lavora_evento(EV, {}, mezzi_finti(fin, os.path.join(tmp, "h")))
ok(x["canali"]["2"]["nota"] == "canale assente sul registratore" and x["esito"] == "fatto", "canale assente")
x = al.lavora_evento(dict(EV, uid=None), {}, mezzi_finti(Finto(tutto()), os.path.join(tmp, "i")))
ok(x["esito"].startswith("registratore sconosciuto"), "kit senza registratore")
# la telecamera corta: si scarica anche il buco
fin = Finto(tutto())
x = al.lavora_evento(dict(EV, durate_canali={"0": 30, "1": 30, "2": 4}), {}, mezzi_finti(fin, os.path.join(tmp, "j")))
ok(x["canali"]["2"]["tratti"]["buco"]["coperti_s"] >= 25 and "buco" not in x["canali"]["0"]["tratti"], "il buco della telecamera corta")

# ------------------------------------------------------------------ il giro di tutti gli eventi (il ponte)
chiamati = []


def lancia(ev, secondi_max):
    chiamati.append(ev["evento"])
    r = {"evento": ev["evento"], "kit": ev["kit"], "esito": "fatto", "in_corso": False, "conti": {"mb": 10.0, "chiamate": 5, "collegamenti": 1},
         "canali": {"0": {"tratti": {"prima": {"coperti_s": 60, "buchi_s": 0}}}}}
    if ev["evento"] == "e2" and chiamati.count("e2") == 1:
        return al.MEMORIA, dict(r, in_corso=True, esito=None, conti={"mb": 3.0, "chiamate": 2, "collegamenti": 1})
    if ev["evento"] == "e3":
        return "fermato dopo 25 minuti", None
    return 0, r


uscite = []
cfg = {"eventi": [dict(EV, evento="e1"), dict(EV, evento="e2", kit=324), dict(EV, evento="e3"), dict(EV, evento="e4", uid=None)]}
out = al.lavoro(cfg, lancia, lambda o: uscite.append(json.dumps(o, default=str)))
es = {x["evento"]: x for x in out["eventi"]}
ok(chiamati == ["e1", "e2", "e3", "e2"], "l'evento morto di memoria si rifa' una volta, in fondo")
ok(es["e2"]["esito"] == "fatto" and "memoria" in es["e2"]["tentativo_prima"]["esito"], "il secondo tentativo tiene traccia del primo")
ok(es["e3"]["esito"] == "fermato dopo 25 minuti" and es["e4"]["esito"].startswith("registratore sconosciuto"), "tempo scaduto e kit sconosciuto")
ok(out["conti"]["in_tutto"]["mb"] == 20.0 and out["conti"]["per_kit"]["581"]["mb"] == 10.0 and out["conti"]["per_kit"]["324"]["mb"] == 10.0,
   "MB in tutto e per kit")
ok(len(out["eventi"]) == 4 and len(uscite) >= 5, "un json per evento, scritto man mano")
out = al.lavoro(dict(cfg, limiti={"ore_in_tutto": 0}), lancia, lambda o: None, adesso=iter([0, 1, 1, 1]).__next__)
ok(out.get("fermato", "").startswith("passate 0") and not out["eventi"], "tempo totale finito: i casi dopo non si fanno")

# ------------------------------------------------------------------ un evento in un processo a parte, come sul PC
FINTO_NVR = r'''
"""focus_nvr finto per prova_allunga.py: un registratore che fa mp4 veri con ffmpeg; FINTO_CADE=1 fa un errore di memoria."""
import ctypes, datetime, os, subprocess


def fps_da_tempi(tempi):
    return 10.0


def nome_per_kit_rifiuti(inizio, canale):
    return f"{inizio:%H%M%S}{canale:02d}S"


class Registratore:
    def __init__(self, cartella=None, log=print):
        self.cartella = cartella

    def collega(self, uid, utente, password, porta=9010, p2p=False, attesa=25):
        return (password == "finta"), "collegato (finto)" if password == "finta" else "password sbagliata"

    def canali(self):
        return [(0, 100, "CH1"), (1, 101, "CH2")]

    def intervallo(self, h):
        return datetime.datetime(2026, 10, 1), datetime.datetime(2026, 11, 11)

    def scarica(self, canale_num, canale_h, inizio, secondi, cartella, attesa_vuoto=30, ffmpeg="ffmpeg"):
        if os.environ.get("FINTO_CADE"):
            ctypes.string_at(0)
        os.makedirs(cartella, exist_ok=True)
        n = int(secondi * 10)
        tempi = [inizio + datetime.timedelta(seconds=i / 10) for i in range(n)]
        if canale_num == 1 and secondi > 100:   # un salto nel viaggio al secondo 30, solo la prima volta
            tempi = [t for t in tempi if not (30 <= (t - inizio).total_seconds() < 33)]
        fps = fps_da_tempi(tempi)
        f = os.path.join(cartella, nome_per_kit_rifiuti(inizio, canale_num) + ".mp4")
        subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=160x90:rate=10", "-frames:v", str(len(tempi)),
                        "-c:v", "libx264", "-g", "20", f], check=True)
        return {"file": f, "mb": round(os.path.getsize(f) / 1e6, 3), "fps": fps, "primo": str(tempi[0]), "ultimo": str(tempi[-1])}

    def chiudi(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.chiudi()
'''


def processo_a_parte(cade=False):
    base = tempfile.mkdtemp(prefix="prova_allunga_processo_")
    comp = os.path.join(base, "p2p_ponte30")
    os.makedirs(os.path.join(comp, "FocusNetSDK"))
    for f in ("compito.py", "allunga.py", "allunga_lavoro.py", "movimento.py"):
        shutil.copy2(os.path.join(QUI, f), comp)
    open(os.path.join(comp, "focus_nvr.py"), "w").write(FINTO_NVR)
    open(os.path.join(comp, "focus_accesso.txt"), "w").write("*;utente;finta\n")   # password finta della prova
    d = os.path.join(base, "evento")
    os.makedirs(d)
    shutil.copy2(os.path.join(comp, "compito.py"), os.path.join(d, "ponte.py"))
    shutil.copy2(os.path.join(comp, "allunga_lavoro.py"), os.path.join(d, "compito.py"))
    ev = dict(EV, canali=[0, 1], durate_canali={"0": 30, "1": 30}, dopo_s=120)
    json.dump({"evento": ev, "cfg": {}, "compito": comp}, open(os.path.join(d, "evento.json"), "w"))
    env = dict(os.environ, FINTO_CADE="1" if cade else "")
    r = subprocess.run([sys.executable, os.path.join(d, "compito.py"), d], cwd=d, env=env, capture_output=True, text=True,
                       timeout=300)
    return r, d, base


if shutil.which("ffmpeg"):
    r, d, base = processo_a_parte()
    ok(r.returncode == 0, f"processo a parte: finito con 0 ({r.returncode} {r.stderr[-300:]})")
    try:
        x = json.load(open(os.path.join(d, "uscita", "allunga_evento.json")))
    except (OSError, ValueError):
        x = {}
    ok(x.get("esito") == "fatto", f"processo a parte: evento fatto ({x.get('esito')})")
    d1 = ((x.get("canali") or {}).get("1") or {}).get("tratti", {}).get("dopo", {})
    ok(len(d1.get("pezzi") or []) == 2 and d1.get("buchi_s") == 0, "processo a parte: il salto nel viaggio ripreso (ora vera dalla spia)")
    video = os.listdir(os.path.join(d, "video"))
    ok(len([v for v in video if v.endswith(".mp4")]) == 5, f"processo a parte: 5 mp4 continui ({len(video)})")
    tagliato = os.path.join(d, "video", d1["pezzi"][0]["file"]) if d1.get("pezzi") else ""
    if tagliato and shutil.which("ffprobe"):
        q = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", tagliato], capture_output=True, text=True)
        ok(q.stdout.strip() == "300", f"processo a parte: l'mp4 tagliato al salto ha 300 fotogrammi ({q.stdout.strip()})")
    ok(len(os.listdir(os.path.join(d, "uscita", "fogli"))) == 5, "processo a parte: un foglio di fotogrammi per mp4")
    shutil.rmtree(base, ignore_errors=True)
    r, d, base = processo_a_parte(cade=True)
    ok(r.returncode not in (0, 1, 3), f"processo che cade: muore lui ({r.returncode})")
    g = open(os.path.join(d, "uscita", "guasto_memoria.txt")).read()
    ok("Fatal Python error" in g and "scarica" in g, "processo che cade: le pile di Python in guasto_memoria.txt")
    shutil.rmtree(base, ignore_errors=True)
else:
    print("--   ffmpeg non c'e': salto le prove col processo a parte")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{'TUTTE VERDI' if not fallite else str(len(fallite)) + ' ROSSE: ' + ', '.join(fallite)}")
sys.exit(1 if fallite else 0)
