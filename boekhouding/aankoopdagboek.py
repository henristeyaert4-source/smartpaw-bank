"""Aankoopdagboek per kwartaal: elke aankoop met leverancier, factuur, grootboekrekening, btw-code, maatstaf en btw,
en of Pro-count ze al in Yuki geboekt heeft.

Doel: de boekhouder hoeft niets meer in te typen. Wat al in Yuki staat (Peppol, Lucy, door Pro-count geboekt) krijgt
status "in Yuki" en dient enkel ter controle. Wat we zelf hebben (upload, mail, Meta-kwitantie) maar nog niet in Yuki
staat, krijgt "te boeken" met een volledig boekingsvoorstel. Zonder document: "factuur ontbreekt".

Grootboekrekening: eerst per leverancier (zoals Pro-count die leverancier in Yuki boekt), anders per platformcategorie
(rekeningen_koppeling.json). Btw-code: eigen code met roosters; de Yuki-btw-codes van Pro-count volgen nog.

Gebruik: python boekhouding/aankoopdagboek.py [JJJJ k ...]  → boekhouding/dagboek/aankoop_<JJJJ>Q<k>.json
Vereist: boekhouding/boek/<JJJJ>Q<k>.json (regels.py) en data/yuki/openstaand.json.
"""
import csv, json, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "boekhouding"

# Rekeningnamen uit het rekeningschema van Pro-count (MAR Smartpaw.csv)
SCHEMA = {}
with open(B / "rekeningschema_procount.csv", encoding="utf-8-sig") as f:
    for r in list(csv.reader(f, delimiter=";"))[1:]:
        if len(r) >= 5:
            SCHEMA[r[0]] = {"naam": r[1], "aftrek": r[4]}

# Per leverancier, afgeleid uit hoe Pro-count ze in Yuki boekte (omschrijving "Factuur van X, <rekening>") jul–okt 2026.
LEVERANCIER = [
    (r"METAPAY|META VERIFIED", "611080", "Meta Verified = abonnement"),
    (r"FACEBK|META ?PLATFORMS", "616502", "Yuki: Meta = RECLAME MET MERK"),
    (r"GOOGLE", "616501", "Yuki: Google = RECLAME ZONDER MERK"),
    (r"ADVANCE ?MEDIA", "616502", "Yuki: Advance Media = RECLAME MET MERK"),
    (r"FINDAJOB", "617000", "Yuki: Findajob = Uitzendkrachten"),
    (r"WIDEM", "612730", "Yuki: Widem = TRANSPORTEN AAN DERDEN"),
    (r"BPOST", "611030", "Yuki: bpost = PORTKOSTEN"),
    (r"BOL\.?COM", "615000", "Yuki: bol.com = Commissielonen"),
    (r"PRO.?COUNT", "615200", "Yuki: Pro-count = Erelonen boekhouders"),
    (r"YUKI", "611080", "Yuki: Yuki works = ABONNEMENTEN"),
    (r"HIGGSFIELD|AMAZON|SHOPIFY(?! HARDWARE)|KLAVIYO|HOLO|LOVABLE|APPSUMO|FIVERR|CANVA|RETURNGO|GODADDY", "611080",
     "Yuki: online abonnementen = ABONNEMENTEN"),
    (r"COMPASS|FURVAC|CHONGXIN|PET2026|PRODUCT70|ALIBABA|QIANYAN|^1618", "604000", "Yuki: fabriek = Aankopen van handelsgoederen"),
    (r"ACTION|DRUKBEDRIJF|COOLBLUE|PRINTDEAL|SD WORKWEAR", "611200", "Yuki: Klein materiaal"),
    (r"HADDOK|NENUPHAR|SANTIBAL|YAKI|PATRON|BORZE|CHARLATAN", "616680", "Yuki: Restaurantkosten (btw niet aftrekbaar)"),
    (r"BOOKING|HOTEL", "616750", "reis- en verblijf buitenland"),
    (r"BELGIAN DOGGOS|THOMAS MORE|POM-OOSTV|PEVA|GS1", "616651", "Yuki: Beroepsbijdragen"),
    (r"AMBULANTE", "616620", "standgeld markt = Beurzen en tentoonstellingen"),
    (r"PACKAGINGDISCOUNTER|SUPPY", "601000", "verpakking = Aankopen van hulpstoffen"),
    (r"KBC VERZEKERING", "613210", "BA-polis KBC"),
    (r"ALMOST 3000", "615300", "Yuki: Almost 3000 = Overige erelonen"),
    (r"PROXIMUS", "657000", "Yuki: Proximus = Diverse financiële kosten"),
]

