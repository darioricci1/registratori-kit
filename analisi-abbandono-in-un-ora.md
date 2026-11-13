# Trovare l'abbandono in un'ora di registrazione (12/11/2026)

Obiettivo: dentro un'ora di una telecamera, mettere l'abbandono **al primo posto** dei candidati, così una persona
guarda uno o due momenti invece dell'ora intera. Dati: le 30 ore della prova pilota (`p2p_ponte6/pilota.py` 0.1.0,
10 positive con l'abbandono noto e il riquadro di Dario, 20 negative), con le miniature di ogni minuto (704x576)
salvate dal compito. Tutto rifatto a tavolino, senza PC e senza registratore.

Codice (ramo `abbandono-in-un-ora`, nessun push):

- `compiti/p2p_ponte6/b_tavolino.py` 0.1.0: il metodo (b) come funzione pura (`scansione`), con le varianti come
  opzioni. Con le opzioni di partenza rifà pilota.py 0.1.0: stessi posti sulle 10 positive, 2,77 falsi per ora fra i
  primi 8 contro i 2,8 del PC (le miniature salvate sono JPEG ricompressi, la differenza viene da lì).
- `compiti/p2p_ponte6/misura_b_tavolino.py` 0.1.0: misura una o più varianti sulle 30 ore
  (`python3 misura_b_tavolino.py <cartella pilota> insieme`). Circa 2 minuti per variante, 5 con la passata fuori zona.
- `compiti/p2p_ponte6/prova_b_tavolino.py` 0.1.0: prove su una scena finta (sacco, sacco fuori zona, sole su un pezzo
  di strada, auto in sosta, furgone che riparte). 24 prove, tutte passano.

Come si conta. **Trovato**: un candidato che tocca il riquadro di Dario (IoU ≥ 0,1, come `confronto` di pilota.py) e
compare nel minuto giusto (l'atteso cade fra il minuto prima e quello della comparsa, ±90 s). **Falso**: nelle
positive ogni candidato che non tocca il riquadro di Dario, nelle negative ogni candidato. I giudizi di Claude
(giudizi_1/2) sulle negative sono tutti «niente»; i candidati nuovi delle negative li ho guardati io (sotto): nessuno è
un rifiuto, quindi contarli tutti falsi è giusto. I falsi si contano fra i primi 1, 3 e 8 per ora (8 sono gli allarmi
che il compito di oggi mostra).

## 1. Perché B mancava 4 positive (più pos03 e pos05)

| Ora | Cosa c'è | Si vede a 704x576? | Perché B lo perdeva |
|---|---|---|---|
| pos01_kit576 | un oggettino scuro alla base del cancello, accanto all'auto che si ferma alle 09:18 | appena: ~10x9 pixel, deltaE massimo 22 | **fuori dalla zona** (la zona è sui cassonetti blu a destra, l'abbandono è a metà inquadratura) e, anche guardando tutta l'inquadratura, a deltaE 14 restano 15 pixel, sotto l'area minima di 45 |
| pos06_kit511 | un bicchiere giallo sul cordolo, dopo l'auto nera che si ferma 2 minuti | sì, piccolo: 7x9 pixel (54), deltaE 27 | era fra i pezzi trovati al minuto giusto, ma **perso nell'ordine**: tramonto, ombre lunghe e auto davanti (pezzi da 1.000-40.000 pixel) passano prima, e al minuto se ne tengono 3 |
| pos07_kit561 | sacco giallo fra due cassonetti, di notte, dopo l'auto bianca | sì (423 pixel) | trovato, ma **3° posto** dietro due falsi (un riflesso grande e un pezzo di cassonetto); il giudice l'aveva segnato «dubbio» |
| pos08_kit461 | sacco bianco accanto al cestino in primo piano | benissimo (1.003 pixel, deltaE 72) | **fuori dalla zona**: la zona è sui cassonetti in fondo alla strada, l'abbandono è al cestino sotto la telecamera |
| pos03_kit589 | sacco giallo sul cassonetto | sì | trovato al 1° posto: va bene |
| pos05_kit548 | telaio di legno appoggiato al cassonetto | sì | trovato, **3° posto** dietro due ombre grandi (4.700 pixel) che spariscono dopo 8 e 15 minuti |

