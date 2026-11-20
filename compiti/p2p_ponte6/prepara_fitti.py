"""prepara_fitti.py: fitti.json del compito p2p_ponte44 (ponte 0.25.0, fitti.py 0.1.0). Kit_Rifiuti,
analisi/piu-fotogrammi-criterio-2026-11-20.md: per decidere se 4-6 fotogrammi al minuto nei minuti agitati trovano più
abbandoni servono più ore con i fotogrammi in più, e il disco dei registratori gira: le ore delle scorte 35/35b/36
(scorta.json) ancora sul registratore, dalla più vicina a uscire.

  python3 -I prepara_fitti.py <scorta.json> <stato.json> <fitti.json> [--perse perse.txt] [--pc COMPUTERONE]
                              [--parti 8] [--nome p2p_ponte44] [--margine_min 0.05] [--modo tutti] [--per_minuto 6]

stato.json = GET op=stato di prova-nvr-remoto (archivio: «primo» di ogni canale, letto dal ponte una volta al giorno).
Un'ora entra se «primo» del suo canale è prima dell'inizio dell'ora meno margine_min giorni (l'ora c'è ancora); le ore
in perse.txt (una per riga: le ore perse dalla 0.99.20) vanno prima delle altre a parità di urgenza, ma l'ordine è il
margine: quella che il disco perde prima va per prima. Niente video, niente catena: solo miniature dei minuti e in più.
Funzioni pure provate in prova_fitti.py.

0.2.0 (20/11/2026, compito p2p_ponte45): l'elenco non invecchia. Il 44 aveva fitti.json fatto alle 10:46 del 20/11 e
partiva quando partiva: le ore escono dal disco ogni giorno. Ora nel compito va fitti_fonte.json (le ore candidate e
quelle gia' fatte), e il ponte, appena parte (e a ogni rilancio del guardiano), legge op=stato e rifa' qui l'elenco
(cfg_da_fonte): il margine e' quello di adesso, cioe' l'inizio dell'ora meno il «primo» del canale meno il tempo
passato da quando il ponte ha letto l'archivio (letto_il: il disco gira di un giorno al giorno). Se op=stato non
risponde, i margini di fitti_fonte.json meno i giorni passati da allora.

  python3 -I prepara_fitti.py --fonte <fitti.json|scorta.json> <gia_fatte.json> <fitti_fonte.json> [--perse perse.txt]
                              [--pc COMPUTERONE] [--parti 4] [--nome p2p_ponte45] [--stato stato.json]

gia_fatte.json = ["pos014_kit434", ...] (le ore che un compito di prima ha gia' messo su Drive). Con --stato stampa
anche l'elenco che il ponte farebbe con quello stato.
version: 0.2.0 (20/11/2026)
0.1.0 (20/11/2026)
"""
import datetime
import json
import sys

VERSIONE = "0.2.0"
MB_ORA_MINUTI = 3.6      # 72 miniature (ora.json delle scorte: mb_minuti 2,1-5,5, media 3,6)
MB_MINIATURA = 0.05


def dt(s):
    return datetime.datetime.strptime(str(s)[:16].replace("T", " "), "%Y-%m-%d %H:%M")


