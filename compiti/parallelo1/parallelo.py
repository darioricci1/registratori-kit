"""
parallelo - i pezzi del compito parallelo1 (registratori-kit): piu' registratori Focus insieme.
VERSION 0.1.0 (16/11/2026)

Perche' (Dario, 16/11/2026: come interrogare piu' registratori contemporaneamente): il ponte li interroga uno alla
volta (SDK = threading.Lock(), «la libreria Focus da un filo alla volta») e ogni collegamento P2P (TUTK) prende 30-60
secondi, quindi un giro su ~300 kit dura ore. La libreria pero' e' quella di UVMS, che tiene collegati molti
registratori insieme: Connect rende un handle hSERVER per registratore e le funzioni di ritorno lo ricevono.

Qui:
  - carica_dll(cartella, agenti): la DLL con le firme di focus_nvr (le stesse misure delle strutture), P2PAgentInit(agenti);
  - LibreriaFocus: UNA istanza IFocusNetSDK con N collegamenti insieme; le tre interfacce di ritorno sono una sola per
    tutti i registratori e smistano per hSERVER (Smistatore). Le funzioni di ritorno non si liberano mai (vivono quanto
    il processo: il compito 28 e' morto con 0xC0000005, IPOTESI una funzione di ritorno gia' liberata);
  - un_kit(): la lettura leggera di un kit (collegamento, modello, canali, minuti registrati oggi; niente video,
    niente comandi alle telecamere);
  - le funzioni pure del compito (credenziali, scelta dei kit, parti, confronti, criterio), provate in
    prova_parallelo.py con una libreria finta.
"""
import ctypes
import datetime
import os
import random
import re
import sys
import threading
import time

VERSION = "0.1.0"

P = ctypes.c_void_p


# ------------------------------------------------------------------ la DLL

def carica_dll(cartella, agenti=16):
    """Le funzioni della DLL di quella cartella, con le firme di focus_nvr, e P2PAgentInit(agenti). Una volta per
    processo."""
    import focus_nvr as fn
    if os.name != "nt":
        raise RuntimeError("la libreria Focus c'e' solo per Windows")
    sbagliate = fn.misure_giuste()
    if sbagliate:
        raise RuntimeError(f"strutture diverse dalla DLL: {sbagliate}")
    if not os.path.exists(os.path.join(cartella, "FocusNetSDK.dll")):
        raise RuntimeError(f"manca FocusNetSDK.dll in {cartella}")
    os.add_dll_directory(cartella)
    os.environ["PATH"] = cartella + os.pathsep + os.environ.get("PATH", "")
    lib = ctypes.CDLL(os.path.join(cartella, "FocusNetSDK.dll"))
    f = {}
    for k, nome in fn.NOMI.items():
        x = getattr(lib, nome)
        if k in ("P2PAgentInit", "P2PAgentDeinit"):
            x.restype, x.argtypes = ctypes.c_int, ([ctypes.c_int] if k == "P2PAgentInit" else [])
        else:
            r, a = fn.FIRME[k]
            x.restype, x.argtypes = r, [P] + a
        f[k] = x
    f["P2PAgentInit"](int(agenti))
    return f


# ------------------------------------------------------------------ smistare le funzioni di ritorno per hSERVER

class Smistatore:
    """Gli esiti di collegamento arrivano dai fili della libreria con l'hSERVER: ognuno va a chi aspetta quel server.
    Un esito per un server che nessuno ha registrato (gia' scollegato, o mai nostro) e' «orfano» e si conta soltanto:
    non deve finire su un collegamento nuovo che ha ricevuto lo stesso numero."""

    def __init__(self):
        self.cond = threading.Condition()
        self.attivi = set()
        self.primo = {}       # hs -> il primo esito arrivato (quello che decide collegato / no)
        self.tutti = {}       # hs -> quanti esiti in tutto (per vedere i cambi a collegamento fatto)
        self.orfani = 0
        self.canali = 0       # esiti dei canali (non servono qui: si contano)

    def registra(self, hs):
        with self.cond:
            self.attivi.add(hs)
            self.primo.pop(hs, None)
            self.tutti[hs] = 0

    def arriva(self, hs, esito):
        with self.cond:
            if hs not in self.attivi:
                self.orfani += 1
                return False
            self.tutti[hs] = self.tutti.get(hs, 0) + 1
            if hs not in self.primo:
                self.primo[hs] = esito
                self.cond.notify_all()
            return True

    def aspetta(self, hs, secondi):
        with self.cond:
            self.cond.wait_for(lambda: hs in self.primo, timeout=secondi)
            return self.primo.get(hs)

    def dimentica(self, hs):
        with self.cond:
            self.attivi.discard(hs)
            self.primo.pop(hs, None)
            return self.tutti.pop(hs, 0)


