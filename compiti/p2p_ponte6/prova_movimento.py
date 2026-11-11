"""Prove a tavolino di movimento.py: libreria finta (registratore che risponde da tabelle, miniature finte in grigi),
niente rete, niente DLL. Uso: python3 prova_movimento.py
version: 0.1.0 (11/11/2026)
"""
import datetime
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import movimento as mv   # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


W, H = mv.LATO_GRIGIO
ATTESO = datetime.datetime(2026, 11, 1, 13, 0, 36)


def giorno_tipi(movimento=(), continua=True):
    t = [1 if continua else 0] * 1440
    for a, b in movimento:
        for i in range(a, b):
            t[i] = 2
    return t


def immagine(t):
    """Una scena in grigi: fondo a 100, un «sacco» scuro nella zona dalle 13:00:36, un'«auto» chiara fuori zona alle 12:50."""
    px = bytearray([100] * (W * H))
    if t >= ATTESO:
        for r in range(20, 30):
            for c in range(75, 85):
                px[r * W + c] = 20
    if datetime.datetime(2026, 11, 1, 12, 50) <= t < datetime.datetime(2026, 11, 1, 12, 52):
        for r in range(40, 54):
            for c in range(0, 30):
                px[r * W + c] = 230
    return bytes(px)


class Finto:
    """Il registratore finto: canali 0, 1, 2; tipi del giorno per canale; miniature che portano l'ora nei «dati»."""

    def __init__(self, tipi, blocca=(), no_miniature=False, byte=40000):
        self.tipi, self.blocca, self.no_mini, self.byte = tipi, set(blocca), no_miniature, byte
        self.modi = {101: {"modo": "continua + movimento", "eventi_accesi": True}}
        self.eventi = []
        self.chiuso = False

    def _forse_blocca(self, nome):
        if nome in self.blocca:
            time.sleep(5)

    def canali(self):
        self._forse_blocca("canali")
        return [(n, 100 + n, f"CH{n + 1}") for n in self.tipi]

    def tipi_del_giorno(self, h, giorno):
        self._forse_blocca("giorno")
        return self.tipi.get(h - 100)

    def intervallo(self, h):
        return (datetime.datetime(2026, 10, 1), datetime.datetime(2026, 11, 11))

    def miniatura(self, h, quando, attesa):
        self._forse_blocca("miniatura")
        if self.no_mini:
            return {"errore": "nessuna miniatura in 12 s"}
        return {"dati": quando.isoformat().encode().ljust(self.byte, b"\0"), "formato": "H.264", "misura": "1920x1080",
                "tipo": 1, "ora_video": quando.isoformat(sep=" ")}

    def chiudi(self):
        self.chiuso = True


def decodifica(dati, formato, nome):
    t = datetime.datetime.fromisoformat(dati.rstrip(b"\0").decode())
    return immagine(t)


def mezzi(finto, collega_ok=True, tempi=None):
    return {"nuovo": lambda: finto, "collega": lambda reg, uid, kit: (collega_ok, "collegato (P2P diretto)" if collega_ok else "password sbagliata"),
            "lucchetto": threading.Lock(), "decodifica": decodifica,
            "tempi": dict(mv.TEMPI, **(tempi or {}))}


CASO = {"nome": "kit581", "uid": "X", "kit": 581, "canale": 0, "atteso": "2026-11-01 13:00:36",
        "zona": {"riquadri": [[0.7, 0.3, 0.25, 0.3]]}}
CFG = {"casi": [CASO], "miniature": {"minuti_prima": 15, "minuti_dopo": 10, "passo_s": 60}}

