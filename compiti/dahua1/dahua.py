"""
dahua - le funzioni del compito dahua1: SOLA LETTURA delle telecamere Dahua dei kit (registratori-kit).
VERSION 0.1.0 (17/11/2026)

Qui ci sono le parti che si provano a tavolino (prova_dahua1.py), senza VPN e senza telecamere vere:
  - accesso_dahua.txt (chiave=valore, righe kit=<sigla>;<indirizzo pubblico del router>) e la scelta dei kit;
  - la maschera dei segreti (password, chiave condivisa, utenti, indirizzi pubblici, seriali);
  - le risposte Dahua chiave=valore (getDeviceType, getSystemInfo, getConfig Encode e VideoStandard, getConfigCaps);
  - il conflitto fra la rete del PC e la rete del kit (192.168.1.0/24);
  - l'autenticazione digest fatta a mano (UN solo tentativo con password per richiesta: urllib la ritenta fino a 5
    volte, e 5 accessi sbagliati bloccano l'utente della telecamera Dahua per mezz'ora);
  - il client HTTP, che accetta SOLO i percorsi di lettura in PERCORSI_AMMESSI (niente setConfig, autoFocus, reboot);
  - la scansione della porta 80 a fili, con un tetto di tempo.

Nomi presi dalla guida «Dahua HTTP API 3.26»: magicBox.cgi?action=getDeviceType (type=...),
magicBox.cgi?action=getSystemInfo (serialNumber, deviceType, processor), configManager.cgi?action=getConfig&name=Encode
(table.Encode[0].MainFormat[0].Video.FPS=..., MainFormat[0/1/2] = registrazione normale / movimento / allarme,
ExtraFormat[0/1/2] = flussi secondari), configManager.cgi?action=getConfig&name=VideoStandard (table.VideoStandard=PAL),
encode.cgi?action=getConfigCaps&channel=1 (caps.MainFormat[0].Video.FPSMax=25), snapshot.cgi?channel=1&type=0 (JPEG).
"""
import hashlib
import http.client
import ipaddress
import os
import re
import socket
import threading
import time

VERSION = "0.1.0"

CAMPI_OBBLIGATORI = ("vpn_psk", "vpn_utente", "vpn_password", "telecamere_utente", "telecamere_password")
SEGRETI = ("vpn_psk", "vpn_utente", "vpn_password", "telecamere_utente", "telecamere_password")

# Le sole richieste che il compito puo' fare. Tutto il resto (setConfig, autoFocus, reboot, ptz...) e' rifiutato prima
# ancora di aprire il collegamento.
PERCORSI_AMMESSI = (
    "/cgi-bin/magicBox.cgi?action=getDeviceType",
    "/cgi-bin/magicBox.cgi?action=getSystemInfo",
    "/cgi-bin/configManager.cgi?action=getConfig&name=Encode",
    "/cgi-bin/configManager.cgi?action=getConfig&name=VideoStandard",
    "/cgi-bin/encode.cgi?action=getConfigCaps&channel=1",
    "/cgi-bin/snapshot.cgi?channel=1&type=0",
)

FLUSSI = {   # (gruppo, indice) -> nome nel risultato
    ("MainFormat", 0): "principale",              # registrazione normale
    ("MainFormat", 1): "principale_movimento",    # registrazione su movimento
    ("MainFormat", 2): "principale_allarme",      # registrazione su allarme
    ("ExtraFormat", 0): "secondario1",
    ("ExtraFormat", 1): "secondario2",
    ("ExtraFormat", 2): "secondario3",
}


class Rifiutata(Exception):
    """Una richiesta fuori da PERCORSI_AMMESSI: non parte."""


# ------------------------------------------------------------------ accesso_dahua.txt

