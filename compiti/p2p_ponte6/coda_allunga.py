"""La coda degli allungamenti chiesti da Kit_Rifiuti (kit-rifiuti-programma, archivio_kit 0.92.0): quali eventi il
ponte allunga in questo giro e cosa ricordare di ognuno. Dario, 12/11/2026: «l'allungamento deve partire da solo, il
giorno stesso, appena il programma trova una clip troppo corta» (il compito 30 ha recuperato 8 eventi su 34, 21 erano
gia' sovrascritti: i registratori tengono 2-3 settimane).

Kit_Rifiuti sullo stesso PC scrive ~/kr_lavori/allunga/coda.json ({"eventi": [richieste]}, con i campi di allunga.json
piu' «e», «da_pc», «chiesto_il», «scade_il»); il ponte la legge (0.19.0: ogni ora, e ogni 5 minuti finche' c'e' lavoro),
sceglie qui cosa fare (da_fare), allunga con allunga.py in ~/kr_lavori/allunga/coda/<evento>/ e ricorda l'esito in
~/kr_lavori/allunga/coda/registro.json (segna). Kit_Rifiuti guarda quelle cartelle e il registro: monta l'evento
«<id>-al», o chiude la richiesta quando il ponte rinuncia.

0.3.0 (16/11/2026): si allunga solo quello che chiede Dario (16/11 mattina: «facciamo che allunghi solo quelle che ti
chiedo di allungare»; «sono semplicemente delle dubbie, che io se ritengo posso anche chiedere di allungare»). La lista
non e' piu' la coda automatica di Kit_Rifiuti (coda.json, che dalla 0.99.10 resta vuota e qui non si legge: le 460 del
16/11 non si scaricano) ne' allunga_urgenti.json (le 39 del 16/11 sono fatte): e' op=allungare del sito kit-rifiuti,
letto col biglietto dell'account di servizio (dal_sito), cioe' le clip dove Dario ha premuto «⤢ Allunga» in
video.html. Tutte fuori dal tetto per kit (le ha scelte lui, una per una). Alla fine del giro gli eventi finiti o
rinunciati tornano al sito (fatti_per_sito, POST op=allungare {fatti}), cosi' non si chiedono piu'.

0.2.0 (16/11/2026): le richieste urgenti del compito (allunga_urgenti.json, le clip tagliate trovate dai giudizi che il
programma non aveva chiesto: 39 il 16/11, che scadono fra 2 e 13 giorni) vanno davanti a tutta la coda, dalla piu'
vicina alla scadenza (unisci), e non contano nel tetto per kit: una clip che il registratore sovrascrive domani non
aspetta dopodomani.

Regole (provate in prova_coda_allunga.py):
  - un evento finito (fatto, parziale, non piu' sul registratore, niente da prendere, registratore sconosciuto) non si
    rifa' mai;
  - uno fallito per il collegamento (registratore non raggiunto, bloccato, errore, processo caduto) si riprova dopo
    un'ora, al massimo TENTATIVI_MAX volte; poi «rinunciato»;
  - una richiesta scaduta (oltre scade_il) non si fa;
  - per giro al massimo PER_GIRO eventi e per kit al massimo PER_KIT_AL_GIORNO al giorno (la banda delle SIM dei kit:
    nessun tetto fisso deciso da Dario, ma i MB si scrivono); le urgenti fuori dal tetto per kit;
  - l'ordine: prima le urgenti per scadenza, poi la coda com'e' (Kit_Rifiuti la scrive gia' in ordine d'urgenza).
version: 0.3.0 (16/11/2026); la lista dal sito (dal_sito, fatti_per_sito)
0.2.0: diagnosi per i risultati gia' sul disco che Kit_Rifiuti non ha montato
"""
import datetime

VERSIONE = "0.3.0"
TENTATIVI_MAX = 3
RIPROVA_S = 3600
PER_GIRO = 6
PER_KIT_AL_GIORNO = 3
GIORNI_MAX = 24        # come ALLUNGA_GIORNI_MAX di archivio_kit: oltre, il registratore l'ha quasi certamente sovrascritto
FINALI = ("fatto", "parziale", "non piu' sul registratore", "niente scaricato", "niente da chiedere",
          "registratore sconosciuto")
DA_TOGLIERE = ("e", "da_pc", "chiesto_il", "urgente", "chiesta_da", "chiesta_il", "canali_stimati")   # per allunga.py e per l'uscita su Drive: niente nomi delle cartelle


