"""
prova_parallelo - le prove a tavolino del compito parallelo1, con una libreria Focus finta.
VERSION 0.1.0 (16/11/2026)

Uso: python3 prova_parallelo.py [cartella con focus_nvr.py]
(di difetto ../../../kit-rifiuti-programma/scripts, o la variabile FOCUS_NVR).

La libreria finta (dll_finta) ha le stesse funzioni della DLL che usa parallelo.LibreriaFocus e chiama le funzioni di
ritorno VERE attraverso la loro tabella (come fa la DLL: puntatore all'oggetto -> tabella -> funzione), da fili suoi,
con ritardi a caso, handle riusati e un esito «orfano» dopo ogni Disconnect. Si puo' farla fallire per kit, oltre un
certo numero di collegamenti insieme, o far cadere il processo (os._exit) oltre un certo numero.

Prove:
  1. funzioni pure: credenziali, scelta dei kit, parti, confronto, fermate, verdetto;
  2. Smistatore: esiti fuori ordine da piu' fili, orfani;
  3. LibreriaFocus con la libreria finta, 8 fili su 30 kit: ogni kit ha il suo esito (nessuno scambio fra hSERVER),
     la seconda password, i muti che vanno in attesa, gli orfani contati;
  4. il compito intero (compito.py -> lavoro.py in processi a parte) sulla libreria finta: tutte le prove, il verdetto,
     niente UID in uscita, la cartella lavori cancellata;
  5. crash della strada A a N=8: A16 non parte, B va avanti;
  6. falliti oltre i 5 punti a A4: la strada A si ferma;
  7. il tetto di tempo.
"""
import ctypes
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time

QUI = os.path.dirname(os.path.abspath(__file__))
VERSION = "0.1.0"


def trova_focus_nvr():
    for d in [sys.argv[1] if len(sys.argv) > 1 else None, os.environ.get("FOCUS_NVR"), QUI,
              os.path.join(QUI, "..", "..", "..", "kit-rifiuti-programma", "scripts")]:
        if d and os.path.exists(os.path.join(d, "focus_nvr.py")):
            return os.path.abspath(d)
    raise SystemExit("manca focus_nvr.py (kit-rifiuti-programma/scripts): passalo come argomento")


# ------------------------------------------------------------------ la libreria finta

