# fps1: a quanti fps registrano davvero tutte le telecamere dei kit

Compito 0.1.0 del 17/11/2026 per il COMPUTERONE. **Pronto, NON mandato.** I `.ssf` sono H.264 grezzo e Kit_Rifiuti
li legge a 25 fps; dagli scarichi passati alcune telecamere ne fanno circa 17,857 (KIT252, 261, 341, 373, 461, 506,
632 su circa 60 misurate) e scorrono 1,4 volte più veloci. Qui la misura di tutte, dal registratore Focus in P2P:
niente VPN, niente password delle telecamere Dahua (a differenza di `dahua1`).

## Come gira

24 ore, al posto del ponte sul COMPUTERONE, anche per la pagina «Registrazioni dei kit». Prende le richieste dal sito
come il ponte (`op=prendi`: il sito rimette in coda tutti i registratori appena il giro prima è finito) e per ognuna,
in un processo a parte (`lavoro.py`) e nello stesso collegamento:

1. la parte del ponte 0.20.1 (`ponte_pezzi.py`, copiato da `p2p_ponte6/compito.py`): canali, minuti di oggi e delle
   24 ore, archivio quando il sito lo chiede, foto delle telecamere una volta al giorno per kit; va al sito con
   `op=esito` appena è pronta, con la versione `p2p_ponte 0.20.1+fps`;
2. per i canali non ancora misurati: 10 secondi di un minuto registrato con i vicini registrati (di giorno, 9-17, se
   c'è; oggi con 10 minuti di margine, poi ieri, poi la notte), e i numeri: `fps_tempi` (mediana degli intervalli fra
   i tempi del registratore, `fps_da_tempi` di focus_nvr), `fps_conteggio` (fotogrammi / tempo fra primo e ultimo),
   `fps_grezzo` (immagini contate nel file H.264/H.265 / durata dichiarata), `fps_sps` (quello che il flusso dichiara),
   risoluzione (registratore e SPS). Il video si cancella subito.

Ogni kit si riprova a ogni giro finché ogni canale ha la misura (un canale senza misura si lascia dopo 6 prove):
così si prendono anche i kit che rispondono solo in certe ore. Se il sito non risponde per 15 minuti, il compito fa
da solo un giro ogni ora sui kit non misurati (`kit.json`, `op=stato` o `registratori.json` dello zip) e non manda
niente.

Un kit alla volta (`insieme` in `fps.json`; più di 1 non è ancora provato, vedi `parallelo1`). Tetto 8 minuti per
kit: poi il processo si uccide, il sito riceve comunque l'esito e il canale in corso conta come una prova. Si ferma
dopo 24 ore dal primo avvio, con `ferma.txt` o con un compito nuovo per questo PC su Drive. Ripreso dopo una caduta,
riparte da `uscita/risultato.json` e `lavori/`.

**Sola lettura**: collegamento, canali, minuti, archivio, riproduzione. Niente impostazioni a registratori o
telecamere.

## Uscita

`uscita/risultato.json`: per kit le ore in cui ha risposto, quante volte sì e quante no, modello, e per canale fps,
fotogrammi, durata, risoluzione, codec, esito, prove; `riassunto` con `telecamere_sotto_24_fps` (dalla più lenta, con
`accelerazione_se_letto_a_25`), conti per frequenza, cosa dichiarano gli SPS, `per_kit` e i kit mai collegati.
`avanzamento.txt` (ultima riga «fatto»), `stato.json`, `guasti/`. Mai UID né password: gli UID stanno in `lavori/`,
che si cancella alla fine.

## Zip e invio

`compito.zip` con, alla radice: `compito.py`, `lavoro.py`, `fps.py`, `ponte_pezzi.py`, `fps.json` (da qui),
`focus_nvr.py` (kit-rifiuti-programma `scripts/`), `FocusNetSDK/` e `focus_accesso.txt` (dallo zip di un compito
precedente, mai in un repository), e se c'è `registratori.json` (per il giro senza sito). Proprietà
`compito=fps1`, `pc=COMPUTERONE`, e il segnaposto `risultato_fps1.zip` su Drive «Analisi video». Chiude il ponte
del COMPUTERONE e ne fa le veci per 24 ore; dopo va rimandato un ponte col nome nuovo.

Prove: `python3 prova_fps1.py [cartella con focus_nvr.py]` (funzioni pure, un H.264 vero di ffmpeg a 125/7 fps se
c'è ffmpeg, il compito intero con sito e libreria finti, la ripresa, il giro senza sito).
