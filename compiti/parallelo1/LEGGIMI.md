# parallelo1: più registratori Focus insieme

Compito 0.1.0 del 16/11/2026 per il COMPUTERONE. **Pronto, NON mandato.** Domanda di Dario: come interrogare più
registratori contemporaneamente. Il ponte li fa uno alla volta (`SDK = threading.Lock()`) e ogni collegamento P2P
(TUTK) prende 30-60 s: un giro su ~300 kit dura ore. La libreria è quella di UVMS, che tiene molti registratori
collegati insieme (Connect rende un hSERVER per registratore, le funzioni di ritorno lo ricevono).

## Cosa misura

Gli stessi kit (fino a 40, fra quelli che rispondono: `op=stato` del sito, prima chi ha più risposte nelle ultime 24
ore; il 998 di prova escluso), sola lettura leggera: collegamento, modello, canali, minuti registrati oggi. Niente
video, niente comandi alle telecamere.

- **N=1**: un processo, un collegamento alla volta (come il ponte). È la base di tutte e due le strade.
- **Strada A**: un processo, UNA istanza della libreria, N Connect insieme da N fili (N = 4, 8, 16); le funzioni di
  ritorno sono una sola tabella per tutti e smistano l'esito per hSERVER (`parallelo.Smistatore`).
- **Strada B**: N processi (N = 2, 4, 8), ognuno con la sua copia della cartella FocusNetSDK e una parte dei kit, uno
  alla volta. Due processi con la libreria insieme non erano mai stati provati.

Ordine N1, B2, A4, B4, A8, B8, A16, 30 s fra una prova e l'altra. Ogni prova gira in processi a parte (`lavoro.py`,
lanciato come `exe --compito`): un crash della libreria non ferma il compito, si legge nel codice d'uscita
(0xC0000005) e in `guasto_memoria.txt`. Una strada si ferma alla prima prova con un crash o con i falliti saliti di
più di 5 punti rispetto a N=1 (anche una prova ferma oltre il doppio del tempo di N=1 conta come crash). Tetto 2 ore.

**Criterio, scritto prima**: una strada vince se con N=8 fa il giro in meno di un quarto del tempo di N=1, senza più
falliti di N=1 e senza crash. Se vincono tutte e due, la più veloce a N=8; entro il 10%, la A (un processo solo).

## Uscita

`uscita/parallelo.json`: i kit per etichetta (mai l'UID), per ogni prova tempo totale, riusciti e falliti contro
N=1, persi e guadagnati, crash e codici d'uscita, memoria (picco per processo e somma), quanti collegamenti insieme
davvero, esiti orfani, i risultati kit per kit (secondi di Connect, dell'esito, delle letture, modo P2P); il
verdetto. `uscita/avanzamento.txt` (ultima riga «fatto»), `uscita/prove/` (avanzamento e guasti di ogni processo).
La cartella `lavori/` (UID dei kit e copie della libreria) si cancella alla fine.

## File

`compito.py` (il giro delle prove), `lavoro.py` (un processo), `parallelo.py` (libreria con N collegamenti, lettura di
un kit, funzioni pure), `parallelo.json` (parametri), `prova_parallelo.py` (prove a tavolino:
`python3 prova_parallelo.py [cartella con focus_nvr.py]`, libreria finta che chiama le funzioni di ritorno vere dalla
loro tabella, da fili suoi, con handle riusati, esiti dopo la chiusura, falliti, muti e crash).

Lo zip (con `focus_nvr.py`, `FocusNetSDK/` e `focus_accesso.txt` presi dal compito p2p_ponte38) sta solo nello
scratchpad: `compito_parallelo1/compito.zip`. Proprietà: `compito=parallelo1`, `pc=COMPUTERONE`. Serve il segnaposto
`risultato_parallelo1.zip` su Drive «Analisi video». Il compito chiude il ponte che gira sul COMPUTERONE (un compito
alla volta): dopo va rimandato un ponte col nome nuovo.