# --- funzioni pure
t = giorno_tipi([(779, 782), (900, 905)])
tr = mv.tratti_di(t)
ok(tr == [(779, 782), (900, 905)], "tratti di movimento")
ok(mv.minuti_per_ora(t)[12] == 1 and mv.minuti_per_ora(t)[13] == 2 and mv.minuti_per_ora(t)[15] == 5, "minuti per ora")
r = mv.rispetto_atteso(tr, 780)
ok(r["dentro"] and r["tratto"] == "12:59-13:02", "abbandono dentro un tratto")
r = mv.rispetto_atteso(tr, 790)
ok(not r["dentro"] and r["prima_min"] == 9 and r["dopo_min"] == 110, "distanze prima e dopo")
ok(mv.entro_margine(mv.rispetto_atteso(tr, 783)) and not mv.entro_margine(mv.rispetto_atteso(tr, 790)), "margine di 2 minuti")
rc = mv.riassunto_canale(t, ATTESO)
ok(rc["ore_con_movimento"] == 3 and rc["minuti_movimento"] == 8 and rc["abbandono"]["dentro"], "riassunto del canale")
ok(rc["ore"][12] != "0" and rc["ore"][14] == "0" and len(rc["ore"]) == 24, "le 24 lettere")
ok(mv.verdetto({0: mv.riassunto_canale(giorno_tipi(), ATTESO)}, 0).startswith("solo «continua»"), "verdetto: solo continua")
ok(mv.verdetto({0: rc}, 0).startswith("il movimento segnato copre"), "verdetto: copre")
ok("NON copre" in mv.verdetto({0: mv.riassunto_canale(giorno_tipi([(600, 610)]), ATTESO)}, 0), "verdetto: non copre")
ok(mv.verdetto({0: {"errore": "x"}}, 0).startswith("non letto"), "verdetto: non letto")
ok(mv.verdetto({0: mv.riassunto_canale([0] * 1440, ATTESO)}, 0) == "niente registrato quel giorno", "verdetto: niente")
ok(mv.pulisci_tipi([1, 2]) [:3] == [1, 2, 0] and len(mv.pulisci_tipi([1] * 2000)) == 1440, "pulisci tipi")
ok(len(mv.tempi_miniature(ATTESO, 30, 30, 60)) == 61, "61 miniature in un'ora a 60 s")
ok(mv.tempi_miniature(datetime.datetime(2026, 11, 1, 0, 5), 30, 0, 60)[0] == datetime.datetime(2026, 11, 1), "miniature nel giorno")
a, b = immagine(ATTESO - datetime.timedelta(minutes=1)), immagine(ATTESO)
zona = mv.maschera(W, H, [[0.7, 0.3, 0.25, 0.3]])
ok(mv.differenza(a, b, zona) > 10 and mv.differenza(a, a, zona) == 0, "differenza nella zona")
luce = bytes(min(255, x + 40) for x in a)
ok(mv.differenza(a, luce, zona) == 0, "la luce che cambia tutta insieme non conta")
ok(mv.differenza(a, None, zona) is None, "differenza senza immagine")
lim, tempi = mv.limiti_da({"limiti": {"mb_totali": 10, "chiamate_totali": 10 ** 6}, "tempi": {"miniatura": 5, "giorno": 999}})
ok(lim["mb_totali"] == 10 and lim["chiamate_totali"] == mv.LIMITI["chiamate_totali"], "i limiti si abbassano, non si alzano")
ok(tempi["miniatura"] == 5 and tempi["giorno"] == mv.TEMPI["giorno"], "i tempi per chiamata si abbassano, non si alzano")

# --- il lavoro con la libreria finta
scritti = []
fin = Finto({0: giorno_tipi([(779, 782)]), 1: giorno_tipi(), 2: giorno_tipi([(300, 301)])})
out = mv.lavoro(CFG, mezzi(fin), lambda o: scritti.append(1))
x = out["casi"][0]
ok(x["verdetto"].startswith("il movimento segnato copre"), "lavoro: verdetto")
ok(x["quante_ore_unione"] == 3 and x["ore_con_movimento_unione"][5] == "1", "lavoro: ore con movimento su tutti i canali")
ok(x["modi"] == {"101": {"modo": "continua + movimento", "eventi_accesi": True}}, "lavoro: modo di registrazione")
ok(x["miniature"]["chieste"] == 26 and x["miniature"]["arrivate"] == 26 and x["miniature"]["decodificate"] == 26,
   "lavoro: 26 miniature")
