"""Allungare le clip tagliate col P2P: i secondi prima e dopo la clip dell'operatrice, presi dal registratore Focus
(Dario, 11/11/2026 sera, in Guarda: «video tagliato troppo presto», «sembra che il video non finisca»; la strada e'
analisi/decisione-p2p-2026-11-11.md di kit-rifiuti-programma, decisione 1: il P2P arricchisce le clip).

Per ogni evento di allunga.json ({evento, kit, giorno, ora_inizio_clip, durata_clip, canali, prima_s, dopo_s, uid,
durate_canali}), per ogni canale:
  - «prima»: [inizio clip - prima_s, inizio clip), di difetto 60 s;
  - «dopo»: [fine clip, fine clip + dopo_s), di difetto 120 s;
  - «buco»: se quella telecamera nella clip dura meno delle altre, [inizio + la sua durata, fine clip);
  - «intera»: un canale che la clip non ha (le note «una sola telecamera») si chiede tutto, da prima a dopo.
Ogni tratto si scarica a richieste di al massimo 3 minuti. Ogni richiesta da' i fotogrammi con la loro ora vera
(OnStreamData); un mp4 si tiene solo fino al primo salto di piu' di 1,5 s fra due fotogrammi, cosi' un mp4 e' sempre
continuo e la sua ora di inizio e di fine sono vere. Dopo un salto, o una richiesta che si ferma prima, si riprova da li'
su un collegamento nuovo (P4 della decisione); se il registratore di nuovo non ha quei secondi, e' un buco e si scrive.
I canali non si uniscono mai qui: per ogni tratto si confrontano inizio, fine e buchi dei canali («sincronia») e un canale
con buchi o sfasato lo dice (compito 25: pezzi persi su due canali, uniti senza buco, telecamere sfasate di 3 minuti).

Prima di scaricare, GetRecordRange di ogni canale: un tratto che il registratore non ha piu' (il disco gira, 2-4
settimane) non si chiede e si scrive «non piu' sul registratore».

Il guasto di stasera (compito 28, 11/11 18:11): il ponte e' morto con 3221225477 (0xC0000005, accesso a memoria non
valida) fra una prova P2P finita e la successiva, mentre il filo principale era in Python (fra «prova 4437: ok» e la
riga della prova dopo, niente traceback nei registri). IPOTESI: la libreria chiama da un suo filo una funzione di
ritorno (stato del collegamento, flusso) di un Registratore gia' chiuso e liberato da Python. Qui ci si protegge in tre
modi: 1) ogni evento gira in un processo suo (allunga_lavoro.py, come owl_misura.py): se muore, muore lui, il ponte
scrive il codice e passa al prossimo (un evento morto per memoria si riprova una volta); 2) i Registratori chiusi non
si liberano fino alla fine del processo (cimitero), e il processo esce con os._exit senza scaricare la DLL; 3) ogni
chiamata alla libreria ha un tempo massimo (movimento.entro) e ogni evento un tempo massimo (il processo si uccide).

I MB: nessun tetto (Dario: niente tetti fissi di banda), ma si scrivono sempre: per richiesta, per evento, per kit e in
tutto. Il lavoro vero (registratore, ffmpeg, processo) arriva da fuori come funzioni: le prove a tavolino sono in
prova_allunga.py con una libreria finta.
version: 0.1.0 (11/11/2026): prima versione.
"""
import datetime
import math
import os
import time

VERSIONE = "0.1.0"

PRIMA_S, DOPO_S = 60, 120     # di difetto (Dario, 11/11)
PEZZO_MAX_S = 180             # una richiesta: al massimo 3 minuti (come la prova lunga)
SOGLIA_BUCO_S = 1.5           # due fotogrammi a piu' di 1,5 s: in mezzo manca qualcosa (a 12-25 fps sono 18-37 fotogrammi)
SOGLIA_INIZIO_S = 6.0         # si comincia dal primo fotogramma chiave: fino a 6 s dopo l'ora chiesta e' normale
SCARTO_SINCRONIA_S = 2.0      # inizi o fini di due canali a piu' di 2 s: sfasati
RICHIESTE_PER_TRATTO = 8
FRESCO = 200                  # secondi di un collegamento (il relay P2P si chiude dopo 5 minuti)
# secondi massimi per chiamata alla libreria; lo scarico: fisso + per_secondo * secondi chiesti (va a 2-3 volte il tempo
# reale, compito 25-26; dentro c'e' gia' il suo «nessun fotogramma per 30 s»)
TEMPI = {"nuovo": 30, "collega": 75, "canali": 20, "intervallo": 20, "chiudi": 20, "scarica_fisso": 90,
         "scarica_per_secondo": 1.5}
