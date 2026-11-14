"""La scorta serale e la catena dell'ora con Qwen (compito 35, ponte p2p 0.18.0). Dario, 12/11 sera: «vale la pena
continuare a scaricare ore per future prove?» (si': il disco dei registratori gira in circa 20 giorni) e il traffico
delle SIM non si paga a consumo, ma con un tetto prudente per kit e per notte. Analisi-abbandono-in-un-ora.md, 8b:
«mettere Qwen dentro la catena dell'ora (miniature -> insieme -> pezzi a piena risoluzione -> Qwen) e riprovare sulle
ore nuove della scorta serale».

Per ogni ora di scorta.json (prepara_scorta.py), in un processo suo (scorta_lavoro.py, come pilota_lavoro.py):
  A) la scorta: le 72 miniature dei minuti (pilota.py con solo_minuti) e, per ogni abbandono dell'ora, il video a piena
     risoluzione sulla sua telecamera (di difetto da 30 s prima a 60 s dopo; allunga.scarica_tratto: mp4 continui col
     nome dell'ora vera). Tutto resta sul PC nella cartella della scorta; nell'uscita del compito solo ora.json, due
     fotogrammi per abbandono (20 s prima e 45 s dopo, 800 pixel) e il foglio dei fotogrammi del video.
  B) la catena, se l'ora e' della catena: b_tavolino «insieme» (soglie congelate) sulle miniature appena salvate, i primi
     3 candidati diventano pezzi a piena risoluzione (da 12 s prima del minuto in cui il pezzo non c'era a 30 s dopo il
     minuto in cui c'e'; i pezzi che si toccano si uniscono) e per ogni candidato la carta di Qwen come nel compito 34:
     il fotogramma 3 s prima del minuto «prima» e quello 25 s dopo il minuto della comparsa, ritagliati intorno al
     riquadro, e la scena intera dopo col riquadro rosso (domanda v3 di vlm_giudica.py). La verita' (l'abbandono noto
     dell'ora e gli altri noti) si scrive accanto a ogni candidato, ma il metodo non la vede.
Nel ponte (compito.py, lavoro_scorta): le ore si fanno solo nella finestra serale (di difetto 19-7) e al massimo per
«ore_di_lavoro» ore; un tetto di MB per kit (un'ora che lo passerebbe salta la catena, poi anche la scorta) e uno in
tutto. Le miniature vanno su Drive in zip da al massimo «mb_parte_drive» MB (i segnaposto scorta35_N.zip). Alla fine
Qwen giudica tutte le carte (vlm.py, staccato) e catena.json unisce ore, candidati, giudizi e verita'.
Il lavoro vero (registratore, ffmpeg, kit_rifiuti) arriva da fuori: prove a tavolino in prova_scorta.py.
version: 0.1.0 (14/11/2026): prima versione.
"""
import datetime
import json
import os
import re
import time

VERSIONE = "0.1.0"

LIMITI = {"ore_di_lavoro": 11.0,      # poi le ore dopo non si fanno (si scrive)
          "minuti_per_ora": 20.0,     # poi il processo dell'ora si uccide
          "mb_per_kit": 1000.0,       # MB dal registratore per kit in tutto il compito: oltre, niente piu' ore del kit
          "mb_in_tutto": 30000.0,     # MB dal registratore in tutto
          "mb_parte_drive": 180.0,    # uno zip delle miniature su Drive (mai sopra 200 MB: il 32 e' arrivato rovinato)
          "ritenta_errore_memoria": 1}
FINESTRA = {"dalle": "19:00", "alle": "07:00"}
CATENA = {"variante": "insieme", "opzioni": {"memoria": 30, "solo_fino": True, "mosso_max": 4.0, "area_max": 0.0075},
          "candidati": 3, "prima_s": 12, "dopo_s": 30, "carta_prima_s": -3, "carta_dopo_s": 25,
          "qwen": [["Qwen/Qwen3-VL-4B-Instruct", "nf4", "v3", "c35"]]}
VIDEO_FOTO_S = (-20, 45)      # i due fotogrammi di ogni abbandono, in secondi dall'atteso
MB_CATENA_STIMA = 130.0       # 3 pezzi da ~100 s a piena risoluzione (compito 33: 57 MB per 150 s)
MB_VIDEO_STIMA = 40.0         # 90 s di una telecamera
CODICI = {3221225477: "errore di memoria della libreria (0xC0000005)", 1: "errore in Python (vedi registro)",
          3: "una chiamata alla libreria non e' tornata in tempo: il processo si e' chiuso da solo"}
MEMORIA = 3221225477
RISPOSTE_V3 = ("waste", "vehicle", "person", "shadow", "bin", "already", "nothing", "unclear")


def limiti_da(cfg):
    """LIMITI abbassati (mai alzati) da cfg["limiti"]."""
    lim = dict(LIMITI)
    for k, v in ((cfg or {}).get("limiti") or {}).items():
        if k in lim and isinstance(v, (int, float)) and 0 <= v < lim[k]:
            lim[k] = type(lim[k])(v)
    return lim


def catena_da(cfg):
    c = dict(CATENA)
    c.update({k: v for k, v in ((cfg or {}).get("catena") or {}).items() if k in CATENA})
    return c


