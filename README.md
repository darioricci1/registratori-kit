# registratori-kit

Dario, 10/11: «è un progetto diverso, lo sposterei in un'altra conversazione e in un GitHub nuovo». Questa cartella
(`prova-nvr-remoto/` dentro `darioricci1/kit-rifiuti-programma`) va portata in un repository suo; questo file dice tutto
quello che serve per continuare senza la conversazione di prima.

## Cosa fa
- Sito https://prova-nvr-remoto.vercel.app (progetto Vercel `prova-nvr-remoto`, id prj_KBYtn53Y7ypOFgykHk028awsoSws,
  pubblicato con l'API di Vercel, NON collegato a git: i push non lo ricostruiscono). Si entra con l'accesso unico di
  Alma (ALMA_PORTA = gestionale; il sito è nell'elenco del gestionale, Sincronizzazioni → Accesso unico).
  - `public/index.html`: prove singole (P2P a mano, scelta del kit dall'elenco UVMS) e la parte RMS (token Teltonika
    scritto nella pagina, solo nel browser). RMS Connect oggi non va: Alma ha 0 crediti RMS («Device has no data left!»).
  - `public/stato.html`: «Registrazioni dei kit». Una riga per ogni telecamera che funziona, raggruppate per kit:
    adesso (registra / ferma / niente), registrazione più vecchia e più recente, giorni, media, percentuale di ogni
    giorno sulle 24 ore dal più recente, foto. In cima «Cose che non tornano» col confronto con l'ANAGRAFICA KIT.
  - `api/p2p.js`: la coda e i dati (Neon, database Alma, schema `nvr_remoto`: richieste, registratori, camera,
    camera_storia, archivio, anagrafica, pc). Il PC entra col biglietto Google dell'account di servizio di Alma
    (aud https://mappakit.alma/nvr-remoto), la pagina con la sessione dell'accesso unico (o un token RMS valido).
  - `api/rms.js`: passa le chiamate a Teltonika RMS col token scritto nella pagina.
  - `api/_accesso.js`, `api/entra.js`: l'accesso unico, copiato da acquisti.
- I PC fanno da ponte, perché la libreria Focus (FocusNetSDK, DLL Windows di Voyager: non si distribuisce fuori da Alma)
  gira solo lì. Compiti di Kit_Rifiuti via Drive (`compito.zip` nella cartella «Analisi video», proprietà `compito` e `pc`):
  - `analisi/compiti/p2p_ponte1`: prove a mano (sul PC «Dario», fino alle 23 circa del 10/11);
  - `p2p_ponte2`: il giro leggero di ogni ora su tutti i registratori (sul COMPUTERONE, 24 ore dal 10/11 13:30);
  - `p2p_ponte3` 0.3.3: il giro con la foto di ogni telecamera e «si vede / nera / tutta uguale / niente»; l'archivio
    di ogni registratore (prima e ultima registrazione, minuti registrati per giorno, ultimi 90 giorni) letto una
    volta al giorno; ogni giorno il database UVMS più recente dal NAS («PROGRAMMA Uvms e database») e l'ANAGRAFICA KIT
    (foglio «Elenco KIT Date Registrazioni», id 1I3-xl5rlQu0xCUA9mj9c5BC_zR27Tioy0X6FRwXqKRw). Mandato al PC «Dario»: lo
    prende quando finisce p2p_ponte1. Nel compito.zip ci sono anche focus_nvr.py, la cartella FocusNetSDK e
    focus_accesso.txt con la password comune: sta solo su Drive di Alma, mai nel repository.
  Un ponte gira 10-24 ore poi si chiude; per rimandarlo: nome di compito nuovo (il PC segna i nomi già fatti).

## Segreti
- La password dei registratori e i file di UVMS: solo su Drive di Alma e nello scratchpad, mai nel repository, nei
  commit, nei messaggi o nelle pagine. Alcuni registratori hanno un'altra password (es. kit 136 Civitella).
- Il token RMS è di Dario: non si salva da nessuna parte.
- Neon: le variabili ALMA_* del progetto sono «sensitive».

## Da fare
- Ponte 0.16.0 (compito p2p_ponte33, mandato al COMPUTERONE il 13/11 alle 12:50): il secondo passaggio della prova
  grande. `prepara_secondo.py` fa `secondo.json` (138 pezzi da 2-3 minuti intorno ai primi 3 candidati «insieme» di
  ogni ora, una telecamera, dalle ore piu' vecchie), che va nel compito come `lungo.json` «leggero»: scarico a piena
  risoluzione, Kit_Rifiuti da riga di comando, in uscita solo dati e 3 immagini per pezzo (risultato piccolo, non piu'
  lo zip da 923 MB del 32). Al massimo 2 analisi insieme. Risultato in `risultato_p2p_ponte33.zip`.
- Ponte 0.15.0 (compito p2p_ponte32, pronto e NON mandato, zip nello scratchpad della sessione del 12/11): la prova
  grande del metodo «insieme» (analisi-abbandono-in-un-ora.md, sezione 6). `grande.json` (prepara_grande.py, prove in
  prova_grande.py) va nel compito come `pilota.json` con `solo_minuti`: 71 ore positive da 40 kit e 150 negative (+30
  riserve), solo le 72 miniature dei minuti per ora (pilota.py 0.2.0). Il disco gira: va mandato presto.
- Ponte 0.13.0 (compito p2p30, pronto e NON mandato): `allunga.json` (allunga.py, processo per evento allunga_lavoro.py,
  prove in prova_allunga.py; l'elenco lo rifà `python3 prepara_allunga.py <chiave.json>`, sola lettura dai due siti).
  Per 34 eventi con la clip tagliata o sospetta, 60 s prima e 120 s dopo la clip (e i buchi delle telecamere più corte)
  canale per canale; mp4 continui con l'ora vera sul COMPUTERONE (`~/kr_lavori/allunga/p2p_ponte30/<evento>/video`), in
  uscita fogli dei fotogrammi e `allunga.json` (esito, MB, secondi, chiamate, buchi, sincronia). Il disco dei
  registratori gira (2-4 settimane, qualcuno 2 mesi): l'11/11 solo 9 eventi su 34 erano ancora sul registratore, non i due
  di Dario (7b56bc2ce8 e cc577ca6e7: KIT560 dal 23/10, KIT324 dal 28/10); il 0b936b6d4f (KIT341) sparisce verso il 12/11.
  Il compito 28 si è chiuso l'11/11 alle 18:11 con 3221225477 (0xC0000005) fra due prove P2P, col filo principale in
  Python: IPOTESI una funzione di ritorno chiamata dalla libreria su un Registratore già liberato; dalla 0.13.0 i
  Registratori non si liberano (CIMITERO) e faulthandler scrive le pile in `uscita/guasto_memoria.txt`. Per mandarlo
  serve anche il segnaposto `risultato_p2p_ponte30.zip` su Drive (Kit_Rifiuti 0.90: un posto per compito).
- Ponte 0.12.0 (compito p2p28, pronto e NON mandato: fase di audit, decide Dario): `movimento.json` (movimento.py,
  prove in prova_movimento.py). La libreria Focus non ha ricerca di file né registro degli allarmi: l'unico indice
  storico del movimento è il tipo di ognuno dei 1440 minuti di GetRecordDaily (continua / movimento / sensore), che
  esiste solo se il registratore è impostato a registrare il movimento; il compito lo legge per i 5 casi di
  dimezza.json con il modo impostato (OnRecordModeStatus), e prova GetThumbImage (una miniatura al minuto per ±30 min,
  cambio nella zona dei cassonetti). Limiti in LIMITI di movimento.py: 100 MB, 60 minuti, 600 chiamate, 30
  collegamenti in tutto; 25 MB, 15 minuti, 120 chiamate, 61 miniature per caso; tempo massimo per ogni chiamata.
- Ponte 0.11.0 (compito p2p26, pronto e non mandato): `dimezza.json` (dimezza.py, prove in prova_dimezza.py) cerca un
  abbandono in un'ora scaricando 3 s all'inizio, alla fine e a metà finché l'intervallo è sotto 60 s, poi dà l'ultimo
  tratto a Kit_Rifiuti; `nas_extra.json` misura l'originale sul NAS del 776eb78a95 (KIT355). Risultati in
  uscita/dimezza.json e video_nas_extra.json. `owl.json` rifà la misura di OWLv2 in un processo a parte
  (owl_misura.py): nel compito 25 onnxruntime non si caricava accanto alla libreria Focus.
- Correzioni di Barbara del 10/11 (mail «Controllo UVMS»): doppioni tolti da UVMS (spariscono dalla pagina alla prossima
  lettura del database UVMS); i «più telecamere» erano canali vuoti contati per sbaglio (corretto nella pagina 2.16.0);
  i «meno telecamere» hanno quasi tutti un ODM aperto, che ora la pagina mostra (ponte 0.5.0); 128, 136 e 155 sono DVR con
  la password messa in laboratorio: va chiesta e scritta in focus_accesso.txt; 507 e 338 hanno il contratto sospeso.
- Su Drive il compito si chiama «p2p_ponte7» (codice in compiti/p2p_ponte6, 0.6.2): il PC «Dario» aveva già preso la 0.6.0 col nome p2p_ponte6, e il nome nuovo lo fa chiudere e ripartire. Domani: controllare che il ponte 0.5.0 abbia mandato gli ODM e che i doppioni siano spariti.
- Repository nuovo (lo crea Dario), poi collegare il progetto Vercel a quel repository.
- Riga nel registro del software del gestionale (già c'è «prova-nvr-remoto», da aggiornare: anagrafica e UVMS dal NAS).
- Domani: guardare le prime foto e gli archivi, e le «Cose che non tornano» col giro completo.
- Prime cose che non tornano (10/11; il kit 998 Roma è il kit di prova di Dario, escluso): kit 200 su due registratori in UVMS
  (VIANO / 200 e VARI / 200 NVR diretto); vie scritte diverse per 419, 597, 651.
