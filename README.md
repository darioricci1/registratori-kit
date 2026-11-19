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
    Dal 14/11 (2.30.0) anche «Telecamere da sistemare»: sfocate, morbide, coperte da un palo o da rami, dalla misura di
    nitidezza di Kit_Rifiuti (`analisi/nitidezza_telecamere.py` di kit-rifiuti-programma) più le note a occhio. Il file
    `dati/telecamere_da_sistemare.json` lo rifà `python3 dati/telecamere_da_sistemare.py` (le note a occhio nuove vanno in
    `OCCHIO_IN_PIU`) e lo serve `op=sistemare` di `api/p2p.js` dietro l'accesso (`includeFiles` in `vercel.json`).
  - Dal 14/11 (2.31.0) anche «Schemi delle ore»: per ogni kit installato il gruppo (si spegne di giorno e riparte al
    tramonto, solare che si spegne di notte, una telecamera sola...), la causa probabile e cosa fare, dalle ore registrate e
    dall'ANAGRAFICA KIT. Il file `dati/schemi_ore.json` lo rifà `python3 dati/schemi_ore.py <cartella> --scarica <chiave>`
    (sola lettura) e lo serve `op=schemi`; il ragionamento e la riga per kit in `analisi-ore-registrazione-2026-11-14.md`.
  - Dal 18/11 (2.43.0) anche «Velocità delle telecamere»: gli fps veri di ogni telecamera (fotogrammi contati in ~10 s
    di registrazione diviso il tempo vero), prima quelle sotto 24 fps con quanto scorre veloce il video letto a 25 come fa
    Kit_Rifiuti, i kit che non hanno mai risposto, e gli fps sotto il canale in «Kit e telecamere». Il file `dati/fps.json`
    lo rifà `python3 -I dati/fps.py <risultato.json>` dal risultato del compito fps1 (`risultato_fps1.zip` su Drive
    «Analisi video», file `risultato.json`) e lo serve `op=fps`. Misura del 17-18/11: 865 telecamere in 298 kit, 82 sotto
    24 fps in 44 kit (63 a ~18 fps), 156 kit mai risposti. Attenzione: il campo `fps` del compito è la mediana degli
    intervalli del registratore e dice 25 anche quando i fotogrammi arrivano a gruppi (il compito ne contava 72 sotto 24);
    `dati/fps.py` usa `fps_conteggio`.
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
- Compito p2p_ponte42 (ponte 0.24.0 col guardiano, guardiano.py 0.1.0, allunga.py 0.2.0; zip in `c42/compito.zip` dello
  scratchpad, segnaposto `risultato_p2p_ponte42.zip` creato da Dario): caricato in compito_2.zip con tipo leggero il 19/11
  alle 9:41 al posto del 41, preso alle 9:42 e partito alle 9:45 sul COMPUTERONE, 72 ore (fino al 22/11 verso le 9:45). Due cose nuove:
  - Il guardiano. Il 40 si era chiuso il 19/11 alle 8:50 dopo 78 minuti con 3221225477 (0xC0000005): `guasto_memoria.txt`
    dice focus_nvr.Registratore.chiudi, riga 543, la Disconnect di una prova P2P dentro il `with`, quindi dentro la DLL,
    dove un try non arriva. Ora compito.py senza `PONTE_FIGLIO=1` fa solo il guardiano: rilancia lo stesso exe con
    «--compito <cartella>» (Kit_Rifiuti lo trova e lo ferma come prima) e il figlio fa il ponte di sempre; se cade per un
    guasto della libreria (0xC0000005, 0xC0000374, 0xC0000409, ...) lo rilancia dopo 20 s con una riga «guardiano: il
    ponte e' caduto con ... in focus_nvr.py:543 chiudi. Lo rilancio» in avanzamento.txt. Tetti: 6 rilanci in un'ora
    (oltre aspetta che l'ora si liberi), 40 in tutto, mai dopo 3 cadute di fila nei primi 2 minuti; un codice che non è
    un guasto (1, chiuso da Kit_Rifiuti) passa a Kit_Rifiuti com'è. `PONTE_FINE` tiene l'ora di fine del compito, un
    figlio rilanciato rilegge UVMS e ANAGRAFICA KIT dopo 12 ore. La riga `t_fine = time.time() + DURATA` resta dov'era:
    allunga_lavoro, pilota_lavoro e scorta_lavoro eseguono il ponte fino a lì (il guardiano scatta solo in `__main__`).
    Prove in prova_guardiano.py (anche un figlio vero che cade per accesso alla memoria).
  - Le 7 «ore da guardare» di video.html (Dario, 19/11: il video vero), in `allunga.json` del compito (copia in
    `ore_vere_allunga.json`, con gli UID già messi): 10 minuti attorno al momento su un canale, dalla più vecchia
    (pos108 e pos148 del 30/10). Con `"copia_video": true` copia_indietro mette gli mp4 anche in
    `uscita/allunga/<evento>/video/`, ricompressi in H.264 a 1280 pixel crf 28 (se ffmpeg non ce la fa, l'originale),
    con `video.json` (MB prima e dopo): arrivano su Drive nel risultato, che Kit_Rifiuti ricarica ogni 30 minuti; gli
    originali restano in `~/kr_lavori/allunga/p2p_ponte42/<evento>/video`. Mentre un evento scarica, il ponte non prende
    prove (la libreria è sua). Un evento già finito in uscita non si rifà se il guardiano rilancia il ponte
    (allunga.gia_fatto; solo per allunga.json, la coda di Dario decide da sé). Nello zip c'è di nuovo movimento.py:
    allunga.entro lo importa (nel 40 e nel 41 mancava, ma nessun allungamento era partito). Prove in prova_copia_video.py.
- Compito p2p_ponte41 (ponte 0.22.0, lo zip del 40 con il nome nuovo in LEGGIMI.txt e ponte.json; `c41/compito.zip`
  dello scratchpad): caricato in compito_2.zip con tipo leggero alle 9:08 del 19/11, preso alle 9:12 e partito alle 9:13
  sul COMPUTERONE. Sostituito dal 42.
- Compito p2p_ponte40 (ponte 0.22.0, peso_giro.py 0.1.0; COMPUTERONE alla 0.99.18 dalle 7:25 del 19/11, caricato in compito_2.zip
  con tipo leggero alle 7:26, partito alle 7:32 del 19/11, fino al 22/11 verso le 7:30): il ponte rimesso in giro sul COMPUTERONE
  dopo movimento1, che il 19/11 alle 5:50 si era chiuso per il compito conteggi20261119 delle statistiche su
  compito.zip (l'indice di movimento era già fatto, movimento_fatto alle 5:32): da allora «Registrazioni dei kit» non si
  aggiornava e gli allungamenti non si scaricavano. Come movimento1 (giro, archivi, allungamenti di op=allungare, UVMS e
  ANAGRAFICA KIT) senza rifare l'indice di movimento (niente movimento.json né movimento.py nel compito), 72 ore
  (`ponte.json`). Caricato con `analisi/posto_compito.py` di kit-rifiuti-programma in compito_2.zip/compito_3.zip con
  `--tipo leggero` (Kit_Rifiuti 0.99.18: gira insieme agli altri compiti e il ponte si chiude solo per un compito
  nuovo nel suo posto, KR_POSTO_COMPITO, drive_alma 0.6.0 `posto_cercato`; compito_nuovo_su_drive non è cambiato).
  Zip in `compito_p2p_ponte40/compito.zip` dello scratchpad (focus_nvr.py, FocusNetSDK/ e focus_accesso.txt da
  movimento1); segnaposto `risultato_p2p_ponte40.zip` creato da Dario. Caduto alle 8:50 con 3221225477 (sopra).
  - Quanto pesa il giro (Dario, 19/11: «richiede molto?»): per ogni prova i MB grezzi dal registratore delle foto di 3 s
    (`mb` di ogni foto) e dello scarico di 15 s delle prove a mano, i MB letti e scritti dal processo del ponte mentre
    dura la prova (GetProcessIoCounters: comprende il collegamento P2P e le domande dell'archivio, che non sono file),
    i secondi di processore (time.process_time del ponte, tutti i fili; ffmpeg a parte no) e, a parte, quelli
    dell'archivio. Va nell'esito al sito (`peso`, `archivio_peso`), in `uscita/peso_prove.jsonl` (una riga per prova) e
    in `uscita/peso_giri.json` (per giro: prove, registratori, MB, MB per prova, secondi di processore del ponte e quota
    di un processore, i 15 registratori più pesanti). Il giro non ha un numero dal sito: ne comincia uno nuovo quando
    torna un registratore già visto o dopo 20 minuti senza prove del giro. Prove: `compiti/p2p_ponte6/prova_peso_giro.py`.
- Compito movimento1 (ponte 0.21.0, movimento.py 0.2.0, caricato su Drive il 19/11 alle 5:06, preso alle 5:19 e partito alle 5:20 sul COMPUTERONE; il p2p_ponte39 si è chiuso alle 5:15 e il suo lavoro lo fa movimento1 fino al 21/11 sera; vedi
  sotto). L'indice di movimento dei registratori Focus, che può essere il primo filtro gratis prima dell'analisi (la
  prova ferma dice 77 s per ora-telecamera: senza un filtro servono circa 7 PC). `movimento.json` di
  `prepara_movimento.py` (sola lettura: registratori.json di positive1d, le ore della prova ferma, op=video del sito
  kit-rifiuti del 18/11, banco_ore_120.json, banco_positive.json di positive1/1c/1d): 422 abbandoni dal 22/10 in 184
  registratori (sito «ok» 229, scorta 14/11 155, prova ferma 142, positive1 58, 1c 24, 1d 24; uniti se si toccano),
  187 ore vuote note, 660 giorni-telecamera. Il compito, dopo quei 184, prende anche tutti i registratori che hanno
  risposto al ponte nelle ultime 24 ore (op=stato). Per ognuno: modo di registrazione di ogni canale
  (OnRecordModeStatus) e tipi dei 1440 minuti di ieri; dove il movimento si registra, i tipi dei giorni chiesti, e per
  ogni abbandono «coperto» (un minuto movimento o sensore nella finestra, ±2 minuti) / «non coperto» / «non sul disco»,
  con la quota di minuti e di ore «movimento» nelle ore senza clip note delle stesse telecamere e nelle ore vuote del
  banco (anche a pezzi di 5 minuti). In uscita/movimento.json anche i tipi grezzi in testo, per rifare i conti qui.
  LIMITI: alzati solo i totali (collegamenti 30 → 420, chiamate 600 → 5000, minuti 60 → 420), collegamento 75 → 150 s.
  Stima: 3-5 ore. Gira dentro il ponte (in un filo suo, il giro continua come il 39), `ponte.json` 64 ore (fino al 21/11
  sera, quando sarebbe finito il 39). Perché così: il ponte 39 per un compito nuovo del COMPUTERONE scrive «su Drive c'è
  un compito nuovo: chiudo questo» e poi «fatto», e Kit_Rifiuti 0.99.16 (`sospeso_da_righe`: «compito nuovo» più
  «ferm» o «non fatt») non lo conta come sospeso: il 39 si chiuderebbe per sempre. Zip in
  `compito_movimento1/compito.zip` dello scratchpad (con focus_nvr.py, FocusNetSDK/ e focus_accesso.txt dal 39);
  proprietà compito=movimento1, pc=COMPUTERONE; il segnaposto `risultato_movimento1.zip` c'è già. Prima di caricarlo,
  compito.zip su Drive deve essere già stato preso (il 19/11 alle 5 era positive1d per il 2026-002, preso).
- Compito p2p_ponte39 (mandato al COMPUTERONE il 18/11 alle 21:40, preso alle 21:49 e partito alle 21:50, 72 ore): il ponte 0.20.1 rimandato dopo fps1, che
  chiudendosi alle 6:27 del 18/11 aveva lasciato «Registrazioni dei kit» senza aggiornamenti e gli allungamenti senza
  nessuno che li scaricasse. Codice uguale al compito 38 (`compiti/p2p_ponte6`, coda_allunga 0.3.0: allungamenti solo da
  op=allungare del sito kit-rifiuti, niente coda automatica né `allunga_urgenti.json`); zip in
  `compito_p2p_ponte39/compito.zip` dello scratchpad col suo LEGGIMI.txt. Il segnaposto `risultato_p2p_ponte39.zip` lo crea
  Dario (l'account di servizio non ha spazio su Drive: 403 storageQuotaExceeded); senza, il risultato resta sul PC. Nomi
  già usati per il ponte: fino a p2p_ponte38 (il 38 è vissuto 35 minuti il 16/11): il prossimo è p2p_ponte40.
- Compito fps1 0.1.0: FATTO (COMPUTERONE, 17/11 11:54 - 18/11 06:27, 1113 minuti, chiuso da un compito nuovo; ogni kit
  provato una volta sola). Risultato in `dati/fps.json` e nella pagina. Il compito (`compiti/fps1/LEGGIMI.md`, zip in `compito_fps1/compito.zip` dello
  scratchpad): gli fps veri di tutte le telecamere dal registratore Focus in P2P (i video sembrano accelerati: alcune
  fanno 17,857 e lette a 25 vanno 1,4 volte più veloci). 24 ore sul giro del sito al posto del ponte (stessi invii a
  op=esito con il codice del ponte 0.20.1 in `ponte_pezzi.py`, foto una volta al giorno per kit), e per ogni canale non
  ancora misurato 10 secondi di un'ora di giorno: fps dai tempi del registratore, dal file grezzo e dall'SPS. Per kit le
  ore in cui ha risposto e quante volte no; riassunto «telecamere sotto 24 fps». Segnaposto `risultato_fps1.zip`.
- Compito dahua1 0.1.0 (pronto il 17/11 e NON mandato; `compiti/dahua1/LEGGIMI.md`): SOLA LETTURA degli fps impostati
  nelle telecamere Dahua dei kit (i video sembrano accelerati), via VPN L2TP/IPsec del router Teltonika in split
  tunneling. Serve `accesso_dahua.txt` nello zip (solo su Drive di Alma) con gli indirizzi pubblici del giorno, e il
  segnaposto `risultato_dahua1.zip`.
- Compito parallelo1 0.1.0 (pronto il 16/11 e NON mandato, zip in `compito_parallelo1/compito.zip` dello scratchpad; codice
  e spiegazione in `compiti/parallelo1/LEGGIMI.md`): più registratori insieme. Sugli stessi 40 kit che rispondono, sola
  lettura leggera: N=1 come il ponte, strada A (una libreria, N=4/8/16 Connect insieme, ritorni smistati per hSERVER) e
  strada B (N=2/4/8 processi, ognuno con la sua libreria). Si ferma da solo al primo crash o a +5 punti di falliti, tetto 2
  ore. Vince chi a N=8 fa il giro in meno di un quarto del tempo di N=1 senza più falliti. Serve il segnaposto
  `risultato_parallelo1.zip`; chiude il ponte del COMPUTERONE, che poi va rimandato.
- Compito p2p_ponte35b (mandato al COMPUTERONE il 14/11 alle 20:40): la scorta del 35 per le 190 ore che né il 35 né il 36
  hanno fatto (il 36, stesso scorta.json con la finestra 00-23:59, la mattina del 14/11 ne ha fatte 30, comprese le 15 del
  35). Codice uguale al 35 (ponte 0.18.0); finestra 19-07, stessi limiti; parti in `scorta35b_1..7.zip`, Qwen con
  l'etichetta c35b, risultato in `risultato_p2p_ponte35b.zip`. Un compito nuovo su compito.zip lo chiude entro 10 minuti.
- Ponte 0.20.0 (compito p2p_ponte38, pronto il 16/11 mattina e NON mandato, zip nello scratchpad della sessione): si
  allunga solo quello che chiede Dario (16/11: «sono semplicemente delle dubbie, che io se ritengo posso anche chiedere di
  allungare»). Il giro della coda chiede a op=allungare del sito kit-rifiuti (biglietto dell'account di servizio, aud
  https://mappakit.alma/kit-rifiuti) le clip dove Dario ha premuto «⤢ Allunga» in video.html, le scrive in
  `~/kr_lavori/allunga/confermate.json` per Kit_Rifiuti, le scarica (coda_allunga 0.3.0, fuori dal tetto per kit) e
  rimanda al sito quelle chiuse (POST op=allungare {fatti}). Non legge più `coda.json` (Kit_Rifiuti 0.99.10 la lascia
  vuota: le 460 richieste automatiche del 16/11 non si scaricano) né `allunga_urgenti.json` (le 39 sono fatte).
- Ponte 0.19.0 (compito p2p_ponte37, pronto il 16/11 notte e NON mandato, zip nello scratchpad della sessione): la coda
  degli allungamenti di Kit_Rifiuti, che nessun ponte leggeva (la patch del 12/11 in kit-rifiuti-programma
  `analisi/compiti/ponte-0.15.0/` non era mai stata applicata: le versioni 0.15-0.18 sono nate senza). Sul COMPUTERONE
  legge `~/kr_lavori/allunga/coda.json` dopo 5 minuti, poi ogni ora e ogni 5 minuti finché c'è lavoro; davanti le
  urgenti del compito (`allunga_urgenti.json`, le 39 clip tagliate dei casi limite ancora entro 24 giorni, dalla più
  vicina alla scadenza, fuori dal tetto di 3 per kit al giorno). Scelta e registro in `coda_allunga.py` 0.2.0 (prove in
  `prova_coda_allunga.py`, anche un giro intero col ponte vero e il lavoro finto); video in
  `~/kr_lavori/allunga/coda/<evento>/`, che Kit_Rifiuti monta come «<id>-al». In uscita `allunga_coda.json` (il giro),
  `allunga_coda_stato.json` (stati, urgenti fatte e no) e `allunga_diagnosi.json` (i risultati già sul disco e cosa ne
  ha fatto Kit_Rifiuti: il compito 30 ne ha 8 «fatto/parziale» e Kit_Rifiuti ne risulta averne trattati 2). Il ponte
  non si chiude più per un compito di un altro PC (`compito_mi_chiude`: prima ogni compito nuovo su Drive lo spegneva,
  e i ponti 34-36 sono vissuti 698, 31 e 73 minuti) e `ponte.json` («durata_ore», 1-168) ne decide la vita: 72 ore.
  Senza `vlm.py`, scorta e prove grandi: Qwen non parte. Serve il segnaposto `risultato_p2p_ponte37.zip`. Stima per le
  39: 13-28 GB dai registratori (120 s prima e 180 dopo su 2-4 canali), poche ore. Dettagli e ordine:
  kit-rifiuti-programma `analisi/allungamenti-2026-11-16.md`.
- Ponte 0.18.0 (compito p2p_ponte35, pronto il 14/11 mattina e NON mandato, zip nello scratchpad della sessione:
  `compito35/compito.zip` col suo LEGGIMI.txt): la **scorta serale** e la **catena dell'ora con Qwen**.
  - Si prepara con `python3 prepara_scorta.py <video.json> <stato_nvr.json> <elenco.tsv.gz> <cartella dei giri>
    <eventi_corrette.json> scorta.json --lancio AAAA-MM-GG` (sola lettura: op=video leggero del sito kit-rifiuti, op=stato
    di questo sito, l'elenco di ArchiveData, i giri di Guarda e op=evento delle clip corrette da Dario per i suoi riquadri).
    Il 14/11: 153 ore positive con 165 abbandoni sicuri ancora sul registratore (68 kit), di cui 96 nella catena (47 kit;
    28 mai viste, 59 gia' nella prova grande e 9 nella pilota: campo `vista`), e 67 negative degli stessi kit e
    telecamere. Fuori: CONFERIMENTI, casi limite, «no» di Dario; la parte cieca, le telecamere senza zona e gli EX
    fanno solo la scorta.
  - Nel compito: `scorta.json` (niente `pilota.json`, `lungo.json`, `pezzi_vlm.json`), `scorta.py`, `scorta_lavoro.py`,
    `b_tavolino.py`, `vlm.py` 0.5.0, `vlm_giudica.py`, oltre a quello di sempre. Il ponte fa scorta.json una volta sola
    (segno `scorta_fatto.txt`), solo dalle 19 alle 7 (`finestra`), al massimo 11 ore di lavoro, un processo per ora:
    miniature dei minuti e 90 s a piena risoluzione di ogni abbandono (A); per le ore della catena «insieme», i pezzi di
    ~100 s dei primi 3 candidati e le carte prima/dopo come nel compito 34 (B). Tetti: 1.000 MB per kit, 30 GB in
    tutto, 15 GB liberi sul disco. Video e miniature restano sul PC (`~/kr_lavori/scorta/p2p_ponte35`); su Drive le
    miniature in zip da al massimo 180 MB nei segnaposto `scorta35_1.zip`... (li crea Dario, insieme a
    `risultato_p2p_ponte35.zip`), nel risultato solo json e immagini piccole (~100-120 MB). Alla fine Qwen giudica le
    carte (domanda v3, `giudizi_Qwen3-VL-4B-Instruct_v3_c35.json`) e `uscita/catena.json` mette insieme ore, candidati,
    verita' (`vero`, `tocca_vero`, `altro_noto`) e giudizio di Qwen, con i conti prima e dopo Qwen.
  - Stima: ~10 ore di registratore e ~1 ora di Qwen, ~23-24 GB dai registratori (al massimo 1 GB per kit), ~24 GB sul PC.
  - Prove: `prova_scorta.py` (funzioni pure, il giro con la finestra e i tetti, un'ora col registratore finto, il ponte
    vero con i processi a parte e un Qwen finto).
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
- Ponte 0.12.0 (compito p2p28; dal 19/11 il codice è in movimento1, sopra): `movimento.json` (movimento.py,
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
