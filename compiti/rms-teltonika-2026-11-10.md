# Teltonika RMS: cosa si legge dalle API (10/11/2026)

Token personale dell'account assistenza@ (società #43204 ALMA SICUREZZA), salvato come segreto di rete dell'ambiente per
rms.teltonika-networks.com: non sta in nessun file. API: https://rms.teltonika-networks.com/api/...

- **Router: 582** (RUT951 481, RUT950 36, RUTX14 21, RUT241 19, altri). 448 hanno «KIT» nel nome («KIT MVT 602»).
- **Stato al 10/11 ore 12:30**: dei 448 kit 293 online e 155 offline (alcuni da anni: KIT MVT 204 dal 29/10/2022).
- **Crediti RMS che scadono entro 30 giorni: 77** (auto_extend_credit = 0 sul primo letto): da controllare.
- **Accesso remoto ai registratori**: 1.031 configurazioni, 449 verso un indirizzo; 446 sono
  192.168.1.2:80 http, cioè la pagina del registratore Focus dietro il router. 448 router hanno «NVR MVT nnn».
  Da programma: POST /devices/connect con l'id della configurazione apre un link temporaneo (RMS Connect).
- Campi utili di ogni router: name, serial, model, status, last_connection_at, firmware, signal, connection_type,
  credit_expire_date, coordinate (cell tower), temperature.

Prossimi passi: un link RMS Connect al registratore di un kit e capire come lo Smart Web Viewer chiede le registrazioni
(per scaricarle da programma); lo stato dei kit nel gestionale o in Mappa Kit.

## RMS Connect provato (10/11/2026, pomeriggio)

- La chiamata giusta: `POST /api/devices/connect/{id accesso}` con `{"duration": secondi}` risponde con `meta.channel`;
  poi `GET /status/channel/{channel}` (senza `/api`) finché l'ultimo messaggio è `completed` e il link è in `link`.
- Provato su KIT MVT 524 e KIT MVT 250, tutti e due online: RMS risponde `error 102 «Device has no data left!»`.
- `GET /api/credits`: tutti i pacchetti comprati da Alma (dal 2022 al pacchetto Management 3 anni del 23/01/2026) hanno
  `credit_left 0`; l'azienda ha `credits_left 0`. RMS Connect verso un apparecchio dietro al router consuma traffico
  (pochi GB gratis, poi si paga con i crediti): è finito. Elenco, stato e accesso al router stesso restano gratis.
- Pagina di prova: https://prova-nvr-remoto.vercel.app (cartella `prova-nvr-remoto/`, progetto Vercel a sé, pubblicato
  con l'API e non collegato al repository: i push non lo ricostruiscono). Il token RMS lo scrive chi la usa.