class LibreriaFocus:
    """Una istanza IFocusNetSDK per tutto il processo; collega()/scollega() da piu' fili insieme."""

    def __init__(self, f, fn):
        self.f, self.fn = f, fn
        self._obj = ctypes.create_string_buffer(64)   # la classe e' solo il puntatore alla tabella (8 byte)
        self.this = ctypes.cast(self._obj, P)
        self.f["ctor"](self.this)
        if not self.f["Init"](self.this):
            raise RuntimeError("Init della libreria Focus fallito")
        self.smista = Smistatore()
        self._tieni = []      # le funzioni di ritorno e le tabelle: mai liberate
        self._prepara_ritorni()

    def _tabella(self, funzioni):
        tab = (P * len(funzioni))(*[ctypes.cast(x, P) for x in funzioni])
        ogg = (P * 1)(ctypes.cast(tab, P))
        self._tieni += [funzioni, tab, ogg]
        return ctypes.cast(ogg, P)

    def _prepara_ritorni(self):
        fn = self.fn

        def su_collegamento(_this, _hi, hs, p):
            try:
                s = ctypes.cast(p, ctypes.POINTER(fn.ST_VM_CONN_STATUS)).contents
                self.smista.arriva(int(hs), {"collegato": s.eStatus == 0, "motivo": s.eReason,
                                             "testo": fn.MOTIVI_COLLEGAMENTO.get(s.eReason, str(s.eReason))})
            except Exception:   # noqa: BLE001 - un'eccezione qui dentro non deve arrivare alla DLL
                pass
            return True

        def su_canale(*_):
            self.smista.canali += 1
            return True

        def niente(*_):
            return True

        cs, cc = fn._CB_SRV, fn._CB_CAN
        self.h_stato = self._tabella([cs(su_collegamento), cc(su_canale), cc(niente), cs(niente)])
        self.h_flusso = self._tabella([cc(niente), cc(niente), cc(niente), cc(niente)])   # niente video
        self.h_eventi = self._tabella([cs(niente), cc(niente)])

    def collega(self, uid, utente, password, attesa=40):
        """(hs, ok, testo, tempi). hs va poi chiuso con scollega(), anche se ok e' falso."""
        fn = self.fn
        ci = fn.ST_VM_CONN_INFO()
        ci.eConnType = fn.E_CONN_TUTK_P2P
        ci.szAddr = uid.encode("ascii")[:127]
        ci.szSiteName = b"Kit_Rifiuti"
        ci.usTcpPort = 9010
        ci.szUserID = utente.encode("utf-8")[:1023]
        ci.szUserPassword = password.encode("utf-8")[:1023]
        t0 = time.time()
        hs = self.f["Connect"](self.this, ctypes.byref(ci))
        tempi = {"connect_s": round(time.time() - t0, 2)}
        ctypes.memset(ctypes.byref(ci), 0, ctypes.sizeof(ci))   # la password non resta in memoria
        if not hs:
            return 0, False, "la libreria non ha accettato i dati di collegamento", tempi
        hs = int(hs)
        self.smista.registra(hs)
        self.f["SetStatusHandler"](self.this, hs, self.h_stato)
        self.f["SetStreamHandler"](self.this, hs, self.h_flusso)
        self.f["SetEventHandler"](self.this, hs, self.h_eventi)
        while time.time() - t0 < attesa:
            es = self.smista.aspetta(hs, 1.0)
            if es is not None:
                if not es["collegato"]:
                    tempi["esito_s"] = round(time.time() - t0, 2)
                    return hs, False, es["testo"], tempi
                break
            if self.info(hs):   # alcune versioni non chiamano OnConnectionStatus: se risponde, e' collegato
                break
        else:
            tempi["esito_s"] = round(time.time() - t0, 2)
            return hs, False, f"nessuna risposta in {attesa} s", tempi
        tempi["esito_s"] = round(time.time() - t0, 2)
        modo = ctypes.c_int(0)
        self.f["GetP2PMode"](self.this, hs, ctypes.byref(modo))
        return hs, True, f"collegato ({fn.MODI_P2P.get(modo.value, modo.value)})", tempi

    def info(self, hs):
        fn = self.fn
        si = fn.ST_VM_SERVER_INFO()
        if not hs or not self.f["GetServerInfo"](self.this, hs, ctypes.byref(si)):
            return None
        return {"modello": si.szModelName.decode("ascii", "replace").strip(), "telecamere": si.ucCameraCount}

    def canali(self, hs):
        p = self.f["GetChannelList"](self.this, hs)
        out, q = [], p
        while q:
            d = q.contents.oData
            out.append((d.uiChannelNum, d.hCHANNEL, d.szTitle.decode("utf-8", "replace").strip()))
            q = q.contents.pNext
        if p:
            self.f["ReleaseChannelList"](self.this, hs, p)
        return out

    def minuti(self, hs, canale_h, giorno):
        """I minuti registrati quel giorno (0-1440), o None se il registratore non risponde."""
        fn = self.fn
        rd = fn.ST_VM_RECORD_DAILY()
        t = fn.tempo_vm(giorno)
        if not self.f["GetRecordDaily"](self.this, hs, canale_h, ctypes.byref(t), ctypes.byref(rd)):
            return None
        n = min(int(rd.uiTypeCount or 1440), 1440)
        return sum(1 for x in rd.eRecType[:n] if x)

    def scollega(self, hs):
        if hs:
            try:
                self.f["Disconnect"](self.this, hs)
            finally:
                self.smista.dimentica(hs)

    def chiudi(self):
        self.f["Release"](self.this)


