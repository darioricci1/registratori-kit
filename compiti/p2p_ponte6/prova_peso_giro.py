"""Prove a tavolino di peso_giro.py (ponte 0.22.0) e di peso_dopo del ponte: quando comincia un giro, cosa si somma,
cosa arriva al sito e in uscita. Niente rete, niente DLL.
Uso: python3 prova_peso_giro.py
version: 0.1.0 (19/11/2026)
"""
import ast
import json
import os
import sys
import tempfile
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import peso_giro as pg   # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


def voce(uid, mb=1.0, rete=1.5, cpu=0.4, pr=0, archivio=False):
    return {"uid": uid, "kit": f"kit {uid}", "priorita": pr, "ok": True, "mb_foto": mb, "mb_scarico": 0.0,
            "mb_rete": rete, "s_processore": cpu, "s_durata": 20.0, "archivio": archivio}


# --- mb_dall_esito
es = {"camere": [{"canale": 1, "mb": 0.8}, {"canale": 2, "mb": None}, {"canale": 3, "mb": "0.45"}], "scarico_mb": 2.5}
ok(pg.mb_dall_esito(es) == (1.25, 2.5), "mb_dall_esito somma le foto (None = 0) e prende lo scarico")
ok(pg.mb_dall_esito({}) == (0.0, 0.0) and pg.mb_dall_esito(None) == (0.0, 0.0), "mb_dall_esito senza esito: zero")

# --- differenza
d = pg.differenza((100.0, 5.0, 1_000_000), (130.04, 5.73, 4_500_000))
ok(d == {"s_durata": 30.0, "s_processore": 0.73, "mb_rete": 3.5}, f"differenza: {d}")
ok(pg.differenza((0, 0, None), (1, 1, 5))["mb_rete"] is None, "differenza senza byte del processo: mb_rete None")
ok(pg.io_processo() is None or isinstance(pg.io_processo(), int), "io_processo: None fuori da Windows o un numero")

# --- segna: i giri
t = 1_000_000.0
st = None
st, n1 = pg.segna(st, voce("A", archivio=True), t, cpu_processo=10.0)
st, n2 = pg.segna(st, voce("B", mb=2.0, rete=None), t + 30, cpu_processo=11.0)
ok(n1 == 1 and n2 == 1, "le prime due prove del giro sono nel giro 1")
st, n0 = pg.segna(st, voce("Z", mb=3.0, pr=1), t + 40, cpu_processo=11.5)
ok(n0 == 0, "una prova chiesta a mano va nel giro 0")
st, n3 = pg.segna(st, voce("C"), t + 60, cpu_processo=12.0)
ok(n3 == 1, "dopo una prova a mano il giro continua")
st, n4 = pg.segna(st, voce("A"), t + 90, cpu_processo=13.0)
ok(n4 == 2, "un registratore gia' visto apre il giro 2")
st, n5 = pg.segna(st, voce("D"), t + 90 + pg.PAUSA_NUOVO_GIRO + 1, cpu_processo=14.0)
ok(n5 == 3, "dopo 20 minuti senza prove del giro ne comincia uno nuovo")
g1 = next(g for g in st["giri"] if g["giro"] == 1)
ok(g1["prove"] == 3 and g1["registratori"] == 3 and g1["mb_foto"] == 4.0, f"giro 1: 3 prove, 4 MB ({g1['mb_foto']})")
ok(g1["mb_rete"] == 3.0 and g1["mb_rete_misurato"], "giro 1: mb_rete solo dove misurato (B no)")
ok(g1["archivi"] == 1, "giro 1: un archivio")
ok(g1["s_processore_processo"] == 2.0, "giro 1: processore di tutto il ponte dal primo all'ultimo")
ok([p["uid"] for p in g1["pesanti"]] == ["B", "A", "C"], "giro 1: i pesanti ordinati (B senza rete conta i suoi 2 MB)")
ok(g1["pesanti"][0]["mb_rete"] in (1.5, None), "i pesanti per mb_rete, poi per mb")
g0 = next(g for g in st["giri"] if g["giro"] == 0)
ok(g0["prove"] == 1 and g0["mb_foto"] == 3.0, "giro 0: la prova a mano")

# --- tetto dei giri tenuti
st2 = None
for i in range(pg.GIRI_TENUTI + 7):
    st2, _ = pg.segna(st2, voce("X"), t + i * 10)
