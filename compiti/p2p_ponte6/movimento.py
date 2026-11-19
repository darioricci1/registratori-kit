"""Dove c'e' stato movimento in una giornata di registrazione, chiesto al registratore Focus invece di guardare il video
(revisione dell'11/11/2026, «filtro economico»: prima di analizzare la registrazione continua, un indice gratis).

Cosa sa dire la libreria FocusNetSDK 1.0.0.3 (letto in FocusNetSDK.h, FNSCommons.h, FNSHandler.h, nel manuale e nella
tabella delle esportazioni della DLL; e' tutto quello che c'e':
  - GetRecordDaily(server, canale, giorno, ST_VM_RECORD_DAILY&): per ognuno dei 1440 minuti il tipo di registrazione
    E_RECORD_TYPE: 0 niente, 1 continua, 2 movimento, 3 sensore, 4 emergenza, 5 ora legale. E' l'unico indice
    «storico» del movimento: al minuto, e solo se il registratore e' impostato a registrare il movimento (modo
    movimento, continua + movimento, ...). Con la sola «continua» ogni minuto vale 1 e non dice niente.
  - OnRecordModeStatus (IStatusHandler, a collegamento aperto): ST_VM_RECORD_MODE con eRecMode (0 spenta, 1 continua,
    2 movimento, 3 sensore, 4 continua+movimento, 5 continua+sensore, 6 movimento+sensore) e bEventOn: dice come e'
    impostato il canale, quindi se l'indice qui sopra puo' esistere.
  - OnChannelEvent / OnServerEvent (IEventHandler): E_EVENT_TYPE_MOTION con MOTION_START / MOTION_END e l'ora. Solo in
    diretta, mentre si e' collegati: non c'e' una funzione che chieda gli eventi passati.
  - GetThumbImage(server, canale, ora) -> OnThumbStream (ST_VM_THUMB_STREAM: l'ora chiesta e un fotogramma codificato,
    ST_VM_VIDEO_STREAM): un fotogramma della registrazione a un'ora qualunque, senza aprire la riproduzione. E' il
    mattone del filtro «a fotogrammi radi» (punto 4 della revisione).
  - Non c'e': ricerca dei file registrati (niente QueryRecordFile / FindFile), dimensione dei pezzi sul disco, registro
    degli allarmi, ricerca intelligente; OnMetaStream (metadati XML) e' del flusso dal vivo dei registratori «AI».

Il compito (movimento.json, p2p_ponte 0.12.0) per ogni caso: per ogni canale i 1440 tipi del giorno dell'abbandono e
il modo di registrazione; sul canale dell'abbandono una miniatura ogni `passo_s` secondi intorno all'ora attesa, con
il cambio nella zona dei cassonetti fra una miniatura e l'altra («cambio») e fra la miniatura prima e quella 5 passi
dopo («cambio che resta»: un sacco resta, un'auto passa). Ogni chiamata alla libreria ha un tempo massimo (`entro`):
dopo il blocco di 3 ore nel dimezzamento, una chiamata che non torna ferma il caso, non il ponte.

Tutto qui e' senza rete e senza la libreria: il registratore e il decodificatore arrivano come funzioni
(prove a tavolino in prova_movimento.py, con una libreria finta). La classe che parla con la DLL vera e'
`classe_registratore()`, che importa focus_nvr solo quando serve.
version: 0.2.0 (19/11/2026): il giro dei registratori (compito movimento1, ponte 0.21.0; Dario, 19/11: «mettilo in
  coda», e poi «adesso»). movimento.json con «registratori» invece di «casi»: per ognuno, in un collegamento solo
  quando basta, il modo di registrazione di ogni canale (OnRecordModeStatus) e i tipi dei 1440 minuti di ieri; dove il
  movimento si registra (registra_movimento), i tipi dei giorni con un abbandono vero e delle ore vuote note. Per ogni
  abbandono (esito_caso) se un minuto della sua finestra (+-2 minuti) e' «movimento» o «sensore»; per le stesse
  telecamere la quota di minuti e di ore con movimento nelle ore senza clip note (quota_vuote) e nelle ore vuote del
  banco (quota_finestra). In uscita anche i 1440 tipi di ogni giorno letto, in testo (una cifra al minuto), per rifare i
  conti a tavolino. Con «tutti_da_stato» dopo i registratori con un caso vengono tutti quelli che hanno risposto al
  ponte nelle ultime 24 ore (aggiungi_da_stato). Niente miniature: GetThumbImage si lega solo quando serve (prima un
  nome sbagliato nella DLL avrebbe fermato anche il giro). LIMITI alzati solo per i totali, perche' ora i registratori
  sono ~300 invece di 5 casi: collegamenti 30 -> 420, chiamate 600 -> 5000, minuti 60 -> 420; MB, per caso (= per
  registratore) e miniature come prima. Il tempo del collegamento passa da 75 a 150 s: collega_con prova piu'
  credenziali da 40 s l'una, e un collegamento lento non deve contare come una chiamata bloccata.
version: 0.1.0 (11/11/2026): prima versione.
"""
import datetime
import threading
import time

VERSIONE = "0.2.0"

TIPI = {0: "niente", 1: "continua", 2: "movimento", 3: "sensore", 4: "emergenza", 5: "ora legale"}
TIPI_MOVIMENTO = (2, 3)       # quelli che nascono da un evento (movimento o sensore)
MODI = {0: "spenta", 1: "continua", 2: "movimento", 3: "sensore", 4: "continua + movimento",
        5: "continua + sensore", 6: "movimento + sensore"}
TEMPI = {"nuovo": 30, "collega": 150, "canali": 20, "giorno": 30, "intervallo": 20, "miniatura": 20, "chiudi": 20}
ATTESA_MINIATURA = 12         # secondi che si aspetta OnThumbStream dopo GetThumbImage
FRESCO = 200                  # secondi di un collegamento (il relay P2P si chiude dopo 5 minuti)
RESTA_PASSI = 5               # «cambio che resta»: la miniatura prima contro quella 5 passi dopo
BLOCCHI_MAX = 2               # dopo 2 chiamate che non tornano la libreria e' da lasciare stare: ci si ferma
LATO_GRIGIO = (96, 54)        # la miniatura ridotta in grigi per il confronto
# I limiti (fase di audit, Dario 11/11): movimento.json li puo' solo abbassare. Quando uno scatta, il caso in corso si
# ferma alla chiamata successiva (il collegamento si chiude, il lucchetto della libreria si lascia), i casi dopo non si
# fanno, uscita/movimento.json dice quale limite e' scattato e con quali conti; il segno di fatto si scrive comunque
# (il lavoro non riparte da solo).
# 0.2.0: nel giro dei registratori un «caso» e' un registratore. Alzati solo i totali (erano per 5 casi): ~300
# registratori, un collegamento l'uno (due o tre se i giorni da leggere sono tanti), ~10 chiamate l'uno, 30-80 s l'uno.
LIMITI = {"mb_totali": 100.0,         # MB ricevuti dal registratore (miniature; i tipi del giorno sono 6 kB a canale)
          "mb_per_caso": 25.0,
          "minuti_totali": 420.0,     # tempo di tutto il lavoro, dal primo collegamento (0.1.0: 60)
          "minuti_per_caso": 15.0,
          "chiamate_totali": 5000,    # chiamate alla libreria (collegamento, canali, giorno, intervallo, miniatura, chiudi)
          "chiamate_per_caso": 120,   # (0.1.0: 600)
          "collegamenti_totali": 420,  # collegamenti P2P aperti (0.1.0: 30, circa 2-5 per caso)
          "miniature_per_caso": 61}


