"""Prove a tavolino di dimezza.py: fotogrammi finti, scaricatore finto che risponde da una lista di immagini, niente rete.
Uso: python3 prova_dimezza.py   (kit_rifiuti.py da KR_SCRIPTS, se no da ../../../kit-rifiuti-programma/scripts)
version: 0.1.0 (11/11/2026)
"""
import datetime
import os
import sys

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.environ.get("KR_SCRIPTS") or os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts"))
import kit_rifiuti as kr   # noqa: E402
import dimezza as dz       # noqa: E402

H, W = 720, 1280
ZONA = [[0.3, 0.3, 0.4, 0.5]]
rnd = np.random.default_rng(7)
SFONDO = (np.clip(rnd.normal(120, 25, (H // 8, W // 8, 3)), 0, 255)).astype(np.uint8).repeat(8, 0).repeat(8, 1)
TEXTURA = (np.clip(rnd.normal(0, 30, (60, 60, 3)), -60, 60)).astype(np.int16)
fallite = []


def scena(t, sacco_da=None, auto_da=None, luce=0.0, rumore=3):
    """Il fotogramma al secondo t: lo sfondo, la luce che cresce di `luce` per ora, un sacco scuro da `sacco_da` e una
    «auto» chiara piu' grande da `auto_da` (tutti e due nella zona)."""
    f = SFONDO.astype(np.int16) + int(round(luce * t / 3600.0))
    if sacco_da is not None and t >= sacco_da:
        f[400:460, 560:620] = np.array([30, 35, 40], np.int16) + TEXTURA
    if auto_da is not None and t >= auto_da:
        f[260:420, 650:880] = np.array([210, 205, 200], np.int16) + np.tile(TEXTURA, (3, 4, 1))[:160, :230]
    f = f + rnd.integers(-rumore, rumore + 1, f.shape)
    return np.clip(f, 0, 255).astype(np.uint8)


def scaricatore(**k):
    """leggi(t) finto: tre fotogrammi del campione di 3 s da `scena`, 0,6 MB per campione; `rotto` = momenti che non
    arrivano."""
    rotto = k.pop("rotto", ())
    chiesti = []

    def leggi(t):
        chiesti.append(t)
        if any(abs(t - r) < 0.5 for r in rotto):
            return None, {"errore": "nessun fotogramma", "secondi": 30}
        return [scena(t + d, **k) for d in dz.TEMPI_FOTOGRAMMI], {"mb": 0.6, "secondi": 4.0, "secondi_video": 3.0}
    return leggi, chiesti


def controlla(nome, cond, dettaglio=""):
    print(("ok    " if cond else "NO    ") + nome + (f"  ({dettaglio})" if dettaglio else ""))
    if not cond:
        fallite.append(nome)


# 1. un sacco a 23 minuti di un'ora, con la luce che cresce di 25 livelli nell'ora
leggi, chiesti = scaricatore(sacco_da=1380.0, luce=25)
cam = dz.Campioni(leggi)
r = dz.cerca(kr, cam, 3600, ZONA)
controlla("sacco: c'e' un cambio", r["esito"] == "cambio", r.get("esito"))
controlla("sacco: il momento e' nell'intervallo", r["esito"] == "cambio" and r["lo"] <= 1380.0 <= r["hi"] + dz.CAMPIONE_S,
          f"{r.get('lo')}-{r.get('hi')}")
controlla("sacco: intervallo sotto 60 s", r["esito"] == "cambio" and r["hi"] - r["lo"] < 60, f"{r.get('hi', 0) - r.get('lo', 0)}")
controlla("sacco: al massimo 8 richieste (inizio, fine, 6 meta')", cam.conti["richieste"] <= 8, str(cam.conti["richieste"]))
controlla("sacco: il pezzo e' il sacco", r["esito"] == "cambio" and kr.nella_zona(r["scelto"]["box"], [[560 / W, 400 / H, 60 / W, 60 / H]], margine=0.0),
          str(r.get("scelto", {}).get("box")))
cf = dz.confronta(1380.0, r.get("lo"), r.get("hi"))
controlla("sacco: confronta dice dentro", cf and cf["dentro"], str(cf))
controlla("sacco: 4,8 MB scaricati, ora intera stimata 720 MB",
          abs(cam.conti["mb"] - 0.6 * cam.conti["richieste"]) < 1e-6
          and dz.stima_ora(cam.conti["mb"], cam.conti["secondi_video"], 3600) == 720.0,
          f"{cam.conti['mb']} MB, {dz.stima_ora(cam.conti['mb'], cam.conti['secondi_video'], 3600)}")
da, sec = dz.finestra_finale(r["lo"], r["hi"], 3600)
controlla("sacco: l'ultimo tratto contiene il momento con 20 s prima", da <= 1380.0 - 0.0 and da + sec >= r["hi"] + 3 and sec <= 95,
          f"{da} + {sec} s")

# 2. niente nella zona, solo luce: lo dice dopo due richieste
leggi, chiesti = scaricatore(luce=40)
cam = dz.Campioni(leggi)
r = dz.cerca(kr, cam, 3600, ZONA)
controlla("niente: nessun cambio", r["esito"] == "nessun cambio", r.get("esito"))
controlla("niente: due richieste sole", cam.conti["richieste"] == 2, str(cam.conti["richieste"]))

# 3. due cambi: un'auto che parcheggia a 40 minuti (pezzo grande) e il sacco a 10: si dimezza il punteggio piu' alto,
# il sacco va negli «altri» con la forchetta dai campioni gia' scaricati, senza richieste in piu'
leggi, chiesti = scaricatore(sacco_da=600.0, auto_da=2400.0, luce=10)
cam = dz.Campioni(leggi)
r = dz.cerca(kr, cam, 3600, ZONA)
controlla("due cambi: c'e' un cambio", r["esito"] == "cambio", r.get("esito"))
controlla("due cambi: si dimezza il pezzo col punteggio piu' alto (l'auto, 2400 s)",
          r["esito"] == "cambio" and r["lo"] <= 2400 <= r["hi"] + 3, f"{r.get('lo')}-{r.get('hi')}")
alt = r.get("altri") or []
controlla("due cambi: il sacco e' fra gli altri", len(alt) >= 1, str(len(alt)))
if alt:
    fk = alt[0]["campioni"]
    controlla("due cambi: forchetta del sacco dai campioni (prima dei 600 s senza, dopo con)",
              fk["a"] is not None and fk["a"] >= 600 and (fk["da"] is None or fk["da"] < 600), str(fk["da"]) + "-" + str(fk["a"]))
controlla("due cambi: gli altri non scaricano niente", cam.conti["richieste"] == len(chiesti) and cam.conti["richieste"] <= 8,
          str(cam.conti["richieste"]))
n_prima = cam.conti["richieste"]
leggi, chiesti = scaricatore(sacco_da=600.0, auto_da=2400.0, luce=10)
cam = dz.Campioni(leggi)
r = dz.cerca(kr, cam, 3600, ZONA, dimezza_altri=1)
a0 = (r.get("altri") or [{}])[0]
controlla("due cambi, dimezza_altri=1: anche il sacco ha il suo intervallo sotto 60 s",
          a0.get("lo") is not None and a0["lo"] <= 600 <= a0["hi"] + 3 and a0["hi"] - a0["lo"] < 60, f"{a0.get('lo')}-{a0.get('hi')}")
controlla("due cambi, dimezza_altri=1: il secondo costa al massimo 6 richieste in piu'",
          cam.conti["richieste"] - n_prima <= 6, f"{n_prima} -> {cam.conti['richieste']}")

# 4. un campione a meta' che non arriva: si prova 6 s piu' in la'; se non arriva neanche quello, ci si ferma
leggi, chiesti = scaricatore(sacco_da=1380.0, rotto=(1798.5,))
cam = dz.Campioni(leggi)
r = dz.cerca(kr, cam, 3600, ZONA)
controlla("rotto una volta: va avanti 6 s dopo", r["esito"] == "cambio" and r["fermato"] is None and r["passi"][0][0] == 1804.5,
          str(r.get("passi", [[None]])[0]))
leggi, chiesti = scaricatore(sacco_da=1380.0, rotto=(1798.5, 1804.5))
cam = dz.Campioni(leggi)
r = dz.cerca(kr, cam, 3600, ZONA)
controlla("rotto due volte: si ferma e lo dice", r["esito"] == "cambio" and r["fermato"] == "campione non scaricato",
          str(r.get("fermato")))
leggi, chiesti = scaricatore(sacco_da=1380.0, rotto=(0.0,))
r = dz.cerca(kr, dz.Campioni(leggi), 3600, ZONA)
controlla("inizio non scaricato: non scaricato", r["esito"] == "non scaricato", r.get("esito"))

# 5. dimezza da solo: una funzione «presente» a gradino
cam = dz.Campioni(lambda t: ([t], {"mb": 0.1}))
lo, hi, passi, ferm = dz.dimezza(cam, 0.0, 3597.0, lambda F: (F[0] >= 2000.0, 0, 0))
controlla("dimezza: gradino a 2000 s", lo < 2000.0 <= hi and hi - lo < 60 and len(passi) == 6, f"{lo}-{hi}, {len(passi)} passi")
controlla("Campioni: un momento si scarica una volta", cam(10.0) is cam(10.0) and cam.conti["richieste"] == 7, str(cam.conti["richieste"]))

# 6. il resto
controlla("finestra_finale dentro la finestra", dz.finestra_finale(5.0, 50.0, 60) == (0.0, 60), str(dz.finestra_finale(5.0, 50.0, 60)))
ini = datetime.datetime(2026, 11, 1, 12, 37, 36)
controlla("secondi_da", dz.secondi_da(ini, "2026-11-01 13:00:36") == 1380.0)
controlla("coperto: prima della prima registrazione no",
          dz.coperto((datetime.datetime(2026, 10, 24, 21), datetime.datetime(2026, 11, 11)), datetime.datetime(2026, 9, 27, 12),
                     datetime.datetime(2026, 9, 27, 12, 2))[0] is False)
controlla("coperto: intervallo non detto si prova", dz.coperto(None, ini, ini)[0] is True)
testo = ("n;tipo;da;a;durata_s;telecamere;punteggio;veicolo;targa\n1;visita;0:00:05;0:00:09;4;1;0.1;;\n"
         "2;abbandono;0:00:31;0:00:50;19;1+2;0.4;si;GY747HN\n")
ab = dz.abbandoni_csv(testo, datetime.datetime(2026, 11, 1, 13, 0, 5))
controlla("abbandoni_csv", len(ab) == 1 and ab[0]["ora"] == "13:00:36" and ab[0]["targa"] == "GY747HN", str(ab))
pv = dz.piu_vicino(ab + [{"ora": "13:05:00", "targa": "", "telecamere": "1"}], datetime.date(2026, 11, 1), "2026-11-01 13:00:40")
controlla("piu_vicino", pv and pv["secondi"] == 4.0 and pv["targa"] == "GY747HN", str(pv))
controlla("piu_vicino senza abbandoni", dz.piu_vicino([], datetime.date(2026, 11, 1), "2026-11-01 13:00:40") is None)
controlla("confronta fuori", dz.confronta(100.0, 200.0, 250.0)["dentro"] is False and dz.confronta(100.0, 200.0, 250.0)["fuori_di_s"] == 100.0)

print(f"\n{'TUTTE VERDI' if not fallite else str(len(fallite)) + ' ROSSE: ' + ', '.join(fallite)}")
if __name__ == "__main__":
    sys.exit(1 if fallite else 0)
