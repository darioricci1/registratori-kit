// attrezzi/tendina-ricerca/tendina.js
// VERSION: 1.2.0 (estratta da bbs-squadre 2.185.0, pickerPersone)
// 1.2.0 (fiere-italia 1.32.0): i risultati in ordine (prima i nomi che cominciano con quello che si scrive, poi gli
//        altri) e la parte trovata in giallo, nel nome e nel dettaglio. `cerca: (testo) => voci` per gli elenchi
//        enormi (87.000 aziende): le voci le trova e le ordina chi chiama, la tendina le mostra. `alScegli: (voce) => {}`
//        con `singola`: scegliere fa un'azione (apre una scheda) invece di diventare la scelta.
// 1.1.0: `singola: true` fa una combobox a scelta singola, senza caselle: si tocca una voce, diventa la
//        scelta (al posto della precedente) e l'elenco si chiude.
//
// TENDINA CON RICERCA E SCELTA MULTIPLA.
// Un campo con la lente e la freccia (chevron) a destra. Cliccando si apre
// l'elenco di tutte le voci in ordine alfabetico, ognuna con la sua casella da
// spuntare; l'elenco resta aperto finché si sceglie. Scrivendo l'elenco si
// restringe (ogni parola scritta deve essere l'inizio di una parola del nome,
// accenti ignorati). Le voci scelte diventano chip nel campo, con la × per
// toglierle.
//
// Tastiera: frecce su/giù per muoversi, Invio spunta (se resta una voce sola,
// spunta quella), Backspace a campo vuoto toglie l'ultima scelta, Esc chiude.
// Telefono: il campo sale in cima allo schermo e in fondo all'elenco c'è il
// pulsante «Fatto», perché l'elenco copre la pagina.
//
// USO
//   const scelti = new Set();
//   tendinaRicerca(document.getElementById("box"), {
//     voci: [{ id: "1", nome: "Andrea Belli", dettaglio: "Adjunct Professor · Cattolica",
//              etichette: [{ testo: "nessun accesso", tipo: "ambra" }] }],
//     scelti,                      // Set di id, la tendina lo modifica
//     massimo: 7,                  // facoltativo
//     segnaposto: "Scrivi qui il nome di chi vuoi invitare",
//     alCambio: (scelti) => {},    // facoltativo
//     singola: true,               // facoltativo: una scelta sola, senza caselle
//   });
// Elenchi enormi o ricerche su più campi: al posto di `voci`
//   tendinaRicerca(box, { singola: true, minimo: 2,
//     cerca: (testo) => [{ id, nome, dettaglio }, ...],   // già filtrate e in ordine, al massimo qualche decina
//     alScegli: (voce) => apriScheda(voce.id) });          // la voce non resta scelta, il campo si svuota
// Una voce con `fissa: true` compare spuntata e bloccata (es. «tu, ci sei
// sempre», «invito mandato») e non entra in `scelti`; con `evidenza: true` ha
// lo sfondo colorato.

