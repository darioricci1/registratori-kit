"""
fps - i pezzi del compito fps1 (registratori-kit): a quanti fotogrammi al secondo registrano DAVVERO le telecamere dei
kit, misurato sul registratore Focus (P2P, senza VPN e senza le password delle telecamere Dahua).
VERSION 0.1.0 (17/11/2026)

Perche': i .ssf sono H.264 grezzo e il programma li tratta a 25 fps; dagli scarichi passati alcune telecamere ne fanno
circa 17,857 (KIT252, 261, 341, 373, 461, 506, 632 su circa 60 misurate): lette a 25 scorrono 1,4 volte piu' veloci.
Qui le funzioni pure (scelta dei kit, scelta dell'ora, lettura del file grezzo H.264/H.265, calcolo, riassunto),
provate a tavolino in prova_fps1.py, e misura_kit(), che usa un Registratore di focus_nvr (vero o finto).

Sola lettura: collegamento, canali, minuti registrati, un tratto di registrazione in riproduzione. Niente impostazioni,
niente PTZ, niente audio, niente comandi alle telecamere.
"""
import datetime
import os
import re
import time

VERSION = "0.1.0"

FPS_PROGRAMMA = 25.0           # quello che Kit_Rifiuti assume per i .ssf
PAROLE_CREDENZIALI = ("password", "sconosciuto", "utente")


# ------------------------------------------------------------------ credenziali (come il ponte e parallelo1)

def leggi_accesso(cartelle):
    """Le righe di focus_accesso.txt (uid;utente;password, «*» per tutti, «*<200» per i kit fino al 199) delle cartelle
    che lo hanno: (per_uid, generiche, vecchie)."""
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


# ------------------------------------------------------------------ i kit

def numero_kit(testo):
    m = re.search(r"(\d{1,4})", str(testo or ""))
    return int(m.group(1)) if m else None


def _etichetta(kit, nome, prese):
    e = f"KIT{kit}" if kit else str(nome or "senza nome")[:40]
    base, k = e, 2
    while e in prese:
        e, k = f"{base}#{k}", k + 1
    prese.add(e)
    return e


def scegli_kit(stato, anche_muti=False, escludi=("998",), solo=None, massimo=None):
    """Dalle righe di op=stato del sito (kit: [{uid, kit, nome, gruppo, stato, risposte_24h, ...}]) TUTTI i registratori,
    un UID una volta sola: prima chi ha piu' risposte nelle ultime 24 ore, poi chi ha l'ultima prova riuscita, poi (solo
    con anche_muti) gli altri. Ritorna (scelti [{uid, numero, etichetta, gruppo}], saltati [{etichetta, motivo}])."""
    righe = (stato or {}).get("kit") or []
    solo = {str(s).upper().replace("KIT", "").lstrip("0") for s in (solo or [])}
    cand, visti = [], set()
    for i, r in enumerate(righe):
        uid = str(r.get("uid") or "").strip()
        kit = str(r.get("kit") or "").strip().lstrip("0")
        if not uid or uid.upper() in visti or kit in escludi:
            continue
        if solo and kit not in solo:
            continue
        visti.add(uid.upper())
        risposte = int(r.get("risposte_24h") or 0)
        ultimo_ok = r.get("stato") == "fatto"
        cand.append((0 if risposte > 0 else (1 if ultimo_ok else 2), -risposte, i, uid, kit, r.get("nome"),
                     r.get("gruppo")))
    cand.sort()
    scelti, saltati, prese = [], [], set()
    for classe, _r, _i, uid, kit, nome, gruppo in cand:
        e = _etichetta(kit, nome, prese)
        if classe == 2 and not anche_muti:
            saltati.append({"etichetta": e, "gruppo": gruppo, "motivo": "nessuna risposta al ponte nelle ultime 24 ore"})
            continue
        scelti.append({"uid": uid, "numero": numero_kit(kit), "etichetta": e, "gruppo": gruppo})
    if massimo:
        for k in scelti[int(massimo):]:
            saltati.append({"etichetta": k["etichetta"], "gruppo": k.get("gruppo"), "motivo": "oltre «massimo_kit»"})
        scelti = scelti[:int(massimo)]
    return scelti, saltati