def leggi_accesso(testo):
    """Il contenuto di accesso_dahua.txt -> (accesso, problemi). accesso = {campo: valore, "kit": [{sigla, server}]}.
    Righe vuote e con # ignorate; chiave=valore (solo il primo «=» divide: le password possono contenerne); i kit
    «kit=<sigla>;<indirizzo pubblico>». problemi: elenco di frasi senza i valori segreti. Funzione pura."""
    acc, kit, problemi = {}, [], []
    for n, riga in enumerate((testo or "").replace("﻿", "").splitlines(), 1):
        r = riga.strip()
        if not r or r.startswith("#"):
            continue
        if "=" not in r:
            problemi.append(f"riga {n}: manca «=»")
            continue
        k, v = r.split("=", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "kit":
            p = [x.strip() for x in v.split(";")]
            if len(p) < 2 or not p[0] or not p[1]:
                problemi.append(f"riga {n}: kit scritto male (serve kit=<sigla>;<indirizzo pubblico>)")
                continue
            kit.append({"sigla": p[0], "server": p[1], "riga": n})
        elif k in CAMPI_OBBLIGATORI:
            if k in acc:
                problemi.append(f"riga {n}: {k} scritto due volte (vale il primo)")
                continue
            acc[k] = v
        else:
            problemi.append(f"riga {n}: campo sconosciuto «{k[:30]}»")
    for k in CAMPI_OBBLIGATORI:
        if not acc.get(k):
            problemi.append(f"manca {k}")
    if not kit:
        problemi.append("nessuna riga kit=<sigla>;<indirizzo pubblico del router>")
    acc["kit"] = kit
    return acc, problemi


def accesso_completo(problemi):
    """Si puo' partire? Solo se non manca niente di obbligatorio (le righe strane si segnalano ma non fermano)."""
    return not any(p.startswith("manca ") or p.startswith("nessuna riga kit") for p in problemi)


def indirizzo_pubblico(s):
    """L'indirizzo del server VPN va bene? Deve essere un IPv4 pubblico (non privato, non 192.168.x, non loopback):
    un indirizzo della rete locale porterebbe la VPN altrove. Ritorna (ok, motivo)."""
    try:
        ip = ipaddress.ip_address(str(s).strip())
    except ValueError:
        return False, "non e' un indirizzo IP"
    if ip.version != 4:
        return False, "non e' IPv4"
    if not ip.is_global:
        return False, "non e' un indirizzo pubblico"
    return True, ""


def scegli_kit(kit, solo=None, massimo=None):
    """I kit da fare, nell'ordine del file: senza doppioni (vale la prima riga di una sigla), solo quelli in «solo» se
    c'e', con un indirizzo pubblico valido, al massimo «massimo». Ritorna (scelti, scartati[{sigla, motivo}])."""
    scelti, scartati, visti = [], [], set()
    voluti = {str(x).strip().upper() for x in (solo or []) if str(x).strip()}
    for k in kit or []:
        sig = str(k.get("sigla", "")).strip()
        chiave = sig.upper()
        if not sig:
            continue
        if chiave in visti:
            scartati.append({"sigla": sig, "motivo": "doppione: vale la prima riga"})
            continue
        visti.add(chiave)
        if voluti and chiave not in voluti:
            scartati.append({"sigla": sig, "motivo": "non nell'elenco «solo» di dahua.json"})
            continue
        ok, perche = indirizzo_pubblico(k.get("server"))
        if not ok:
            scartati.append({"sigla": sig, "motivo": f"indirizzo del router: {perche}"})
            continue
        if massimo is not None and len(scelti) >= int(massimo):
            scartati.append({"sigla": sig, "motivo": f"oltre il massimo di {massimo} kit"})
            continue
        scelti.append({"sigla": sig, "server": str(k["server"]).strip()})
    return scelti, scartati


# ------------------------------------------------------------------ maschere

def maschera_ip(s):
    """93.45.12.200 -> 93.x.x.200: si riconosce il kit nel risultato, non si scrive l'indirizzo intero."""
    p = str(s).split(".")
    return f"{p[0]}.x.x.{p[-1]}" if len(p) == 4 else "x.x.x.x"


def maschera_seriale(s):
    """Primi 3 e ultimi 2 caratteri, il resto *."""
    s = str(s or "")
    if len(s) <= 5:
        return "*" * len(s)
    return s[:3] + "*" * (len(s) - 5) + s[-2:]


def sostituzioni(acc, kit=None):
    """Le coppie (valore segreto, al suo posto) per maschera(): i segreti di accesso_dahua.txt e gli indirizzi dei
    router. Prima i valori piu' lunghi (una password che contiene l'utente non resta a meta')."""
    coppie = []
    for k in SEGRETI:
        v = (acc or {}).get(k)
        if v:
            coppie.append((v, f"<{k}>"))
    for x in (kit if kit is not None else (acc or {}).get("kit") or []):
        if x.get("server"):
            coppie.append((str(x["server"]), maschera_ip(x["server"])))
    return sorted(coppie, key=lambda c: -len(c[0]))


def maschera(testo, coppie):
    """Il testo con ogni valore segreto sostituito. Va usata su TUTTO quello che finisce in uscita/ o in un registro."""
    t = "" if testo is None else str(testo)
    for v, al_posto in coppie or []:
        if v:
            t = t.replace(v, al_posto)
    return t


# ------------------------------------------------------------------ risposte Dahua

def chiave_valore(testo):
    """Le righe chiave=valore di una risposta Dahua -> dict (le righe senza «=» si saltano)."""
    out = {}
    for riga in (testo or "").replace("\r", "").split("\n"):
        if "=" in riga:
            k, v = riga.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _numero(v):
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else f


def leggi_encode(testo, canale=0):
    """getConfig&name=Encode -> {nome del flusso: {fps, larghezza, altezza, risoluzione, bitrate_kbps,
    controllo_bitrate, codec, gop, profilo, qualita, attivo}} per il canale (da 0). Nomi dei flussi in FLUSSI."""
    kv = chiave_valore(testo)
    out = {}
    pat = re.compile(r"^table\.Encode\[(\d+)\]\.(MainFormat|ExtraFormat)\[(\d+)\]\.(.+)$")
    grezzi = {}
    for k, v in kv.items():
        m = pat.match(k)
        if not m or int(m.group(1)) != canale:
            continue
        grezzi.setdefault((m.group(2), int(m.group(3))), {})[m.group(4)] = v
    for (gruppo, i), g in sorted(grezzi.items()):
        nome = FLUSSI.get((gruppo, i), f"{gruppo}{i}")
        larg, alt = _numero(g.get("Video.Width")), _numero(g.get("Video.Height"))
        attivo = g.get("VideoEnable")
        out[nome] = {
            "fps": _numero(g.get("Video.FPS")),
            "larghezza": larg, "altezza": alt,
            "risoluzione": f"{larg}x{alt}" if larg and alt else g.get("Video.resolution"),
            "bitrate_kbps": _numero(g.get("Video.BitRate")),
            "controllo_bitrate": g.get("Video.BitRateControl"),
            "codec": g.get("Video.Compression"),
            "gop": _numero(g.get("Video.GOP")),
            "profilo": g.get("Video.Profile"),
            "qualita": _numero(g.get("Video.Quality")),
            "attivo": None if attivo is None else attivo.lower() == "true",
        }
    return out


def leggi_caps(testo):
    """encode.cgi?action=getConfigCaps -> {nome del flusso: {fps_max, codec_possibili, risoluzioni}} (prefisso «caps.»,
    a volte «caps[0].»)."""
    kv = chiave_valore(testo)
    pat = re.compile(r"^caps(?:\[\d+\])?\.(MainFormat|ExtraFormat)\[(\d+)\]\.Video\.(FPSMax|CompressionTypes|ResolutionTypes)$")
    out = {}
    for k, v in kv.items():
        m = pat.match(k)
        if not m:
            continue
        nome = FLUSSI.get((m.group(1), int(m.group(2))), f"{m.group(1)}{m.group(2)}")
        d = out.setdefault(nome, {})
        if m.group(3) == "FPSMax":
            d["fps_max"] = _numero(v)
        elif m.group(3) == "CompressionTypes":
            d["codec_possibili"] = v
        else:
            d["risoluzioni"] = v
    return out


def accelerazione(fps, a=25.0):
    """Se un video registrato a «fps» viene trattato come se fosse a «a» fotogrammi al secondo, scorre «a/fps» volte
    piu' veloce (15 fps letti a 25: 1,67 volte). None se fps non si sa."""
    try:
        f = float(fps)
    except (TypeError, ValueError):
        return None
    return round(a / f, 2) if f > 0 else None


def riassunto_telecamera(tipo, info, encode, caps, standard):
    """Le cifre che contano per la domanda di Dario, da una telecamera gia' letta."""
    pr = (encode or {}).get("principale") or {}
    fps = pr.get("fps")
    diversi = sorted({v.get("fps") for k, v in (encode or {}).items() if k.startswith("principale") and v.get("fps")})
    return {
        "modello": (tipo or {}).get("type") or (info or {}).get("deviceType"),
        "fps": fps,
        "fps_massimo": ((caps or {}).get("principale") or {}).get("fps_max"),
        "fps_registrazioni_principali": diversi,
        "risoluzione": pr.get("risoluzione"),
        "bitrate_kbps": pr.get("bitrate_kbps"),
        "codec": pr.get("codec"),
        "gop": pr.get("gop"),
        "standard": standard,
        "accelerazione_se_letto_a_25": accelerazione(fps),
    }


# ------------------------------------------------------------------ rete del PC

def reti_in_conflitto(reti_pc, rete_kit="192.168.1.0/24", ignora=()):
    """reti_pc: elenco di {rete: "a.b.c.d/n", dove: nome dell'interfaccia}, dagli indirizzi e dalle rotte del PC.
    Ritorna quelle che si sovrappongono alla rete del kit, saltando la rotta di difetto (/0), le multicast e le
    interfacce in «ignora» (la nostra VPN). Funzione pura."""
    kit = ipaddress.ip_network(rete_kit, strict=False)
    out = []
    for r in reti_pc or []:
        if r.get("dove") in ignora:
            continue
        try:
            n = ipaddress.ip_network(str(r.get("rete")), strict=False)
        except ValueError:
            continue
        if n.version != 4 or n.prefixlen == 0 or n.is_multicast or n.network_address == ipaddress.ip_address("255.255.255.255"):
            continue
        if n.overlaps(kit):
            out.append(r)
    return out


def indirizzi_da_provare(rete_kit, salta=(), noti=()):
    """Gli host della rete del kit (192.168.1.1-254), senza quelli da saltare (il router .1 e il registratore Focus .2
    di difetto), con quelli noti (.120, .170) davanti."""
    rete = ipaddress.ip_network(rete_kit, strict=False)
    tutti = [str(h) for h in rete.hosts()] or [str(rete.network_address)]
    salta = {str(x) for x in salta}
    davanti = [x for x in noti if x in tutti and x not in salta]
    return davanti + [x for x in tutti if x not in salta and x not in davanti]


def scansione(indirizzi, porta=80, fili=64, attesa=1.5, tetto_s=90.0):
    """Chi risponde sulla porta (TCP connect, niente dati mandati). Ritorna (aperti in ordine di indirizzo, secondi,
    finita_entro_il_tetto)."""
    t0 = time.time()
    coda = list(indirizzi)
    aperti, lk = [], threading.Lock()

    def lavora():
        while time.time() - t0 < tetto_s:
            with lk:
                if not coda:
                    return
                ip = coda.pop(0)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(attesa)
            try:
                if s.connect_ex((ip, porta)) == 0:
                    with lk:
                        aperti.append(ip)
            except OSError:
                pass
            finally:
                s.close()

    ff = [threading.Thread(target=lavora, daemon=True) for _ in range(max(1, min(fili, len(coda) or 1)))]
    for f in ff:
        f.start()
    for f in ff:
        f.join(max(0.1, tetto_s - (time.time() - t0) + attesa + 1))
    with lk:
        finita = not coda
    return sorted(set(aperti), key=lambda x: tuple(int(p) for p in x.split("."))), round(time.time() - t0, 1), finita


# ------------------------------------------------------------------ digest e HTTP

def leggi_sfida(intestazione):
    """WWW-Authenticate: Digest realm="...", nonce="...", qop="auth", opaque="..." -> dict, o None se non e' digest."""
    if not intestazione or not intestazione.strip().lower().startswith("digest"):
        return None
    corpo = intestazione.strip()[6:]
    out = {}
    for m in re.finditer(r'(\w+)\s*=\s*(?:"([^"]*)"|([^,\s]+))', corpo):
        out[m.group(1).lower()] = m.group(2) if m.group(2) is not None else m.group(3)
    return out


def risposta_digest(sfida, utente, password, metodo, uri, cnonce=None, nc="00000001"):
    """L'intestazione Authorization per la sfida (RFC 2617, MD5, qop auth o niente). cnonce fisso solo nelle prove."""
    realm, nonce = sfida.get("realm", ""), sfida.get("nonce", "")
    qop = None
    if sfida.get("qop"):
        scelte = [q.strip() for q in sfida["qop"].split(",")]
        qop = "auth" if "auth" in scelte else scelte[0]
    cnonce = cnonce or hashlib.md5(os.urandom(16)).hexdigest()[:16]
    ha1 = hashlib.md5(f"{utente}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{metodo}:{uri}".encode()).hexdigest()
    if qop:
        resp = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()).hexdigest()
    else:
        resp = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
    parti = [f'username="{utente}"', f'realm="{realm}"', f'nonce="{nonce}"', f'uri="{uri}"', f'response="{resp}"']
    if sfida.get("opaque") is not None:
        parti.append(f'opaque="{sfida["opaque"]}"')
    if qop:
        parti += [f"qop={qop}", f"nc={nc}", f'cnonce="{cnonce}"']
    if sfida.get("algorithm"):
        parti.append(f"algorithm={sfida['algorithm']}")
    return "Digest " + ", ".join(parti), resp