(function () {
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const senzaAccenti = (t) => String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const parole = (t) => senzaAccenti(t).split(/[\s'’,.-]+/).filter(Boolean);
  // 1.2.0: il testo con le parole cercate in giallo (accenti ignorati: senzaAccenti lascia la stessa lunghezza)
  const evidenzia = (testo, cercate) => {
    const s = String(testo == null ? "" : testo);
    if (!cercate || !cercate.length || !s) return esc(s);
    const n = senzaAccenti(s), segni = new Array(s.length).fill(false);
    for (const p of cercate) { let k = n.indexOf(p); while (k >= 0) { for (let x = k; x < k + p.length && x < s.length; x++) segni[x] = true; k = n.indexOf(p, k + 1); } }
    let out = "", dentro = false;
    for (let x = 0; x < s.length; x++) {
      if (segni[x] !== dentro) { out += segni[x] ? '<mark class="tr-trovato">' : "</mark>"; dentro = segni[x]; }
      out += esc(s[x]);
    }
    return out + (dentro ? "</mark>" : "");
  };
  const LENTE = '<svg class="tr-lente" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="M20 20l-3.5-3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const CHEVRON = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  function tendinaRicerca(box, o) {
    const scelti = o.scelti || new Set();
    const singola = !!o.singola;
    const massimo = singola ? 1 : (o.massimo || 0);
    const tutte = (o.voci || []).slice()
      .sort((x, y) => String(x.nome).localeCompare(String(y.nome), "it", { sensitivity: "base" }));
    const perId = new Map(tutte.map((v) => [String(v.id), v]));
    let trovate = [], sel = 0, aperto = false;

    box.innerHTML = `<div class="tr-scatola">
      <div class="tr-campo"><span class="tr-chip"></span>
        <div class="tr-scrivi">${LENTE}<input type="text" placeholder="${esc(o.segnaposto || "Cerca un nome…")}" autocomplete="off" role="combobox" aria-expanded="false"></div>
        <button type="button" class="tr-freccia" aria-label="Apri l'elenco">${CHEVRON}</button></div>
      <div class="tr-elenco" role="listbox" hidden></div></div>`;
    const scatola = box.querySelector(".tr-scatola"), inp = box.querySelector("input");
    const elenco = box.querySelector(".tr-elenco"), chip = box.querySelector(".tr-chip");

    const cambiato = () => { disegnaChip(); if (aperto) disegnaElenco(); o.alCambio && o.alCambio(scelti); };
    const disegnaChip = () => {
      chip.innerHTML = [...scelti].map((id) => `<span class="tr-pastiglia">${esc((perId.get(String(id)) || {}).nome || "?")}<button type="button" data-via="${esc(id)}" aria-label="Togli">×</button></span>`).join("");
      chip.querySelectorAll("[data-via]").forEach((b) => { b.onclick = (e) => { e.stopPropagation(); scelti.delete(b.dataset.via); cambiato(); }; });
    };
    const disegnaElenco = () => {
      const cerca = parole(inp.value);
      let visibili;
      if (o.cerca) {
        // 1.2.0: elenco enorme, le voci le trova chi chiama
        visibili = inp.value.trim().length >= (o.minimo || 1) ? o.cerca(inp.value) || [] : [];
      } else {
        const passa = (v) => cerca.every((w) => parole(v.nome).some((x) => x.startsWith(w)));
        visibili = tutte.filter(passa);
        // 1.2.0: prima i nomi che cominciano con quello che si è scritto, poi gli altri (in ordine alfabetico)
        const tutto = senzaAccenti(inp.value).trim();
        if (tutto) visibili = [...visibili.filter((v) => senzaAccenti(v.nome).startsWith(tutto)), ...visibili.filter((v) => !senzaAccenti(v.nome).startsWith(tutto))];
      }
      trovate = visibili.filter((v) => !v.fissa);
      if (sel >= trovate.length) sel = Math.max(0, trovate.length - 1);
      const pieno = !singola && massimo && scelti.size >= massimo;
      const righe = visibili.map((v) => {
        const i = v.fissa ? -1 : trovate.indexOf(v);
        const spuntata = v.fissa || scelti.has(v.id);
        const bloccata = v.fissa || (pieno && !scelti.has(v.id));
        const etichette = (v.etichette || []).map((e) => ` <span class="tr-etichetta ${esc(e.tipo || "")}">${esc(e.testo)}</span>`).join("");
        return `<label class="tr-voce ${i === sel ? "attiva" : ""} ${v.evidenza ? "evidenza" : ""} ${singola && spuntata ? "scelta" : ""}" ${i >= 0 ? `data-i="${i}"` : ""} role="option" aria-selected="${spuntata}">
          ${singola ? "" : `<input type="checkbox" ${spuntata ? "checked" : ""} ${bloccata ? "disabled" : ""}>`}
          <span><b>${evidenzia(v.nome, cerca)}</b>${etichette}${v.dettaglio ? ` <span class="tr-dettaglio">${evidenzia(v.dettaglio, cerca)}</span>` : ""}</span></label>`;
      }).join("");
      elenco.innerHTML = (pieno ? `<div class="tr-voce tr-nota">Hai già scelto ${massimo} voci, il massimo: per aggiungerne una, togline un'altra.</div>` : "") +
        (righe || `<div class="tr-voce tr-nota">${esc(o.cerca ? (inp.value.trim().length < (o.minimo || 1) ? (o.testoScrivi || "Scrivi per cercare.") : (o.testoNessuno || "Nessun nome così.")) : tutte.length ? (o.testoNessuno || "Nessun nome così.") : (o.testoVuoto || "Per ora l'elenco è vuoto."))}</div>`) +
        (scelti.size && !singola ? `<button type="button" class="tr-fatto">Fatto (${scelti.size} ${scelti.size === 1 ? "scelta" : "scelte"})</button>` : "");
      elenco.querySelectorAll(".tr-voce[data-i]").forEach((el) => {
        if (singola) { el.onclick = () => spunta(trovate[Number(el.dataset.i)]); return; }
        el.querySelector("input").onchange = (e) => {
          const v = trovate[Number(el.dataset.i)];
          if (e.target.checked) scelti.add(v.id); else scelti.delete(v.id);
          sel = Number(el.dataset.i);
          // scelta una voce dopo averla cercata: il campo si svuota, si cerca la prossima
          if (e.target.checked && inp.value) { inp.value = ""; sel = 0; }
          cambiato(); inp.focus();
        };
      });
      const fatto = elenco.querySelector(".tr-fatto");
      if (fatto) fatto.onclick = chiudi;
      const att = elenco.querySelector(".tr-voce.attiva");
      if (att) att.scrollIntoView({ block: "nearest" });
    };
    const telefono = () => matchMedia("(max-width:760px)").matches;
    const apri = () => {
      if (aperto) return;
      aperto = true; elenco.hidden = false; scatola.classList.add("aperta"); inp.setAttribute("aria-expanded", "true"); disegnaElenco();
      // sul telefono il campo sale in cima: sotto resta spazio per l'elenco
      if (telefono() && !box.closest("dialog, .velo")) {
        document.body.classList.add("tr-aperta");
        setTimeout(() => window.scrollTo({ top: box.getBoundingClientRect().top + window.scrollY - 8, behavior: "smooth" }), 250);
      }
    };
    const chiudi = () => {
      aperto = false; elenco.hidden = true; inp.value = ""; scatola.classList.remove("aperta");
      inp.setAttribute("aria-expanded", "false"); document.body.classList.remove("tr-aperta");
    };
    const spunta = (v) => {
      if (singola && o.alScegli) { inp.value = ""; chiudi(); inp.blur(); o.alScegli(v); return; }   // 1.2.0: scegliere fa un'azione
      if (singola) { scelti.clear(); scelti.add(v.id); inp.value = ""; cambiato(); chiudi(); inp.blur(); return; }
      if (scelti.has(v.id)) scelti.delete(v.id); else if (!massimo || scelti.size < massimo) scelti.add(v.id); cambiato();
    };

    inp.onfocus = apri;
    inp.onclick = apri;
    box.querySelector(".tr-freccia").onclick = () => { if (aperto) chiudi(); else { apri(); inp.focus(); } };
    inp.oninput = () => { sel = 0; apri(); disegnaElenco(); };
    inp.onkeydown = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); chiudi(); inp.blur(); return; }
      if (e.key === "Backspace" && !inp.value && scelti.size) { scelti.delete([...scelti].pop()); cambiato(); return; }
      if (!aperto) apri();
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!trovate.length) return;
        sel = (sel + (e.key === "ArrowDown" ? 1 : trovate.length - 1)) % trovate.length;
        disegnaElenco();
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (!trovate.length) return;
        spunta(trovate[trovate.length === 1 ? 0 : sel]);
        if (inp.value) { inp.value = ""; sel = 0; disegnaElenco(); }
      }
    };
    // clic fuori: si chiude (e se la tendina sparisce dalla pagina, si smette di ascoltare)
    const fuori = (e) => { if (!box.isConnected) return document.removeEventListener("mousedown", fuori); if (aperto && !box.contains(e.target)) chiudi(); };
    document.addEventListener("mousedown", fuori);
    disegnaChip();
    return { chiudi, apri, scelti };
  }

  tendinaRicerca.evidenzia = evidenzia;   // 1.2.0: lo stesso giallo anche fuori dalla tendina (per esempio nelle tabelle)
  tendinaRicerca.senzaAccenti = senzaAccenti;
  window.tendinaRicerca = tendinaRicerca;
})();
