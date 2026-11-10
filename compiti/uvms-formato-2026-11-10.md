# Il database di UVMS (10/11/2026)

Da `uvms_09_11_2026.db` e `uvms_config.ini` che Dario ha dato in chat (le copie stanno solo nello scratchpad: il
database contiene le password cifrate dei registratori e non entra nel repository). Qui solo la struttura.

## Com'è fatto

SQLite 3 (user_version 24). Le tabelle che contano:

- `groups` (115 righe): `id, name, parent_group_id, seq`. Un gruppo per cliente o comune («ALEA-Bertinoro»,
  «SAN LAZZARO DI SAVENA», «VARI»). Nessun gruppo ha un padre (`parent_group_id` sempre 0): l'elenco è piatto.
- `sites` (525 righe): un registratore. `group_id` → `groups.id`; `name` è «NNN - via» (il numero del kit davanti);
  `ip` è l'UID P2P di 20 caratteri (479 righe), un indirizzo (6) o altro (40); `port` 9010, `webport` 80;
  `userid` `admin` (523) o un altro utente (2); `password` cifrata (base64, quasi sempre 16 byte: un blocco AES);
  `use_p2p` 1 (519) o 0; `model` FN-5004 (121), FNR-3004 (107), FNR-3204 (81), vuoto (208), FT-2004/FX-2004 (3);
  `version` il firmware; `totalcamera` 4 (315) o 9 (191); `selected_ch` «1-4», «1-8», …; coordinate e altri campi vuoti.
- `channels` (2.823 righe): `siteid` → `sites.id`, `name` («CH1»…), `seq` (da 0) e impostazioni dell'immagine.
- `users` (1 riga): l'utente del programma UVMS, con la sua password cifrata.
- Le tabelle `*_on`, `favorite*`, `schedule*`, `sites_reg`, `sites_info`, `custom_site*` sono vuote.

`uvms_config.ini`: percorsi (catture in `C:/RIPRESE`), opzioni di visualizzazione e finestre; niente elenco dei
registratori.

## La password

La stessa password (quella comune dei registratori, che Dario ha detto) compare con 241 cifrati diversi: la cifratura
dipende da qualcosa della riga, oppure ha un sale. Quindi non basta copiare un cifrato da una riga all'altra senza
provarlo. Per il collegamento diretto non serve: `focus_nvr.py` e il ponte P2P usano la password in chiaro, data a
parte (focus_accesso.txt).

## Si può generare dall'anagrafica kit?

Sì per tutto tranne la password: gruppo = comune o cliente, `name` = «numero - via», `ip` = UID P2P, `port` 9010,
`webport` 80, `userid` admin, `use_p2p` 1, `totalcamera` e `selected_ch` dai canali, una riga di `channels` per canale.
Mancano due cose: l'UID P2P nell'anagrafica (oggi lo manda Giacomo per mail) e il modo di cifrare la password. Prova
da fare: un database con un sito nuovo e la password copiata da un sito che funziona, aperto da Barbara in UVMS; se
UVMS si collega, il cifrato non dipende dalla riga e si può generare tutto.

## Usato già

L'elenco dei 519 registratori con UID (gruppo, nome, numero del kit, modello, canali, firmware; niente password) è
nella tabella Neon `nvr_remoto.registratori` della pagina https://prova-nvr-remoto.vercel.app: il kit si sceglie
scrivendo numero, via o comune, e l'UID si compila da solo.
