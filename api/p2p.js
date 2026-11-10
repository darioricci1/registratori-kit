// prova-nvr-remoto/api/p2p.js - version: 1.7.0 (10/11/2026)
// 1.7.0: un registratore che UVMS ha due volte (stesso UID, due nomi) resta due righe: la chiave e' (uid, nome).
// 1.6.2: op=stato da' anche quando e' stato letto l'archivio di ogni telecamera (letto_il).
// 1.6.1: anche l'account di servizio legge le viste della pagina (per l'Excel delle correzioni).
// 1.6.0: l'ANAGRAFICA KIT (foglio «Elenco KIT Date Registrazioni») accanto ai registratori, per trovare le cose che non
//        tornano: nvr_remoto.anagrafica, caricata dall'account di servizio (op=anagrafica, POST), letta con op=stato.
// 1.5.1: l'archivio di un registratore si rilegge una volta al giorno (le percentuali dei giorni cambiano).
// 1.5.0: (ponte 0.3.0) la foto di ogni telecamera a ogni giro con «si vede / nera / niente» (nvr_remoto.camera, l'ultima foto, e
//        nvr_remoto.camera_storia, una riga per giro), e l'archivio di ogni telecamera letto una volta (nvr_remoto.archivio:
//        prima e ultima registrazione, giorni con registrazioni). op=pc per l'account di servizio.
// 1.4.1: l'elenco delle prove singole mostra solo quelle chieste a mano (il giro sta nella pagina dello stato).
// 1.4.0: il giro parte da solo ogni ora (quando un PC chiede lavoro e l'ultimo giro e' di piu' di 55 minuti fa);
//        op=stato da' anche le ultime 24 ore: quante prove hanno risposto. Le prove piu' vecchie di 7 giorni si buttano.
// 1.3.0: il giro di tutti i registratori (op=accoda) e lo stato di ogni kit con l'ultima prova (op=stato); le prove
//        chieste a mano passano davanti al giro (priorita).
// 1.2.0: l'elenco dei registratori (kit, comune, UID, modello, canali) letto dal database di UVMS, per scegliere il kit
//        invece di copiare l'UID; lo carica l'account di servizio (op=registratori, POST). Niente password.
// 1.1.0: la pagina entra anche con l'accesso unico di Alma (Google dal gestionale), senza token RMS.
// La coda delle prove P2P: la pagina chiede «collegati al registratore con questo UID», il PC dell'ufficio (il compito
// p2p_ponte di Kit_Rifiuti, che ha la libreria Focus) prende la richiesta, si collega in P2P, e rimanda l'esito con
// un fotogramma. Su Vercel la libreria Focus non gira (e' una DLL Windows): per questo serve il PC.
// Chi chiede: la pagina, con la sessione dell'accesso unico di Alma oppure con un token RMS valido.
// Chi risponde: il PC, con il biglietto Google dell'account di servizio di Alma (aud DESTINATARIO).
// Le password dei registratori non passano da qui: le ha il PC.
// Neon, schema nvr_remoto.
import { neon } from "@neondatabase/serverless";
import { chiE } from "./_accesso.js";

const DESTINATARIO = "https://mappakit.alma/nvr-remoto";
const ACCOUNT = "account-di-servizio@almasicurezza-479911.iam.gserviceaccount.com";
const RE_UID = /^[A-Z0-9]{20}$/;
let pronto = null;

function db() {
  const url = process.env.ALMA_DATABASE_URL || process.env.ALMA_POSTGRES_URL;
  if (!url) throw new Error("database non collegato");
  return neon(url);
}