LIMITI = {"minuti_per_caso": 25.0,      # poi il processo dell'evento si uccide
          "ore_in_tutto": 10.0,         # poi i casi dopo non si fanno
          "ritenta_errore_memoria": 1}  # un evento morto con 0xC0000005 si rifa' una volta, in fondo
CODICI = {3221225477: "errore di memoria della libreria (0xC0000005, accesso a memoria non valida)",
          3221225725: "pila esaurita (0xC00000FD)", 3221226505: "errore grave nel processo (0xC0000409)",
          3221225786: "chiuso dall'esterno (0xC000013A)", 1: "errore in Python (vedi registro_python.txt)",
          3: "una chiamata alla libreria non e' tornata in tempo: il processo si e' chiuso da solo"}
MEMORIA = 3221225477


def limiti_da(cfg):
    """I limiti e i tempi per chiamata in uso: quelli qui sopra, abbassati (mai alzati) da cfg["limiti"] e cfg["tempi"]."""
    lim = dict(LIMITI)
    for k, v in ((cfg or {}).get("limiti") or {}).items():
        if k in lim and isinstance(v, (int, float)) and 0 <= v < lim[k]:
            lim[k] = type(lim[k])(v)
    tempi = dict(TEMPI)
    for k, v in ((cfg or {}).get("tempi") or {}).items():
        if k in tempi and isinstance(v, (int, float)) and 0 < v < tempi[k]:
            tempi[k] = v
    return lim, tempi


def esito_processo(codice):
    """Il codice d'uscita del processo di un evento in parole."""
    if codice == 0:
        return "finito"
    if isinstance(codice, str):
        return codice
    return CODICI.get(codice, f"uscito con il codice {codice}")


# ------------------------------------------------------------------ funzioni pure: tempi e tratti

def ora(t):
    return t.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4] if t else None


def momenti(ev):
    """(inizio, fine) della clip dell'operatrice."""
    s = datetime.datetime.strptime(f"{ev['giorno']} {ev['ora_inizio_clip']}", "%Y-%m-%d %H:%M:%S")
    return s, s + datetime.timedelta(seconds=float(ev.get("durata_clip") or 0))


def tratti(ev, prima_s=PRIMA_S, dopo_s=DOPO_S):
    """{canale: [(etichetta, da, a)]} da chiedere. I canali si contano da 0 come in reg.canali() (CH1 = 0)."""
    s, e = momenti(ev)
    p = datetime.timedelta(seconds=float(ev.get("prima_s", prima_s)))
    d = datetime.timedelta(seconds=float(ev.get("dopo_s", dopo_s)))
    dur = ev.get("durate_canali") or {}
    out = {}
    for c in ev["canali"]:
        c = int(c)
        mia = dur.get(str(c))
        if mia is None:
            out[c] = [("intera", s - p, e + d)]
            continue
        t = [("prima", s - p, s)]
        if (e - s).total_seconds() - float(mia) > SOGLIA_BUCO_S:
            t.append(("buco", s + datetime.timedelta(seconds=float(mia)), e))
        t.append(("dopo", e, e + d))
        out[c] = [x for x in t if x[2] > x[1]]
    return out


def dentro_registrazione(tr, iv):
    """Un tratto (etichetta, da, a) ristretto a quello che il registratore ha ([primo, ultimo] di GetRecordRange):
    (tratto o None, nota o None). iv None: il registratore non l'ha detto, si prova lo stesso."""
    et, da, a = tr
    if not iv or not iv[0] or not iv[1]:
        return tr, None
    primo, ultimo = iv
    if a <= primo:
        return None, f"non piu' sul registratore (la registrazione piu' vecchia e' delle {ora(primo)[:16]})"
    if da >= ultimo:
        return None, f"non ancora sul registratore (l'ultima registrazione e' delle {ora(ultimo)[:16]})"
    nota = None
    if da < primo:
        nota = f"dal registratore solo da {ora(primo)}: i primi {round((primo - da).total_seconds())} s non ci sono piu'"
        da = primo
    if a > ultimo:
        a = ultimo
    return (et, da, a), nota