def kit_da_registratori(reg, escludi=("998",), solo=None, massimo=None):
    """registratori.json degli zip di Kit_Rifiuti ({"252": {"uid": ..., ...}}) quando il sito non risponde: tutti,
    in ordine di numero (non si sa chi risponde)."""
    righe = [{"uid": (v or {}).get("uid"), "kit": k, "nome": k, "stato": "fatto"}
             for k, v in sorted((reg or {}).items(), key=lambda x: (numero_kit(x[0]) or 0, x[0]))]
    return scegli_kit({"kit": righe}, True, escludi, solo, massimo)


# ------------------------------------------------------------------ l'ora da scaricare

def minuti_registrati(tratti):
    """[(inizio, fine_esclusa, tipo)] -> {minuto: tipo}."""
    out = {}
    for a, b, t in tratti or []:
        for m in range(max(0, int(a)), min(1440, int(b))):
            out[m] = t
    return out


def scegli_inizio(tratti_oggi, tratti_ieri, adesso, ore_giorno=(9, 17), margine_min=10, secondo=20):
    """Il momento da scaricare per un canale: un minuto registrato con registrato anche il minuto prima e quello dopo
    (lontano dai buchi), di giorno se si puo', il piu' recente; di oggi solo se e' finito da almeno margine_min minuti
    (l'ultimo minuto puo' essere ancora in scrittura). Ordine: di giorno oggi, di giorno ieri, a qualunque ora oggi o
    ieri, poi un minuto qualunque registrato anche senza i vicini. Ritorna (datetime, perche) o (None, perche)."""
    oggi = datetime.datetime.combine(adesso.date(), datetime.time())
    ieri = oggi - datetime.timedelta(days=1)
    limite = adesso.hour * 60 + adesso.minute - int(margine_min)
    giorni = [(oggi, "oggi", {m: t for m, t in minuti_registrati(tratti_oggi).items() if m < limite}),
              (ieri, "ieri", minuti_registrati(tratti_ieri))]
    if not any(g[2] for g in giorni):
        return None, "niente registrato oggi e ieri"
    a, b = int(ore_giorno[0]) * 60, int(ore_giorno[1]) * 60

    def pieno(regs, m):
        return (m - 1) in regs and (m + 1) in regs

    passi = [("di giorno", lambda regs, m: a <= m < b and pieno(regs, m), [giorni[0], giorni[1]]),
             ("non di giorno", pieno, [giorni[0], giorni[1]]),
             ("vicino a un buco", lambda regs, m: True, [giorni[0], giorni[1]])]
    for nome, va, quali in passi:
        for base, quale, regs in quali:
            for m in sorted(regs, reverse=True):
                if va(regs, m):
                    t = regs[m]
                    return (base + datetime.timedelta(minutes=m, seconds=int(secondo)),
                            f"{nome}, {quale} {m // 60:02d}:{m % 60:02d} ({TIPI.get(t, t)})")
    return None, "niente registrato oggi e ieri"


TIPI = {0: "", 1: "continua", 2: "movimento", 3: "sensore", 4: "emergenza", 5: "ora legale"}


# ------------------------------------------------------------------ il file grezzo H.264 / H.265

def unita_nal(dati):
    """Le unita' NAL di un flusso Annex B (codici d'inizio 00 00 01 e 00 00 00 01), senza il codice d'inizio."""
    pos, n, inizi = 0, len(dati), []
    while True:
        i = dati.find(b"\x00\x00\x01", pos)
        if i < 0:
            break
        inizi.append(i + 3)
        pos = i + 3
    out = []
    for j, s in enumerate(inizi):
        e = inizi[j + 1] - 3 if j + 1 < len(inizi) else n
        if j + 1 < len(inizi) and e > s and dati[e - 1] == 0:   # lo 00 in piu' del codice a 4 byte
            e -= 1
        if e > s:
            out.append(dati[s:e])
    return out


