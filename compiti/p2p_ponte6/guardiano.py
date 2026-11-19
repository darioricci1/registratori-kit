"""Il guardiano del ponte: il lavoro con la libreria Focus gira in un processo figlio, e se la libreria lo fa cadere
(0xC0000005, accesso alla memoria) il guardiano lo rilancia, cosi' il compito non muore (ponte 0.23.0, 19/11/2026).

Perche': il compito p2p_ponte40 si e' chiuso il 19/11 alle 8:50 dopo 78 minuti con «errore 3221225477», come il
compito 28 l'11/11. guasto_memoria.txt (faulthandler) dice dove: focus_nvr.Registratore.chiudi, sulla riga di
Disconnect, dentro il `with` di una prova P2P. E' dentro la DLL: Python non lo puo' prendere con un try, e Kit_Rifiuti
un compito caduto non lo fa ripartire, quindi la pagina «Registrazioni dei kit» si fermava fino al compito dopo.

Come gira: Kit_Rifiuti lancia compito.py come sempre. Senza PONTE_FIGLIO=1 nell'ambiente compito.py fa il guardiano:
rilancia lo stesso exe con «--compito <cartella>» (lo stesso modo in cui Kit_Rifiuti lo trova e lo ferma) e
PONTE_FIGLIO=1, PONTE_FINE (l'ora di fine del compito, che non si allunga a ogni rilancio) e PONTE_RILANCIO (quante
volte e' gia' ripartito). Il figlio fa il ponte di prima. Quando il figlio finisce:
- con 0 (finito, o «su Drive c'e' un compito nuovo: chiudo questo») il guardiano finisce con 0;
- con un guasto della libreria (accesso alla memoria, heap rovinato, stack rotto: GUASTI) lo rilancia dopo ATTESA_S
  secondi, con una riga nell'avanzamento (codice, minuti di vita, ultima funzione di guasto_memoria.txt);
- con qualunque altro codice (un errore di Python, il processo chiuso da Kit_Rifiuti) finisce con quel codice.
Tetti: al massimo TETTO_ORA rilanci in un'ora (oltre si aspetta che l'ora si liberi) e TETTO_TOTALE in tutto il
compito; dopo TETTO_SUBITO cadute di fila nei primi SUBITO_S secondi di vita non si rilancia piu' (il guasto non e' a
caso). Superato un tetto il guardiano finisce col codice del guasto, come prima.
La decisione e' decidi(), una funzione pura; guarda() e' il giro, con lancia/dormi/adesso finti nelle prove
(prova_guardiano.py, anche con un figlio vero che cade per accesso alla memoria).
version: 0.1.0 (19/11/2026)
"""
import os
import re
import subprocess
import sys
import time

VERSIONE = "0.1.0"
# Codici di uscita di Windows che vengono dalla libreria, non da Python. Kit_Rifiuti li vede come numeri senza segno.
GUASTI = {
    0xC0000005: "accesso alla memoria",
    0xC0000374: "heap rovinato",
    0xC0000409: "stack rotto (fail fast)",
    0xC000001D: "istruzione non valida",
    0xC00000FD: "stack esaurito",
}
SEGNALI = {11: "accesso alla memoria (SIGSEGV)", 6: "abort (SIGABRT)", 7: "SIGBUS"}   # fuori da Windows, per le prove
TETTO_ORA = 6
TETTO_TOTALE = 40
TETTO_SUBITO = 3
SUBITO_S = 120
ATTESA_S = 20


def che_guasto(codice):
    """Il nome del guasto della libreria per un codice di uscita, o None se non e' un guasto (0, 1, ...). Funzione pura.
    Accetta il codice senza segno (3221225477), con segno (-1073741819) e i segnali di Popen fuori da Windows (-11)."""
    if codice is None:
        return None
    try:
        c = int(codice)
    except (TypeError, ValueError):
        return None
    if c < 0 and -c in SEGNALI:
        return SEGNALI[-c]
    return GUASTI.get(c & 0xFFFFFFFF)