def primo_salto(tempi, soglia=SOGLIA_BUCO_S):
    """L'indice dell'ultimo fotogramma prima del primo salto di piu' di `soglia` secondi, o None se non ce ne sono."""
    for i in range(len(tempi) - 1):
        if (tempi[i + 1] - tempi[i]).total_seconds() > soglia:
            return i
    return None


def buchi_di(pezzi, da, a, soglia=SOGLIA_BUCO_S, soglia_inizio=SOGLIA_INIZIO_S):
    """I secondi di [da, a) che i pezzi ([(inizio, fine)]) non coprono: [(da, a)]. All'inizio si tollera il fotogramma
    chiave (soglia_inizio), in mezzo e alla fine `soglia`."""
    out, t = [], da
    for i, (p0, p1) in enumerate(sorted(pezzi)):
        tolleranza = soglia_inizio if i == 0 else soglia
        if (p0 - t).total_seconds() > tolleranza:
            out.append((t, p0))
        t = max(t, p1)
    if (a - t).total_seconds() > soglia:
        out.append((t, a))
    return out


def secondi(intervalli):
    return round(sum((b - a).total_seconds() for a, b in intervalli), 2)


def sincronia(per_canale):
    """per_canale: {canale: {etichetta: {"da", "a", "pezzi": [(inizio, fine)], "buchi": [(da, a)]}}} (datetime).
    Per ogni etichetta che hanno almeno due canali: scarto degli inizi e delle fini, secondi mancanti per canale, e
    «sincroni» / «sfasati» / «con buchi». I canali non si uniscono: questo dice solo se si potrebbe."""
    etichette = sorted({et for t in per_canale.values() for et in t})
    out = {}
    for et in etichette:
        c = {k: v[et] for k, v in per_canale.items() if et in v and v[et].get("pezzi")}
        mancanti = {str(k): secondi(v[et].get("buchi") or []) for k, v in per_canale.items() if et in v}
        x = {"canali": len(c), "mancanti_s": mancanti}
        if len(c) >= 2:
            inizi = [min(p[0] for p in v["pezzi"]) for v in c.values()]
            fini = [max(p[1] for p in v["pezzi"]) for v in c.values()]
            x["scarto_inizio_s"] = round((max(inizi) - min(inizi)).total_seconds(), 2)
            x["scarto_fine_s"] = round((max(fini) - min(fini)).total_seconds(), 2)
            if any(mancanti.values()):
                x["esito"] = "con buchi: non unire i canali senza tenere conto dei secondi mancanti"
            elif x["scarto_inizio_s"] > SCARTO_SINCRONIA_S or x["scarto_fine_s"] > SCARTO_SINCRONIA_S:
                x["esito"] = "sfasati: non unire"
            else:
                x["esito"] = "sincroni"
        else:
            x["esito"] = "un canale solo" if c else "nessun canale"
        out[et] = x
    return out


def esito_evento(x):
    """La parola per l'evento dai suoi tratti: fatto / parziale / non piu' sul registratore / niente."""
    tr = [t for c in (x.get("canali") or {}).values() for t in (c.get("tratti") or {}).values()]
    if not tr:
        return x.get("esito") or "niente da chiedere"
    presi = [t for t in tr if t.get("pezzi")]
    via = [t for t in tr if str(t.get("nota") or "").startswith("non piu'")]
    if not presi:
        if via and len(via) == len(tr):
            return "non piu' sul registratore"
        return "niente scaricato"
    if all(not t.get("buchi_s") and not t.get("nota") for t in tr):
        return "fatto"
    return "parziale"


def nome_pezzo(canale, etichetta, inizio, fine):
    """CH1_prima_20261021-160358_160457.mp4: telecamera da 1, tratto, ora vera del primo e dell'ultimo fotogramma."""
    return f"CH{canale + 1}_{etichetta}_{inizio:%Y%m%d-%H%M%S}_{fine:%H%M%S}"


