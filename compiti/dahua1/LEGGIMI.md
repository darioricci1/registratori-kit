# dahua1: a quanti fps registrano davvero le telecamere Dahua dei kit

Compito 0.1.0 del 17/11/2026. **Pronto, NON mandato.** Domanda: i video `.ssf` sembrano trattati a 25 fps e sul sito
alcuni sembrano accelerati; se le telecamere registrano a meno, un video letto a 25 scorre 25/fps volte più veloce
(15 fps → 1,67 volte). Il compito chiede alle telecamere la loro impostazione.

## Cosa fa

Per ogni kit di `accesso_dahua.txt`:

1. crea la connessione VPN dell'utente «KitRifiuti-Dahua» (L2TP/IPsec, chiave condivisa, `-SplitTunneling`, rotta
   solo per 192.168.1.0/24 con `Add-VpnConnectionRoute`) verso l'indirizzo pubblico del router Teltonika, e si
   collega con `rasdial` (prima MSChapv2+Chap, poi Pap solo se il router rifiuta l'autenticazione);
2. controlla che 192.168.1.1 passi davvero dalla VPN e che la rotta di difetto no; se no, si scollega senza toccare
   niente;
3. scansiona la porta 80 di 192.168.1.3-254 (64 fili, 1,5 s, tetto 90 s; .120 e .170 per primi);
4. a chi risponde manda **una** richiesta senza password a `getDeviceType`: solo se chiede il digest con realm
   «Login to …» (Dahua) legge `getDeviceType`, `getSystemInfo`, `getConfig&name=Encode`, `getConfig&name=VideoStandard`,
   `encode.cgi?action=getConfigCaps&channel=1` (FPSMax) e `snapshot.cgi?channel=1&type=0`;
5. `rasdial /disconnect`, kit dopo; alla fine (anche dopo un errore) `Remove-VpnConnection -Force`.

Tetti: 10 minuti per kit, 90 in tutto, 30 kit (`dahua.json`). Si ferma anche con `ferma.txt` nella cartella del
compito o con un compito nuovo per questo PC su Drive. Ripreso dopo una caduta salta i kit già fatti.

## Cosa NON fa

- Non cambia niente su telecamere, registratori o router: le richieste possibili sono solo quelle in
  `dahua.PERCORSI_AMMESSI` (tutte GET di lettura); setConfig, autoFocus, reboot, PTZ sono rifiutati prima di partire.
- Non tocca il router (.1) né il registratore Focus (.2), nemmeno con la scansione.
- Non manda la password delle telecamere a ciò che non è Dahua (antenne .14/.24/.34…).
- Non riprova una password rifiutata (5 accessi sbagliati bloccano l'utente Dahua per mezz'ora).
- Non si collega se il PC ha già una rete o una rotta su 192.168.1.x: scrive il conflitto e salta i kit.
- Non legge le impostazioni del registratore Focus (che potrebbe registrare a un'altra frequenza) e non misura i
  fotogrammi del flusso RTSP: dice cosa è impostato nella telecamera.

## accesso_dahua.txt (nello zip accanto a compito.py, mai nel repository)

Testo UTF-8, una cosa per riga, `chiave=valore` (solo il primo `=` divide), `#` per i commenti:

```
vpn_psk=<chiave condivisa IPsec>
vpn_utente=<utente L2TP>
vpn_password=<password L2TP>
telecamere_utente=<utente delle telecamere>
telecamere_password=<password delle telecamere>
kit=<sigla>;<indirizzo pubblico del router>
kit=<sigla>;<indirizzo pubblico del router>
```

L'indirizzo pubblico cambia a ogni riavvio del router: va preso dall'SMS poco prima di mandare il compito. Un
indirizzo privato o scritto male scarta quel kit. Se manca un campo il compito si ferma subito e lo scrive in
`risultato.json`. Nel risultato e nei registri i segreti diventano `<vpn_psk>`…, i router `93.x.x.200`, i seriali
`4L0*******23`.

## Uscita

`risultato.json` (`riassunto`: una riga per telecamera con fps, fps massimo, risoluzione, codec,
`accelerazione_se_letto_a_25`; poi per kit: VPN, scansione, telecamere con tutti i flussi — principale normale /
movimento / allarme, secondari — e gli altri apparati), `foto/<kit>_<ultimo numero dell'ip>.jpg`, `registro.txt`,
`avanzamento.txt` (ultima riga «fatto»), `stato.json`.

## Zip e invio

`compito.zip` con, alla radice: `compito.py`, `dahua.py`, `dahua.json`, `accesso_dahua.txt` (niente prove, niente
LEGGIMI). Su Drive «Analisi video» con le proprietà `compito=dahua1` e `pc=<il PC>`, e il segnaposto
`risultato_dahua1.zip`. Il PC deve avere Windows con PowerShell (`Add-VpnConnection`) e `rasdial`; non servono i
permessi di amministratore (connessione dell'utente, rotta nella connessione).

Prove: `python3 prova_dahua1.py` (funzioni pure con le righe della guida Dahua HTTP API 3.26, una telecamera finta
con digest vero su 127.0.0.1, il compito intero con una VPN finta).
