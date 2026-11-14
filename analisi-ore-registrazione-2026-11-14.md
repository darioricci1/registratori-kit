# Le ore di registrazione dei kit: che problema hanno e dove (14/11/2026)

Dati: gli archivi dei registratori letti dal giro (ore registrate di ogni telecamera dal 27/10, 24 ore per giorno, sito
registratori-kit, op=ore e op=stato), l'ANAGRAFICA KIT e la scheda ODM del foglio «Elenco KIT Date Registrazioni» letti
oggi, le telecamere da sistemare (nitidezza). Per ogni kit si guarda solo dal giorno dopo l'installazione: prima il kit
era in magazzino o in un'altra posizione. Il conto si rifà con `python3 dati/schemi_ore.py <cartella> --scarica <chiave>`;
la pagina https://registratori-kit.vercel.app/stato.html ha la vista «Schemi delle ore» con le stesse righe.

## In breve

1. **I kit a sola batteria (42Ah senza pannello) si spengono di giorno e ripartono al tramonto: 16 kit, tutti a
   batteria.** Si ricaricano dalla pubblica illuminazione, che dà corrente solo di notte. Si spengono fra le 7 e le 12 e
   ripartono fra le 16 e le 18: di 199 spegnimenti brevi dei kit a batteria, 168 finiscono nell'ora delle 17, quando si accendono i lampioni. Nessuno
   dei 37 kit a 220V o Townet lo fa. Di questi 16: 2 sono già tornati a posto (236, 578), 2 hanno la batteria cambiata
   da due giorni (504, 515: da ricontrollare), **2 si spengono ancora con la batteria nuova** (230 dal 05/11, 398 dal
   04/11: lì il guasto è la carica, cioè caricabatterie/power, fusibile o il collegamento alla pubblica), e 10 vanno
   sistemati sul posto: **345, 347 e 606 non registrano mai di giorno**; 219, 440 e 518 reggono poche ore dopo l'alba;
   267, 276, 385 e 490 hanno cominciato da poco (dall'01/11 all'08/11), la batteria sta cedendo.
2. **I kit solari sono il problema più grande.** Su 94 installati, 55 non rispondono mai al giro (nessuna ora letta), 11
   non sono nemmeno nell'elenco UVMS, e dei 27 di cui si leggono le ore solo 3 registrano sempre. Lo schema è l'opposto
   dei kit a lampione: si spengono la sera o di notte (fra le 22 e le 4) e ripartono la mattina fra le 8 e le 10, quando il
   pannello ricarica; dopo i giorni nuvolosi restano spenti giorni interi. In Puglia i solari si spengono negli **stessi
   giorni** (31/10, 2-3/11, 8/11, 11-13/11) a Bari, Canosa, Manfredonia e Molfetta: è il tempo, non il singolo kit. 8 solari
   sono spenti quasi sempre (241, 455, 524, 667, 679 al nord; 320, 498, 513 in Puglia): lì è il pannello (ombra), la
   batteria o il regolatore. 455 e 667 si accendono solo qualche ora di giorno col sole: la batteria non tiene
   più. Con le giornate di novembre un pannello da 140W e una 42Ah non bastano dove c'è poco sole.
3. **Quando un kit si spegne, di solito si spegne tutto insieme**: nelle ore in cui almeno una telecamera non registra, nel
   63% dei casi non registra nessuna (alimentazione o registratore). Nel resto è una telecamera sola: 34 kit registrano
   ma hanno una telecamera spenta o mai vista. **Il satellite si guasta molto più del cavo**: fino a 28 problemi su 223
   satelliti (13%) contro 13 su 896 telecamere via cavo (1,5%).
4. **Le cause che non tornano coi dati**: la registrazione a movimento non fa buchi (237 telecamere hanno tratti «a
   sensore», 210 registrano tutte le ore); l'orologio dei registratori non è avanti in nessuno, e quelli a lampione si
   spengono e riaccendono proprio all'alba e al tramonto, quindi l'ora è giusta; il disco pieno non fa buchi, fa solo
   sparire i giorni vecchi (ogni registratore tiene in media 15 giorni, 10 kit meno di 10); le telecamere sfocate non
   c'entrano (33 kit su 35 con una sfocata registrano sempre).

