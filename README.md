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
- Ponte 0.11.0 (compito p2p26, pronto e non mandato): `dimezza.json` (dimezza.py, prove in prova_dimezza.py) cerca un
  abbandono in un'ora scaricando 3 s all'inizio, alla fine e a metà finché l'intervallo è sotto 60 s, poi dà l'ultimo
  tratto a Kit_Rifiuti; `nas_extra.json` misura l'originale sul NAS del 776eb78a95 (KIT355). Risultati in
  uscita/dimezza.json e video_nas_extra.json.
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
