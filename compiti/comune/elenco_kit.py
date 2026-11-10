"""Lo stato dei registratori dentro «Elenco KIT Date Registrazioni» (Dario, 10/11/2026: «unisci queste info a Elenco
KIT, almeno fogli anagrafica e odm»). Scrive SOLO colonne sue, in fondo, coi nomi che cominciano con «REG»: nelle righe
INSTALLATO dell'ANAGRAFICA KIT e nelle righe aperte (senza data di chiusura) dell'ODM. Le colonne che ci sono non si
toccano. Funzioni pure per i testi (provate qui sotto) e una funzione che scrive col Sheets API.
version: 1.0.1"""
import datetime
import re

FOGLIO = "1I3-xl5rlQu0xCUA9mj9c5BC_zR27Tioy0X6FRwXqKRw"
DAL = "2026-10-27"
COL_ANA = ["REG stato oggi", "REG telecamere che registrano", "REG media dal 27/10", "REG controllato il"]
COL_ODM = ["REG stato oggi", "REG controllato il"]


def _tratti(t):
    return [(int(a) * 60 + int(b), int(c) * 60 + int(e), ty) for a, b, c, e, ty in
            re.findall(r"(\d\d):(\d\d)-(\d\d):(\d\d) (\w+)", str(t or ""))]


def stato_kit(k, attese, archivio_kit):
    """(testo, registrano, media) di un kit dalla sua ultima prova del giro e dal suo archivio."""
    e = k.get("esito") or {}
    if k.get("stato") == "fallito":
        return "non risponde: " + (e.get("collegamento") or e.get("errore") or "?"), "", ""
    if k.get("stato") != "fatto":
        return "non ancora controllato", "", ""
    t = datetime.datetime.fromisoformat(k["finito_il"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=1)))
    ora = t.hour * 60 + t.minute
    reg, problemi = 0, []
    for c in e.get("canali") or []:
        tr = _tratti(c.get("registrato_oggi"))
        if tr:
            reg += 1
        if c["numero"] >= (attese or 3):
            continue
        if not tr:
            problemi.append("CH %02d niente oggi" % (c["numero"] + 1))
        else:
            # 1.0.1: il testo dei tratti arriva tagliato a 200 caratteri: l'ultimo minuto vero e' ultimo_minuto
            fine = max([b for _, b, _ in tr] + ([c["ultimo_minuto"]] if c.get("ultimo_minuto") is not None else []))
            if all(ty == "continua" for *_, ty in tr) and ora - fine > 30:
                problemi.append("CH %02d ferma dalle %02d:%02d" % ((c["numero"] + 1,) + divmod(fine, 60)))
    medie = []
    for a in archivio_kit:
        g = a.get("giorni") or {}
        v = [m for d, m in g.items() if d >= DAL and m is not None and d < t.strftime("%Y-%m-%d")] if isinstance(g, dict) else []
        if v:
            medie.append(100 * sum(v) / (1440 * len(v)))
    media = f"{round(sum(medie) / len(medie))}%" if medie else ""
    testo = (f"{reg} su {attese} registrano" if attese else f"{reg} registrano") + (": " + ", ".join(problemi) if problemi else "")
    return testo, reg, media


def scrivi(sessione, stato, log=print):
    """sessione: AuthorizedSession con lo scope drive (l'account di servizio di Alma). stato: la risposta di op=stato."""
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{FOGLIO}"
    ana = {a["kit"]: a for a in stato.get("anagrafica") or []}
    arc = {}
    for a in stato.get("archivio") or []:
        arc.setdefault(a["uid"], []).append(a)
    per_kit = {}
    for k in stato.get("kit") or []:
        if "NON INSTALLATI" in (k.get("gruppo") or "").upper():
            continue
        try:
            n = int(k["kit"])
        except (TypeError, ValueError):
            continue
        if n not in per_kit or (k.get("finito_il") or "") > (per_kit[n].get("finito_il") or ""):
            per_kit[n] = k
    quando = lambda k: (datetime.datetime.fromisoformat(k["finito_il"].replace("Z", "+00:00")).astimezone(
        datetime.timezone(datetime.timedelta(hours=1))).strftime("%d/%m/%Y %H:%M") if k.get("finito_il") else "")
    meta = sessione.get(base, params={"fields": "sheets(properties(title,sheetId,gridProperties(columnCount)))"}).json()
    props = {s["properties"]["title"]: s["properties"] for s in meta["sheets"]}
    for titolo, col_kit, filtro, nomi in (("ANAGRAFICA KIT", 3, lambda r: len(r) > 1 and r[1].strip() == "INSTALLATO", COL_ANA),
                                          ("ODM", 2, lambda r: not (len(r) > 14 and r[14].strip()), COL_ODM)):
        righe = sessione.get(f"{base}/values/{titolo}!A1:ZZ4000").json().get("values", [])
        intest = righe[0] if righe else []
        # le colonne REG: quelle che ci sono gia', se no in fondo
        if nomi[0] in intest:
            primo = intest.index(nomi[0])
        else:
            primo = len(intest)
            serve = primo + len(nomi) - props[titolo]["gridProperties"]["columnCount"]
            if serve > 0:
                sessione.post(f"{base}:batchUpdate", json={"requests": [{"appendDimension": {
                    "sheetId": props[titolo]["sheetId"], "dimension": "COLUMNS", "length": serve}}]}).raise_for_status()
        valori = [nomi]
        for r in righe[1:]:
            n = r[col_kit].strip() if len(r) > col_kit else ""
            k = per_kit.get(int(n)) if n.isdigit() else None
            if not n.isdigit() or not filtro(r) or not k:
                valori.append([""] * len(nomi))
                continue
            a = ana.get(int(n)) or {}
            testo, reg, media = stato_kit(k, a.get("telecamere"), arc.get(k["uid"], []))
            valori.append([testo, reg, media, quando(k)] if titolo == "ANAGRAFICA KIT" else [testo, quando(k)])
        da, a_col = _col(primo), _col(primo + len(nomi) - 1)
        r = sessione.put(f"{base}/values/{titolo}!{da}1:{a_col}{len(valori)}", params={"valueInputOption": "RAW"},
                         json={"values": valori})
        r.raise_for_status()
        log(f"{titolo}: colonne {da}-{a_col}, {sum(1 for v in valori[1:] if v[0])} righe scritte")


def _col(i):
    s = ""
    i += 1
    while i:
        i, m = divmod(i - 1, 26)
        s = chr(65 + m) + s
    return s


if __name__ == "__main__":
    assert _col(0) == "A" and _col(27) == "AB" and _col(28) == "AC"
    k = {"stato": "fatto", "finito_il": "2026-11-10T13:00:00Z", "esito": {"canali": [
        {"numero": 0, "registrato_oggi": "00:00-13:59 continua"}, {"numero": 1, "registrato_oggi": ""},
        {"numero": 2, "registrato_oggi": "00:00-08:00 sensore"}, {"numero": 3, "registrato_oggi": ""}]}}
    print(stato_kit(k, 3, [{"giorni": {"2026-11-01": 1440, "2026-11-02": 720, "2026-10-01": 0}}]))
    assert stato_kit(k, 3, [{"giorni": {"2026-11-01": 1440, "2026-11-02": 720}}]) == ("2 su 3 registrano: CH 02 niente oggi", 2, "75%")
    print("prove passate")