# Per platformcategorie (val terug als geen leveranciersregel past). Aanpassingen t.o.v. rekeningen_koppeling.json
# volgen Pro-count's eigen boekingen in Yuki.
CATEGORIE_CORRECTIE = {
    "Personeel (student)": "617000",          # Findajob = Uitzendkrachten (geen loon)
    "Software & abonnementen": "611080",      # ABONNEMENTEN
    "Representatie & reizen": "616680",       # meestal restaurant; hotel/reizen via leveranciersregel
    "Marketing & content": "616502",
}

# Btw-keuze zoals in Yuki (Shany, 29/10: geen codes, je kiest per factuur): 21%, verlegd, invoer met/zonder verlegging,
# intracommunautair goederen/diensten. Verlegd uit de EU = intracommunautair; abonnement = diensten. Restaurant altijd 0% aftrek.
BTW = {
    "BE21":   {"code": "BE21",   "uitleg": "Yuki: 21%", "roosters": "82 · 59"},
    "BE21NA": {"code": "BE21NA", "uitleg": "Yuki: 0% aftrek (restaurant)", "roosters": "82"},
    "EU":     {"code": "EUDV",   "uitleg": "Yuki: intracommunautair diensten (verlegd)", "roosters": "88 · 55 · 59"},
    "NONEU":  {"code": "NEUDV",  "uitleg": "Yuki: btw verlegd (dienst buiten EU)", "roosters": "87 · 56 · 59"},
    "INVOER": {"code": "INVOER", "uitleg": "Yuki: invoer met verlegging (art. 41, invoeraangifte Widem)", "roosters": "87 · 56 · 59 (op invoeraangifte)"},
    "EUG":    {"code": "EUG",    "uitleg": "Yuki: intracommunautair goederen, als de factuur btw verlegd vermeldt; anders buitenlandse btw, niet aftrekbaar", "roosters": "86 · 55 · 59"},
    "GEEN":   {"code": "GEEN",   "uitleg": "Yuki: geen btw / vrijgesteld", "roosters": "82"},
    "NAKIJKEN": {"code": "?",    "uitleg": "btw-behandeling nakijken", "roosters": "?"},
}

# Btw-type verfijnen waar de bankregel NAKIJKEN gaf
TYPE_LEVERANCIER = [
    (r"PACKAGING ?DISCOUNTER|DRUKBEDRIJF|SUPPY", "EUG"),
    (r"CHONGXIN|COMPASS|ALIBABA|PET2026|QIANYAN", "INVOER"),
]


def btw_type(r, bw):
    typ = r["btw_type"]
    if typ != "NAKIJKEN":
        return typ
    t = " ".join(str(x) for x in (r.get("tegenpartij"), bw.get("leverancier"), bw.get("label"))).upper()
    for pat, nieuw in TYPE_LEVERANCIER:
        if re.search(pat, t, re.I):
            return nieuw
    bt = str(bw.get("btw_type") or "").lower()
    if "invoer" in bt:
        return "INVOER"
    return typ


STOP = {"factuur", "van", "bvba", "limited", "ireland", "betaling", "inc", "nv", "bv", "belgium", "via", "mollie", "logistics"}


def _tok(s):
    return {w for w in re.findall(r"[a-z]{4,}", (s or "").lower()) if w not in STOP}


