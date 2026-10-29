"""Deelt alle bankverrichtingen (KBC, Revolut, KBC-kredietkaart) in en maakt een kasoverzicht per maand.

Uitvoer:
  data/kas-per-maand.json   {maanden:[{maand, categorie: bedrag, ...}], groepen, onbekend[], bijgewerkt}
  data/gecategoriseerd.json alle verrichtingen met categorie
Bedragen = kas, incl. btw (wat er echt op de rekening binnenkwam of vertrok).
Regels staan bovenaan: pas ze aan als een verrichting in "Te bekijken" belandt.
"""
import glob, json, re
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("data")

# (regex op tegenpartij + mededeling, categorie)  — eerste match wint
REGELS = [
    # interne bewegingen (tellen niet mee)
    (r"SMARTPAW VOF.*(REVOLUT|LT76 3250)|NAAR REVOLUTE BUSINESS|PAYMENT FROM SMARTPAW|AANKOOP GOEDEREN|PRODUCT AANKOOP LEVERANCIER|VOORSCHOT PRODUCTEN|EXCHANGED (TO|FROM)|RECOVER NEGATIVE BALANCE|INTERN NAAR REVOLUT", "Intern (KBC↔Revolut)"),
    (r"KBC-MASTERCARD BUSINESS ESSENTIAL AFREKENING", "Kredietkaart-afrekening"),
    (r"YUKI", "Software & abonnementen"),
    # inkomsten
    (r"STRIPE", "Omzet webshop (Shopify)"),
    (r"BOLCOM", "Omzet bol.com"),
    (r"PAYPAL \*SMARTPAW", "Terugbetalingen aan klanten"),
    (r"PAYPAL|MOLLIE PAYMENTS|SUMUP|AMAZON PAYMENTS|TO-BE BV", "Omzet overige kanalen"),
    (r"HOGESCHOOL GENT", "Overige ontvangsten"),
    # financiering
    (r"OPNEMING INVESTERINGSKREDIET", "Financiering in (KBC-krediet)"),
    (r"BETALING INVESTERINGSKREDIET", "KBC-krediet aflossing + rente"),
    (r"GELEEND BEDRAG FURVAC", "Lening Kaydee (in)"),
    (r"KAYDEE GIELEN", "Lening Kaydee (terug)"),
    (r"CREAZY", "Creazy"),
    (r"BTW-ONTVANGSTEN", "Btw"),
    # voorraad
    (r"FURVAC|PET20\d{8}|PRODUCT70%|^1618 6196|ALIBABA", "Voorraad (fabriek)"),
    (r"PACKAGINGDISCOUNTER|SUPPY", "Voorraad (verpakking & giveaways)"),
    # fulfilment
    (r"WIDEM", "Widem (fulfilment, vracht, invoer)"),
    (r"BPOST|POSTNL|RETURNGO", "Verzending & retours (overig)"),
    # marketing
    (r"FACEBK|METAPAY|FB\.ME", "Ads Meta"),
    (r"GOOGLE ADS|GOOGLE\s*\*?ADS", "Ads Google"),
    (r"ADVANCEMEDIA|DIGITAL LEADER|FIVERR|HIGGSFIELD|DRUKBEDRIJF|PRINTDEAL|HOLO AI", "Marketing & content"),
    (r"FINDAJOB", "Personeel (student)"),
    # software & admin
    (r"SHOPIFY HARDWARE", "Materiaal"),
    (r"SHOPIFY|KLAVIYO|GOOGLE|LOVABLE|APPSUMO|GODADDY|YUKI", "Software & abonnementen"),
    (r"PRO-COUNT|PRO - COUNT", "Boekhouder"),
    (r"KREDIETDOSSIER|AFREKENING OP .* VAN BE84|KBC-BUSINESS PRO|BOOSTPACK|COMPANY PRO PLAN FEE|PLAN FEE", "Bankkosten"),
    (r"KBC VERZEKERINGEN", "Verzekering"),
    (r"ACERTA", "Sociale bijdragen vennoten"),
    (r"HENRI STEYAERT", "Terugbetaling kosten aan Henri"),
    (r"GS1|PEVA|POM-OOSTV", "Administratie & lidmaatschappen"),
    (r"AMBULANTE ZELFSTANDIGEN", "Markten & events"),
    (r"COOLBLUE|ACTION|SD WORKWEAR|PLUS GENT|ALBERT HEIJN|Q WASH", "Materiaal"),
    (r"HADDOK|SANTIBAL|YAKI|BORZE|CHARLATAN|NENUPHAR|BOOKING|PARKING|PAY\*PATRON|BANCONTACT PAYCONIQ", "Representatie & reizen"),
]

