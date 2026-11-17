"""
prova_dahua1 - le prove a tavolino del compito dahua1, senza VPN e senza telecamere vere.
VERSION 0.1.0 (17/11/2026)

Uso: python3 prova_dahua1.py

  1. accesso_dahua.txt: completo, incompleto, password con «=», commenti, BOM, doppioni, righe kit sbagliate;
  2. scelta dei kit: doppioni, indirizzi privati o sbagliati, «solo», massimo;
  3. maschera dei segreti e degli indirizzi dei router, seriali;
  4. le risposte Dahua con le righe della guida «Dahua HTTP API 3.26» (getConfig Encode, getConfigCaps,
     VideoStandard, getSystemInfo, getDeviceType), fps con la virgola, canali, accelerazione;
  5. conflitto fra le reti del PC e 192.168.1.0/24, indirizzi da provare;
  6. digest: l'esempio della RFC 2617, la sfida Dahua;
  7. solo lettura: setConfig, autoFocus, reboot, ptz rifiutati prima di partire;
  8. una telecamera Dahua finta su 127.0.0.1 (digest vero): password giusta, password sbagliata (UNA sola prova),
     un apparato che non e' Dahua (la password non parte mai), la scansione;
  9. il compito intero con una VPN finta: risultato, foto, VPN tolta alla fine, nessun segreto in uscita, ripresa;
     il conflitto di rete (nessun collegamento), accesso_dahua.txt mancante o incompleto.
"""
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
VERSION = "0.1.0"

import dahua as dh   # noqa: E402

PROVE = {"ok": 0, "ko": 0}


def vero(cond, cosa):
    if cond:
        PROVE["ok"] += 1
    else:
        PROVE["ko"] += 1
        print("  NO:", cosa)


# righe della guida «Dahua HTTP API 3.26» (getConfig&name=Encode, encode.cgi?action=getConfigCaps), piu' un secondo
# canale e un flusso secondario a 12,5 fps
ENCODE = """table.Encode[0].MainFormat[0].Audio.Bitrate=64
table.Encode[0].MainFormat[0].AudioEnable=true
table.Encode[0].MainFormat[0].Video.resolution=1920x1080
table.Encode[0].MainFormat[0].Video.BitRate=4096
table.Encode[0].MainFormat[0].Video.BitRateControl=CBR
table.Encode[0].MainFormat[0].Video.Compression=H.264
table.Encode[0].MainFormat[0].Video.CustomResolutionName=1080P
table.Encode[0].MainFormat[0].Video.FPS=18
table.Encode[0].MainFormat[0].Video.GOP=36
table.Encode[0].MainFormat[0].Video.Height=1080
table.Encode[0].MainFormat[0].Video.Pack=PS
table.Encode[0].MainFormat[0].Video.Profile=High
table.Encode[0].MainFormat[0].Video.Quality=4
table.Encode[0].MainFormat[0].Video.Width=1920
table.Encode[0].MainFormat[0].VideoEnable=true
table.Encode[0].MainFormat[1].Video.FPS=18
table.Encode[0].MainFormat[1].Video.Width=1920
table.Encode[0].MainFormat[1].Video.Height=1080
table.Encode[0].MainFormat[2].Video.FPS=25
table.Encode[0].MainFormat[3].Video.FPS=25
table.Encode[0].ExtraFormat[0].Video.Compression=H.265
table.Encode[0].ExtraFormat[0].Video.FPS=12.5
table.Encode[0].ExtraFormat[0].Video.Width=704
table.Encode[0].ExtraFormat[0].Video.Height=576
table.Encode[0].ExtraFormat[0].VideoEnable=false
table.Encode[1].MainFormat[0].Video.FPS=7
"""
CAPS = """caps.MainFormat[0].Audio.CompressionTypes=G.711A, AMR
caps.MainFormat[0].Video.CompressionTypes=H.264,MJPG
caps.MainFormat[0].Video.ResolutionTypes=2048 x 1536,1080,SXGA, 1280 x 960,720,D1,CIF
caps.MainFormat[0].Video.BitRateOptions=448,2560
caps.MainFormat[0].Video.FPSMax=25
caps.ExtraFormat[0].Video.FPSMax=25
caps.SnapFormat[0].Video.FPSMax=2
"""
SISTEMA = "serialNumber=PA1FQ15900207\ndeviceType=27\nprocessor=ST7108\n"


