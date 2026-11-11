"""Trovare un abbandono in un'ora di registrazione scaricando il meno possibile, col dimezzamento (Dario, 11/11/2026:
«per allenarti a trovare i video, trova un video lungo e vedi se li' dentro trovi il video rilevato dalla videoanalisi;
anche con la tecnica del dimezzamento, cosi' risparmiamo banda»).

Il metodo, sulla zona dei cassonetti di quel kit e di quella telecamera (zone_cassonetti.json, telecamera = canale + 1):
1. si scaricano 3 s all'inizio e 3 s alla fine della finestra; la mediana dei loro fotogrammi e' il prima e il dopo;
2. pezzi_zona di kit_rifiuti (stessa luce, deltaE, «se n'e' andato qualcosa», «resta») dice se nella zona e' cambiato
   qualcosa che e' rimasto; si tiene il pezzo col punteggio piu' alto e si scrivono gli altri (luce, auto parcheggiate);
3. dimezzare: 3 s a meta' dell'intervallo; se nei pixel cambiati del pezzo la meta' e' piu' vicina al dopo che al prima
   (presente_pezzo, come la ricerca per meta' della 0.87.0) il pezzo c'e' gia' e l'intervallo e' la prima meta', se no
   la seconda; si ripete finche' l'intervallo e' sotto i 60 s;
4. per gli altri pezzi non si scarica niente: si guarda in quali dei campioni gia' scaricati c'erano.
Poi compito.py scarica intero l'ultimo intervallo (piu' un margine) e lo da' a Kit_Rifiuti.

Tutto qui e' senza rete e senza la libreria Focus: chi scarica e' una funzione data (`leggi`), le funzioni di
kit_rifiuti arrivano come modulo (`kr`). Le prove a tavolino sono in prova_dimezza.py.
version: 0.1.0 (11/11/2026): prima versione, per dimezza.json del compito p2p_ponte6 0.11.0.
"""
import csv
import datetime
import io

import numpy as np

VERSIONE = "0.1.0"
CAMPIONE_S = 3          # secondi scaricati per ogni campione (inizio, fine, meta')
TEMPI_FOTOGRAMMI = (0.4, 1.2, 2.0)   # dove si prendono i fotogrammi dentro il campione (secondi dall'inizio del file)
SOGLIA_S = 60.0         # si dimezza finche' l'intervallo e' sotto i 60 s
MASSIMI = 5             # pezzi tenuti da pezzi_zona: il primo si dimezza, gli altri si scrivono
PASSI_MAX = 12          # 3600 s -> sotto 60 s sono 6 passi: 12 e' il tetto contro un ciclo che non finisce
PRIMA_S = 20.0          # all'ultimo intervallo si aggiungono 20 s prima (chi arriva) e 10 dopo, per Kit_Rifiuti
DOPO_S = 10.0


def mediana(fotogrammi):
    """La mediana dei fotogrammi (BGR uint8, stessa misura), o None se non ce ne sono."""
    f = [x for x in (fotogrammi or []) if x is not None]
    if not f:
        return None
    if len(f) == 1:
        return f[0]
    return np.median(np.stack(f), axis=0).astype(np.uint8)


class Campioni:
    """I campioni scaricati, una volta sola per momento. leggi(t) -> (fotogrammi o None, info) con info
    {"mb", "secondi", "secondi_video", "errore"}; t sono i secondi dall'inizio della finestra. Conta richieste, MB,
    secondi di attesa e secondi di video."""

    def __init__(self, leggi):
        self.leggi = leggi
        self.visti = {}
        self.registro = []
        self.conti = {"richieste": 0, "mb": 0.0, "secondi": 0.0, "secondi_video": 0.0}

    def __call__(self, t):
        t = round(float(t), 1)
        if t in self.visti:
            return self.visti[t]
        fot, info = self.leggi(t)
        info = dict(info or {})
        self.conti["richieste"] += 1
        for k in ("mb", "secondi", "secondi_video"):
            self.conti[k] = round(self.conti[k] + float(info.get(k) or 0), 2)
        self.registro.append({"t": t, "fotogrammi": len(fot or []), **{k: info.get(k) for k in ("mb", "secondi", "errore")}})
        self.visti[t] = fot or None
        return self.visti[t]


def cambi(kr, prima, dopo, riquadri, escludi=(), massimi=MASSIMI):
    """Il confronto della zona fra i fotogrammi dell'inizio e della fine: (candidati di pezzi_zona in ordine di
    punteggio, pezzi trovati, A, B, maschera). candidati vuoto = nella zona non e' cambiato niente che sia rimasto."""
    A, B = mediana(prima), mediana(dopo)
    H, W = A.shape[:2]
    zm = kr.maschera_zone(riquadri, escludi, H, W)
    cand, n = kr.pezzi_zona(A, B, [f for f in dopo if f is not None], zm, massimi=massimi)
    return sorted(cand, key=lambda c: -c["punteggio"]), n, A, B, zm