def sembra_dahua(sfida):
    """Una sfida digest di una telecamera Dahua: realm «Login to <seriale>» (o con Dahua nel nome). Le antenne e gli
    altri apparati sulla porta 80 non ricevono mai la password delle telecamere."""
    realm = (sfida or {}).get("realm", "")
    return realm.lower().startswith("login to") or "dahua" in realm.lower()


def controlla_percorso(percorso):
    if percorso not in PERCORSI_AMMESSI:
        raise Rifiutata(f"richiesta non ammessa (solo lettura): {percorso[:60]}")


def _get(ip, porta, percorso, intestazioni, attesa, massimo):
    c = http.client.HTTPConnection(ip, porta, timeout=attesa)
    try:
        c.request("GET", percorso, headers=dict({"User-Agent": "lettura", "Connection": "close"}, **intestazioni))
        r = c.getresponse()
        corpo = r.read(massimo + 1)
        return r.status, {k.lower(): v for k, v in r.getheaders()}, corpo[:massimo]
    finally:
        c.close()


class Telecamera:
    """Il client di UNA telecamera: solo GET, solo PERCORSI_AMMESSI, la password mandata al massimo una volta per
    richiesta e mai piu' dopo un rifiuto (blocco dell'utente Dahua dopo 5 accessi sbagliati)."""

    def __init__(self, ip, utente, password, porta=80, attesa=8.0):
        self.ip, self.utente, self.password, self.porta, self.attesa = ip, utente, password, porta, attesa
        self.rifiutato = False
        self.richieste = 0
        self.byte = 0

    def sonda(self):
        """Una richiesta SENZA password a getDeviceType: ritorna (stato HTTP, sfida o None, realm)."""
        p = PERCORSI_AMMESSI[0]
        st, h, _ = _get(self.ip, self.porta, p, {}, self.attesa, 65536)
        self.richieste += 1
        sf = leggi_sfida(h.get("www-authenticate"))
        return st, sf, (sf or {}).get("realm")

    def leggi(self, percorso, massimo=8 * 1024 * 1024):
        """GET di un percorso ammesso -> (stato, corpo in byte). 401 dopo la password = rifiutata, e non si riprova."""
        controlla_percorso(percorso)
        if self.rifiutato:
            return 401, b""
        st, h, corpo = _get(self.ip, self.porta, percorso, {}, self.attesa, massimo)
        self.richieste += 1
        if st == 401:
            sf = leggi_sfida(h.get("www-authenticate"))
            if not sf:
                return st, b""
            aut, _ = risposta_digest(sf, self.utente, self.password, "GET", percorso)
            st, h, corpo = _get(self.ip, self.porta, percorso, {"Authorization": aut}, self.attesa, massimo)
            self.richieste += 1
            if st == 401:
                self.rifiutato = True
        self.byte += len(corpo)
        return st, corpo
