"""Prove a tavolino del guardiano del ponte (guardiano.py 0.1.0, ponte 0.23.0): quali codici sono un guasto della
libreria, quando si rilancia, si aspetta o si smette, e il giro con un figlio finto e con un figlio vero che cade per
accesso alla memoria (ctypes legge l'indirizzo 0). Niente rete, niente DLL.
Uso: python3 prova_guardiano.py
version: 0.1.1 (19/11/2026): il ponte puo' essere dopo la 0.23.0
"""
import ast
import os
import subprocess
import sys
import tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import guardiano as g   # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


# --- che_guasto
ok(g.che_guasto(3221225477) == "accesso alla memoria", "3221225477 (quello del 40 e del 28) e' accesso alla memoria")
ok(g.che_guasto(-1073741819) == "accesso alla memoria", "lo stesso codice con segno")
ok(g.che_guasto(0xC0000374) == "heap rovinato" and g.che_guasto(0xC0000409), "heap rovinato e stack rotto")
ok(g.che_guasto(-11) and g.che_guasto(-6), "SIGSEGV e SIGABRT fuori da Windows")
ok(all(g.che_guasto(c) is None for c in (0, 1, 2, None, "x", -15, 15, 0xC000013A)),
   "0, 1, un kill (-15), Ctrl+C (0xC000013A) non sono guasti della libreria")
ok(g.esadecimale(3221225477) == "0xC0000005" and g.esadecimale(-1073741819) == "0xC0000005", "esadecimale")

# --- codice_per_uscire
c = g.codice_per_uscire(3221225477)
ok(c == (-1073741819 if os.name == "nt" else 5), f"codice_per_uscire(3221225477) = {c}")
ok(g.codice_per_uscire(0) == 0 and g.codice_per_uscire(1) == 1, "codice_per_uscire di 0 e 1")
ok(g.codice_per_uscire(256) == (256 if os.name == "nt" else 1), "fuori da Windows un codice non diventa 0 per caso")

# --- decidi
T = 1_000_000.0
F = T + 72 * 3600
ok(g.decidi([(T, 4680)], T, F)[0] == "rilancia", "la prima caduta dopo 78 minuti: si rilancia")
ok(g.decidi([(T, 4680)], F, F)[0] == "smetti", "a tempo finito si smette")
sei = [(T - 3000 + i * 400, 400) for i in range(6)]
ok(g.decidi(sei, T, F)[0] == "rilancia", "6 cadute nell'ultima ora: si rilancia ancora (tetto 6)")
sette = sei + [(T, 300)]
cosa, attesa, perche = g.decidi(sette, T, F)
ok(cosa == "aspetta" and attesa == 601, f"7 cadute nell'ultima ora: si aspetta che la prima esca dall'ora ({cosa}, {attesa})")
ok(g.decidi(sette, T, T + 100)[0] == "smetti", "7 nell'ora e il compito finisce prima che si liberi: si smette")
subito = [(T - 300, 5000), (T - 200, 30), (T - 100, 40), (T, 50)]
ok(g.decidi(subito, T, F)[0] == "smetti", "3 cadute di fila nei primi 2 minuti: si smette")
ok(g.decidi(subito[:3], T, F)[0] == "rilancia", "2 cadute di fila nei primi 2 minuti: si rilancia ancora")
ok(g.decidi([(T - 3700, 30), (T - 3650, 30), (T, 4000)], T, F)[0] == "rilancia",
   "due cadute subito e poi una dopo un'ora di vita: si rilancia")
tante = [(T - 86400 * 2 + i * 4000, 4000) for i in range(41)]
ok(g.decidi(tante, T, F)[0] == "smetti", "oltre 40 rilanci nel compito: si smette")
ok(g.decidi(tante[:40], T, F)[0] == "rilancia", "40 cadute: il 40esimo rilancio si fa")

# --- dove_e_caduto, sul guasto_memoria.txt vero del 40
G40 = '''Windows fatal exception: access violation

Thread 0x00008d8c (most recent call first):
  File "C:\\Users\\Alma\\archivio_kit3\\_compiti\\p2p_ponte40\\focus_nvr.py", line 543 in chiudi
  File "C:\\Users\\Alma\\archivio_kit3\\_compiti\\p2p_ponte40\\focus_nvr.py", line 553 in __exit__
  <invalid frame>
'''
ok(g.dove_e_caduto(G40) == "focus_nvr.py:543 chiudi", f"dove_e_caduto del 40: {g.dove_e_caduto(G40)!r}")
due = G40.replace("543 in chiudi", "100 in vecchia") + "\n" + G40
ok(g.dove_e_caduto(due) == "focus_nvr.py:543 chiudi", "dove_e_caduto guarda l'ultimo guasto del file")
ok(g.dove_e_caduto("") == "" and g.dove_e_caduto("niente") == "", "dove_e_caduto senza guasto: vuoto")

# --- ambiente e fine
env = g.ambiente_figlio({"KR_POSTO_COMPITO": "compito_2.zip", "_MEIPASS2": "x", "PATH": "p"}, F, 2)
ok(env["PONTE_FIGLIO"] == "1" and env["PONTE_FINE"] == str(int(F)) and env["PONTE_RILANCIO"] == "2"
   and env["KR_POSTO_COMPITO"] == "compito_2.zip" and "_MEIPASS2" not in env, "ambiente_figlio")
