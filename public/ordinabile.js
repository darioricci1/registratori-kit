// attrezzi/tabelle-ordinabili/ordinabile.js
// VERSION: 1.0.0 (nato in fiere-italia, pagina 1.13.0, 21 ottobre 2026)
//
// TUTTE LE COLONNE ORDINABILI CON UN CLIC SULL'INTESTAZIONE.
// Un clic ordina per quella colonna, un altro clic inverte; la freccia accanto al titolo dice
// come è ordinata. Si usa anche da tastiera (Tab sull'intestazione, poi Invio).
//
// DUE MODI.
// 1. Tabella scritta tutta nella pagina: la riordina da sé, riga per riga.
//      tabellaOrdinabile(document.querySelector("#mia-tabella"));
//    Il valore di una cella è il suo testo; i numeri all'italiana («3.397», «12,5») contano come
//    numeri. Per date o valori diversi dal testo: <td data-valore="2026-04-12">12 apr 2026</td>.
// 2. Tabella fatta dal programma a pezzi (paginata, migliaia di righe): ordina il programma i suoi
//    dati, il pezzo dice solo cosa è stato chiesto.
//      const t = tabellaOrdinabile(tab, { alCambio: (chiave, verso) => { ordina(chiave, verso); disegna(); } });
//    chiave = data-chiave dell'intestazione (se no il numero della colonna), verso = 1 crescente, -1 decrescente.
//
// Sull'intestazione: data-chiave="nome" (la chiave per alCambio), data-ordina="no" (colonna ferma),
// data-verso="giu" (il primo clic ordina dal più grande: utile per numeri e date recenti).
// Restituisce { ordina(), stato(), imposta(colonna, verso) }; imposta() segna la freccia senza riordinare
// (per esempio quando l'ordine arriva dall'indirizzo della pagina o da un menu).
//
// Lo stile è in ordinabile.css (usa --grigio e --accento del progetto, se ci sono).

(function () {
  function valore(td) {
    if (!td) return "";
    const v = (td.dataset.valore != null ? td.dataset.valore : td.textContent).trim();
    if (/^-?[\d.]+(,\d+)?$/.test(v) && /\d/.test(v)) return Number(v.replace(/\./g, "").replace(",", "."));
    return v.toLocaleLowerCase("it");
  }
  function confronta(x, y) {
    if (x === "" && y !== "") return 1;           // le celle vuote sempre in fondo
    if (y === "" && x !== "") return -1;
    if (typeof x === "number" && typeof y === "number") return x - y;
    if (typeof x === "number") return -1;
    if (typeof y === "number") return 1;
    return x.localeCompare(y, "it", { numeric: true });
  }

  function tabellaOrdinabile(tab, o) {
    o = o || {};
    const ths = [...tab.tHead.rows[0].cells];
    let stato = { col: o.col == null ? null : o.col, verso: o.verso || 1 };
    const chiaveDi = (i) => ths[i].dataset.chiave || i;
    function segna() {
      ths.forEach((th, i) => {
        if (th.dataset.ordina === "no") return;
        th.setAttribute("aria-sort", i === stato.col ? (stato.verso > 0 ? "ascending" : "descending") : "none");
      });
    }
    function ordina() {
      if (stato.col == null) return;
      for (const tb of tab.tBodies) {
        const righe = [...tb.rows];
        righe.sort((a, b) => {
          const x = valore(a.cells[stato.col]), y = valore(b.cells[stato.col]);
          const c = confronta(x, y);
          return x === "" || y === "" ? c : c * stato.verso;   // le vuote restano in fondo anche al contrario
        });
        righe.forEach((r) => tb.appendChild(r));
      }
    }
    ths.forEach((th, i) => {
      if (th.dataset.ordina === "no") return;
      th.classList.add("ordinabile");
      th.tabIndex = 0;
      th.title = th.title || "Ordina per questa colonna";
      const clic = () => {
        stato = { col: i, verso: stato.col === i ? -stato.verso : th.dataset.verso === "giu" ? -1 : 1 };
        segna();
        if (o.alCambio) o.alCambio(chiaveDi(i), stato.verso); else ordina();
      };
      th.addEventListener("click", clic);
      th.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); clic(); } });
    });
    segna();
    return {
      ordina,
      stato: () => ({ chiave: stato.col == null ? null : chiaveDi(stato.col), col: stato.col, verso: stato.verso }),
      imposta(col, verso) {
        const i = typeof col === "number" ? col : ths.findIndex((th) => th.dataset.chiave === col);
        stato = { col: i >= 0 ? i : null, verso: verso || 1 };
        segna();
      },
    };
  }
  window.tabellaOrdinabile = tabellaOrdinabile;
})();