In breve: due su quattro sono la **zona** (l'abbandono non è ai cassonetti disegnati), uno è l'**ordine** (un oggetto
piccolo che perde contro le ombre grandi), uno è al limite della **risoluzione**. Nessuno era tolto da «via» o da
«all'inizio non c'era».

## 2. Le varianti, una alla volta e poi insieme

Ogni riga è una misura vera sulle 30 ore (10 positive). «1°», «pr3», «pr8»: abbandoni trovati al primo posto, nei
primi 3, nei primi 8. «Falsi/h»: falsi per ora-telecamera fra i primi 3 e fra i primi 8.

| Variante | Cosa cambia | 1° | pr3 | pr8 | falsi/h (3) | falsi/h (8) |
|---|---|---|---|---|---|---|
| **oggi** (pilota.py 0.1.0) | — | 5 | 7 | 7 | 1,40 | 2,77 |
| radice | deltaE × √area invece di × area | 5 | 7 | 7 | 1,40 | 2,77 |
| base | ×3 a un pezzo piccolo alla base dei cassonetti | 5 | 7 | 7 | 1,40 | 2,77 |
| massimi8 | 8 pezzi per minuto invece di 3 | 5 | 7 | 7 | 1,40 | 2,80 |
| ombra | scarta se la tessitura (gradienti) è la stessa di prima | 4 | 6 | 6 | 1,27 | 2,53 |
| resta8 | il cambio deve restare 8 minuti invece di 5 | 5 | 7 | 7 | 1,40 | 2,63 |
| durata10 | scarta se sparisce prima di 10 minuti | 5 | 7 | 7 | 1,37 | 2,70 |
| fermo | scarta se nei minuti del dopo cambia ancora (relativo al deltaE) | 5 | 7 | 7 | 1,40 | 2,60 |
| mosso4 | come fermo, soglia fissa: 4 deltaE | 5 | 7 | 7 | 1,13 | 2,13 |
| area3000 | pezzi fino a 3.000 pixel (0,75% dell'immagine) | 6 | 7 | 7 | 1,33 | 2,63 |
| fino | solo chi resta fino alla fine dell'ora (+5 min) | 6 | 7 | 7 | 1,27 | 2,47 |
| memoria30 | scarta se com'è adesso c'era già nella mezz'ora prima | 6 | 7 | 7 | 1,23 | 2,30 |
| pesata | tutta l'inquadratura, fuori zona vale metà | 3 | 3 | 5 | 2,20 | 4,27 |
| **insieme** | memoria30 + fino + mosso4 + area3000 | **8** | **8** | **8** | **0,80** | **1,13** |
| insieme, mosso 3,5 | | 7 | 7 | 7 | 0,83 | 1,10 |
| insieme, mosso 4,5 | | 7 | 8 | 8 | 0,93 | 1,33 |
| insieme, mosso 5 | | 6 | 7 | 8 | 1,00 | 1,53 |
| insieme senza memoria | | 7 | 7 | 7 | 1,00 | 1,67 |
| insieme senza area | | 7 | 8 | 8 | 0,83 | 1,17 |
| insieme senza fino | | 7 | 8 | 8 | 0,97 | 1,53 |
| insieme + fuori zona | seconda passata su tutta l'inquadratura, in coda | 8 | 8 | 9 | 1,47 | 2,30 |

Con **insieme**, fra i soli primi posti: 0,33 falsi per ora (10 ore su 30 hanno un falso in cima; oggi 0,57).

Cosa dicono:

- **Da sola nessuna regola sposta molto**: ognuna toglie qualche falso, nessuna toglie un abbandono (tranne «ombra»,
  che perde pos03: un sacco giallo sul coperchio giallo ha la stessa tessitura di prima. Scartata). «radice», «base» e
  «massimi8» non cambiano niente: l'ordine dentro un minuto lo decide ancora pezzi_zona, e il pezzo piccolo resta
  fuori prima di arrivare al punteggio.
- **Insieme sì**, perché le quattro regole tolgono falsi diversi: *memoria* il fondo che torna (auto che ripartono,
  ombre che passano due volte), *fino* le soste e le ombre del pomeriggio, *mosso* le foglie e i rami che si muovono,
  *area* le auto e le ombre larghe. Tolti quelli, al minuto di pos06 il bicchiere giallo entra fra i 3 pezzi e finisce
  primo; pos05 e pos07 salgono dal 3° al 1° posto.
- **Fuori zona**: pesare tutta l'inquadratura insieme alla zona peggiora tutto (la luce si pareggia su tutta
  l'immagine e di notte si perde pos07). Una seconda passata messa *in coda* ritrova pos08 (4° posto), ma raddoppia i
  falsi fra i primi 8. È un'opzione, non la scelta.

### Quanto è fragile

10 positive sono poche e le soglie le ho viste sulle stesse 10: il guadagno va letto come ipotesi da confermare.

- **pos06 è appeso a un filo**: il suo «mosso» è 3,99 contro la soglia 4,0. Con 3,5 sparisce, con 4,5 è 2°, con 5 è
  6°. Senza pos06 la variante resta a **7 su 10 al primo posto** (oggi 5): questo è il guadagno su cui contare.
- **pos05** (mosso 3,44) cade con la soglia a 3,5 di poco. Il «mosso» degli 8 trovati va da 1,5 a 4,0: la soglia è
  sul bordo della nuvola, non in mezzo.
- **fino alla fine** è la regola più naturale (chi abbandona non torna a riprendere), ma butta un abbandono raccolto
  prima della fine dell'ora (da un operatore, da chi rovista). Nelle 10 ore non succede; in una prova grande va
  contato.
- **area ≤ 3.000 pixel** (0,75% dell'immagine): l'abbandono più grande qui è di 1.374 pixel (cartoni). Un materasso
  vicino alla telecamera la sfora. «Insieme senza area» costa solo 0,03 falsi per ora: si può anche togliere.
- **memoria30** è la più robusta: da sola dà +1 al primo posto e −0,47 falsi su 8, e toglie una sola cosa che non
  può essere un abbandono (com'è adesso c'era già prima).

I falsi che restano (primo candidato delle negative, guardati uno a uno): foglie gialle che cadono e restano (neg06,
neg10), un cassonetto spostato (neg07, neg13), auto parcheggiate fino alla fine (neg14, neg16), erba e un animale
(neg15), una chiazza bagnata sull'asfalto (neg19), una striscia di cassonetto con le ombre (neg05). Nessuno è un
rifiuto.

## 3. La scelta

**«insieme»** = memoria 30 minuti + solo chi resta fino alla fine + mosso ≤ 4 + pezzo ≤ 3.000 pixel, sulla zona come
oggi (`bt.opzioni(memoria=30, solo_fino=True, mosso_max=4.0, area_max=0.0075)`).

Sulle 30 ore: **8 abbandoni su 10 al primo posto** (7 senza il caso al limite di pos06), **0,33 falsi per ora fra i
primi posti, 0,80 fra i primi 3, 1,13 fra i primi 8** (oggi 5 su 10, 0,57 / 1,40 / 2,77). In pratica: per ogni ora si
guarda il primo candidato (al massimo il secondo), e sbaglia una volta ogni tre ore.

Resta fuori: **pos08** e **pos01**, che sono abbandoni fuori dalla zona disegnata. La correzione giusta non è
guardare tutta l'inquadratura (raddoppia i falsi), è **ridisegnare la zona** di quei kit dove la gente abbandona
davvero (il cestino di KIT461, il cancello di KIT576), cosa che le scene delle 10 positive già dicono. pos01 resta
comunque al limite della miniatura (15 pixel sopra soglia).

Non l'ho messa in pilota.py: il compito che gira sul PC resta 0.1.0 finché la regola non è confermata sulle ore nuove.

## 4. Cosa serve per fidarsi

Con 8 su 10 l'intervallo vero (Wilson, 95%) va da 49% a 94%: non distingue «quasi sempre» da «una volta su due».

- **Ore positive**: per stimare la quota al primo posto con ±10 punti servono ~60 positive, con ±7 ~120. Per dire che
  «insieme» batte «oggi» di 2 abbandoni su 10 (75% contro 55%) con 80% di potenza ne servono ~60-80. **Obiettivo: 80
  positive**, da almeno 40 kit diversi (non due ore dallo stesso kit: kit589 e kit423 compaiono due volte già qui), metà
  di giorno e metà di notte o col sole basso, presi dagli eventi giudicati dove c'è il riquadro di Dario.
- **Ore negative**: i falsi per ora con ±0,1 a un tasso di 0,3-0,8 vogliono 100-200 ore. **Obiettivo: 150 negative**
  sorteggiate alla cieca come oggi.
- **Le soglie si congelano adesso** (quelle di sopra) e la prova nuova si misura senza ritoccarle; solo dopo si
  ritarano, e su un'altra metà.
- Costo: il metodo (b) chiede al registratore ~3 MB e ~20 secondi di miniature per ora (conti di pilota.json), quindi
  230 ore sono ~700 MB e un paio d'ore di registratore. Le miniature fitte e il metodo (a) non servono a questa misura.
- In più, da segnare in ogni ora positiva: se l'abbandono è dentro la zona disegnata (oggi 8 su 10), e se è stato
  raccolto prima della fine dell'ora (per sapere quanto costa la regola «fino alla fine»).

## 5. La prossima mossa

1. Un compito «pilota 2» con 80 positive e 150 negative, solo miniature dei minuti (niente fitte, niente metodo a),
   e la misura con `misura_b_tavolino.py oggi insieme insieme_fuori` a soglie ferme.
2. In parallelo, le zone di KIT461 e KIT576 ridisegnate sul punto dell'abbandono, e un controllo su quante positive
   cadono fuori zona nella prova grande: se sono più di una su dieci, la zona va rifatta su tutti i kit con le scene
   degli abbandoni, non solo sui cassonetti.
3. I falsi che restano sono auto in sosta e foglie: il primo candidato si può passare al rivelatore di veicoli che
   kit_rifiuti ha già (YOLO in ONNX) sulla miniatura, che costa zero chiamate al registratore.

## 6. La prova grande, preparata (12/11/2026 sera, compito 32: pronto, non mandato)

- `compiti/p2p_ponte6/prepara_grande.py` 0.1.0 (prove in `prova_grande.py`, 25 prove) fa `grande.json`, che nel compito
  diventa `pilota.json` con `"solo_minuti": true`: `pilota.py` 0.2.0 scarica per ogni ora solo le 72 miniature dei
  minuti, come la pilota (`pilota/<ora>/minuti/`, `ora.json`). Ponte `compito.py` 0.15.0.
- **Positive: 71 da 40 kit**, non 80 da 40+. Dai 468 eventi con un giudizio sicuro di Claude con riquadro
  (etichette_claude, etichette_prova, giri di Guarda) ne restano 82 possibili, tutti in 40 kit: 197 sono gia' spariti
  dal disco dei registratori, 82 sono di kit del cieco, 67 di telecamere senza zona, 40 di kit «EX», 14 di registratori
  che non rispondono, 4 casi limite. Al massimo 4 ore per kit (23 kit con una, 8 con due, 4 con tre, 5 con quattro):
  `ora_del_kit = 1` sono le 40 indipendenti. Di notte solo 7 (i giudizi di Claude sono quasi tutti di giorno), fuori
  zona 2. Nessuna dai giri di Guarda (eventi vecchi o del cieco): 52 da etichette_claude, 19 da etichette_prova.
- **Negative: 150 + 30 riserve**, una per kit (180 kit), meta' di notte, lontane almeno 2 ore da ogni abbandono o
  evento noto dello stesso kit (5 scartate).
- Il disco gira: 24 positive spariscono entro due giorni (`resta_giorni`). Prima si manda, piu' positive restano.
- Stima: 221 ore, ~700 MB dal registratore, ~1 minuto per ora, 3,5-4,5 ore di COMPUTERONE.
- `misura_b_tavolino.py` 0.2.0: un candidato che tocca un altro abbandono noto dell'ora non conta come falso.

## 7. La prova grande (compito 32, 12/11 sera): il metodo «insieme» regge a metà

Il COMPUTERONE ha scaricato le miniature di 221 ore in 4 ore e 40 minuti. Lo zip arrivato su Drive era rovinato a metà
(6.451 file su 16.363 illeggibili): le 71 ore positive sono arrivate quasi tutte, le negative solo 62 su 150. Misurate
132 ore (70 con un abbandono chiaro noto da 40 kit, 62 senza), soglie congelate prima di vedere i dati.

| variante | abbandono al 1° posto | nei primi 3 | nei primi 8 | falsi all'ora (primi 3) | falsi all'ora (primi 8) |
|---|---|---|---|---|---|
| oggi (metodo B) | 14 / 70 (20%) | 31 (44%) | 43 (61%) | 1,55 | 3,38 |
| **insieme** | **27 / 70 (39%)** | **36 (51%)** | 39 (56%) | **1,02** | **1,39** |

- «insieme» raddoppia il primo posto e dimezza i falsi allarmi, ma è lontano dall'8 su 10 della pilota: su 10 casi i
  numeri erano gonfiati dalla scelta delle soglie sugli stessi casi. Il valore vero è intorno al 40% al primo posto.
- Circa 27 abbandoni su 70 non sono trovati da nessuna variante nemmeno fra i primi 8: oggetto troppo piccolo nella
  miniatura, fuori dalla zona disegnata, notte. È il tetto delle miniature da sole.
- Per l'imbuto a due stadi: con i primi 3 candidati dell'ora si prende l'abbandono in metà dei casi, al costo di circa
  3 micro-clip a piena risoluzione all'ora per telecamera (e 1 falso all'ora da scartare dopo). Lo stadio 2 (micro-clip
  HD + programma delle clip + modello visivo locale) deve togliere i falsi; il tetto del 56-61% lo alzano solo un
  rilevatore migliore e la zona degli abbandoni per telecamera.

## 8. Il secondo passaggio (compito 33, 13/11)

Per ogni ora della prova grande, i primi 3 candidati di «insieme» sono diventati pezzi di 2-3 minuti a piena risoluzione
(una telecamera), scaricati dal registratore (circa 30 s l'uno) e analizzati da Kit_Rifiuti 0.93 come una clip.
138 pezzi: 130 analizzati, 8 già sovrascritti (le ore più vecchie, 20-23/10).

- Ore positive con almeno un pezzo analizzato: 58. In 38 uno dei pezzi contiene l'abbandono vero (è il «fra i primi 3» di
  «insieme»). Su quei 38 pezzi l'analisi trova l'abbandono nel momento giusto (±20 s) in **37**, e in tutti c'è la
  persona che arriva (visita).
- Sui 92 pezzi senza l'abbandono vero (candidati sbagliati e ore negative) l'analisi dice «abbandono» in **92 su 92**,
  quasi sempre col punteggio massimo. Le ore negative con un pezzo: 13, tutte con un abbandono detto.
- Unica differenza utile: in 13 pezzi falsi non passa nessuno (nessuna visita), in quelli veri passa sempre qualcuno.
  Tenere solo i pezzi con una visita toglie 13 falsi su 92 senza perdere niente.

Conclusione: il secondo passaggio con l'analisi delle clip così com'è **ritrova il momento e la persona, ma non scarta i
falsi allarmi**: l'analisi è fatta per clip che le operatrici hanno già scelto perché contengono un abbandono, e nei pezzi
scelti da «insieme» (dove qualcosa è davvero cambiato) trova sempre un candidato. Per scartare serve un giudice sul pezzo:
il filtro dei falsi allarmi allenato anche su pezzi senza abbandono (le ore negative della prova grande sono già i
negativi), oppure il modello visivo locale (Qwen) sui pochi pezzi rimasti. Prossimo passo: riallenare il filtro coi
130 pezzi (38 veri, 92 falsi) e misurare quanti falsi toglie a parità di veri.

### 8b. Qwen sui candidati (compito 34, 13/11 sera)

Filtro coi soli numeri del report sui 130 pezzi: debole (AUC 0,69; per tenere 33 veri su 38 passano 59 falsi su 92).
Poi Qwen3-VL 4B (4 bit, sulla RTX 3070 del COMPUTERONE) con la domanda v3: per ogni candidato «insieme» fra i primi 3,
un fotogramma prima e uno dopo a piena risoluzione dal pezzo scaricato, ritagliati intorno al riquadro, più la scena
intera; risposta fra waste, vehicle, person, shadow, bin, already, nothing, unclear. 158 carte (15 pezzi senza video), 8 s
l'una, 21 minuti in tutto.

| | carte | Qwen dice «waste» |
|---|---|---|
| candidato vero (l'abbandono) | 33 | **32** |
| candidato falso | 125 | **56** (69 tolti: 48 nothing, 8 already, 6 bin, 5 vehicle, 2 person) |

- Tiene 32 abbandoni su 33 e toglie il 55% dei falsi allarmi.
- Sulle ore positive col vero fra i primi 3 (33), dopo Qwen il vero e' il primo dei candidati rimasti in 28.
- Falsi all'ora fra i primi 3 sulle 132 ore della prova: da 1,02 a circa 0,46.

Prossimi passi: mettere Qwen dentro la catena dell'ora (miniature -> insieme -> pezzi a piena risoluzione -> Qwen), la
domanda v3 col fotogramma «dopo» preso quando la scena e' ferma, e riprovare sulle ore nuove della scorta serale.