# ------------------------------------------------------------------ un kit: la lettura leggera

PAROLE_CREDENZIALI = ("password", "sconosciuto", "utente")


def un_kit(lib, kit, credenziali, attesa=40, oggi=None):
    """Collegamento (provando le credenziali in ordine), modello, canali, minuti registrati oggi per canale, chiusura.
    Il risultato non contiene ne' l'UID ne' le credenziali: solo l'etichetta del kit."""
    oggi = oggi or datetime.datetime.combine(datetime.date.today(), datetime.time())
    r = {"kit": kit["etichetta"], "ok": False, "inizio": time.strftime("%H:%M:%S")}
    t0 = time.time()
    hs, ok, testo, tempi = 0, False, "sul PC manca focus_accesso.txt con utente e password", {}
    try:
        for i, (ut, pw) in enumerate(credenziali):
            if hs:
                lib.scollega(hs)
                hs = 0
            hs, ok, testo, tempi = lib.collega(kit["uid"], ut, pw, attesa)
            r["tentativi"] = i + 1
            if ok or not any(w in testo for w in PAROLE_CREDENZIALI):
                break
        r["collegamento"] = testo
        r["secondi_collegamento"] = round(time.time() - t0, 1)
        r.update(tempi)
        if "(" in testo:
            r["modo"] = testo.split("(", 1)[1].rstrip(")")
        if ok:
            t1 = time.time()
            inf = lib.info(hs)
            can = lib.canali(hs)
            r["modello"] = (inf or {}).get("modello")
            r["telecamere"] = (inf or {}).get("telecamere")
            r["canali"] = len(can)
            r["minuti_oggi"] = [lib.minuti(hs, h, oggi) for _num, h, _tit in can]
            r["secondi_letture"] = round(time.time() - t1, 1)
            r["ok"] = inf is not None
            if inf is None:
                r["errore"] = "collegato ma il registratore non da' modello e canali"
    except Exception as ex:   # noqa: BLE001 - un kit non ferma gli altri
        r["errore"] = f"{type(ex).__name__}: {str(ex)[:200]}"
    finally:
        try:
            lib.scollega(hs)
        except Exception as ex:   # noqa: BLE001
            r["errore_chiusura"] = f"{type(ex).__name__}: {str(ex)[:200]}"
    r["secondi"] = round(time.time() - t0, 1)
    return r