# ------------------------------------------------------------------ il collegamento (registratore dato da fuori)

class Bloccata(Exception):
    """Una chiamata alla libreria non e' tornata nel tempo massimo (il processo va chiuso)."""


def entro(funzione, secondi_max, nome="chiamata"):
    """movimento.entro, con la Bloccata di qui: funzione() in un filo suo, aspettata al massimo `secondi_max`."""
    import movimento
    try:
        return movimento.entro(funzione, secondi_max, nome)
    except movimento.Bloccata as ex:
        raise Bloccata(str(ex)) from None


class Collegamento:
    """Un registratore in P2P per un evento: un collegamento finche' e' fresco (FRESCO secondi), poi uno nuovo; ogni
    chiamata sotto tempo massimo e contata. I Registratori chiusi vanno in mezzi["cimitero"] e non si liberano.
    mezzi: nuovo() -> registratore, collega(reg) -> (ok, testo), tempi."""

    def __init__(self, mezzi, conti):
        self.m, self.conti = mezzi, conti
        self.reg, self.t, self.per, self.storia = None, 0.0, {}, []

    def chiama(self, nome, funzione, secondi_max=None):
        self.conti["chiamate"] += 1
        return entro(funzione, secondi_max or self.m["tempi"].get(nome, 30), nome)

    def apri(self):
        if self.reg is not None and time.time() - self.t < FRESCO:
            return
        self.chiudi()
        t0 = time.time()
        self.conti["collegamenti"] += 1
        self.reg = self.chiama("nuovo", self.m["nuovo"])
        self.m["cimitero"].append(self.reg)
        ok, testo = self.chiama("collega", lambda: self.m["collega"](self.reg))
        self.storia.append({"ok": bool(ok), "testo": testo, "secondi": round(time.time() - t0, 1)})
        if not ok:
            self.chiudi()
            raise ConnectionError(testo)
        self.per = {n: h for n, h, _ in self.chiama("canali", self.reg.canali)}
        self.t = time.time()

    def chiudi(self):
        if self.reg is not None:
            reg, self.reg = self.reg, None
            try:
                self.chiama("chiudi", reg.chiudi)
            except Exception:   # noqa: BLE001 - un chiudi che non torna non ferma niente: il processo finisce comunque
                pass

    def intervallo(self, canale):
        self.apri()
        if canale not in self.per:
            return None
        return self.chiama("intervallo", lambda: self.reg.intervallo(self.per[canale]))

    def scarica(self, canale, da, sec, cartella):
        self.apri()
        if canale not in self.per:
            return {"errore": "canale assente", "tempi": []}
        t = self.m["tempi"]
        h = self.per[canale]
        return self.chiama("scarica", lambda: self.reg.scarica(canale, h, da, sec, cartella, ffmpeg=self.m.get("ffmpeg", "ffmpeg")),
                           t["scarica_fisso"] + t["scarica_per_secondo"] * sec)


