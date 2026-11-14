# registratori-kit/dati/schemi_ore.py - version: 0.1.0 (14/11/2026)
# 0.1.0: gli schemi delle ore registrate (Dario, 14/11: «capire qual è il problema del kit, se è ricorrente: se funziona
#        sempre solo a mezzogiorno, o sempre solo di notte... anche in base a come è composto il kit»). Per ogni telecamera
#        le ore registrate dal 27/10 (op=ore) dentro l'archivio (op=stato), dal giorno dopo l'installazione; per ogni kit le
#        ore in cui almeno una telecamera registra, i tratti spenti con l'ora d'inizio e di fine, il giorno per giorno; poi la
#        diagnosi per gruppi (A lampione, B solare, C ripartito, D fermo, E giorni interi, F sparsi, G una telecamera sola, H
#        senza ore, M senza registratore, N non risponde) con l'ANAGRAFICA KIT (BATT, N. TELECAMERE, installazione, data
#        della batteria), gli ODM e le telecamere da sistemare. Analisi e report: analisi-ore-registrazione-2026-11-14.md.
# Uso (sola lettura):
#   python3 dati/schemi_ore.py <cartella> --scarica <chiave.json>   scarica op=stato, op=ore, op=sistemare (biglietto del
#                                                                     PC) e le schede ANAGRAFICA KIT e ODM nella cartella
#   python3 dati/schemi_ore.py <cartella>                             rifà dati/schemi_ore.json dai file della cartella
# La chiave dell'account di servizio resta fuori dal repository: si passa una copia e la si cancella dopo.
import json, re, sys, os, collections, statistics as stt, datetime as dt

FOGLIO_KIT = "1I3-xl5rlQu0xCUA9mj9c5BC_zR27Tioy0X6FRwXqKRw"   # «Elenco KIT Date Registrazioni»
SITO = "https://registratori-kit.vercel.app/api/p2p?op="


def scarica(chiave, D):
    import urllib.request
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request, AuthorizedSession
    c = service_account.IDTokenCredentials.from_service_account_file(chiave, target_audience="https://mappakit.alma/nvr-remoto")
    c.refresh(Request())
    for op in ("stato", "ore", "sistemare"):
        with urllib.request.urlopen(urllib.request.Request(SITO + op, headers={"Authorization": "Bearer " + c.token}), timeout=180) as r:
            json.dump(json.load(r), open(f"{D}/{op}.json", "w"), ensure_ascii=False)
    s = AuthorizedSession(service_account.Credentials.from_service_account_file(
        chiave, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]))
    v = lambda t, r: s.get(f"https://sheets.googleapis.com/v4/spreadsheets/{FOGLIO_KIT}/values/'{t}'!{r}").json().get("values", [])
    json.dump(v("ANAGRAFICA KIT", "A1:AF1500"), open(f"{D}/anagrafica.json", "w"), ensure_ascii=False)
    json.dump({"ODM": v("ODM", "A1:Z4000")}, open(f"{D}/altri.json", "w"), ensure_ascii=False)