def conta_fotogrammi(nal, codec="H.264"):
    """Quante immagini ci sono nel flusso: le fette che cominciano un'immagine (H.264: tipi 1 e 5 con first_mb_in_slice
    = 0, cioe' il primo bit dopo l'intestazione a 1; H.265: tipi 0-31 con first_slice_segment_in_pic_flag a 1).
    Ritorna anche quanti fotogrammi chiave."""
    immagini, chiave = 0, 0
    for u in nal:
        if not u:
            continue
        if codec == "H.265":
            if len(u) < 3:
                continue
            t = (u[0] >> 1) & 0x3F
            if t < 32 and (u[2] & 0x80):
                immagini += 1
                if 16 <= t <= 21:
                    chiave += 1
        else:
            if len(u) < 2:
                continue
            t = u[0] & 0x1F
            if t in (1, 5) and (u[1] & 0x80):
                immagini += 1
                if t == 5:
                    chiave += 1
    return immagini, chiave


class Bit:
    """Lettore di bit per gli Exp-Golomb dell'SPS (dopo aver tolto i byte 03 di emulazione)."""

    def __init__(self, dati):
        self.d, self.p = dati, 0

    def u(self, n):
        v = 0
        for _ in range(n):
            if self.p >= len(self.d) * 8:
                raise ValueError("SPS finito prima del previsto")
            v = (v << 1) | ((self.d[self.p >> 3] >> (7 - (self.p & 7))) & 1)
            self.p += 1
        return v

    def ue(self):
        z = 0
        while self.u(1) == 0:
            z += 1
            if z > 31:
                raise ValueError("Exp-Golomb non valido")
        return (1 << z) - 1 + self.u(z)

    def se(self):
        k = self.ue()
        return (k + 1) // 2 if k % 2 else -(k // 2)


def senza_emulazione(u):
    return re.sub(b"\x00\x00\x03", b"\x00\x00", bytes(u))


def leggi_sps_h264(u):
    """Un'unita' NAL SPS H.264 (tipo 7) -> {larghezza, altezza, profilo, livello, fps_sps, fisso} (fps_sps None se il
    flusso non dichiara il tempo). Il «fps dichiarato» e' time_scale / (2 * num_units_in_tick)."""
    b = Bit(senza_emulazione(u[1:]))
    profilo = b.u(8)
    b.u(8)
    livello = b.u(8)
    b.ue()
    croma = 1
    if profilo in (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135):
        croma = b.ue()
        if croma == 3:
            b.u(1)
        b.ue()
        b.ue()
        b.u(1)
        if b.u(1):
            for i in range(8 if croma != 3 else 12):
                if b.u(1):
                    ultimo, prossimo = 8, 8
                    for _ in range(16 if i < 6 else 64):
                        if prossimo:
                            prossimo = (ultimo + b.se() + 256) % 256
                        ultimo = prossimo or ultimo
    b.ue()                                  # log2_max_frame_num_minus4
    poc = b.ue()
    if poc == 0:
        b.ue()
    elif poc == 1:
        b.u(1)
        b.se()
        b.se()
        for _ in range(b.ue()):
            b.se()
    b.ue()                                  # max_num_ref_frames
    b.u(1)
    larg_mb = b.ue() + 1
    alt_mb = b.ue() + 1
    solo_frame = b.u(1)
    if not solo_frame:
        b.u(1)
    b.u(1)
    taglio = [0, 0, 0, 0]
    if b.u(1):
        taglio = [b.ue(), b.ue(), b.ue(), b.ue()]
    sx = 1 if croma in (0, 3) else 2
    sy = (1 if croma in (0, 3) else (2 if croma == 1 else 1)) * (2 - solo_frame)
    out = {"profilo": profilo, "livello": livello,
           "larghezza": larg_mb * 16 - sx * (taglio[0] + taglio[1]),
           "altezza": (2 - solo_frame) * alt_mb * 16 - sy * (taglio[2] + taglio[3]),
           "fps_sps": None, "fisso": None}
    if b.u(1):                              # vui_parameters_present_flag
        if b.u(1):
            if b.u(8) == 255:
                b.u(16)
                b.u(16)
        if b.u(1):
            b.u(1)
        if b.u(1):
            b.u(3)
            b.u(1)
            if b.u(1):
                b.u(24)
        if b.u(1):
            b.ue()
            b.ue()
        if b.u(1):
            tick, scala = b.u(32), b.u(32)
            out["fisso"] = bool(b.u(1))
            if tick:
                out["fps_sps"] = round(scala / (2.0 * tick), 3)
    return out