async function tabelle(sql) {
  if (!pronto) pronto = (async () => {
    await sql`create schema if not exists nvr_remoto`;
    await sql`create table if not exists nvr_remoto.richieste (
      id serial primary key, chiesto_il timestamptz default now(), kit text, uid text not null, canale int,
      stato text default 'in coda', pc text, preso_il timestamptz, finito_il timestamptz, esito jsonb, foto bytea)`;
    await sql`create table if not exists nvr_remoto.registratori (uid text primary key, gruppo text, nome text, kit text,
      modello text, canali int, firmware text, aggiornato_il timestamptz default now())`;
    await sql`alter table nvr_remoto.richieste add column if not exists priorita int default 1`;
    await sql`create index if not exists richieste_uid on nvr_remoto.richieste (uid, id desc)`;
    await sql`create table if not exists nvr_remoto.camera (uid text, canale int, il timestamptz, vista text, luce real,
      contrasto real, dalle text, foto bytea, primary key (uid, canale))`;
    await sql`create table if not exists nvr_remoto.camera_storia (uid text, canale int, il timestamptz default now(), vista text)`;
    await sql`create index if not exists camera_storia_uid on nvr_remoto.camera_storia (uid, il desc)`;
    await sql`create table if not exists nvr_remoto.archivio (uid text, canale int, primo text, ultimo text, giorni jsonb,
      letto_il timestamptz default now(), primary key (uid, canale))`;
    await sql`create table if not exists nvr_remoto.anagrafica (kit int primary key, stato text, indirizzo text, cloud text,
      cliente text, telecamere int, installato_il text, aggiornata_il timestamptz default now())`;
    await sql`alter table nvr_remoto.registratori drop constraint if exists registratori_pkey`;
    await sql`create unique index if not exists registratori_uid_nome on nvr_remoto.registratori (uid, nome)`;
    await sql`create table if not exists nvr_remoto.pc (nome text primary key, visto_il timestamptz, versione text)`;
  })().catch((e) => { pronto = null; throw e; });
  return pronto;
}

async function rmsValido(tok) {
  if (!tok) return false;
  try {
    const r = await fetch("https://rms.teltonika-networks.com/api/devices?limit=1", { headers: { Authorization: "Bearer " + tok } });
    return r.ok && (await r.json()).success === true;
  } catch { return false; }
}

async function pcValido(req) {
  const h = String(req.headers.authorization || "");
  if (!h.startsWith("Bearer ")) return false;
  try {
    const r = await fetch("https://oauth2.googleapis.com/tokeninfo?id_token=" + encodeURIComponent(h.slice(7).trim()));
    if (!r.ok) return false;
    const d = await r.json();
    return d.aud === DESTINATARIO && String(d.email || "").toLowerCase() === ACCOUNT && String(d.email_verified) === "true";
  } catch { return false; }
}