GROEP = {
    "Omzet webshop (Shopify)": "Inkomsten", "Omzet bol.com": "Inkomsten", "Omzet overige kanalen": "Inkomsten", "Betaalkosten": "Werking", "Terugbetalingen aan klanten": "Inkomsten", "Overige ontvangsten": "Werking",
    "Voorraad (fabriek)": "Voorraad", "Voorraad (verpakking & giveaways)": "Voorraad",
    "Widem (fulfilment, vracht, invoer)": "Fulfilment", "Verzending & retours (overig)": "Fulfilment",
    "Ads Meta": "Marketing", "Ads Google": "Marketing", "Marketing & content": "Marketing", "Personeel (student)": "Marketing",
    "Software & abonnementen": "Werking", "Boekhouder": "Werking", "Bankkosten": "Werking", "Verzekering": "Werking",
    "Administratie & lidmaatschappen": "Werking", "Materiaal": "Werking", "Representatie & reizen": "Werking",
    "Markten & events": "Werking", "Terugbetaling kosten aan Henri": "Werking",
    "Sociale bijdragen vennoten": "Vennoten", "Btw": "Btw",
    "Financiering in (KBC-krediet)": "Financiering", "KBC-krediet aflossing + rente": "Financiering",
    "Lening Kaydee (in)": "Financiering", "Lening Kaydee (terug)": "Financiering", "Creazy": "Financiering",
    "Kredietkaart 2025 (geen detail)": "Werking", "Te bekijken": "Te bekijken",
}

KAART_DETAIL_VANAF = "2026-02-01"  # afrekeningen vanaf hier zijn gedekt door de kaartdetails (uitgaven vanaf jan 2026)


HEEFT_PAYPAL = False


def categorie(r):
    t = f"{r.get('tegenpartij','')} {r.get('mededeling','')}".upper().strip()
    if r.get("bron") == "PayPal":
        code = r.get("soort", "")
        if code == "FEE":
            return "Betaalkosten"
        if code.startswith("T04"):
            return "Intern (PayPal→KBC)"
        if code.startswith("T11") or r["bedrag"] < 0 and code.startswith(("T12", "T17")):
            return "Terugbetalingen aan klanten"
        if code.startswith(("T00", "T01")) and r["bedrag"] > 0:
            return "Omzet overige kanalen"
        return "Te bekijken"
    # 25/05/2026: Creazy stortte €435,72 en SmartPaw betaalde daarmee een Findajob-factuur van Creazy → verrekend, geen SmartPaw-kost
    if r.get("datum") == "2026-05-25" and abs(abs(r["bedrag"]) - 435.72) < 0.01 and re.search(r"CREAZY|FINDAJOB", t):
        return "Intern (voor Creazy, verrekend)"
    if HEEFT_PAYPAL and "PAYPAL" in t and r["bedrag"] > 0 and r.get("bron") == "KBC":
        return "Intern (PayPal→KBC)"
    for pat, cat in REGELS:
        if re.search(pat, t):
            if cat.startswith("Omzet") and r["bedrag"] < 0:
                continue  # uitgave bij een betaalprovider is geen omzet
            return cat
    return "Te bekijken"