def leggi_grezzo(percorso, codec="H.264"):
    """Il file grezzo dello scarico -> {byte, nal, fotogrammi_grezzo, chiave, sps: {...}} senza tenere il video."""
    with open(percorso, "rb") as fh:
        dati = fh.read()
    nal = unita_nal(dati)
    immagini, chiave = conta_fotogrammi(nal, codec)
    out = {"byte": len(dati), "nal": len(nal), "fotogrammi_grezzo": immagini, "chiave": chiave}
    if codec != "H.265":
        for u in nal:
            if u and (u[0] & 0x1F) == 7:
                try:
                    out["sps"] = leggi_sps_h264(u)
                except (ValueError, IndexError) as ex:
                    out["sps"] = {"errore": str(ex)}
                break
    return out


# ------------------------------------------------------------------ il calcolo

def _dt(t):
    if isinstance(t, datetime.datetime):
        return t
    try:
        return datetime.datetime.fromisoformat(str(t))
    except (TypeError, ValueError):
        return None


def misura_canale(res, grezzo, inizio, secondi):
    """Lo scarico di focus_nvr.Registratore.scarica (res) e la lettura del file (grezzo) -> i numeri del canale:
      fps_tempi      dai tempi dei fotogrammi dati dal registratore (mediana degli intervalli: fps_da_tempi);
      fps_conteggio  (fotogrammi - 1) / (ultimo - primo), sempre dai tempi;
      fps_grezzo     immagini contate nel file grezzo / durata dichiarata (dal primo fotogramma alla fine chiesta, se
                     lo scarico e' arrivato in fondo; altrimenti fino all'ultimo fotogramma);
      fps            la stima che vale (tempi, poi conteggio, poi grezzo) e accelerazione_se_letto_a_25 = 25 / fps."""
    res, grezzo = res or {}, grezzo or {}
    out = {"inizio": inizio.strftime("%Y-%m-%d %H:%M:%S") if isinstance(inizio, datetime.datetime) else inizio,
           "secondi_chiesti": secondi, "codec": res.get("codec"), "risoluzione": res.get("misura"),
           "fotogrammi": res.get("fotogrammi") or 0, "mb": res.get("mb"), "attesa_s": res.get("attesa_s"),
           "velocita": res.get("velocita"), "fps_tempi": res.get("fps")}
    primo, ultimo = _dt(res.get("primo")), _dt(res.get("ultimo"))
    n = out["fotogrammi"]
    if primo and ultimo and ultimo > primo and n > 1:
        out["durata_tempi_s"] = round((ultimo - primo).total_seconds(), 3)
        out["fps_conteggio"] = round((n - 1) / out["durata_tempi_s"], 3)
    if grezzo:
        out["fotogrammi_grezzo"] = grezzo.get("fotogrammi_grezzo")
        out["chiave"] = grezzo.get("chiave")
        sps = grezzo.get("sps") or {}
        if sps.get("larghezza"):
            out["risoluzione_sps"] = f"{sps['larghezza']}x{sps['altezza']}"
        out["fps_sps"] = sps.get("fps_sps")
        fine = inizio + datetime.timedelta(seconds=secondi) if isinstance(inizio, datetime.datetime) else None
        if primo and fine and not res.get("errore") and fine > primo:
            durata = (fine - primo).total_seconds()
            out["durata_dichiarata_s"] = round(durata, 3)
        elif out.get("durata_tempi_s") and out.get("fps_conteggio"):
            durata = out["durata_tempi_s"] + 1 / out["fps_conteggio"]
            out["durata_dichiarata_s"] = round(durata, 3)
        else:
            durata = None
        if durata and out["fotogrammi_grezzo"]:
            out["fps_grezzo"] = round(out["fotogrammi_grezzo"] / durata, 3)
    fps = out.get("fps_tempi") or out.get("fps_conteggio") or out.get("fps_grezzo")
    out["fps"] = fps
    out["accelerazione_se_letto_a_25"] = round(FPS_PROGRAMMA / fps, 3) if fps else None
    if res.get("errore"):
        out["errore_scarico"] = res["errore"]
    if not n:
        out["esito"] = "nessun fotogramma: " + str(res.get("errore") or "?")
    elif fps is None:
        out["esito"] = "fotogrammi senza tempi utili"
    else:
        stime = [x for x in (out.get("fps_tempi"), out.get("fps_conteggio"), out.get("fps_grezzo")) if x]
        out["discordanti"] = bool(stime) and (max(stime) - min(stime)) > 0.1 * max(stime)
        out["esito"] = "misurato" + (" (le stime non vanno d'accordo)" if out["discordanti"] else "")
    return out


