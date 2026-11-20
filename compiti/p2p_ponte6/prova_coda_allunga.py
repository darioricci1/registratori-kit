"""Prove a tavolino di coda_allunga.py e delle funzioni pure del ponte 0.19.0 per la coda (compito_mi_chiude,
durata_da, prossimo_giro_coda): quali richieste di Kit_Rifiuti si allungano in un giro, in che ordine, cosa si ricorda
di ognuna, e quando il ponte si chiude. Niente rete, niente DLL.
Uso: python3 prova_coda_allunga.py
version: 0.4.0 (20/11/2026): subito (coda_allunga 0.4.0, ponte 0.26.0): nuove, minuti_da, l'attesa nel registro,
prossima_occhiata, l'occhiata e il giro che parte da lei col ponte vero, i lavori che cedono (fitti) e quelli che no.
0.3.0 (16/11/2026): la lista viene dal sito (dal_sito, fatti_per_sito): solo le clip chieste da Dario; il giro
intero col sito finto (niente coda.json, niente allunga_urgenti.json).
0.2.0 (16/11/2026): le urgenti (unisci, fuori dal tetto per kit), il riassunto, e le funzioni del ponte.
0.1.0 (12/11/2026)
"""
import ast
import datetime
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import coda_allunga as ca   # noqa: E402

fallite = []


def ok(cond, nome):
    print(("ok   " if cond else "NO   ") + nome)
    if not cond:
        fallite.append(nome)


OGGI = datetime.date(2026, 11, 12)
ADESSO = datetime.datetime(2026, 11, 12, 15, 0).timestamp()


def r(ev, kit=499, scade="2026-12-01", giorno="2026-11-10"):
    return {"evento": ev, "kit": kit, "giorno": giorno, "ora_inizio_clip": "18:44:51", "durata_clip": 32.0,
            "canali": [0, 1], "prima_s": 60, "dopo_s": 120, "scade_il": scade, "e": {"nome": "no targa 184451"},
            "da_pc": "PC-A", "chiesto_il": "2026-11-12 10:00", "motivi": ["fonte incompleta"]}


# ------------------------------------------------------------------ da_fare, per_ponte, segna (0.1.0)
coda = [r("a"), r("b"), r("c", kit=1), r("d", scade="2026-11-11"), {"evento": "e"}, r("a")]
s = ca.da_fare(coda, {}, ADESSO, OGGI)
ok([x["evento"] for x in s] == ["a", "b", "c"], "nell'ordine della coda; scadute, senza ora e doppioni fuori")
s = ca.da_fare(coda, {}, ADESSO, OGGI, per_giro=2)
ok([x["evento"] for x in s] == ["a", "b"], "al massimo per_giro eventi")
reg = {"z1": {"kit": 499, "giorno_lavoro": "2026-11-12"}, "z2": {"kit": 499, "giorno_lavoro": "2026-11-12"}}
ok([x["evento"] for x in ca.da_fare(coda, reg, ADESSO, OGGI)] == ["a", "c"], "al massimo 3 per kit al giorno (2 gia' fatti oggi)")
reg = {"a": {"stato": "finito"}, "b": {"stato": "rinunciato"}, "c": {"stato": "da_riprovare", "ultimo": ADESSO - 600}}
ok(ca.da_fare(coda, reg, ADESSO, OGGI) == [], "finiti e rinunciati mai piu', da riprovare non prima di un'ora")
reg["c"]["ultimo"] = ADESSO - 3700
ok([x["evento"] for x in ca.da_fare(coda, reg, ADESSO, OGGI)] == ["c"], "dopo un'ora si riprova")
p = ca.per_ponte(dict(r("a"), urgente=True))
ok("e" not in p and "da_pc" not in p and "urgente" not in p and p["ora_inizio_clip"] == "18:44:51" and p["motivi"],
   "per il ponte senza i nomi")

reg = {}
ok(ca.segna(reg, {"evento": "a", "kit": 499, "esito": "fatto", "conti": {"mb": 120.5}}, ADESSO, OGGI) == "finito"
   and reg["a"]["mb"] == 120.5 and reg["a"]["giorno_lavoro"] == "2026-11-12", "fatto: finito, coi MB")
