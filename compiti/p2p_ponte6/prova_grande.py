"""Prove a tavolino delle funzioni pure di prepara_grande.py: giudizi sicuri, il primo per evento, la scelta delle
positive (kit, notte e giorno, sovrapposizioni), gli altri abbandoni noti nell'ora, il sorteggio delle negative, la
distanza dagli abbandoni noti, i giorni che restano sul disco. Niente rete, niente file.
Uso: python3 prova_grande.py
version: 0.1.0 (12/11/2026)
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepara_grande as pg  # noqa: E402

D = datetime.datetime
fallite = []


def ok(cond, nome):
    print(("ok    " if cond else "ROSSA ") + nome)
    if not cond:
        fallite.append(nome)


# ------------------------------------------------------------------ giudizi
cl = [{"evento": "e1", "cam": 1, "inizio": 20, "box": [0.1, 0.1, 0.05, 0.05], "sicuro": True},
      {"evento": "e2", "cam": 2, "inizio": 10, "box": [], "sicuro": True},                 # senza riquadro
      {"evento": "e3", "cam": 1, "inizio": 10, "box": [0.2, 0.2, 0.1, 0.1], "sicuro": False}]   # non sicuro
pr = [{"evento": "e1", "cam": 1, "inizio": 20, "box": [0.11, 0.1, 0.05, 0.05], "sicuro": True}]
fi = [("giro9", [{"evento": "e4", "cam": 3, "t": 30.5, "box": [0.3, 0.3, 0.1, 0.1], "sicuro": True, "esito": "abbandono"},
                 {"evento": "e5", "cam": 3, "t": 30.5, "box": [0.3, 0.3, 0.1, 0.1], "sicuro": True, "esito": "niente"},
                 {"giro": "e6xxxxxxxx-rfdetr", "cam": 1, "t": 5, "box": [0.3, 0.3, 0.1, 0.1], "sicuro": True},
                 {"evento": "e1", "cam": 2, "t": 12, "box": [0.5, 0.5, 0.1, 0.1], "sicuro": True}])]
g = pg.giudizi_sicuri(cl, pr, fi)
ok(sorted({x["evento"] for x in g}) == ["e1", "e4", "e6xxxxxxxx"], "giudizi: solo sicuri, con riquadro e con esito abbandono")
p = pg.primo_per_evento(g)
ok(p["e1"]["t"] == 12 and p["e1"]["cam"] == 2, "primo per evento: il momento piu' presto")
g2 = [x for x in g if not (x["evento"] == "e1" and x["t"] == 12)]
ok(pg.primo_per_evento(g2)["e1"]["fonte"] == "etichette_prova", "a parita' di momento vince etichette_prova")

# ------------------------------------------------------------------ zona
ok(pg.tocca([0.1, 0.1, 0.1, 0.1], [[0.15, 0.15, 0.2, 0.2]]) and not pg.tocca([0.1, 0.1, 0.1, 0.1], [[0.5, 0.5, 0.2, 0.2]]),
   "dentro_zona: il riquadro tocca la zona o no")

# ------------------------------------------------------------------ positive
a = D(2026, 11, 1, 10, 30)
ini, off = pg.inizio_positiva("e1", a)
ok(5 * 60 <= off <= 55 * 60 and ini == a - datetime.timedelta(seconds=off), f"inizio sorteggiato fra 5 e 55 minuti prima ({off} s)")
ok(pg.inizio_positiva("e1", a) == (ini, off), "il sorteggio e' fisso (seme + evento)")
offs = {pg.inizio_positiva(f"x{i}", a)[1] // 600 for i in range(200)}
ok(len(offs) >= 5, "l'abbandono cade in punti diversi dell'ora")


def scheda(e, kit, giorno, ora, notte=False):
    return {"evento": e, "kit": kit, "notte": notte, "inizio": f"2026-11-{giorno:02d} {ora:02d}:00:00"}


sch = ([scheda(f"a{i}", 1, 1 + i, 10) for i in range(6)] + [scheda("b0", 2, 1, 10), scheda("b1", 2, 1, 10, True)]
       + [scheda(f"c{i}", 10 + i, 3, 22, True) for i in range(3)] + [scheda("d0", 3, 2, 9), scheda("d1", 3, 2, 9)])
s = pg.scegli_positive(sch, quante=50, per_kit=4)
kit = {}
for x in s:
    kit[x["kit"]] = kit.get(x["kit"], 0) + 1
ok(kit[1] == 4, f"al massimo 4 ore per kit ({kit[1]})")
ok(kit[2] == 1 and kit[3] == 1, "due ore dello stesso kit che si sovrappongono: una sola")
ok(len(s) == len({x["evento"] for x in s}), "ogni evento una volta sola")
s1 = pg.scegli_positive(sch, quante=6, per_kit=4)
ok(len({x["kit"] for x in s1}) == 6, "poche ore: prima una per kit (6 kit diversi)")
ok(sum(x["notte"] for x in s1) >= 3, "poche ore: notte e giorno a turno")

noti = [{"evento": "z1", "cam": 1, "atteso": D(2026, 11, 1, 10, 20), "box": [0.1, 0.1, 0.1, 0.1]},
        {"evento": "z2", "cam": 2, "atteso": D(2026, 11, 1, 10, 20), "box": [0.1, 0.1, 0.1, 0.1]},
        {"evento": "z3", "cam": 1, "atteso": D(2026, 11, 1, 12, 20), "box": [0.1, 0.1, 0.1, 0.1]},
        {"evento": "a0", "cam": 1, "atteso": D(2026, 11, 1, 10, 30), "box": [0.1, 0.1, 0.1, 0.1]}]
an = pg.altri_noti(dict(scheda("a0", 1, 1, 10), canale=0), noti)
ok([x["evento"] for x in an] == ["z1"], "altri_noti: stessa telecamera, dentro l'ora, non l'evento stesso")

# ------------------------------------------------------------------ disco
arch = {"primo": "2026-10-25 08:00", "letto_il": "2026-11-11T20:00:00Z", "giorni": {}}
oggi = datetime.date(2026, 11, 12)
ok(pg.resta_giorni(arch, D(2026, 10, 30, 10), oggi) == 4, "resta_giorni: 30/10 con il disco dal 25/10, letto ieri: 4 giorni")
ok(pg.resta_giorni(arch, D(2026, 10, 25, 10), oggi) < 0, "resta_giorni: gia' sparita")
ok(pg.resta_giorni({}, D(2026, 10, 30), oggi) is None, "resta_giorni: archivio non letto")

# ------------------------------------------------------------------ negative
pieno = {f"2026-11-{d:02d}": 1440 for d in range(1, 13)}
pool = [{"kit": k, "uid": f"U{k}", "canali": [0, 1], "parte": "sviluppo",
         "archivio": {c: {"primo": "2026-10-20 00:00", "letto_il": "2026-11-12", "giorni": pieno} for c in (0, 1)}}
        for k in range(5)]
pres, fuori = pg.estrai_negative(pool, oggi, 8, per_kit=2)
per = {}
for v in pres:
    per[v["kit"]] = per.get(v["kit"], 0) + 1
ok(len(pres) == 8 and max(per.values()) == 2, f"negative: fino a 2 per kit quando i kit non bastano ({per})")
ok(all(len({v["inizio"][:10] for v in pres if v["kit"] == k}) == per[k] for k in per), "negative dello stesso kit: giorni diversi")
pres1, _ = pg.estrai_negative(pool, oggi, 5, per_kit=2)
ok(len({v["kit"] for v in pres1}) == 5, "negative: prima una per kit")
ok(pres == pg.estrai_negative(pool, oggi, 8, per_kit=2)[0], "negative: il sorteggio e' fisso")
ok(sum(v["notte"] for v in pres) >= 3, "negative: anche di notte")
buco = [dict(pool[0], archivio={c: {"primo": "2026-10-20 00:00", "letto_il": "2026-11-12",
                                    "giorni": {k: 300 for k in pieno}} for c in (0, 1)})]
p0, f0 = pg.estrai_negative(buco, oggi, 2, per_kit=2)
ok(p0 == [] and f0 and "minuti registrati" in f0[0]["perche"], "negative: un giorno non registrato intero non entra")
v = {"inizio": "2026-11-05 10:00:00"}
ok(pg.vicino(v, [D(2026, 11, 5, 8, 30)]) and pg.vicino(v, [D(2026, 11, 5, 12, 50)]), "a meno di 2 ore da un abbandono: fuori")
ok(pg.vicino(v, [D(2026, 11, 5, 7, 50), D(2026, 11, 5, 13, 10)]) is None, "a piu' di 2 ore: dentro")
ok(pg.si_sovrappone({"inizio": "2026-11-05 10:00:00"}, {"inizio": "2026-11-05 10:59:00"})
   and not pg.si_sovrappone({"inizio": "2026-11-05 10:00:00"}, {"inizio": "2026-11-05 11:00:00"}), "ore che si sovrappongono")

print(f"\n{'TUTTE VERDI' if not fallite else str(len(fallite)) + ' ROSSE: ' + ', '.join(fallite)}")
sys.exit(1 if fallite else 0)