def esadecimale(codice):
    try:
        if int(codice) < 0 and -int(codice) in SEGNALI:
            return f"segnale {-int(codice)}"
        return f"0x{int(codice) & 0xFFFFFFFF:08X}"
    except (TypeError, ValueError):
        return str(codice)


def decidi(cadute, adesso, fine, tetto_ora=TETTO_ORA, tetto_totale=TETTO_TOTALE, tetto_subito=TETTO_SUBITO,
           subito_s=SUBITO_S):
    """cadute: le cadute per guasto finora, [(quando, secondi di vita)], l'ultima in fondo. Ritorna (cosa, secondi,
    perche'): ("rilancia", 0, ...), ("aspetta", s, ...) se l'ora ha gia' tetto_ora rilanci, ("smetti", 0, ...).
    Funzione pura."""
    if adesso >= fine:
        return "smetti", 0, "il tempo del compito e' finito"
    if len(cadute) > tetto_totale:
        return "smetti", 0, f"gia' {len(cadute) - 1} rilanci in questo compito (tetto {tetto_totale})"
    coda = cadute[-tetto_subito:]
    if len(coda) >= tetto_subito and all(v < subito_s for _, v in coda):
        return "smetti", 0, f"caduto {tetto_subito} volte di fila nei primi {subito_s} s: non e' un guasto a caso"
    nell_ora = sorted(q for q, _ in cadute if q > adesso - 3600)
    if len(nell_ora) > tetto_ora:
        libero = nell_ora[-tetto_ora - 1] + 3600   # quando la caduta piu' vecchia che conta esce dall'ora
        attesa = max(1, int(libero - adesso) + 1)
        if adesso + attesa >= fine:
            return "smetti", 0, f"{len(nell_ora)} cadute nell'ultima ora e il compito finisce prima che si liberi"
        return "aspetta", attesa, f"{len(nell_ora)} cadute nell'ultima ora (tetto {tetto_ora} rilanci)"
    return "rilancia", 0, f"rilancio {len(cadute)}, {len(nell_ora)} nell'ultima ora"


RE_RIGA = re.compile(r'File "([^"]+)", line (\d+) in (\S+)')


def dove_e_caduto(testo):
    """Dall'ultimo guasto in guasto_memoria.txt (faulthandler), la funzione in cima alla pila del primo filo:
    «focus_nvr.py:543 chiudi», o "" se non si legge. Funzione pura."""
    t = testo or ""
    k = t.rfind("Fatal Python error")
    k = max(k, t.rfind("fatal exception"))
    if k < 0:
        return ""
    m = RE_RIGA.search(t, k)
    if not m:
        return ""
    return f"{os.path.basename(m.group(1).replace(chr(92), '/'))}:{m.group(2)} {m.group(3)}"


def comando_figlio(cartella, exe=None, congelato=None, script=None):
    """Il comando per il figlio: l'exe di Kit_Rifiuti con «--compito <cartella>» (come lo lancia Kit_Rifiuti, che cosi'
    lo trova e lo ferma); fuori dall'exe (prove) python con lo script. Funzione pura."""
    exe = exe or sys.executable
    congelato = getattr(sys, "frozen", False) if congelato is None else congelato
    if congelato:
        return [exe, "--compito", cartella]
    return [exe, script or os.path.join(cartella, "compito.py"), cartella]


def ambiente_figlio(base, fine, rilancio):
    """L'ambiente del figlio: quello del guardiano (KR_POSTO_COMPITO e gli altri di Kit_Rifiuti) piu' PONTE_FIGLIO,
    PONTE_FINE e PONTE_RILANCIO, e PyInstaller che riparte da capo. Funzione pura."""
    env = dict(base)
    env["PONTE_FIGLIO"] = "1"
    env["PONTE_FINE"] = str(int(fine))
    env["PONTE_RILANCIO"] = str(int(rilancio))
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    for k in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL"):
        env.pop(k, None)
    return env


