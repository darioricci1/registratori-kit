# fuoco5: ripristino del fuoco di KIT249 SP7 (Viano), cam 3

Compito 0.5.0 del 16/11/2026. Fa **una cosa sola**: riporta il fuoco della cam 3 del sito (canale 2 del registratore
Focus, contando da 0) alla foto di partenza di fuoco4 (16/11 alle 9:31). L'autorizzazione è quella di Dario del 15/11:
«solo KIT249, solo zoom e fuoco, rimettere com'era».

Qui stanno solo `compito.py`, `prova_ripristino.py` e `fuoco.json`. Lo zip da caricare (con `focus_nvr.py`, la
libreria FocusNetSDK, `focus_accesso.txt`, `remoto.json` con l'uid e `riferimento/partenza.npy` e `.jpg`) sta solo
nello scratchpad: `compito_fuoco5/compito.zip`. Proprietà: `compito=fuoco5`, `pc=2026-002`.

Prove a tavolino: `python3 prova_ripristino.py [cartella con riferimento/]`, e con `FOTO_FUOCO4=<cartella del
risultato di fuoco4>` anche sulle foto vere di quella prova.

## Cosa è successo in fuoco4 (16/11, 9:31-9:37)

Nitidezza = varianza del Laplaciano sulle foto 960x540 del risultato. Partenza 23.384, fine 135. I comandi sono stati
64, **tutti di fuoco** (FOCUS_IN 10 = «vicino», FOCUS_OUT 11 = «lontano»), nessuno di zoom.

| Ora | Comandi | Foto e nitidezza | Cosa vuol dire |
|---|---|---|---|
| 9:31:15 | vicino 150, poi lontano 150 (verifica) | 005: 21.926, 006: 22.069 | quasi niente: la telecamera era ancora a fuoco al 95% |
| | | | ma le soglie di «uguale», prese da 4 foto ferme, erano strettissime (fine 0,03): «non tornata» |
| 9:31:35 | vicino 150 | 008: 804 | il primo salto: un impulso «vicino» la butta fuori fuoco |
| 9:31:42-50 | lontano 150, lontano 150 | 009: 778, 010: 5.767 | «lontano» fa passi piccoli: il primo se lo mangia il gioco |
| 9:31:58 | vicino 150 (la ricerca torna indietro) | 011: 219 | altro salto |
| 9:32:13-27 | vicino 75 ×3 | 013-015: 142, 136, 130 | in fondo alla sfocatura |
| 9:32:32-36 | lontano 75 ×3, **senza foto in mezzo** | 016: 313 | |
| 9:32:42-33:07 | lontano 75 ×5 | 017-021: 1.540, 7.576, 14.822, 21.282, **24.180** | alla 021 era di nuovo a fuoco (meglio della partenza, scala 1,000), ma la «distanza» 1,36 > 1 non bastava per dire «tornata» |
| 9:33:13-20 | lontano 75, vicino 75 | 022: 20.665, 023: 20.756 | |
| 9:33:36 | vicino 37 | 025: 783 | terzo salto, con l'impulso più corto |
| 9:33:46-34:02 | lontano 37 ×2, vicino 37 | 026-028: 768, 1.612, 1.397 | fermo: «non torna nemmeno con la foto» |
| 9:34:09-20 | **vicino 150 ×5 alla cieca** (rimetti: pareggiare il conto netto -5) | 029: 122 | il colpo finale: in fondo alla corsa |
| 9:34:30-37:25 | 36 impulsi ±150/75/37 guidati da una «distanza» ferma a ~31 | 030-056: 112-262 | la guida era satura: girava a vuoto |

Perché:

1. **L'ottica non è simmetrica.** Un impulso «vicino» fa salti enormi (anche da 37 ms: 20.418 → 783), uno «lontano»
   passi piccoli e regolari. Contare gli impulsi non dice dov'è la lente, e `rimetti` ha pareggiato il conto con 5
   «vicino» da 150 ms senza guardare.
2. **Soglie troppo strette.** «Uguale alla partenza» era «entro 1,5 volte il rumore di 4 foto ferme»: la verifica da
   150 ms non è «tornata» per uno scarto invisibile, ed è partita la ricerca; alla foto 021 la telecamera era di nuovo
   a fuoco e il compito non l'ha riconosciuto.
3. **Passi alla cieca.** La ricerca (`cerca_meglio`) tornava indietro di più passi senza foto, e `rimetti` ne ha
   mandati 5 di fila.
4. **Guida satura.** La «distanza dalla partenza» (1 - correlazione dei dettagli fini) oltre una certa sfocatura vale
   sempre ~31: da lì in poi la ricerca non sapeva da che parte andare.
5. **Lo zoom non è cambiato.** Zero comandi di zoom. L'ingrandimento che si vede è la sfocatura più il «respiro» della
   lente (scala stimata 1,016-1,04 sulle foto sfocate, 1,000 sulla 021 a fuoco): l'inquadratura del confronto è la
   stessa (bidoni e auto negli stessi punti).

## Come lavora il ripristino (e perché non ripete fuoco4)

- Un impulso alla volta, **sempre seguito da una foto** (le prove controllano che non ci siano mai due impulsi senza
  foto in mezzo). Niente conto netto, niente «rimetti».
- Parte da «lontano» (11), il verso che in fuoco4 ha sempre recuperato (017-021), a 75 ms; oltre il 30% della
  nitidezza di partenza passa a 37 ms.
- Guida a due regimi: lontano dal picco la **forma** (somiglianza con la partenza a quattro scale, dopo aver tolto un
  eventuale spostamento), che scende in modo regolare anche dove la nitidezza è al fondo; vicino al picco la
  **nitidezza**. Due passi di fila peggiori = picco passato: inverte e dimezza l'impulso. Dieci passi fermi = verso
  sbagliato o fine corsa: inverte. Un'auto o una persona che entra fra due foto non conta come peggioramento.
- Si ferma **appena** nitidezza ≥ 70% della partenza e inquadratura che combacia (stessa scena, spostamento ≤ 4 px a
  1280, scala entro l'1,5%). Con la luce diversa dalle 9:31 si ferma sul picco ritrovato (≥ 85% del massimo visto).
- Messa a fuoco automatica: **la libreria non ce l'ha** (FocusNetSDK 1.0.0.3: in `E_PTZ_CTRL` solo direzioni, zoom,
  fuoco, iride, giro, menu OSD; più i preset, e un preset della posizione buona non è mai stato salvato). Non si usano
  i comandi del menu OSD.
- Solo i comandi 10 e 11: `Fuoco._ptz` rifiuta qualunque altro comando, anche lo zoom. Il «lascia» finale solo sul
  fuoco.
- Tetti: 150 impulsi, 45 minuti dal primo comando, 8 inversioni. Il «lascia» non confermato ferma tutto.
- Luce: finestra 9:30-15:00 sull'ora del PC e foto del canale di giorno (o luce 45-215 e un altro canale a colori).
- Se il PC si spegne a metà, riparte da capo: è guidato dalle foto, non dal conto degli impulsi.

## Uscita

`ripristino.json` (ogni passo: verso, ms, foto prima e dopo, nitidezza, rapporto con la partenza, forma, somiglianza,
spostamento, scala, giudizio; inversioni; esito), `foto/NNN_*.jpg` (la foto dopo il passo N è quella prima del passo
N+1), `fine.jpg`, `confronto_fine.jpg` (partenza a sinistra, fine a destra), `avanzamento.txt`, `stato.json`.