def scarica_tratto(col, canale, tratto, mezzi, conti, scrivi=lambda: None):
    """Un tratto di un canale: richieste da al massimo PEZZO_MAX_S finche' e' coperto; ogni pezzo continuo diventa un
    mp4 col nome dell'ora vera; dopo un salto o una fine anticipata si riprova da li' su un collegamento nuovo. Ritorna
    il dict del tratto (pezzi, buchi, MB, richieste); le eccezioni di collegamento e Bloccata salgono."""
    et, da, a = tratto
    tmp = os.path.join(mezzi["cartella_video"], "tmp")
    x = {"da": ora(da), "a": ora(a), "pezzi": [], "richieste": 0, "mb": 0.0, "secondi_attesa": 0.0, "note": []}
    dt_pezzi = []
    t, ritentato, nuovo = da, None, False
    coperto = da - datetime.timedelta(seconds=SOGLIA_INIZIO_S)   # fin dove i pezzi tenuti arrivano
    while (a - t).total_seconds() > SOGLIA_BUCO_S and x["richieste"] < RICHIESTE_PER_TRATTO:
        if nuovo:
            col.chiudi()
            nuovo = False
        sec = int(math.ceil(min(PEZZO_MAX_S, (a - t).total_seconds())))
        x["richieste"] += 1
        t0 = time.time()
        res = col.scarica(canale, t, sec, tmp)
        x["secondi_attesa"] = round(x["secondi_attesa"] + time.time() - t0, 1)
        mb = float(res.get("mb") or 0)
        x["mb"] = round(x["mb"] + mb, 2)
        conti["mb"] += mb
        tempi = [f for f in (res.get("tempi") or []) if f < t + datetime.timedelta(seconds=sec)]
        file = str(res.get("file") or "")
        if not tempi or not file.endswith(".mp4"):
            perche = res.get("errore") or ("ffmpeg: " + str(res.get("ffmpeg"))[-120:] if tempi else "nessun fotogramma")
            _togli(file)
            if res.get("errore") == "canale assente":
                x["note"].append("canale assente sul registratore")
                break
            if ritentato != t:   # un secondo tentativo, su un collegamento nuovo
                ritentato, nuovo = t, True
                x["note"].append(f"{ora(t)[11:19]}: {perche}, riprovo")
                continue
            x["note"].append(f"{ora(t)[11:19]}: {perche} anche al secondo tentativo")
            t, ritentato = t + datetime.timedelta(seconds=sec), None
            continue
        if (tempi[0] - t).total_seconds() > SOGLIA_INIZIO_S and ritentato != t:
            _togli(file)   # mancano i primi secondi: un secondo tentativo prima di dire che sono un buco
            ritentato, nuovo = t, True
            x["note"].append(f"{ora(t)[11:19]}: primo fotogramma {round((tempi[0] - t).total_seconds(), 1)} s dopo, riprovo")
            continue
        k = primo_salto(tempi)
        n = len(tempi) if k is None else k + 1
        inizio, fine = tempi[0], tempi[n - 1]
        if fine <= coperto:
            # di nuovo gli stessi fotogrammi prima del salto (lo scarico parte dal fotogramma chiave fino a 2 s prima):
            # il salto e' nella registrazione, non nel viaggio. Si riparte dal primo fotogramma dopo il salto.
            _togli(file)
            dopo = tempi[k + 1] if k is not None else t + datetime.timedelta(seconds=sec)
            if dopo <= t:
                dopo = t + datetime.timedelta(seconds=2.1)
            x["note"].append(f"{ora(fine)[11:19]}: il registratore non ha i secondi fino alle {ora(dopo)[11:19]}")
            t, ritentato, nuovo = dopo, None, True
            continue
        nome = nome_pezzo(canale, et, inizio, fine) + ".mp4"
        dest = os.path.join(mezzi["cartella_video"], nome)
        if k is None:
            mezzi["sposta"](file, dest)
        elif not mezzi["taglia"](file, n, dest):
            x["note"].append(f"{ora(t)[11:19]}: non riesco a tagliare il pezzo al salto: lo butto")
            _togli(file)
            dest = None
        else:
            _togli(file)
        if dest:
            fps = res.get("fps")
            p = {"file": nome, "inizio": ora(inizio), "fine": ora(fine), "secondi": round((fine - inizio).total_seconds(), 2),
                 "fotogrammi": n, "fps": fps, "mb_richiesta": round(mb, 2), "codec": res.get("codec"), "misura": res.get("misura")}
            if k is not None:
                p["salto_dopo_s"] = round((tempi[k + 1] - tempi[k]).total_seconds(), 2)
            if dt_pezzi and inizio < dt_pezzi[-1][1]:
                p["sovrapposto_s"] = round((dt_pezzi[-1][1] - inizio).total_seconds(), 2)
            foglio = mezzi["foglio"](dest, os.path.join(mezzi["cartella_fogli"], nome[:-4] + ".jpg"))
            if foglio:
                p["foglio"] = os.path.basename(foglio)
            x["pezzi"].append(p)
            dt_pezzi.append((inizio, fine))
            coperto = max(coperto, fine)
        passo = datetime.timedelta(seconds=1.0 / float(res.get("fps") or 25))
        avanti = fine + passo
        if k is not None or (t + datetime.timedelta(seconds=sec) - fine).total_seconds() > SOGLIA_BUCO_S:
            nuovo = True   # salto o fine anticipata: il resto da un collegamento nuovo
        ritentato = None
        t = avanti if avanti > t else t + datetime.timedelta(seconds=sec)
        scrivi()
    if (a - t).total_seconds() > SOGLIA_BUCO_S and x["richieste"] >= RICHIESTE_PER_TRATTO:
        x["note"].append(f"fermato dopo {RICHIESTE_PER_TRATTO} richieste")
    b = buchi_di(dt_pezzi, da, a)
    x["buchi"] = [[ora(p), ora(q)] for p, q in b]
    x["buchi_s"] = secondi(b)
    x["coperti_s"] = round(sum((q - p).total_seconds() for p, q in dt_pezzi), 2)
    x["_pezzi"], x["_buchi"] = dt_pezzi, b
    if not x["note"]:
        del x["note"]
    return x