def esito_processo(codice):
    if codice == 0:
        return "finito"
    if isinstance(codice, str):
        return codice
    return CODICI.get(codice, f"uscito con il codice {codice}")


# ------------------------------------------------------------------ funzioni pure: tempi

def dt(s):
    return datetime.datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S")


def hms(t):
    return t.strftime("%Y-%m-%d %H:%M:%S") if t else None


def minuti_di(hhmm):
    h, m = str(hhmm).split(":")
    return int(h) * 60 + int(m)


def in_finestra(t, dalle, alle):
    """t (datetime) e' dentro la finestra [dalle, alle) ("19:00", "07:00"; puo' passare la mezzanotte)?"""
    m, a, b = t.hour * 60 + t.minute, minuti_di(dalle), minuti_di(alle)
    return a <= m < b if a < b else (m >= a or m < b)


def secondi_alla_finestra(t, dalle, alle):
    """Quanti secondi mancano all'apertura della finestra (0 se e' gia' aperta)."""
    if in_finestra(t, dalle, alle):
        return 0
    a = t.replace(hour=minuti_di(dalle) // 60, minute=minuti_di(dalle) % 60, second=0, microsecond=0)
    if a <= t:
        a += datetime.timedelta(days=1)
    return int((a - t).total_seconds())


def coda(ore):
    """L'ordine: le positive come vengono (prepara_scorta le mette per urgenza: prima quelle che il disco perde prima),
    dopo ogni positiva della catena una negativa, cosi' se la notte finisce la misura ha tutte e due le popolazioni; le
    negative avanzate in fondo."""
    pos = [o for o in ore if o.get("tipo") == "positiva"]
    neg = [o for o in ore if o.get("tipo") == "negativa"]
    out = []
    for o in pos:
        out.append(o)
        if o.get("catena") and neg:
            out.append(neg.pop(0))
    return out + neg


def finestre(candidati, prima_s, dopo_s):
    """[(da, a, [ranghi])] dei pezzi da scaricare per i candidati (gia' in classifica, rango da 1): da prima_s secondi
    prima del minuto «prima» a dopo_s dopo il minuto della comparsa; i pezzi che si toccano diventano uno."""
    righe = sorted((c["comparsa_prima"] - datetime.timedelta(seconds=prima_s),
                    c["comparsa"] + datetime.timedelta(seconds=dopo_s), k) for k, c in enumerate(candidati, 1))
    out = []
    for a, b, k in righe:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
            out[-1][2].append(k)
        else:
            out.append([a, b, [k]])
    return [(a, b, sorted(k)) for a, b, k in out]


def tempi_carta(c, carta_prima_s, carta_dopo_s):
    """I due momenti della carta di un candidato: (prima, dopo) = minuto «prima» + carta_prima_s, comparsa +
    carta_dopo_s (come prepara_vlm33.py: -3 s e +25 s)."""
    return (c["comparsa_prima"] + datetime.timedelta(seconds=carta_prima_s),
            c["comparsa"] + datetime.timedelta(seconds=carta_dopo_s))


def pezzo_per(t, pezzi, tolleranza_s=1.0):
    """Il pezzo [(inizio, fine, file)] che contiene t (con tolleranza ai bordi) e i secondi dal suo inizio; il piu'
    vicino se nessuno lo contiene ma uno ci arriva entro la tolleranza. (None, None) se non c'e'."""
    tol = datetime.timedelta(seconds=tolleranza_s)
    for a, b, f in pezzi:
        if a - tol <= t <= b + tol:
            s = (min(max(t, a), b) - a).total_seconds()
            return f, round(s, 2)
    return None, None


def quadro_carta(h, w, box):
    """Il ritaglio della carta (come carte_dai_pezzi del 34: lato 3 volte il riquadro, almeno il 18% del lato corto,
    centrato) e il riquadro rosso in pixel: ((x0, y0, x1, y1), (rx0, ry0, rx1, ry1))."""
    x, y, bw, bh = box
    cx, cy = (x + bw / 2) * w, (y + bh / 2) * h
    lato = max(3 * bw * w, 3 * bh * h, 0.18 * min(w, h))
    x0, y0 = int(max(0, cx - lato / 2)), int(max(0, cy - lato / 2))
    x1, y1 = int(min(w, cx + lato / 2)), int(min(h, cy + lato / 2))
    return (x0, y0, x1, y1), (int(x * w), int(y * h), int((x + bw) * w), int((y + bh) * h))


def iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0.0, min(ax2, bx2) - max(a[0], b[0])), max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def verita(c, ora, iou_min=0.1, margine_s=90):
    """La verita' di un candidato (il metodo non la vede): «vero» = e' l'abbandono noto dell'ora (b_tavolino.trovato:
    tocca il riquadro e il momento torna, con margine_s); «tocca_vero» = tocca il riquadro a qualunque ora;
    «altro_noto» = tocca un altro abbandono noto dell'ora (allora non e' un falso, come in misura_b_tavolino 0.2.0)."""
    if ora.get("tipo") != "positiva" or not ora.get("box_dario"):
        return {"vero": False, "tocca_vero": False, "altro_noto": False}
    at, bd = dt(ora["atteso"]), ora["box_dario"]
    tocca = iou(c["box"], bd) >= iou_min
    vero = bool(tocca and c["comparsa_prima"] - datetime.timedelta(seconds=margine_s) <= at
                <= c["comparsa"] + datetime.timedelta(seconds=margine_s))
    altri = [n["box"] for n in ora.get("altri_noti") or [] if n.get("box")]
    altri += [e["box"] for e in ora.get("eventi") or [] if e.get("evento") != ora.get("evento") and e.get("box")]
    altro = (not tocca) and any(iou(c["box"], b) >= iou_min for b in altri)
    return {"vero": vero, "tocca_vero": tocca, "altro_noto": altro}