ok(ca.segna(reg, {"evento": "b", "esito": "non piu' sul registratore"}, ADESSO, OGGI) == "finito",
   "non piu' sul registratore: finito (non si riprova)")
ok(ca.segna(reg, {"evento": "p", "esito": "parziale"}, ADESSO, OGGI) == "finito", "parziale: finito")
st = [ca.segna(reg, {"evento": "c", "esito": "registratore non raggiunto: relay"}, ADESSO + i, OGGI) for i in range(3)]
ok(st == ["da_riprovare", "da_riprovare", "rinunciato"] and reg["c"]["tentativi"] == 3,
   "collegamento fallito: si riprova, alla terza si rinuncia")
ok(ca.segna(reg, {"evento": "m", "esito": "errore di memoria della libreria (0xC0000005) (a meta')"}, ADESSO, OGGI)
   == "da_riprovare", "processo caduto: si riprova")
ok(ca.segna(reg, {"evento": "s", "esito": "registratore sconosciuto: il kit non c'e'"}, ADESSO, OGGI) == "finito",
   "registratore sconosciuto: finito")

# ------------------------------------------------------------------ 0.2.0: le urgenti
urg = [{"evento": "u2", "kit": 7, "giorno": "2026-10-26", "ora_inizio_clip": "09:00:00"},
       {"evento": "u1", "kit": 7, "giorno": "2026-10-24", "ora_inizio_clip": "21:01:55"},
       {"evento": "b", "kit": 499, "giorno": "2026-11-10", "ora_inizio_clip": "10:00:00"},
       {"kit": 1}]
lista = ca.unisci(urg, [r("a"), r("b")])
ok([x["evento"] for x in lista] == ["u1", "u2", "b", "a"], "urgenti davanti, dalla piu' vicina alla scadenza; un doppione conta come urgente")
ok(lista[0]["scade_il"] == "2026-11-17" and lista[0]["urgente"] and not lista[3].get("urgente"),
   "scade_il delle urgenti dal giorno + 24; la coda resta com'e'")
ok(ca.scadenza({"giorno": "2026-10-24"}) == datetime.date(2026, 11, 17) and ca.scadenza({}) is None
   and ca.scadenza({"scade_il": "2026-11-20", "giorno": "2026-10-01"}) == datetime.date(2026, 11, 20), "scadenza")
reg = {"z1": {"kit": 7, "giorno_lavoro": "2026-11-12"}, "z2": {"kit": 7, "giorno_lavoro": "2026-11-12"},
       "z3": {"kit": 7, "giorno_lavoro": "2026-11-12"}}
cinque = ca.unisci([{"evento": f"k{i}", "kit": 7, "giorno": "2026-10-30", "ora_inizio_clip": f"1{i}:00:00"} for i in range(5)],
                   [r("n", kit=7)])
s = ca.da_fare(cinque, reg, ADESSO, OGGI)
ok([x["evento"] for x in s] == ["k0", "k1", "k2", "k3", "k4"], "le urgenti non hanno il tetto per kit, la coda si'")
reg2 = {f"k{i}": {"kit": 7, "giorno_lavoro": "2026-11-12", "urgente": True, "stato": "finito"} for i in range(5)}
ok([x["evento"] for x in ca.da_fare(cinque, reg2, ADESSO, OGGI)] == ["n"], "e le urgenti fatte non tolgono posto alla coda")
ok([x["evento"] for x in ca.da_fare(ca.unisci([{"evento": "v", "kit": 1, "giorno": "2026-10-01",
                                                "ora_inizio_clip": "10:00:00"}], []), {}, ADESSO, OGGI)] == [],
   "un'urgente gia' scaduta non si fa")
reg = {}
ca.segna(reg, {"evento": "u1", "kit": 7, "esito": "registratore non raggiunto"}, ADESSO, OGGI, urgente=True)
ca.segna(reg, {"evento": "u1", "kit": 7, "esito": "fatto"}, ADESSO + 4000, OGGI)
ok(reg["u1"].get("urgente") and reg["u1"]["stato"] == "finito", "l'urgente resta segnata come tale")
ria = ca.riassunto(reg, lista, OGGI)
ok(ria["stati"] == {"finito": 1} and ria["aperte"] == 3 and [u["stato"] for u in ria["urgenti"]] == ["finito", "da fare", "da fare"]
   and json.dumps(ria).find("no targa") < 0, "riassunto: stati, aperte, urgenti; niente nomi")