def dll_finta(opz=None):
    import focus_nvr as fn
    o = {"ritardo": [0.05, 0.25], "falliscono": [], "muti": [], "seconda_password": [], "max_insieme": 0,
         "crash_oltre": 0, "connect_blocca": 0.0, "seme": 7}
    o.update(opz or {})
    rnd = random.Random(o["seme"])
    stato = {"liberi": [], "prossimo": 1000, "attivi": {}, "aperti": set(), "gestori": {}, "liste": {},
             "collegati": set(), "massimo": 0}
    lk = threading.Lock()

    def chiama_stato(hs, ok, motivo):
        with lk:
            ptr = stato["gestori"].get(hs)
        if not ptr:
            return
        tab = ctypes.c_void_p.from_address(ptr).value
        f = fn._CB_SRV(ctypes.c_void_p.from_address(tab).value)
        s = fn.ST_VM_CONN_STATUS(0 if ok else 1, 13 if ok else motivo)
        f(None, 0, hs, ctypes.addressof(s))

    def connect(_this, pci):
        ci = pci._obj
        uid = ci.szAddr.decode()
        pw = ci.szUserPassword.decode()
        if o["connect_blocca"]:
            time.sleep(o["connect_blocca"])
        with lk:
            hs = stato["liberi"].pop(0) if stato["liberi"] else stato["prossimo"]
            if hs == stato["prossimo"]:
                stato["prossimo"] += 1
            stato["attivi"][hs] = uid
            stato["aperti"].add(hs)
            n = len(stato["aperti"])   # i collegamenti non ancora chiusi con Disconnect
            stato["massimo"] = max(stato["massimo"], n)
        if o["crash_oltre"] and n > o["crash_oltre"]:
            os._exit(3)
        troppi = bool(o["max_insieme"]) and n > o["max_insieme"]
        giusta = "altra" if uid in o["seconda_password"] else "giusta"

        def esito():
            time.sleep(rnd.uniform(*o["ritardo"]))
            for _ in range(100):   # aspetta che il gestore sia registrato (SetStatusHandler dopo Connect)
                with lk:
                    if hs in stato["gestori"] or hs not in stato["attivi"]:
                        break
                time.sleep(0.01)
            with lk:
                if stato["attivi"].get(hs) != uid:
                    return
            if uid in o["muti"]:
                return
            if uid in o["falliscono"] or troppi:
                chiama_stato(hs, False, 7)
            elif pw != giusta:
                chiama_stato(hs, False, 2)
            else:
                with lk:
                    stato["collegati"].add(hs)
                chiama_stato(hs, True, 13)
        threading.Thread(target=esito, daemon=True).start()
        return hs

    def disconnect(_this, hs):
        with lk:
            stato["collegati"].discard(hs)
            stato["aperti"].discard(hs)

        def libera():
            time.sleep(0.02)
            chiama_stato(hs, False, 10)   # un esito dopo la chiusura: deve finire fra gli orfani
            with lk:
                stato["attivi"].pop(hs, None)
                stato["gestori"].pop(hs, None)
                stato["liberi"].append(hs)
        threading.Thread(target=libera, daemon=True).start()

    def set_stato(_this, hs, ptr):
        with lk:
            stato["gestori"][hs] = ptr.value if hasattr(ptr, "value") else ptr
        return 1

    def info(_this, hs, psi):
        with lk:
            if hs not in stato["collegati"]:
                return 0
            uid = stato["attivi"].get(hs, "")
        si = psi._obj
        si.szModelName = ("FINTO-" + uid[-4:]).encode()
        si.ucCameraCount = 4
        return 1

    def lista(_this, hs):
        nodi = [fn.ST_VM_CHANNEL_LIST() for _ in range(4)]
        for i, x in enumerate(nodi):
            x.oData.hSERVER, x.oData.hCHANNEL, x.oData.uiChannelNum = hs, hs * 10 + i, i + 1
            x.oData.szTitle = f"CH{i + 1}".encode()
            if i < 3:
                x.pNext = ctypes.pointer(nodi[i + 1])
        p = ctypes.pointer(nodi[0])
        with lk:
            stato["liste"][ctypes.addressof(nodi[0])] = nodi
        return p

    def rilascia(_this, _hs, p):
        with lk:
            stato["liste"].pop(ctypes.addressof(p.contents), None)

    def giornaliero(_this, hs, ch, _pt, prd):
        with lk:
            if hs not in stato["collegati"]:
                return 0
        rd = prd._obj
        rd.uiTypeCount = 1440
        for i in range(60 * (ch % 10 + 1)):
            rd.eRecType[i] = 1
        return 1

    def modo(_this, _hs, pm):
        pm._obj.value = 2
        return 1

    f = {"ctor": lambda _t: None, "Init": lambda _t: 1, "Release": lambda _t: None, "Connect": connect,
         "Disconnect": disconnect, "SetStatusHandler": set_stato, "SetStreamHandler": lambda *_: 1,
         "SetEventHandler": lambda *_: 1, "GetServerInfo": info, "GetChannelList": lista,
         "ReleaseChannelList": rilascia, "GetRecordDaily": giornaliero, "GetP2PMode": modo}
    f["_stato"] = stato
    return f


# ------------------------------------------------------------------ prove

def uguale(a, b, cosa):
    if a != b:
        raise AssertionError(f"{cosa}: {a!r} invece di {b!r}")