def dimezza(campione, lo, hi, presente, soglia=SOGLIA_S, passi_max=PASSI_MAX):
    """lo: un momento in cui il pezzo non c'e', hi: uno in cui c'e'. Si scarica il campione a meta' e, se presente(F)
    dice di si', hi = meta', se no lo = meta', finche' hi - lo < soglia. Se un campione non arriva si prova una volta
    6 s piu' in la'; se non arriva neanche quello ci si ferma. Ritorna (lo, hi, passi [[t, c'e', dA, dB]], fermato)."""
    passi = []
    while hi - lo >= soglia and len(passi) < passi_max:
        m = (lo + hi) / 2.0
        F = campione(m)
        if not F:
            m2 = m + 2 * CAMPIONE_S
            F = campione(m2) if lo < m2 < hi else None
            if not F:
                passi.append([round(m, 1), None, None, None])
                return lo, hi, passi, "campione non scaricato"
            m = m2
        si, dA, dB = presente(F)
        passi.append([round(m, 1), bool(si), dA, dB])
        if si:
            hi = m
        else:
            lo = m
    return lo, hi, passi, None


def forchetta(visti, presente):
    """Per un pezzo, dai campioni gia' scaricati ({t: fotogrammi}): l'ultimo momento senza il pezzo prima del primo
    momento col pezzo. Ritorna {"da", "a", "stati": [[t, c'e']]}; da/a None se non si puo' dire."""
    stati = []
    for t in sorted(visti):
        if visti[t]:
            stati.append([t, bool(presente(visti[t])[0])])
    da = a = None
    for i, (t, si) in enumerate(stati):
        if si:
            a = t
            da = stati[i - 1][0] if i else None
            break
    return {"da": da, "a": a, "stati": stati}


def scheda_pezzo(c):
    return {k: c.get(k) for k in ("box", "area", "dE", "punteggio", "quota", "via", "diversi", "n_dopo")}


def cerca(kr, campione, durata, riquadri, escludi=(), soglia=SOGLIA_S, massimi=MASSIMI, dimezza_altri=0):
    """Tutta la ricerca su una finestra di `durata` secondi. campione(t) -> fotogrammi (Campioni). Ritorna
    {"esito": "cambio" | "nessun cambio" | "non scaricato", "lo", "hi", "momento", "scelto", "passi", "altri", ...}.
    I primi `dimezza_altri` degli altri pezzi si dimezzano anche loro, partendo dalla forchetta dei campioni gia'
    scaricati (nella misura della ricerca per meta' il sacco del KIT581 era il secondo pezzo, dopo un'ombra)."""
    fine_t = max(0.0, float(durata) - CAMPIONE_S)
    prima, dopo = campione(0.0), campione(fine_t)
    if not prima or not dopo:
        return {"esito": "non scaricato", "nota": "manca " + ("l'inizio" if not prima else "la fine") + " della finestra"}
    cand, n, A, B, zm = cambi(kr, prima, dopo, riquadri, escludi, massimi)
    out = {"pezzi_trovati": n, "quota_zona": round(float(zm.mean()), 3), "misura": [int(A.shape[1]), int(A.shape[0])]}
    if not cand:
        out.update(esito="nessun cambio", nota="fra l'inizio e la fine nella zona non e' cambiato niente che sia rimasto: "
                                               "niente da dimezzare")
        return out
    presenti = [(c, (lambda pp: (lambda F: kr.presente_pezzo(mediana(F), pp)))(kr.pixel_pezzo(A, B, zm, c["box"])))
                for c in cand]
    scelto, pres = presenti[0]
    lo, hi, passi, fermato = dimezza(campione, 0.0, fine_t, pres, soglia)
    out.update(esito="cambio", scelto=scheda_pezzo(scelto), lo=round(lo, 1), hi=round(hi, 1),
               momento=round((lo + hi + CAMPIONE_S) / 2.0, 1), passi=passi, fermato=fermato)
    out["altri"] = []
    for c, p in presenti[1:]:
        x = scheda_pezzo(c)
        x["campioni"] = fk = forchetta(campione.visti, p)
        if len(out["altri"]) < dimezza_altri and fk["a"] is not None:
            a_lo, a_hi, a_passi, a_ferm = dimezza(campione, fk["da"] if fk["da"] is not None else 0.0, fk["a"], p, soglia)
            x.update(lo=round(a_lo, 1), hi=round(a_hi, 1), momento=round((a_lo + a_hi + CAMPIONE_S) / 2.0, 1),
                     passi=a_passi, fermato=a_ferm)
        out["altri"].append(x)
    return out