# ------------------------------------------------------------------ 0.3.0: dal sito, solo le clip chieste da Dario
sito = {"oggi": "2026-11-16", "eventi": [dict(r("s1"), chiesta_da="dario@alma", canali_stimati=True), dict(r("s2", kit=7)),
                                         {"evento": "s3", "kit": 7}, dict(r("s1")), "x"]}
ds = ca.dal_sito(sito)
ok([x["evento"] for x in ds] == ["s1", "s2"] and all(x["urgente"] for x in ds), "dal sito: complete, senza doppioni, tutte di Dario")
ok(ca.dal_sito(None) == [] and ca.dal_sito([1]) == [] and ca.dal_sito({"eventi": None}) == [], "dal sito: una risposta rotta e' vuota")
pp = ca.per_ponte(ds[0])
ok(not any(k in pp for k in ("chiesta_da", "canali_stimati", "e", "urgente")) and pp["canali"] == [0, 1],
   "per allunga.py senza chi l'ha chiesta e senza i nomi")
ok(ca.fatti_per_sito({"s1": {"stato": "finito", "esito": "fatto"}, "s2": {"stato": "da_riprovare"}, "zz": {"stato": "finito"}}, ds)
   == [{"evento": "s1", "esito": "fatto"}], "al sito tornano solo i chiusi della lista")

# ------------------------------------------------------------------ 0.4.0: subito
ok(ca.nuove(coda, {}, ADESSO, OGGI) == ["a", "b", "c"], "nuove: quello che un giro farebbe adesso")
many = [dict(r(f"m{i}"), urgente=True) for i in range(9)]   # quelle di Dario: fuori dal tetto per kit
ok(len(ca.nuove(many, {}, ADESSO, OGGI)) == 9 and len(ca.da_fare(many, {}, ADESSO, OGGI)) == 6, "nuove: senza il tetto per giro")
ok(ca.nuove(coda, {"a": {"stato": "finito"}, "b": {"stato": "rinunciato"},
                   "c": {"stato": "da_riprovare", "ultimo": ADESSO - 60}}, ADESSO, OGGI) == [],
   "nuove: niente se tutto e' finito o aspetta di riprovare")
t_utc = datetime.datetime(2026, 11, 12, 13, 30, tzinfo=datetime.timezone.utc).timestamp()
ok(ca.minuti_da("2026-11-12T13:00:00.000Z", t_utc) == 30.0, "minuti_da: l'ora del sito in UTC")
loc = datetime.datetime(2026, 11, 12, 10, 0).timestamp()
ok(ca.minuti_da("2026-11-12 09:15:00", loc) == 45.0, "minuti_da: un'ora senza fuso e' locale")
ok(ca.minuti_da(None, ADESSO) is None and ca.minuti_da("ieri", ADESSO) is None and ca.minuti_da("2026-11-12T16:00:00Z", t_utc) == 0.0,
   "minuti_da: niente, illeggibile o nel futuro")
reg = {}
ca.segna(reg, {"evento": "w", "esito": "registratore non raggiunto"}, ADESSO, OGGI, attesa_min=3.5)
ca.segna(reg, {"evento": "w", "esito": "fatto"}, ADESSO + 4000, OGGI, attesa_min=70.0)
ok(reg["w"]["attesa_min"] == 3.5 and reg["w"]["stato"] == "finito", "l'attesa e' quella della prima partenza")
ca.segna(reg, {"evento": "y", "esito": "fatto"}, ADESSO, OGGI)
ok("attesa_min" not in reg["y"], "senza chiesta_il niente attesa")
ca.segna(reg, {"evento": "z", "esito": "fatto"}, ADESSO, OGGI, attesa_min=12.0)
ok(ca.riassunto(reg, [], OGGI)["attesa_min"] == {"quanti": 2, "mediana": 12.0, "massima": 12.0}, "l'attesa nel riassunto")