def gruppi_zip(voci, tetto_mb):
    """voci: [(nome, mb)] in ordine. Gruppi consecutivi con la somma sotto tetto_mb (una voce piu' grande da sola sta
    in un gruppo suo). [[nomi]]."""
    out, cur, s = [], [], 0.0
    for nome, mb in voci:
        if cur and s + mb > tetto_mb:
            out.append(cur)
            cur, s = [], 0.0
        cur.append(nome)
        s += mb
    if cur:
        out.append(cur)
    return out


def tetto(ora, mb_kit, mb_tutto, lim):
    """Cosa si fa di un'ora con i MB gia' presi dal suo kit e in tutto: "tutto", "senza_catena" (la catena passerebbe il
    tetto del kit) o "niente" (con il perche'). Ritorna (cosa, perche')."""
    stima_scorta = 3.5 + MB_VIDEO_STIMA * len(ora.get("video") or [])
    if mb_tutto + stima_scorta > lim["mb_in_tutto"]:
        return "niente", f"tetto in tutto ({lim['mb_in_tutto']:g} MB)"
    if mb_kit + stima_scorta > lim["mb_per_kit"]:
        return "niente", f"tetto del kit ({lim['mb_per_kit']:g} MB, presi {mb_kit:.0f})"
    if ora.get("catena") and (mb_kit + stima_scorta + MB_CATENA_STIMA > lim["mb_per_kit"]
                              or mb_tutto + stima_scorta + MB_CATENA_STIMA > lim["mb_in_tutto"]):
        return "senza_catena", "la catena passerebbe il tetto"
    return "tutto", ""


def risposta_qwen(g):
    """La risposta v3 di un giudizio di vlm_giudica: dal json nel testo (leggi() di vlm_giudica non conosce «already» e
    la cerca nelle parole), se no dalla risposta ripassata in italiano."""
    m = re.search(r"\{.*\}", str(g.get("testo") or ""), re.S)
    if m:
        try:
            r = str(json.loads(m.group(0)).get("risposta", "")).strip().lower()
            if r in RISPOSTE_V3:
                return r
        except ValueError:
            pass
        r = re.search(r'"risposta"\s*:\s*"([a-z_]+)"', m.group(0))
        if r and r.group(1) in RISPOSTE_V3:
            return r.group(1)
    return {"giusto": "waste", "riquadro": "waste", "veicolo": "vehicle", "persona": "person", "ombra": "shadow",
            "cassonetto": "bin", "niente": "nothing", "non_si_capisce": "unclear"}.get(g.get("risposta"), "unclear")


def unisci_giudizi(ore, giudizi):
    """ore: i dict delle ore (ora.json); giudizi: [{"id", "risposta", "testo", ...}] di Qwen. Ad ogni carta di ogni ora
    aggiunge «qwen» (risposta v3, sicuro, prima, dopo) e «tiene» (Qwen dice waste). Ritorna quante carte giudicate."""
    per = {g["id"]: g for g in giudizi or []}
    n = 0
    for x in ore:
        for c in ((x.get("catena") or {}).get("candidati") or []):
            g = per.get(c.get("carta"))
            if not g:
                continue
            r = risposta_qwen(g)
            testo = {}
            m = re.search(r"\{.*\}", str(g.get("testo") or ""), re.S)
            if m:
                try:
                    testo = json.loads(m.group(0))
                except ValueError:
                    testo = {}
            c["qwen"] = {"risposta": r, "sicuro": bool(g.get("sicuro")), "prima": str(testo.get("prima", ""))[:80],
                         "dopo": str(testo.get("dopo", ""))[:80], "secondi": g.get("secondi")}
            c["tiene"] = r == "waste"
            n += 1
    return n