def _togli(f):
    try:
        if f and os.path.exists(f):
            os.remove(f)
    except OSError:
        pass


def lavora_evento(ev, cfg, mezzi, scrivi=lambda x: None, av=lambda t: None):
    """Un evento intero, in un processo suo (o nel filo del ponte). mezzi: nuovo, collega(reg) -> (ok, testo), tempi,
    sposta(da, a), taglia(file, n, a) -> bool, foglio(mp4, jpg) -> jpg o None, cartella_video, cartella_fogli,
    cimitero, ffmpeg. Ritorna il dict dell'evento; scrivi(x) lo salva man mano (un processo che muore lascia quello
    che ha fatto)."""
    lim, tempi = limiti_da(cfg)
    mezzi = dict(mezzi, tempi=dict(tempi, **(mezzi.get("tempi") or {})))
    mezzi.setdefault("cimitero", [])
    for k in ("cartella_video", "cartella_fogli"):
        os.makedirs(mezzi[k], exist_ok=True)
    conti = {"chiamate": 0, "collegamenti": 0, "mb": 0.0}
    t0 = time.time()
    s, e = momenti(ev)
    x = {"evento": ev["evento"], "kit": ev.get("kit"), "giorno": ev.get("giorno"), "clip": [ora(s), ora(e)],
         "inizio_lavoro": time.strftime("%Y-%m-%d %H:%M:%S"), "in_corso": True, "canali": {},
         "cartella_video": mezzi["cartella_video"], "allunga": VERSIONE}

    def salva():
        x["conti"] = {"chiamate": conti["chiamate"], "collegamenti": conti["collegamenti"], "mb": round(conti["mb"], 2),
                      "secondi_lavoro": round(time.time() - t0, 1)}
        scrivi(x)

    if not ev.get("uid"):
        x.update(esito="registratore sconosciuto: il kit non c'e' nell'elenco di UVMS", in_corso=False)
        salva()
        return x
    col = Collegamento(mezzi, conti)
    per_canale = {}
    try:
        for c, trs in tratti(ev, cfg.get("prima_s", PRIMA_S), cfg.get("dopo_s", DOPO_S)).items():
            xc = x["canali"][str(c)] = {"tratti": {}}
            iv = col.intervallo(c)
            xc["registrazione"] = [ora(v) for v in iv] if iv else None
            if c not in col.per:
                xc["nota"] = "canale assente sul registratore"
                continue
            per_canale[c] = {}
            for tr in trs:
                giusto, nota = dentro_registrazione(tr, iv)
                if giusto is None:
                    xc["tratti"][tr[0]] = {"da": ora(tr[1]), "a": ora(tr[2]), "nota": nota, "pezzi": [], "buchi_s": 0}
                    continue
                r = scarica_tratto(col, c, giusto, mezzi, conti, salva)
                if nota:
                    r["nota"] = nota
                per_canale[c][tr[0]] = {"pezzi": r.pop("_pezzi"), "buchi": r.pop("_buchi")}
                xc["tratti"][tr[0]] = r
                av(f"allunga {ev['evento']} CH{c + 1} {tr[0]}: {len(r['pezzi'])} pezzi, {r['coperti_s']} s, buchi "
                   f"{r['buchi_s']} s, {r['mb']} MB, {r['richieste']} richieste")
                salva()
        x["esito"] = esito_evento(x)
    except Bloccata as ex:
        x["esito"] = f"bloccato: {ex}"
        x["bloccato"] = True
    except ConnectionError as ex:
        x["esito"] = f"registratore non raggiunto: {ex}"
    except (OSError, RuntimeError) as ex:
        x["esito"] = ("libreria non caricata: " if not col.storia else "errore: ") + f"{type(ex).__name__}: {str(ex)[:200]}"
    finally:
        if not x.get("bloccato"):
            col.chiudi()
    x["sincronia"] = sincronia(per_canale)
    x["collegamenti"] = col.storia
    x["in_corso"] = False
    x["fine_lavoro"] = time.strftime("%Y-%m-%d %H:%M:%S")
    salva()
    av(f"allunga {ev['evento']}: {x['esito']}, {x['conti']['mb']} MB, {x['conti']['chiamate']} chiamate")
    return x