def classe_fps(f):
    """La frequenza «di catalogo» piu' vicina (per il conteggio del riassunto): 25, 20, 17.857 (= 125/7), 15, ..."""
    if not f:
        return None
    noti = [30.0, 25.0, 20.0, 17.857, 15.0, 12.5, 12.0, 10.0, 8.0, 6.0, 5.0, 3.0, 1.0]
    v = min(noti, key=lambda x: abs(x - f))
    return str(v) if abs(v - f) <= 0.04 * v else f"altro ({round(f, 2)})"


def riassunto(kit, soglia=24.0):
    """kit: {etichetta: {esito, collegamento, canali: [...]}} -> il riassunto: quanti kit e telecamere, quante per
    frequenza, e l'elenco «telecamere sotto 24 fps» (dalla piu' lenta), con l'accelerazione se lette a 25."""
    righe, conti, collegati, non = [], {}, 0, []
    for e in sorted(kit, key=lambda x: (numero_kit(x) or 0, x)):
        k = kit[e] or {}
        if k.get("collegato"):
            collegati += 1
        else:
            non.append({"kit": e, "esito": k.get("esito"), "non_risposto": k.get("non_risposto")})
        for c in k.get("canali") or []:
            f = c.get("fps")
            if f is None:
                continue
            cl = classe_fps(f)
            conti[cl] = conti.get(cl, 0) + 1
            righe.append({"kit": e, "canale": c.get("canale"), "titolo": c.get("titolo"), "fps": f,
                          "fps_grezzo": c.get("fps_grezzo"), "fps_sps": c.get("fps_sps"),
                          "risoluzione": c.get("risoluzione"), "codec": c.get("codec"),
                          "accelerazione_se_letto_a_25": c.get("accelerazione_se_letto_a_25"),
                          "discordanti": c.get("discordanti")})
    sotto = sorted((r for r in righe if r["fps"] < soglia), key=lambda r: (r["fps"], numero_kit(r["kit"]) or 0))
    per_kit = [{"kit": e, "ore_risposta": (kit[e] or {}).get("ore_risposta") or [],
                "risposte": (kit[e] or {}).get("risposte_n") or 0, "non_risposto": (kit[e] or {}).get("non_risposto") or 0,
                "canali": (kit[e] or {}).get("canali_n"),
                "misurati": sum(1 for c in (kit[e] or {}).get("canali") or [] if c.get("fps")),
                "misurato": bool((kit[e] or {}).get("misurato"))}
               for e in sorted(kit, key=lambda x: (numero_kit(x) or 0, x))]
    return {"soglia_fps": soglia, "kit": len(kit), "kit_collegati": collegati, "telecamere_misurate": len(righe),
            "telecamere_sotto_soglia": len(sotto), "kit_con_telecamere_sotto": sorted({r["kit"] for r in sotto},
                                                                                  key=lambda x: numero_kit(x) or 0),
            "per_frequenza": dict(sorted(conti.items(), key=lambda x: -x[1])),
            "sps_dichiarano": _sps_conti(righe), "telecamere_sotto_24_fps": sotto, "kit_non_collegati": non,
            "kit_misurati": sum(1 for x in per_kit if x["misurato"]), "per_kit": per_kit}


