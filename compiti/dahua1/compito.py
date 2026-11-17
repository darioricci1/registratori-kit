"""
Compito dahua1 (registratori-kit): a quanti fotogrammi al secondo registrano DAVVERO le telecamere Dahua dei kit?
VERSION 0.1.0 (17/11/2026)

Perche': i video .ssf dei registratori sembrano trattati a 25 fps, e sul sito alcuni sembrano accelerati. Se le
telecamere registrano a meno (15, 12, 10...), il video letto a 25 scorre 25/fps volte piu' veloce. Questo compito
chiede alle telecamere la loro impostazione, e basta.

SOLA LETTURA. Il compito non cambia MAI un'impostazione di telecamere, registratori o router: alle telecamere solo
GET di getDeviceType, getSystemInfo, getConfig Encode e VideoStandard, getConfigCaps e una snapshot (elenco chiuso in
dahua.PERCORSI_AMMESSI: tutto il resto e' rifiutato prima di partire). Niente setConfig, autoFocus, reboot, PTZ. Al
registratore Focus (.2) e al router (.1) non si manda niente, nemmeno la scansione della porta 80. Alle cose sulla porta
80 che non sono Dahua (antenne...) va una sola richiesta senza password e mai la password delle telecamere. La password
delle telecamere si manda al massimo una volta per richiesta e, se una telecamera la rifiuta, non le si chiede piu'
niente (5 accessi sbagliati bloccano l'utente Dahua).

Sul PC si cambia SOLO una connessione VPN dell'utente, «KitRifiuti-Dahua», che il compito crea, usa e alla fine
cancella (Remove-VpnConnection -Force), anche dopo un errore. -SplitTunneling: il PC non perde internet ne' Drive, e
nella VPN passa solo 192.168.1.0/24 (Add-VpnConnectionRoute). Prima di collegarsi controlla che il PC non abbia gia'
una rete o una rotta su 192.168.1.x: se c'e', il kit si salta e si scrive. Dopo il collegamento controlla che
192.168.1.1 passi davvero dalla VPN: se no, si scollega senza scansionare niente.

Per ogni kit (accesso_dahua.txt, kit=<sigla>;<indirizzo pubblico del router>): VPN L2TP/IPsec con chiave condivisa
-> rasdial -> scansione della porta 80 su 192.168.1.3-254 (fili, tetto di tempo) -> per ogni Dahua le letture e la
snapshot -> rasdial /disconnect. Tetti: 10 minuti per kit, 90 minuti in tutto (dahua.json).

Si ferma da solo: alla fine; al tetto; se nella cartella del compito compare ferma.txt; se su Drive arriva un compito
nuovo per questo PC (come i ponti). Ripreso dopo una caduta, salta i kit gia' fatti; finito, non rifa' niente.

Uscita (uscita/, che Kit_Rifiuti manda su Drive in risultato_dahua1.zip): risultato.json (per kit e telecamera: ip,
modello, fps, fps massimo, risoluzione, bitrate, codec, GOP, esito, tempi), foto/<kit>_<ip>.jpg, registro.txt,
avanzamento.txt (ultima riga «fatto»), stato.json. Nessun segreto: password, chiave, utenti, indirizzi dei router e
seriali passano tutti da dahua.maschera.
"""
import json
import os
import subprocess
import sys
import time
import traceback

VERSION = "0.1.0"
C = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, C)
U = os.path.join(C, "uscita")
PC = os.environ.get("COMPUTERNAME", "PC")[:40]
NOFIN = 0x08000000 if os.name == "nt" else 0

import dahua as dh   # noqa: E402

DIFETTI = {
    "nome_vpn": "KitRifiuti-Dahua",
    "rete_kit": "192.168.1.0/24",
    "salta": ["192.168.1.1", "192.168.1.2"],          # router e registratore Focus: niente
    "noti": ["192.168.1.120", "192.168.1.170"],        # davanti nella scansione
    "porta": 80,
    "fili_scansione": 64,
    "attesa_scansione_s": 1.5,
    "tetto_scansione_s": 90,
    "attesa_http_s": 10,
    "autenticazioni": [["MSChapv2", "Chap"], ["Pap"]],  # una prova per elenco, si passa alla dopo solo se non entra
    "cifratura": "Optional",
    "attesa_rasdial_s": 75,
    "attesa_powershell_s": 60,
    "pausa_dopo_collegamento_s": 3,
    "tetto_kit_min": 10,
    "tetto_min": 90,
    "solo": [],                                       # sigle: se c'e', solo quei kit
    "massimo_kit": 30,
    "controlla_drive": True,
}

