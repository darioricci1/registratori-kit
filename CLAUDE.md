# Come si lavora qui

**Si parla in italiano, sempre.** Dario è italiano: ogni risposta a lui è in italiano.

Questo repository è **registratori-kit**: lo stato dei registratori Focus dei kit di Alma Sicurezza (chi registra,
da quando, la percentuale di ogni giorno, le foto, il confronto con l'ANAGRAFICA KIT). Fino al 10/11/2026 stava in
`darioricci1/kit-rifiuti-programma`, cartella `prova-nvr-remoto/` e `analisi/compiti/p2p_ponte*`: Dario l'ha voluto a
parte. Cosa c'è e da dove ripartire: `README.md`.

## Il giro
- Commit e push direttamente su `main`, niente rami e pull request. Un push al massimo per ogni risposta a Dario: ogni
  push ricostruisce il sito su Vercel (progetto `prova-nvr-remoto`).
- Prima del push: `node --check` sui `.js` di `api/` e sugli script dentro le pagine, `python3 -m py_compile` sui
  compiti.
- Versione nell'intestazione di ogni file, alzata a ogni modifica. Messaggi di commit in italiano che dicono la decisione.
- I ponti sui PC (cartella `compiti/`) arrivano col meccanismo dei compiti di Kit_Rifiuti: `compito.zip` nella cartella
  Drive «Analisi video» con le proprietà `compito` (un nome nuovo per ogni invio) e `pc`.
- Il sito è nel registro del software del gestionale (`nucleo/software-registro.js` di `darioricci1/gestionale-alma`,
  riga «prova-nvr-remoto»): a ogni cambio si aggiorna lì.

## Segreti
- Le password dei registratori (quella comune e quella dei kit fino al 199) e i file di UVMS: solo su Drive di Alma
  (dentro il compito, in `focus_accesso.txt`) e nello scratchpad. Mai nel repository, in un commit, in un messaggio o in
  una pagina.
- La chiave dell'account di servizio di Alma non entra mai nel repository.
- La libreria FocusNetSDK è di Voyager/Focus: non entra nel repository e non esce da Alma.
- Il token RMS di Teltonika è di Dario: non si salva da nessuna parte.
