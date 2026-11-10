// prova-nvr-remoto/api/_accesso.js - version: 1.0.0 (10/11/2026)
// L'accesso unico di Alma, come in acquisti (api/_accesso_unico.js): si entra col proprio Google dal gestionale, che
// rimanda qui con un biglietto usa e getta; il biglietto si riscatta nel database comune e nasce una sessione (cookie
// con un numero casuale). Si accende con ALMA_PORTA (l'indirizzo del gestionale) e funziona solo se il gestionale ha
// questo sito nell'elenco (Sincronizzazioni, Accesso unico): quello si aggiunge a mano.
import { neon } from "@neondatabase/serverless";
import { randomBytes } from "node:crypto";

const NOME = "alma_nvr";
const GIORNI = 14;
let sqlInUso = null;
const sql = (t, p = []) => {
  if (!sqlInUso) sqlInUso = neon(process.env.ALMA_DATABASE_URL || process.env.ALMA_POSTGRES_URL);
  return sqlInUso.query(t, p);
};
export const porta = () => {
  const p = String(process.env.ALMA_PORTA || "").trim().replace(/\/+$/, "");
  return /^https:\/\/[a-z0-9.-]+$/i.test(p) ? p : "";
};
const host = (req) => String(req.headers["x-forwarded-host"] || req.headers.host || "").split(",")[0].trim().toLowerCase();
function dalCookie(c) {
  for (const pezzo of String(c || "").split(";")) {
    const i = pezzo.indexOf("=");
    if (i > 0 && pezzo.slice(0, i).trim() === NOME) return pezzo.slice(i + 1).trim() || null;
  }
  return null;
}

/** L'email di chi e' entrato, o null. */
export async function chiE(req) {
  const id = dalCookie(req.headers.cookie);
  if (!id || id.length < 20) return null;
  const r = await sql(`select s.email from accesso.sessione s join accesso.persona p on p.email = s.email
    where s.id = $1 and s.uscita_il is null and s.scade_il > now()`, [id]).catch(() => []);
  return r.length ? r[0].email : null;
}

/** /api/entra: va al gestionale, torna col biglietto, nasce la sessione, si torna alla pagina. */
export default async function entra(req, res) {
  const p = porta();
  if (!p) return res.status(503).send("Accesso unico non acceso (manca ALMA_PORTA).");
  if (await chiE(req)) { res.setHeader("Location", "/"); return res.status(302).end(); }
  const codice = String(req.query.alma_biglietto || "");
  if (codice) {
    const [chi] = await sql(`update accesso.biglietto b set usato_il = now() from accesso.persona p
      where b.codice = $1 and b.usato_il is null and b.scade_il > now() and b.verso = $2 and p.email = b.email
      returning b.email, coalesce(p.nome, b.nome) as nome`, [codice, host(req)]).catch(() => []);
    if (chi) {
      const nuovo = randomBytes(32).toString("base64url");
      await sql(`insert into accesso.sessione (id, email, nome, scade_il) values ($1, $2, $3, now() + make_interval(days => $4))`,
        [nuovo, chi.email, chi.nome, GIORNI]);
      res.setHeader("Set-Cookie", `${NOME}=${nuovo}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${GIORNI * 86400}`);
      res.setHeader("Location", "/");
      return res.status(302).end();
    }
    return res.status(403).send("Il biglietto non vale (scaduto, o il gestionale non ha questo sito nell'elenco dell'accesso unico).");
  }
  res.setHeader("Location", `${p}/entra?poi=${encodeURIComponent(`https://${host(req)}/api/entra`)}`);
  return res.status(302).end();
}