def analizza(D):
    """Primo passo: per registratore e telecamera le matrici delle ore e le misure. Scrive <cartella>/risultati.json."""
    st = json.load(open(f"{D}/stato.json")); ore_l = json.load(open(f"{D}/ore.json"))
    ana_v = json.load(open(f"{D}/anagrafica.json")); alt = json.load(open(f"{D}/altri.json"))
    sis = json.load(open(f"{D}/sistemare.json"))
    DAL = dt.date(2026, 10, 27)
    ORE = {(x["uid"], x["canale"]): x["ore"] or {} for x in ore_l}
    VAL = {c: i for i, c in enumerate("0123456789A")}

    # ---------- anagrafica: la riga INSTALLATO del kit, se no l'ultima
    h = ana_v[0]
    righe = [dict(zip(h, r + [""] * (len(h) - len(r)))) for r in ana_v[1:]]
    ANA = {}
    for r in righe:
        k = re.sub(r"\D", "", r["KIT"])
        if not k: continue
        k = int(k)
        if k not in ANA or r["STATO"].strip().upper() == "INSTALLATO" or ANA[k]["STATO"].strip().upper() != "INSTALLATO":
            if k in ANA and ANA[k]["STATO"].strip().upper() == "INSTALLATO" and r["STATO"].strip().upper() != "INSTALLATO": continue
            ANA[k] = r

    def alimentazione(b):
        b = (b or "").lower()
        if "solare" in b: return "solare"
        if "220" in b: return "220V"
        if "townet" in b: return "Townet"
        if re.search(r"\d+\s*ah", b): return "batteria"   # 42Ah senza pannello: si ricarica dalla pubblica illuminazione (ODM)
        return "?"

    def n_sat(t):
        t = (t or "").upper().replace(" ", "")
        m = re.search(r"\+(\d?)SAT", t)
        return 0 if not m else int(m.group(1) or 1)

    def n_tlc(t):
        t = (t or "").upper().replace(" ", "")
        tot = 0
        for p in t.split("+"):
            m = re.match(r"(\d+)?(SAT)?", p)
            if m.group(1): tot += int(m.group(1))
            elif m.group(2): tot += 1
        return tot or None

    # ODM aperti per kit (scheda ODM: DATA CHIUSURA vuota)
    ODM = collections.defaultdict(list)
    for r in alt["ODM"][1:]:
        r = r + [""] * (26 - len(r))
        k = re.sub(r"\D", "", r[2])
        if k and not r[14].strip(): ODM[int(k)].append((r[5], r[6], r[7], r[15].replace("\n", " ")))

    # nitidezza
    SFOC = collections.defaultdict(list)
    for t in sis["telecamere"]:
        SFOC[t["kit_n"]].append(f"CH{t['cam']} {t['problema']}")

    # ---------- registratori
    def kit_n(nome):
        m = re.match(r"^\s*(\d{2,4})", nome or "")
        return int(m.group(1)) if m else None

    REG = {}
    for k in st["kit"]:
        REG.setdefault(k["uid"], k)
    ARC = collections.defaultdict(dict)
    for a in st["archivio"]:
        ARC[a["uid"]][a["canale"]] = a

    def locale(iso):   # novembre: CET, UTC+1
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (t + dt.timedelta(hours=1)).replace(tzinfo=None)

    def data_ana(s):
        """«09/11/2026», «9/11/26» o il numero di serie di Excel («46065»): la data, o None."""
        s = (s or "").strip()
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
        if m:
            a = int(m.group(3)); a += 2000 if a < 100 else 0
            try: return dt.date(a, int(m.group(2)), int(m.group(1)))
            except ValueError: return None
        if re.fullmatch(r"4\d{4}", s): return dt.date(1899, 12, 30) + dt.timedelta(days=int(s))
        return None

    def matrice(a, dal=None):
        """{giorno: [24 valori 0..10 o None]} per i giorni conosciuti fra il primo sul disco (o il 27/10) e la lettura."""
        if not a["primo"]: return {}
        primo = dt.datetime.strptime(a["primo"], "%Y-%m-%d %H:%M")
        letto = locale(a["letto_il"])
        o = ORE.get((a["uid"], a["canale"]), {})
        g = a["giorni"] or {}
        out = {}
        d = max(DAL, primo.date(), dal or DAL)
        if dal and dal > primo.date(): primo = dt.datetime(dal.year, dal.month, dal.day) - dt.timedelta(hours=1)
        while d <= letto.date():
            iso = d.isoformat()
            if iso in o:
                v = [VAL.get(c) for c in o[iso]]
            elif iso in g:
                if g[iso] is None: v = [None] * 24
                elif g[iso] == 0: v = [0] * 24
                elif g[iso] >= 1438: v = [10] * 24
                else: v = None   # solo il totale
            else:
                v = [0] * 24   # il registratore dice: niente quel giorno
            if v is not None:
                v = list(v)
                if d == primo.date():
                    for x in range(0, primo.hour + 1): v[x] = None
                if d == letto.date():
                    for x in range(max(0, letto.hour - 1), 24): v[x] = None
                if any(x is not None for x in v): out[iso] = v
            d += dt.timedelta(days=1)
        return out

    GIORNO = range(8, 16)          # luce piena (alba ~7, tramonto ~17 fra il 27/10 e il 14/11)
    NOTTE = list(range(18, 24)) + list(range(0, 6))

    def corse(serie):
        """serie: lista di (giorno, ora, acceso bool) in ordine; i tratti spenti (>=2 ore, <=30 ore) con ora d'inizio e di fine."""
        out, ini, n = [], None, 0
        prec = None
        for g, o, on in serie:
            if on is None:
                ini = None; n = 0; prec = None; continue
            if not on:
                if ini is None: ini = (g, o)
                n += 1
            else:
                if ini is not None and n >= 2: out.append((ini[1], o, n, ini[0], g))
                ini, n = None, 0
        return out

    def profilo(m):
        num, den = [0] * 24, [0] * 24
        for v in m.values():
            for o, x in enumerate(v):
                if x is None: continue
                den[o] += 1; num[o] += x >= 5
        return [num[o] / den[o] if den[o] else None for o in range(24)]

    def frazione(m, ore=range(24)):
        n = t = 0
        for v in m.values():
            for o in ore:
                if v[o] is None: continue
                t += 1; n += v[o] >= 5
        return n / t if t else None

    def classifica(m):
        if not m: return "nessun dato", {}
        f = frazione(m); fg = frazione(m, GIORNO); fn = frazione(m, NOTTE)
        giorni = sorted(m)
        tot = {g: sum(1 for x in m[g] if x is not None and x >= 5) / max(1, sum(1 for x in m[g] if x is not None)) for g in giorni}
        pieni = sum(1 for g in giorni if tot[g] >= .95); vuoti = sum(1 for g in giorni if tot[g] <= .02)
        parz = sum(1 for v in m.values() for x in v if x is not None and 1 <= x <= 8)
        noz = sum(1 for v in m.values() for x in v if x is not None and x >= 1)
        meta = len(giorni) // 2
        f1 = sum(tot[g] for g in giorni[:meta]) / max(1, meta) if meta else None
        f2 = sum(tot[g] for g in giorni[meta:]) / max(1, len(giorni) - meta)
        # ultimo giorno con qualcosa
        acc = [g for g in giorni if tot[g] > .02]
        ferma_dal = None
        if acc and acc[-1] < giorni[-1] and len([g for g in giorni if g > acc[-1]]) >= 2: ferma_dal = acc[-1]
        pr = profilo(m)
        fisse_off = [o for o in range(24) if pr[o] is not None and pr[o] <= .2]
        info = dict(f=f, giorno=fg, notte=fn, giorni=len(giorni), pieni=pieni, vuoti=vuoti, parziali=parz / noz if noz else 0,
                    prima=f1, dopo=f2, ferma_dal=ferma_dal, ore_off=fisse_off, profilo=pr, dal=giorni[0], al=giorni[-1])
        if f >= .97: c = "sempre verde"
        elif f <= .02: c = "sempre rossa"
        elif ferma_dal and f2 is not None and f2 < .25: c = "ferma dal " + ferma_dal
        elif fg is not None and fn is not None and fg >= .7 and fn <= .3: c = "solo di giorno"
        elif fg is not None and fn is not None and fn >= .7 and fg <= .3: c = "solo di notte"
        elif pieni + vuoti >= .8 * len(giorni) and vuoti >= 1 and pieni >= 1: c = "spenta a giorni interi"
        elif len(fisse_off) >= 2 and f >= .3: c = "buco a ore fisse"
        elif info["parziali"] >= .25: c = "a pezzi (movimento?)"
        else: c = "buchi sparsi"
        if f1 is not None and f2 is not None and f1 - f2 >= .3 and not c.startswith("ferma"): info["peggiora"] = True
        if f1 is not None and f2 is not None and f2 - f1 >= .3: info["migliora"] = True
        return c, info

    def fasce(ore):
        """[3,4,5,9] -> '03-06, 09-10'"""
        out, i = [], 0
        ore = sorted(ore)
        while i < len(ore):
            j = i
            while j + 1 < len(ore) and ore[j + 1] == ore[j] + 1: j += 1
            out.append(f"{ore[i]:02d}-{ore[j] + 1:02d}"); i = j + 1
        return ", ".join(out)

    RIS = []
    for uid, reg in REG.items():
        kn = kit_n(reg["nome"])
        an = ANA.get(kn) or {}
        canali = ARC.get(uid, {})
        e = reg.get("esito") or {}
        titoli = {c["numero"]: c.get("titolo", "") for c in e.get("canali", [])}
        tipi = {c["numero"]: c.get("registrato_oggi", "") for c in e.get("canali", [])}
        attese = n_tlc(an.get("N. TELECAMERE"))
        di = data_ana(an.get("Data installazione"))
        inizio = di + dt.timedelta(days=1) if di and di >= DAL else None   # 14/11: prima dell'installazione il kit era altrove
        cam = []
        for ch, a in sorted(canali.items()):
            m = matrice(a, inizio)
            ha = any(x and x > 0 for v in m.values() for x in v) or any((v or 0) > 0 for v in (a["giorni"] or {}).values())
            dentro = attese is not None and ch < attese
            if not ha and not dentro: continue   # canale vuoto, non una telecamera
            c, info = classifica(m)
            info["sensore"] = bool(re.search(r"sensore|moviment", tipi.get(ch, "")))
            info["titolo"] = titoli.get(ch, "")
            cam.append(dict(canale=ch, schema=c, **info, _m=m))
        # serie del kit: un'ora è accesa se almeno una telecamera di quelle che registrano ha registrato
        vive = [x for x in cam if x["schema"] != "sempre rossa" and x["_m"]]
        serie, sincr, sole = [], [0, 0], collections.Counter()
        if vive:
            giorni = sorted(set(g for x in vive for g in x["_m"]))
            for g in giorni:
                for o in range(24):
                    vals = [x["_m"][g][o] for x in vive if g in x["_m"] and x["_m"][g][o] is not None]
                    if not vals: serie.append((g, o, None)); continue
                    on = [v >= 5 for v in vals]
                    serie.append((g, o, any(on)))
                    if len(vals) >= 2 and not all(on):
                        sincr[0] += 1; sincr[1] += (not any(on))
            for x in vive:   # ore spente di una telecamera mentre il kit è acceso
                n = t = 0
                for g, o, kon in serie:
                    if kon and g in x["_m"] and x["_m"][g][o] is not None:
                        t += 1; n += x["_m"][g][o] < 5
                x["sola_off"] = n / t if t else 0
        kc = corse(serie)
        gtl = collections.OrderedDict()   # il giorno per giorno del kit: quota delle ore accese, una cifra (A = tutto)
        for g, o, on in serie:
            if on is None: continue
            x = gtl.setdefault(g, [0, 0]); x[0] += on; x[1] += 1
        tl = "".join("0123456789A"[round(10 * a / b)] for a, b in gtl.values())
        kfr = sum(1 for _, _, on in serie if on) / max(1, sum(1 for _, _, on in serie if on is not None)) if serie else None
        # profilo del kit
        kp = [0] * 24; kd = [0] * 24
        for g, o, on in serie:
            if on is None: continue
            kd[o] += 1; kp[o] += on
        kprof = [kp[o] / kd[o] if kd[o] else None for o in range(24)]
        # firma dei tratti spenti del kit
        fine_tramonto = sum(1 for a, b, n, *_ in kc if n <= 30 and 16 <= b <= 18 and (7 <= a <= 16))
        fine_mattina = sum(1 for a, b, n, *_ in kc if n <= 30 and 7 <= b <= 12 and (a >= 17 or a <= 6))
        primo = canali and next(iter(canali.values()))["primo"]
        letto = canali and next(iter(canali.values()))["letto_il"]
        disco = None
        if primo:
            p = dt.datetime.strptime(primo, "%Y-%m-%d %H:%M"); l = locale(letto)
            disco = (l - p).total_seconds() / 86400
        ultimo = canali and next(iter(canali.values()))["ultimo"]
        avanti = None
        if ultimo and letto:
            u = dt.datetime.strptime(ultimo, "%Y-%m-%d %H:%M"); l = locale(letto)
            avanti = (u - l).total_seconds() / 60
        inst = an.get("Data installazione", "")
        RIS.append(dict(
            uid=uid, kit=kn, nome=reg["nome"], gruppo=reg["gruppo"], modello=reg["modello"] or (e.get("registratore") or {}).get("modello", ""),
            risponde=reg["stato"], stato_ana=an.get("STATO", ""), comune=an.get("CLOUD", "") or reg["gruppo"], batt=an.get("BATT", ""),
            alim=alimentazione(an.get("BATT")), tlc_ana=an.get("N. TELECAMERE", ""), attese=attese, sat=n_sat(an.get("N. TELECAMERE")),
            versione=an.get("VERSIONE", ""), sim=an.get("SIM", ""), rut=(an.get("RUT tipo", "").split() or [""])[0].upper(),
            installato=inst, inizio=inizio.isoformat() if inizio else None, data_batt=an.get("POWER\ndata batt", ""), eccezione=an.get("ECCEZIONE", ""),
            odm=ODM.get(kn, []), sfocate=SFOC.get(kn, []), letto=letto, primo=primo, ultimo=ultimo, disco_giorni=disco, orologio_min=avanti,
            tl=tl, tl_dal=next(iter(gtl), None), kit_f=kfr, kit_profilo=kprof, kit_corse=kc, fine_tramonto=fine_tramonto, fine_mattina=fine_mattina,
            sincr=(sincr[1] / sincr[0]) if sincr[0] else None, sincr_n=sincr[0],
            camere=[{k: v for k, v in x.items() if k != "_m"} for x in cam]))

    json.dump(RIS, open(f"{D}/risultati.json", "w"), ensure_ascii=False, indent=0, default=str)
    print(len(RIS), "registratori;", sum(len(r["camere"]) for r in RIS), "telecamere")
    print(collections.Counter(c["schema"] if not c["schema"].startswith("ferma") else "ferma" for r in RIS for c in r["camere"]))