def fine_da_ambiente(env, difetto):
    """L'ora di fine per il figlio: PONTE_FINE se c'e' ed e' un numero, se no il difetto. Funzione pura."""
    try:
        f = float((env or {}).get("PONTE_FINE") or "")
    except ValueError:
        return difetto
    return f if f == f and f > 0 else difetto


def lancia_vero(cmd, cartella, env, uscita):
    """Fa girare il figlio fino alla fine e ne ritorna il codice di uscita."""
    with open(os.path.join(uscita, "registro_figlio.txt"), "a", encoding="utf-8", errors="replace") as log:
        p = subprocess.Popen(cmd, cwd=cartella, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=0x00000040 | 0x08000000 if os.name == "nt" else 0)   # IDLE, senza finestra
        try:
            with open(os.path.join(uscita, "pid_figlio.txt"), "w", encoding="utf-8") as fh:
                fh.write(str(p.pid))
        except OSError:
            pass
        return p.wait()


def guarda(cartella, fine, av, lancia=None, dormi=time.sleep, adesso=time.time, cmd=None, env=None):
    """Il giro del guardiano: lancia il figlio, e lo rilancia dopo un guasto della libreria finche' decidi() lo
    permette. Ritorna il codice di uscita per Kit_Rifiuti (0 se il figlio ha finito bene)."""
    uscita = os.path.join(cartella, "uscita")
    os.makedirs(uscita, exist_ok=True)
    lancia = lancia or lancia_vero
    cmd = cmd or comando_figlio(cartella)
    base = dict(os.environ if env is None else env)
    cadute = []
    av(f"guardiano {VERSIONE}: il ponte gira in un processo figlio, rilanciato se la libreria lo fa cadere "
       f"(al massimo {TETTO_ORA} volte in un'ora, {TETTO_TOTALE} in tutto)")
    while True:
        t0 = adesso()
        codice = lancia(cmd, cartella, ambiente_figlio(base, fine, len(cadute)), uscita)
        vita = adesso() - t0
        guasto = che_guasto(codice)
        if not guasto:
            if codice:
                av(f"guardiano: il ponte e' finito con {codice} ({esadecimale(codice)}), non e' un guasto della "
                   "libreria: non lo rilancio")
            return int(codice or 0)
        cadute.append((adesso(), vita))
        try:
            dove = dove_e_caduto(open(os.path.join(uscita, "guasto_memoria.txt"), encoding="utf-8",
                                      errors="replace").read())
        except OSError:
            dove = ""
        cosa, attesa, perche = decidi(cadute, adesso(), fine)
        riga = (f"guardiano: il ponte e' caduto con {esadecimale(codice)} ({guasto}) dopo {round(vita / 60)} min"
                + (f", in {dove}" if dove else ""))
        if cosa == "smetti":
            av(f"{riga}. Non lo rilancio: {perche}")
            return int(codice)
        if cosa == "aspetta":
            av(f"{riga}. {perche}: aspetto {round(attesa / 60)} min prima di rilanciarlo")
            dormi(attesa)
        else:
            av(f"{riga}. Lo rilancio fra {ATTESA_S} s ({perche})")
            dormi(ATTESA_S)
        if adesso() >= fine:
            av("guardiano: il tempo del compito e' finito mentre aspettavo, non lo rilancio")
            return int(codice)


def codice_per_uscire(codice):
    """Il codice da passare a os._exit: su Windows un DWORD scritto come int con segno (3221225477 -> -1073741819),
    altrove gli 8 bit. Funzione pura."""
    c = int(codice or 0) & 0xFFFFFFFF
    if os.name == "nt":
        return c - (1 << 32) if c >= (1 << 31) else c
    return c & 0xFF or (1 if c else 0)
