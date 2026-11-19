"""Quanto pesa il giro del ponte: i MB scaricati da ogni registratore e i secondi di processore (ponte 0.22.0, compito
p2p_ponte40). Dario, 19/11: «richiede molto?». Fino al ponte 0.21.0 non era misurato.

Per ogni prova del giro il ponte segna:
- mb_foto: i MB grezzi arrivati dal registratore per le foto di 3 secondi (il flusso prima di ffmpeg: e' quello che
  passa sulla SIM del kit; `mb` di focus_nvr.Registratore.scarica);
- mb_scarico: i 15 secondi delle prove chieste a mano (non nel giro, ma sulla stessa SIM);
- mb_rete: i byte che il processo del ponte ha letto e scritto mentre durava la prova (GetProcessIoCounters su
  Windows: tutte le operazioni del processo, quindi anche il collegamento P2P, le domande dell'archivio e i minuti
  registrati, che non sono file; ci finisce anche quello che fa nello stesso tempo un altro filo del ponte);
- s_processore: i secondi di processore del processo del ponte durante la prova (time.process_time: tutti i fili, la
  libreria Focus compresa; ffmpeg, che gira a parte per fare la foto, no);
- s_durata, archivio (se ha letto anche l'archivio), con mb_rete e secondi dell'archivio a parte.

Il giro non ha un numero dal sito (op=prendi da' solo la richiesta): un giro nuovo comincia quando torna un registratore
gia' visto nel giro in corso, o dopo 20 minuti senza prove del giro (il sito riparte appena finito il precedente).
In uscita: peso_prove.jsonl (una riga per prova, si aggiunge) e peso_giri.json (un riassunto per giro, con i 15
registratori che pesano di piu'), riscritto a ogni prova; restano gli ultimi 200 giri.
Funzioni pure tranne io_processo. Prove in prova_peso_giro.py.
version: 0.1.0 (19/11/2026)
"""
import os
import time

VERSIONE = "0.1.0"
PAUSA_NUOVO_GIRO = 20 * 60
GIRI_TENUTI = 200
PESANTI = 15