# ------------------------------------------------------------------ 0.2.0: la diagnosi dei risultati gia' sul disco
dg = ca.diagnosi([{"cartella": "p2p_ponte30", "evento": "a", "esito": "fatto"},
                  {"cartella": "p2p_ponte30", "evento": "b", "esito": "non piu' sul registratore"},
                  {"cartella": "p2p_ponte30", "evento": "c", "esito": "parziale: 2 canali"},
                  {"cartella": "coda", "evento": "d", "esito": "fatto"}],
                 {"a": {"azione": "montato"}, "b": {"azione": "chiudi", "esito": "non piu'"}, "d": {"azione": "aspetta", "tentativi": 3}},
                 {"z": {"stato": "aperta"}, "y": {"stato": "chiusa"}, "x": {}})
ok(dg["per_azione"] == {"montato": 1, "chiudi": 1, "mai guardato": 1, "aspetta": 1} and dg["fatti_non_montati"] == ["c", "d"]
   and dg["richieste_di_questo_pc"] == {"aperta": 2, "chiusa": 1} and dg["risultati"][3]["tentativi"] == 3,
   "diagnosi: chi e' stato montato, chi mai guardato, chi aspetta")

# ------------------------------------------------------------------ 0.19.0: le funzioni pure del ponte
src = open(os.path.join(QUI, "compito.py"), encoding="utf-8").read()
g = {"DURATA": 24 * 3600}
for nodo in ast.parse(src).body:
    if isinstance(nodo, ast.FunctionDef) and nodo.name in ("compito_mi_chiude", "durata_da", "prossimo_giro_coda",
                                                            "prossima_occhiata"):
        exec(compile(ast.Module([nodo], []), "compito.py", "exec"), g)   # noqa: S102 - il nostro codice
ok(all(k in g for k in ("compito_mi_chiude", "durata_da", "prossimo_giro_coda")), "le tre funzioni ci sono")
chiude = g["compito_mi_chiude"]
ok(not chiude({"compito": "nas3", "pc": "2026-002"}, "p2p_ponte37", "COMPUTERONE"), "un compito per un altro PC non chiude il ponte")
ok(chiude({"compito": "nas3", "pc": "computerone"}, "p2p_ponte37", "COMPUTERONE"), "uno per questo PC si'")
ok(chiude({"compito": "x"}, "p2p_ponte37", "COMPUTERONE"), "uno senza pc si'")
ok(not chiude({"compito": "p2p_ponte37", "pc": "COMPUTERONE"}, "p2p_ponte37", "COMPUTERONE") and not chiude({}, "a", "B"),
   "se stesso o niente no")
du = g["durata_da"]
ok(du({"durata_ore": 72}) == 72 * 3600 and du({"durata_ore": 1000}) == 168 * 3600 and du({"durata_ore": 0}) == 3600
   and du({}) == 24 * 3600 and du({"durata_ore": "x"}) == 24 * 3600 and du(None) == 24 * 3600
   and du({"durata_ore": float("nan")}) == 24 * 3600, "durata da ponte.json, fra 1 e 168 ore")
pg = g["prossimo_giro_coda"]
ok(not pg(0, 100, 0, False) and pg(0, 3600, 0, False) and pg(0, 300, 3, False) and not pg(0, 299, 3, False)
   and not pg(0, 10 ** 6, 0, True), "il giro: ogni ora, ogni 5 minuti se c'e' lavoro, mai due insieme")
po = g["prossima_occhiata"]
ok(po(0, 120, False) and not po(0, 119, False) and not po(0, 10 ** 6, True), "l'occhiata: ogni 2 minuti, mai mentre gira il giro")