# ------------------------------------------------------------------ funzioni pure

def leggi_accesso(cartelle):
    """Le righe di focus_accesso.txt (uid;utente;password, «*» per tutti, «*<200» per i kit fino al 199) della prima
    cartella che lo ha: (per_uid, generiche, vecchie)."""
    tutte, generiche, vecchie = {}, [], []
    for d in cartelle:
        f = os.path.join(d, "focus_accesso.txt") if d else ""
        if not f or not os.path.exists(f):
            continue
        for riga in open(f, encoding="utf-8", errors="replace"):
            p = [x.strip() for x in riga.strip().split(";")]
            if len(p) >= 3 and p[0]:
                if p[0] == "*":
                    generiche.append((p[1], p[2]))
                elif p[0] == "*<200":
                    vecchie.append((p[1], p[2]))
                else:
                    tutte.setdefault(p[0].upper(), (p[1], p[2]))
    return tutte, generiche, vecchie


def credenziali(uid, numero, accesso):
    """Le (utente, password) da provare per quell'UID, in ordine e senza doppioni (come il ponte)."""
    tutte, generiche, vecchie = accesso
    ordine = (vecchie + generiche) if (numero is not None and numero < 200) else (generiche + vecchie)
    lista = ([tutte[uid.upper()]] if uid.upper() in tutte else []) + ordine
    visti, out = set(), []
    for c in lista:
        if c not in visti:
            visti.add(c)
            out.append(c)
    return out


def numero_kit(testo):
    m = re.search(r"(\d{1,4})", str(testo or ""))
    return int(m.group(1)) if m else None


def scegli_kit(stato, quanti=40, seme=1, escludi=("998",)):
    """Dalle righe di op=stato del sito (kit: [{uid, kit, nome, stato, risposte_24h, ...}]) i kit che rispondono:
    prima quelli con piu' risposte nelle ultime 24 ore, poi quelli con l'ultima prova riuscita; un UID una volta sola.
    Ritorna [{uid, numero, etichetta}] in un ordine mescolato col seme (lo stesso per tutte le prove)."""
    rnd = random.Random(seme)
    righe = (stato or {}).get("kit") or []
    cand, visti = [], set()
    for r in righe:
        uid = str(r.get("uid") or "").strip()
        kit = str(r.get("kit") or "").strip().lstrip("0")
        if not uid or uid.upper() in visti or kit in escludi:
            continue
        risposte = int(r.get("risposte_24h") or 0)
        if risposte <= 0 and r.get("stato") != "fatto":
            continue
        visti.add(uid.upper())
        cand.append((-risposte, 0 if r.get("stato") == "fatto" else 1, rnd.random(), uid, kit, r.get("nome")))
    cand.sort()
    scelti = cand[:quanti]
    rnd.shuffle(scelti)
    out, etichette = [], set()
    for _a, _b, _c, uid, kit, nome in scelti:
        e = f"KIT{kit}" if kit else str(nome or "senza nome")[:40]
        base, k = e, 2
        while e in etichette:
            e, k = f"{base}#{k}", k + 1
        etichette.add(e)
        out.append({"uid": uid, "numero": numero_kit(kit), "etichetta": e})
    return out


def parti(kit, n):
    """I kit divisi in n parti a giro (la 1a prende il 1o, il (n+1)o, ...): parti di misura quasi uguale."""
    n = max(1, int(n))
    return [p for p in (kit[i::n] for i in range(n)) if p]


def confronta(base, prova, etichette):
    """base, prova: {etichetta: ok}. Un kit che manca nella prova (processo caduto o fermato) conta come fallito.
    Ritorna riusciti, falliti, punti (falliti in piu' rispetto alla base, in punti percentuali), persi e guadagnati."""
    n = len(etichette) or 1
    fb = sum(1 for e in etichette if not base.get(e))
    fp = sum(1 for e in etichette if not prova.get(e))
    return {"kit": len(etichette), "riusciti": len(etichette) - fp, "falliti": fp, "falliti_base": fb,
            "falliti_pct": round(100 * fp / n, 1), "punti": round(100 * (fp - fb) / n, 1),
            "persi": sorted(e for e in etichette if base.get(e) and not prova.get(e)),
            "guadagnati": sorted(e for e in etichette if prova.get(e) and not base.get(e)),
            "mancanti": sorted(e for e in etichette if e not in prova)}


