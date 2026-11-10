// attrezzi/fumetti-neri/fumetti-neri.js (culla) · VERSION 1.0.0
// Le spiegazioni (title, data-spiega) in un fumetto nero che resta negli screenshot e si apre anche col dito.
// Copia autonoma, senza dipendenze, di public/attrezzi/spiega.js del Gestionale ALMA 0.168.0 (02/11/2026),
// generato li' da nucleo/spiega.js e nucleo/spiega-browser.js. Regola, perche' e opzioni in README.md.
// Uso: <script src="fumetti-neri.js"></script> in testa alla pagina, prima di Chart.js. Non serve altro:
//   title="Resa: le offerte vinte sulle inviate"   -> «Resa» in grassetto, il resto sotto
//   data-spiega="Titolo: testo"                     -> come title, ma il browser da solo non lo mostra mai
//   data-spiega-no                                  -> li' resta il title del browser
// In node (prova-fumetti.mjs) non tocca niente e da' le funzioni pure: leggiSpiega, postoFumetto, stileChart.
(function () {
function leggiSpiega(testo) {
  var t = String(testo == null ? "" : testo).replace(/\r\n?/g, "\n").replace(/[ \t]+\n/g, "\n").trim();
  if (!t) return null;
  var a = t.indexOf("\n");
  if (a > 0) {
    var prima = t.slice(0, a).trim(), dopo = t.slice(a + 1).trim();
    if (prima.length <= 80 && dopo) return { titolo: prima.replace(/:$/, ""), resto: dopo };
  }
  var m = /^([^:\n]{1,60}):[ \t]+(\S[\s\S]*)$/.exec(t);
  if (m && !/\d$/.test(m[1]) && !/https?$/i.test(m[1]) && m[1].split(/\s+/).length <= 8) return { titolo: m[1].trim(), resto: m[2].trim() };
  return { titolo: "", resto: t };
}
function postoFumetto(el, fu, vista, margine) {
  var m = margine == null ? 8 : margine, stacco = 8;
  var w = Math.max(0, Math.min(fu.w, vista.w - 2 * m));
  var suSpazio = el.top - stacco - m, giuSpazio = vista.h - el.bottom - stacco - m;
  var sopra = fu.h <= suSpazio || (fu.h > giuSpazio && suSpazio > giuSpazio);
  var top = sopra ? el.top - stacco - fu.h : el.bottom + stacco;
  top = Math.max(m, Math.min(top, vista.h - m - fu.h));
  var centro = (el.left + el.right) / 2;
  var left = Math.max(m, Math.min(centro - w / 2, vista.w - m - w));
  var freccia = Math.max(12, Math.min(centro - left, w - 12));
  return { sopra: sopra, top: Math.round(top), left: Math.round(left), w: Math.round(w), freccia: Math.round(freccia) };
}
function stileChart(C, stile) {
  if (!C || !C.defaults || C.__spiega) return;
  C.__spiega = true;
  var d = C.defaults.plugins && C.defaults.plugins.tooltip;
  if (d) for (var k in stile) {
    if (stile[k] && typeof stile[k] === "object") d[k] = Object.assign({}, d[k] || {}, stile[k]);
    else d[k] = stile[k];
  }
  if (typeof C.register !== "function") return;
  C.register({
    id: "spiegaStile",
    beforeInit: function (chart) {
      var o = chart.config && chart.config.options, t = o && o.plugins && o.plugins.tooltip;
      if (!t || t.enabled === false || t.external) return;
      for (var k in stile) delete t[k];
      delete t.borderColor;
    },
  });
}
if (typeof document === "undefined") {
  if (typeof module !== "undefined" && module.exports) module.exports = { leggiSpiega: leggiSpiega, postoFumetto: postoFumetto, stileChart: stileChart };
  return;
}
(function avviaSpiega(css, stile) {
  if (window.__spiega) return;
  window.__spiega = true;
  var CAMPI = "input, select, textarea, option, [contenteditable=''], [contenteditable=true], [data-spiega-no]";
  var fu = null, corpo = null, attuale = null, prestato = null, timer = null, zittito = null, tocco = null;

  function fumetto() {
    if (fu) return fu;
    if (!document.getElementById("spiega-stile")) {
      var s = document.createElement("style");
      s.id = "spiega-stile";
      s.textContent = css;
      (document.head || document.documentElement).appendChild(s);
    }
    fu = document.createElement("div");
    fu.id = "spiega-fumetto";
    fu.className = "spiega-fumetto";
    fu.setAttribute("role", "tooltip");
    fu.hidden = true;
    document.body.appendChild(fu);
    return fu;
  }

  /** L'elemento con una spiegazione sotto il punto toccato, o null. */
  function bersaglio(nodo) {
    var e = nodo && nodo.nodeType === 1 ? nodo : nodo && nodo.parentElement;
    if (!e || !e.closest || e.closest(CAMPI) || e.closest(".spiega-fumetto")) return null;
    // Il piu' vicino con un testo; quello col title prestato al fumetto conta ancora.
    for (var b = e; b && b !== document.body && b !== document.documentElement; b = b.parentElement) {
      if (b.matches("iframe, svg title")) return null;
      if (testoDi(b)) return b;
    }
    return null;
  }
  function testoDi(b) {
    if (prestato && prestato.el === b && !b.hasAttribute("data-spiega")) return prestato.title.trim();
    return (b.getAttribute("data-spiega") || b.getAttribute("title") || "").trim();
  }

  /** Toglie il title per il tempo del fumetto (niente riquadro doppio) e lo rimette dopo. */
  function prendi(b) {
    var t = b.getAttribute("title");
    if (t == null) return;
    var nome = !b.hasAttribute("aria-label") && !b.hasAttribute("aria-labelledby") && !(b.textContent || "").trim();
    prestato = { el: b, title: t, nome: nome };
    b.removeAttribute("title");
    if (nome) b.setAttribute("aria-label", t);
  }
  function rendi() {
    var p = prestato;
    prestato = null;
    if (!p) return;
    if (!p.el.hasAttribute("title")) p.el.setAttribute("title", p.title);
    if (p.nome && p.el.getAttribute("aria-label") === p.title) p.el.removeAttribute("aria-label");
  }

  function mostra(b) {
    clearTimeout(timer);
    if (attuale === b && fu && !fu.hidden) return;
    nascondi();
    var testo = testoDi(b), parti = leggiSpiega(testo);
    if (!parti) return;
    var f = fumetto();
    prendi(b);
    f.textContent = "";
    if (parti.titolo) {
      var tt = document.createElement("strong");
      tt.className = "sp-titolo";
      tt.textContent = parti.titolo;
      f.appendChild(tt);
    }
    var r = document.createElement("span");
    r.className = "sp-resto";
    r.textContent = parti.resto;
    f.appendChild(r);
    f.style.left = "0px"; f.style.top = "0px";
    f.style.visibility = "hidden";
    f.hidden = false;
    var q = b.getBoundingClientRect();
    var p = postoFumetto(q, { w: f.offsetWidth, h: f.offsetHeight }, { w: document.documentElement.clientWidth || innerWidth, h: innerHeight });
    f.style.left = p.left + "px";
    f.style.top = p.top + "px";
    f.style.setProperty("--sp-freccia", p.freccia + "px");
    f.classList.toggle("sotto", !p.sopra);
    f.style.visibility = "";
    attuale = b;
    if (!(prestato && prestato.nome)) {
      var d = (b.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
      if (d.indexOf(f.id) < 0) { d.push(f.id); b.setAttribute("aria-describedby", d.join(" ")); }
    }
  }
  function nascondi() {
    clearTimeout(timer);
    if (attuale) {
      var d = (attuale.getAttribute("aria-describedby") || "").split(/\s+/).filter(function (x) { return x && x !== "spiega-fumetto"; });
      if (d.length) attuale.setAttribute("aria-describedby", d.join(" ")); else attuale.removeAttribute("aria-describedby");
    }
    rendi();
    attuale = null;
    if (fu) fu.hidden = true;
  }

  // Il mouse: dopo 250 ms, finche' resta sull'elemento.
  document.addEventListener("pointerover", function (ev) {
    if (ev.pointerType === "touch") return;
    var b = bersaglio(ev.target);
    if (b === attuale && b) { clearTimeout(timer); return; }
    clearTimeout(timer);
    if (!b) { if (attuale && !attuale.contains(ev.target)) nascondi(); return; }
    if (b === zittito) return;
    // Il title va via subito: il riquadro del browser non fa in tempo a comparire.
    if (attuale) nascondi();
    prendi(b);
    timer = setTimeout(function () { rendi(); if (b.isConnected) mostra(b); }, 250);
  }, true);
  document.addEventListener("pointerout", function (ev) {
    if (ev.pointerType === "touch") return;
    var b = bersaglio(ev.target);
    var dove = ev.relatedTarget;
    if (zittito && !(dove && zittito.contains(dove))) zittito = null;
    if (!b || (dove && b.contains(dove))) return;
    clearTimeout(timer);
    if (attuale === b || (prestato && prestato.el === b)) nascondi();
  }, true);

  // La tastiera: col fuoco (solo quello visibile, non quello del clic).
  document.addEventListener("focusin", function (ev) {
    var b = bersaglio(ev.target);
    if (!b || b !== ev.target) return;
    var visibile = true;
    try { visibile = b.matches(":focus-visible"); } catch (e) {}
    if (visibile) mostra(b);
  });
  document.addEventListener("focusout", function (ev) { if (attuale && ev.target === attuale) nascondi(); });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && fu && !fu.hidden) { zittito = attuale; nascondi(); }
  });

  // Il dito: un tocco breve apre, un secondo tocco o un tocco altrove chiude.
  document.addEventListener("pointerdown", function (ev) {
    if (ev.pointerType === "touch") tocco = { x: ev.clientX, y: ev.clientY, t: Date.now(), el: ev.target };
    else tocco = null;
    if (attuale && !attuale.contains(ev.target)) nascondi();
  }, true);
  document.addEventListener("pointerup", function (ev) {
    if (ev.pointerType !== "touch" || !tocco) return;
    var breve = Date.now() - tocco.t < 600 && Math.abs(ev.clientX - tocco.x) < 12 && Math.abs(ev.clientY - tocco.y) < 12;
    var b = breve ? bersaglio(tocco.el) : null;
    tocco = null;
    if (!b) return;
    if (attuale === b) nascondi(); else mostra(b);
  }, true);

  // Lo scorrimento e la finestra che cambia lo staccano dall'elemento: via.
  addEventListener("scroll", function () { if (attuale) nascondi(); }, true);
  addEventListener("resize", function () { if (attuale) nascondi(); });
  addEventListener("blur", function () { if (attuale) nascondi(); });

  // Chart.js: gia' caricato, o quando arriva (/mk/vendor/chart.umd.js scrive window.Chart).
  if (window.Chart) stileChart(window.Chart, stile);
  else {
    try {
      var C;
      Object.defineProperty(window, "Chart", {
        configurable: true, enumerable: true,
        get: function () { return C; },
        set: function (v) { C = v; try { stileChart(v, stile); } catch (e) {} },
      });
    } catch (e) {}
  }
  window.spiega = { mostra: mostra, nascondi: nascondi, leggi: leggiSpiega };
})("\n  .spiega-fumetto { --sp-fondo: rgba(0, 0, 0, 0.9); --sp-testo: #fff; --sp-freccia: 50%;\n    position: fixed; z-index: 2147483000; left: 0; top: 0; box-sizing: border-box;\n    width: max-content; max-width: min(320px, calc(100vw - 16px)); padding: 8px 10px; border-radius: 6px;\n    background: var(--sp-fondo); color: var(--sp-testo); pointer-events: none;\n    font-family: -apple-system, system-ui, \"Segoe UI\", sans-serif; font-size: 13px; font-weight: 400; line-height: 1.4;\n    text-align: left; white-space: normal; overflow-wrap: anywhere; letter-spacing: normal; text-transform: none; }\n  .spiega-fumetto[hidden] { display: none; }\n  .spiega-fumetto .sp-titolo { display: block; font-weight: 700; margin-bottom: 3px; }\n  .spiega-fumetto .sp-resto { display: block; white-space: pre-line; }\n  .spiega-fumetto::after { content: \"\"; position: absolute; left: var(--sp-freccia); top: 100%; margin-left: -6px;\n    border: 6px solid transparent; border-top-color: var(--sp-fondo); }\n  .spiega-fumetto.sotto::after { top: auto; bottom: 100%; border-top-color: transparent; border-bottom-color: var(--sp-fondo); }\n  @media print { .spiega-fumetto { display: none; } }\n", {"backgroundColor":"rgba(0, 0, 0, 0.9)","titleColor":"#fff","bodyColor":"#fff","footerColor":"#fff","borderWidth":0,"cornerRadius":6,"padding":10,"caretSize":6,"boxPadding":4,"titleMarginBottom":6,"titleFont":{"size":13,"weight":"bold"},"bodyFont":{"size":13},"footerFont":{"size":13,"weight":"bold"}});
})();