ERRORI_RASDIAL = {
    623: "la connessione VPN non si trova nella rubrica",
    628: "collegamento chiuso dall'altra parte prima di finire",
    651: "il dispositivo ha dato errore",
    691: "utente o password della VPN rifiutati",
    718: "il router non ha risposto in tempo alla parte PPP",
    720: "nessun protocollo di rete in comune (PPP)",
    732: "parametri PPP non concordati",
    741: "il router non accetta la cifratura chiesta",
    742: "il router non accetta la cifratura chiesta",
    768: "cifratura dei dati non riuscita",
    781: "IPsec: certificato mancante (la chiave condivisa non e' stata usata)",
    787: "IPsec: il PC non riesce a farsi riconoscire dal router",
    788: "IPsec: parametri di sicurezza non concordati",
    789: "IPsec non riuscito: chiave condivisa sbagliata o parametri IPsec diversi",
    809: "nessuna risposta su UDP 500/4500: router spento, indirizzo cambiato, porte chiuse o NAT (vedi LEGGIMI)",
    812: "il metodo di autenticazione non e' permesso dal router",
    868: "nome del server non risolto",
    919: "il metodo di autenticazione non va bene al router",
}


def spiega_rasdial(codice):
    try:
        c = int(codice)
    except (TypeError, ValueError):
        return str(codice)
    return ERRORI_RASDIAL.get(c, f"errore {c}")


# ------------------------------------------------------------------ registri (sempre mascherati)

MASCHERE = []


def _scrivi_riga(nome, t):
    os.makedirs(U, exist_ok=True)
    with open(os.path.join(U, nome), "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%H:%M:%S ") + t + "\n")


def reg(t):
    """Una riga nel registro (uscita/registro.txt), mascherata."""
    t = dh.maschera(t, MASCHERE)
    _scrivi_riga("registro.txt", t)
    print(t, flush=True)


def av(t):
    """Una riga nell'avanzamento (e nel registro), mascherata."""
    t = dh.maschera(t, MASCHERE)
    _scrivi_riga("avanzamento.txt", t)
    _scrivi_riga("registro.txt", t)
    print(t, flush=True)


def scrivi_json(nome, dati):
    """In uscita/, prima in un .tmp; il testo intero passa dalla maschera (anche quello che non dovrebbe averne)."""
    p = os.path.join(U, nome)
    testo = dh.maschera(json.dumps(dati, ensure_ascii=False, indent=1, default=str), MASCHERE)
    with open(p + ".tmp", "w", encoding="utf-8") as fh:
        fh.write(testo)
    os.replace(p + ".tmp", p)


def leggi_json(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def carica_cfg():
    cfg = dict(DIFETTI)
    f = os.path.join(C, "dahua.json")
    d = leggi_json(f)
    if isinstance(d, dict):
        cfg.update({k: v for k, v in d.items() if not k.startswith("_")})
    return cfg


# ------------------------------------------------------------------ la VPN di Windows

def esegui(cmd, attesa, env_in_piu=None):
    """Un comando senza finestra -> (codice, testo mascherato). Mai un'eccezione col comando dentro: TimeoutExpired e
    gli altri errori riportano il comando, e il comando di rasdial ha la password."""
    env = dict(os.environ)
    env.update(env_in_piu or {})
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=attesa, env=env, stdin=subprocess.DEVNULL,
                           creationflags=NOFIN)
        testo = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
        return r.returncode, dh.maschera(testo.strip(), MASCHERE)[-2000:]
    except subprocess.TimeoutExpired:
        return -1, f"tempo scaduto ({attesa} s)"
    except OSError as ex:
        return -2, dh.maschera(f"{type(ex).__name__}: {ex.strerror or ''}", MASCHERE)