class Bloccata(Exception):
    """Una chiamata alla libreria non e' tornata nel tempo massimo."""


class Limite(Exception):
    """Un limite di LIMITI e' scattato: ci si ferma."""


def limiti_da(cfg):
    """I limiti in uso: quelli di LIMITI, abbassati (mai alzati) da cfg["limiti"]; anche i tempi per chiamata."""
    lim = dict(LIMITI)
    for k, v in ((cfg or {}).get("limiti") or {}).items():
        if k in lim and isinstance(v, (int, float)) and 0 < v < lim[k]:
            lim[k] = type(lim[k])(v)
    tempi = dict(TEMPI)
    for k, v in ((cfg or {}).get("tempi") or {}).items():
        if k in tempi and isinstance(v, (int, float)) and 0 < v < tempi[k]:
            tempi[k] = v
    return lim, tempi


def controlla(conti, lim):
    """Il primo limite superato dai conti ({"chiamate", "collegamenti", "byte", "t0", e i *_caso}), o None."""
    ora = time.time()
    prove = (("mb_totali", conti["byte"] / 1e6), ("mb_per_caso", conti["byte_caso"] / 1e6),
             ("minuti_totali", (ora - conti["t0"]) / 60), ("minuti_per_caso", (ora - conti["t0_caso"]) / 60),
             ("chiamate_totali", conti["chiamate"]), ("chiamate_per_caso", conti["chiamate_caso"]),
             ("collegamenti_totali", conti["collegamenti"]))
    for k, v in prove:
        if v >= lim[k]:
            return f"{k}: {round(v, 2)} su {lim[k]}"
    return None


def nuovi_conti():
    t = time.time()
    return {"chiamate": 0, "collegamenti": 0, "byte": 0, "t0": t, "chiamate_caso": 0, "byte_caso": 0, "t0_caso": t}


def entro(funzione, secondi, nome="chiamata"):
    """funzione() in un filo suo, aspettata al massimo `secondi`. Ritorna il risultato o rilancia la sua eccezione; se
    non torna in tempo, Bloccata (il filo resta li', daemon: non si puo' fermare una chiamata dentro una DLL)."""
    esito = {}

    def gira():
        try:
            esito["r"] = funzione()
        except BaseException as ex:   # noqa: BLE001 - si rilancia nel filo di chi chiama
            esito["e"] = ex

    t = threading.Thread(target=gira, daemon=True, name="focus_" + nome)
    t.start()
    t.join(secondi)
    if t.is_alive():
        raise Bloccata(f"{nome}: nessuna risposta in {secondi} s")
    if "e" in esito:
        raise esito["e"]
    return esito.get("r")


# ------------------------------------------------------------------ funzioni pure: i 1440 minuti del giorno