def _giorno(s):
    try:
        return datetime.date.fromisoformat(str(s or "")[:10])
    except ValueError:
        return None


def scadenza(r, giorni_max=GIORNI_MAX):
    """Il giorno dopo il quale il registratore non ha piu' la clip: scade_il della richiesta, se no giorno + giorni_max;
    None se non si sa. Funzione pura."""
    s = _giorno(r.get("scade_il"))
    if s:
        return s
    g = _giorno(r.get("giorno"))
    return g + datetime.timedelta(days=giorni_max) if g else None


def unisci(urgenti, coda, giorni_max=GIORNI_MAX):
    """La lista di lavoro: le urgenti (segnate «urgente», con scade_il se mancava) dalla piu' vicina alla scadenza, poi
    la coda nel suo ordine; un evento che e' in tutte e due conta una volta, come urgente. Funzione pura."""
    urg = []
    for r in urgenti or []:
        if isinstance(r, dict) and r.get("evento"):
            x = dict(r, urgente=True)
            s = scadenza(x, giorni_max)
            if s and not x.get("scade_il"):
                x["scade_il"] = s.isoformat()
            urg.append(x)
    urg.sort(key=lambda r: (scadenza(r, giorni_max) or datetime.date.max, str(r.get("ora_inizio_clip") or ""), r["evento"]))
    visti = {r["evento"] for r in urg}
    return urg + [r for r in coda or [] if isinstance(r, dict) and r.get("evento") not in visti]


def dal_sito(risposta):
    """0.3.0: le richieste da allungare dalla risposta di op=allungare del sito ({"eventi": [richieste con «chiesta_da»]}),
    tutte chieste da Dario: solo quelle con evento, giorno, ora della clip, kit e canali; doppioni fuori; tutte «urgente»
    (fuori dal tetto per kit: le ha scelte lui). L'ordine resta quello del sito (dalla prima che scade). Funzione pura."""
    out, visti = [], set()
    eventi = (risposta.get("eventi") or []) if isinstance(risposta, dict) else []
    for r in eventi:
        if not isinstance(r, dict):
            continue
        ev = str(r.get("evento") or "")
        if not ev or ev in visti or not r.get("giorno") or not r.get("ora_inizio_clip") or not r.get("kit") \
                or not isinstance(r.get("canali"), list) or not r["canali"]:
            continue
        visti.add(ev)
        out.append(dict(r, urgente=True))
    return out


def fatti_per_sito(registro, lista):
    """0.3.0: per il sito (POST op=allungare {fatti}): gli eventi della lista che il ponte ha chiuso (finito o rinunciato),
    con l'esito breve. Funzione pura."""
    out = []
    for r in lista or []:
        x = (registro or {}).get(r.get("evento")) or {}
        if x.get("stato") in ("finito", "rinunciato"):
            out.append({"evento": r["evento"], "esito": (x.get("esito") or x["stato"])[:160]})
    return out


def da_fare(coda, registro, adesso, oggi=None, per_giro=PER_GIRO, per_kit=PER_KIT_AL_GIORNO, riprova_s=RIPROVA_S,
            tentativi_max=TENTATIVI_MAX):
    """Le richieste da allungare in questo giro, nell'ordine della lista (unisci). coda: [richieste]; registro: {evento:
    {stato, tentativi, ultimo (epoch), giorno_lavoro, kit}}; adesso: epoch. Funzione pura."""
    oggi = oggi or datetime.date.fromtimestamp(adesso)
    oggi_s = oggi.isoformat()
    per_kit_oggi = {}
    for x in (registro or {}).values():
        if x.get("giorno_lavoro") == oggi_s and not x.get("urgente"):
            per_kit_oggi[str(x.get("kit"))] = per_kit_oggi.get(str(x.get("kit")), 0) + 1
    out, visti = [], set()
    for r in coda or []:
        ev = r.get("evento") if isinstance(r, dict) else None
        if not ev or ev in visti or not r.get("ora_inizio_clip") or not r.get("giorno"):
            continue
        visti.add(ev)
        x = (registro or {}).get(ev) or {}
        if x.get("stato") in ("finito", "rinunciato"):
            continue
        if x.get("stato") == "da_riprovare" and adesso - float(x.get("ultimo") or 0) < riprova_s:
            continue
        scade = _giorno(r.get("scade_il"))
        if scade and scade < oggi:
            continue
        k = str(r.get("kit"))
        if not r.get("urgente"):
            if per_kit_oggi.get(k, 0) >= per_kit:
                continue
            per_kit_oggi[k] = per_kit_oggi.get(k, 0) + 1
        out.append(r)
        if len(out) >= per_giro:
            break
    return out