def powershell(script, attesa, env_in_piu=None):
    return esegui(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
                   "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + script], attesa, env_in_piu)


PS_RETI = (
    "$a = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | ForEach-Object { "
    "@{rete=($_.IPAddress + '/' + $_.PrefixLength); dove=$_.InterfaceAlias} }); "
    "$r = @(Get-NetRoute -AddressFamily IPv4 -ErrorAction SilentlyContinue | ForEach-Object { "
    "@{rete=$_.DestinationPrefix; dove=$_.InterfaceAlias} }); "
    "ConvertTo-Json -Compress -Depth 3 @($a + $r)"
)

PS_PREPARA = (
    "$ErrorActionPreference='Stop'; $n=$env:KR_VPN_NOME; "
    "if (Get-VpnConnection -Name $n -ErrorAction SilentlyContinue) { "
    "  rasdial $n /disconnect | Out-Null; Remove-VpnConnection -Name $n -Force }; "
    "$aut = $env:KR_VPN_AUT -split ','; "
    "Add-VpnConnection -Name $n -ServerAddress $env:KR_VPN_SERVER -TunnelType L2tp -L2tpPsk $env:KR_VPN_PSK "
    "  -AuthenticationMethod $aut -EncryptionLevel $env:KR_VPN_CIFRATURA -SplitTunneling:$true "
    "  -RememberCredential:$false -Force; "
    "Add-VpnConnectionRoute -ConnectionName $n -DestinationPrefix $env:KR_RETE_KIT; "
    "$c = Get-VpnConnection -Name $n; "
    "ConvertTo-Json -Compress @{split=[bool]$c.SplitTunneling; tipo=[string]$c.TunnelType; "
    "  rotte=@($c.Routes | ForEach-Object { [string]$_.DestinationPrefix })}"
)

PS_VERIFICA = (
    "$n=$env:KR_VPN_NOME; "
    "$f = Find-NetRoute -RemoteIPAddress $env:KR_PROVA_IP -ErrorAction SilentlyContinue | "
    "  Where-Object { $_.InterfaceAlias } | Select-Object -First 1; "
    "$ip = @(Get-NetIPAddress -InterfaceAlias $n -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
    "  ForEach-Object { $_.IPAddress + '/' + $_.PrefixLength }); "
    "$d = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
    "  Where-Object { $_.InterfaceAlias -eq $n }; "
    "ConvertTo-Json -Compress @{interfaccia=[string]$f.InterfaceAlias; ip_vpn=$ip; difetto_su_vpn=[bool]$d}"
)

PS_RIMUOVI = (
    "$n=$env:KR_VPN_NOME; "
    "if (Get-VpnConnection -Name $n -ErrorAction SilentlyContinue) { "
    "  rasdial $n /disconnect | Out-Null; Remove-VpnConnection -Name $n -Force; 'tolta' } else { 'non c''era' }"
)


def _json_ultima_riga(testo):
    for riga in reversed((testo or "").splitlines()):
        riga = riga.strip()
        if riga.startswith("{") or riga.startswith("["):
            try:
                return json.loads(riga)
            except ValueError:
                return None
    return None


class VpnWindows:
    """La connessione «KitRifiuti-Dahua» dell'utente: creata per un kit, collegata, controllata, scollegata, tolta.
    I segreti passano a PowerShell nelle variabili d'ambiente del solo processo figlio (mai nella riga di comando);
    a rasdial servono sulla riga di comando (rasdial non li legge altrove): l'errore e l'uscita sono mascherati."""

    def __init__(self, cfg, acc):
        self.cfg, self.acc = cfg, acc
        self.nome = cfg["nome_vpn"]

    def _env(self, **x):
        e = {"KR_VPN_NOME": self.nome, "KR_RETE_KIT": self.cfg["rete_kit"]}
        e.update(x)
        return e

    def reti_pc(self):
        codice, testo = powershell(PS_RETI, self.cfg["attesa_powershell_s"], self._env())
        d = _json_ultima_riga(testo)
        if d is None:
            return None, f"reti del PC non lette ({codice}: {testo[-200:]})"
        return ([d] if isinstance(d, dict) else d), ""

    def prepara(self, server, autenticazione):
        codice, testo = powershell(PS_PREPARA, self.cfg["attesa_powershell_s"], self._env(
            KR_VPN_SERVER=server, KR_VPN_PSK=self.acc["vpn_psk"], KR_VPN_AUT=",".join(autenticazione),
            KR_VPN_CIFRATURA=self.cfg["cifratura"]))
        d = _json_ultima_riga(testo)
        if codice != 0 or not isinstance(d, dict):
            return False, {"errore": f"connessione VPN non creata ({codice}): {testo[-300:]}"}
        if not d.get("split"):
            return False, {"errore": "la connessione non e' in split tunneling: non mi collego"}
        return True, d

    def collega(self):
        cmd = ["rasdial", self.nome, self.acc["vpn_utente"], self.acc["vpn_password"]]
        codice, testo = esegui(cmd, self.cfg["attesa_rasdial_s"])
        if codice == 623:   # rubrica dell'utente: rasdial a volte guarda solo quella del sistema
            pbk = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Network", "Connections", "Pbk", "rasphone.pbk")
            if os.path.exists(pbk):
                codice, testo = esegui(cmd + ["/PHONEBOOK:" + pbk], self.cfg["attesa_rasdial_s"])
        if codice != 0:
            return False, {"codice": codice, "errore": spiega_rasdial(codice) if codice > 0 else testo,
                           "uscita": testo[-300:]}
        return True, {"codice": 0}

    def verifica(self, ip_prova):
        codice, testo = powershell(PS_VERIFICA, self.cfg["attesa_powershell_s"], self._env(KR_PROVA_IP=ip_prova))
        d = _json_ultima_riga(testo)
        if not isinstance(d, dict):
            return False, {"errore": f"rotta non letta ({codice}: {testo[-200:]})"}
        if d.get("difetto_su_vpn"):
            return False, dict(d, errore="la rotta di difetto passa dalla VPN: niente split tunneling, mi scollego")
        if d.get("interfaccia") != self.nome:
            return False, dict(d, errore=f"{ip_prova} non passa dalla VPN (passa da «{d.get('interfaccia')}»)")
        return True, d

    def scollega(self):
        return esegui(["rasdial", self.nome, "/disconnect"], 30)

    def rimuovi(self):
        return powershell(PS_RIMUOVI, self.cfg["attesa_powershell_s"], self._env())


# ------------------------------------------------------------------ le telecamere

def foto_nome(sigla, ip):
    s = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in sigla)[:40]
    return f"{s}_{ip.split('.')[-1]}.jpg"