# ------------------------------------------------------------------ 0.19.0: un giro intero della coda, col ponte vero
# (le definizioni del ponte fino all'ascolto, come allunga_lavoro.py; lavoro_allunga finto che scrive i risultati dove li
# scrive quello vero: ~/kr_lavori/allunga/coda/<evento>/uscita/allunga_evento.json, che archivio_kit legge)
import shutil   # noqa: E402
import tempfile   # noqa: E402
tmp = tempfile.mkdtemp(prefix="prova_coda_allunga_")
casa, comp = os.path.join(tmp, "casa"), os.path.join(tmp, "p2p_ponte37")
os.makedirs(os.path.join(casa, "kr_lavori", "allunga"))
os.makedirs(comp)
oggi = datetime.date.today()
g_ = (oggi - datetime.timedelta(days=20)).isoformat()
# la coda automatica di Kit_Rifiuti e le urgenti del compito ci sono ancora sul disco: il ponte 0.20.0 non le legge
json.dump({"eventi": [dict(r("v1", kit=5, giorno=g_), scade_il=None)]}, open(os.path.join(casa, "kr_lavori", "allunga", "coda.json"), "w"))
json.dump({"eventi": [{"evento": "u9", "kit": 6, "giorno": (oggi - datetime.timedelta(days=23)).isoformat(),
                       "ora_inizio_clip": "21:01:55", "durata_clip": 92.2, "canali": [0, 1, 2], "prima_s": 120, "dopo_s": 180}]},
          open(os.path.join(comp, "allunga_urgenti.json"), "w"))
json.dump({"durata_ore": 48}, open(os.path.join(comp, "ponte.json"), "w"))
vecchi = (dict(os.environ), list(sys.argv))
os.environ.update(HOME=casa, USERPROFILE=casa, COMPUTERNAME="COMPUTERONE")
sys.argv[:] = ["compito.py", comp]
pre = src[:src.index("\nt_fine = time.time() + DURATA")]
gp = {"__name__": "ponte", "__file__": os.path.join(comp, "compito.py")}
exec(compile(pre, "compito.py", "exec"), gp)   # noqa: S102 - il nostro codice
ok(gp["DURATA"] == 48 * 3600, "ponte.json: il ponte vive 48 ore")
chiesti = []


def finto(cfg, base=None, nome_uscita="allunga.json"):
    out = {"eventi": []}
    for ev in cfg["eventi"]:
        chiesti.append(ev["evento"])
        d = os.path.join(base, ev["evento"], "uscita")
        os.makedirs(d, exist_ok=True)
        x = {"evento": ev["evento"], "kit": ev["kit"], "esito": "fatto" if ev["evento"] != "q2" else "registratore non raggiunto"}
        json.dump(x, open(os.path.join(d, "allunga_evento.json"), "w"))
        out["eventi"].append(x)
    return out


gp["lavoro_allunga"] = finto
mandati = []
sito_su = [True]


def sito_finto(op, dati=None):
    if not sito_su[0]:
        raise OSError("sito giu'")
    if dati is not None:
        mandati.append((op, dati))
        return {"ok": True}
    quando = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=7)).isoformat().replace("+00:00", "Z")
    return {"oggi": oggi.isoformat(), "eventi": [dict(r(e, kit=k, giorno=g_), scade_il=None, chiesta_da="dario@alma",
                                                      chiesta_il=quando) for e, k in (("u9", 6), ("q1", 5), ("q2", 5))]
            + [dict(r(e, kit=5, giorno=g_), scade_il=None, chiesta_il=quando) for e in extra]}


extra = []


gp["sito_kit"] = sito_finto
n = gp["giro_coda_allunga"]()
reg_v = json.load(open(os.path.join(casa, "kr_lavori", "allunga", "coda", "registro.json")))
ok(n == 3 and chiesti == ["u9", "q1", "q2"], f"un giro: solo le clip chieste da Dario, nell'ordine del sito ({chiesti})")
conf = json.load(open(os.path.join(casa, "kr_lavori", "allunga", "confermate.json")))
ok([x["evento"] for x in conf["eventi"]] == ["u9", "q1", "q2"], "la lista del sito scritta in confermate.json per Kit_Rifiuti")
ok(mandati == [("allungare", {"fatti": [{"evento": "u9", "esito": "fatto"}, {"evento": "q1", "esito": "fatto"}]})],
   f"al sito tornano le chiuse ({mandati})")
ok(reg_v["u9"]["stato"] == "finito" and reg_v["u9"].get("urgente") and reg_v["q2"]["stato"] == "da_riprovare",
   "il registro del ponte: finiti, urgenti, da riprovare")
