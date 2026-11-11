"""Prepara allunga.json: gli eventi le cui clip sono tagliate o sospette, coi dati per chiedere al registratore i minuti
che mancano prima e dopo (Dario, 11/11/2026 sera, in Guarda: «video tagliato troppo presto»; decisione-p2p-2026-11-11.md
di kit-rifiuti-programma: il P2P serve ad arricchire le clip dell'operatrice).

Sola lettura, due siti, con l'account di servizio di Alma:
  - kit-rifiuti.vercel.app  op=video&leggero=1 (a pagine, come leggi_riquadri.py) per scegliere gli eventi, poi op=evento
    per ognuno (kit, giorno, ora della clip dal nome «a mano HHMMSS», telecamere e durate);
  - prova-nvr-remoto.vercel.app  op=stato (UID del registratore di ogni kit, archivio di ogni canale, anagrafica).
Scelta (le stesse parole di analisi/inventario_etichette.py 0.1.2): dati.completo falso, dati.non_intero, una telecamera
sotto 5 s, una nota di Dario con «tagliato / non completo / corto / una sola telecamera / file nero / manca», piu' gli
eventi dati a mano (FISSI: 7b56bc2ce8 e cc577ca6e7, note di Dario in Guarda dell'11/11).
Uso: python3 prepara_allunga.py <chiave.json> [allunga.json]
La chiave non si copia da nessuna parte; nel json niente targhe, password o indirizzi (gli UID si', come in dimezza.json).
version: 0.1.0 (11/11/2026)
"""
import datetime
import json
import re
import sys
import urllib.request

KR = "https://kit-rifiuti.vercel.app/api/fogli"
NVR = "https://prova-nvr-remoto.vercel.app/api/p2p"
DURATA_CORTA = 5.0
PAROLE_TAGLIO = re.compile(r"non (e' |è )?complet|tagliat|corto|una sola telecamera|file nero|manca", re.I)
FISSI = {"7b56bc2ce8": "Dario in Guarda, 11/11: «video tagliato troppo presto»",
         "cc577ca6e7": "Dario in Guarda, 11/11: «sembra che il video non finisca»"}
PRIMA_S, DOPO_S = 60, 120


# ------------------------------------------------------------------ funzioni pure (provate in prova_allunga.py)

def numero_kit(testo):
    """«KIT560 Zona ...», «KIT 452», «EX KIT450 ...», «EXKIT666» -> (560, False), (452, False), (450, True). Un kit spostato
    («EX») porta con se' il registratore: le registrazioni di allora, se ci sono ancora, stanno sul suo disco."""
    m = re.match(r"\s*(EX\s*)?KIT\s*0*(\d{1,4})\b", str(testo or ""), re.I)
    return (int(m.group(2)), bool(m.group(1))) if m else (None, False)