def leggi_telecamera(ip, sigla, cfg, acc, scadenza):
    """Tutte le letture di una telecamera (solo se e' una Dahua). Ritorna il dict del risultato."""
    t0 = time.time()
    tc = dh.Telecamera(ip, acc["telecamere_utente"], acc["telecamere_password"], cfg["porta"], cfg["attesa_http_s"])
    out = {"ip": ip, "dahua": False}
    try:
        st, sfida, realm = tc.sonda()
        out["sonda_http"] = st
        if st != 401 or not sfida:
            out["esito"] = f"non e' una Dahua (getDeviceType senza password: HTTP {st})"
            return out
        if not dh.sembra_dahua(sfida):
            out["esito"] = "chiede una password ma non sembra una Dahua: password non mandata"
            out["realm"] = dh.maschera_seriale(realm)
            return out
        out["dahua"] = True
        letture = {}
        for nome, p in (("tipo", dh.PERCORSI_AMMESSI[0]), ("info", dh.PERCORSI_AMMESSI[1]),
                        ("encode", dh.PERCORSI_AMMESSI[2]), ("standard", dh.PERCORSI_AMMESSI[3]),
                        ("caps", dh.PERCORSI_AMMESSI[4])):
            if time.time() > scadenza:
                out["tetto"] = True
                break
            st, corpo = tc.leggi(p, 2 * 1024 * 1024)
            letture[nome] = (st, corpo.decode("utf-8", "replace"))
            if tc.rifiutato:
                break
        if tc.rifiutato:
            out["esito"] = "password delle telecamere rifiutata: non chiedo altro (blocco dopo 5 tentativi)"
            return out
        testo = {k: v[1] for k, v in letture.items() if v[0] == 200}
        out["http"] = {k: v[0] for k, v in letture.items()}
        tipo = dh.chiave_valore(testo.get("tipo"))
        info = dh.chiave_valore(testo.get("info"))
        encode = dh.leggi_encode(testo.get("encode"))
        caps = dh.leggi_caps(testo.get("caps"))
        standard = dh.chiave_valore(testo.get("standard")).get("table.VideoStandard")
        out.update(dh.riassunto_telecamera(tipo, info, encode, caps, standard))
        out["sistema"] = {"deviceType": info.get("deviceType"), "processor": info.get("processor"),
                          "seriale": dh.maschera_seriale(info.get("serialNumber"))}
        out["flussi"] = encode
        out["capacita"] = caps
        if time.time() < scadenza:
            st, jpg = tc.leggi(dh.PERCORSI_AMMESSI[5])
            if st == 200 and jpg[:2] == b"\xff\xd8":
                os.makedirs(os.path.join(U, "foto"), exist_ok=True)
                nome = foto_nome(sigla, ip)
                with open(os.path.join(U, "foto", nome), "wb") as fh:
                    fh.write(jpg)
                out["foto"] = "foto/" + nome
                out["foto_kb"] = round(len(jpg) / 1024)
            else:
                out["foto"] = None
                out["foto_http"] = st
        out["esito"] = "letta" if out.get("fps") is not None else "letta in parte (Encode senza FPS)"
    except dh.Rifiutata as ex:
        out["esito"] = f"rifiutata: {ex}"
    except Exception as ex:   # noqa: BLE001
        out["esito"] = f"errore: {type(ex).__name__}: {dh.maschera(str(ex)[:200], MASCHERE)}"
    finally:
        out["richieste"] = tc.richieste
        out["kb"] = round(tc.byte / 1024)
        out["secondi"] = round(time.time() - t0, 1)
    return out