# ------------------------------------------------------------------ 1-7 funzioni pure

def prove_pure():
    print("1. accesso_dahua.txt")
    testo = ("﻿# accesso di prova\n"
             "vpn_psk=chiave=con=uguali\n"
             "vpn_utente=utentevpn\n"
             "vpn_password=PwVpn!123\n"
             "telecamere_utente=admin\n"
             "telecamere_password=Cam#Pass\n"
             "\n"
             "kit=KIT249;93.45.12.200\n"
             "kit=KIT560 ; 151.20.3.4 \n"
             "kit=KIT1\n"
             "colore=blu\n")
    acc, pb = dh.leggi_accesso(testo)
    vero(acc["vpn_psk"] == "chiave=con=uguali", "la chiave con «=» resta intera")
    vero(acc["telecamere_password"] == "Cam#Pass", "password delle telecamere")
    vero([k["sigla"] for k in acc["kit"]] == ["KIT249", "KIT560"] and acc["kit"][1]["server"] == "151.20.3.4",
         "due kit, spazi tolti")
    vero(any("kit scritto male" in p for p in pb) and any("sconosciuto" in p for p in pb), "righe strane segnalate")
    vero(dh.accesso_completo(pb), "le righe strane non fermano")
    vero(not any("Cam#Pass" in p or "PwVpn" in p for p in pb), "nessun segreto nei problemi")
    acc2, pb2 = dh.leggi_accesso("vpn_psk=x\nvpn_utente=u\ntelecamere_utente=admin\n")
    vero(not dh.accesso_completo(pb2), "incompleto: non si parte")
    vero("manca vpn_password" in pb2 and "manca telecamere_password" in pb2, "dice cosa manca")
    vero(any(p.startswith("nessuna riga kit") for p in pb2), "dice che mancano i kit")
    _, pb3 = dh.leggi_accesso("vpn_psk=a\nvpn_psk=b\n")
    vero(any("due volte" in p for p in pb3), "doppione segnalato")
    vero(not dh.accesso_completo(dh.leggi_accesso("")[1]), "file vuoto")

    print("2. scelta dei kit")
    kit = [{"sigla": "KIT1", "server": "93.1.1.1"}, {"sigla": "kit1", "server": "93.1.1.2"},
           {"sigla": "KIT2", "server": "192.168.1.1"}, {"sigla": "KIT3", "server": "pippo"},
           {"sigla": "KIT4", "server": "10.0.0.1"}, {"sigla": "KIT5", "server": "100.64.0.1"},
           {"sigla": "KIT6", "server": "151.2.3.4"}, {"sigla": "KIT7", "server": "151.2.3.5"}]
    s, sc = dh.scegli_kit(kit)
    vero([k["sigla"] for k in s] == ["KIT1", "KIT6", "KIT7"], f"scelti {[k['sigla'] for k in s]}")
    mot = {x["sigla"]: x["motivo"] for x in sc}
    vero("doppione" in mot["kit1"] and "pubblico" in mot["KIT2"] and "non e' un indirizzo" in mot["KIT3"]
         and "pubblico" in mot["KIT5"], f"motivi {mot}")
    s, _ = dh.scegli_kit(kit, solo=["kit7"])
    vero([k["sigla"] for k in s] == ["KIT7"], "solo")
    s, sc = dh.scegli_kit(kit, massimo=2)
    vero(len(s) == 2 and any("massimo" in x["motivo"] for x in sc), "massimo")

    print("3. maschere")
    coppie = dh.sostituzioni(acc)
    t = dh.maschera("rasdial X utentevpn PwVpn!123 server 93.45.12.200 psk chiave=con=uguali admin Cam#Pass", coppie)
    for seg in ("utentevpn", "PwVpn!123", "93.45.12.200", "chiave=con=uguali", "Cam#Pass"):
        vero(seg not in t, f"{seg} mascherato")
    vero("93.x.x.200" in t, "router riconoscibile")
    a2, _ = dh.leggi_accesso("vpn_psk=k\nvpn_utente=ab\nvpn_password=abcdef\ntelecamere_utente=u\n"
                             "telecamere_password=p\nkit=K;8.8.8.8\n")
    vero("cdef" not in dh.maschera("x abcdef y", dh.sostituzioni(a2)), "prima i valori lunghi")
    vero(dh.maschera_seriale("PA1FQ15900207") == "PA1********07", dh.maschera_seriale("PA1FQ15900207"))
    vero(dh.maschera_ip("93.45.12.200") == "93.x.x.200", "maschera_ip")

    print("4. risposte Dahua")
    e = dh.leggi_encode(ENCODE)
    p = e["principale"]
    vero(p["fps"] == 18 and p["larghezza"] == 1920 and p["altezza"] == 1080 and p["risoluzione"] == "1920x1080",
         f"principale {p}")
    vero(p["bitrate_kbps"] == 4096 and p["controllo_bitrate"] == "CBR" and p["codec"] == "H.264" and p["gop"] == 36
         and p["attivo"] is True and p["profilo"] == "High", "campi del principale")
    vero(e["principale_allarme"]["fps"] == 25 and e["principale_movimento"]["fps"] == 18, "movimento e allarme")
    vero(e["MainFormat3"]["fps"] == 25, "indice fuori elenco col suo nome")
    vero(e["secondario1"]["fps"] == 12.5 and e["secondario1"]["attivo"] is False and e["secondario1"]["codec"] == "H.265",
         "secondario a 12,5 fps")
    vero(dh.leggi_encode(ENCODE, canale=1)["principale"]["fps"] == 7, "canale 2")
    c = dh.leggi_caps(CAPS)
    vero(c["principale"]["fps_max"] == 25 and c["secondario1"]["fps_max"] == 25, f"caps {c}")
    vero(c["principale"]["codec_possibili"] == "H.264,MJPG", "codec possibili")
    vero(dh.leggi_caps("caps[0].MainFormat[0].Video.FPSMax=20")["principale"]["fps_max"] == 20, "caps[0].")
    vero(dh.accelerazione(15) == 1.67 and dh.accelerazione(25) == 1.0 and dh.accelerazione(None) is None
         and dh.accelerazione(0) is None, "accelerazione")
    r = dh.riassunto_telecamera({"type": "IPC-HFW3449T-ZS-IL"}, dh.chiave_valore(SISTEMA), e, c, "PAL")
    vero(r["modello"] == "IPC-HFW3449T-ZS-IL" and r["fps"] == 18 and r["fps_massimo"] == 25 and r["standard"] == "PAL"
         and r["fps_registrazioni_principali"] == [18, 25] and r["accelerazione_se_letto_a_25"] == 1.39, f"riassunto {r}")
    vero(dh.chiave_valore("table.VideoStandard=PAL\r\n")["table.VideoStandard"] == "PAL", "VideoStandard")
    vero(dh.chiave_valore("type=DVR")["type"] == "DVR", "getDeviceType")
    vero(dh.leggi_encode("Error\r\nBad Request!") == {}, "risposta d'errore")

    print("5. reti del PC")
    rete = [{"rete": "192.168.1.34/24", "dove": "Ethernet"}, {"rete": "192.168.100.20/24", "dove": "Wi-Fi"},
            {"rete": "0.0.0.0/0", "dove": "Ethernet"}, {"rete": "224.0.0.0/4", "dove": "Ethernet"},
            {"rete": "255.255.255.255/32", "dove": "Ethernet"}, {"rete": "192.168.1.0/24", "dove": "KitRifiuti-Dahua"}]
    cf = dh.reti_in_conflitto(rete, ignora=("KitRifiuti-Dahua",))
    vero([x["dove"] for x in cf] == ["Ethernet"], f"conflitti {cf}")
    vero(dh.reti_in_conflitto(rete[1:], ignora=("KitRifiuti-Dahua",)) == [], "senza 192.168.1.x nessun conflitto")
    vero(len(dh.reti_in_conflitto([{"rete": "192.168.0.0/16", "dove": "VPN altra"}])) == 1, "una /16 che la copre")
    vero(len(dh.reti_in_conflitto([{"rete": "192.168.0.0/24", "dove": "Ethernet"}], "192.168.0.25/32")) == 1,
         "indirizzo della VPN dentro la LAN del PC")
    ind = dh.indirizzi_da_provare("192.168.1.0/24", ["192.168.1.1", "192.168.1.2"], ["192.168.1.120", "192.168.1.170"])
    vero(len(ind) == 252 and ind[:2] == ["192.168.1.120", "192.168.1.170"] and "192.168.1.1" not in ind
         and "192.168.1.2" not in ind and "192.168.1.254" in ind and len(set(ind)) == 252, "indirizzi da provare")

    print("6. digest")
    sf = dh.leggi_sfida('Digest realm="testrealm@host.com", qop="auth,auth-int", '
                        'nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41"')
    _, resp = dh.risposta_digest(sf, "Mufasa", "Circle Of Life", "GET", "/dir/index.html", cnonce="0a4f113b")
    vero(resp == "6629fae49393a05397450978507c4ef1", f"RFC 2617: {resp}")
    vero(dh.leggi_sfida("Basic realm=x") is None and dh.leggi_sfida(None) is None, "non digest")
    vero(dh.sembra_dahua(dh.leggi_sfida('Digest realm="Login to 4L0ABCDEF123", qop="auth", nonce="1"')), "realm Dahua")
    vero(not dh.sembra_dahua(dh.leggi_sfida('Digest realm="AirOS", nonce="1"')), "realm di un'antenna")

    print("7. solo lettura")
    for cattivo in ("/cgi-bin/configManager.cgi?action=setConfig&Encode[0].MainFormat[0].Video.FPS=25",
                    "/cgi-bin/devVideoInput.cgi?action=autoFocus&channel=1",
                    "/cgi-bin/magicBox.cgi?action=reboot",
                    "/cgi-bin/ptz.cgi?action=start&channel=1&code=FocusNear",
                    "/cgi-bin/configManager.cgi?action=getConfig&name=Encode&x=setConfig",
                    "/cgi-bin/snapshot.cgi?channel=1&type=0#"):
        try:
            dh.controlla_percorso(cattivo)
            vero(False, f"lasciata passare {cattivo}")
        except dh.Rifiutata:
            vero(True, "")
    vero(all("set" not in p.lower() and "reboot" not in p and "focus" not in p.lower() for p in dh.PERCORSI_AMMESSI),
         "l'elenco ammesso e' solo lettura")
    vero(all(re.search(r"action=get|snapshot\.cgi", p) for p in dh.PERCORSI_AMMESSI), "solo get e snapshot")