# ------------------------------------------------------------------ il giro di tutti gli eventi (nel ponte)

def conti_di(eventi):
    """MB, secondi ottenuti, chiamate, collegamenti: in tutto e per kit; e quanti eventi per esito."""
    tot = {"mb": 0.0, "secondi_ottenuti": 0.0, "secondi_mancanti": 0.0, "chiamate": 0, "collegamenti": 0, "eventi": len(eventi)}
    kit, esiti = {}, {}
    for x in eventi:
        c = x.get("conti") or {}
        ott = sum(t.get("coperti_s") or 0 for ch in (x.get("canali") or {}).values() for t in (ch.get("tratti") or {}).values())
        man = sum(t.get("buchi_s") or 0 for ch in (x.get("canali") or {}).values() for t in (ch.get("tratti") or {}).values())
        for k, v in (("mb", c.get("mb") or 0), ("secondi_ottenuti", ott), ("secondi_mancanti", man),
                     ("chiamate", c.get("chiamate") or 0), ("collegamenti", c.get("collegamenti") or 0)):
            tot[k] += v
        k = str(x.get("kit"))
        kit.setdefault(k, {"mb": 0.0, "eventi": 0})
        kit[k]["mb"] = round(kit[k]["mb"] + (c.get("mb") or 0), 2)
        kit[k]["eventi"] += 1
        es = str(x.get("esito") or "?").split(":")[0]
        esiti[es] = esiti.get(es, 0) + 1
    for k in ("mb", "secondi_ottenuti", "secondi_mancanti"):
        tot[k] = round(tot[k], 2)
    return {"in_tutto": tot, "per_kit": kit, "esiti": esiti}