def lavora_kit(kit, cfg, acc, vpn, conflitti_pc, scadenza_tutto, reti_pc=None):
    """Un kit intero, con la VPN sempre scollegata alla fine. Ritorna il dict del kit."""
    t0 = time.time()
    scadenza = min(scadenza_tutto, t0 + float(cfg["tetto_kit_min"]) * 60)
    r = {"sigla": kit["sigla"], "router": dh.maschera_ip(kit["server"]), "inizio": time.strftime("%Y-%m-%d %H:%M:%S"),
         "telecamere": [], "altri": []}
    if conflitti_pc:
        r["esito"] = "saltato: il PC ha gia' una rete o una rotta su " + cfg["rete_kit"]
        r["conflitti"] = conflitti_pc
        r["secondi"] = 0
        return r
    collegato = False
    try:
        vpn_info = {}
        for aut in cfg["autenticazioni"]:
            ok, d = vpn.prepara(kit["server"], aut)
            if not ok:
                r["esito"] = "VPN non creata"
                vpn_info.setdefault("tentativi", []).append(dict(d, autenticazione=aut))
                break
            t1 = time.time()
            ok, d = vpn.collega()
            vpn_info.setdefault("tentativi", []).append(dict(d, autenticazione=aut, secondi=round(time.time() - t1, 1)))
            if ok:
                collegato = True
                break
            if d.get("codice") not in (691, 812, 919, 732, 741, 742):   # solo un problema di autenticazione prova l'altra
                break
        r["vpn"] = vpn_info
        if not collegato:
            r.setdefault("esito", "VPN non collegata: " + str((vpn_info.get("tentativi") or [{}])[-1].get("errore")))
            return r
        time.sleep(float(cfg["pausa_dopo_collegamento_s"]))
        ok, d = vpn.verifica(cfg["salta"][0] if cfg["salta"] else "192.168.1.1")
        r["vpn"]["verifica"] = d
        if not ok:
            r["esito"] = "collegata ma la rete del kit non passa dalla VPN: niente scansione (" + str(d.get("errore")) + ")"
            return r
        ip_vpn = d.get("ip_vpn") or []
        ip_vpn = [ip_vpn] if isinstance(ip_vpn, str) else ip_vpn
        for x in ip_vpn:
            if dh.reti_in_conflitto(reti_pc or [], x, ignora=(cfg["nome_vpn"],)):
                r["esito"] = "l'indirizzo dato dalla VPN cade in una rete del PC: mi scollego senza scansione"
                return r
        indirizzi = dh.indirizzi_da_provare(cfg["rete_kit"], cfg["salta"], cfg["noti"])
        tetto = max(5.0, min(float(cfg["tetto_scansione_s"]), scadenza - time.time() - 30))
        aperti, sec, finita = dh.scansione(indirizzi, cfg["porta"], int(cfg["fili_scansione"]),
                                           float(cfg["attesa_scansione_s"]), tetto)
        r["scansione"] = {"provati": len(indirizzi), "porta_80_aperta": aperti, "secondi": sec, "completa": finita}
        reg(f"{kit['sigla']}: porta {cfg['porta']} aperta su {', '.join(aperti) or 'nessuno'} ({sec} s)")
        for ip in aperti:
            if time.time() > scadenza:
                r["tetto_kit"] = True
                break
            t = leggi_telecamera(ip, kit["sigla"], cfg, acc, scadenza)
            (r["telecamere"] if t.get("dahua") else r["altri"]).append(t)
            reg(f"{kit['sigla']} {ip}: {t.get('esito')} modello {t.get('modello')} fps {t.get('fps')} "
                f"(massimo {t.get('fps_massimo')}) {t.get('risoluzione')} {t.get('codec')}")
        lette = [t for t in r["telecamere"] if t.get("fps") is not None]
        r["esito"] = f"fatto: {len(lette)} telecamere lette su {len(r['telecamere'])} Dahua trovate"
    except Exception as ex:   # noqa: BLE001
        r["esito"] = f"errore: {type(ex).__name__}: {dh.maschera(str(ex)[:300], MASCHERE)}"
    finally:
        if collegato or r.get("vpn"):
            codice, testo = vpn.scollega()
            r["scollegato"] = codice == 0 or "not connected" in testo.lower() or "non connesso" in testo.lower()
        r["secondi"] = round(time.time() - t0, 1)
    return r