ok(len(st2["giri"]) == pg.GIRI_TENUTI and st2["giri"][-1]["giro"] == pg.GIRI_TENUTI + 7, "restano gli ultimi 200 giri")
st3 = None
for i in range(40):
    st3, _ = pg.segna(st3, voce(f"U{i}", mb=i), t + i)
ok(len(st3["giri"][0]["pesanti"]) == pg.PESANTI and st3["giri"][0]["pesanti"][0]["uid"] in ("U0", "U39"),
   "al massimo 15 pesanti per giro")

# --- riassunto
r = pg.riassunto(st)
ok(r["versione"] == pg.VERSIONE and len(r["giri"]) == 4, "riassunto: tutti i giri, giro 0 compreso")
x1 = next(g for g in r["giri"] if g["giro"] == 1)
ok(x1["minuti"] == 1.0 and x1["mb_per_prova"] == round(4 / 3, 3), f"riassunto giro 1: {x1['minuti']} min, {x1['mb_per_prova']} MB a prova")
ok(x1["quota_processore"] == round(2.0 / 60, 3) and "cpu_inizio" not in x1, "riassunto: quota di un processore, niente cpu_inizio")
ok(next(g for g in r["giri"] if g["giro"] == 0)["quota_processore"] is None, "giro 0 senza quota")
json.dumps(r)

# --- peso_dopo del ponte, preso da compito.py con un'uscita finta
src = open(os.path.join(QUI, "compito.py"), encoding="utf-8").read()
U = tempfile.mkdtemp()
g = {"pg": pg, "os": os, "json": json, "time": time, "U": U, "PC": "COMPUTERONE", "VERSIONE": "p2p_ponte prova",
     "PESO": {"stato": None}, "avvisi": []}
g["av"] = g["avvisi"].append
for nodo in ast.parse(src).body:
    if isinstance(nodo, ast.FunctionDef) and nodo.name in ("peso_prima", "peso_dopo", "scrivi_json"):
        exec(compile(ast.Module([nodo], []), "compito.py", "exec"), g)   # noqa: S102 - il nostro codice
ok("p2p_ponte 0.22.0" in src, "il ponte e' alla 0.22.0")
ok('"movimento.json", "movimento_fatto.txt"' in src, "il lavoro del movimento c'e' ancora, ma parte solo con movimento.json")
prima = g["peso_prima"]()
ok(prima is not None and len(prima) == 3, "peso_prima: un'istantanea")
es = {"camere": [{"canale": 1, "mb": 0.6}, {"canale": 2, "mb": 0.7}], "archivio": [{"canale": 1}],
      "archivio_peso": {"s_durata": 12.0, "mb_rete": None}}
g["peso_dopo"]({"id": 7, "uid": "UIDA", "kit": "VIANO · 200", "priorita": 0}, True, es, prima)
ok(es["peso"]["mb_foto"] == 1.3 and es["peso"]["giro"] == 1, f"peso nell'esito per il sito: {es.get('peso')}")
righe = open(os.path.join(U, "peso_prove.jsonl"), encoding="utf-8").read().splitlines()
ok(len(righe) == 1 and json.loads(righe[0])["archivio_s"] == 12.0 and json.loads(righe[0])["id"] == 7,
   "peso_prove.jsonl: una riga con l'archivio")
pj = json.load(open(os.path.join(U, "peso_giri.json"), encoding="utf-8"))
ok(pj["pc"] == "COMPUTERONE" and pj["giri"][0]["prove"] == 1 and pj["giri"][0]["archivi"] == 1, "peso_giri.json scritto")
g["peso_dopo"]({"id": 8, "uid": "UIDB"}, False, None, prima)   # un esito che non e' un dizionario: niente eccezioni
ok(any("peso del giro" in a for a in g["avvisi"]), "peso_dopo non ferma il ponte se qualcosa va storto (lo scrive)")
g["peso_dopo"]({"id": 9, "uid": "UIDC"}, True, {}, None)
ok(len(open(os.path.join(U, "peso_prove.jsonl"), encoding="utf-8").read().splitlines()) == 1, "senza istantanea non segna")

print(f"\n{len(fallite)} fallite" if fallite else "\ntutte giuste")
sys.exit(1 if fallite else 0)
