"""prova_ripristino.py 0.5.0 (16/11/2026): le prove a tavolino del compito fuoco5 (ripristino del fuoco di KIT249 cam 3),
senza registratore.
- un'ottica finta fatta come quella vista in fuoco4: impulsi «vicino» molto piu' lunghi di quelli «lontano», gioco
  degli ingranaggi, fine corsa, impulsi che variano, la lente che «respira» (ingrandisce un poco quando e' sfocata);
  le foto sono la partenza vera (riferimento/partenza.jpg, se c'e') o una scena sintetica, sfocate e ingrandite;
- un registratore finto al livello di PTZControl: solo i comandi 10 e 11, ogni «premi» seguito dal «lascia»;
- le foto vere di fuoco4 (cartella data con FOTO_FUOCO4=..., se c'e'): le misure dicono «stessa scena», «a fuoco e
  combacia» e «un altro canale» dove devono.
Uso: python prova_ripristino.py [cartella del compito con riferimento/]"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compito as c   # noqa: E402
import cv2   # noqa: E402
import numpy as np   # noqa: E402

VERSION = "0.5.0"
ZITTO = lambda *_: None   # noqa: E731
CFG = dict(c.DIFETTI)
ERRORI = []


def ok(cond, cosa):
    print(("ok   " if cond else "NO   ") + cosa)
    if not cond:
        ERRORI.append(cosa)


def scena():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    f = os.path.join(d, "riferimento", "partenza.jpg")
    if os.path.exists(f):
        return c.piccola(cv2.imread(f)), "partenza vera di fuoco4"
    rnd = np.random.default_rng(3)
    g = cv2.resize(rnd.normal(128, 50, (90, 160)).astype(np.float32), (640, 360), interpolation=cv2.INTER_CUBIC)
    g += cv2.resize(rnd.normal(0, 25, (360, 640)).astype(np.float32), (640, 360))
    for _ in range(40):
        x, y = int(rnd.integers(0, 600)), int(rnd.integers(30, 300))
        cv2.rectangle(g, (x, y), (x + int(rnd.integers(10, 80)), y + int(rnd.integers(10, 60))),
                      float(rnd.integers(0, 255)), -1)
    return np.clip(g, 0, 255).astype(np.float32), "scena sintetica"


NITIDA, ORIGINE = scena()


class Ottica:
    """La telecamera finta per ripristina(): posizione p del fuoco (0 = la partenza), sfocatura sigma = |p| * sfoca,
    scala 1 + respiro * p. Un impulso sposta il motore di (passo_vicino o passo_lontano) * ms / 75, con jitter; la lente
    segue col gioco; fine corsa a +-corsa. luce scala il contrasto (una mattina piu' grigia)."""

    def __init__(self, p0=12.0, passo_vicino=6.0, passo_lontano=1.0, gioco=0.4, jitter=0.15, sfoca=0.9,
                 respiro=0.002, corsa=14.0, luce=1.0, scena=None, seed=1, lascia_rotto_da=None, picco=0.0,
                 auto=None):
        self.L = self.m = p0
        self.pv, self.pl, self.gioco, self.jitter, self.sfoca = passo_vicino, passo_lontano, gioco, jitter, sfoca
        self.respiro, self.corsa, self.luce, self.picco = respiro, corsa, luce, picco
        self.scena = NITIDA if scena is None else scena
        self.rnd = random.Random(seed)
        self.impulsi, self.scatti, self.versi, self.foto_fra = 0, 0, [], []
        self.ultimo_scatto_dopo = True
        self.lascia_rotto_da = lascia_rotto_da
        self.auto = auto                                 # (prima foto, ultima foto): un'auto parcheggiata davanti

    def scatta(self, nome):
        self.scatti += 1
        self.ultimo_scatto_dopo = True
        e = self.L - self.picco
        g = self.scena
        s = 1 + self.respiro * e
        if abs(s - 1) > 1e-4:
            g = c.riscala(g, s)
        sig = abs(e) * self.sfoca
        if sig > 0.05:
            g = cv2.GaussianBlur(g, (0, 0), sig)
        if self.auto and self.auto[0] <= self.scatti <= self.auto[1]:
            g = g.copy()
            cv2.rectangle(g, (300, 120), (460, 260), 235.0, -1)
            cv2.rectangle(g, (320, 140), (440, 190), 60.0, -1)
        g = (g - 128) * self.luce + 128
        g = g + np.random.default_rng(self.scatti).normal(0, 1.0, g.shape).astype(np.float32)
        return {"g": np.clip(g, 0, 255).astype(np.float32), "file": f"{self.scatti:03d}_{nome}.jpg"}

    def muovi(self, verso, ms):
        if self.impulsi >= CFG["impulsi_max"]:
            raise c.Fermo("tetto")
        self.foto_fra.append(self.ultimo_scatto_dopo)
        self.ultimo_scatto_dopo = False
        self.impulsi += 1
        self.versi.append((verso, ms))
        if self.lascia_rotto_da is not None and self.impulsi >= self.lascia_rotto_da:
            raise c.Fermo("il «lascia» non e' stato confermato dal registratore: niente altri impulsi")
        amp = (self.pv if verso > 0 else self.pl) * ms / 75 * (1 + self.jitter * (2 * self.rnd.random() - 1))
        self.m = max(-self.corsa, min(self.corsa, self.m + verso * amp))
        meta = self.gioco / 2
        if self.m - self.L > meta:
            self.L = self.m - meta
        elif self.L - self.m > meta:
            self.L = self.m + meta


class Orologio:
    """Il tempo finto: ogni foto ~9 s (impulso, assestamento, istantanea)."""

    def __init__(self, o):
        self.o = o

    def __call__(self):
        return self.o.scatti * 9.0


def gira(o, **cfg):
    cc = dict(CFG, **cfg)
    return c.ripristina(o, NITIDA, cc, ZITTO, ora=Orologio(o))


def invarianti(o, es, cosa):
    ok(all(o.foto_fra), f"{cosa}: mai due impulsi senza una foto in mezzo")
    ok(o.impulsi <= CFG["impulsi_max"], f"{cosa}: dentro il tetto di impulsi ({o.impulsi})")
    ok(all(p["foto_prima"] and p["foto_dopo"] for p in es["passi"]), f"{cosa}: ogni passo ha la foto prima e dopo")
    ok(len(es["passi"]) == o.impulsi, f"{cosa}: un passo registrato per ogni impulso")


def prova_ripristino():
    print(f"-- ripristino sull'ottica finta ({ORIGINE})")
    nit_ref = c.nitidezza(NITIDA)
    # 1. come la fine di fuoco4: sfocata dalla parte «vicino», fine corsa vicino
    o = Ottica(p0=12.0)
    es = gira(o)
    r = c.nitidezza(o.scatta("controllo")["g"]) / nit_ref
    ok(es.get("tornata") is True, f"dalla fine di fuoco4 torna ({es.get('esito')}, {o.impulsi} impulsi)")
    ok(r >= 0.7, f"nitidezza finale vera {r:.0%} >= 70%")
    ok(o.versi[0][0] == -1, "il primo impulso e' «lontano»")
    invarianti(o, es, "fine di fuoco4")
    # 2. molti semi e jitter: torna sempre, e mai oltre 45 minuti
    tornate, tempi = 0, []
    for seed in range(12):
        o = Ottica(p0=8 + seed % 6, seed=seed, jitter=0.3)
        es = gira(o)
        tornate += bool(es.get("tornata"))
        tempi.append(Orologio(o)())
        invarianti(o, es, f"seme {seed}")
    ok(tornate == 12, f"12 partenze diverse con jitter 30%: tornate {tornate}")
    ok(max(tempi) <= 45 * 60 + 60, f"tempo massimo {max(tempi) / 60:.1f} minuti")
    # 3. passi lontani grandi: passa il picco, inverte e torna
    o = Ottica(p0=10.0, passo_lontano=3.0, passo_vicino=3.0, gioco=0.2, seed=5)
    es = gira(o)
    ok(es.get("tornata") is True, f"passi grandi: torna ({es.get('esito')}, inversioni {len(es['inversioni'])})")
    invarianti(o, es, "passi grandi")
    # 4. sfocata dall'altra parte: il verso iniziale e' sbagliato, inverte e torna
    o = Ottica(p0=-6.0, passo_vicino=1.0, passo_lontano=1.0, seed=7)
    es = gira(o)
    ok(es.get("tornata") is True and es["inversioni"],
       f"verso sbagliato: inverte e torna ({es.get('esito')}, {o.impulsi} impulsi)")
    invarianti(o, es, "verso sbagliato")
    # 5. gia' a fuoco: nessun comando
    o = Ottica(p0=0.0)
    es = gira(o)
    ok(o.impulsi == 0 and es.get("tornata"), f"gia' a fuoco: nessun impulso ({es.get('esito')})")
    # 6. un altro canale (un'altra scena): nessun comando
    altra = np.ascontiguousarray(np.flipud(np.fliplr(NITIDA)))
    o = Ottica(p0=5.0, scena=cv2.GaussianBlur(altra, (0, 0), 3))
    es = gira(o)
    ok(o.impulsi == 0 and "senza comandi" in es.get("esito", ""), f"altra scena: nessun impulso ({es.get('esito')})")
    # 7. luce diversa: il massimo raggiungibile e' sotto il 70%, si ferma sul picco
    o = Ottica(p0=8.0, luce=0.75, seed=3)
    es = gira(o)
    e = abs(o.L)
    ok(es.get("tornata") is True and e < 1.5, f"luce piu' grigia: si ferma sul picco (|p| {e:.2f}, {es.get('esito')})")
    invarianti(o, es, "luce diversa")
    # 8. il «lascia» non confermato: si ferma subito
    o = Ottica(p0=8.0, lascia_rotto_da=3)
    es = gira(o)
    ok(o.impulsi == 3 and "lascia" in es.get("fermo", ""), f"lascia non confermato: fermo al 3o impulso")
    # 9. tetto di impulsi e di tempo
    o = Ottica(p0=14.0, passo_lontano=0.0, passo_vicino=0.0)
    es = gira(o, impulsi_max=30)
    ok(es.get("fermo") and o.impulsi <= 30 + 0, f"ottica ferma: si ferma ({es.get('fermo')}, {o.impulsi} impulsi)")
    o = Ottica(p0=14.0, passo_lontano=0.0, passo_vicino=0.0)
    es = gira(o, minuti_max=2)
    ok("minuti" in es.get("fermo", ""), f"tetto di tempo: {es.get('fermo')}")
    # 11. in fondo alla corsa, come la fine di fuoco4, e un'auto che si ferma davanti per 6 foto a meta' strada
    o = Ottica(p0=14.0, auto=(5, 10), seed=4)
    es = gira(o)
    ok(es.get("tornata") is True and any(p.get("scena_cambiata") for p in es["passi"]),
       f"fine corsa e auto davanti: se ne accorge e torna ({es.get('esito')}, {o.impulsi} impulsi)")
    invarianti(o, es, "fine corsa e auto")
    # 10. a fuoco ma spostata (inquadratura diversa): si ferma e lo dice
    sp = cv2.warpAffine(NITIDA, np.float32([[1, 0, 12], [0, 1, 0]]), (640, 360), borderMode=cv2.BORDER_REFLECT)
    o = Ottica(p0=6.0, scena=sp, seed=2)
    es = gira(o)
    ok(not es.get("tornata") and "non combacia" in es.get("esito", ""),
       f"a fuoco ma spostata: non dice tornata ({es.get('esito')})")


class Ptz:
    """Il registratore finto al livello di PTZControl."""

    def __init__(self, rifiuta_lascia=0):
        self.chiamate, self.rifiuta_lascia = [], rifiuta_lascia

    def __call__(self, h, comando, inizio, velocita):
        self.chiamate.append((comando, inizio))
        if not inizio and self.rifiuta_lascia > 0:
            self.rifiuta_lascia -= 1
            return False
        return True


def prova_guida():
    print("-- guida e giudizio (pure)")
    g = lambda r, f: c.guida({"rapporto": r, "forma": f}, CFG)   # noqa: E731
    ok(g(0.5, 0.99)[0] == "nit" and g(0.1, 0.95)[0] == "forma", "vicino al picco la nitidezza, lontano la forma")
    ok(c.giudica(g(0.1, 0.95), g(0.05, 0.93), CFG) == "meglio", "lontano: forma piu' vicina alla partenza = meglio")
    ok(c.giudica(g(0.05, 0.92), g(0.1, 0.95), CFG) == "peggio", "lontano: forma piu' lontana = peggio")
    ok(c.giudica(g(0.1, 0.951), g(0.1, 0.95), CFG) == "uguale", "lontano: differenza nel rumore = uguale")
    ok(c.giudica(g(0.35, 0.98), g(0.2, 0.97), CFG) == "meglio", "dalla forma alla nitidezza = meglio")
    ok(c.giudica(g(0.2, 0.97), g(0.6, 0.99), CFG) == "peggio", "dalla nitidezza alla forma = peggio")
    ok(c.giudica(g(0.8, 0.99), g(1.0, 0.99), CFG) == "peggio", "vicino: nitidezza giu' del 20% = peggio")


def prova_comandi():
    print("-- comandi al registratore finto")
    p = Ptz()
    k = c.Comandi(p, dormi=lambda _: None)
    k.impulso(1, -1, 75)
    k.impulso(1, +1, 37)
    ok(p.chiamate == [(11, True), (11, False), (10, True), (10, False)], "lontano = 11, vicino = 10, premi e lascia")
    p = Ptz(rifiuta_lascia=1)
    k = c.Comandi(p, dormi=lambda _: None)
    _, fermo = k.impulso(1, -1, 75)
    ok(fermo and p.chiamate[-1] == (11, False) and len(p.chiamate) == 3, "il lascia si ripete una volta")
    p = Ptz(rifiuta_lascia=5)
    k = c.Comandi(p, dormi=lambda _: None)
    _, fermo = k.impulso(1, -1, 75)
    ok(not fermo, "lascia mai confermato: lo dice")

    def rotto(*_):
        raise RuntimeError("rotto")
    p = Ptz()
    k = c.Comandi(p, dormi=rotto)
    try:
        k.impulso(1, +1, 75)
    except RuntimeError:
        pass
    ok(p.chiamate[-1] == (10, False), "il lascia parte anche se l'attesa si rompe")
    p = Ptz()
    c.Comandi(p).ferma_tutto(1)
    ok({x for x, _ in p.chiamate} == {10, 11} and all(not i for _, i in p.chiamate), "ferma_tutto: solo lascia del fuoco")
    f = object.__new__(c.Fuoco)
    f.reg = type("R", (), {"this": None, "server": 0})()
    f.ptz = lambda *a: True
    for z in (8, 9):
        try:
            f._ptz(1, z, True, 1)
            ok(False, f"lo zoom ({z}) e' rifiutato")
        except c.Fermo:
            ok(True, f"lo zoom ({z}) e' rifiutato")


def prova_foto_vere():
    d = os.environ.get("FOTO_FUOCO4")
    if not d or not os.path.isdir(d):
        print("-- foto vere di fuoco4: non date (FOTO_FUOCO4), salto")
        return
    print("-- foto vere di fuoco4")
    ref = np.load(os.path.join(d, "partenza.npy")).astype(np.float32)
    nr = c.nitidezza(ref)

    def m(f, scala=True):
        return c.misura(ref, c.piccola(cv2.imread(os.path.join(d, f))), nr, con_scala=scala)
    fine = m("foto/056_riporta.jpg")
    ok(fine["somiglianza"] >= CFG["stessa_scena"] and fine["rapporto"] < 0.05,
       f"la fine di fuoco4: stessa scena, molto sfocata ({fine})")
    picco = m("foto/021_riporta.jpg")
    ok(picco["rapporto"] >= 0.7 and c.combacia(picco, CFG), f"il picco ritrovato a meta' prova: tornata ({picco})")
    for f in ("canali/inizio_ch1.jpg", "canali/inizio_ch2.jpg"):
        x = m(f, scala=False)
        ok(x["somiglianza"] < CFG["stessa_scena"], f"{f}: un'altra telecamera ({x['somiglianza']})")
    seq = [m(f"foto/{n:03d}_riporta.jpg", scala=False)["rapporto"] for n in range(16, 22)]
    ok(all(b > a for a, b in zip(seq, seq[1:])), f"i passi «lontano» 016-021 di fuoco4 migliorano sempre: {seq}")


def prova_main():
    """main() con un registratore finto (la telecamera di prova al posto di quella vera): niente nomi rotti, la luce
    controllata prima dei comandi, il «lascia» finale, ripristino.json e stato.json scritti."""
    import json
    import shutil
    import tempfile
    import types
    print("-- main con un registratore finto")
    d = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(d, "riferimento"))
        np.save(os.path.join(d, "riferimento", "partenza.npy"), NITIDA)
        cv2.imwrite(os.path.join(d, "riferimento", "partenza.jpg"), cv2.cvtColor(NITIDA.astype(np.uint8),
                                                                                   cv2.COLOR_GRAY2BGR))
        json.dump({"uid": "FINTO", "kit_numero": 249, "kit": "prova", "aspetta_giorno": False, "assestamento": 0},
                  open(os.path.join(d, "fuoco.json"), "w"))
        o = Ottica(p0=10.0, seed=9)
        fermate, vera = [], c.Telecamera

        class Finta:
            def __init__(self, fn, cfg, uid, kit_n, log=None):
                self.impulsi, self.comandi, self.collegamenti, self.h, self.per = 0, [], [], None, {2: (7, "CH3")}
                self.reg = types.SimpleNamespace(info=lambda: {"modello": "finto"})
                colore = cv2.cvtColor(NITIDA.astype(np.uint8), cv2.COLOR_GRAY2BGR)
                colore[..., 2] = np.clip(colore[..., 2].astype(int) + 60, 0, 255)   # a colori: e' giorno
                self.F = types.SimpleNamespace(comandabile=lambda h: True, istantanea=lambda: [colore])

            def collega(self):
                return "collegato (finto)"

            def scegli(self, canale):
                self.h = self.per[canale][0]

            def scheda_luce(self, n, bgr):
                return vera.scheda_luce(self, n, bgr)

            def scatta(self, nome):
                return o.scatta(nome)

            def muovi(self, verso, ms):
                o.muovi(verso, ms)
                self.impulsi = o.impulsi

            def ferma(self):
                fermate.append(True)
                return [True] * 4

            def chiudi(self):
                pass
        vecchi = (c.C, c.U, c.Telecamera)
        c.C, c.U, c.Telecamera = d, os.path.join(d, "uscita"), Finta
        sys.modules.setdefault("focus_nvr", types.ModuleType("focus_nvr"))
        try:
            c.main()
        finally:
            c.C, c.U, c.Telecamera = vecchi
        es = json.load(open(os.path.join(d, "uscita", "ripristino.json"), encoding="utf-8"))
        st = json.load(open(os.path.join(d, "uscita", "stato.json"), encoding="utf-8"))
        ok(es.get("ripristino", {}).get("tornata") is True, f"main: tornata ({es.get('esito')})")
        ok(fermate and st.get("fase") == "finito", "main: lascia finale e stato «finito»")
        ok(es["comandi"]["zoom"] == 0 and es["luce"]["canale"]["giorno"], "main: niente zoom, luce controllata")
        ok(os.path.exists(os.path.join(d, "uscita", "confronto_fine.jpg")), "main: confronto_fine.jpg")
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    prova_guida()
    prova_comandi()
    prova_ripristino()
    prova_foto_vere()
    prova_main()
    print("TUTTO BENE" if not ERRORI else f"{len(ERRORI)} PROVE FALLITE: {ERRORI}")
    sys.exit(1 if ERRORI else 0)