def conti_catena(ore, quanti=3):
    """Il riassunto della catena (le misure vere le fa Dario dai dati): ore valutabili per tipo; per le positive dove
    e' l'abbandono fra i candidati prima di Qwen e fra quelli che Qwen tiene; falsi all'ora fra i primi `quanti`,
    prima e dopo Qwen (un falso = ne' vero ne' altro noto). Le ore «viste» (pilota, prova grande) anche a parte."""
    def vuoto():
        return {"ore": 0, "primo": 0, "nei_primi": 0, "primo_dopo_qwen": 0, "nei_primi_dopo_qwen": 0, "falsi": 0,
                "falsi_dopo_qwen": 0, "senza_giudizio": 0}
    tot = {"positive": vuoto(), "negative": vuoto(), "positive_mai_viste": vuoto()}
    for x in ore:
        cat = x.get("catena") or {}
        if not cat.get("fatta"):
            continue
        cand = (cat.get("candidati") or [])[:quanti]
        dove = [tot["positive" if x.get("tipo") == "positiva" else "negative"]]
        if x.get("tipo") == "positiva" and not x.get("vista"):
            dove.append(tot["positive_mai_viste"])
        tenuti = [c for c in cand if c.get("tiene")]
        for d in dove:
            d["ore"] += 1
            d["senza_giudizio"] += sum(1 for c in cand if "qwen" not in c)
            d["falsi"] += sum(1 for c in cand if not c.get("vero") and not c.get("altro_noto"))
            d["falsi_dopo_qwen"] += sum(1 for c in tenuti if not c.get("vero") and not c.get("altro_noto"))
            if x.get("tipo") == "positiva":
                d["primo"] += bool(cand and cand[0].get("vero"))
                d["nei_primi"] += any(c.get("vero") for c in cand)
                d["primo_dopo_qwen"] += bool(tenuti and tenuti[0].get("vero"))
                d["nei_primi_dopo_qwen"] += any(c.get("vero") for c in tenuti)
    for d in tot.values():
        n = d["ore"] or 1
        d["falsi_all_ora"] = round(d["falsi"] / n, 2)
        d["falsi_all_ora_dopo_qwen"] = round(d["falsi_dopo_qwen"] / n, 2)
    return tot


# ------------------------------------------------------------------ il giro di tutte le ore (nel ponte)

def giro(cfg, lancia, manda_parte, mb_minuti, scrivi_out, av=lambda t: None, adesso=datetime.datetime.now,
         orologio=time.time, dorme=time.sleep, perche_chiudere=lambda: None, gb_liberi=lambda: 999.0, gia=None,
         prima=None):
    """Tutte le ore di scorta.json, una alla volta, nell'ordine di coda(). lancia(ora, secondi_max) -> (codice, dict
    dell'ora o None); manda_parte(ore, k) -> la voce della parte k (uno zip delle miniature di quelle ore su Drive);
    mb_minuti(nome) -> MB delle miniature di quell'ora sul PC (0 se non ci sono); perche_chiudere() -> None o il motivo
    per non aspettare piu' la finestra (il ponte che chiude, un compito nuovo su Drive); gb_liberi() -> GB liberi sul
    disco del PC. Fuori dalla finestra si aspetta; si smette dopo ore_di_lavoro ore di lavoro (contate solo mentre
    un'ora gira), col disco sotto gb_liberi_min o quando perche_chiudere() dice qualcosa. Il tetto di MB per kit e in
    tutto decide ora per ora (tetto()). gia: {nome: dict} delle ore gia' finite (ripresa del compito: non si rifanno);
    prima: lo scorta.json della volta prima (le parti gia' mandate). Ritorna out (scritto anche man mano)."""
    lim = limiti_da(cfg)
    fin = dict(FINESTRA, **(cfg.get("finestra") or {}))
    gb_min = float(cfg.get("gb_liberi_min", 15))
    gia, prima = gia or {}, prima or {}
    out = {"scorta": VERSIONE, "limiti": lim, "finestra": fin, "inizio": hms(adesso()), "ore": [],
           "parti": [p for p in prima.get("parti") or [] if p.get("ok") or p.get("zip_sul_pc")]}
    in_zip = {o for p in out["parti"] for o in p.get("ore") or []}
    st = {"da_zip": [], "mb_kit": {}, "mb_tutto": 0.0, "lavorato": float(prima.get("secondi_di_lavoro") or 0)}

    def scrivi():
        out["secondi_di_lavoro"] = round(st["lavorato"])
        out["mb_in_tutto"] = round(st["mb_tutto"], 1)
        out["mb_per_kit"] = {str(k): round(v, 1) for k, v in sorted(st["mb_kit"].items())}
        scrivi_out(out)

    def zip_pronti(tutti=False):
        gruppi = gruppi_zip([(o, mb_minuti(o)) for o in st["da_zip"]], lim["mb_parte_drive"] * 0.97)
        for g in (gruppi if tutti else gruppi[:-1]):
            k = len(out["parti"]) + 1
            try:
                voce = manda_parte(g, k)
            except Exception as ex:   # noqa: BLE001
                voce = {"parte": k, "ok": False, "ore": g, "drive": f"{type(ex).__name__}: {str(ex)[:200]}"}
            out["parti"].append(voce)
            av(f"scorta: parte {k} ({voce.get('mb')} MB, {len(g)} ore): {voce.get('drive')}")
            st["da_zip"] = [o for o in st["da_zip"] if o not in g]
        scrivi()

    q = coda(cfg.get("ore") or [])
    rifatte = {}
    while q:
        ora = q.pop(0)
        if ora["nome"] in gia:
            x = dict(gia[ora["nome"]], ripreso="finita prima della ripresa del compito")
        else:
            perche = None
            while not perche and not in_finestra(adesso(), fin["dalle"], fin["alle"]):
                perche = perche_chiudere()
                if not perche:
                    attesa = secondi_alla_finestra(adesso(), fin["dalle"], fin["alle"])
                    av(f"scorta: fuori dalla finestra {fin['dalle']}-{fin['alle']}, riprovo fra "
                       f"{min(attesa, 600) // 60} minuti")
                    dorme(max(30, min(attesa, 600)))
            if not perche and st["lavorato"] > lim["ore_di_lavoro"] * 3600:
                perche = f"passate {lim['ore_di_lavoro']:g} ore di lavoro"
            if not perche:
                perche = perche_chiudere()
            if not perche and gb_liberi() < gb_min:
                perche = f"disco quasi pieno ({gb_liberi():.0f} GB liberi)"
            if perche:
                out["fermato"] = f"{perche}: {len(q) + 1} ore non fatte"
                out["non_fatte"] = [ora["nome"]] + [o["nome"] for o in q]
                av(f"scorta: mi fermo, {out['fermato']}")
                break
            cosa, perche = tetto(ora, st["mb_kit"].get(ora["kit"], 0.0), st["mb_tutto"], lim)
            if cosa == "niente":
                out["ore"].append({"nome": ora["nome"], "tipo": ora["tipo"], "kit": ora["kit"],
                                   "esito": "saltata: " + perche, "valutabile": False, "mb": 0})
                scrivi()
                continue
            av(f"scorta {ora['nome']} ({ora['tipo']}, kit {ora['kit']}, {cosa}): parte")
            t1 = orologio()
            try:
                codice, r = lancia(dict(ora, budget=cosa), lim["minuti_per_ora"] * 60)
            except Exception as ex:   # noqa: BLE001
                codice, r = f"non partito: {type(ex).__name__}: {str(ex)[:200]}", None
            st["lavorato"] += orologio() - t1
            x = dict(r) if r else {"nome": ora["nome"], "tipo": ora["tipo"], "kit": ora["kit"]}
            x["processo"] = {"codice": codice, "esito": esito_processo(codice)}
            if codice != 0 and (r is None or r.get("in_corso") or not r.get("esito")):
                x["esito"] = esito_processo(codice) + (" (a meta')" if r else "")
            if codice == MEMORIA and rifatte.get(ora["nome"], 0) < lim["ritenta_errore_memoria"]:
                rifatte[ora["nome"]] = 1
                q.append(ora)
                x["si_rifa"] = True
        mb = float((x.get("conti") or {}).get("mb") or 0)
        st["mb_kit"][ora["kit"]] = st["mb_kit"].get(ora["kit"], 0.0) + mb
        st["mb_tutto"] += mb
        cat = x.get("catena") if isinstance(x.get("catena"), dict) else {}
        riga = {k: x.get(k) for k in ("nome", "tipo", "kit", "esito", "valutabile", "vista", "processo", "si_rifa")}
        riga.update(mb=round(mb, 1), catena=cat.get("esito"), video=[v.get("esito") for v in x.get("video") or []])
        k = next((i for i, y in enumerate(out["ore"]) if y.get("nome") == ora["nome"]), None)
        if k is None:
            out["ore"].append(riga)
        else:
            out["ore"][k] = riga
        if (ora["nome"] not in in_zip and ora["nome"] not in st["da_zip"] and not x.get("si_rifa")
                and mb_minuti(ora["nome"]) > 0):
            st["da_zip"].append(ora["nome"])
        zip_pronti()
    zip_pronti(tutti=True)
    out["fine_ore"] = hms(adesso())
    scrivi()
    return out