async function corpo(req) {
  if (req.body && typeof req.body === "object") return req.body;
  const parti = [];
  for await (const c of req) parti.push(c);
  try { return JSON.parse(Buffer.concat(parti).toString("utf8") || "{}"); } catch { return {}; }
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  const op = String(req.query.op || "");
  try {
    const sql = db();
    await tabelle(sql);
    // --- l'elenco da UVMS (account di servizio)
    if (op === "registratori" && req.method === "POST") {
      if (!(await pcValido(req))) return res.status(401).json({ errore: "biglietto mancante o sbagliato" });
      const righe = ((await corpo(req)).registratori || []).filter((r) => RE_UID.test(String(r.uid || "").toUpperCase()));
      await sql`delete from nvr_remoto.registratori`;
      for (let i = 0; i < righe.length; i += 100) {
        const pezzo = righe.slice(i, i + 100);
        await sql.query(`insert into nvr_remoto.registratori (uid, gruppo, nome, kit, modello, canali, firmware)
          select * from unnest($1::text[], $2::text[], $3::text[], $4::text[], $5::text[], $6::int[], $7::text[]) on conflict (uid, nome) do nothing`,
          [pezzo.map((r) => String(r.uid).toUpperCase()), pezzo.map((r) => r.gruppo || ""), pezzo.map((r) => r.nome || ""),
           pezzo.map((r) => r.kit || ""), pezzo.map((r) => r.modello || ""), pezzo.map((r) => Number(r.canali) || null), pezzo.map((r) => r.firmware || "")]);
      }
      return res.json({ ok: true, salvati: righe.length });
    }
    // --- il giro di tutti i registratori: dalla pagina (accesso Alma) o dall'account di servizio
    if (op === "accoda" && req.method === "POST") {
      if (!(await pcValido(req)) && !(await chiE(req))) return res.status(401).json({ errore: "non autorizzato" });
      const r = await sql`insert into nvr_remoto.richieste (kit, uid, priorita)
        select distinct on (g.uid) g.gruppo || ' · ' || g.nome, g.uid, 0 from nvr_remoto.registratori g
        where not exists (select 1 from nvr_remoto.richieste q where q.uid = g.uid and q.stato in ('in coda', 'in corso'))
        returning id`;
      return res.json({ accodati: r.length });
    }
    if (op === "anagrafica" && req.method === "POST") {
      if (!(await pcValido(req))) return res.status(401).json({ errore: "biglietto mancante o sbagliato" });
      const righe = ((await corpo(req)).righe || []).filter((r) => Number.isInteger(Number(r.kit)));
      if (righe.length < 50) return res.status(400).json({ errore: "troppe poche righe: non sostituisco l'anagrafica" });
      await sql`delete from nvr_remoto.anagrafica`;
      for (let i = 0; i < righe.length; i += 200) {
        const p = righe.slice(i, i + 200);
        await sql.query(`insert into nvr_remoto.anagrafica (kit, stato, indirizzo, cloud, cliente, telecamere, installato_il)
          select * from unnest($1::int[], $2::text[], $3::text[], $4::text[], $5::text[], $6::int[], $7::text[]) on conflict (kit) do nothing`,
          [p.map((r) => Number(r.kit)), p.map((r) => r.stato || ""), p.map((r) => r.indirizzo || ""), p.map((r) => r.cloud || ""),
           p.map((r) => r.cliente || ""), p.map((r) => Number(r.telecamere) || null), p.map((r) => r.installato_il || "")]);
      }
      return res.json({ ok: true, salvati: righe.length });
    }
    if (op === "pc") {
      if (!(await pcValido(req)) && !(await chiE(req))) return res.status(401).json({ errore: "non autorizzato" });
      const pc = await sql`select nome, visto_il, versione from nvr_remoto.pc order by visto_il desc`;
      const conti = await sql`select stato, priorita, count(*)::int as n from nvr_remoto.richieste group by 1, 2 order by 1, 2`;
      return res.json({ pc, conti });
    }
    // --- il PC
    if (op === "prendi" || op === "esito") {
      if (!(await pcValido(req))) return res.status(401).json({ errore: "biglietto del PC mancante o sbagliato" });
      const b = await corpo(req);
      const nome = String(b.pc || req.query.pc || "?").slice(0, 40);
      await sql`insert into nvr_remoto.pc (nome, visto_il, versione) values (${nome}, now(), ${String(b.versione || "").slice(0, 20)})
                on conflict (nome) do update set visto_il = now(), versione = excluded.versione`;
      if (op === "prendi") {
        // il giro di ogni ora: se nessun giro e' in coda e l'ultimo e' partito da piu' di 55 minuti
        const [g] = await sql`select (select count(*) from nvr_remoto.richieste where priorita = 0 and stato in ('in coda', 'in corso'))::int as aperti,
          coalesce(extract(epoch from now() - (select max(chiesto_il) from nvr_remoto.richieste where priorita = 0)), 1e9)::int as secondi`;
        if (g.aperti === 0 && g.secondi > 55 * 60) {
          await sql`insert into nvr_remoto.richieste (kit, uid, priorita) select distinct on (uid) gruppo || ' · ' || nome, uid, 0 from nvr_remoto.registratori order by uid, nome`;
          await sql`delete from nvr_remoto.richieste where chiesto_il < now() - interval '7 days'`;
        }
        // una richiesta presa da piu' di 5 minuti e mai finita torna in coda (il PC si e' spento a meta')
        await sql`update nvr_remoto.richieste set stato = 'in coda', pc = null where stato = 'in corso' and preso_il < now() - interval '5 minutes'`;
        // il ponte 0.1.0 scarica sempre 15 secondi: il giro lo lascia al 0.2.0 quando ce n'e' uno acceso
        const [nuovo] = await sql`select count(*)::int as n from nvr_remoto.pc where versione not like '%0.1.%' and visto_il > now() - interval '2 minutes'`;
        const minima = /0\.1\./.test(String(b.versione || "")) && nuovo.n > 0 ? 1 : 0;
        const r = await sql`update nvr_remoto.richieste set stato = 'in corso', pc = ${nome}, preso_il = now()
          where id = (select id from nvr_remoto.richieste where stato = 'in coda' and priorita >= ${minima} order by priorita desc, id limit 1 for update skip locked)
          returning id, kit, uid, canale, priorita`;
        if (r[0]) {
          const a = await sql`select count(*)::int as n, coalesce(min(letto_il) < now() - interval '24 hours', true) as vecchio
            from nvr_remoto.archivio where uid = ${r[0].uid}`;
          r[0].serve_archivio = a[0].n === 0 || a[0].vecchio;
        }
        return res.json({ richiesta: r[0] || null });
      }
      const id = Number(b.id);
      const [rq] = await sql`select uid from nvr_remoto.richieste where id = ${id}`;
      const es = b.esito || {};
      if (rq) {
        for (const c of (es.camere || []).slice(0, 16)) {
          const jpg = c.foto ? Buffer.from(String(c.foto), "base64") : null;
          if (jpg && jpg.length > 400e3) continue;
          await sql`insert into nvr_remoto.camera (uid, canale, il, vista, luce, contrasto, dalle, foto)
            values (${rq.uid}, ${Number(c.canale)}, now(), ${String(c.vista || "")}, ${c.luce ?? null}, ${c.contrasto ?? null}, ${String(c.dalle || "")}, ${jpg})
            on conflict (uid, canale) do update set il = now(), vista = excluded.vista, luce = excluded.luce, contrasto = excluded.contrasto,
              dalle = excluded.dalle, foto = coalesce(excluded.foto, nvr_remoto.camera.foto)`;
          await sql`insert into nvr_remoto.camera_storia (uid, canale, vista) values (${rq.uid}, ${Number(c.canale)}, ${String(c.vista || "")})`;
          delete c.foto;
        }
        for (const a of (es.archivio || []).slice(0, 16)) {
          await sql`insert into nvr_remoto.archivio (uid, canale, primo, ultimo, giorni) values (${rq.uid}, ${Number(a.canale)},
            ${String(a.primo || "")}, ${String(a.ultimo || "")}, ${JSON.stringify(a.giorni || {})}::jsonb)
            on conflict (uid, canale) do update set primo = excluded.primo, ultimo = excluded.ultimo, giorni = excluded.giorni, letto_il = now()`;
        }
        delete es.archivio;
      }
      const foto = b.foto ? Buffer.from(String(b.foto), "base64") : null;
      if (foto && foto.length > 3e6) return res.status(413).json({ errore: "foto troppo grande" });
      await sql`update nvr_remoto.richieste set stato = ${b.ok ? "fatto" : "fallito"}, finito_il = now(),
                esito = ${JSON.stringify(es)}::jsonb, foto = ${foto} where id = ${id}`;
      await sql`delete from nvr_remoto.camera_storia where il < now() - interval '7 days'`;
      return res.json({ ok: true });
    }
    // --- la pagina
    if (op === "chi") return res.json({ email: await chiE(req) });
    if (!(await chiE(req)) && !(await pcValido(req)) && !(await rmsValido(String(req.headers["x-rms-token"] || "").trim())))
      return res.status(401).json({ errore: "Entra con Google (bottone «Entra con Alma») o scrivi un token RMS valido.", entra: true });
    if (op === "chiedi" && req.method === "POST") {
      const b = await corpo(req);
      const uid = String(b.uid || "").trim().toUpperCase();
      if (!RE_UID.test(uid)) return res.status(400).json({ errore: "L'UID P2P sono 20 lettere e numeri (lo mostra il registratore in Rete, P2P)." });
      const can = Number(b.canale) >= 1 && Number(b.canale) <= 16 ? Number(b.canale) : null;
      const r = await sql`insert into nvr_remoto.richieste (kit, uid, canale, priorita) values (${String(b.kit || "").slice(0, 80)}, ${uid}, ${can}, ${b.priorita === 0 ? 0 : 1}) returning id`;
      return res.json({ id: r[0].id });
    }
    if (op === "stato") {
      const righe = await sql`select g.uid, g.gruppo, g.nome, g.kit, g.modello, g.canali as canali_uvms,
          u.id, u.stato, u.finito_il, u.esito, u.foto is not null as ha_foto,
          (select count(*) from nvr_remoto.richieste q where q.uid = g.uid and q.stato in ('in coda', 'in corso'))::int as in_coda,
          (select count(*) from nvr_remoto.richieste q where q.uid = g.uid and q.stato in ('fatto', 'fallito') and q.finito_il > now() - interval '24 hours')::int as prove_24h,
          (select count(*) from nvr_remoto.richieste q where q.uid = g.uid and q.stato = 'fatto' and q.finito_il > now() - interval '24 hours')::int as risposte_24h
        from nvr_remoto.registratori g
        left join lateral (select id, stato, finito_il, esito, foto from nvr_remoto.richieste r
          where r.uid = g.uid and r.stato in ('fatto', 'fallito') order by r.id desc limit 1) u on true
        order by g.gruppo, g.nome`;
      const coda = await sql`select count(*)::int as n from nvr_remoto.richieste where stato in ('in coda', 'in corso')`;
      const cam = await sql`select c.uid, c.canale, c.il, c.vista, c.luce, c.contrasto, c.dalle, c.foto is not null as ha_foto,
          (select count(*) from nvr_remoto.camera_storia s where s.uid = c.uid and s.canale = c.canale and s.il > now() - interval '24 hours')::int as giri_24h,
          (select count(*) from nvr_remoto.camera_storia s where s.uid = c.uid and s.canale = c.canale and s.il > now() - interval '24 hours' and s.vista = 'si vede')::int as viste_24h
        from nvr_remoto.camera c`;
      const arc = await sql`select uid, canale, primo, ultimo, giorni, letto_il from nvr_remoto.archivio`;
      const ana = await sql`select kit, stato, indirizzo, cloud, cliente, telecamere, installato_il, aggiornata_il from nvr_remoto.anagrafica`;
      return res.json({ ora: new Date().toISOString(), coda: coda[0].n, kit: righe, camere: cam, archivio: arc, anagrafica: ana });
    }
    if (op === "registratori") {
      return res.json(await sql`select uid, gruppo, nome, kit, modello, canali, firmware from nvr_remoto.registratori order by gruppo, nome`);
    }
    if (op === "elenco") {
      const righe = await sql`select id, chiesto_il, kit, uid, canale, stato, pc, preso_il, finito_il, esito, foto is not null as ha_foto
        from nvr_remoto.richieste where priorita >= 1 order by id desc limit 30`;
      const pc = await sql`select nome, visto_il, versione, extract(epoch from now() - visto_il)::int as secondi from nvr_remoto.pc order by visto_il desc`;
      return res.json({ richieste: righe, pc });
    }
    if (op === "fotocam") {
      const r = await sql`select foto from nvr_remoto.camera where uid = ${String(req.query.uid || "")} and canale = ${Number(req.query.canale)}`;
      if (!r[0] || !r[0].foto) return res.status(404).json({ errore: "niente foto" });
      res.setHeader("Content-Type", "image/jpeg");
      return res.send(Buffer.from(r[0].foto));
    }
    if (op === "foto") {
      const r = await sql`select foto from nvr_remoto.richieste where id = ${Number(req.query.id)}`;
      if (!r[0] || !r[0].foto) return res.status(404).json({ errore: "niente foto" });
      res.setHeader("Content-Type", "image/jpeg");
      return res.send(Buffer.from(r[0].foto));
    }
    return res.status(400).json({ errore: "op sconosciuta" });
  } catch (e) {
    return res.status(500).json({ errore: String(e.message || e).slice(0, 300) });
  }
}