def prova_pure():
    import parallelo as pa
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "focus_accesso.txt"), "w") as fh:
        fh.write("*;u;comune\n*<200;u;vecchia\nUIDX;v;sua\n")
    acc = pa.leggi_accesso([d, None, "/non/esiste"])
    uguale(pa.credenziali("uidx", 500, acc), [("v", "sua"), ("u", "comune"), ("u", "vecchia")], "credenziali uid")
    uguale(pa.credenziali("altro", 136, acc), [("u", "vecchia"), ("u", "comune")], "credenziali sotto 200")
    shutil.rmtree(d)
    righe = [{"uid": f"U{i}", "kit": str(100 + i), "risposte_24h": i % 5, "stato": "fatto" if i % 3 else "fallito"}
             for i in range(60)]
    righe += [{"uid": "U5", "kit": "105"}, {"uid": "U998", "kit": "998", "risposte_24h": 9}, {"uid": "", "kit": "1"}]
    k = pa.scegli_kit({"kit": righe}, 40, 1)
    uguale(len(k), 40, "quanti kit")
    uguale(len({x["uid"] for x in k}), 40, "uid diversi")
    if any(x["uid"] == "U998" for x in k):
        raise AssertionError("il kit 998 (prova di Dario) non va scelto")
    if any(r["risposte_24h"] == 0 and r["stato"] != "fatto" for r in righe[:60] for x in k if x["uid"] == r["uid"]):
        raise AssertionError("scelto un kit che non risponde")
    uguale(k, pa.scegli_kit({"kit": righe}, 40, 1), "stessa scelta con lo stesso seme")
    uguale([len(p) for p in pa.parti(list(range(40)), 8)], [5] * 8, "parti")
    uguale([len(p) for p in pa.parti(list(range(5)), 8)], [1] * 5, "parti con pochi kit")
    et = ["a", "b", "c", "d"]
    c = pa.confronta({"a": True, "b": True, "c": False, "d": True}, {"a": True, "b": False, "c": True}, et)
    uguale((c["falliti"], c["falliti_base"], c["punti"], c["persi"], c["guadagnati"], c["mancanti"]),
           (2, 1, 25.0, ["b", "d"], ["c"], ["d"]), "confronto")
    uguale(pa.da_fermare({"n": 4, "crash": None, "confronto": {"punti": 5.0}}), None, "5 punti non fermano")
    if not pa.da_fermare({"n": 4, "crash": None, "confronto": {"punti": 5.1}}):
        raise AssertionError("5,1 punti fermano")
    if not pa.da_fermare({"n": 8, "crash": "processo 1: codice 0xC0000005", "confronto": {}}):
        raise AssertionError("il crash ferma")
    cf = lambda f, fb=2: {"falliti": f, "falliti_base": fb}   # noqa: E731
    prove = [{"strada": "1", "n": 1, "secondi": 1000, "confronto": cf(2)},
             {"strada": "A", "n": 8, "secondi": 200, "confronto": cf(2)},
             {"strada": "B", "n": 8, "secondi": 190, "confronto": cf(2)}]
    v = pa.verdetto(prove)
    uguale((v["strade"]["A"]["vince"], v["strade"]["B"]["vince"], v["vince"]), (True, True, "A"), "pari: vince A")
    prove[2]["secondi"] = 150
    uguale(pa.verdetto(prove)["vince"], "B", "B molto piu' veloce")
    prove[1]["secondi"] = 250
    uguale(pa.verdetto(prove)["strade"]["A"]["vince"], False, "un quarto esatto non basta")
    prove[2]["confronto"] = cf(3)
    uguale(pa.verdetto(prove)["vince"], None, "un fallito in piu' non vince")
    uguale(pa.verdetto(prove[:1])["strade"]["A"]["vince"], False, "N=8 non misurato")
    uguale(pa.codice_leggibile(3221225477), "0xC0000005", "codice del crash")
    uguale(pa.codice_leggibile(-1073741819), "0xC0000005", "codice del crash negativo")
    print("1. funzioni pure: ok")


def prova_smistatore():
    import parallelo as pa
    s = pa.Smistatore()
    hs = list(range(1, 51))
    for h in hs:
        s.registra(h)
    out = {}

    def aspetta(h):
        out[h] = s.aspetta(h, 5)

    fili = [threading.Thread(target=aspetta, args=(h,)) for h in hs]
    for x in fili:
        x.start()
    mescolati = hs[:]
    random.Random(3).shuffle(mescolati)
    for h in mescolati:
        threading.Thread(target=s.arriva, args=(h, {"collegato": h % 2 == 0, "h": h})).start()
    for x in fili:
        x.join()
    uguale(all(out[h]["h"] == h for h in hs), True, "ogni filo il suo esito")
    s.dimentica(7)
    s.arriva(7, {"collegato": False, "h": 7})
    s.arriva(999, {"collegato": True})
    uguale(s.orfani, 2, "orfani")
    s.registra(7)
    uguale(s.aspetta(7, 0.05), None, "un handle riusato non eredita l'esito vecchio")
    print("2. smistatore: ok")