CAMPI_CATENA = ("nome", "tipo", "kit", "telecamera", "inizio", "notte", "evento", "atteso", "box_dario", "fonte",
                "eventi", "altri_noti", "vista", "parte", "dentro_zona", "resta_giorni", "ora_del_kit", "per", "esito",
                "valutabile", "catena", "zona")


def catena_finale(ore_x, giudizi, perche, cat):
    """catena.json: per ogni ora i campi che servono alla misura (ora, candidati con la verita', giudizio di Qwen),
    i conti di conti_catena e com'e' andato Qwen."""
    n = unisci_giudizi(ore_x, giudizi or [])
    return {"scorta": VERSIONE, "qwen": cat.get("qwen"), "qwen_esito": perche, "carte_giudicate": n,
            "conti": conti_catena(ore_x), "ore": [{k: x.get(k) for k in CAMPI_CATENA if k in x} for x in ore_x]}


def carte_per_qwen(ore_x):
    """Le voci di carte.json per vlm_giudica (id, file, e per chi misura vero, rango, ora, tipo)."""
    out = []
    for x in ore_x:
        for c in ((x.get("catena") or {}).get("candidati") or []) if isinstance(x.get("catena"), dict) else []:
            if c.get("carta"):
                out.append({"id": c["carta"], "file": c["carta"] + ".jpg", "vero": bool(c.get("vero")),
                            "rango": c["rango"], "ora": x["nome"], "tipo": x.get("tipo")})
    return out


def nome_giudizi(prova):
    """Il file dei giudizi che vlm.py 0.5.0 scrive per una prova [modello, modo, domanda, etichetta?]."""
    return (f"giudizi_{prova[0].split('/')[-1]}_{prova[2]}" + (f"_{prova[3]}" if len(prova) > 3 and prova[3] else "")
            + ".json")


# ------------------------------------------------------------------ il lavoro di un'ora (registratore dato da fuori)