def lavoro(cfg, lancia, scrivi_out, av=lambda t: None, adesso=time.time):
    """Tutti gli eventi di allunga.json, uno alla volta: lancia(ev, secondi_max) -> (codice del processo, dict
    dell'evento o None). Un evento morto con l'errore di memoria si rifa' una volta, in fondo alla coda. scrivi_out(out)
    scrive uscita/allunga.json."""
    lim, tempi = limiti_da(cfg)
    t0 = adesso()
    out = {"allunga": VERSIONE, "limiti": lim, "tempi_per_chiamata_s": tempi, "prima_s": cfg.get("prima_s", PRIMA_S),
           "dopo_s": cfg.get("dopo_s", DOPO_S), "inizio": time.strftime("%Y-%m-%d %H:%M:%S"), "eventi": []}
    coda = list(cfg.get("eventi") or [])
    rifatti = {}
    while coda:
        ev = coda.pop(0)
        if adesso() - t0 > lim["ore_in_tutto"] * 3600:
            out["fermato"] = f"passate {lim['ore_in_tutto']} ore: {len(coda) + 1} eventi non fatti"
            break
        if not ev.get("uid"):
            x = {"evento": ev["evento"], "kit": ev.get("kit"), "esito": "registratore sconosciuto: il kit non c'e' nell'elenco di UVMS"}
        else:
            av(f"allunga {ev['evento']} (kit {ev.get('kit')}): parte")
            try:
                codice, r = lancia(ev, lim["minuti_per_caso"] * 60)
            except Exception as ex:   # noqa: BLE001 - un evento rotto non ferma gli altri
                codice, r = f"non partito: {type(ex).__name__}: {str(ex)[:200]}", None
            x = dict(r) if r else {"evento": ev["evento"], "kit": ev.get("kit")}
            x["processo"] = {"codice": codice, "esito": esito_processo(codice)}
            if codice != 0 and (r is None or r.get("in_corso") or not r.get("esito")):
                x["esito"] = esito_processo(codice) + (" (a meta': quello che c'e' e' quello che si e' fatto)" if r else "")
                x.pop("in_corso", None)
            if codice == MEMORIA and rifatti.get(ev["evento"], 0) < lim["ritenta_errore_memoria"]:
                rifatti[ev["evento"]] = rifatti.get(ev["evento"], 0) + 1
                coda.append(ev)
                x["si_rifa"] = True
        prima = next((i for i, y in enumerate(out["eventi"]) if y.get("evento") == ev["evento"]), None)
        if prima is not None:
            x["tentativo_prima"] = {k: out["eventi"][prima].get(k) for k in ("esito", "processo", "conti")}
            out["eventi"][prima] = x
        else:
            out["eventi"].append(x)
        out["conti"] = conti_di(out["eventi"])
        scrivi_out(out)
    out["conti"] = conti_di(out["eventi"])
    out["minuti"] = round((adesso() - t0) / 60, 1)
    out["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    scrivi_out(out)
    return out


# ------------------------------------------------------------------ la DLL vera e ffmpeg (solo sul PC)

_classe = {}


def classe_registratore():
    """focus_nvr.Registratore con lo scarico che rende anche l'ora vera di ogni fotogramma (res["tempi"]): scarica la
    raccoglie gia' e la passa a fps_da_tempi; qui la si legge li', senza toccare focus_nvr.py."""
    if "c" in _classe:
        return _classe["c"]
    import focus_nvr as fn

    class RegistratoreAllunga(fn.Registratore):
        def scarica(self, *a, **k):
            presi = []
            vecchia = fn.fps_da_tempi

            def spia(tempi):
                presi.append(list(tempi))
                return vecchia(tempi)
            fn.fps_da_tempi = spia
            try:
                res = super().scarica(*a, **k)
            finally:
                fn.fps_da_tempi = vecchia
            res["tempi"] = presi[-1] if presi else []
            return res

    _classe["c"] = RegistratoreAllunga
    return RegistratoreAllunga


def mezzi_veri(cartella_sdk, collega_con, ffmpeg, ev, cartella, cimitero, nofin=0):
    """I mezzi di lavora_evento sul PC: la DLL vera, ffmpeg per tagliare al salto e per il foglio dei fotogrammi."""
    import shutil
    import subprocess
    classe = classe_registratore()

    def taglia(file, n, dest):
        r = subprocess.run([ffmpeg, "-v", "error", "-y", "-i", file, "-frames:v", str(n), "-c", "copy", "-movflags",
                            "+faststart", dest], capture_output=True, timeout=300, creationflags=nofin)
        return r.returncode == 0 and os.path.exists(dest)

    def foglio(mp4, jpg):
        """Un fotogramma ogni 5 s, 6 per riga, 240 pixel: per guardare in fretta se l'abbandono c'e'."""
        try:
            subprocess.run([ffmpeg, "-v", "error", "-y", "-i", mp4, "-vf", "fps=1/5,scale=240:-2,tile=6x6", "-frames:v", "1",
                            "-q:v", "6", jpg], capture_output=True, timeout=300, creationflags=nofin)
        except (OSError, subprocess.SubprocessError):
            return None
        return jpg if os.path.exists(jpg) else None

    return {"nuovo": lambda: classe(cartella_sdk, log=lambda *_: None),
            "collega": lambda reg: collega_con(reg, ev["uid"], ev.get("kit")),
            "sposta": lambda a, b: shutil.move(a, b), "taglia": taglia, "foglio": foglio, "ffmpeg": ffmpeg,
            "cartella_video": os.path.join(cartella, "video"), "cartella_fogli": os.path.join(cartella, "uscita", "fogli"),
            "cimitero": cimitero}