## I gruppi e cosa fare

| Gruppo | Kit | Problema probabile | Cosa fare |
|---|---|---|---|
| A. si spegne di giorno, riparte al tramonto | 16 (tutti a batteria) | pubblica illuminazione + batteria che non regge il giorno | sul posto: batteria; dove è già nuova (230, 398) caricabatterie/power, fusibile, collegamento alla pubblica |
| B. solare, si spegne di notte o per giorni | 23 (tutti solari) | il pannello non ricarica abbastanza (novembre, nuvole); 8 quasi sempre spenti: pannello, batteria o regolatore | sul posto: batteria e pannello; per l'inverno batteria più grande o secondo pannello dove c'è poco sole |
| C. spento per giorni, poi ripartito | 7 | 5 su 7 ripartiti fra le 11 e le 15, in orario di lavoro: un intervento (o un kit spostato) | niente, controllare che l'ODM dica cosa è stato fatto |
| D. fermo adesso | 1 (352, Unione Valli) | non registra dal 31/10, tutto il kit | sul posto: alimentazione |
| E. spento a giorni interi | 1 (593, Foggia) | spento dal 05/11 al 10/11 senza uno schema | sul posto: alimentazione e registratore |
| F. buchi sparsi | 2 (396, 521) | 97% delle ore, niente di ricorrente | niente |
| G. kit acceso, una telecamera no | 34 | telecamera, cavo o (più spesso) satellite | da remoto foto/live, poi sul posto |
| H. risponde ma senza ore | 4 | installato da poco (363) o archivio senza le ore | niente per ora |
| M. nessun registratore in UVMS | 15 (11 solari) | non si può leggere | controllare UVMS |
| N. non risponde, ore mai lette | 91 (55 solari, 31 a batteria, 4 a 220V) | dalle ore non si può dire: spento o senza rete | SMS di riavvio e SIM; per i solari è il sospetto principale batteria scarica |
| OK, sempre verde | 268 | | niente |

## Le ipotesi, una per una

**Lampione (pubblica illuminazione che si spegne di giorno).** In anagrafica la colonna BATT dice solo «42Ah» per 317
kit installati: niente pannello, niente 220V. Gli ODM vecchi dicono da dove si ricaricano («probabile problema di
pubblica», «spegnimento dalle 8 alle 17, controllare power e batteria», «si spegne dalle 10 alle 21, problema batteria»,
«risponde solo di sera»). Sostengono: 16 kit con lo schema, tutti a batteria; dei tratti spenti brevi (meno di 30 ore)
dei kit a batteria, 125 su 199 cominciano alle 7-8 e 182 finiscono alle 16-17. Contraddicono: nessuno (0 su 37 kit a
220V o Townet, 0 su 27 solari con le ore). Riscontri negli ODM: 236 «fino al 30/10 kit spento dalle 8 alle 18:30; dal
31/10 acceso» (le ore dicono lo stesso: dal 31/10 non succede più); 267 «kit spento dalle 15 alle 17»; 440 «risponde solo
di sera»; 606 «batteria scarica»; 578 power cambiato il 30/10 e da allora va. Quanto regge la batteria dopo l'alba dice
quanto è messa male: 0-1 ore (morta o non si carica) per 12 kit, 2-5 ore per 219, 267, 440 e 518. Certezza: alta.

