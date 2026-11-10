// prova-nvr-remoto/api/rms.js - version: 1.0.0 (10/11/2026)
// Passa le chiamate della pagina all'API di Teltonika RMS (il browser non puo' chiamarla direttamente).
// Il token RMS non sta qui: lo scrive chi usa la pagina e arriva in X-Rms-Token a ogni chiamata. Senza token la funzione
// non fa niente, quindi la pagina pubblica non apre i registratori a chi la trova.
// ?op=kit            i router con «KIT» nel nome (stato online/offline, ultima connessione)
// ?op=accessi&id=N   le configurazioni di accesso remoto di un router
// ?op=apri&id=N      apre una sessione RMS Connect sull'accesso N e aspetta il link (max ~25 s)
// ?op=crediti        crediti e risorse dell'azienda su RMS
const B = "https://rms.teltonika-networks.com";

async function rms(tok, percorso, corpo) {
  const r = await fetch(B + percorso, {
    method: corpo ? "POST" : "GET",
    headers: { Authorization: "Bearer " + tok, "Content-Type": "application/json" },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const t = await r.text();
  try { return JSON.parse(t); } catch { return { success: false, errors: [{ message: "HTTP " + r.status }] }; }
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  const tok = String(req.headers["x-rms-token"] || "").trim();
  if (!tok) return res.status(401).json({ errore: "Manca il token RMS." });
  const { op, id } = req.query;
  try {
    if (op === "kit") {
      const tutti = [];
      for (let off = 0; off < 2000; off += 100) {
        const d = await rms(tok, `/api/devices?limit=100&offset=${off}`);
        if (!d.success) return res.status(400).json({ errore: (d.errors || [{}])[0].message || "RMS non risponde" });
        tutti.push(...d.data);
        if (d.data.length < 100) break;
      }
      return res.json(tutti.filter((x) => /KIT/i.test(x.name || "")).map((x) => ({
        id: x.id, nome: x.name, modello: x.model, online: x.status === 1, ultima: x.last_connection_at || "",
        segnale: x.signal ?? null, credito_fino: x.credit_expire_date || "",
      })));
    }
    if (op === "accessi") {
      const d = await rms(tok, `/api/devices/remote-access?device_id=${encodeURIComponent(id)}`);
      return res.json((d.data || []).filter((x) => x.destination_ip).map((x) => ({ id: x.id, nome: x.name, ip: x.destination_ip, porta: x.destination_port, protocollo: x.protocol })));
    }
    if (op === "apri") {
      const d = await rms(tok, `/api/devices/connect/${encodeURIComponent(id)}`, { duration: 900 });
      const ch = d.meta && d.meta.channel;
      if (!ch) return res.status(400).json({ errore: (d.errors || [{}])[0].message || "RMS non ha aperto la sessione" });
      for (let i = 0; i < 12; i++) {
        await new Promise((ok) => setTimeout(ok, 2000));
        const s = await rms(tok, `/status/channel/${ch}`);
        for (const lista of Object.values((s && s.data) || {})) {
          const u = lista[lista.length - 1] || {};
          if (u.status === "completed" && u.link) return res.json({ link: u.link });
          if (u.status === "error" || u.status === "warning") return res.json({ errore: u.value || "errore", codice: u.errorCode || null });
        }
      }
      return res.json({ errore: "RMS non ha risposto in 25 secondi" });
    }
    if (op === "crediti") {
      const d = await rms(tok, "/api/credits");
      return res.json((d.data || []).map((c) => ({ nome: c.credit_name, quanti: c.credit_count, rimasti: c.credit_left, dal: c.assigned_at })));
    }
    return res.status(400).json({ errore: "op sconosciuta" });
  } catch (e) {
    return res.status(500).json({ errore: String(e.message || e) });
  }
}