def per_ponte(r):
    """La richiesta come voce di allunga.json, senza i nomi delle cartelle delle operatrici. Funzione pura."""
    return {k: v for k, v in r.items() if k not in DA_TOGLIERE}


def segna(registro, x, adesso, oggi=None, tentativi_max=TENTATIVI_MAX, urgente=False):
    """Ricorda l'esito di un evento (x: la voce di uscita di allunga.lavoro). Ritorna lo stato nuovo. Funzione pura
    (cambia `registro`)."""
    ev = x.get("evento")
    prima = registro.get(ev) or {}
    es = str(x.get("esito") or "")
    tentativi = int(prima.get("tentativi") or 0) + 1
    if es.split(":")[0] in FINALI or es.startswith(FINALI):
        stato = "finito"
    elif tentativi >= tentativi_max:
        stato = "rinunciato"
    else:
        stato = "da_riprovare"
    registro[ev] = {"stato": stato, "tentativi": tentativi, "ultimo": adesso, "esito": es[:160], "kit": x.get("kit"),
                    "giorno_lavoro": (oggi or datetime.date.fromtimestamp(adesso)).isoformat(),
                    "mb": (x.get("conti") or {}).get("mb"), **({"urgente": True} if urgente or prima.get("urgente") else {})}
    return stato


def riassunto(registro, lista, oggi):
    """Per uscita/allunga_coda_stato.json (su Drive, senza nomi): quanti eventi per stato, quante richieste aspettano
    ancora e, delle urgenti, chi e' fatto e chi no. Funzione pura."""
    stati = {}
    for x in (registro or {}).values():
        stati[x.get("stato")] = stati.get(x.get("stato"), 0) + 1
    aperte = [r for r in lista or [] if ((registro or {}).get(r.get("evento")) or {}).get("stato") not in ("finito", "rinunciato")
              and not ((_giorno(r.get("scade_il")) or oggi) < oggi)]
    urg = [r for r in lista or [] if r.get("urgente")]
    return {"stati": stati, "aperte": len(aperte), "in_lista": len(lista or []),
            "urgenti": [{"evento": r["evento"], "kit": r.get("kit"), "scade_il": r.get("scade_il"),
                         "stato": ((registro or {}).get(r["evento"]) or {}).get("stato", "da fare"),
                         "esito": ((registro or {}).get(r["evento"]) or {}).get("esito", "")[:80]} for r in urg]}


def diagnosi(risultati, trattati, richieste):
    """0.2.0: i risultati sul disco del ponte ([{cartella, evento, esito, ...}]) messi accanto a quello che Kit_Rifiuti
    ne ha fatto (allungati.json: {evento: {azione, esito, tentativi}}) e alle richieste di questo PC
    (allunga_richieste.json: {evento: {stato}}). Per trovare perche' un risultato «fatto» non diventa un evento «-al»:
    «mai guardati» sono quelli che Kit_Rifiuti non ha mai scritto in allungati.json (prepara_allungati non ci e' arrivato).
    Solo id, esiti e conti. Funzione pura."""
    tr = trattati if isinstance(trattati, dict) else {}
    out, conti = [], {}
    for x in risultati or []:
        t = tr.get(x.get("evento")) or {}
        az = t.get("azione") or "mai guardato"
        conti[az] = conti.get(az, 0) + 1
        out.append(dict(x, kit_rifiuti=az, kit_rifiuti_esito=str(t.get("esito") or "")[:80],
                        tentativi=t.get("tentativi", 0)))
    da_montare = [x["evento"] for x in out if str(x.get("esito", "")).split(":")[0] in ("fatto", "parziale")
                  and x["kit_rifiuti"] != "montato"]
    st = {}
    for r in (richieste.values() if isinstance(richieste, dict) else []):
        k = (r or {}).get("stato", "aperta")
        st[k] = st.get(k, 0) + 1
    return {"risultati": out, "per_azione": conti, "fatti_non_montati": da_montare,
            "trattati_in_tutto": len(tr), "richieste_di_questo_pc": st}