def diagnosi(D):
    """Secondo passo: la diagnosi per kit. Scrive <cartella>/schemi.json."""
    R = json.load(open(f"{D}/risultati.json"))
    ODMR = json.load(open(f"{D}/altri.json"))["ODM"]
    GIORNO = range(8, 16); NOTTE = list(range(18, 24)) + list(range(0, 6))

    def data_it(iso):
        return f"{iso[8:10]}/{iso[5:7]}"

    def dmy(s):
        m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None

    ODM = collections.defaultdict(list)   # dal 20/10/2026, aperti o chiusi
    for r in ODMR[1:]:
        r = r + [""] * (26 - len(r))
        k = re.sub(r"\D", "", r[2])
        a = dmy(r[5]); c = dmy(r[14])
        if not k: continue
        if not r[14].strip() or (c and c >= dt.date(2026, 10, 20)) or (a and a >= dt.date(2026, 10, 20)):
            ODM[int(k)].append(dict(aperto=r[5], tipo=r[6], stato=r[7], chiuso=r[14], note=re.sub(r"\s+", " ", r[15])[:160]))

    def alim_di(b):
        b = (b or "").lower()
        return "solare" if "solare" in b else "220V" if "220" in b else "Townet" if "townet" in b else "batteria" if re.search(r"\d+\s*ah", b) else "?"

    def media(p, ore):
        v = [p[o] for o in ore if p[o] is not None]
        return sum(v) / len(v) if v else None

    def fasce(ore):
        ore = sorted(ore); out, i = [], 0
        while i < len(ore):
            j = i
            while j + 1 < len(ore) and ore[j + 1] == ore[j] + 1: j += 1
            out.append(f"{ore[i]:02d}-{ore[j] + 1:02d}"); i = j + 1
        return ", ".join(out)

    # un registratore per kit: quello con le ore, se no quello che risponde
    per_kit = {}
    for r in R:
        if r["kit"] is None: continue
        k = r["kit"]
        voto = (r["kit_f"] is not None, r["risponde"] == "fatto", bool(r["camere"]))
        if k not in per_kit or voto > per_kit[k][0]: per_kit[k] = (voto, r)
    altri = [r for r in R if r["kit"] is None and r["camere"]]

    righe, conti = [], collections.Counter()
    for k, (_, r) in sorted(per_kit.items()):
        if r["stato_ana"] != "INSTALLATO":
            conti["fuori: non INSTALLATO in anagrafica"] += 1; continue
        al = r["alim"]; riga = dict(kit=k, comune=r["comune"], indirizzo=re.sub(r"^\s*\d+\s*-\s*", "", r["nome"])[:40], alim=al,
                                    batt=r["batt"], modello=r["modello"], tlc=r["tlc_ana"], risponde=r["risponde"] == "fatto",
                                    disco=round(r["disco_giorni"]) if r["disco_giorni"] else None, odm=ODM.get(k, []),
                                    sfocate=r["sfocate"], installato=r["installato"], data_batt=r["data_batt"])
        cams = r["camere"]
        if r["kit_f"] is None and r["risponde"] == "fatto":
            riga.update(gruppo="H. risponde ma senza ore lette (o installato da poco)", schema="-", causa="", certezza="-", fare="niente per ora", tl="")
            righe.append(riga); continue
        if r["kit_f"] is None:
            riga.update(gruppo="N. non risponde, ore mai lette", schema="-", causa=(
                "kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router" if al == "solare"
                else "spento o senza rete: dalle ore non si può dire"), certezza="-",
                fare="da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto", tl="")
            righe.append(riga); continue
        tl = r["tl"]
        p = r["kit_profilo"]; Kd = media(p, GIORNO); Kn = media(p, NOTTE); K = r["kit_f"]
        riga.update(K=round(K * 100), Kd=round(Kd * 100) if Kd is not None else None, Kn=round(Kn * 100) if Kn is not None else None,
                    tl=tl, dal=r["tl_dal"])
        corte = [(a, b, n, g0, g1) for a, b, n, g0, g1 in r["kit_corse"] if n <= 30]
        lunghe = [(a, b, n, g0, g1) for a, b, n, g0, g1 in r["kit_corse"] if n > 30]
        lamp = [(a, b, n, g0, g1) for a, b, n, g0, g1 in corte if 7 <= a <= 16 and 16 <= b <= 18]
        notte = [(a, b, n, g0, g1) for a, b, n, g0, g1 in corte if (a >= 17 or a <= 6) and 7 <= b <= 13]
        giorni = max(1, len(tl))
        vuoti = sum(1 for c in tl if c in "0123")
        ultimi_ok = tl[-3:] and all(c in "9A" for c in tl[-3:-1] or tl[-1:])
        if K >= .97:
            riga.update(gruppo="OK", schema="sempre verde", causa="", certezza="", fare="niente")
        elif Kn is not None and Kd is not None and Kn >= .85 and Kn - Kd >= .1 and len(lamp) >= 2:
            aut = stt.median([a - 7 for a, *_ in lamp])
            ogni = len(lamp) / giorni
            primo = min(g0 for *_, g0, _ in lamp)
            riga.update(gruppo="A. si spegne di giorno, riparte al tramonto", schema=(
                f"di notte sempre; di giorno {round(Kd * 100)}%: si spegne verso le {7 + aut:.0f} e riparte alle 16-17, "
                f"{len(lamp)} giorni su {giorni} (dal {data_it(primo)})"),
                causa=("pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno"
                       + (" (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica)" if aut <= 1 else
                          f" (regge circa {aut:.0f} ore dopo l'alba)")),
                certezza="alta" if al == "batteria" else "media (in anagrafica non è a batteria)",
                fare="sul posto: batteria (e caricabatterie/power); se ogni giorno, subito" if ogni >= .5 else
                     "sul posto alla prossima occasione: batteria che sta cedendo")
            # l'ultimo giorno intero è il penultimo (l'ultimo è letto a metà, di solito solo la notte)
            ultimo = max(g0 for *_, g0, _ in lamp)
            fine = (dt.date.fromisoformat(r["tl_dal"]) + dt.timedelta(days=len(tl) - 2)).isoformat()
            db = dmy(r["data_batt"])
            dopo = [x for x in lamp if db and x[3] > db.isoformat()]
            if db and db >= dt.date(2026, 10, 27) and len(dopo) >= 3:
                riga["causa"] = ("pubblica illuminazione: il lampione dà corrente solo di notte e il kit non regge il giorno; "
                                 f"la batteria è stata cambiata il {db:%d/%m} e si spegne ancora ({len(dopo)} giorni): non è (solo) la "
                                 "batteria, ma la carica (caricabatterie/power, fusibile o il collegamento alla pubblica)")
                riga["fare"] = "sul posto: caricabatterie/power, fusibile e collegamento alla pubblica (la batteria è già nuova)"
            elif db and db >= dt.date.fromisoformat(fine) - dt.timedelta(days=3):
                riga["causa"] += f"; la batteria è stata cambiata il {db:%d/%m}: troppo presto per dire se è bastato"
                riga["fare"] = "da remoto: ricontrollare fra qualche giorno (batteria appena cambiata)"
            elif (dt.date.fromisoformat(fine) - dt.date.fromisoformat(ultimo)).days >= 4:
                riga["schema"] += f"; dal {data_it((dt.date.fromisoformat(ultimo) + dt.timedelta(days=1)).isoformat())} non succede più"
                riga["fare"] = "niente: è tornato a posto" + (f" (cambio del {db:%d/%m})" if db and db.isoformat() >= ultimo else "")
        elif al == "solare":
            quasi = vuoti >= .6 * giorni
            solo_sole = K < .15 and Kd is not None and Kn is not None and Kn <= .02 and Kd > .03
            riga.update(gruppo="B. solare: si spegne di notte o per giorni", quasi=quasi, schema=(
                (f"{vuoti} giorni spenti su {giorni}" if vuoti != 1 else f"1 giorno spento su {giorni}") + (f"; {len(notte) if len(notte) > 1 else 'una'} volt{'e' if len(notte) > 1 else 'a'} si spegne di sera o di notte e riparte la mattina" if notte else "")
                + ("; quando si accende è solo qualche ora di giorno" if solo_sole else "")),
                causa=("va solo quando il sole batte sul pannello: la batteria non tiene più (o non è collegata)" if solo_sole else
                       "quasi sempre spento: pannello in ombra o guasto, batteria o regolatore guasti" if quasi else
                       "il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi"),
                certezza="media",
                fare=("sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore" if quasi else
                      "sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello"))
        elif lunghe and ultimi_ok and tl and tl[-1] in "9A6789":
            a, b, n, g0, g1 = lunghe[-1]
            riga.update(gruppo="C. spento per giorni, poi ripartito", schema=(
                f"spento dal {data_it(g0)} alle {a:02d} al {data_it(g1)} alle {b:02d} ({n // 24 or 1} giorn{'i' if n // 24 > 1 else 'o'}); ora registra"),
                causa=("ripartito in orario di lavoro: probabilmente un intervento (riavvio o riparazione)" if 8 <= b <= 17 else
                       "ripartito da solo fuori orario: probabile ritorno della corrente"),
                certezza="media", fare="niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico")
            if lamp:
                riga["schema"] += f"; anche {len(lamp)} giorni spento di giorno"
        elif tl and all(c in "0123" for c in tl[-3:-1] or tl[-1:]):
            ult = max((i for i, c in enumerate(tl) if c not in "0123-"), default=None)
            dal = (dt.date.fromisoformat(riga["dal"]) + dt.timedelta(days=(ult or 0) + 1)).isoformat() if ult is not None else riga["dal"]
            riga.update(gruppo="D. fermo adesso", schema=f"non registra dal {data_it(dal)}",
                        causa="tutto il kit insieme: alimentazione o registratore", certezza="media",
                        fare="da remoto se risponde (riavvio); se no sul posto: alimentazione")
        elif lunghe:
            riga.update(gruppo="E. si spegne per giorni interi", schema=f"{vuoti} giorni spenti su {giorni}, a più riprese",
                        causa="tutto il kit insieme: alimentazione o registratore che si blocca; dalle ore non si distingue",
                        certezza="bassa", fare="sul posto: alimentazione e registratore")
        else:
            off = [o for o in range(24) if p[o] is not None and p[o] < .85]
            riga.update(gruppo="F. buchi sparsi", schema=f"{round(K * 100)}% delle ore; buchi soprattutto {fasce(off) or 'sparsi'}",
                        causa="non c'è uno schema chiaro", certezza="bassa", fare="da guardare")
        # le telecamere che sbagliano da sole (il kit registra, loro no)
        att = r["attese"]; vive = [c for c in cams if c["schema"] not in ("sempre rossa", "nessun dato")]
        note = []
        for c in cams:
            nome = f"CH{c['canale'] + 1}"
            if c["schema"] in ("sempre rossa", "nessun dato"): continue
            so = c.get("sola_off") or 0
            if so < .15: continue
            sat = r["sat"] and att and c["canale"] >= att - r["sat"]
            pr = c["profilo"]; dg = media(pr, GIORNO); dn = media(pr, NOTTE)
            if c["schema"].startswith("ferma"):
                t = f"{nome} ferma dal {data_it(c['ferma_dal'])}"
            elif dg is not None and dn is not None and dg - dn >= .5: t = f"{nome} registra solo di giorno"
            elif dg is not None and dn is not None and dn - dg >= .5: t = f"{nome} registra solo di notte"
            else: t = f"{nome} spenta {round(so * 100)}% delle ore in cui il kit registra"
            note.append(t + (" (forse il satellite)" if sat else ""))
        manca = (att - len(vive)) if att else 0
        if manca > 0 and riga["gruppo"] != "N. non risponde, ore mai lette":
            rosse = [f"CH{c['canale'] + 1}" for c in cams if c["schema"] == "sempre rossa"]
            note.append(f"{manca} telecamera{'e' if manca > 1 else ''} su {att} mai registrata dal 27/10"
                        + (f" ({', '.join(rosse)})" if rosse else "") + (" (forse il satellite)" if r["sat"] else ""))
        riga["telecamere"] = "; ".join(note)
        if note and riga["gruppo"] == "OK":
            riga.update(gruppo="G. kit acceso, una telecamera no", schema=riga["telecamere"],
                        causa="una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio",
                        certezza="media", fare="da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite")
        righe.append(riga)

    ANA = json.load(open(f"{D}/anagrafica.json")); h = ANA[0]
    for x in ANA[1:]:
        x = dict(zip(h, x + [""] * (len(h) - len(x))))
        k = re.sub(r"\D", "", x["KIT"])
        if x["STATO"].strip() != "INSTALLATO" or not k or int(k) in per_kit: continue
        conti["installati senza registratore in UVMS"] += 1
        righe.append(dict(kit=int(k), comune=x["CLOUD"], indirizzo=x["INDIRIZZO"][:40], alim=alim_di(x["BATT"]),
                          batt=x["BATT"], modello="", tlc=x["N. TELECAMERE"], risponde=False, disco=None, odm=ODM.get(int(k), []),
                          sfocate=[], installato=x["Data installazione"], data_batt="", gruppo="M. nessun registratore in UVMS",
                          schema="-", causa="non è nell'elenco dei registratori letto da UVMS", certezza="-", fare="controllare UVMS", tl="", telecamere=""))
    # 0.1.0: i solari spenti negli stessi giorni di altri solari della stessa regione: è il tempo, non il singolo kit
    REG = {}
    for x in ANA[1:]:
        x = dict(zip(h, x + [""] * (len(h) - len(x))))
        k = re.sub(r"\D", "", x["KIT"])
        if k and x["STATO"].strip() == "INSTALLATO": REG[int(k)] = x["REGIONE"].strip().upper()
    def spenti(riga):
        d0 = dt.date.fromisoformat(riga["dal"])
        return {(d0 + dt.timedelta(days=i)).isoformat() for i, c in enumerate(riga["tl"][:-1]) if c in "0123"}
    sol = [x for x in righe if x.get("tl") and x["alim"] == "solare" and x.get("dal")]
    for x in sol:
        if not x["gruppo"].startswith("B.") or x.get("quasi"): continue
        mie = spenti(x); altri_z = [y for y in sol if y is not x and REG.get(y["kit"]) == REG.get(x["kit"])]
        if not mie or len(altri_z) < 2: continue
        insieme = [g for g in mie if sum(g in spenti(y) for y in altri_z) >= 2]
        if len(insieme) >= .5 * len(mie):
            x["schema"] += f"; {len(insieme)} di questi giorni spenti anche altri solari della stessa regione"
            x["causa"] += " (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit)"
            x["insieme"] = True
    righe.sort(key=lambda x: x["kit"])
    # i conti delle ipotesi: quanti kit le sostengono e quanti le contraddicono
    G = {x["kit"]: x for x in righe}
    con_ore = [r for r in per_kit.values() if r[1]["kit_f"] is not None and r[1]["stato_ana"] == "INSTALLATO"]
    con_ore = [r for _, r in con_ore]
    ip = {}
    ip["per_alimentazione"] = {a: dict(installati=sum(1 for x in righe if x["alim"] == a and x["gruppo"] != "fuori"),
                                       **collections.Counter(x["gruppo"][0] for x in righe if x["alim"] == a))
                               for a in sorted({x["alim"] for x in righe})}
    ore_fine = collections.defaultdict(collections.Counter); ore_ini = collections.defaultdict(collections.Counter)
    for r in con_ore:
        for a, b, n, *_ in r["kit_corse"]:
            if n <= 30: ore_ini[r["alim"]][a] += 1; ore_fine[r["alim"]][b] += 1
    ip["tratti_spenti_brevi"] = {a: dict(inizio=dict(sorted(ore_ini[a].items())), fine=dict(sorted(ore_fine[a].items()))) for a in ore_ini}
    n = s1 = 0
    for r in con_ore:
        if r["sincr_n"]: n += r["sincr_n"]; s1 += r["sincr"] * r["sincr_n"]
    ip["ore_con_una_telecamera_spenta"] = n; ip["di_cui_tutto_il_kit"] = round(s1)
    pos = collections.Counter(); pb = collections.Counter()
    for r in con_ore:
        att, sat = r["attese"], r["sat"]
        if not att: continue
        vive = [c for c in r["camere"] if c["schema"] not in ("sempre rossa", "nessun dato")]
        for c in r["camere"]:
            if c["canale"] >= att: continue
            t = ("satellite" if c["canale"] >= att - sat else "via cavo, kit col satellite") if sat else "via cavo, kit senza satellite"
            pos[t] += 1
            if c["schema"] not in ("sempre rossa", "nessun dato") and (c.get("sola_off") or 0) >= .15: pb[t] += 1
        pb["mancanti in kit " + ("col satellite" if sat else "senza satellite")] += max(0, att - len(vive))
    ip["telecamere_per_posto"] = dict(pos); ip["problemi_da_sole"] = dict(pb)
    sens = [c for r in con_ore for c in r["camere"] if c["sensore"] and c.get("f") is not None]
    ip["telecamere_a_sensore"] = dict(tutte=len(sens), sempre_verdi=sum(1 for c in sens if c["schema"] == "sempre verde"))
    dg = [r["disco_giorni"] for r in con_ore if r["disco_giorni"] and r["primo"] > "2026-10-27"]
    ip["disco"] = dict(kit=len(dg), mediana_giorni=round(stt.median(dg), 1) if dg else None, sotto_10_giorni=sum(1 for x in dg if x < 10))
    ip["orologio_avanti_oltre_10_min"] = sum(1 for r in con_ore if r["orologio_min"] and r["orologio_min"] > 10)
    sf = [x for x in righe if x.get("sfocate")]
    ip["kit_con_telecamere_sfocate"] = dict(tutti=len(sf), che_registrano_bene=sum(1 for x in sf if x["gruppo"] == "OK"))
    json.dump(dict(ipotesi=ip, righe=righe, altri=[dict(nome=a["nome"], gruppo=a["gruppo"], K=a["kit_f"]) for a in altri], conti=conti),
              open(f"{D}/schemi.json", "w"), ensure_ascii=False, indent=1)
    print(collections.Counter(x["gruppo"] for x in righe))
    print(conti)

if __name__ == "__main__":
    D = sys.argv[1]
    if "--scarica" in sys.argv: scarica(sys.argv[sys.argv.index("--scarica") + 1], D)
    analizza(D)
    diagnosi(D)
    S = json.load(open(f"{D}/schemi.json"))
    campi = ("kit", "comune", "indirizzo", "alim", "batt", "modello", "tlc", "gruppo", "schema", "causa", "certezza", "fare",
             "telecamere", "tl", "dal", "K", "Kd", "Kn", "disco", "installato")
    out = dict(versione="0.1.0", fatto_il=dt.date.today().isoformat(), ipotesi=S.get("ipotesi", {}),
               righe=[{k: x.get(k) for k in campi} | {"odm": len(x.get("odm") or []), "sfocate": ", ".join(x.get("sfocate") or [])}
                      for x in S["righe"]])
    qui = os.path.dirname(os.path.abspath(__file__))
    json.dump(out, open(os.path.join(qui, "schemi_ore.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("dati/schemi_ore.json:", len(out["righe"]), "kit")