def immagini_carta(cv2, prima, dopo, box, lato_ritaglio=640, lato_scena=1280):
    """Le tre immagini della carta di Qwen (come carte_dai_pezzi del compito 34): prima e dopo ritagliati col riquadro
    rosso, lati `lato_ritaglio`; la scena dopo col riquadro, larga `lato_scena`."""
    h, w = dopo.shape[:2]
    (x0, y0, x1, y1), r = quadro_carta(h, w, box)
    lato = max(x1 - x0, y1 - y0)
    out = {}
    for nome, q in (("prima", prima), ("dopo", dopo)):
        if q.shape[:2] != (h, w):
            q = cv2.resize(q, (w, h))
        z = q[y0:y1, x0:x1].copy()
        cv2.rectangle(z, (r[0] - x0, r[1] - y0), (r[2] - x0, r[3] - y0), (0, 0, 255), max(2, int(lato / 150)))
        k = lato_ritaglio / max(z.shape[:2])
        out[nome] = cv2.resize(z, None, fx=k, fy=k)
    tutto = dopo.copy()
    cv2.rectangle(tutto, r[:2], r[2:], (0, 0, 255), max(3, w // 300))
    k = lato_scena / w
    out["scena"] = cv2.resize(tutto, None, fx=k, fy=k)
    return out


def _scrivi_jpg(cv2, img, percorso, largo=None, q=85):
    if img is None:
        return None
    if largo and img.shape[1] > largo:
        img = cv2.resize(img, (largo, max(1, int(round(img.shape[0] * largo / img.shape[1])))), interpolation=cv2.INTER_AREA)
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    cv2.imwrite(percorso, img, [cv2.IMWRITE_JPEG_QUALITY, int(q)])
    return os.path.basename(percorso)


def _pezzi_di(tr, cartella):
    """[(inizio, fine, file)] dei pezzi di un tratto di allunga.scarica_tratto (pezzi e _pezzi vanno insieme)."""
    return [(a, b, os.path.join(cartella, p["file"])) for p, (a, b) in zip(tr.get("pezzi") or [], tr.get("_pezzi") or [])]


def lavora_ora(ora, cfg, mezzi, scrivi=lambda x: None, av=lambda t: None):
    """Un'ora di scorta.json. mezzi: quelli di pilota.lavora_ora (nuovo, collega, kr, decodifica, fotogrammi, grezzi,
    cimitero, ffmpeg; «uscita» = la cartella dell'ora SUL PC, dove vanno minuti/), quelli di allunga.scarica_tratto
    (sposta, taglia, foglio), fotogramma(mp4, secondi) -> BGR o None, cv2, e «drive» = la cartella dell'ora
    nell'uscita del compito (solo cose piccole). ora["budget"]: "tutto" o "senza_catena" (il tetto del kit, deciso dal
    ponte). Ritorna il dict dell'ora, scritto anche man mano con scrivi."""
    import allunga as al
    import pilota as pl
    cv2 = mezzi["cv2"]
    cat = catena_da(cfg)
    PC, UD = mezzi["uscita"], mezzi["drive"]
    for d in (PC, UD):
        os.makedirs(d, exist_ok=True)
    t0 = time.time()
    x = {k: ora.get(k) for k in ("nome", "tipo", "kit", "canale", "inizio", "notte", "zona", "evento", "atteso",
                                 "box_dario", "box_da", "fonte", "eventi", "altri_noti", "vista", "parte", "catena",
                                 "fuori_catena", "dentro_zona", "resta_giorni", "ora_del_kit", "per", "budget") if k in ora}
    x.update(telecamera=int(ora["canale"]) + 1, scorta=VERSIONE, pilota=pl.VERSIONE, in_corso=True,
             inizio_lavoro=time.strftime("%Y-%m-%d %H:%M:%S"), cartella_pc=PC)
    x["catena"] = {"chiesta": bool(ora.get("catena")), "fatta": False}
    conti = {"chiamate": 0, "collegamenti": 0, "mb": 0.0}

    def salva():
        mm = (x.get("minuti") or {}).get("conti") or {}
        x["conti"] = {"mb": round(conti["mb"] + (mm.get("mb") or 0), 3),
                      "mb_minuti": mm.get("mb") or 0, "mb_video": round(sum(v.get("mb") or 0 for v in x.get("video") or []), 2),
                      "mb_catena": round(sum(p.get("mb") or 0 for p in x["catena"].get("pezzi") or []), 2),
                      "chiamate": conti["chiamate"] + (mm.get("chiamate") or 0),
                      "collegamenti": conti["collegamenti"] + (mm.get("collegamenti") or 0),
                      "secondi": round(time.time() - t0, 1)}
        scrivi(x)

    # A1) le miniature dei minuti (pilota.py, solo_minuti): in PC/minuti, il registro in x["minuti"]
    m = pl.lavora_ora(dict(ora, zona=ora.get("zona") or {"riquadri": [], "escludi": []}), {"solo_minuti": True},
                      mezzi, lambda r: None, av)
    x["minuti"] = {k: m.get(k) for k in ("esito", "valutabile", "registrazione", "b", "conti", "collegamenti", "minuti")}
    salva()
    if m.get("bloccato"):
        x.update(esito=m.get("esito"), bloccato=True, valutabile=False, in_corso=False)
        salva()
        return x
    mz = dict(mezzi, tempi=dict(al.TEMPI, **(mezzi.get("tempi") or {})))
    mz.setdefault("cimitero", [])
    col = al.Collegamento(mz, conti)
    vivo = m.get("registrazione") is not None or m.get("valutabile")
    try:
        # A2) il video a piena risoluzione di ogni abbandono dell'ora
        x["video"] = []
        for v in ora.get("video") or []:
            da = dt(v["inizio"])
            a = da + datetime.timedelta(seconds=float(v["secondi"]))
            xv = {"evento": v["evento"], "canale": v["canale"], "da": hms(da), "a": hms(a)}
            x["video"].append(xv)
            if not vivo:
                xv["esito"] = "saltato: " + str(m.get("esito"))
                continue
            iv = col.intervallo(int(v["canale"]))
            ok_, perche = pl.coperto(iv, da, a)
            if not ok_:
                xv["esito"] = perche
                continue
            cart = os.path.join(PC, "video")
            tr = al.scarica_tratto(col, int(v["canale"]), ("abbandono", da, a),
                                   dict(mz, cartella_video=cart, cartella_fogli=os.path.join(UD, "fogli")), conti, salva)
            pezzi = _pezzi_di(tr, cart)
            xv.update(esito="fatto" if pezzi else "niente scaricato", mb=tr.get("mb"), richieste=tr.get("richieste"),
                      secondi_attesa=tr.get("secondi_attesa"), coperti_s=tr.get("coperti_s"), buchi_s=tr.get("buchi_s"),
                      pezzi=[{k: p.get(k) for k in ("file", "inizio", "fine", "secondi", "fps", "misura", "foglio")}
                             for p in tr.get("pezzi") or []], note=tr.get("note"))
            atteso = next((dt(e["atteso"]) for e in ora.get("eventi") or [] if e.get("evento") == v["evento"]), None)
            if atteso and pezzi:
                xv["fotogrammi"] = {}
                for nome, s in zip(("prima", "dopo"), VIDEO_FOTO_S):
                    f, off = pezzo_per(atteso + datetime.timedelta(seconds=s), pezzi)
                    img = mezzi["fotogramma"](f, off) if f else None
                    xv["fotogrammi"][nome] = _scrivi_jpg(cv2, img, os.path.join(UD, f"{v['evento']}_{nome}.jpg"), 800, 72)
            av(f"scorta {ora['nome']}: video {v['evento']} {xv['esito']}, {xv.get('mb')} MB")
            salva()
        # B) la catena
        if ora.get("catena") and ora.get("budget", "tutto") != "tutto":
            x["catena"]["esito"] = "saltata: la catena passerebbe il tetto del kit"
        elif ora.get("catena") and not m.get("valutabile"):
            x["catena"]["esito"] = "saltata: miniature non valutabili (" + str(m.get("esito")) + ")"
        elif ora.get("catena"):
            _catena(ora, cfg, cat, mz, col, conti, x, PC, UD, salva, av)
        x["esito"] = m.get("esito") if not m.get("valutabile") else "fatto"
        x["valutabile"] = bool(m.get("valutabile"))
    except al.Bloccata as ex:
        x.update(esito=f"bloccato: {ex}", bloccato=True, valutabile=bool(m.get("valutabile")))
    except ConnectionError as ex:
        x.update(esito=f"registratore non raggiunto: {ex}", valutabile=bool(m.get("valutabile")))
    except (OSError, RuntimeError) as ex:
        x.update(esito=f"errore: {type(ex).__name__}: {str(ex)[:200]}", valutabile=bool(m.get("valutabile")))
    finally:
        if not x.get("bloccato"):
            col.chiudi()
    x["collegamenti"] = col.storia
    x["in_corso"] = False
    x["fine_lavoro"] = time.strftime("%Y-%m-%d %H:%M:%S")
    salva()
    av(f"scorta {ora['nome']}: {x.get('esito')}, {x['conti']['mb']} MB, catena {x['catena'].get('esito')}")
    return x


def _catena(ora, cfg, cat, mz, col, conti, x, PC, UD, salva, av):
    """La catena di un'ora: insieme sulle miniature salvate, i pezzi dei primi candidati, le carte."""
    import b_tavolino as bt
    import pilota as pl
    cv2, kr = mz["cv2"], mz["kr"]
    inizio = dt(ora["inizio"])
    fine = inizio + datetime.timedelta(minutes=60)
    ts = pl.tempi_scansione(inizio)
    fot = []
    for t in ts:
        p = os.path.join(PC, "minuti", f"{t:%H%M%S}.jpg")
        fot.append(cv2.imread(p) if os.path.exists(p) else None)
    t1 = time.time()
    cand = bt.scansione(kr, cv2, fot, ts, inizio, fine, ora["zona"]["riquadri"], ora["zona"].get("escludi") or [],
                        bt.opzioni(**cat["opzioni"]))
    c_ = x["catena"]
    c_.update(variante=cat["variante"], opzioni=cat["opzioni"], b_tavolino=bt.VERSIONE,
              secondi_scansione=round(time.time() - t1, 1), candidati_tutti=len(cand))
    top = cand[:int(cat["candidati"])]
    righe = []
    for k, c in enumerate(cand[:30], 1):
        r = {"rango": k, "box": c["box"], "comparsa": hms(c["comparsa"]), "comparsa_prima": hms(c["comparsa_prima"]),
             "punteggio": c["punteggio"], "area": c["area"], "dE": c["dE"], "durata_min": c["durata_min"],
             "fino": c["fino_alla_fine"], "mosso": c.get("mosso"), "fuori": c.get("fuori")}
        r.update(verita(c, ora))
        righe.append(r)
    c_["candidati"] = righe
    salva()
    cart = os.path.join(PC, "pezzi")
    pezzi = []
    c_["pezzi"] = []
    for da, a, ranghi in finestre(top, cat["prima_s"], cat["dopo_s"]):
        tr = al_scarica(mz, col, int(ora["canale"]), da, a, cart, conti, salva)
        pezzi += _pezzi_di(tr, cart)
        c_["pezzi"].append({"da": hms(da), "a": hms(a), "ranghi": ranghi, "mb": tr.get("mb"),
                            "richieste": tr.get("richieste"), "secondi_attesa": tr.get("secondi_attesa"),
                            "coperti_s": tr.get("coperti_s"), "buchi_s": tr.get("buchi_s"), "note": tr.get("note"),
                            "file": [p.get("file") for p in tr.get("pezzi") or []]})
        salva()
    carte = os.path.join(PC, "carte")
    for c, r in zip(top, righe):
        tp, td = tempi_carta(c, cat["carta_prima_s"], cat["carta_dopo_s"])
        fp, op = pezzo_per(tp, pezzi)
        fd, od = pezzo_per(td, pezzi)
        r.update(t_prima=hms(tp), t_dopo=hms(td))
        q = [mz["fotogramma"](fp, op) if fp else None, mz["fotogramma"](fd, od) if fd else None]
        if any(v is None for v in q):
            r["carta_manca"] = "fotogramma prima" if q[0] is None else "fotogramma dopo"
            continue
        ident = f"{ora['nome']}_{r['rango']}"
        im = immagini_carta(cv2, q[0], q[1], c["box"])
        _scrivi_jpg(cv2, im["prima"], os.path.join(carte, f"{ident}_prima.jpg"), q=90)
        _scrivi_jpg(cv2, im["dopo"], os.path.join(carte, f"{ident}_dopo.jpg"), q=90)
        _scrivi_jpg(cv2, im["scena"], os.path.join(carte, f"{ident}.jpg"), q=90)
        for nome, lato in (("prima", 320), ("dopo", 320), ("scena", 640)):   # le copie piccole in uscita
            _scrivi_jpg(cv2, im[nome], os.path.join(UD, "carte", f"{ident}{'' if nome == 'scena' else '_' + nome}.jpg"),
                        lato, 70)
        r["carta"] = ident
    c_["carte"] = sum(1 for r in righe if r.get("carta"))
    c_["fatta"] = True
    c_["esito"] = f"{len(cand)} candidati, {c_['carte']} carte"
    av(f"scorta {ora['nome']}: catena {c_['esito']}")
    salva()


def al_scarica(mz, col, canale, da, a, cartella, conti, salva):
    """Un tratto a piena risoluzione con allunga.scarica_tratto; i fogli dei pezzi della catena restano sul PC."""
    import allunga as al
    return al.scarica_tratto(col, canale, ("pezzo", da, a),
                             dict(mz, cartella_video=cartella, cartella_fogli=os.path.join(cartella, "fogli")), conti, salva)


# ------------------------------------------------------------------ la DLL vera e ffmpeg (solo sul PC)

def classe_registratore():
    """Il registratore di movimento.py (le miniature) con lo scarico che rende anche l'ora vera di ogni fotogramma
    (come allunga.classe_registratore): un collegamento solo fa tutte e due le cose."""
    if "c" in _classe:
        return _classe["c"]
    import focus_nvr as fn
    import movimento as mv
    base = mv.classe_registratore()

    class RegistratoreScorta(base):
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

    _classe["c"] = RegistratoreScorta
    return RegistratoreScorta


_classe = {}


def mezzi_veri(cartella_sdk, collega_con, ffmpeg, ora, pc, drive, grezzi, cimitero, nofin=0):
    """I mezzi di lavora_ora sul PC: quelli di pilota.mezzi_veri (miniature, decodifica, kit_rifiuti) con il
    registratore che sa anche scaricare con l'ora vera, piu' quelli di allunga (sposta, taglia, foglio) e il
    fotogramma di un mp4 con ffmpeg."""
    import subprocess
    import cv2
    import allunga as al
    import pilota as pl
    m = pl.mezzi_veri(cartella_sdk, collega_con, ffmpeg, ora, pc, grezzi, cimitero, nofin)
    a = al.mezzi_veri(cartella_sdk, collega_con, ffmpeg, ora, pc, cimitero, nofin)
    classe = classe_registratore()
    tmp = os.path.join(grezzi, "fotogrammi")

    def fotogramma(mp4, secondi):
        os.makedirs(tmp, exist_ok=True)
        out = os.path.join(tmp, f"f_{os.getpid()}_{int(time.time() * 1000) % 10 ** 9}.jpg")
        try:
            subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", f"{float(secondi):.2f}", "-i", mp4, "-frames:v", "1",
                            "-q:v", "2", out], capture_output=True, timeout=120, creationflags=nofin)
            return cv2.imread(out) if os.path.exists(out) else None
        finally:
            try:
                os.remove(out)
            except OSError:
                pass

    m.update(nuovo=lambda: classe(cartella_sdk, log=lambda *_: None), sposta=a["sposta"], taglia=a["taglia"],
             foglio=a["foglio"], fotogramma=fotogramma, cv2=cv2, drive=drive)
    return m