ok(x["miniature"]["cambio"]["posto"] == 1, "lavoro: il cambio piu' grande nella zona e' all'ora attesa")
ok(x["miniature"]["resta"]["posto"] is not None and x["miniature"]["resta"]["posto"] <= 5, "lavoro: il cambio che resta e' fra i primi")
ok(fin.chiuso and scritti and out["conti"]["chiamate"] > 0, "lavoro: chiuso, scritto, contato")
ok(not mezzi(fin)["lucchetto"].locked(), "lavoro: lucchetto libero")
ok("dati" not in str(x["miniature"]["elenco"][0].keys()), "lavoro: i dati delle miniature non vanno nel json")

# l'auto fuori zona non vince: il cambio di tutta l'immagine alle 12:50 c'e', nella zona no
serie = {s["da"]: s for s in x["miniature"]["serie"]}
ok(serie["12:49:36"]["tutto"] > serie["12:49:36"]["cambio"], "lavoro: l'auto fuori zona cambia l'immagine, non la zona")

# registratore che non risponde
out = mv.lavoro(CFG, mezzi(Finto({0: giorno_tipi()}), collega_ok=False), lambda o: None)
ok(out["casi"][0]["esito"].startswith("registratore non raggiunto"), "collegamento rifiutato")

# una chiamata che si blocca: il caso si ferma, il lucchetto si libera, dopo due blocchi i casi dopo non si fanno
m = mezzi(Finto({0: giorno_tipi()}, blocca={"giorno"}), tempi={"giorno": 0.3})
t0 = time.time()
out = mv.lavoro({"casi": [CASO, dict(CASO, nome="b"), dict(CASO, nome="c")], "miniature": CFG["miniature"]}, m, lambda o: None)
ok(time.time() - t0 < 4, "bloccata: non si aspetta la libreria")
ok(len(out["blocchi"]) == 2 and "fermato" in out and len(out["casi"]) == 2, "bloccata: due blocchi e ci si ferma")
ok(not m["lucchetto"].locked(), "bloccata: lucchetto libero")

# miniature che non arrivano
out = mv.lavoro(CFG, mezzi(Finto({0: giorno_tipi()}, no_miniature=True)), lambda o: None)
x = out["casi"][0]
ok(x["miniature"]["arrivate"] == 0 and x["miniature"]["cambio"]["posto"] is None, "miniature assenti")
ok(x["verdetto"].startswith("solo «continua»"), "miniature assenti: verdetto dai tipi")

# limite dei MB: miniature da 1 MB, limite 5 MB per caso -> il caso si ferma e il secondo non parte
cfg = dict(CFG, casi=[CASO, dict(CASO, nome="b")], limiti={"mb_per_caso": 5, "mb_totali": 5})
out = mv.lavoro(cfg, mezzi(Finto({0: giorno_tipi()}, byte=1_000_000)), lambda o: None)
x = out["casi"][0]
ok(x.get("limite", "").startswith("limite scattato: mb_"), "limite MB: il caso si ferma")
ok(x["miniature"]["arrivate"] == 5 and out["conti"]["mb"] == 5.0, "limite MB: 5 miniature da 1 MB")
ok(len(out["casi"]) == 1 and out["fermato"].startswith("limite scattato"), "limite MB: il caso dopo non parte")

# limite delle chiamate per caso
cfg = dict(CFG, limiti={"chiamate_per_caso": 10})
out = mv.lavoro(cfg, mezzi(Finto({0: giorno_tipi(), 1: giorno_tipi()})), lambda o: None)
ok(out["casi"][0].get("limite", "").startswith("limite scattato: chiamate_per_caso"), "limite chiamate")
ok(out["conti"]["chiamate"] <= 11, "limite chiamate: al massimo una in piu' (il chiudi)")

# limite dei collegamenti
cfg = dict(CFG, limiti={"collegamenti_totali": 1})
out = mv.lavoro(cfg, mezzi(Finto({0: giorno_tipi()})), lambda o: None)
ok("collegamenti_totali" in out["casi"][0].get("limite", ""), "limite collegamenti: le miniature non partono")

print(f"\n{'TUTTE PASSATE' if not fallite else str(len(fallite)) + ' FALLITE: ' + ', '.join(fallite)}")
if __name__ == "__main__":
    sys.exit(1 if fallite else 0)