def ora_dal_nome(nome):
    """«a mano 160458», «targa XX000XX 083338», «no targa 163727» -> "16:04:58"; None se il nome non la dice."""
    m = re.search(r"(?:^|\s)(\d{2})(\d{2})(\d{2})$", str(nome or "").strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59 or int(m.group(3)) > 59:
        return None
    return f"{m.group(1)}:{m.group(2)}:{m.group(3)}"


def numero(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


TARGA = re.compile(r"\b[A-Z]{2}\s?\d{3}\s?[A-Z-]{2}\b")


def senza_targhe(t):
    """Le targhe fuori dai testi che vanno nel json (stanno nei nomi delle cartelle delle operatrici)."""
    return TARGA.sub("[targa]", str(t))


def motivi(righe, fissi=FISSI):
    """Perche' un evento (le sue righe di op=video) e' da allungare: lista di testi, vuota se non lo e'."""
    out = []
    ev = righe[0]["evento"]
    if ev in fissi:
        out.append(fissi[ev])
    d = [r.get("dati") or {} for r in righe]
    if any(x.get("completo") in (False, "false") for x in d):
        out.append("una telecamera «non completa»")
    ni = next((str(x.get("non_intero")) for x in d if x.get("non_intero")), "")
    if ni:
        out.append("non intero: " + ni[:120])
    corte = sorted({r["cam"] for r in righe if (numero((r.get("dati") or {}).get("durata")) or 99) < DURATA_CORTA})
    if corte:
        out.append("telecamere sotto 5 s: " + ", ".join(str(c) for c in corte))
    if any(PAROLE_TAGLIO.search(str(r.get("nota") or "")) for r in righe):
        out.append("nota di Dario: " + next(str(r["nota"]) for r in righe if PAROLE_TAGLIO.search(str(r.get("nota") or "")))[:120])
    return [senza_targhe(m) for m in out]


def durate_per_canale(righe):
    """{canale da 0: secondi della clip di quella telecamera}: il piu' corto fra il video del sito e l'originale sul NAS
    (quello che c'e' davvero), dell'ultimo giro di ogni telecamera."""
    out = {}
    for r in righe:
        c = int(r["cam"]) - 1
        if c in out:
            continue
        d = r.get("dati") or {}
        v = [x for x in (numero(d.get("durata")), numero(d.get("durata_nas"))) if x]
        out[c] = round(min(v), 2) if v else None
    return out


def durata_clip(righe):
    """La durata della clip: la piu' lunga fra tutte le telecamere, sito o NAS (la telecamera piu' lunga dice quanto
    durava la clip dell'operatrice; le altre, se sono piu' corte, hanno un buco)."""
    v = [numero((r.get("dati") or {}).get(k)) for r in righe for k in ("durata", "durata_nas")]
    v = [x for x in v if x]
    return round(max(v), 2) if v else None


def registratore_del_kit(kit, righe_stato):
    """(uid, nome, canali secondo UVMS) del registratore del kit dalle righe di op=stato: fra piu' righe, quella che ha
    risposto per ultima. (None, None, None) se il kit non c'e'."""
    c = [k for k in righe_stato if str(k.get("kit") or "").lstrip("0") == str(kit)]
    if not c:
        return None, None, None
    c.sort(key=lambda k: (k.get("stato") == "fatto", str(k.get("finito_il") or "")), reverse=True)
    k = c[0]
    try:
        can = int(k.get("canali_uvms"))
    except (TypeError, ValueError):
        can = None
    return k["uid"], f"{k.get('gruppo')} · {k.get('nome')}", can


def disponibile(archivio, uid, canali, da):
    """Il registratore ha ancora il momento `da` (datetime) su questi canali? Dall'archivio letto dal ponte (primo e
    ultimo di ogni canale). {"stima": "si" / "no" / "non so", "primo": ..., "letto_il": ...}."""
    righe = [a for a in archivio if a.get("uid") == uid and a.get("canale") in canali and a.get("primo")]
    if not righe:
        return {"stima": "non so"}
    primo = max(a["primo"] for a in righe)
    letto = max(str(a.get("letto_il") or "") for a in righe)
    try:
        p = datetime.datetime.strptime(primo[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return {"stima": "non so", "primo": primo}
    # l'archivio e' di qualche giorno fa e il disco gira: un giorno di margine per ogni giorno da allora
    try:
        giorni = max(0, (datetime.datetime.now(datetime.timezone.utc) -
                         datetime.datetime.fromisoformat(letto.replace("Z", "+00:00"))).days)
    except ValueError:
        giorni = 0
    stima = "si" if da >= p + datetime.timedelta(days=giorni + 1) else "no" if da < p else "forse"
    return {"stima": stima, "primo": primo, "letto_il": letto[:16]}


def evento_da_righe(righe, stato, prima_s=PRIMA_S, dopo_s=DOPO_S):
    """Una voce di allunga.json dalle righe di op=evento e dalla risposta di op=stato."""
    d = righe[0].get("dati") or {}
    kit, ex = numero_kit(d.get("kit"))
    ora = ora_dal_nome(d.get("nome"))
    per = durate_per_canale(righe)
    uid, nome_reg, can_uvms = registratore_del_kit(kit, stato.get("kit") or []) if kit else (None, None, None)
    ana = next((a for a in stato.get("anagrafica") or [] if a.get("kit") == kit), {})
    try:
        attese = int(ana.get("telecamere") or 0)
    except (TypeError, ValueError):
        attese = 0
    # i canali: quelli della clip e, se l'anagrafica ne dice di piu' (le note «una sola telecamera»), anche gli altri
    # (i canali di UVMS no: un NVR ne ha 9 e quasi tutti vuoti)
    canali = sorted(set(per) | set(range(attese)))
    x = {"evento": righe[0]["evento"], "kit": kit, "giorno": d.get("giorno"), "ora_inizio_clip": ora,
         "durata_clip": durata_clip(righe), "canali": canali, "prima_s": prima_s, "dopo_s": dopo_s,
         "durate_canali": {str(k): v for k, v in sorted(per.items())}, "uid": uid, "registratore": nome_reg,
         "motivi": motivi(righe), "misura": f"{d.get('W')}x{d.get('H')}"}
    if ex:
        x["kit_spostato"] = "nel nome della cartella «EX KIT»: il kit e' stato spostato, si chiede al suo registratore"
    if ora and d.get("giorno") and uid:
        da = datetime.datetime.strptime(f"{d['giorno']} {ora}", "%Y-%m-%d %H:%M:%S") - datetime.timedelta(seconds=prima_s)
        x["sul_registratore"] = disponibile(stato.get("archivio") or [], uid, canali, da)
    return x


def ordine(ev):
    """Prima quelli che il registratore ha ancora, i piu' vecchi per primi (il disco gira: sono i prossimi a sparire);
    poi quelli che non si sa; poi quelli gia' sovrascritti (costano solo GetRecordRange, per confermarlo), gli eventi di
    Dario in testa."""
    posto = {"si": 0, "forse": 1, "non so": 2}.get((ev.get("sul_registratore") or {}).get("stima"), 3)
    return posto, ev["evento"] not in FISSI, str(ev.get("giorno")), str(ev.get("ora_inizio_clip")), ev["evento"]


def stima_mb(ev, mb_al_secondo_per_mp=(0.10, 0.21)):
    """(minimo, massimo) MB attesi per l'evento: secondi da scaricare per canale per i megapixel, con i due ritmi
    misurati sul KIT581 (2688x1520): 0,43 MB/s per canale nella prova lunga del compito 25, 0,84 nei tratti del 26."""
    try:
        w, h = (int(v) for v in ev["misura"].split("x"))
    except (KeyError, ValueError):
        w, h = 1920, 1080
    mp = w * h / 1e6
    sec = 0.0
    for c in ev["canali"]:
        dur = ev["durate_canali"].get(str(c))
        if dur is None:
            sec += ev["prima_s"] + (ev["durata_clip"] or 0) + ev["dopo_s"]
        else:
            sec += ev["prima_s"] + ev["dopo_s"] + max(0.0, (ev["durata_clip"] or 0) - dur)
    return round(sec * mp * mb_al_secondo_per_mp[0]), round(sec * mp * mb_al_secondo_per_mp[1])


# ------------------------------------------------------------------ la rete (sola lettura)

def biglietto(chiave, destinatario):
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    cr = service_account.IDTokenCredentials.from_service_account_file(chiave, target_audience=destinatario)
    cr.refresh(Request())
    return cr.token


def leggi(url, tok, timeout=180):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=timeout) as r:
        return json.load(r)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    chiave, uscita = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "allunga.json")
    tk = biglietto(chiave, "https://mappakit.alma/kit-rifiuti")
    video = []
    while True:
        p = leggi(f"{KR}?op=video&quanti=1000&leggero=1&pagina=200&da={len(video)}", tk)["video"]
        video += p
        if len(p) < 200:
            break
    per_ev = {}
    for v in video:
        per_ev.setdefault(v["evento"], []).append(v)
    scelti = sorted(e for e, l in per_ev.items() if motivi(l))
    stato = leggi(f"{NVR}?op=stato", biglietto(chiave, "https://mappakit.alma/nvr-remoto"))
    eventi = []
    for e in scelti:
        righe = leggi(f"{KR}?op=evento&evento={e}", tk)["video"] or per_ev[e]
        righe.sort(key=lambda r: str(r.get("arrivato") or ""), reverse=True)
        eventi.append(evento_da_righe(righe, stato))
    eventi.sort(key=ordine)
    cfg = {"pc": "COMPUTERONE",
           "come": ("allunga.py: per ogni evento i secondi prima e dopo la clip (e i buchi delle telecamere piu' corte) "
                    "dal registratore in P2P, canale per canale, in un processo a parte per evento; mp4 con l'ora vera "
                    "di inizio e fine, buchi segnati, canali sfasati mai uniti (Dario, 11/11/2026)"),
           "preparato_il": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "prima_s": PRIMA_S, "dopo_s": DOPO_S,
           "eventi": eventi}
    with open(uscita, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=1)
    lo = sum(stima_mb(x)[0] for x in eventi)
    hi = sum(stima_mb(x)[1] for x in eventi)
    print(f"{len(eventi)} eventi in {uscita}; stima {lo}-{hi} MB se tutti fossero ancora sul registratore")
    for x in eventi:
        print(x["evento"], x["kit"], x["giorno"], x["ora_inizio_clip"], x["durata_clip"], x["canali"],
              (x.get("sul_registratore") or {}).get("stima"), stima_mb(x), "; ".join(x["motivi"])[:90])


if __name__ == "__main__":
    main()