def _sps_conti(righe):
    c = {}
    for r in righe:
        k = str(r.get("fps_sps")) if r.get("fps_sps") else "niente"
        c[k] = c.get(k, 0) + 1
    return c


# ------------------------------------------------------------------ un kit (Registratore vero o finto)

def collega(reg, uid, cred, attesa=40):
    """Il primo collegamento che entra, provando le credenziali in ordine (come collega_con del ponte)."""
    testo, tentativi = "sul PC manca focus_accesso.txt con utente e password dei registratori", 0
    for cr in cred:
        tentativi += 1
        ok, testo = reg.collega(uid, cr[0], cr[1], 9010, True, attesa=attesa)
        if ok or not any(w in testo for w in PAROLE_CREDENZIALI):
            return ok, testo, tentativi, cr
    return False, testo, tentativi, None


def misura_canali(reg, canali, cred_usata, uid, cfg, cartella, r, scrivi=None, adesso=None, scadenza=None,
                  salta=(), niente_ffmpeg="fps1-senza-ffmpeg"):
    """Sul registratore gia' collegato: per ogni canale (numero, handle, titolo) che non e' in «salta», minuti di oggi e
    ieri, scelta dell'ora, scarico di cfg['secondi'] secondi, lettura del grezzo, misura; il video si cancella subito.
    r e' il risultato del kit: i canali si aggiungono in r['canali'] e scrivi(r) si chiama dopo ognuno (cosi' un crash
    lascia quello che c'era). Niente UID e niente credenziali nel risultato."""
    adesso = adesso or datetime.datetime.now()
    oggi = datetime.datetime.combine(adesso.date(), datetime.time())
    scrivi = scrivi or (lambda _r: None)
    r.setdefault("canali", [])
    t_coll = time.time()
    relay = "relay" in str(r.get("collegamento") or "")
    for num, h, tit in canali:
        if num in salta:
            continue
        if scadenza and time.time() > scadenza:
            r["tetto_kit"] = True
            r["canali"].append({"canale": num, "titolo": tit, "esito": "non fatto: tetto di tempo del kit"})
            continue
        if relay and time.time() - t_coll > float(cfg.get("relay_ricollega_s", 240)) and cred_usata:
            # il relay TUTK si chiude dopo 5 minuti: prima di arrivarci, un collegamento nuovo
            try:
                reg.f["Disconnect"](reg.this, reg.server)
            except Exception:   # noqa: BLE001
                pass
            reg.server = 0
            ok2, testo2 = reg.collega(uid, cred_usata[0], cred_usata[1], 9010, True, attesa=float(cfg.get("attesa_fps", 40)))
            r["ricollegato"] = r.get("ricollegato", 0) + 1
            t_coll = time.time()
            if not ok2:
                r["canali"].append({"canale": num, "titolo": tit, "esito": "ricollegamento fallito: " + testo2})
                break
            relay = "relay" in testo2
            h = {n: hh for n, hh, _t in reg.canali()}.get(num, h)
        c = {"canale": num, "titolo": tit}
        t1 = time.time()
        try:
            tr_oggi = reg.minuti_registrati(h, oggi)
            tr_ieri = reg.minuti_registrati(h, oggi - datetime.timedelta(days=1))
            c["minuti_oggi"] = sum(b - a for a, b, _t in (tr_oggi or []))
            c["minuti_ieri"] = sum(b - a for a, b, _t in (tr_ieri or []))
            inizio, perche = scegli_inizio(tr_oggi, tr_ieri, adesso, tuple(cfg.get("ore_giorno", (9, 17))),
                                           int(cfg.get("margine_min", 10)))
            c["scelta"] = perche
            if inizio is None:
                c["esito"] = perche
            else:
                sec = int(cfg.get("secondi", 10))
                r["canale_in_corso"] = num   # se il processo cade o si pianta qui, il compito lo conta su questo canale
                scrivi(r)
                res = reg.scarica(num, h, inizio, sec, cartella, attesa_vuoto=float(cfg.get("attesa_vuoto", 20)),
                                  ffmpeg=niente_ffmpeg)
                f = res.get("file")
                g = None
                if f and os.path.exists(f):
                    try:
                        g = leggi_grezzo(f, res.get("codec") or "H.264")
                    finally:
                        cancella(f)
                c.update(misura_canale(res, g, inizio, sec))
        except Exception as ex:   # noqa: BLE001 - un canale non ferma gli altri
            c["esito"] = f"errore: {type(ex).__name__}: {str(ex)[:200]}"
        r.pop("canale_in_corso", None)
        c["secondi"] = round(time.time() - t1, 1)
        c["il"] = adesso.strftime("%Y-%m-%d %H:%M")
        r["canali"].append(c)
        scrivi(r)
    return r