def prova_libreria():
    import focus_nvr as fn
    import parallelo as pa
    uids = [f"FINTO{i:04d}" for i in range(30)]
    dll = dll_finta({"falliscono": uids[0:3], "muti": uids[3:5], "seconda_password": uids[5:8]})
    lib = pa.LibreriaFocus(dll, fn)
    acc = ({}, [("u", "giusta"), ("u", "altra")], [])
    kit = [{"uid": u, "numero": 300 + i, "etichetta": f"KIT{300 + i}"} for i, u in enumerate(uids)]
    risultati, lk = {}, threading.Lock()
    coda = list(kit)

    def filo():
        while True:
            with lk:
                if not coda:
                    return
                k = coda.pop()
            r = pa.un_kit(lib, k, pa.credenziali(k["uid"], k["numero"], acc), attesa=2)
            with lk:
                risultati[k["etichetta"]] = r
    fili = [threading.Thread(target=filo) for _ in range(8)]
    t0 = time.time()
    for x in fili:
        x.start()
    for x in fili:
        x.join()
    for i, k in enumerate(kit):
        r = risultati[k["etichetta"]]
        if i < 3:
            uguale((r["ok"], r["collegamento"]), (False, "P2P fallito"), f"{k['etichetta']} fallisce")
        elif i < 5:
            uguale((r["ok"], r["collegamento"]), (False, "nessuna risposta in 2 s"), f"{k['etichetta']} muto")
        else:
            uguale(r["ok"], True, f"{k['etichetta']} ok")
            uguale(r["modello"], "FINTO-" + k["uid"][-4:], f"{k['etichetta']}: il modello e' il suo, non di un altro")
            uguale(r["minuti_oggi"], [60, 120, 180, 240], f"{k['etichetta']} minuti")
            uguale(r["tentativi"], 2 if i < 8 else 1, f"{k['etichetta']} tentativi")
        if k["uid"] in json.dumps(r):
            raise AssertionError("l'UID e' finito nel risultato")
    time.sleep(0.3)
    if dll["_stato"]["massimo"] < 6:
        raise AssertionError(f"collegamenti insieme: {dll['_stato']['massimo']}, dovevano essere ~8")
    if lib.smista.orfani < 25:
        raise AssertionError(f"orfani contati: {lib.smista.orfani}")
    print(f"3. libreria con 8 fili: ok ({round(time.time() - t0, 1)} s, fino a {dll['_stato']['massimo']} insieme, "
          f"{lib.smista.orfani} esiti orfani scartati)")


def compito_finto(cfg, finta, kit_n=24):
    d = tempfile.mkdtemp(prefix="parallelo1_")
    for f in ("compito.py", "lavoro.py", "parallelo.py", "prova_parallelo.py"):
        shutil.copy2(os.path.join(QUI, f), d)
    os.makedirs(os.path.join(d, "FocusNetSDK"))
    open(os.path.join(d, "FocusNetSDK", "FocusNetSDK.dll"), "w").write("finta")
    with open(os.path.join(d, "focus_accesso.txt"), "w") as fh:
        fh.write("*;u;giusta\n")
    json.dump([{"uid": f"SEGRETO{i:04d}", "numero": 400 + i, "etichetta": f"KIT{400 + i}"} for i in range(kit_n)],
              open(os.path.join(d, "kit.json"), "w"))
    json.dump(cfg, open(os.path.join(d, "parallelo.json"), "w"))
    env = dict(os.environ, PARALLELO_FINTA=json.dumps(finta),
               PYTHONPATH=os.pathsep.join([os.environ["FOCUS_NVR_DIR"], d]))
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(d, "compito.py"), d], env=env, capture_output=True, text=True,
                       timeout=600)
    if r.returncode:
        raise AssertionError(f"compito caduto: {r.stdout[-2000:]} {r.stderr[-2000:]}")
    es = json.load(open(os.path.join(d, "uscita", "parallelo.json")))
    tutto = ""
    for radice, _c, files in os.walk(os.path.join(d, "uscita")):
        for f in files:
            tutto += open(os.path.join(radice, f), encoding="utf-8", errors="replace").read()
    if "SEGRETO" in tutto or "giusta" in tutto:
        raise AssertionError("un UID o una password sono finiti in uscita")
    if os.path.exists(os.path.join(d, "lavori")):
        raise AssertionError("la cartella lavori (con gli UID) non e' stata cancellata")
    if "fatto" not in open(os.path.join(d, "uscita", "avanzamento.txt"), encoding="utf-8").read().splitlines()[-1]:
        raise AssertionError("avanzamento senza la riga «fatto»")
    shutil.rmtree(d)
    return es, round(time.time() - t0, 1)


