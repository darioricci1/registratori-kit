// registratori-kit/public/xlsx.js - version: 1.0.0 (10/11/2026)
// Un vero file Excel (.xlsx) fatto nella pagina, senza librerie esterne (Dario: «un vero xlsx invece che un csv»).
// Un .xlsx e' uno zip di file XML: lo zip «stored» col CRC32 e' quello di kit-rifiuti-web/public/pacchetto.js.
// XLSX.scarica(nomeFile, [{ nome, intestazione: [...], righe: [[...]], larghezze: [...] }])
const XLSX = (() => {
  const TAB = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  const crc32 = (b) => { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = TAB[(c ^ b[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  function zip(files) {
    const enc = new TextEncoder(), parti = [], centrale = []; let pos = 0;
    for (const f of files) {
      const nome = enc.encode(f.nome), d = typeof f.dati === "string" ? enc.encode(f.dati) : f.dati, crc = crc32(d);
      const h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint32(14, crc, true);
      h.setUint32(18, d.length, true); h.setUint32(22, d.length, true); h.setUint16(26, nome.length, true);
      parti.push(new Uint8Array(h.buffer), nome, d);
      const c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
      c.setUint32(16, crc, true); c.setUint32(20, d.length, true); c.setUint32(24, d.length, true); c.setUint16(28, nome.length, true);
      c.setUint32(42, pos, true);
      centrale.push(new Uint8Array(c.buffer), nome);
      pos += 30 + nome.length + d.length;
    }
    const dim = centrale.reduce((a, b) => a + b.length, 0), fine = new DataView(new ArrayBuffer(22));
    fine.setUint32(0, 0x06054b50, true); fine.setUint16(8, files.length, true); fine.setUint16(10, files.length, true);
    fine.setUint32(12, dim, true); fine.setUint32(16, pos, true);
    return new Blob([...parti, ...centrale, new Uint8Array(fine.buffer)], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  }
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "");
  const col = (i) => { let s = ""; i++; while (i) { const m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; };
  function foglio(f) {
    const righe = [f.intestazione, ...f.righe];
    const xmlRighe = righe.map((r, ri) => `<row r="${ri + 1}">` + r.map((v, ci) => {
      const ref = col(ci) + (ri + 1), st = ri === 0 ? ' s="1"' : "";
      if (typeof v === "number" && Number.isFinite(v)) return `<c r="${ref}"${st}><v>${v}</v></c>`;
      if (v == null || v === "") return ri === 0 ? `<c r="${ref}"${st}/>` : "";
      return `<c r="${ref}" t="inlineStr"${st}><is><t xml:space="preserve">${esc(v)}</t></is></c>`;
    }).join("") + "</row>").join("");
    const nCol = Math.max(1, ...righe.map((r) => r.length));
    const larg = (f.larghezze || []).map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join("");
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
      `<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>` +
      (larg ? `<cols>${larg}</cols>` : "") + `<sheetData>${xmlRighe}</sheetData>` +
      `<autoFilter ref="A1:${col(nCol - 1)}${righe.length}"/></worksheet>`;
  }
  function crea(fogli) {
    const nomi = fogli.map((f, i) => esc(String(f.nome || `Foglio${i + 1}`).replace(/[\\/?*[\]:]/g, " ").slice(0, 31)));
    const files = [
      { nome: "[Content_Types].xml", dati: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>${fogli.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("")}</Types>` },
      { nome: "_rels/.rels", dati: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>` },
      { nome: "xl/workbook.xml", dati: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${nomi.map((n, i) => `<sheet name="${n}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join("")}</sheets></workbook>` },
      { nome: "xl/_rels/workbook.xml.rels", dati: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${fogli.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join("")}<Relationship Id="rId${fogli.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>` },
      { nome: "xl/styles.xml", dati: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2457C5"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf/><xf fontId="1" fillId="2" applyFont="1" applyFill="1"><alignment wrapText="1" vertical="bottom"/></xf></cellXfs></styleSheet>` },
      ...fogli.map((f, i) => ({ nome: `xl/worksheets/sheet${i + 1}.xml`, dati: foglio(f) })),
    ];
    return zip(files);
  }
  function scarica(nomeFile, fogli) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(crea(fogli)); a.download = nomeFile.endsWith(".xlsx") ? nomeFile : nomeFile + ".xlsx";
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 60000);
  }
  return { crea, scarica, zip, crc32 };
})();
if (typeof module !== "undefined") module.exports = XLSX;
