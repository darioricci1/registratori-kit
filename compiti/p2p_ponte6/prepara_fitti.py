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
version: 0.1.0 (20/11/2026)
"""
import datetime
import json
import sys

VERSIONE = "0.1.0"
MB_ORA_MINUTI = 3.6      # 72 miniature (ora.json delle scorte: mb_minuti 2,1-5,5, media 3,6)
MB_MINIATURA = 0.05


def dt(s):
    return datetime.datetime.strptime(str(s)[:16].replace("T", " "), "%Y-%m-%d %H:%M")


def margini(ore, archivio):
    """[(ora, margine in giorni o None)]: quanto prima dell'inizio dell'ora comincia la registrazione rimasta sul disco
    di quel canale («primo» dell'archivio). Funzione pura."""
    ar = {(a.get("uid"), int(a.get("canale", -1))): a for a in archivio}
    out = []
    for o in ore:
        a = ar.get((o.get("uid"), int(o.get("canale", -1))))
        m = None
        if a and a.get("primo"):
            m = round((dt(o["inizio"]) - dt(a["primo"])).total_seconds() / 86400, 2)
        out.append((o, m))
    return out


def scegli(ore, archivio, perse=(), margine_min=0.05):
    """Le ore ancora sul registratore, in ordine di margine (le perse prima a parità), ognuna pronta per scorta.py:
    niente video, niente catena, «margine_giorni» scritto. Funzione pura."""
    perse = set(perse)
    tenute = []
    for o, m in margini(ore, archivio):
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


def main(a):
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
    sigla = opz["--nome"].replace("p2p_ponte", "")
    cfg = {"pc": opz["--pc"], "preparato_il": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "prepara": f"prepara_fitti.py {VERSIONE}", "stato_letto": st.get("ora"), "ordine_dato": True,
           "fitti": {"modo": opz["--modo"], "per_minuto": int(opz["--per_minuto"])},
           "finestra": {"dalle": "00:00", "alle": "23:59"},
           "limiti": {"ore_di_lavoro": 10.0, "minuti_per_ora": 18.0, "mb_in_tutto": 5000.0, "mb_parte_drive": 170.0},
           "gb_liberi_min": 5, "posti_drive": [f"fitti{sigla}_{k}.zip" for k in range(1, int(opz["--parti"]) + 1)],
           "come": "le ore delle scorte ancora sul registratore, dalla più vicina a uscire; per ognuna le 72 miniature "
                   "dei minuti e le miniature in più (fitti.py) in <ora>/fitti/",
           "ore": ore}
    pn = sum(o["persa"] for o in ore)
    n = int(opz["--per_minuto"])
    cfg["stima_mb"] = round(stima_mb(len(ore) - pn, opz["--modo"], n) + stima_mb(pn, "tutti", n), 1)
    cfg["stima_mb_drive"] = round(stima_mb(len(ore) - pn, opz["--modo"], n, minuti=False)
                                  + stima_mb(pn, "tutti", n, minuti=False), 1)
    cfg["ore"] = ore
    json.dump(cfg, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(ore)} ore ancora sul registratore ({pn} perse), stima {cfg['stima_mb']} MB dal registratore, "
          f"{cfg['stima_mb_drive']} MB su Drive")
    for o in ore:
        print(f"  {o['nome']:<16} {o['tipo']:<9} {o['inizio']}  margine {o['margine_giorni']:>5} giorni"
              + ("  PERSA" if o["persa"] else ""))


if __name__ == "__main__":
    main(sys.argv)