def _dagen(a, b):
    return (date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days


def rekening(r, bw):
    if re.search(r"proforma|\bPI[- ]|voorschot", str(bw.get("label", "")) + " " + str(bw.get("uitleg", "")), re.I):
        return "406000", "voorschot op proforma: Vooruitbetalingen tot de factuur er is"
    t = " ".join(str(x) for x in (r.get("tegenpartij"), r.get("mededeling"), bw.get("leverancier"), bw.get("label"))).upper()
    for pat, nr, bron in LEVERANCIER:
        if re.search(pat, t, re.I):
            return nr, bron
    nr = CATEGORIE_CORRECTIE.get(r["categorie"])
    if not nr:
        k = json.loads((B / "rekeningen_koppeling.json").read_text()).get(r["categorie"])
        nr = k["rekening"] if isinstance(k, dict) else None
    return nr, "volgens platformcategorie"


def tegenrekening(r):
    bron, rid = r["bron"], r["id"]
    if bron == "KBC":
        return "550000", "KBC zichtrekening"
    if bron == "Revolut":
        return ("550002", "Revolut USD") if "USD" in (r.get("mededeling") or "") + str(r.get("munt", "")) else ("550001", "Revolut EUR")
    if rid.startswith("kaart-2103"):
        return "434001", "Mastercard Kaydee (2103)"
    if rid.startswith("kaart-6682"):
        return "434000", "Mastercard Henri (6682)"
    return "", bron


def factuurnummer(bw):
    for veld in ("factuurnummer", "transactie_id"):
        if bw.get(veld):
            return str(bw[veld])
    m = re.search(r"([A-Z]{0,6}-?\d[\w\-/]{4,})", bw.get("label") or "")
    return m.group(1) if m else ""


def bedragen(typ, incl, bw):
    """→ (maatstaf, btw aftrekbaar, verlegde btw)"""
    if typ == "BE21":
        btw = bw["btw"] if bw.get("btw") is not None else round(incl * 21 / 121, 2)
        return round(incl - btw, 2), round(btw, 2), 0.0
    if typ in ("EU", "NONEU", "INVOER", "EUG"):
        return round(incl, 2), 0.0, round(incl * 0.21, 2)
    return round(incl, 2), 0.0, 0.0  # BE21NA (kost incl. btw), GEEN, NAKIJKEN


def main(kwartalen):
    yuki = json.loads((ROOT / "data/yuki/openstaand.json").read_text()) if (ROOT / "data/yuki/openstaand.json").exists() else {}
    yalle = yuki.get("leveranciers_boekingen", [])
    yfact = [e for e in yalle if e["bedrag"] < 0]  # facturen (credit 440000)
    yfact += [{"id": c["id"], "datum": c["datum"], "bedrag": -c["origineel"], "contact": c["contact"],
               "omschrijving": c["omschrijving"]} for c in yuki.get("crediteuren", []) if c.get("origineel")]
    yuki_van = yuki.get("leveranciers_van", "2026-07-01")
    gebruikt = set()
    (B / "dagboek").mkdir(exist_ok=True)
    for jaar, k in kwartalen:
        pad = B / "boek" / f"{jaar}Q{k}.json"
        if not pad.exists():
            print(f"{jaar}Q{k}: geen boek-bestand, eerst regels.py draaien"); continue
        boek = json.loads(pad.read_text())
        lijnen = []
        for r in sorted(boek["regels"], key=lambda x: (x["datum"], x["id"])):
            if r["status"] == "verklaard" or r["bedrag"] >= 0 or r["btw_type"] == "FIN":
                continue
            bw = r.get("bewijs") or {}
            incl = round(-r["bedrag"], 2)
            typ = btw_type(r, bw)
            nr, nr_bron = rekening(r, bw)
            teg_nr, teg_naam = tegenrekening(r)
            if nr == "406000":
                typ = "GEEN"  # voorschot: geen btw tot levering/factuur
            maatstaf, btw, verlegd = bedragen(typ, incl, bw)
            # Yuki-status
            yid = bw.get("yuki_id") if bw.get("soort") == "yuki" else None
            if not yid and r["datum"] >= yuki_van:
                best = None
                for e in yfact:
                    if e["id"] in gebruikt or abs(abs(e["bedrag"]) - incl) > 0.021:
                        continue
                    d = _dagen(r["datum"], e["datum"])
                    naam = _tok(r["tegenpartij"] + " " + r.get("mededeling", "") + " " + str(bw.get("leverancier", "")))
                    if -35 <= d <= 75 and (naam & _tok(e["contact"])) and (best is None or abs(d) < abs(_dagen(r["datum"], best["datum"]))):
                        best = e
                if not best and str(bw.get("datum") or r["datum"]) < yuki_van:
                    # factuur vóór de Yuki-ophaalperiode geboekt: de betaling ervan staat wel in Yuki (zelfde leverancier, bedrag, ±7 d)
                    for e in yalle:
                        if e["id"] not in gebruikt and e["bedrag"] > 0 and abs(e["bedrag"] - incl) <= 0.021 and abs(_dagen(r["datum"], e["datum"])) <= 7 \
                                and (_tok(r["tegenpartij"] + " " + str(bw.get("leverancier", ""))) & _tok(e["contact"])):
                            best = e; break
                if not best and r["categorie"] == "Voorraad (fabriek)":
                    # fabriek in USD: Pro-count boekt de betaling tegen de factuur aan hun eigen koers → ±2 %, ±7 dagen
                    for e in yalle:
                        if e["id"] not in gebruikt and abs(abs(e["bedrag"]) - incl) <= 0.02 * incl and abs(_dagen(r["datum"], e["datum"])) <= 7 \
                                and (_tok(r["tegenpartij"] + " " + str(bw.get("leverancier", ""))) & _tok(e["contact"])):
                            best = e; break
                if best:
                    yid = best["id"]
            if yid:
                gebruikt.add(yid)
                status = "in Yuki"
            elif r["status"] == "gekoppeld":
                status = "te boeken"
            else:
                status = "factuur ontbreekt"
            lijnen.append({
                "id": r["id"], "status": status, "yuki_id": yid,
                "factuurdatum": bw.get("datum") or r["datum"], "betaald_op": r["datum"],
                "leverancier": bw.get("leverancier") or r["tegenpartij"], "btw_nummer": bw.get("btw_nummer") or "",
                "factuurnummer": factuurnummer(bw), "document": bw.get("bestand") or bw.get("label") or "",
                "asset_id": bw.get("asset_id"), "omschrijving": (bw.get("uitleg") or r.get("mededeling") or "")[:120],
                "rekening": nr, "rekening_naam": SCHEMA.get(nr, {}).get("naam", "?"), "rekening_bron": nr_bron,
                "btw_code": BTW[typ]["code"], "btw_uitleg": BTW[typ]["uitleg"], "roosters": BTW[typ]["roosters"],
                "incl": incl, "maatstaf": maatstaf, "btw": btw, "verlegde_btw": verlegd,
                "betaald_via": teg_nr, "betaald_via_naam": teg_naam,
                "nakijken": typ in ("NAKIJKEN", "EUG") or not nr,
            })
        # Facturen die al in Yuki staan maar nog niet betaald zijn (geen bankverrichting): ook in het dagboek
        AUTO = r"BOL\.?COM|META|FACEBOOK|GOOGLE|SHOPIFY|KLAVIYO|HIGGSFIELD|CANVA|AMAZON|APPSUMO|RETURNGO|MANYCHAT|KBC BANK|YUKI"
        BTW_LEV = [(r"DOGGOS", "GEEN"), (r"THOMAS MORE", "NAKIJKEN")]
        bank = json.loads((ROOT / "data/gecategoriseerd.json").read_text())
        al_betaald = set()
        def ogm(contact, ref):
            d = re.sub(r"\D", "", ref or "")
            base = None
            if re.search("WIDEM", contact, re.I) and len(d) == 8: base = "00" + d
            elif re.search("FINDAJOB", contact, re.I) and len(d) == 9: base = "001" + d[2:]
            elif re.search("BPOST", contact, re.I) and len(d) == 9: base = "0" + d
            elif re.search("THOMAS MORE", contact, re.I) and len(d) == 8: base = "22" + d
            elif re.search("PRO.?COUNT", contact, re.I) and d == "270345": return "260100345155"
            if not base: return None
            return base + f"{(int(base) % 97) or 97:02d}"
        handmatig = json.loads((B / "yuki_betaald.json").read_text()) if (B / "yuki_betaald.json").exists() else {}
        def betaald(c):
            if c.get("referentie") in handmatig:
                return True
            o = ogm(c["contact"], c.get("referentie"))
            for r in bank:
                if r["id"] in al_betaald or r["bedrag_eur"] >= 0 or abs(-r["bedrag_eur"] - c["open"]) > 0.051 or _dagen(r["datum"], c["datum"]) < -3:
                    continue
                med = re.sub(r"\D", "", r.get("mededeling") or "")
                if o and len(med) == 12 and med != o:
                    continue  # andere factuur van dezelfde leverancier
                if o and med == o or (_tok(c["contact"]) & _tok(r.get("tegenpartij", ""))) or not (r.get("tegenpartij") or "").strip():
                    al_betaald.add(r["id"]); return True
            return False
        for c in sorted(yuki.get("crediteuren", []), key=lambda c: c["datum"]):
            if not (boek["van"] <= c["datum"] <= boek["tot"]) or (c.get("open") or 0) <= 0 or re.search(AUTO, c["contact"], re.I):
                continue
            if betaald(c):
                continue  # in Yuki nog open, maar op de bank al betaald: hoort bij een bankverrichting hierboven
            typ = next((t for pat, t in BTW_LEV if re.search(pat, c["contact"], re.I)), "BE21")
            nr, nr_bron = rekening({"tegenpartij": c["contact"], "mededeling": c.get("omschrijving", ""), "categorie": ""}, {})
            incl = round(c["open"], 2)
            maatstaf, btw, verlegd = bedragen(typ, incl, {})
            lijnen.append({
                "id": "yuki-" + c["id"], "status": "in Yuki", "yuki_id": c["id"], "factuurdatum": c["datum"], "betaald_op": "",
                "leverancier": c["contact"], "btw_nummer": "", "factuurnummer": c.get("referentie", ""), "document": "",
                "asset_id": None, "omschrijving": (c.get("omschrijving") or "")[:120],
                "rekening": nr, "rekening_naam": SCHEMA.get(nr, {}).get("naam", "?"), "rekening_bron": nr_bron,
                "btw_code": BTW[typ]["code"], "btw_uitleg": BTW[typ]["uitleg"], "roosters": BTW[typ]["roosters"],
                "incl": incl, "maatstaf": maatstaf, "btw": btw, "verlegde_btw": verlegd,
                "betaald_via": "", "betaald_via_naam": "nog te betalen" + (f" (vervalt {c['vervaldag']})" if c.get("vervaldag") else ""),
                "nakijken": typ == "NAKIJKEN" or not nr, "onbetaald": True,
            })
        tel = {s: sum(1 for l in lijnen if l["status"] == s) for s in ("in Yuki", "te boeken", "factuur ontbreekt")}
        som = {s: round(sum(l["incl"] for l in lijnen if l["status"] == s), 2) for s in tel}
        per_rek = {}
        for l in lijnen:
            p = per_rek.setdefault(l["rekening"], {"rekening": l["rekening"], "naam": l["rekening_naam"], "aantal": 0, "maatstaf": 0.0, "btw": 0.0})
            p["aantal"] += 1; p["maatstaf"] = round(p["maatstaf"] + l["maatstaf"], 2); p["btw"] = round(p["btw"] + l["btw"], 2)
        doc = {"kwartaal": f"{jaar}Q{k}", "van": boek["van"], "tot": boek["tot"], "telling": tel, "bedrag": som,
               "per_rekening": sorted(per_rek.values(), key=lambda p: -p["maatstaf"]),
               "lijnen": list(reversed(lijnen)), "yuki_opgehaald": yuki.get("opgehaald"),
               "uitleg": "Elke aankoop met boekingsvoorstel. 'In Yuki' = Pro-count heeft ze al (enkel controle). "
                         "'Te boeken' = wij hebben het document, Yuki nog niet. Grootboekrekeningen volgen Pro-count's eigen boekingen; "
                         "btw-codes zijn eigen codes tot Pro-count hun Yuki-codes bezorgt.",
               "bijgewerkt": date.today().isoformat()}
        (B / "dagboek" / f"aankoop_{jaar}Q{k}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        print(f"{jaar}Q{k}", tel, som)


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    if a:
        qs = list(zip(a[0::2], a[1::2]))
    else:
        t = date.today(); q = (t.month - 1) // 3 + 1
        qs = [(t.year if q > 1 else t.year - 1, q - 1 if q > 1 else 4), (t.year, q)]
    main(qs)
