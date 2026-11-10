// registratori-kit/api/_orari.js
// version: 1.0.0 (10/11/2026) - le ore in cui un kit e' acceso, lette dalle note degli ODM (Dario: «se un odm ti dice che il
//   kit funziona solo in alcuni orari, prova ad accedere in quegli orari»). Funzione pura, provata in prove/orari.test.mjs.
//   Valgono solo le frasi su quando il kit C'E' («risponde solo di sera», «acceso solo dalle 10 alle 16»); quelle su quando
//   manca («salta dalle 7 alle 19», «spento dalle...») non dicono quando provarlo e si lasciano stare.

/** Le finestre [ora_inizio, ora_fine) in cui provare il kit, in ore italiane 0-24. Una finestra che passa la mezzanotte
 *  ha inizio > fine (22 -> 6). Nessuna finestra: []. */
function finestreAccese(note) {
  const t = String(note || "").toLowerCase().replace(/\s+/g, " ");
  const out = [];
  const presente = "(?:acces[oa]|rimast[oa] acces[oa]|risponde|si vede|funziona|va|visibile|si collega)";
  // «acceso solo dalle 10 alle 16», «risponde solo dalle 7:30 alle 19»
  const re = new RegExp(presente + "[^.;\\-]{0,30}?solo dalle (?:ore )?(\\d{1,2})(?:[:.,]\\d{2})? (?:alle|-) ?(?:ore )?(\\d{1,2})", "g");
  for (const m of t.matchAll(re)) out.push([Number(m[1]), Number(m[2])]);
  // «risponde solo di sera», «si vede solo di notte», «solo la mattina»
  const parti = [[/solo (?:di |la )?sera/, [18, 23]], [/solo (?:di |la )?notte/, [22, 6]], [/solo (?:di |la )?mattin[ao]/, [7, 12]],
    [/solo (?:di |il )?pomeriggio/, [13, 18]], [/solo (?:di )?giorno/, [9, 17]]];
  for (const [r, f] of parti) {
    const m = t.match(new RegExp(presente + "[^.;\\-]{0,20}?" + r.source));
    if (m) out.push(f);
  }
  // «risponde a sms alle 20:30», «risponde solo di sera alle 22 circa»: un'ora sola, si prova da un'ora prima a un'ora dopo
  for (const m of t.matchAll(/risponde[^.;\-]{0,40}? alle (?:ore )?(\d{1,2})(?:[:.,]\d{2})?/g)) {
    const h = Number(m[1]);
    if (!out.some(([a, b]) => (a <= b ? h >= a && h < b : h >= a || h < b))) out.push([(h + 23) % 24, (h + 2) % 24]);
  }
  return out.filter(([a, b]) => a >= 0 && a <= 24 && b >= 0 && b <= 24 && a !== b);
}

/** L'ora h (0-23) sta in una delle finestre? */
function dentro(finestre, h) {
  return finestre.some(([a, b]) => (a < b ? h >= a && h < b : h >= a || h < b));
}

/** Le note di tutti gli ODM di un kit (il campo odm dell'anagrafica: JSON dal ponte 0.9.0, testo prima). */
function noteOdm(odm) {
  try {
    const l = JSON.parse(odm || "[]");
    if (Array.isArray(l)) return l.map((x) => String(x.note || "")).join(" · ");
  } catch { /* testo dei ponti vecchi */ }
  return String(odm || "");
}

export { finestreAccese, dentro, noteOdm };