# ------------------------------------------------------------------ fermate

def compito_nuovo_su_drive():
    """Su Drive c'e' un compito con un altro nome per questo PC (o per nessuno)? Allora questo si chiude (come i ponti)."""
    try:
        import drive_alma
        f = drive_alma.trova("compito.zip", (C, os.path.dirname(sys.executable)))
        pr = (f or {}).get("appProperties") or {}
        try:
            pc = drive_alma.nome_del_pc()
        except Exception:   # noqa: BLE001
            pc = PC
        nome, per = str(pr.get("compito") or ""), str(pr.get("pc") or "")
        return bool(nome) and nome != os.path.basename(os.path.normpath(C)) and (not per or per.upper() == str(pc).upper())
    except Exception:   # noqa: BLE001
        return False


def motivo_per_fermarsi(cfg, scadenza, ultimo_drive):
    if time.time() > scadenza:
        return f"tetto di {cfg['tetto_min']} minuti"
    if os.path.exists(os.path.join(C, "ferma.txt")):
        return "ferma.txt nella cartella del compito"
    if cfg.get("controlla_drive") and time.time() - ultimo_drive[0] > 300:
        ultimo_drive[0] = time.time()
        if compito_nuovo_su_drive():
            return "su Drive c'e' un compito nuovo per questo PC"
    return None


# ------------------------------------------------------------------ il giro