ok(all(6.5 <= reg_v[e].get("attesa_min", -1) <= 9 for e in ("u9", "q1", "q2")), "0.26.0: nel registro da quanti minuti era chiesta")
ok(not gp["ALLUNGA_PRIMA"].is_set(), "0.26.0: finito il giro, i fitti non aspettano piu'")
stato = json.load(open(os.path.join(comp, "uscita", "allunga_coda_stato.json")))
ok(stato["stati"] == {"finito": 2, "da_riprovare": 1} and stato["urgenti"][0]["stato"] == "finito" and stato["al_sito"] == 2, "lo stato in uscita")
dgv = json.load(open(os.path.join(comp, "uscita", "allunga_diagnosi.json")))
ok(dgv["per_azione"] == {} and dgv["lavoro_trovato"] is False, "la diagnosi in uscita, prima dei risultati")
ok(os.path.exists(os.path.join(casa, "kr_lavori", "allunga", "coda", "u9", "uscita", "allunga_evento.json")),
   "il risultato dove lo cerca Kit_Rifiuti (risultati_allunga: */*/uscita/allunga_evento.json)")
chiesti.clear()
sito_su[0] = False
ok(gp["giro_coda_allunga"]() == 0 and chiesti == [], "subito dopo niente (q2 si riprova dopo un'ora), anche col sito giu' (l'ultima lista)")
dgv = json.load(open(os.path.join(comp, "uscita", "allunga_diagnosi.json")))
ok(dgv["per_azione"] == {"mai guardato": 3} and dgv["fatti_non_montati"] == ["q1", "u9"],
   "al giro dopo la diagnosi vede i risultati che Kit_Rifiuti non ha ancora guardato")
# 0.26.0: l'occhiata di ogni 2 minuti
ok(gp["occhiata_allunga"]() == [] and gp["OCCHIATE"]["sito_giu"] == 1, "occhiata col sito giu': niente, e si conta")
sito_su[0] = True
ok(gp["occhiata_allunga"]() == [], "occhiata: niente di nuovo (q2 aspetta l'ora per riprovare)")
extra.append("q3")
ok(gp["occhiata_allunga"]() == ["q3"] and gp["OCCHIATE"]["sito_giu"] == 0, "occhiata: Dario ha chiesto q3")
mandati.clear()
ok(gp["parti_coda_allunga"](solo_se_nuove=True), "l'occhiata fa partire il filo")
for t in gp["CODA_VIVA"]:
    t.join(60)
ok(chiesti == ["q3"], f"e il filo allunga subito q3 ({chiesti})")
chiesti.clear()
ok(gp["parti_coda_allunga"](solo_se_nuove=True), "un'altra occhiata")
for t in gp["CODA_VIVA"]:
    t.join(60)
ok(chiesti == [], "senza niente di nuovo il giro non parte")
import threading   # noqa: E402
fermo = threading.Event()
lav = threading.Thread(target=fermo.wait, name="fitti_fonte.json", daemon=True)
lav.start()
gp["MISURE_VIVE"].append(lav)
ok(gp["misure_in_corso"]() and not gp["lavori_che_tengono"](), "i fitti sono un lavoro che cede")
extra.append("q4")
ok(gp["parti_coda_allunga"](solo_se_nuove=True), "la coda parte anche mentre girano i fitti")
for t in gp["CODA_VIVA"]:
    t.join(60)
ok(chiesti == ["q4"], f"e allunga q4 ({chiesti})")
lav2 = threading.Thread(target=fermo.wait, name="scorta.json", daemon=True)
lav2.start()
gp["MISURE_VIVE"].append(lav2)
ok(gp["lavori_che_tengono"]() and not gp["parti_coda_allunga"](solo_se_nuove=True), "un lavoro che tiene la libreria la ferma")
fermo.set()
try:
    gp["AV"].close()
except Exception:   # noqa: BLE001
    pass
os.environ.clear()
os.environ.update(vecchi[0])
sys.argv[:] = vecchi[1]
shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{len(fallite)} prove fallite")
sys.exit(1 if fallite else 0)