def io_processo():
    """I byte letti + scritti + altri del processo (Windows, GetProcessIoCounters), o None altrove o se non riesce."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount",
                                                          "OtherOperationCount", "ReadTransferCount",
                                                          "WriteTransferCount", "OtherTransferCount")]
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.GetProcessIoCounters.argtypes = [wintypes.HANDLE, ctypes.POINTER(IO)]
        io = IO()
        if not k.GetProcessIoCounters(k.GetCurrentProcess(), ctypes.byref(io)):
            return None
        return int(io.ReadTransferCount + io.WriteTransferCount + io.OtherTransferCount)
    except Exception:   # noqa: BLE001
        return None


def istantanea():
    """(orologio, processore, byte del processo) adesso."""
    return time.time(), time.process_time(), io_processo()


def differenza(prima, dopo):
    """{s_durata, s_processore, mb_rete} fra due istantanee. Funzione pura."""
    t0, c0, b0 = prima
    t1, c1, b1 = dopo
    return {"s_durata": round(max(0.0, t1 - t0), 1), "s_processore": round(max(0.0, c1 - c0), 2),
            "mb_rete": None if b0 is None or b1 is None else round(max(0, b1 - b0) / 1e6, 3)}


def mb_dall_esito(es):
    """(mb_foto, mb_scarico) da un esito del ponte: le «mb» delle foto (camere) e dello scarico di 15 s. Funzione pura."""
    es = es or {}
    foto = sum(float(c.get("mb") or 0) for c in es.get("camere") or [] if isinstance(c, dict))
    sc = es.get("scarico_mb")
    return round(foto, 3), round(float(sc or 0), 3)


def nuovo_stato():
    return {"giro": 0, "visti": [], "ultimo": None, "giri": []}


def _vuoto(n, adesso):
    return {"giro": n, "inizio": adesso, "fine": adesso, "prove": 0, "riuscite": 0, "registratori": 0,
            "mb_foto": 0.0, "mb_scarico": 0.0, "mb_rete": 0.0, "mb_rete_misurato": False, "s_processore": 0.0,
            "s_durata": 0.0, "archivi": 0, "s_processore_processo": None, "pesanti": []}


def segna(stato, voce, adesso, cpu_processo=None):
    """Aggiunge una prova (voce: uid, kit, priorita, ok, mb_foto, mb_scarico, mb_rete, s_processore, s_durata, archivio)
    allo stato e ritorna (stato, numero del giro). Le prove chieste a mano (priorita diversa da 0) vanno nel giro 0.
    cpu_processo: time.process_time() di adesso, per i secondi di processore di tutto il ponte nel giro (anche fra una
    prova e l'altra). Funzione pura (lo stato si modifica e si ritorna)."""
    st = stato or nuovo_stato()
    a_mano = voce.get("priorita") not in (0, None)
    if a_mano:
        n = 0
    else:
        nuovo = (not st["giri"] or st["giro"] == 0 or voce.get("uid") in st["visti"]
                 or (st["ultimo"] is not None and adesso - st["ultimo"] > PAUSA_NUOVO_GIRO))
        if nuovo:
            st["giro"] = max([g["giro"] for g in st["giri"]] + [0]) + 1
            st["visti"] = []
            g = _vuoto(st["giro"], adesso)
            g["cpu_inizio"] = cpu_processo
            st["giri"].append(g)
        st["visti"].append(voce.get("uid"))
        st["ultimo"] = adesso
        n = st["giro"]
    g = next((x for x in st["giri"] if x["giro"] == n), None)
    if g is None:   # il giro 0 (a mano) nasce la prima volta che serve
        g = _vuoto(0, adesso)
        st["giri"].insert(0, g)
    g["fine"] = adesso
    g["prove"] += 1
    g["riuscite"] += 1 if voce.get("ok") else 0
    g["registratori"] = len(set(st["visti"])) if n else g["prove"]
    for k in ("mb_foto", "mb_scarico", "s_processore", "s_durata"):
        g[k] = round(g[k] + float(voce.get(k) or 0), 3)
    if voce.get("mb_rete") is not None:
        g["mb_rete"] = round(g["mb_rete"] + float(voce["mb_rete"]), 3)
        g["mb_rete_misurato"] = True
    g["archivi"] += 1 if voce.get("archivio") else 0
    if cpu_processo is not None and g.get("cpu_inizio") is not None:
        g["s_processore_processo"] = round(cpu_processo - g["cpu_inizio"], 1)
    peso = round(float(voce.get("mb_foto") or 0) + float(voce.get("mb_scarico") or 0), 3)
    g["pesanti"] = sorted(g["pesanti"] + [{"kit": voce.get("kit"), "uid": voce.get("uid"), "mb": peso,
                                           "mb_rete": voce.get("mb_rete"), "s_processore": voce.get("s_processore"),
                                           "archivio": bool(voce.get("archivio"))}],
                          key=lambda x: (-(x["mb_rete"] if x["mb_rete"] is not None else x["mb"]), -x["mb"]))[:PESANTI]
    vecchi = [x for x in st["giri"] if x["giro"]][:-GIRI_TENUTI]
    st["giri"] = [x for x in st["giri"] if x not in vecchi]
    return st, n


def riassunto(stato):
    """Il json da scrivere: i giri con la durata, i MB per registratore e la quota di un processore. Funzione pura."""
    out = []
    for g in (stato or {}).get("giri") or []:
        x = {k: v for k, v in g.items() if k != "cpu_inizio"}
        durata = max(1.0, g["fine"] - g["inizio"])
        x["inizio"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(g["inizio"]))
        x["fine"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(g["fine"]))
        x["minuti"] = round(durata / 60, 1)
        n = max(1, g["prove"])
        x["mb_per_prova"] = round((g["mb_foto"] + g["mb_scarico"]) / n, 3)
        x["mb_rete_per_prova"] = round(g["mb_rete"] / n, 3) if g["mb_rete_misurato"] else None
        cpu = g["s_processore_processo"] if g["s_processore_processo"] is not None else g["s_processore"]
        x["quota_processore"] = round(cpu / durata, 3) if g["giro"] else None   # 1.0 = un processore intero per tutto il giro
        out.append(x)
    return {"versione": VERSIONE, "giri": out}