def main(vpn_fatta=None):
    """vpn_fatta: solo per le prove (una VPN finta); sul PC e' None e si usa VpnWindows."""
    os.makedirs(U, exist_ok=True)
    f_ris, f_stato = os.path.join(U, "risultato.json"), os.path.join(U, "stato.json")
    stato = leggi_json(f_stato) or {}
    if stato.get("fase") == "finito":
        av("compito gia' finito: non rifaccio niente")
        av("fatto")
        return
    cfg = carica_cfg()
    t_inizio = time.time()
    scadenza = t_inizio + float(cfg["tetto_min"]) * 60
    prima = leggi_json(f_ris) or {}
    ris = {"compito": "dahua1", "versione": VERSION, "pc": PC, "inizio": time.strftime("%Y-%m-%d %H:%M:%S"),
           "ripreso": bool(prima.get("kit")), "sola_lettura": list(dh.PERCORSI_AMMESSI),
           "parametri": {k: cfg[k] for k in DIFETTI}, "kit": prima.get("kit") or []}

    def segna(fase):
        stato.update(fase=fase, ora=time.strftime("%Y-%m-%d %H:%M:%S"), versione=VERSION)
        scrivi_json("stato.json", stato)

    av(f"dahua1 {VERSION} su {PC}")
    segna("in corso")
    vpn = None
    try:
        try:
            testo = open(os.path.join(C, "accesso_dahua.txt"), encoding="utf-8", errors="replace").read()
        except OSError:
            testo = None
        if testo is None:
            ris["errore"] = "manca accesso_dahua.txt accanto a compito.py: niente da fare (vedi LEGGIMI.md)"
            av(ris["errore"])
            return
        acc, problemi = dh.leggi_accesso(testo)
        MASCHERE[:] = dh.sostituzioni(acc)
        ris["accesso_problemi"] = problemi
        for p in problemi:
            av("accesso_dahua.txt: " + p)
        if not dh.accesso_completo(problemi):
            ris["errore"] = "accesso_dahua.txt incompleto: " + "; ".join(p for p in problemi if p.startswith(("manca", "nessuna")))
            av(ris["errore"])
            return
        if os.name != "nt" and vpn_fatta is None:
            ris["errore"] = "serve Windows (VPN con PowerShell e rasdial)"
            av(ris["errore"])
            return
        scelti, scartati = dh.scegli_kit(acc["kit"], cfg.get("solo"), cfg.get("massimo_kit"))
        ris["kit_scartati"] = scartati
        av(f"{len(scelti)} kit da fare, {len(scartati)} scartati")
        vpn = vpn_fatta or VpnWindows(cfg, acc)
        c, t = vpn.rimuovi()   # una connessione rimasta da un giro caduto
        reg(f"pulizia iniziale della connessione {cfg['nome_vpn']}: {t or c}")
        reti, perche = vpn.reti_pc()
        if reti is None:
            ris["errore"] = "non riesco a leggere le reti del PC, non mi collego: " + perche
            av(ris["errore"])
            return
        conflitti = dh.reti_in_conflitto(reti, cfg["rete_kit"], ignora=(cfg["nome_vpn"],))
        reti_lan = [x for x in reti if not str(x.get("rete", "")).startswith("127.")
                    and not str(x.get("rete", "")).endswith("/32")]   # le reti vere del PC, non i singoli host
        ris["rete_pc_in_conflitto"] = conflitti
        if conflitti:
            av(f"ATTENZIONE: il PC ha gia' {', '.join(sorted({x['rete'] for x in conflitti}))} "
               f"(conflitto con {cfg['rete_kit']}): i kit si saltano")
        fatti = {k["sigla"].upper() for k in ris["kit"] if not str(k.get("esito", "")).startswith("errore")}
        ris["kit"] = [k for k in ris["kit"] if k["sigla"].upper() in fatti]
        ultimo_drive = [time.time()]
        for kit in scelti:
            if kit["sigla"].upper() in fatti:
                continue
            motivo = motivo_per_fermarsi(cfg, scadenza, ultimo_drive)
            if motivo:
                ris["fermato"] = motivo
                av("mi fermo: " + motivo)
                break
            av(f"{kit['sigla']}: comincio")
            r = lavora_kit(kit, cfg, acc, vpn, conflitti, scadenza, reti_lan)
            ris["kit"].append(r)
            scrivi_json("risultato.json", ris)
            av(f"{kit['sigla']}: {r.get('esito')} in {r.get('secondi')} s")
    except Exception as ex:   # noqa: BLE001
        ris["errore"] = f"{type(ex).__name__}: {dh.maschera(str(ex)[:400], MASCHERE)}"
        av(ris["errore"])
        reg(dh.maschera(traceback.format_exc()[-2000:], MASCHERE))
    finally:
        if vpn is not None:
            try:
                vpn.scollega()
                c, t = vpn.rimuovi()
                ris["vpn_tolta"] = c == 0
                reg(f"connessione {cfg['nome_vpn']} alla fine: {t or c}")
            except Exception as ex:   # noqa: BLE001
                ris["vpn_tolta"] = False
                reg("connessione non tolta: " + dh.maschera(str(ex)[:200], MASCHERE))
        ris["riassunto"] = riassunto(ris.get("kit") or [])
        ris["fine"] = time.strftime("%Y-%m-%d %H:%M:%S")
        ris["minuti"] = round((time.time() - t_inizio) / 60, 1)
        scrivi_json("risultato.json", ris)
        segna("finito")
        av("fatto")


def riassunto(kit):
    """Una riga per telecamera letta, per leggere il risultato a colpo d'occhio."""
    righe = []
    for k in kit:
        for t in k.get("telecamere") or []:
            righe.append({"kit": k.get("sigla"), "ip": t.get("ip"), "modello": t.get("modello"), "fps": t.get("fps"),
                          "fps_massimo": t.get("fps_massimo"), "risoluzione": t.get("risoluzione"),
                          "codec": t.get("codec"), "accelerazione_se_letto_a_25": t.get("accelerazione_se_letto_a_25"),
                          "esito": t.get("esito")})
    return righe


if __name__ == "__main__":
    main()