def da_fermare(prova, soglia_punti=5.0):
    """Il motivo per non salire di N su quella strada, o None."""
    if prova.get("crash"):
        return f"crash a N={prova['n']} ({prova['crash']})"
    c = prova.get("confronto") or {}
    if c.get("punti", 0) > soglia_punti:
        return f"falliti +{c['punti']} punti rispetto a N=1 a N={prova['n']} (soglia {soglia_punti})"
    return None


CRITERIO = ("Una strada vince se con N=8 fa il giro dei kit in meno di un quarto del tempo di N=1 (stessi kit) senza "
            "piu' falliti di N=1, senza crash e senza essere stata fermata dal tetto. Se vincono tutte e due vince la "
            "piu' veloce a N=8; se i tempi sono entro il 10% l'una dall'altra, la A (un processo e una libreria sola).")


def verdetto(prove, quarto=0.25):
    """prove: [{nome, strada, n, secondi, crash, fermata_tetto, confronto}]. Il giudizio di ogni strada col criterio
    scritto prima (CRITERIO) e la strada che vince, o None."""
    base = next((p for p in prove if p["strada"] == "1"), None)
    out = {"criterio": CRITERIO, "strade": {}, "vince": None}
    if not base or not base.get("secondi"):
        out["nota"] = "manca la prova con N=1"
        return out
    t1 = base["secondi"]
    for s in ("A", "B"):
        p8 = next((p for p in prove if p["strada"] == s and p["n"] == 8), None)
        if p8 is None:
            out["strade"][s] = {"vince": False, "perche": "N=8 non misurato (strada fermata prima o tetto di tempo)"}
            continue
        c = p8.get("confronto") or {}
        rapporto = round(p8["secondi"] / t1, 3) if t1 else None
        motivi = []
        if p8.get("crash"):
            motivi.append(f"crash ({p8['crash']})")
        if p8.get("fermata_tetto"):
            motivi.append("fermata dal tetto di tempo")
        if rapporto is None or rapporto >= quarto:
            motivi.append(f"tempo {rapporto} di N=1 (serve meno di {quarto})")
        if c.get("falliti", 0) > c.get("falliti_base", 0):
            motivi.append(f"falliti {c.get('falliti')} contro {c.get('falliti_base')} di N=1")
        out["strade"][s] = {"vince": not motivi, "tempo_su_n1": rapporto, "secondi": p8["secondi"],
                            "falliti": c.get("falliti"), "falliti_n1": c.get("falliti_base"),
                            "perche": "; ".join(motivi) or "sotto un quarto del tempo e senza falliti in piu'"}
    vincenti = [s for s in ("A", "B") if out["strade"][s]["vince"]]
    if len(vincenti) == 1:
        out["vince"] = vincenti[0]
    elif len(vincenti) == 2:
        a, b = out["strade"]["A"]["secondi"], out["strade"]["B"]["secondi"]
        out["vince"] = "A" if a <= b * 1.10 else "B"
    return out


def codice_leggibile(c):
    if c is None:
        return None
    c = int(c)
    if c < 0:
        c &= 0xFFFFFFFF
    return f"0x{c:08X}" if c > 0xFFFF else str(c)


def memoria_mb():
    """Memoria del processo: {'ora_mb', 'picco_mb'} (Windows: working set; altrove: il picco di getrusage)."""
    try:
        if os.name == "nt":
            class PMC(ctypes.Structure):
                _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]
            k = ctypes.windll.kernel32
            k.GetCurrentProcess.restype = ctypes.c_void_p
            m = PMC()
            m.cb = ctypes.sizeof(PMC)
            f = k.K32GetProcessMemoryInfo
            f.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
            if f(k.GetCurrentProcess(), ctypes.byref(m), m.cb):
                return {"ora_mb": round(m.WorkingSetSize / 1e6, 1), "picco_mb": round(m.PeakWorkingSetSize / 1e6, 1)}
            return {}
        import resource
        picco = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {"picco_mb": round(picco / (1e6 if sys.platform == "darwin" else 1e3), 1)}
    except Exception as ex:   # noqa: BLE001
        return {"errore": f"{type(ex).__name__}: {ex}"}