def giorni_passati(quando, adesso):
    """0.2.0: i giorni da `quando` («2026-11-20T09:12:46.126Z», UTC) ad `adesso` (datetime con fuso); 0 se non si legge
    o se `adesso` manca. Mai negativi. Funzione pura."""
    if not quando or adesso is None:
        return 0.0
    try:
        t = datetime.datetime.fromisoformat(str(quando).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return max(0.0, (adesso - t).total_seconds() / 86400)


def margini(ore, archivio, adesso=None):
    """[(ora, margine in giorni o None)]: quanto prima dell'inizio dell'ora comincia la registrazione rimasta sul disco
    di quel canale («primo» dell'archivio). 0.2.0: con `adesso` (datetime con fuso) meno i giorni passati da letto_il,
    cioe' il margine di adesso e non quello del giorno in cui il ponte ha letto l'archivio. Funzione pura."""
    ar = {(a.get("uid"), int(a.get("canale", -1))): a for a in archivio}
    out = []
    for o in ore:
        a = ar.get((o.get("uid"), int(o.get("canale", -1))))
        m = None
        if a and a.get("primo"):
            m = round((dt(o["inizio"]) - dt(a["primo"])).total_seconds() / 86400
                      - giorni_passati(a.get("letto_il"), adesso), 2)
        out.append((o, m))
    return out


def scegli(ore, archivio, perse=(), margine_min=0.05, adesso=None, con_margini=None):
    """Le ore ancora sul registratore, in ordine di margine (le perse prima a parità), ognuna pronta per scorta.py:
    niente video, niente catena, «margine_giorni» scritto. 0.2.0: `adesso` come in margini; con_margini = [(ora,
    margine)] gia' fatti (senza archivio). Funzione pura."""
    perse = set(perse)
    tenute = []
    for o, m in (con_margini if con_margini is not None else margini(ore, archivio, adesso)):
        if m is None or m < margine_min:
            continue
        x = dict(o, video=[], catena=False, margine_giorni=m, persa=o["nome"] in perse)
        if x["persa"]:
            x["fitti_modo"] = "tutti"   # le ore perse: tutti gli intervalli, a tavolino si sceglie
        x.pop("fuori_catena", None)
        tenute.append(x)
    tenute.sort(key=lambda x: (x["margine_giorni"], not x["persa"], x["nome"]))
    return tenute


def stima_mb(n_ore, modo="tutti", per_minuto=6, intervalli_agitati=12, minuti=True):
    """MB dal registratore (minuti=True) o su Drive (minuti=False: solo le miniature in più): tutti i 71 intervalli o
    quelli agitati (12 in media sulle 204 ore delle scorte: 19 di giorno, 5 di notte). Funzione pura."""
    iv = 71 if modo == "tutti" else intervalli_agitati
    return round(n_ore * ((MB_ORA_MINUTI if minuti else 0) + iv * (per_minuto - 1) * MB_MINIATURA), 1)


def cfg_per(ore, pc, nome, parti=4, modo="agitati", per_minuto=6, stato_letto=None, adesso=None):
    """0.2.0: la configurazione della scorta «fitti» per scorta.py (quella di fitti.json del 44) attorno alle ore
    scelte, con le stime. Funzione pura."""
    sigla = str(nome).replace("p2p_ponte", "")
    cfg = {"pc": pc, "preparato_il": (adesso or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"),
           "prepara": f"prepara_fitti.py {VERSIONE}", "stato_letto": stato_letto, "ordine_dato": True,
           "fitti": {"modo": modo, "per_minuto": int(per_minuto)},
           "finestra": {"dalle": "00:00", "alle": "23:59"},
           "limiti": {"ore_di_lavoro": 10.0, "minuti_per_ora": 18.0, "mb_in_tutto": 5000.0, "mb_parte_drive": 170.0},
           "gb_liberi_min": 5, "posti_drive": [f"fitti{sigla}_{k}.zip" for k in range(1, int(parti) + 1)],
           "come": "le ore delle scorte ancora sul registratore, dalla più vicina a uscire; per ognuna le 72 miniature "
                   "dei minuti e le miniature in più (fitti.py) in <ora>/fitti/"}
    pn = sum(bool(o.get("persa")) for o in ore)
    n = int(per_minuto)
    cfg["stima_mb"] = round(stima_mb(len(ore) - pn, modo, n) + stima_mb(pn, "tutti", n), 1)
    cfg["stima_mb_drive"] = round(stima_mb(len(ore) - pn, modo, n, minuti=False) + stima_mb(pn, "tutti", n, minuti=False), 1)
    cfg["ore"] = ore
    return cfg


CAMPI_FONTE = ("pc", "nome", "parti", "modo", "per_minuto", "margine_min", "perse", "gia_fatte", "stato_letto")


def fonte_da(ore, gia_fatte, perse=(), pc="COMPUTERONE", nome="p2p_ponte45", parti=4, modo="agitati", per_minuto=6,
             margine_min=0.05, stato_letto=None, adesso=None):
    """0.2.0: fitti_fonte.json: le ore candidate (quelle di un fitti.json o di scorta.json, senza le gia' fatte), coi
    margini che avevano allora, e i parametri per rifare l'elenco nel ponte. Funzione pura."""
    gia = set(gia_fatte or [])
    cand = []
    for o in ore or []:
        if o.get("nome") in gia:
            continue
        x = {k: v for k, v in o.items() if k not in ("persa", "fitti_modo")}
        cand.append(x)
    return {"versione": VERSIONE, "preparato_il": (adesso or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"),
            "pc": pc, "nome": nome, "parti": int(parti), "modo": modo, "per_minuto": int(per_minuto),
            "margine_min": float(margine_min), "perse": sorted(set(perse or [])), "gia_fatte": sorted(gia),
            "stato_letto": stato_letto,
            "come": "il ponte rifa' l'elenco quando parte (prepara_fitti.cfg_da_fonte) con op=stato di quel momento",
            "ore": cand}


def cfg_da_fonte(fonte, stato, adesso):
    """0.2.0, nel ponte alla partenza: fitti_fonte.json + op=stato di adesso -> la cfg della scorta «fitti» con le ore
    ancora sul registratore adesso, dalla piu' vicina a uscire. stato None o senza archivio: i margini scritti nella
    fonte meno i giorni passati da fonte["stato_letto"]. `adesso`: datetime con fuso. Funzione pura."""
    gia = set(fonte.get("gia_fatte") or [])
    ore = [o for o in fonte.get("ore") or [] if o.get("nome") not in gia]
    perse = fonte.get("perse") or []
    mm = float(fonte.get("margine_min", 0.05))
    archivio = (stato or {}).get("archivio") if isinstance(stato, dict) else None
    if archivio:
        scelte = scegli(ore, archivio, perse, mm, adesso)
        come, letto = "op=stato alla partenza del ponte", stato.get("ora")
    else:
        passati = giorni_passati(fonte.get("stato_letto"), adesso)
        cm = [(o, None if o.get("margine_giorni") is None else round(float(o["margine_giorni"]) - passati, 2)) for o in ore]
        scelte = scegli(ore, None, perse, mm, con_margini=cm)
        come, letto = f"op=stato non letto: i margini della fonte meno {round(passati, 2)} giorni", fonte.get("stato_letto")
    cfg = cfg_per(scelte, fonte.get("pc") or "COMPUTERONE", fonte.get("nome") or "p2p_ponte45", fonte.get("parti", 4),
                  fonte.get("modo", "agitati"), fonte.get("per_minuto", 6), letto,
                  adesso.astimezone().replace(tzinfo=None) if adesso else None)
    for k in ("gb_liberi_min", "finestra"):   # la fonte puo' cambiarli
        if fonte.get(k) is not None:
            cfg[k] = fonte[k]
    cfg["limiti"] = dict(cfg["limiti"], **(fonte.get("limiti") or {}))
    cfg.update(rifatto_con=come, candidate=len(ore), gia_fatte=len(gia))
    return cfg


def main_fonte(a):
    """--fonte <fitti.json|scorta.json> <gia_fatte.json> <fitti_fonte.json> [opzioni]"""
    sorgente, gia_f, uscita = a[2], a[3], a[4]
    opz = {"--perse": None, "--pc": "COMPUTERONE", "--parti": "4", "--nome": "p2p_ponte45", "--margine_min": "0.05",
           "--modo": "agitati", "--per_minuto": "6", "--stato": None}
    i = 5
    while i < len(a):
        opz[a[i]] = a[i + 1]
        i += 2
    src = json.load(open(sorgente, encoding="utf-8"))
    gia = json.load(open(gia_f, encoding="utf-8")) if gia_f != "-" else []
    perse = [r.strip() for r in open(opz["--perse"], encoding="utf-8") if r.strip()] if opz["--perse"] else \
        [o["nome"] for o in src.get("ore") or [] if o.get("persa")]
    f = fonte_da(src.get("ore") or [], gia, perse, opz["--pc"], opz["--nome"], opz["--parti"], opz["--modo"],
                 opz["--per_minuto"], opz["--margine_min"], src.get("stato_letto"))
    json.dump(f, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(f['ore'])} ore candidate ({len(f['gia_fatte'])} gia' fatte fuori, {len(f['perse'])} perse) in {uscita}")
    if opz["--stato"]:
        st = json.load(open(opz["--stato"], encoding="utf-8"))
        cfg = cfg_da_fonte(f, st, datetime.datetime.now(datetime.timezone.utc))
        print(f"con {opz['--stato']}: {len(cfg['ore'])} ore ancora sul registratore, stima {cfg['stima_mb']} MB dal "
              f"registratore, {cfg['stima_mb_drive']} MB su Drive")
        for o in cfg["ore"]:
            print(f"  {o['nome']:<16} {o['tipo']:<9} {o['inizio']}  margine {o['margine_giorni']:>5} giorni"
                  + ("  PERSA" if o["persa"] else ""))


def main(a):
    if len(a) > 1 and a[1] == "--fonte":
        return main_fonte(a)
    scorta, stato, uscita = a[1], a[2], a[3]
    opz = {"--perse": None, "--pc": "2026-002", "--parti": "4", "--nome": "p2p_ponte44", "--margine_min": "0.05",
           "--modo": "agitati", "--per_minuto": "6"}
    i = 4
    while i < len(a):
        opz[a[i]] = a[i + 1]
        i += 2
    sc = json.load(open(scorta, encoding="utf-8"))
    st = json.load(open(stato, encoding="utf-8"))
    perse = [r.strip() for r in open(opz["--perse"], encoding="utf-8")] if opz["--perse"] else []
    ore = scegli(sc["ore"], st["archivio"], perse, float(opz["--margine_min"]))
    cfg = cfg_per(ore, opz["--pc"], opz["--nome"], opz["--parti"], opz["--modo"], opz["--per_minuto"], st.get("ora"))
    pn = sum(o["persa"] for o in ore)
    json.dump(cfg, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(ore)} ore ancora sul registratore ({pn} perse), stima {cfg['stima_mb']} MB dal registratore, "
          f"{cfg['stima_mb_drive']} MB su Drive")
    for o in ore:
        print(f"  {o['nome']:<16} {o['tipo']:<9} {o['inizio']}  margine {o['margine_giorni']:>5} giorni"
              + ("  PERSA" if o["persa"] else ""))


if __name__ == "__main__":
    main(sys.argv)