BASE_CFG = {"pausa_s": 0, "attesa": 2, "tetto_ore": 0.1}


def prova_compito():
    es, s = compito_finto(BASE_CFG, {"ritardo": [0.3, 0.5], "falliscono": ["SEGRETO0003"]})
    nomi = [p["nome"] for p in es["prove"]]
    uguale(nomi, ["N1", "B2", "A4", "B4", "A8", "B8", "A16"], "ordine delle prove")
    for p in es["prove"]:
        uguale((p["crash"], p["confronto"]["falliti"], p["confronto"]["falliti_base"]), (None, 1, 1), p["nome"])
        uguale(p["processi_n"], p["n"] if p["strada"] == "B" else 1, f"{p['nome']} processi")
    t = {p["nome"]: p["secondi"] for p in es["prove"]}
    v = es["verdetto"]
    if not (t["A8"] < t["N1"] / 4 and v["strade"]["A"]["vince"]):
        raise AssertionError(f"A8 doveva vincere: {t} {v}")
    print(f"4. compito intero: ok in {s} s; tempi {t}; vince {v['vince']}")


def prova_crash():
    es, s = compito_finto(BASE_CFG, {"ritardo": [0.2, 0.3], "crash_oltre": 6})
    nomi = [p["nome"] for p in es["prove"]]
    uguale(nomi, ["N1", "B2", "A4", "B4", "A8", "B8"], "A16 non parte dopo il crash di A8")
    a8 = next(p for p in es["prove"] if p["nome"] == "A8")
    if not a8["crash"] or "A" not in es["fermate"]:
        raise AssertionError(f"il crash di A8 non e' stato visto: {a8['crash']} {es['fermate']}")
    uguale(es["verdetto"]["strade"]["A"]["vince"], False, "A col crash non vince")
    print(f"5. crash a A8: ok ({a8['crash']}; strada A ferma, B misurata fino a 8)")


def prova_falliti():
    es, s = compito_finto(BASE_CFG, {"ritardo": [0.2, 0.3], "max_insieme": 2})
    nomi = [p["nome"] for p in es["prove"]]
    if "A8" in nomi or "A16" in nomi or "A" not in es["fermate"]:
        raise AssertionError(f"A doveva fermarsi a A4: {nomi} {es['fermate']}")
    print(f"6. falliti oltre 5 punti: ok ({es['fermate']['A']})")


def prova_tetto():
    es, s = compito_finto(dict(BASE_CFG, tetto_ore=8 / 3600, minuti_minimi_prova=0), {"ritardo": [0.4, 0.5]})
    if "tetto" not in es["fermate"]:
        raise AssertionError(f"il tetto non ha fermato niente: {es['fermate']}")
    print(f"7. tetto: ok ({es['fermate']['tetto']}; prove fatte {[p['nome'] for p in es['prove']]})")


def main():
    d = trova_focus_nvr()
    os.environ["FOCUS_NVR_DIR"] = d
    sys.path.insert(0, d)
    sys.path.insert(0, QUI)
    prova_pure()
    prova_smistatore()
    prova_libreria()
    prova_compito()
    prova_crash()
    prova_falliti()
    prova_tetto()
    print("tutte le prove passate")


if __name__ == "__main__":
    main()