def finestra_finale(lo, hi, durata, prima_s=PRIMA_S, dopo_s=DOPO_S, campione_s=CAMPIONE_S):
    """L'ultimo intervallo da scaricare intero (secondi dall'inizio della finestra): da lo - prima_s alla fine del
    campione hi piu' dopo_s, dentro la finestra. Ritorna (da, secondi)."""
    da = max(0.0, float(lo) - prima_s)
    a = min(float(durata), float(hi) + campione_s + dopo_s)
    return round(da, 1), max(1, int(round(a - da)))


def confronta(atteso_s, lo, hi, campione_s=CAMPIONE_S):
    """Il momento atteso (secondi dall'inizio della finestra) contro l'intervallo trovato [lo, hi + campione]."""
    if atteso_s is None or lo is None or hi is None:
        return None
    a, b = float(lo), float(hi) + campione_s
    centro = (a + b) / 2.0
    return {"atteso_s": round(float(atteso_s), 1), "dentro": a <= atteso_s <= b, "dal_centro_s": round(atteso_s - centro, 1),
            "fuori_di_s": round(max(0.0, a - atteso_s, atteso_s - b), 1)}


def stima_ora(mb, secondi_video, durata):
    """Quanti MB sarebbe stata la finestra intera, coi MB al secondo dei campioni. None senza misura."""
    if not secondi_video or secondi_video <= 0 or mb is None:
        return None
    return round(float(mb) / float(secondi_video) * float(durata), 1)


def secondi_da(inizio, quando):
    """I secondi di `quando` ("AAAA-MM-GG HH:MM:SS") dall'inizio della finestra (datetime), o None."""
    if not quando:
        return None
    return (datetime.datetime.strptime(quando, "%Y-%m-%d %H:%M:%S") - inizio).total_seconds()


def coperto(intervallo, da, a):
    """Il registratore ha il tratto [da, a)? intervallo = (prima, ultima registrazione) o None (non detto: si prova).
    Ritorna (si/no, perche')."""
    if not intervallo or not intervallo[0] or not intervallo[1]:
        return True, "intervallo non detto dal registratore: si prova"
    p, u = intervallo
    if da < p:
        return False, f"il registratore registra dal {p:%d/%m/%Y %H:%M}: il tratto chiesto non c'e' piu'"
    if a > u:
        return False, f"l'ultima registrazione e' del {u:%d/%m/%Y %H:%M}"
    return True, "c'e'"


def abbandoni_csv(testo, inizio_clip):
    """Dagli eventi.csv di Kit_Rifiuti (separatore «;», «da» in H:MM:SS dall'inizio della clip): gli abbandoni con
    l'ora vera. [{"ora", "da_s", "telecamere", "targa", "punteggio", "come"}]."""
    out = []
    for r in csv.DictReader(io.StringIO(testo or ""), delimiter=";"):
        if (r.get("tipo") or "") != "abbandono":
            continue
        try:
            h, m, s = (float(x) for x in str(r.get("da") or "0:0:0").split(":"))
            da = h * 3600 + m * 60 + s
        except ValueError:
            continue
        out.append({"ora": (inizio_clip + datetime.timedelta(seconds=da)).strftime("%H:%M:%S"), "da_s": round(da, 1),
                    "telecamere": r.get("telecamere"), "targa": r.get("targa") or "", "punteggio": r.get("punteggio"),
                    "come": (r.get("come") or "")[:200]})
    return out


def piu_vicino(abbandoni, giorno, atteso):
    """Dei abbandoni di abbandoni_csv, quanti secondi dista dall'ora attesa ("AAAA-MM-GG HH:MM:SS") il piu' vicino, e
    la sua targa. giorno: la data del tratto. None se non ce ne sono o non c'e' l'ora attesa."""
    if not abbandoni or not atteso:
        return None
    a = datetime.datetime.strptime(atteso, "%Y-%m-%d %H:%M:%S")
    d = [(abs((datetime.datetime.combine(giorno, datetime.datetime.strptime(x["ora"], "%H:%M:%S").time()) - a).total_seconds()), x)
         for x in abbandoni]
    s, x = min(d, key=lambda v: v[0])
    return {"secondi": round(s, 1), "ora": x["ora"], "targa": x["targa"], "telecamere": x["telecamere"]}