**Solare che si spegne di notte o d'inverno.** Sostengono: 23 solari su 27 con le ore hanno buchi; dei loro 34 tratti spenti
brevi, 24 cominciano fra le 22 e le 6 e 26 finiscono fra le 8 e le 12 (l'opposto dei kit a lampione); in Puglia i giorni spenti
coincidono fra kit diversi; 55 solari su 94 non rispondono mai (contro 31 su 317 a batteria). Contraddicono: 3 solari
sempre verdi (203, 226, 362) e 382 col solo satellite da guardare. Non sappiamo: se i solari che non rispondono sono spenti del tutto o hanno
solo il router spento (il giro prova circa 5 volte al giorno: un kit acceso solo qualche ora può sfuggire), e il meteo
vero di quei giorni (non l'ho controllato). Certezza: media.

**Tutto il kit insieme o una telecamera sola.** 63% delle ore spente sono di tutto il kit: alimentazione o registratore,
non le telecamere. Il 37% è una telecamera sola, e lì pesa il satellite: nei kit col satellite le telecamere oltre quelle
via cavo (il satellite è di solito l'ultimo canale, ma l'anagrafica non dice quale: per questo nelle righe c'è «forse il
satellite») hanno 11 problemi su 223 più 17 telecamere mai registrate; le telecamere via cavo 10 su 896 più 3 mai
registrate. Alcuni satelliti hanno uno schema loro: 506 CH3 registra solo di notte, 535 CH3 solo di giorno (un satellite
col suo pannello e la batteria che non tiene), 230 CH4 solo di notte.

**Disco pieno che sovrascrive.** Ogni registratore tiene da 6 a oltre 200 giorni (mediana 15); quando è pieno cancella i giorni
più vecchi, ma non fa buchi in mezzo: nessun buco visto si spiega così. Serve solo per sapere fin quando un video si può
ancora scaricare (426, 501, 315, 321 meno di 7 giorni). Certezza: alta che non sia la causa dei buchi.

**Orologio sbagliato.** Nessun registratore ha registrazioni più avanti dell'ora di lettura. I kit a lampione si
spengono all'alba e si riaccendono al tramonto all'ora giusta: il loro orologio è giusto. Un orologio indietro non si vede
dalle ore: per gli altri non si può dire.

**Registrazione solo a movimento.** I registratori dicono il tipo di ogni tratto di oggi: 237 telecamere hanno tratti
«a sensore» alternati a tratti «continua», e 210 di queste registrano tutte le ore. Nessun buco di notte si spiega col
movimento. Certezza: alta.

**Peggioramento nel tempo.** Nei kit a lampione sì: 267, 276, 385 e 490 hanno cominciato a spegnersi di giorno fra
l'01/11 e l'08/11, dopo giorni pieni: batterie che cedono. Nei solari i giorni spenti aumentano verso metà novembre, ma
con 18 giorni di dati non si separa la stagione dal tempo.

**Cosa non c'è nei dati.** Il canale del satellite (l'anagrafica dice solo quanti), la data della batteria per molti kit
(colonna «POWER data batt» spesso vuota), lo stato del router e della SIM nelle ore spente (RMS è senza crediti), il
meteo. Le ore valgono dal 27/10: prima non sono state lette.

## Per kit

Una riga per kit installato. «Schema» dice cosa fanno le ore; i numeri di canale sono quelli di UVMS (CH1 = telecamera 1).

### A. si spegne di giorno, riparte al tramonto (16 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 219 | SAN POLO D ENZA | batteria | di notte sempre; di giorno 28%: si spegne verso le 10 e riparte alle 16-17, 17 giorni su 18 (dal 28/10) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (regge circa 3 ore dopo l'alba) | alta | sul posto: batteria (e caricabatterie/power); se ogni giorno, subito |
| 230 | CASTELLARANO | batteria | di notte sempre; di giorno 1%: si spegne verso le 8 e riparte alle 16-17, 17 giorni su 18 (dal 27/10); CH4 registra solo di notte (forse il satellite) | pubblica illuminazione: il lampione dà corrente solo di notte e il kit non regge il giorno; la batteria è stata cambiata il 05/11 e si spegne ancora (8 giorni): non è (solo) la batteria, ma la carica (caricabatterie/power, fusibile o il collegamento alla pubblica) | alta | sul posto: caricabatterie/power, fusibile e collegamento alla pubblica (la batteria è già nuova) |
| 236 | CASTEGGIO | batteria | di notte sempre; di giorno 80%: si spegne verso le 7 e riparte alle 16-17, 4 giorni su 19 (dal 27/10); dal 31/10 non succede più | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | niente: è tornato a posto |
| 267 | ALEA - Meldola | batteria | di notte sempre; di giorno 75%: si spegne verso le 12 e riparte alle 16-17, 9 giorni su 19 (dal 01/11) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (regge circa 5 ore dopo l'alba) | alta | sul posto alla prossima occasione: batteria che sta cedendo |
| 276 | VIGONZA | batteria | di notte sempre; di giorno 55%: si spegne verso le 7 e riparte alle 16-17, 8 giorni su 18 (dal 06/11) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | sul posto alla prossima occasione: batteria che sta cedendo |
| 345 | FOGGIA | batteria | di notte sempre; di giorno 0%: si spegne verso le 8 e riparte alle 16-17, 11 giorni su 11 (dal 03/11) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | sul posto: batteria (e caricabatterie/power); se ogni giorno, subito |
| 347 | OZZANO EMILIA | batteria | di notte sempre; di giorno 0%: si spegne verso le 7 e riparte alle 16-17, 18 giorni su 19 (dal 27/10) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | sul posto: batteria (e caricabatterie/power); se ogni giorno, subito |
| 385 | DOZZA | batteria | di notte sempre; di giorno 67%: si spegne verso le 8 e riparte alle 16-17, 6 giorni su 19 (dal 08/11); CH2 spenta 79% delle ore in cui il kit registra; 1 telecamera su 4 mai registrata dal 27/10 (CH4) (forse il satellite) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | sul posto alla prossima occasione: batteria che sta cedendo |
| 398 | LOIANO | batteria | di notte sempre; di giorno 3%: si spegne verso le 8 e riparte alle 16-17, 13 giorni su 15 (dal 31/10) | pubblica illuminazione: il lampione dà corrente solo di notte e il kit non regge il giorno; la batteria è stata cambiata il 04/11 e si spegne ancora (9 giorni): non è (solo) la batteria, ma la carica (caricabatterie/power, fusibile o il collegamento alla pubblica) | alta | sul posto: caricabatterie/power, fusibile e collegamento alla pubblica (la batteria è già nuova) |
| 440 | GRIZZANA MORANDI | batteria | di notte sempre; di giorno 14%: si spegne verso le 9 e riparte alle 16-17, 11 giorni su 13 (dal 03/11) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (regge circa 2 ore dopo l'alba) | alta | sul posto: batteria (e caricabatterie/power); se ogni giorno, subito |
| 490 | ALTA VAL TIDONE | batteria | di notte sempre; di giorno 67%: si spegne verso le 7 e riparte alle 16-17, 6 giorni su 18 (dal 07/11) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | sul posto alla prossima occasione: batteria che sta cedendo |
| 504 | MERANO | batteria | di notte sempre; di giorno 5%: si spegne verso le 8 e riparte alle 16-17, 17 giorni su 18 (dal 27/10) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica); la batteria è stata cambiata il 12/11: troppo presto per dire se è bastato | alta | da remoto: ricontrollare fra qualche giorno (batteria appena cambiata) |
| 515 | MERANO | batteria | di notte sempre; di giorno 75%: si spegne verso le 8 e riparte alle 16-17, 4 giorni su 19 (dal 29/10) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica); la batteria è stata cambiata il 12/11: troppo presto per dire se è bastato | alta | da remoto: ricontrollare fra qualche giorno (batteria appena cambiata) |
| 518 | MERANO | batteria | di notte sempre; di giorno 34%: si spegne verso le 11 e riparte alle 16-17, 16 giorni su 16 (dal 29/10) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (regge circa 4 ore dopo l'alba) | alta | sul posto: batteria (e caricabatterie/power); se ogni giorno, subito |
| 578 | GEOVEST - Calderara di Reno | batteria | di notte sempre; di giorno 80%: si spegne verso le 7 e riparte alle 16-17, 3 giorni su 18 (dal 27/10); dal 30/10 non succede più | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | niente: è tornato a posto (cambio del 30/10) |
| 606 | ALTA VAL TIDONE | batteria | di notte sempre; di giorno 0%: si spegne verso le 7 e riparte alle 16-17, 18 giorni su 19 (dal 27/10) | pubblica illuminazione: il lampione dà corrente solo di notte e la batteria non regge il giorno (si spegne appena si spengono i lampioni: batteria morta, staccata o che non si carica) | alta | sul posto: batteria (e caricabatterie/power); se ogni giorno, subito |

### B. solare: si spegne di notte o per giorni (23 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 241 | MONTESE | solare | 14 giorni spenti su 15; una volta si spegne di sera o di notte e riparte la mattina | quasi sempre spento: pannello in ombra o guasto, batteria o regolatore guasti | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |
| 305 | GRANDATE | solare | 3 giorni spenti su 11; 2 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 320 | CANOSA DI PUGLIA | solare | 12 giorni spenti su 18; 2 volte si spegne di sera o di notte e riparte la mattina; 1 telecamera su 2 mai registrata dal 27/10 (CH2) | quasi sempre spento: pannello in ombra o guasto, batteria o regolatore guasti | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |
| 325 | CODIGORO | solare | 5 giorni spenti su 18; 2 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 327 | BARI | solare | 7 giorni spenti su 18; 7 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 358 | CANOSA DI PUGLIA | solare | 1 giorno spento su 18; 3 volte si spegne di sera o di notte e riparte la mattina; 1 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 394 | BUSTO ARSIZIO | solare | 5 giorni spenti su 18; una volta si spegne di sera o di notte e riparte la mattina; CH3 spenta 78% delle ore in cui il kit registra (forse il satellite) | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 406 | CANOSA DI PUGLIA | solare | 6 giorni spenti su 18; 5 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 439 | MOLFETTA | solare | 2 giorni spenti su 14; una volta si spegne di sera o di notte e riparte la mattina; 2 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 455 | PORDENONE | solare | 16 giorni spenti su 18; quando si accende è solo qualche ora di giorno | va solo quando il sole batte sul pannello: la batteria non tiene più (o non è collegata) | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |
| 470 | MONTESE | solare | 8 giorni spenti su 17; 2 volte si spegne di sera o di notte e riparte la mattina; 7 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 473 | BARI | solare | 4 giorni spenti su 19; 4 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 498 | MANFREDONIA | solare | 16 giorni spenti su 18 | quasi sempre spento: pannello in ombra o guasto, batteria o regolatore guasti | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |
| 512 | MANFREDONIA | solare | 3 giorni spenti su 18; 4 volte si spegne di sera o di notte e riparte la mattina; 2 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 513 | MANFREDONIA | solare | 11 giorni spenti su 15 | quasi sempre spento: pannello in ombra o guasto, batteria o regolatore guasti | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |
| 524 | TOANO | solare | 14 giorni spenti su 16 | quasi sempre spento: pannello in ombra o guasto, batteria o regolatore guasti | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |
| 542 | SAN NICANDRO GARGANICO | solare | 6 giorni spenti su 18; 4 volte si spegne di sera o di notte e riparte la mattina; 5 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 551 | CANOSA DI PUGLIA | solare | 3 giorni spenti su 18; una volta si spegne di sera o di notte e riparte la mattina; 3 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 552 | MOLFETTA | solare | 4 giorni spenti su 18; una volta si spegne di sera o di notte e riparte la mattina; 3 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 653 | CASTENASO | solare | 9 giorni spenti su 16; una volta si spegne di sera o di notte e riparte la mattina; 8 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 667 | BUSTO ARSIZIO | solare | 17 giorni spenti su 18; quando si accende è solo qualche ora di giorno | va solo quando il sole batte sul pannello: la batteria non tiene più (o non è collegata) | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |
| 677 | CANOSA DI PUGLIA | solare | 6 giorni spenti su 18; 6 di questi giorni spenti anche altri solari della stessa regione | il pannello non ricarica abbastanza la batteria nelle giornate corte e nuvolose: si spegne di notte e dopo i giorni nuvolosi (gli stessi giorni di altri kit solari vicini: il tempo, non solo il kit) | media | sul posto: batteria e pulizia/orientamento del pannello; d'inverno valutare la batteria più grande o il secondo pannello |
| 679 | UBR - Lugo | solare | 5 giorni spenti su 7; 2 volte si spegne di sera o di notte e riparte la mattina | quasi sempre spento: pannello in ombra o guasto, batteria o regolatore guasti | media | sul posto: pannello (ombra, sporco, orientamento), batteria e regolatore |

### C. spento per giorni, poi ripartito (7 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 205 | SAN POLO D ENZA | 220V | spento dal 27/10 alle 00 al 30/10 alle 14 (3 giorni); ora registra | ripartito in orario di lavoro: probabilmente un intervento (riavvio o riparazione) | media | niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico |
| 344 | SAN MARTINO IN RIO | batteria | spento dal 27/10 alle 00 al 04/11 alle 15 (8 giorni); ora registra | ripartito in orario di lavoro: probabilmente un intervento (riavvio o riparazione) | media | niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico |
| 373 | PORDENONE | batteria | spento dal 06/11 alle 05 al 09/11 alle 14 (3 giorni); ora registra | ripartito in orario di lavoro: probabilmente un intervento (riavvio o riparazione) | media | niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico |
| 619 | VERGATO | batteria | spento dal 28/10 alle 12 al 05/11 alle 11 (7 giorni); ora registra | ripartito in orario di lavoro: probabilmente un intervento (riavvio o riparazione) | media | niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico |
| 629 | GEOVEST - Finale Emilia | batteria | spento dal 31/10 alle 04 al 01/11 alle 20 (1 giorno); ora registra | ripartito da solo fuori orario: probabile ritorno della corrente | media | niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico |
| 640 | DOZZA | batteria | spento dal 08/11 alle 08 al 10/11 alle 15 (2 giorni); ora registra | ripartito in orario di lavoro: probabilmente un intervento (riavvio o riparazione) | media | niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico |
| 662 | CARPINETI | batteria | spento dal 27/10 alle 00 al 09/11 alle 07 (13 giorni); ora registra | ripartito da solo fuori orario: probabile ritorno della corrente | media | niente, se l'ODM dice cosa è stato fatto; se no chiedere al tecnico |

### D. fermo adesso (1 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 352 | UNIONE VALLI E DELIZIE | batteria | non registra dal 31/10 | tutto il kit insieme: alimentazione o registratore | media | da remoto se risponde (riavvio); se no sul posto: alimentazione |

### E. si spegne per giorni interi (1 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 593 | FOGGIA | batteria | 6 giorni spenti su 18, a più riprese | tutto il kit insieme: alimentazione o registratore che si blocca; dalle ore non si distingue | bassa | sul posto: alimentazione e registratore |

### F. buchi sparsi (2 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 396 | FOGGIA | batteria | 97% delle ore; buchi soprattutto sparsi | non c'è uno schema chiaro | bassa | da guardare |
| 521 | CASTELLARANO | batteria | 97% delle ore; buchi soprattutto sparsi | non c'è uno schema chiaro | bassa | da guardare |

### G. kit acceso, una telecamera no (34 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 155 | SAN LAZZARO DI SAVENA | ? | CH1 spenta 35% delle ore in cui il kit registra | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 211 | GATTATICO | 220V | 1 telecamera su 4 mai registrata dal 27/10 (CH4) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 223 | UBR - Alfonsine | batteria | 1 telecamera su 4 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 248 | MARANELLO | batteria | CH2 ferma dal 08/11 | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 250 | MONTERENZIO | batteria | CH3 ferma dal 06/11 (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 255 | PORDENONE | batteria | CH3 spenta 35% delle ore in cui il kit registra (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 270 | CORREGGIO | batteria | 1 telecamera su 3 mai registrata dal 27/10 (CH2) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 304 | AMAGA - Abbiategrasso | batteria | CH3 ferma dal 29/10 | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 311 | SASSUOLO | batteria | CH3 ferma dal 29/10 | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 316 | PORDENONE | batteria | CH2 spenta 20% delle ore in cui il kit registra; CH4 spenta 93% delle ore in cui il kit registra (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 338 | DOZZA | batteria | CH3 spenta 47% delle ore in cui il kit registra | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 357 | FOGGIA | batteria | 1 telecamera su 4 mai registrata dal 27/10 (CH4) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 359 | SAN VITO AL TAGLIAMENTO | batteria | CH3 spenta 48% delle ore in cui il kit registra (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 361 | BOLZANO | 220V | CH1 spenta 80% delle ore in cui il kit registra | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 376 | AMAGA - Abbiategrasso | batteria | 1 telecamera su 4 mai registrata dal 27/10 (CH4) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 378 | REA - Rosignano Marittimo | batteria | 1 telecamera su 3 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 382 | POLAVENO | solare | CH4 spenta 21% delle ore in cui il kit registra (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 386 | SANT ILARIO D ENZA | batteria | 1 telecamera su 3 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 407 | TRANI | batteria | 1 telecamera su 4 mai registrata dal 27/10 (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 436 | SAN LAZZARO DI SAVENA | Townet | 1 telecamera su 3 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 459 | FOGGIA | batteria | 1 telecamera su 4 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 463 | UBR - Bagnacavallo | batteria | 1 telecamera su 4 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 467 | SANT ILARIO D ENZA | batteria | 1 telecamera su 4 mai registrata dal 27/10 | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 483 | UNIONE VAL D ENZA - Montecchio  | batteria | 1 telecamera su 3 mai registrata dal 27/10 (CH3) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 506 | APRICA - Sarezzo | batteria | CH3 registra solo di notte (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 511 | MINERBIO | batteria | CH3 ferma dal 06/11 (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 535 | LUZZI | batteria | CH3 registra solo di giorno | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 580 | AMBIENTE SPA - Pescara | batteria | CH3 ferma dal 02/11 (forse il satellite); CH4 ferma dal 29/10 (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 600 | SAN LAZZARO DI SAVENA | batteria | 1 telecamera su 3 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 604 | CASALFIUMANESE | batteria | 1 telecamera su 3 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 612 | UBR - Fusignano | batteria | 1 telecamera su 3 mai registrata dal 27/10 (CH3) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 651 | SALSOMAGGIORE | batteria | 1 telecamera su 4 mai registrata dal 27/10 (CH4) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 657 | SAN BONIFACIO | batteria | CH3 spenta 47% delle ore in cui il kit registra | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |
| 661 | AMBIENTE SPA - Pescara | batteria | 1 telecamera su 4 mai registrata dal 27/10 (CH4) (forse il satellite) | una telecamera sola: telecamera, cavo/connettore o, per il satellite, la sua batteria o il collegamento radio | media | da remoto: guardare la foto/il live; poi sul posto: telecamera, cavo o satellite |

### H. risponde ma senza ore lette (o installato da poco) (4 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 363 | CONCORDIA SULLA SECCHIA | batteria | - | - | - | niente per ora |
| 393 | MARANELLO | batteria | - | - | - | niente per ora |
| 432 | UNIONE VAL D ENZA - Montecchio  | batteria | - | - | - | niente per ora |
| 482 | BARI | solare | - | - | - | niente per ora |

### M. nessun registratore in UVMS (15 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 39 | GEOVEST - Calderara di Reno | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 52 | MOLFETTA | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 57 | MOLFETTA | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 60 | GRANAROLO | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 61 | SAN LAZZARO DI SAVENA | batteria | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 62 | MARZABOTTO | batteria | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 63 | SAN LAZZARO DI SAVENA | batteria | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 65 | FORTE DEI MARMI | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 66 | FORTE DEI MARMI | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 67 | FORTE DEI MARMI | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 68 | FORTE DEI MARMI | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 71 | LERICI | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 77 | TRANI | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 80 | MOLFETTA | solare | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |
| 998 | Roma | ? | - | non è nell'elenco dei registratori letto da UVMS | - | controllare UVMS |

### N. non risponde, ore mai lette (91 kit)

| Kit | Comune | Alim. | Schema | Probabile causa | Certezza | Cosa fare |
|---|---|---|---|---|---|---|
| 128 | SAN LAZZARO DI SAVENA | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 136 | ALEA - Civitella | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 204 | SAN POLO D ENZA | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 207 | MARZABOTTO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 208 | PALMANOVA | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 213 | MONTESE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 216 | SAN LAZZARO DI SAVENA | 220V | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 217 | MALALBERGO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 229 | UNIONE VAL D ENZA - Montecchio  | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 232 | UBR - Sant Agata sul Santerno  | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 238 | CANOSA DI PUGLIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 245 | MONGHIDORO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 260 | CANOSA DI PUGLIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 264 | MARZABOTTO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 307 | AMBIENTE SPA - Pescara | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 310 | UBR - Fusignano | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 322 | CAMPEGINE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 326 | CASTENASO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 330 | GORIZIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 332 | CAVRIAGO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 334 | REGGIO EMILIA | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 348 | OZZANO EMILIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 356 | UNIONE COLLINE MATILDICHE | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 365 | COMO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 366 | CANOSA DI PUGLIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 367 | VERGATO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 380 | MOLFETTA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 381 | GEOVEST - Crevalcore | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 387 | FOSSOMBRONE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 389 | FOSSOMBRONE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 424 | GEOVEST - San Giovanni in Pers | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 425 | BIBBIANO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 427 | UBR - Lugo | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 428 | CODIGORO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 430 | FONTANELICE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 431 | UBR - Massa Lombarda | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 438 | GEOVEST - Crevalcore | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 441 | GRIZZANA MORANDI | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 446 | Aprica-COMO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 454 | BUSTO ARSIZIO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 464 | BARI | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 465 | UBR - Bagnara di Romagna | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 469 | ALEA - Civitella | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 471 | MONTESE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 472 | COMO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 477 | BIBBIANO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 479 | BARI | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 480 | BARI | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 481 | CERVIGNANO DEL FRIULI | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 491 | GRANAROLO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 492 | UBR - Lugo | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 493 | MONZUNO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 494 | MANFREDONIA | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 495 | MONZUNO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 496 | MANFREDONIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 497 | CORREGGIO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 499 | MONZUNO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 502 | CASALFIUMANESE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 507 | BARI | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 508 | MANFREDONIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 509 | MANFREDONIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 537 | MANFREDONIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 538 | BORE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 539 | SALSOMAGGIORE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 540 | LOIANO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 541 | CODIGORO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 545 | UNIONE COLLINE MATILDICHE | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 550 | CANOSA DI PUGLIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 553 | GEOVEST - Castel Maggiore - URG | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 554 | UBR - Lugo | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 555 | CREMONA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 563 | CASTEL D AIANO | ? | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 564 | GATTATICO | 220V | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 570 | GEOVEST - Calderara di Reno | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 587 | MONTERENZIO | 220V | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 595 | GORIZIA | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 598 | CASTEL D AIANO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 616 | MARANELLO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 617 | UBR - Lugo | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 620 | SAN GIORGIO BIGARELLO | 220V | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 623 | CASTEL GUELFO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 624 | CASTEL D AIANO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 635 | UNIONE VALLI E DELIZIE | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 648 | GRANAROLO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 655 | MODENA | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 659 | LECCO | batteria | - | spento o senza rete: dalle ore non si può dire | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 669 | TOANO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 672 | MONZUNO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 674 | UBR - Lugo | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 680 | ALEA - Dovadola | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |
| 681 | MONZUNO | solare | - | kit solare: la batteria scarica è il primo sospetto, ma non sappiamo se è spento tutto o solo il router | - | da remoto: SMS di riavvio e controllo della SIM; se non torna, sul posto |

### OK: sempre verdi (268 kit)

200, 201, 203, 206, 209, 210, 212, 214, 215, 220, 222, 224, 225, 226, 228, 233, 234, 235, 237, 240, 242, 244, 247, 249, 251, 252, 253, 256, 257, 258, 261, 262, 263, 265, 266, 268, 269, 271, 272, 274, 275, 277, 278, 279, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 312, 313, 314, 315, 317, 318, 319, 321, 323, 324, 328, 329, 331, 333, 335, 336, 339, 340, 341, 343, 346, 349, 350, 351, 353, 354, 355, 360, 362, 364, 368, 369, 370, 371, 372, 374, 375, 377, 379, 383, 384, 388, 391, 392, 395, 397, 399, 400, 401, 402, 403, 404, 405, 408, 409, 410, 411, 412, 413, 414, 415, 417, 418, 419, 421, 422, 423, 426, 433, 434, 435, 437, 442, 443, 444, 445, 447, 448, 449, 451, 452, 453, 456, 457, 458, 460, 461, 462, 466, 468, 474, 475, 476, 478, 484, 485, 486, 487, 488, 489, 501, 503, 505, 510, 514, 516, 517, 519, 520, 522, 523, 525, 526, 527, 528, 529, 531, 533, 536, 543, 544, 546, 547, 548, 549, 556, 557, 558, 560, 561, 562, 565, 566, 567, 568, 569, 571, 572, 573, 574, 575, 576, 577, 579, 581, 582, 583, 585, 588, 589, 590, 591, 592, 594, 596, 597, 599, 601, 602, 603, 605, 607, 608, 609, 610, 611, 613, 614, 615, 618, 621, 625, 627, 631, 632, 634, 636, 637, 638, 639, 641, 643, 644, 645, 647, 649, 650, 652, 654, 656, 660, 663, 664, 665, 666, 668, 670, 671, 673, 676, 678.