def ora_minuto(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def pulisci_tipi(grezzi, quanti=1440):
    """I tipi letti dalla struttura -> lista di 1440 interi (quello che manca vale 0)."""
    t = [int(x) for x in list(grezzi or [])[:quanti]]
    return t + [0] * (1440 - len(t))


def conta_tipi(tipi):
    """{nome del tipo: minuti}, solo i tipi che ci sono."""
    out = {}
    for x in tipi:
        k = TIPI.get(x, f"tipo {x}")
        out[k] = out.get(k, 0) + 1
    return out


def tratti_di(tipi, voluti=TIPI_MOVIMENTO):
    """[(minuto_inizio, minuto_fine_escluso)] dei minuti consecutivi con un tipo fra `voluti`."""
    out, inizio = [], None
    for i, x in enumerate(list(tipi) + [None]):
        dentro = x in voluti
        if dentro and inizio is None:
            inizio = i
        elif not dentro and inizio is not None:
            out.append((inizio, i))
            inizio = None
    return out


def minuti_per_ora(tipi, voluti=TIPI_MOVIMENTO):
    """I minuti con un tipo fra `voluti` in ognuna delle 24 ore."""
    m = [0] * 24
    for i, x in enumerate(tipi[:1440]):
        if x in voluti:
            m[i // 60] += 1
    return m


def lettere_ore(m):
    """24 conti di minuti -> 24 lettere come ore_del_giorno del ponte: «0» niente, «A» tutta l'ora, un passo ogni 6
    minuti; un'ora con anche un minuto solo vale almeno «1» (si deve vedere)."""
    return "".join("0" if x <= 0 else "0123456789A"[max(1, min(10, round(min(60, x) / 6)))] for x in m)


def rispetto_atteso(tratti, minuto):
    """Dove cade il minuto dell'abbandono rispetto ai tratti di movimento: dentro (e in quale), o a quanti minuti dal
    movimento prima e da quello dopo. Le distanze sono fra il minuto atteso e il minuto di movimento piu' vicino."""
    out = {"minuto": ora_minuto(minuto), "dentro": False, "tratto": None, "prima_min": None, "dopo_min": None}
    for a, b in tratti:
        if a <= minuto < b:
            out.update(dentro=True, tratto=f"{ora_minuto(a)}-{ora_minuto(b)}", prima_min=0, dopo_min=0)
            return out
        if b <= minuto:
            out["prima_min"] = minuto - (b - 1)
        elif a > minuto and out["dopo_min"] is None:
            out["dopo_min"] = a - minuto
    return out


def entro_margine(r, margine=2):
    """Il movimento e' entro `margine` minuti dall'ora attesa (l'ora di Dario e l'orologio del registratore possono
    essere di qualche secondo diverse)?"""
    return bool(r["dentro"] or (r["prima_min"] is not None and r["prima_min"] <= margine)
                or (r["dopo_min"] is not None and r["dopo_min"] <= margine))


def riassunto_canale(tipi, atteso=None):
    """Tutto quello che dice un canale per un giorno: tipi, ore con movimento, tratti, dove cade l'abbandono."""
    tipi = pulisci_tipi(tipi)
    tr = tratti_di(tipi)
    mpo = minuti_per_ora(tipi)
    out = {"tipi": conta_tipi(tipi), "registrati": sum(1 for x in tipi if x),
           "minuti_movimento": sum(b - a for a, b in tr), "ore_con_movimento": sum(1 for x in mpo if x),
           "ore": lettere_ore(mpo), "ore_registrate": lettere_ore(minuti_per_ora(tipi, (1, 2, 3, 4, 5))),
           "tratti": [f"{ora_minuto(a)}-{ora_minuto(b)}" for a, b in tr[:400]], "tratti_quanti": len(tr)}
    if atteso is not None:
        r = rispetto_atteso(tr, atteso.hour * 60 + atteso.minute)
        r["entro_2_min"] = entro_margine(r)
        r["tipo_al_minuto"] = TIPI.get(tipi[atteso.hour * 60 + atteso.minute], "?")
        out["abbandono"] = r
    return out


def verdetto(canali, canale_atteso):
    """Una frase per il caso, dai riassunti dei canali ({numero: riassunto o {"errore"}})."""
    letti = {k: v for k, v in canali.items() if "tipi" in v}
    if not letti:
        return "non letto: il registratore non ha risposto per nessun canale"
    if not any(v["minuti_movimento"] for v in letti.values()):
        if not any(v["registrati"] for v in letti.values()):
            return "niente registrato quel giorno"
        return ("solo «continua»: il registratore non segna il movimento (impostazione), da qui nessun filtro gratis; "
                "resta la miniatura a fotogrammi radi")
    v = letti.get(canale_atteso)
    if v is None or "abbandono" not in v:
        return "il canale dell'abbandono non si e' letto; il movimento c'e' sugli altri"
    a = v["abbandono"]
    risparmio = round(100 * (1 - v["ore_con_movimento"] / 24))
    if a["dentro"] or a["entro_2_min"]:
        return (f"il movimento segnato copre l'abbandono ({a['tratto'] or 'a ' + str(min(x for x in (a['prima_min'], a['dopo_min']) if x is not None)) + ' min'}): "
                f"filtro usabile, {v['ore_con_movimento']} ore su 24 con movimento (risparmio {risparmio}%)")
    vicino = [x for x in (a["prima_min"], a["dopo_min"]) if x is not None]
    return (f"il movimento segnato NON copre l'abbandono (il piu' vicino a {min(vicino) if vicino else '-'} min): "
            "come filtro perde questo caso")


def unione_ore(canali):
    """Le ore con movimento su almeno un canale (24 lettere 0/1) e quante sono."""
    m = [0] * 24
    for v in canali.values():
        for i, c in enumerate(v.get("ore") or ""):
            if c != "0":
                m[i] = 1
    return "".join(str(x) for x in m), sum(m)


# ------------------------------------------------------------------ funzioni pure: le miniature

def tempi_miniature(atteso, prima_min, dopo_min, passo_s):
    """I momenti delle miniature intorno all'ora attesa, dentro lo stesso giorno."""
    giorno = atteso.replace(hour=0, minute=0, second=0, microsecond=0)
    t = max(giorno, atteso - datetime.timedelta(minutes=prima_min))
    fine = min(giorno + datetime.timedelta(seconds=86399), atteso + datetime.timedelta(minutes=dopo_min))
    out = []
    while t <= fine:
        out.append(t)
        t += datetime.timedelta(seconds=passo_s)
    return out


def maschera(w, h, riquadri):
    """Gli indici dei pixel dentro i riquadri ([x, y, l, a] in frazioni dell'immagine); tutti se non ce ne sono."""
    if not riquadri:
        return list(range(w * h))
    out = set()
    for x, y, l, a in riquadri:
        x0, y0 = max(0, int(x * w)), max(0, int(y * h))
        x1, y1 = min(w, max(x0 + 1, int(round((x + l) * w)))), min(h, max(y0 + 1, int(round((y + a) * h))))
        for r in range(y0, y1):
            out.update(range(r * w + x0, r * w + x1))
    return sorted(out)


def differenza(a, b, indici):
    """La differenza media (0-255) fra due immagini in grigi (bytes della stessa misura) sui pixel `indici`, tolta la
    differenza di luce media (una nuvola cambia tutto, un sacco cambia un pezzo)."""
    if not a or not b or len(a) != len(b) or not indici:
        return None
    sa = sum(a[i] for i in indici) / len(indici)
    sb = sum(b[i] for i in indici) / len(indici)
    d = sb - sa
    return round(sum(abs(b[i] - a[i] - d) for i in indici) / len(indici), 2)


def cambi(miniature, w, h, riquadri, resta=RESTA_PASSI):
    """miniature [{"t": datetime, "grigio": bytes o None, ...}] -> per ogni coppia di miniature buone consecutive
    {"da", "a", "cambio" (nella zona), "cambio_tutto", "resta" (la prima contro quella `resta` passi dopo)}."""
    buone = [m for m in miniature if m.get("grigio")]
    zona, tutto = maschera(w, h, riquadri), list(range(w * h))
    out = []
    for i in range(len(buone) - 1):
        a, b = buone[i], buone[i + 1]
        c = buone[min(len(buone) - 1, i + resta)]
        out.append({"da": a["t"], "a": b["t"], "cambio": differenza(a["grigio"], b["grigio"], zona),
                    "cambio_tutto": differenza(a["grigio"], b["grigio"], tutto),
                    "resta": differenza(a["grigio"], c["grigio"], zona)})
    return out


def posto_atteso(cambi_, atteso, chiave="cambio", primi=3):
    """In quale coppia cade l'ora attesa (da < atteso <= a), a che posto e' il suo cambio fra tutti (1 = il piu'
    grande) e i `primi` momenti col cambio piu' grande."""
    validi = [c for c in cambi_ if c.get(chiave) is not None]
    ordine = sorted(validi, key=lambda c: -c[chiave])
    out = {"chiave": chiave, "coppie": len(validi), "posto": None, "valore": None,
           "primi": [{"da": f"{c['da']:%H:%M:%S}", "a": f"{c['a']:%H:%M:%S}", chiave: c[chiave]} for c in ordine[:primi]]}
    for c in validi:
        if c["da"] < atteso <= c["a"]:
            out["posto"] = ordine.index(c) + 1
            out["valore"] = c[chiave]
            break
    return out


def riassunto_miniature(miniature):
    """Quante chieste, arrivate, decodificate; byte e secondi d'attesa (mediana e massimo); formato e misura."""
    arr = [m for m in miniature if m.get("byte")]
    byte = sorted(m["byte"] for m in arr)
    sec = sorted(m["secondi"] for m in miniature if m.get("secondi") is not None)
    return {"chieste": len(miniature), "arrivate": len(arr), "decodificate": sum(1 for m in miniature if m.get("grigio")),
            "byte_mediana": byte[len(byte) // 2] if byte else None, "byte_massimo": byte[-1] if byte else None,
            "kb_totali": round(sum(byte) / 1024, 1),
            "secondi_mediana": sec[len(sec) // 2] if sec else None, "secondi_massimo": sec[-1] if sec else None,
            "formati": sorted({m.get("formato") or "?" for m in arr}), "misure": sorted({m.get("misura") or "?" for m in arr})}


# ------------------------------------------------------------------ il lavoro (registratore e decodifica date da fuori)

class Sessione:
    """Un collegamento al registratore, con il lucchetto della libreria preso per tutto il tempo e ogni chiamata
    sotto tempo massimo. mezzi: nuovo() -> registratore, collega(reg) -> (ok, testo), lucchetto, tempi."""

    def __init__(self, mezzi, registro):
        self.m, self.registro, self.reg, self.t0 = mezzi, registro, None, 0.0

    def chiama(self, nome, funzione, controlla_limiti=True):
        c = self.m["conti"]
        if controlla_limiti:
            perche = controlla(c, self.m["limiti"])
            if perche:
                raise Limite(perche)
        c["chiamate"] += 1
        c["chiamate_caso"] += 1
        return entro(funzione, self.m["tempi"].get(nome, 30), nome)

    def __enter__(self):
        self.m["lucchetto"].acquire()
        try:
            t0 = time.time()
            self.m["conti"]["collegamenti"] += 1
            self.reg = self.chiama("nuovo", self.m["nuovo"])
            ok, testo = self.chiama("collega", lambda: self.m["collega"](self.reg))
            self.registro.append({"ok": bool(ok), "testo": testo, "secondi": round(time.time() - t0, 1)})
            if not ok:
                raise ConnectionError(testo)
            self.t0 = time.time()
            return self
        except BaseException:
            self._chiudi()
            raise

    def fresca(self):
        return time.time() - self.t0 < FRESCO

    def _chiudi(self):
        try:
            if self.reg is not None:
                self.chiama("chiudi", self.reg.chiudi, controlla_limiti=False)
        except Exception:   # noqa: BLE001 - anche un chiudi bloccato non deve tenere il lucchetto
            pass
        self.reg = None
        self.m["lucchetto"].release()

    def __exit__(self, *_):
        self._chiudi()


def un_caso(caso, cfg, mezzi, scrivi=lambda: None, av=lambda t: None):
    """Un caso di movimento.json. mezzi: nuovo, collega(reg, uid, kit), lucchetto, tempi, decodifica(dati, formato,
    nome) -> bytes in grigi LATO_GRIGIO o None, blocchi (lista condivisa delle chiamate bloccate). Ritorna il dict del
    caso (scritto anche man mano attraverso scrivi())."""
    atteso = datetime.datetime.strptime(caso["atteso"], "%Y-%m-%d %H:%M:%S")
    giorno = atteso.replace(hour=0, minute=0, second=0, microsecond=0)
    canale_atteso = int(caso["canale"])
    x = {"nome": caso["nome"], "kit": caso["kit"], "canale": canale_atteso, "atteso": caso["atteso"],
         "giorno": f"{giorno:%Y-%m-%d}", "collegamenti": [], "canali": {}, "inizio": time.strftime("%Y-%m-%d %H:%M:%S")}
    m = dict(mezzi, collega=lambda reg: mezzi["collega"](reg, caso["uid"], int(caso["kit"])))
    conti = mezzi["conti"]
    conti.update(chiamate_caso=0, byte_caso=0, t0_caso=time.time())
    t0 = time.time()
    # 1) i tipi del giorno di ogni canale e il modo di registrazione: poche chiamate, un collegamento
    try:
        with Sessione(m, x["collegamenti"]) as s:
            elenco = s.chiama("canali", s.reg.canali)
            x["elenco_canali"] = [{"numero": n, "titolo": t} for n, _, t in elenco]
            for n, h, _ in elenco:
                try:
                    grezzi = s.chiama("giorno", lambda: s.reg.tipi_del_giorno(h, giorno))
                except Bloccata as ex:
                    mezzi["blocchi"].append(str(ex))
                    x["canali"][str(n)] = {"errore": str(ex)}
                    break
                if grezzi is None:
                    x["canali"][str(n)] = {"errore": "GetRecordDaily ha risposto «no»"}
                    continue
                x["canali"][str(n)] = riassunto_canale(grezzi, atteso if n == canale_atteso else None)
                try:
                    iv = s.chiama("intervallo", lambda: s.reg.intervallo(h))
                    x["canali"][str(n)]["registra"] = [str(v) for v in iv] if iv else None
                except Bloccata as ex:
                    mezzi["blocchi"].append(str(ex))
                    break
            time.sleep(1)   # OnRecordModeStatus arriva da solo dopo il collegamento: gli si lascia un attimo
            x["modi"] = {str(k): v for k, v in (getattr(s.reg, "modi", None) or {}).items()}
            x["eventi_in_diretta"] = list(getattr(s.reg, "eventi", None) or [])[:200]
    except Bloccata as ex:
        mezzi["blocchi"].append(str(ex))
        x["esito"] = f"bloccato: {ex}"
    except Limite as ex:
        x["esito"] = x["limite"] = f"limite scattato: {ex}"
    except (ConnectionError, OSError, RuntimeError) as ex:
        x["esito"] = f"registratore non raggiunto: {ex}"
    x["verdetto"] = verdetto({int(k): v for k, v in x["canali"].items()}, canale_atteso)
    x["ore_con_movimento_unione"], x["quante_ore_unione"] = unione_ore(x["canali"])
    x["secondi_tipi"] = round(time.time() - t0, 1)
    scrivi()
    av(f"movimento {caso['nome']}: {x['verdetto']}")
    x["conti_tipi"] = {"chiamate": conti["chiamate_caso"], "collegamenti": len(x["collegamenti"])}
    if "esito" in x or len(mezzi["blocchi"]) >= BLOCCHI_MAX:
        return x
    # 2) le miniature intorno all'ora attesa sul canale dell'abbandono, a collegamenti di FRESCO secondi
    mc = cfg.get("miniature") or {}
    if not mc.get("passo_s"):
        return x
    tempi = tempi_miniature(atteso, int(mc.get("minuti_prima", 30)), int(mc.get("minuti_dopo", 30)), int(mc["passo_s"]))
    tempi = tempi[:int(mezzi["limiti"]["miniature_per_caso"])]
    mini = [{"t": t} for t in tempi]
    t1, i = time.time(), 0
    while i < len(mini) and len(mezzi["blocchi"]) < BLOCCHI_MAX:
        try:
            with Sessione(m, x["collegamenti"]) as s:
                per = {n: h for n, h, _ in s.chiama("canali", s.reg.canali)}
                if canale_atteso not in per:
                    x["miniature_errore"] = "canale dell'abbandono assente"
                    break
                while i < len(mini) and s.fresca():
                    q = mini[i]
                    t2 = time.time()
                    try:
                        r = s.chiama("miniatura", lambda: s.reg.miniatura(per[canale_atteso], q["t"], ATTESA_MINIATURA))
                    except Bloccata as ex:
                        mezzi["blocchi"].append(str(ex))
                        q["errore"] = str(ex)
                        i += 1
                        break
                    q["secondi"] = round(time.time() - t2, 2)
                    if r and r.get("dati"):
                        conti["byte"] += len(r["dati"])
                        conti["byte_caso"] += len(r["dati"])
                        q.update(byte=len(r["dati"]), formato=r.get("formato"), misura=r.get("misura"),
                                 tipo=r.get("tipo"), ora_video=r.get("ora_video"), dati=r["dati"])
                    else:
                        q["errore"] = (r or {}).get("errore") or "nessuna miniatura"
                    i += 1
        except Bloccata as ex:
            mezzi["blocchi"].append(str(ex))
            break
        except Limite as ex:
            x["limite"] = f"limite scattato: {ex}"
            break
        except (ConnectionError, OSError, RuntimeError) as ex:
            x["miniature_errore"] = f"registratore non raggiunto: {ex}"
            break
    for q in mini:   # la decodifica fuori dal lucchetto: e' ffmpeg, non la libreria
        dati = q.pop("dati", None)
        if dati:
            try:
                q["grigio"] = mezzi["decodifica"](dati, q.get("formato"),
                                               f"{caso['nome']}_{q['t']:%H%M%S}_ch{canale_atteso + 1}")
            except Exception as ex:   # noqa: BLE001
                q["errore_decodifica"] = f"{type(ex).__name__}: {str(ex)[:120]}"
    w, h = LATO_GRIGIO
    riq = (caso.get("zona") or {}).get("riquadri") or []
    cc = cambi(mini, w, h, riq)
    x["miniature"] = riassunto_miniature(mini)
    x["miniature"]["secondi_lavoro"] = round(time.time() - t1, 1)
    x["miniature"]["zona"] = riq
    x["miniature"]["cambio"] = posto_atteso(cc, atteso, "cambio")
    x["miniature"]["resta"] = posto_atteso(cc, atteso, "resta")
    x["miniature"]["serie"] = [{"da": f"{c['da']:%H:%M:%S}", "cambio": c["cambio"], "tutto": c["cambio_tutto"],
                                "resta": c["resta"]} for c in cc]
    x["miniature"]["elenco"] = [{"t": f"{q['t']:%H:%M:%S}", **{k: q[k] for k in ("byte", "secondi", "tipo", "ora_video",
                                 "errore", "errore_decodifica") if q.get(k) is not None}} for q in mini]
    x["conti"] = {"chiamate": conti["chiamate_caso"], "collegamenti": len(x["collegamenti"]),
                  "mb": round(conti["byte_caso"] / 1e6, 3), "secondi": round(time.time() - t0, 1)}
    scrivi()
    av(f"movimento {caso['nome']}: miniature {x['miniature']['arrivate']}/{x['miniature']['chieste']}, "
       f"posto del cambio all'ora attesa {x['miniature']['cambio']['posto']}, che resta {x['miniature']['resta']['posto']}")
    return x


def lavoro(cfg, mezzi, scrivi_out, av=lambda t: None):
    """Tutti i casi di movimento.json, uno dopo l'altro; dopo BLOCCHI_MAX chiamate bloccate ci si ferma. scrivi_out(out)
    scrive uscita/movimento.json. 0.2.0: con «registratori» il giro dei registratori (giro_registratori)."""
    if cfg.get("registratori") is not None:
        return giro_registratori(cfg, mezzi, scrivi_out, av)
    mezzi = dict(mezzi)
    lim, tempi = limiti_da(cfg)
    mezzi.setdefault("limiti", lim)
    mezzi.setdefault("tempi", tempi)
    mezzi.setdefault("blocchi", [])
    mezzi.setdefault("conti", nuovi_conti())
    c = mezzi["conti"]
    out = {"movimento": VERSIONE, "limiti": mezzi["limiti"], "tempi_per_chiamata_s": mezzi["tempi"],
           "casi": [], "blocchi": mezzi["blocchi"], "inizio": time.strftime("%Y-%m-%d %H:%M:%S")}
    for caso in cfg.get("casi") or []:
        if len(mezzi["blocchi"]) >= BLOCCHI_MAX:
            out["fermato"] = f"{len(mezzi['blocchi'])} chiamate alla libreria senza risposta: i casi dopo non si fanno"
            break
        perche = controlla(dict(c, chiamate_caso=0, byte_caso=0, t0_caso=time.time()), mezzi["limiti"])
        if perche or any(x.get("limite") for x in out["casi"]):
            out["fermato"] = "limite scattato: " + (perche or next(x["limite"] for x in out["casi"] if x.get("limite")))
            break
        try:
            out["casi"].append(un_caso(caso, cfg, mezzi, lambda: scrivi_out(out), av))
        except Exception as ex:   # noqa: BLE001 - un caso rotto non ferma gli altri
            out["casi"].append({"nome": caso.get("nome"), "esito": f"errore {type(ex).__name__}: {str(ex)[:300]}"})
        scrivi_out(out)
    out["conti"] = {"chiamate": c["chiamate"], "collegamenti": c["collegamenti"], "mb": round(c["byte"] / 1e6, 3),
                    "minuti": round((time.time() - c["t0"]) / 60, 1)}
    out["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    scrivi_out(out)
    return out


# ------------------------------------------------------------------ 0.2.0: il giro dei registratori (compito movimento1)

MODI_CON_MOVIMENTO = ("movimento", "sensore", "continua + movimento", "continua + sensore", "movimento + sensore")
ATTESA_MODI = 4.0     # secondi che si aspetta OnRecordModeStatus dopo il collegamento (arriva da solo)
ORA_PIENA = 30        # un'ora vuota conta se ha almeno 30 minuti registrati


def tipi_in_testo(tipi):
    """1440 tipi -> 1440 caratteri, una cifra al minuto («?» per un tipo oltre il 9). Funzione pura."""
    return "".join(str(x) if 0 <= int(x) <= 9 else "?" for x in pulisci_tipi(tipi))


def da_testo(s):
    """Il contrario di tipi_in_testo («?» vale 9, che non e' ne' continua ne' movimento). Funzione pura."""
    return [int(c) if c.isdigit() else 9 for c in str(s or "")[:1440]] + [0] * max(0, 1440 - len(str(s or "")))


def minuto_di(hhmm):
    h, m = str(hhmm).split(":")[:2]
    return int(h) * 60 + int(m)


def registra_movimento(modi, tipi_ieri):
    """(«si» / «no» / «?», perche') dai modi dei canali ({numero: {"modo"}}) e dai tipi di ieri ({numero: lista}):
    «si» se ieri c'e' un minuto movimento o sensore, o se un canale e' impostato con il movimento; «no» se i modi
    dicono tutti senza movimento, o se non sono arrivati e ieri ogni minuto e' «continua» o «niente»; «?» se non si e'
    letto niente. Funzione pura."""
    con = [n for n, t in (tipi_ieri or {}).items() if t and any(x in TIPI_MOVIMENTO for x in t)]
    if con:
        return "si", f"ieri minuti con movimento sui canali {sorted(int(n) for n in con)}"
    impostati = [n for n, m in (modi or {}).items() if (m or {}).get("modo") in MODI_CON_MOVIMENTO]
    if impostati:
        return "si", f"impostato a movimento sui canali {sorted(int(n) for n in impostati)}, ieri nessun minuto"
    if modi:
        return "no", "modo: " + ", ".join(sorted({str((m or {}).get("modo")) for m in modi.values()}))
    if any(t for t in (tipi_ieri or {}).values()):
        return "no", "il modo non e' arrivato; ieri solo «continua» o «niente»"
    return "?", "ne' il modo ne' i tipi di ieri"


def esito_caso(caso, tipi_di):
    """Un abbandono: per ogni sua telecamera i minuti della finestra (da-a, il margine e' gia' dentro) registrati e con
    movimento; «coperto» se un minuto della finestra e' movimento o sensore su una telecamera (su quella sola se il
    canale e' certo, che e' il caso di difetto), «non coperto», «non sul disco» (nessun minuto registrato nella
    finestra), «non letto». tipi_di(canale) -> 1440 tipi o None. Funzione pura."""
    a, b = minuto_di(caso["da"]), minuto_di(caso["a"])
    per, letti = {}, 0
    for c in caso["canali"]:
        t = tipi_di(c)
        if t is None:
            per[str(c)] = None
            continue
        letti += 1
        f = t[a:b + 1]
        per[str(c)] = {"registrati": sum(1 for x in f if x), "movimento": sum(1 for x in f if x in TIPI_MOVIMENTO),
                       "tipi": "".join(str(x) if 0 <= x <= 9 else "?" for x in f)}
    vivi = [v for v in per.values() if v]
    if not letti:
        esito = "non letto"
    elif not any(v["registrati"] for v in vivi):
        esito = "non sul disco"
    elif any(v["movimento"] for v in vivi):
        esito = "coperto"
    else:
        esito = "non coperto"
    return {"nome": caso.get("nome"), "giorno": caso["giorno"], "da": caso["da"], "a": caso["a"],
            "canali": caso["canali"], "fonti": caso.get("fonti"), "eventi": caso.get("eventi"), "esito": esito,
            "per_canale": per}


def ore_escluse(noti, margine=1):
    """Le ore che non contano fra le vuote: quella di ogni minuto noto («HH:MM») e `margine` ore prima e dopo.
    Funzione pura."""
    out = set()
    for n in noti or []:
        h = minuto_di(n) // 60
        out.update(range(max(0, h - margine), min(23, h + margine) + 1))
    return out


def quota_vuote(tipi, escluse, piena=ORA_PIENA):
    """Nelle ore fuori da `escluse` con almeno `piena` minuti registrati: quante ore, quante con almeno un minuto
    movimento, minuti registrati e minuti movimento. Funzione pura."""
    out = {"ore": 0, "ore_con_movimento": 0, "minuti_registrati": 0, "minuti_movimento": 0}
    for h in range(24):
        if h in escluse:
            continue
        f = tipi[h * 60:(h + 1) * 60]
        reg = sum(1 for x in f if x)
        if reg < piena:
            continue
        mov = sum(1 for x in f if x in TIPI_MOVIMENTO)
        out["ore"] += 1
        out["ore_con_movimento"] += 1 if mov else 0
        out["minuti_registrati"] += reg
        out["minuti_movimento"] += mov
    return out


def quota_finestra(tipi, da, a):
    """Un'ora vuota nota (da-a): minuti registrati e con movimento, e i tratti di 5 minuti con movimento su quelli
    registrati (un filtro a 5 minuti farebbe analizzare quelli). Funzione pura."""
    x, y = minuto_di(da), minuto_di(a)
    f = tipi[x:y]
    pezzi = [f[i:i + 5] for i in range(0, len(f), 5)]
    return {"minuti_registrati": sum(1 for v in f if v), "minuti_movimento": sum(1 for v in f if v in TIPI_MOVIMENTO),
            "pezzi_5_registrati": sum(1 for p in pezzi if any(p)),
            "pezzi_5_movimento": sum(1 for p in pezzi if any(v in TIPI_MOVIMENTO for v in p))}


def somma(a, b):
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def conti_registratore(r, letti):
    """Dai tipi letti ({(giorno, canale): lista}) i casi, le vuote del banco e la quota delle ore vuote di ogni giorno e
    telecamera letti. Funzione pura."""
    casi = [esito_caso(c, lambda can, g=c["giorno"]: letti.get((g, int(can)))) for c in r.get("casi") or []]
    vuote = []
    for v in r.get("vuote") or []:
        t = letti.get((v["giorno"], int(v["canale"])))
        vuote.append(dict(v, **(quota_finestra(t, v["da"], v["a"]) if t is not None else {"esito": "non letto"})))
    quota = {}
    for (g, c), t in letti.items():
        q = quota_vuote(t, ore_escluse(((r.get("giorni") or {}).get(g) or {}).get("noti")))
        quota = somma(quota, q)
    return casi, vuote, quota


def aggiungi_da_stato(registratori, stato, escludi=("998",)):
    """Ai registratori di movimento.json (prima) quelli di op=stato del sito che hanno risposto al ponte nelle ultime
    24 ore e che non ci sono gia' (per UID e per kit), dal piu' risposto. Funzione pura."""
    out = list(registratori or [])
    visti = {str(r.get("uid") or "").upper() for r in out} | {str(r.get("kit")) for r in out}
    righe = []
    for i, x in enumerate((stato or {}).get("kit") or []):
        uid = str(x.get("uid") or "").strip()
        kit = str(x.get("kit") or "").strip().lstrip("0")
        if not uid or not kit.isdigit() or kit in escludi or uid.upper() in visti or kit in visti:
            continue
        risposte = int(x.get("risposte_24h") or 0)
        if risposte <= 0:
            continue
        visti.update((uid.upper(), kit))
        righe.append((-risposte, i, {"kit": int(kit), "uid": uid, "giorni": {}, "casi": [], "vuote": [],
                                     "da_stato": True}))
    return out + [r for *_, r in sorted(righe, key=lambda z: z[:2])]


def un_registratore(r, cfg, mezzi, av=lambda t: None):
    """Un registratore del giro: collegamento, canali, tipi di ieri di ogni canale, modo; se il movimento si registra,
    i tipi dei giorni chiesti (riaprendo il collegamento quando non e' piu' fresco). Ritorna il dict del registratore."""
    ieri = datetime.datetime.strptime(cfg["ieri"], "%Y-%m-%d") if cfg.get("ieri") else \
        datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=1), datetime.time())
    x = {"kit": r["kit"], "collegamenti": [], "inizio": time.strftime("%Y-%m-%d %H:%M:%S"), "ieri": f"{ieri:%Y-%m-%d}"}
    if r.get("da_stato"):
        x["da_stato"] = True
    m = dict(mezzi, collega=lambda reg: mezzi["collega"](reg, r["uid"], int(r["kit"])))
    conti = mezzi["conti"]
    conti.update(chiamate_caso=0, byte_caso=0, t0_caso=time.time())
    t0 = time.time()
    da_leggere = [(g, int(c)) for g, gg in (r.get("giorni") or {}).items() for c in gg.get("canali") or []]
    letti, tipi_ieri = {}, {}
    try:
        with Sessione(m, x["collegamenti"]) as s:
            elenco = s.chiama("canali", s.reg.canali)
            per = {int(n): h for n, h, _ in elenco}
            x["canali"] = [{"numero": n, "titolo": t} for n, _, t in elenco]
            for n, h in per.items():
                t = s.chiama("giorno", lambda: s.reg.tipi_del_giorno(h, ieri))
                tipi_ieri[n] = pulisci_tipi(t) if t is not None else None
            fino = time.time() + ATTESA_MODI
            modi_h = getattr(s.reg, "modi", None)
            while time.time() < fino and len(modi_h or {}) < len(per):
                time.sleep(0.25)
            da_h = {h: n for n, h in per.items()}
            x["modi"] = {str(da_h.get(k, k)): v for k, v in dict(modi_h or {}).items()}
            x["eventi_in_diretta"] = list(getattr(s.reg, "eventi", None) or [])[:50]
            x["registra_movimento"], x["perche"] = registra_movimento(
                {int(k): v for k, v in x["modi"].items() if str(k).isdigit()}, {k: v for k, v in tipi_ieri.items() if v})
            if x["registra_movimento"] == "si":
                while da_leggere and s.fresca():   # (il primo collegamento ha gia' fatto ieri: puo' non restare tempo)
                    g, c = da_leggere.pop(0)
                    if c not in per:
                        letti[(g, c)] = None
                        continue
                    t = s.chiama("giorno", lambda: s.reg.tipi_del_giorno(per[c], datetime.datetime.strptime(g, "%Y-%m-%d")))
                    letti[(g, c)] = pulisci_tipi(t) if t is not None else None
        while x.get("registra_movimento") == "si" and da_leggere and len(mezzi["blocchi"]) < BLOCCHI_MAX:
            with Sessione(m, x["collegamenti"]) as s:   # il relay si chiude dopo 5 minuti: un collegamento nuovo
                per = {int(n): h for n, h, _ in s.chiama("canali", s.reg.canali)}
                primo = True
                while da_leggere and (primo or s.fresca()):   # almeno un giorno per collegamento: si va sempre avanti
                    primo = False
                    g, c = da_leggere.pop(0)
                    t = s.chiama("giorno", lambda: s.reg.tipi_del_giorno(per[c], datetime.datetime.strptime(g, "%Y-%m-%d"))) \
                        if c in per else None
                    letti[(g, c)] = pulisci_tipi(t) if t is not None else None
    except Bloccata as ex:
        mezzi["blocchi"].append(str(ex))
        x["esito"] = f"bloccato: {ex}"
    except Limite as ex:
        x["esito"] = x["limite"] = f"limite scattato: {ex}"
    except (ConnectionError, OSError, RuntimeError) as ex:
        x["esito"] = f"registratore non raggiunto: {ex}"
    x.setdefault("esito", "letto")
    x["ieri_tipi"] = {str(n): (tipi_in_testo(t) if t is not None else None) for n, t in tipi_ieri.items()}
    x["ieri_conti"] = {str(n): conta_tipi(t) for n, t in tipi_ieri.items() if t is not None}
    validi = {k: v for k, v in letti.items() if v is not None}
    x["casi"], x["vuote"], x["quota_vuote"] = conti_registratore(r, validi)
    if x.get("registra_movimento") != "si":
        for c in x["casi"]:
            c["esito"] = "movimento non registrato" if x.get("registra_movimento") == "no" else "non letto"
    x["giorni_letti"] = {f"{g} ch{c + 1}": (tipi_in_testo(t) if t is not None else None) for (g, c), t in letti.items()}
    x["giorni_non_letti"] = [f"{g} ch{c + 1}" for g, c in da_leggere]
    x["conti"] = {"chiamate": conti["chiamate_caso"], "collegamenti": len(x["collegamenti"]),
                  "secondi": round(time.time() - t0, 1)}
    av(f"movimento kit {r['kit']}: {x['esito']}, registra movimento {x.get('registra_movimento', '-')}"
       + (f", casi {sum(1 for c in x['casi'] if c['esito'] == 'coperto')}/{len(x['casi'])} coperti" if x["casi"] else ""))
    return x


def riassunto_giro(regs):
    """I numeri del giro: registratori per esito e per modo, casi per esito e per fonte, quota delle ore vuote sui
    registratori che segnano il movimento. Funzione pura."""
    out = {"registratori": len(regs), "letti": sum(1 for x in regs if x.get("esito") == "letto"),
           "registra_movimento": {}, "modi": {}, "casi": {}, "casi_per_fonte": {}, "quota_vuote": {}, "vuote_banco": {}}
    for x in regs:
        k = x.get("registra_movimento") or "non letto"
        out["registra_movimento"][k] = out["registra_movimento"].get(k, 0) + 1
        for v in (x.get("modi") or {}).values():
            mo = str((v or {}).get("modo"))
            out["modi"][mo] = out["modi"].get(mo, 0) + 1
        for c in x.get("casi") or []:
            out["casi"][c["esito"]] = out["casi"].get(c["esito"], 0) + 1
            for f in c.get("fonti") or []:
                d = out["casi_per_fonte"].setdefault(f, {})
                d[c["esito"]] = d.get(c["esito"], 0) + 1
        if x.get("registra_movimento") == "si":
            out["quota_vuote"] = somma(out["quota_vuote"], x.get("quota_vuote") or {})
            for v in x.get("vuote") or []:
                if "minuti_registrati" in v:
                    out["vuote_banco"] = somma(out["vuote_banco"], {k: v[k] for k in ("minuti_registrati",
                                               "minuti_movimento", "pezzi_5_registrati", "pezzi_5_movimento")})
    q = out["quota_vuote"]
    if q.get("ore"):
        q["quota_ore"] = round(q["ore_con_movimento"] / q["ore"], 3)
    if q.get("minuti_registrati"):
        q["quota_minuti"] = round(q["minuti_movimento"] / q["minuti_registrati"], 3)
    vb = out["vuote_banco"]
    if vb.get("pezzi_5_registrati"):
        vb["quota_pezzi_5"] = round(vb["pezzi_5_movimento"] / vb["pezzi_5_registrati"], 3)
    letti = out["casi"].get("coperto", 0) + out["casi"].get("non coperto", 0)
    if letti:
        out["casi_coperti_quota"] = round(out["casi"].get("coperto", 0) / letti, 3)
    return out


def giro_registratori(cfg, mezzi, scrivi_out, av=lambda t: None):
    """movimento.json con «registratori»: uno dopo l'altro (stessi limiti e blocchi dei casi). scrivi_out(out)."""
    lim, tempi = limiti_da(cfg)
    mezzi = dict(mezzi)
    mezzi.setdefault("limiti", lim)
    mezzi.setdefault("tempi", tempi)
    mezzi.setdefault("blocchi", [])
    mezzi.setdefault("conti", nuovi_conti())
    c = mezzi["conti"]
    regs = list(cfg.get("registratori") or [])
    if cfg.get("tutti_da_stato") and mezzi.get("stato"):
        try:
            regs = aggiungi_da_stato(regs, mezzi["stato"]())
        except Exception as ex:   # noqa: BLE001 - senza il sito si fanno quelli con un caso
            av(f"movimento: op=stato non letto ({type(ex).__name__}: {str(ex)[:120]}), solo i registratori con un caso")
    out = {"movimento": VERSIONE, "limiti": mezzi["limiti"], "tempi_per_chiamata_s": mezzi["tempi"],
           "registratori_in_elenco": len(regs), "registratori": [], "blocchi": mezzi["blocchi"],
           "inizio": time.strftime("%Y-%m-%d %H:%M:%S")}
    av(f"movimento: {len(regs)} registratori ({sum(1 for r in regs if r.get('casi'))} con un caso)")
    for i, r in enumerate(regs):
        if len(mezzi["blocchi"]) >= BLOCCHI_MAX:
            out["fermato"] = f"{len(mezzi['blocchi'])} chiamate alla libreria senza risposta: i registratori dopo non si fanno"
            break
        perche = controlla(dict(c, chiamate_caso=0, byte_caso=0, t0_caso=time.time()), mezzi["limiti"])
        if perche:
            out["fermato"] = "limite scattato: " + perche
            break
        try:
            out["registratori"].append(un_registratore(r, cfg, mezzi, av))
        except Exception as ex:   # noqa: BLE001 - un registratore rotto non ferma gli altri
            out["registratori"].append({"kit": r.get("kit"), "esito": f"errore {type(ex).__name__}: {str(ex)[:300]}"})
        x = out["registratori"][-1]
        if x.get("limite") and "per_caso" not in x["limite"]:
            out["fermato"] = x["limite"]
            break
        if i % 5 == 4 or i == len(regs) - 1:
            out["riassunto"] = riassunto_giro(out["registratori"])
            scrivi_out(out)
    if "fermato" in out:
        out["non_fatti"] = [r.get("kit") for r in regs[len(out["registratori"]):]]
    out["riassunto"] = riassunto_giro(out["registratori"])
    out["conti"] = {"chiamate": c["chiamate"], "collegamenti": c["collegamenti"], "mb": round(c["byte"] / 1e6, 3),
                    "minuti": round((time.time() - c["t0"]) / 60, 1)}
    out["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
    scrivi_out(out)
    return out


# ------------------------------------------------------------------ la DLL vera (solo su Windows, solo quando serve)

_classe = {}


def classe_registratore():
    """focus_nvr.Registratore con quello che serve qui: i tipi grezzi dei 1440 minuti, GetThumbImage con OnThumbStream,
    OnRecordModeStatus (il modo di registrazione di ogni canale) e gli eventi di canale. Il resto (collegamento, canali,
    scarico) e' quello di focus_nvr."""
    if "c" in _classe:
        return _classe["c"]
    import ctypes
    import os
    import focus_nvr as fn

    class ST_VM_THUMB_STREAM(ctypes.Structure):
        _fields_ = [("oRequest", fn.ST_VM_TIME), ("oVideo", fn.ST_VM_VIDEO_STREAM), ("uiReserved", ctypes.c_uint * 4)]

    class ST_VM_RECORD_MODE(ctypes.Structure):
        _fields_ = [("bRecModeChange", ctypes.c_bool), ("eRecMode", ctypes.c_int), ("bEventOn", ctypes.c_bool),
                    ("bEmergency", ctypes.c_bool), ("bDiskfail", ctypes.c_bool), ("uiReserved", ctypes.c_uint * 4)]

    class ST_VM_SERVER_EVENT(ctypes.Structure):
        _fields_ = [("eEventType", ctypes.c_int), ("eEventTypeSub", ctypes.c_int), ("oTriggerTime", fn.ST_VM_TIME),
                    ("uiEventDataSize", ctypes.c_uint), ("pEventData", ctypes.c_void_p), ("uiReserved", ctypes.c_uint * 4)]

    NOME_MINIATURA = "?GetThumbImage@IFocusNetSDK@@UEAA_N_K0Utag_ST_VM_TIME@@@Z"
    EVENTI = {0: "movimento", 1: "sensore", 2: "video", 3: "impostazioni", 4: "disco", 5: "sistema", 6: "registrazione"}
    SOTTO = {1: "inizio", 2: "fine", 3: "inizio", 4: "fine", 5: "video c'e'", 6: "video perso", 13: "inizio", 14: "fine"}

    class RegistratoreMovimento(fn.Registratore):
        _miniatura = None

        def __init__(self, cartella=None, log=print):
            self.modi, self.eventi = {}, []
            self._mini = {"h": None, "dati": None, "evento": threading.Event()}
            self._cartella = cartella
            super().__init__(cartella, log)

        @classmethod
        def _lega_miniatura(cls, cartella):
            """0.2.0: GetThumbImage si lega solo quando serve una miniatura: un nome sbagliato non ferma i tipi."""
            if cls._miniatura is None:
                lib = ctypes.CDLL(os.path.join(fn.cartella_sdk(cartella), "FocusNetSDK.dll"))
                f = getattr(lib, NOME_MINIATURA)
                f.restype = ctypes.c_uint8
                f.argtypes = [ctypes.c_void_p, fn.c_handle, fn.c_handle, ctypes.POINTER(fn.ST_VM_TIME)]
                cls._miniatura = f
            return cls._miniatura

        def _prepara_ritorni(self):
            super()._prepara_ritorni()
            stato, flusso, eventi = self._tieni[0], self._tieni[3], self._tieni[6]   # le liste date a _tabella

            def su_modo(_this, _hi, _hs, hc, p):
                try:
                    r = ctypes.cast(p, ctypes.POINTER(ST_VM_RECORD_MODE)).contents
                    self.modi[int(hc)] = {"modo": MODI.get(r.eRecMode, r.eRecMode), "eventi_accesi": bool(r.bEventOn),
                                          "emergenza": bool(r.bEmergency), "disco_rotto": bool(r.bDiskfail)}
                except Exception:   # noqa: BLE001 - niente eccezioni verso la DLL
                    pass
                return True

            def su_miniatura(_this, _hi, _hs, hc, p):
                try:
                    if hc == self._mini["h"] and not self._mini["evento"].is_set():
                        s = ctypes.cast(p, ctypes.POINTER(ST_VM_THUMB_STREAM)).contents
                        v = s.oVideo
                        dati = ctypes.string_at(v.pData, v.uiDataSize) if v.pData and v.uiDataSize else b""
                        t = fn.da_tempo_vm(v.oStreamTime)
                        self._mini["dati"] = {"dati": dati, "formato": "H.265" if v.eVideoFormat == fn.E_VIDEO_H265 else "H.264",
                                              "misura": f"{v.usWidth_Org}x{v.usHeight_Org}", "tipo": int(v.eFrameType),
                                              "ora_video": t.isoformat(sep=" ") if t else None,
                                              "codice_inizio": fn.ha_codice_inizio(dati)}
                        self._mini["evento"].set()
                except Exception:   # noqa: BLE001
                    self._mini["evento"].set()
                return True

            def su_evento(_this, _hi, _hs, hc, p):
                try:
                    if len(self.eventi) < 500:
                        e = ctypes.cast(p, ctypes.POINTER(ST_VM_SERVER_EVENT)).contents
                        t = fn.da_tempo_vm(e.oTriggerTime)
                        self.eventi.append({"canale_h": int(hc), "tipo": EVENTI.get(e.eEventType, e.eEventType),
                                            "fase": SOTTO.get(e.eEventTypeSub, e.eEventTypeSub),
                                            "ora": t.isoformat(sep=" ") if t else None})
                except Exception:   # noqa: BLE001
                    pass
                return True

            self._cb_mov = [fn._CB_CAN(su_modo), fn._CB_CAN(su_miniatura), fn._CB_CAN(su_evento)]
            self.h_stato = self._tabella([stato[0], stato[1], self._cb_mov[0], stato[3]])
            self.h_flusso = self._tabella([flusso[0], flusso[1], self._cb_mov[1], flusso[3]])
            self.h_eventi = self._tabella([eventi[0], self._cb_mov[2]])

        def tipi_del_giorno(self, canale_h, giorno):
            rd = fn.ST_VM_RECORD_DAILY()
            t = fn.tempo_vm(giorno)
            if not self.f["GetRecordDaily"](self.this, self.server, canale_h, ctypes.byref(t), ctypes.byref(rd)):
                return None
            return list(rd.eRecType[:min(int(rd.uiTypeCount or 1440), 1440)])

        def miniatura(self, canale_h, quando, attesa=ATTESA_MINIATURA):
            self._mini.update(h=canale_h, dati=None)
            self._mini["evento"].clear()
            t = fn.tempo_vm(quando)
            if not RegistratoreMovimento._lega_miniatura(self._cartella)(self.this, self.server, canale_h, ctypes.byref(t)):
                return {"errore": "GetThumbImage ha risposto «no»"}
            if not self._mini["evento"].wait(attesa):
                return {"errore": f"nessuna miniatura in {attesa} s"}
            return self._mini["dati"]

    _classe["c"] = RegistratoreMovimento
    return RegistratoreMovimento