ok(g.fine_da_ambiente(env, 5) == int(F) and g.fine_da_ambiente({}, 5) == 5 and g.fine_da_ambiente({"PONTE_FINE": "x"}, 5) == 5,
   "fine_da_ambiente")
ok(g.comando_figlio("C:/c", exe="KR.exe", congelato=True) == ["KR.exe", "--compito", "C:/c"],
   "nell'exe il figlio e' «--compito <cartella>», come lo trova e lo ferma Kit_Rifiuti")
ok(g.comando_figlio("/c", exe="py", congelato=False) == ["py", "/c/compito.py", "/c"], "fuori dall'exe: python compito.py")

# --- il giro con un figlio finto
with tempfile.TemporaryDirectory() as d:
    righe, sonni, lanci = [], [], []
    orologio = [T]
    codici = [3221225477, 3221225477, 0]

    def lancia(cmd, cartella, env, uscita):
        lanci.append(env["PONTE_RILANCIO"])
        orologio[0] += 3000
        return codici.pop(0)

    def dormi(s):
        sonni.append(s)
        orologio[0] += s

    r = g.guarda(d, T + 72 * 3600, righe.append, lancia=lancia, dormi=dormi, adesso=lambda: orologio[0], cmd=["x"])
    ok(r == 0 and lanci == ["0", "1", "2"], f"due cadute e poi la fine: 3 lanci, esce con 0 ({r}, {lanci})")
    ok(sum("Lo rilancio" in x for x in righe) == 2 and sonni == [g.ATTESA_S] * 2, "due righe «Lo rilancio» e due attese")

    righe.clear()
    codici[:] = [1]
    ok(g.guarda(d, T + 72 * 3600, righe.append, lancia=lancia, dormi=dormi, adesso=lambda: orologio[0], cmd=["x"]) == 1
       and any("non e' un guasto" in x for x in righe), "un errore di Python (1) non si rilancia e passa a Kit_Rifiuti")

    righe.clear()
    codici[:] = [3221225477] * 10

    def lancia_subito(cmd, cartella, env, uscita):
        orologio[0] += 10
        return codici.pop(0)

    r = g.guarda(d, T + 72 * 3600 * 10, righe.append, lancia=lancia_subito, dormi=dormi, adesso=lambda: orologio[0],
                 cmd=["x"])
    ok(r == 3221225477 and len(codici) == 7 and "Non lo rilancio" in righe[-1],
       f"cade subito 3 volte: si smette col codice del guasto ({r}, {len(codici)} non usati)")

# --- il giro con un figlio vero che cade per accesso alla memoria, poi finisce bene
FIGLIO = r'''
import os, sys, ctypes, faulthandler
u = os.path.join(sys.argv[1], "uscita")
faulthandler.enable(open(os.path.join(u, "guasto_memoria.txt"), "a"), all_threads=True)
n = int(os.environ["PONTE_RILANCIO"])
open(os.path.join(u, "figli.txt"), "a").write(f"{n} {os.environ['PONTE_FIGLIO']} {os.environ['PONTE_FINE']}\n")
def chiudi():
    ctypes.string_at(0)
if n < 2:
    chiudi()
sys.exit(0)
'''
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "uscita"))
    script = os.path.join(d, "figlio.py")
    open(script, "w").write(FIGLIO)
    righe = []
    vecchia = g.ATTESA_S
    g.ATTESA_S = 0
    try:
        r = g.guarda(d, T * 10_000, righe.append, cmd=[sys.executable, script, d])
    finally:
        g.ATTESA_S = vecchia
    figli = open(os.path.join(d, "uscita", "figli.txt")).read().split("\n")
    ok(r == 0 and [x.split()[0] for x in figli if x] == ["0", "1", "2"],
       f"figlio vero: cade due volte (SIGSEGV), al terzo finisce, il guardiano esce con 0 ({r})")
    cadute = [x for x in righe if "e' caduto" in x]
    ok(len(cadute) == 2 and all("string_at" in x and "segnale 11" in x for x in cadute),
       f"la riga dice dove e' caduto: {cadute[:1]}")

# --- compito.py: il guardiano viene prima di tutto il resto, e il figlio usa la fine del guardiano
src = open(os.path.join(QUI, "compito.py"), encoding="utf-8").read()
ast.parse(src)
k_g = src.find("guardiano.guarda(")
ok(0 < k_g < src.find("def credenziali(") and k_g < src.find("def prova(") and "PONTE_FIGLIO" in src[:k_g],
   "compito.py: senza PONTE_FIGLIO fa il guardiano prima di definire le prove")
ok("\nt_fine = time.time() + DURATA\nimport guardiano" in src and "guardiano.fine_da_ambiente(os.environ, t_fine)" in src
   and '__name__ == "__main__" and os.environ.get("PONTE_FIGLIO")' in src and int(__import__("re").search(r'VERSIONE = "p2p_ponte 0\.(\d+)', src).group(1)) >= 23,
   "compito.py: t_fine da PONTE_FINE dopo la riga dove si fermano i lavori a parte, guardiano solo in __main__, 0.23.0 o dopo")
p = subprocess.run([sys.executable, "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read())",
                    os.path.join(QUI, "guardiano.py")])
ok(p.returncode == 0, "guardiano.py si legge")

print(f"\n{'TUTTE OK' if not fallite else str(len(fallite)) + ' FALLITE'}")
sys.exit(1 if fallite else 0)