def cancella(f):
    """Il video scaricato via (anche l'.mp4 se un ffmpeg l'avesse fatto): si tengono solo i numeri."""
    for p in (f, os.path.splitext(f)[0] + ".mp4", os.path.splitext(f)[0] + ".grezzo"):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


# ------------------------------------------------------------------ il giro di 24 ore (decisioni pure)

def numero_da_richiesta(testo):
    """Il numero del kit dalla richiesta del sito («ALEA-Civitella · 136 - Via ...» -> 136), come numero_kit del ponte."""
    m = re.search(r"(?:^|·)\s*(\d{1,4})\b", str(testo or ""))
    return int(m.group(1)) if m else None


def etichetta_per_uid(uid, testo, mappa):
    """L'etichetta di un registratore (KIT<numero>, o il nome), sempre la stessa per lo stesso UID; due UID con lo
    stesso numero prendono «#2». mappa {UID: etichetta} si aggiorna (sta in lavori/, non in uscita: ha gli UID)."""
    u = str(uid or "").upper()
    if u in mappa:
        return mappa[u]
    n = numero_da_richiesta(testo)
    e = f"KIT{n}" if n is not None else (str(testo or "senza nome").split("·")[-1].strip()[:40] or "senza nome")
    prese, base, k = set(mappa.values()), e, 2
    while e in prese:
        e, k = f"{base}#{k}", k + 1
    mappa[u] = e
    return e


def canale_chiuso(c, max_tentativi=6):
    """Un canale non si riprova piu' quando ha la misura, o dopo max_tentativi prove senza."""
    return bool(c.get("fps")) or int(c.get("tentativi") or 0) >= int(max_tentativi)


def canali_da_saltare(k, max_tentativi=6):
    return sorted(int(c["canale"]) for c in (k or {}).get("canali") or [] if canale_chiuso(c, max_tentativi))


def kit_misurato(k, max_tentativi=6):
    """Il kit non ha piu' bisogno dello scarico: ha risposto almeno una volta e ogni suo canale e' chiuso."""
    k = k or {}
    can = k.get("canali") or []
    n = k.get("canali_n")
    return bool(k.get("risposte")) and n is not None and len(can) >= int(n) and all(canale_chiuso(c, max_tentativi)
                                                                                     for c in can)