def main():
    rows = []
    for f in sorted(glob.glob(str(DATA / "transacties-*.json"))):
        rows += json.loads(Path(f).read_text())
    kaart = DATA / "kaart-2026.json"
    if kaart.exists():
        rows += json.loads(kaart.read_text())

    global HEEFT_PAYPAL
    HEEFT_PAYPAL = any(r.get("bron") == "PayPal" for r in rows)
    # USD-betaling Revolut omrekenen met de koers van de wissel op dezelfde dag
    eur_per_usd = {}
    for r in rows:
        if r["bron"] == "Revolut" and "EXCHANGED" in r["mededeling"].upper():
            eur_per_usd.setdefault(r["datum"], {})["usd" if r["munt"] == "USD" else "eur"] = abs(r["bedrag"])
    out, onbekend = [], []
    for r in rows:
        cat = categorie(r)
        bedrag = r["bedrag"]
        if r["munt"] == "USD":
            k = eur_per_usd.get(r["datum"])
            bedrag = round(bedrag * k["eur"] / k["usd"], 2) if k and k.get("usd") else round(bedrag / 1.16, 2)
        if cat == "Kredietkaart-afrekening":
            if r["datum"] >= KAART_DETAIL_VANAF:
                cat = "Intern (kaartafrekening, detail apart)"
            else:
                cat = "Kredietkaart 2025 (geen detail)"
        rr = dict(r, categorie=cat, bedrag_eur=bedrag)
        # KBC-krediet: rente apart van kapitaal
        if cat == "KBC-krediet aflossing + rente":
            m = re.search(r"KAPITAAL ([\d,.]+)", r["mededeling"].upper())
            kap = float(m[1].replace(",", ".")) if m else 0.0
            out.append(dict(rr, categorie="Aflossing KBC-krediet", bedrag_eur=-kap))
            rr = dict(rr, categorie="Rente KBC-krediet", bedrag_eur=round(bedrag + kap, 2))
        out.append(rr)
        if cat == "Te bekijken":
            onbekend.append({k: r[k] for k in ("datum", "bron", "bedrag", "tegenpartij", "mededeling")})

    GROEP.update({"Aflossing KBC-krediet": "Financiering", "Rente KBC-krediet": "Werking"})
    per = {}
    for r in out:
        if r["categorie"].startswith("Intern"):
            continue
        m = per.setdefault(r["datum"][:7], {})
        m[r["categorie"]] = round(m.get(r["categorie"], 0) + r["bedrag_eur"], 2)
    maanden = [dict(maand=k, **v) for k, v in sorted(per.items())]
    # IBAN per leverancier (voor betaal-QR's): meest gebruikte tegenrekening bij uitgaande betalingen
    ib = {}
    for r in out:
        if r["bedrag"] < 0 and r.get("tegenrekening") and not r["categorie"].startswith("Intern"):
            naam = re.sub(r"\s+(NV|BV|VZW|BVBA|SRL|SA)\b.*$", "", (r.get("tegenpartij") or "").strip(), flags=re.I).upper()
            ib.setdefault(naam, {}).setdefault(r["tegenrekening"], 0)
            ib[naam][r["tegenrekening"]] += 1
    (DATA / "iban-leveranciers.json").write_text(json.dumps({n: max(v, key=v.get) for n, v in ib.items() if n}, ensure_ascii=False, indent=1))
    (DATA / "gecategoriseerd.json").write_text(json.dumps(sorted(out, key=lambda r: r["datum"], reverse=True), ensure_ascii=False, indent=1))
    (DATA / "kas-per-maand.json").write_text(json.dumps({
        "maanden": maanden, "groepen": GROEP, "onbekend": onbekend,
        "bijgewerkt": datetime.now(timezone.utc).isoformat(timespec="seconds")}, ensure_ascii=False, indent=1))
    print(f"{len(out)} verrichtingen, {len(onbekend)} te bekijken")


if __name__ == "__main__":
    main()