# ------------------------------------------------------------------ 8 la telecamera finta

class Finta:
    """Una telecamera Dahua finta (digest MD5 qop=auth) o un apparato non Dahua."""

    def __init__(self, utente="admin", password="Cam#Pass", dahua=True):
        self.utente, self.password, self.dahua = utente, password, dahua
        self.nonce = "abc123nonce"
        self.richieste, self.autorizzazioni, self.sbagliate = [], 0, 0
        finta = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                finta.richieste.append(("GET", self.path))
                realm = "Login to 4L0ABCDEF123" if finta.dahua else "AirOS"
                aut = self.headers.get("Authorization")
                if aut:
                    finta.autorizzazioni += 1
                if not aut or not finta.giusta(aut, realm, self.path):
                    if aut:
                        finta.sbagliate += 1
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", f'Digest realm="{realm}", qop="auth", nonce="{finta.nonce}", '
                                                         'opaque="op"')
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                corpo = finta.risposta(self.path)
                self.send_response(200)
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_POST(self):
                finta.richieste.append(("POST", self.path))
                self.send_response(405)
                self.end_headers()

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.porta = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def giusta(self, aut, realm, uri):
        d = dict((m.group(1), m.group(2) if m.group(2) is not None else m.group(3))
                 for m in re.finditer(r'(\w+)=(?:"([^"]*)"|([^,\s]+))', aut[7:]))
        ha1 = hashlib.md5(f"{self.utente}:{realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"GET:{uri}".encode()).hexdigest()
        atteso = hashlib.md5(f"{ha1}:{self.nonce}:{d.get('nc')}:{d.get('cnonce')}:auth:{ha2}".encode()).hexdigest()
        return d.get("username") == self.utente and d.get("uri") == uri and d.get("response") == atteso

    def risposta(self, path):
        if "getDeviceType" in path:
            return b"type=IPC-HFW5559E1-ZE-IL\r\n"
        if "getSystemInfo" in path:
            return b"serialNumber=4L0ABCDEF123\r\ndeviceType=IPC-HFW5559E1-ZE-IL\r\nprocessor=SSC338\r\n"
        if "name=Encode" in path:
            return ENCODE.replace("FPS=18", "FPS=15").replace("\n", "\r\n").encode()
        if "VideoStandard" in path:
            return b"table.VideoStandard=PAL\r\n"
        if "getConfigCaps" in path:
            return CAPS.encode()
        if "snapshot" in path:
            return b"\xff\xd8\xff\xe0" + b"0" * 2000 + b"\xff\xd9"
        return b"Error"

    def chiudi(self):
        self.srv.shutdown()
        self.srv.server_close()


def prove_telecamera():
    print("8. telecamera finta")
    f = Finta()
    try:
        tc = dh.Telecamera("127.0.0.1", "admin", "Cam#Pass", f.porta, 5)
        st, sf, realm = tc.sonda()
        vero(st == 401 and dh.sembra_dahua(sf) and f.autorizzazioni == 0, "sonda senza password")
        st, corpo = tc.leggi(dh.PERCORSI_AMMESSI[2])
        vero(st == 200 and dh.leggi_encode(corpo.decode())["principale"]["fps"] == 15, "Encode letto col digest")
        st, jpg = tc.leggi(dh.PERCORSI_AMMESSI[5])
        vero(st == 200 and jpg[:2] == b"\xff\xd8", "snapshot")
        try:
            tc.leggi("/cgi-bin/configManager.cgi?action=setConfig&Encode[0].MainFormat[0].Video.FPS=25")
            vero(False, "setConfig partito")
        except dh.Rifiutata:
            vero(True, "")
        vero(all(m == "GET" and "set" not in p.lower() for m, p in f.richieste), "solo GET di lettura arrivati")
    finally:
        f.chiudi()

    f = Finta(password="un'altra")
    try:
        tc = dh.Telecamera("127.0.0.1", "admin", "Cam#Pass", f.porta, 5)
        tc.sonda()
        st, _ = tc.leggi(dh.PERCORSI_AMMESSI[0])
        st2, _ = tc.leggi(dh.PERCORSI_AMMESSI[1])
        vero(st == 401 and tc.rifiutato and st2 == 401, "password sbagliata: rifiutata")
        vero(f.sbagliate == 1, f"UNA sola password sbagliata mandata (sono {f.sbagliate})")
    finally:
        f.chiudi()

    f = Finta(dahua=False)
    try:
        r = _con_compito(lambda cp: cp.leggi_telecamera("127.0.0.1", "KIT1", dict(cp.DIFETTI, porta=f.porta),
                                                        {"telecamere_utente": "admin", "telecamere_password": "Cam#Pass"},
                                                        1e12))
        vero(not r["dahua"] and f.autorizzazioni == 0 and "non mandata" in r["esito"], f"antenna: {r.get('esito')}")
        vero("4L0ABCDEF123" not in json.dumps(r), "")
    finally:
        f.chiudi()

    # la scansione: una porta aperta e una chiusa
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    porta = srv.getsockname()[1]
    aperti, sec, finita = dh.scansione(["127.0.0.1", "127.0.0.2"], porta, fili=4, attesa=0.5, tetto_s=10)
    srv.close()
    vero(aperti == ["127.0.0.1"] and finita, f"scansione {aperti}")
    aperti, sec, finita = dh.scansione(["127.0.0.1"] * 50, 9, fili=1, attesa=0.2, tetto_s=0.01)
    vero(sec < 3, "tetto della scansione")


# ------------------------------------------------------------------ 9 il compito intero

class VpnFinta:
    def __init__(self, reti=None, collega_ok=True, rotta_ok=True, codice=0):
        self.reti = reti if reti is not None else [{"rete": "10.0.0.5/24", "dove": "Ethernet"},
                                                   {"rete": "0.0.0.0/0", "dove": "Ethernet"}]
        self.collega_ok, self.rotta_ok, self.codice = collega_ok, rotta_ok, codice
        self.chiamate = []
        self.collegata = False

    def reti_pc(self):
        self.chiamate.append("reti")
        return self.reti, ""

    def prepara(self, server, aut):
        self.chiamate.append(("prepara", server, tuple(aut)))
        return True, {"split": True, "rotte": ["127.0.0.1/32"]}

    def collega(self):
        self.chiamate.append("collega")
        if not self.collega_ok:
            return False, {"codice": self.codice, "errore": "rifiutata"}
        self.collegata = True
        return True, {"codice": 0}

    def verifica(self, ip):
        self.chiamate.append("verifica")
        if not self.rotta_ok:
            return False, {"errore": "non passa dalla VPN"}
        return True, {"interfaccia": "KitRifiuti-Dahua", "ip_vpn": ["192.168.0.25/32"]}

    def scollega(self):
        self.chiamate.append("scollega")
        self.collegata = False
        return 0, ""

    def rimuovi(self):
        self.chiamate.append("rimuovi")
        return 0, "tolta"


ACCESSO = ("vpn_psk=PskSegreta99\nvpn_utente=utentevpn\nvpn_password=PwVpn!123\ntelecamere_utente=admin\n"
           "telecamere_password=Cam#Pass\nkit=KIT249;93.45.12.200\nkit=KIT560;151.20.3.4\nkit=KIT9;192.168.1.50\n")


def _con_compito(fun, cartella=None):
    """Importa compito.py come se girasse nella cartella data (o in QUI), chiama fun(modulo)."""
    import importlib
    vecchio = sys.argv[:]
    sys.argv = [os.path.join(QUI, "compito.py")] + ([cartella] if cartella else [])
    try:
        sys.modules.pop("compito", None)
        cp = importlib.import_module("compito")
        if cartella:
            cp.C, cp.U = cartella, os.path.join(cartella, "uscita")
        else:
            cp.U = tempfile.mkdtemp()
        return fun(cp)
    finally:
        sys.argv = vecchio


def cartella_compito(accesso=ACCESSO, cfg=None):
    d = tempfile.mkdtemp(prefix="dahua1_")
    for x in ("compito.py", "dahua.py"):
        shutil.copy2(os.path.join(QUI, x), d)
    if accesso is not None:
        open(os.path.join(d, "accesso_dahua.txt"), "w", encoding="utf-8").write(accesso)
    json.dump(cfg or {}, open(os.path.join(d, "dahua.json"), "w"))
    return d


def segreti_in(cartella):
    trovati = []
    for radice, _, files in os.walk(os.path.join(cartella, "uscita")):
        for x in files:
            b = open(os.path.join(radice, x), "rb").read()
            for s in ("PskSegreta99", "utentevpn", "PwVpn!123", "Cam#Pass", "93.45.12.200", "151.20.3.4",
                      "4L0ABCDEF123"):
                if s.encode() in b:
                    trovati.append(f"{x}: {s}")
    return trovati


def prove_compito():
    print("9. il compito intero")
    f = Finta()
    try:
        cfg = {"rete_kit": "127.0.0.1/32", "salta": [], "noti": [], "porta": f.porta, "controlla_drive": False,
               "attesa_scansione_s": 0.5, "tetto_scansione_s": 10, "attesa_http_s": 5,
               "pausa_dopo_collegamento_s": 0}
        d = cartella_compito(cfg=cfg)
        v = VpnFinta()
        _con_compito(lambda cp: cp.main(vpn_fatta=v), d)
        r = json.load(open(os.path.join(d, "uscita", "risultato.json"), encoding="utf-8"))
        vero([k["sigla"] for k in r["kit"]] == ["KIT249", "KIT560"], f"kit fatti {[k['sigla'] for k in r['kit']]}")
        vero(any(x["sigla"] == "KIT9" for x in r["kit_scartati"]), "kit con indirizzo privato scartato")
        t = r["kit"][0]["telecamere"][0]
        vero(t["fps"] == 15 and t["fps_massimo"] == 25 and t["modello"] == "IPC-HFW5559E1-ZE-IL"
             and t["accelerazione_se_letto_a_25"] == 1.67 and t["codec"] == "H.264" and t["standard"] == "PAL",
             f"telecamera {t}")
        vero(t["sistema"]["seriale"] == "4L0*******23", t["sistema"])
        vero(os.path.exists(os.path.join(d, "uscita", t["foto"])), "foto salvata")
        vero(r["kit"][0]["router"] == "93.x.x.200", "router mascherato")
        vero(len(r["riassunto"]) == 2 and r["riassunto"][0]["fps"] == 15, "riassunto")
        vero(v.chiamate[0] == "rimuovi" and v.chiamate[-1] == "rimuovi" and not v.collegata, "VPN tolta prima e dopo")
        vero(v.chiamate.count("collega") == 2 and v.chiamate.count("scollega") >= 2, "un collegamento per kit")
        vero(r["vpn_tolta"] is True, "vpn_tolta")
        av = open(os.path.join(d, "uscita", "avanzamento.txt"), encoding="utf-8").read().strip().splitlines()
        vero(av[-1].endswith("fatto"), "ultima riga «fatto»")
        vero(segreti_in(d) == [], f"segreti in uscita: {segreti_in(d)}")
        vero(all(m == "GET" for m, _ in f.richieste) and f.sbagliate == 0, "solo GET, nessuna password sbagliata")
        v2 = VpnFinta()
        _con_compito(lambda cp: cp.main(vpn_fatta=v2), d)
        vero(v2.chiamate == [], "finito: non rifa' niente")

        # ripreso a meta': il kit gia' fatto non si rifa'
        d3 = cartella_compito(cfg=cfg)
        os.makedirs(os.path.join(d3, "uscita"))
        json.dump({"kit": [{"sigla": "KIT249", "esito": "fatto: 1"}]},
                  open(os.path.join(d3, "uscita", "risultato.json"), "w"))
        v3 = VpnFinta()
        _con_compito(lambda cp: cp.main(vpn_fatta=v3), d3)
        vero([c for c in v3.chiamate if isinstance(c, tuple)] == [("prepara", "151.20.3.4", ("MSChapv2", "Chap"))],
             f"ripreso: solo il secondo kit {v3.chiamate}")

        # conflitto: il PC ha gia' la rete del kit -> nessun collegamento
        d4 = cartella_compito(cfg=cfg)
        v4 = VpnFinta(reti=[{"rete": "127.0.0.5/8", "dove": "Ethernet"}])
        _con_compito(lambda cp: cp.main(vpn_fatta=v4), d4)
        r4 = json.load(open(os.path.join(d4, "uscita", "risultato.json"), encoding="utf-8"))
        vero("collega" not in v4.chiamate and all(k["esito"].startswith("saltato") for k in r4["kit"]),
             "conflitto: nessun collegamento, kit saltati")

        # la rete del kit non passa dalla VPN -> niente scansione
        d5 = cartella_compito(cfg=cfg)
        n0 = len(f.richieste)
        v5 = VpnFinta(rotta_ok=False)
        _con_compito(lambda cp: cp.main(vpn_fatta=v5), d5)
        r5 = json.load(open(os.path.join(d5, "uscita", "risultato.json"), encoding="utf-8"))
        vero(len(f.richieste) == n0 and "non passa dalla VPN" in r5["kit"][0]["esito"]
             and v5.chiamate.count("scollega") >= 2, "rotta sbagliata: scollegata, nessuna richiesta")

        # VPN rifiutata per l'autenticazione: prova l'altro metodo, poi passa al kit dopo
        d6 = cartella_compito(cfg=cfg)
        v6 = VpnFinta(collega_ok=False, codice=691)
        _con_compito(lambda cp: cp.main(vpn_fatta=v6), d6)
        r6 = json.load(open(os.path.join(d6, "uscita", "risultato.json"), encoding="utf-8"))
        vero(v6.chiamate.count("collega") == 4 and "VPN non collegata" in r6["kit"][0]["esito"],
             f"691: due metodi per kit {v6.chiamate.count('collega')}")
        v7 = VpnFinta(collega_ok=False, codice=809)
        d7 = cartella_compito(cfg=cfg)
        _con_compito(lambda cp: cp.main(vpn_fatta=v7), d7)
        vero(v7.chiamate.count("collega") == 2, "809: un solo tentativo per kit")

        # ferma.txt
        d8 = cartella_compito(cfg=cfg)
        open(os.path.join(d8, "ferma.txt"), "w").write("basta")
        v8 = VpnFinta()
        _con_compito(lambda cp: cp.main(vpn_fatta=v8), d8)
        r8 = json.load(open(os.path.join(d8, "uscita", "risultato.json"), encoding="utf-8"))
        vero("ferma.txt" in r8.get("fermato", "") and "collega" not in v8.chiamate, "ferma.txt")
    finally:
        f.chiudi()

    # accesso_dahua.txt mancante o incompleto
    d = cartella_compito(accesso=None)
    _con_compito(lambda cp: cp.main(vpn_fatta=VpnFinta()), d)
    r = json.load(open(os.path.join(d, "uscita", "risultato.json"), encoding="utf-8"))
    vero("manca accesso_dahua.txt" in r.get("errore", ""), "accesso mancante")
    d = cartella_compito(accesso="vpn_psk=PskSegreta99\nvpn_utente=utentevpn\n")
    v = VpnFinta()
    _con_compito(lambda cp: cp.main(vpn_fatta=v), d)
    r = json.load(open(os.path.join(d, "uscita", "risultato.json"), encoding="utf-8"))
    vero("incompleto" in r.get("errore", "") and "vpn_password" in r["errore"] and v.chiamate == [],
         f"accesso incompleto: {r.get('errore')}")
    vero(segreti_in(d) == [], "nessun segreto nemmeno qui")


if __name__ == "__main__":
    prove_pure()
    prove_telecamera()
    prove_compito()
    print(f"\n{PROVE['ok']} prove giuste, {PROVE['ko']} sbagliate")
    sys.exit(1 if PROVE["ko"] else 0)