def serve_foto(k, oggi):
    """Foto delle telecamere (come il ponte) una volta al giorno per kit: oggi non ancora fatte."""
    return str((k or {}).get("foto_il") or "") != oggi.strftime("%Y-%m-%d")


def unisci(k, lavoro, quando, max_tentativi=6):
    """Il risultato di un processo (lavoro) dentro lo stato del kit (k): l'ora in cui ha risposto o un «non risposto»
    in piu', e per ogni canale la misura migliore (una misura non si perde per una prova dopo andata male) e quante
    prove. quando: datetime della prova. Ritorna k."""
    k = dict(k or {})
    lavoro = lavoro or {}
    k["provato"] = int(k.get("provato") or 0) + 1
    k.setdefault("risposte", [])
    k.setdefault("non_risposto", 0)
    if lavoro.get("collegato"):
        k["risposte"] = (k["risposte"] + [quando.strftime("%Y-%m-%d %H:%M")])[-48:]
        k["risposte_n"] = int(k.get("risposte_n") or 0) + 1
        k["ore_risposta"] = sorted({int(x[11:13]) for x in k["risposte"]})
        for x in ("modello", "telecamere", "canali_n", "modo"):
            if lavoro.get(x) is not None:
                k[x] = lavoro[x]
        if lavoro.get("foto_fatte"):
            k["foto_il"] = quando.strftime("%Y-%m-%d")
    else:
        k["non_risposto"] += 1
        k["ultimo_errore"] = lavoro.get("esito") or lavoro.get("collegamento")
    per = {int(c["canale"]): dict(c) for c in k.get("canali") or []}
    canali_lavoro = list(lavoro.get("canali") or [])
    if lavoro.get("caduto") and lavoro.get("canale_in_corso") is not None:
        canali_lavoro.append({"canale": lavoro["canale_in_corso"], "esito": lavoro["caduto"] + " durante lo scarico"})
    for c in canali_lavoro:
        n = int(c["canale"])
        vecchio = per.get(n, {})
        if vecchio.get("fps"):
            vecchio["prove_dopo"] = int(vecchio.get("prove_dopo") or 0) + 1
            per[n] = vecchio
            continue
        nuovo = dict(c)
        nuovo["tentativi"] = int(vecchio.get("tentativi") or 0) + 1
        per[n] = nuovo
    k["canali"] = [per[n] for n in sorted(per)]
    k["misurato"] = kit_misurato(k, max_tentativi)
    k["collegato"] = bool(k["risposte"])
    k["esito"] = (f"{sum(1 for c in k['canali'] if c.get('fps'))} canali misurati su {k.get('canali_n')}"
                  if k["risposte"] else f"mai risposto ({k['non_risposto']} prove)")
    return k


def da_fare(kit, stato, max_tentativi=6):
    """Per il giro fatto da solo (senza il sito): i kit [{uid, numero, etichetta}] non ancora misurati."""
    return [x for x in kit if not kit_misurato(stato.get(x["etichetta"]), max_tentativi)]


def prossimo_giro(ultimo_inizio, adesso_s, ogni_s=3600):
    """Quando parte il prossimo giro fatto da solo: un'ora dopo l'inizio del precedente (subito se e' il primo)."""
    return adesso_s if not ultimo_inizio else ultimo_inizio + ogni_s


def versione_per_il_sito(versione_ponte):
    """La versione che il PC dice al sito (op=prendi/esito). Il sito la legge con delle regole: « 0.0.»-« 0.3.» non
    leggono l'archivio, « 0.0.»-« 0.6.» non mandano le ore, «0.1.» lascia il giro a un ponte piu' nuovo. Quindi il
    compito si presenta come il ponte da cui ha preso il codice, con «+fps» (20 caratteri al massimo: il sito taglia)."""
    return f"{versione_ponte}+fps"[:20]
