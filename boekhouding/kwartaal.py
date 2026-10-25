"""Kwartaalpakket voor de boekhouder: verkopen, aankopen (met btw-type), bankafstemming, btw-voorbereiding,
ontbrekende documenten en OSS-opvolging. Alleen een voorbereiding: Pro-count controleert en dient in.

Gebruik: python boekhouding/kwartaal.py 2026 3   → boekhouding/rapporten/SmartPaw_Q3-2026.xlsx + .json
"""
import json, re, sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "boekhouding"

# btw-type per uitgave: (regex op tegenpartij+mededeling+categorie, type, toelichting)
# BE21 = Belgische leverancier, 21% aftrekbaar · BE21NA = Belgische btw, niet aftrekbaar (restaurant, hotel)
# EU = dienst uit EU, btw verlegd (vak 88/55) · NONEU = dienst buiten EU, btw verlegd (vak 87/56)
# GEEN = geen btw / vrijgesteld · INVOER = goederen uit China (btw via invoeraangifte Widem)
# NAKIJKEN = btw-behandeling onzeker · FIN = geen aankoop (btw-betaling, lening, aflossing, vennoot)
TYPES = [
    (r"BTW-ONTVANGSTEN|Btw$", "FIN", "btw-betaling"),
    (r"Aflossing KBC|Lening|Creazy|Sociale bijdragen|Terugbetalingen aan klanten", "FIN", "geen aankoop"),
    (r"Rente KBC|Bankkosten|KBC VERZEKERINGEN|Verzekering|COMPANY PRO PLAN FEE", "GEEN", "vrijgesteld / geen btw"),
    (r"FACEBK|METAPAY|GOOGLE|SHOPIFY(?! HARDWARE)|HOLO AI|FIVERR", "EU", "dienst Ierland/EU, verlegd"),
    (r"ADVANCEMEDIA", "EU", "dienst Nederland, verlegd"),
    (r"KLAVIYO|HIGGSFIELD|LOVABLE|APPSUMO|GODADDY|RETURNGO", "NONEU", "dienst buiten EU, verlegd"),
    (r"FURVAC|PRODUCT70|ALIBABA|^1618", "INVOER", "goederen China; btw via invoer (Widem)"),
    (r"HADDOK|SANTIBAL|YAKI|BORZE|CHARLATAN|NENUPHAR|PATRON|BANCONTACT PAYCONIQ", "BE21NA", "restaurant/representatie"),
    (r"BOOKING", "GEEN", "hotel buitenland, buitenlandse btw niet aftrekbaar"),
    (r"DRUKBEDRIJF|PACKAGINGDISCOUNTER|SUPPY", "NAKIJKEN", "buitenlandse/onbekende leverancier"),
    (r"POM-OOSTV|AMBULANTE|PEVA|GS1", "NAKIJKEN", "lidmaatschap/standgeld: btw?"),
    (r"HENRI STEYAERT", "NAKIJKEN", "terugbetaling privé betaalde kost: factuur + btw nakijken"),
    (r"WIDEM|PRO-COUNT|PRO - COUNT|FINDAJOB|BPOST|YUKI|ACTION|PLUS GENT|SHOPIFY HARDWARE|COOLBLUE|SD WORKWEAR|PRINTDEAL|DIGITAL LEADER|Q WASH", "BE21", "Belgische leverancier"),
]
VAK = {"BE21": "82 (+ btw in 59)", "BE21NA": "82 (btw niet aftrekbaar)", "EU": "88 / 55 / 59", "NONEU": "87 / 56 / 59",
       "GEEN": "82 zonder btw", "INVOER": "invoeraangifte (Widem)", "NAKIJKEN": "?", "FIN": "—"}


def btw_type(r):
    t = f"{r.get('tegenpartij','')} {r.get('mededeling','')} {r.get('categorie','')}".upper()
    for pat, typ, uitleg in TYPES:
        if re.search(pat, t, re.I):
            return typ, uitleg
    return "NAKIJKEN", "geen regel"


def kwartaal(jaar, k):
    m0 = (k - 1) * 3 + 1
    return f"{jaar}-{m0:02d}-01", f"{jaar}-{m0+2:02d}-{[31,30,30,31][k-1]:02d}", [f"{jaar}-{m:02d}" for m in range(m0, m0 + 3)]


def main(jaar=2026, k=3):
    van, tot, maanden = kwartaal(jaar, k)
    shop = json.loads((B / f"input/shopify_{jaar}Q{k}.json").read_text())
    g = json.loads((ROOT / "data/gecategoriseerd.json").read_text())
    bol = {r["maand"]: r for r in json.loads((ROOT / "data/bol/overzicht.json").read_text())["maanden"]}
    status = json.loads((ROOT / "data/status.json").read_text())

    in_q = [r for r in g if van <= r["datum"] <= tot]
    uit = sorted([r for r in in_q if r["bedrag_eur"] < 0 and not r["categorie"].startswith("Intern")], key=lambda r: r["datum"])
    stripe = sum(r["bedrag_eur"] for r in in_q if r["categorie"] == "Omzet webshop (Shopify)")

    wb = Workbook()
    F = "Arial"
    h = Font(name=F, bold=True, color="FFFFFF"); hf = PatternFill("solid", fgColor="0E6B5C")
    norm = Font(name=F, size=10); bold = Font(name=F, size=10, bold=True); titel = Font(name=F, size=14, bold=True)
    eur = '€ #,##0.00;[Red]-€ #,##0.00;-'
    thin = Border(bottom=Side(style="thin", color="D9DDD5"))

    def tabel(ws, rij, kop, rijen, breedtes=None, geld=()):
        for j, c in enumerate(kop, 1):
            x = ws.cell(rij, j, c); x.font = h; x.fill = hf; x.alignment = Alignment(wrap_text=True, vertical="center")
        for i, r in enumerate(rijen, rij + 1):
            for j, v in enumerate(r, 1):
                x = ws.cell(i, j, v); x.font = norm; x.border = thin
                if j in geld: x.number_format = eur
        if breedtes:
            for j, w in enumerate(breedtes, 1):
                ws.column_dimensions[get_column_letter(j)].width = w
        return rij + 1, rij + len(rijen)

    # --- 1. Samenvatting (vult zich met formules uit de andere tabbladen)
    s = wb.active; s.title = "Samenvatting"
    s["A1"] = f"SmartPaw VOF — kwartaalpakket Q{k} {jaar}"; s["A1"].font = titel
    s["A2"] = f"Voorbereid door het SmartPaw-financiënplatform op {date.today().isoformat()}. Voorbereiding: Pro-count controleert en dient in."; s["A2"].font = norm

    # --- 2. Verkopen
    v = wb.create_sheet("Verkopen")
    v["A1"] = f"Verkopen Q{k} {jaar} (Shopify per factuurland + bol.com)"; v["A1"].font = bold
    rijen = [[p["land"], p["orders"], p["bruto"], p["korting"], p["retours"], p["netto"], p["verzending"], p["btw"], p["totaal"]] for p in shop["per_land"]]
    a, z = tabel(v, 3, ["Shopify – land", "Orders", "Bruto", "Korting", "Retours", "Netto excl. btw", "Verzending (incl. btw)", "Btw", "Totaal incl. btw"], rijen,
                 [26, 9, 13, 13, 13, 15, 15, 13, 15], geld=(3, 4, 5, 6, 7, 8, 9))
    tr = z + 1
    v.cell(tr, 1, "Totaal Shopify").font = bold
    for c in range(2, 10):
        L = get_column_letter(c); x = v.cell(tr, c, f"=SUM({L}{a}:{L}{z})"); x.font = bold
        if c > 2: x.number_format = eur
    shop_tot_row = tr
    br = tr + 2
    v.cell(br, 1, "bol.com (uit de bol-facturen)").font = bold
    rijen_b = []
    for m in maanden:
        b = bol.get(m, {})
        rijen_b.append([m, b.get("orders", 0), b.get("omzet_incl", 0), f"=C{{r}}/1.21", f"=C{{r}}-D{{r}}", b.get("commissie", 0), b.get("bol_ads", 0), b.get("retourlabels", 0)])
    a2, z2 = tabel(v, br + 1, ["bol – maand", "Orders", "Omzet incl. btw (na retouren)", "Netto excl. btw", "Btw 21%", "Commissie (kost, verlegd)", "bol-ads (kost)", "Retourlabels (kost)"], [], geld=())
    for i, rr in enumerate(rijen_b):
        r = a2 + i
        for j, val in enumerate(rr, 1):
            x = v.cell(r, j, val.replace("{r}", str(r)) if isinstance(val, str) and "{r}" in val else val); x.font = norm; x.border = thin
            if j > 2: x.number_format = eur
    z2 = a2 + len(rijen_b) - 1
    bt = z2 + 1
    v.cell(bt, 1, "Totaal bol").font = bold
    for c in range(2, 9):
        L = get_column_letter(c); x = v.cell(bt, c, f"=SUM({L}{a2}:{L}{z2})"); x.font = bold
        if c > 2: x.number_format = eur
    bol_tot_row = bt
    pr = bt + 2
    v.cell(pr, 1, "Per betaalwijze (Shopify)").font = bold
    a3, z3 = tabel(v, pr + 1, ["Betaalwijze", "Bruto", "Terugbetaald", "Netto"], [[p["betaalwijze"], p["bruto"], p["terugbetaald"], p["netto"]] for p in shop["per_betaalwijze"]], geld=(2, 3, 4))
    fr = z3 + 2
    fees = sum(v2 for kk, v2 in shop["shopify_payments_fees"].items() if not kk.startswith("_"))
    v.cell(fr, 1, "Shopify Payments-kosten (fees)"); v.cell(fr, 4, fees).number_format = eur
    v.cell(fr + 1, 1, "Verwachte uitbetalingen (netto − fees)"); v.cell(fr + 1, 4, f"=D{a3}-D{fr}").number_format = eur
    v.cell(fr + 2, 1, "Stortingen Shopify Payments op KBC in dit kwartaal"); v.cell(fr + 2, 4, round(stripe, 2)).number_format = eur
    v.cell(fr + 3, 1, "Verschil (timing: verkoop eind vorig kwartaal betaald in dit kwartaal, en omgekeerd)"); v.cell(fr + 3, 4, f"=D{fr+2}-D{fr+1}").number_format = eur
    for r in range(fr, fr + 4):
        v.cell(r, 1).font = norm

    # --- 3. Aankopen
    k_ = wb.create_sheet("Aankopen")
    k_["A1"] = f"Uitgaven Q{k} {jaar} volgens de bank (KBC, KBC-kredietkaart, Revolut) — met btw-behandeling"; k_["A1"].font = bold
    rows, ontbrekend = [], []
    for r in uit:
        typ, uitleg = btw_type(r)
        bedrag = -r["bedrag_eur"]
        rows.append([r["datum"], r["bron"], (r.get("tegenpartij") or r.get("mededeling") or "")[:45], r["categorie"], typ, VAK[typ], uitleg, bedrag])
        if typ not in ("FIN",) and r["categorie"] not in ("Rente KBC-krediet", "Bankkosten", "Aflossing KBC-krediet"):
            ontbrekend.append([r["datum"], (r.get("tegenpartij") or r.get("mededeling") or "")[:45], bedrag, typ, "factuur in Lucy/Yuki?"])
    a4, z4 = tabel(k_, 3, ["Datum", "Rekening", "Leverancier", "Categorie", "Btw-type", "Vak aangifte", "Toelichting", "Betaald (incl. btw)", "Maatstaf (excl. btw)", "Btw"], [], [11, 10, 34, 26, 10, 16, 30, 14, 14, 12])
    for i, rr in enumerate(rows):
        r = a4 + i
        for j, val in enumerate(rr, 1):
            x = k_.cell(r, j, val); x.font = norm; x.border = thin
        k_.cell(r, 8).number_format = eur
        typ = rr[4]
        k_.cell(r, 9, f"=H{r}/1.21" if typ in ("BE21", "BE21NA") else f"=H{r}").number_format = eur
        k_.cell(r, 10, f"=H{r}-I{r}" if typ in ("BE21", "BE21NA") else (f"=I{r}*0.21" if typ in ("EU", "NONEU") else 0)).number_format = eur
    z4 = a4 + len(rows) - 1
    k_.auto_filter.ref = f"A3:J{z4}"

    # --- 4. Btw-voorbereiding
    b = wb.create_sheet("Btw-voorbereiding")
    b["A1"] = f"Btw-aangifte Q{k} {jaar} — voorbereiding (ter controle door Pro-count)"; b["A1"].font = bold
    rng = f"Aankopen!$E${a4}:$E${z4}"
    def som(col, typ): return f'=SUMIFS(Aankopen!${col}${a4}:${col}${z4},{rng},"{typ}")'
    regels = [
        ("03", "Verkopen 21% (maatstaf): Shopify netto + verzending excl. btw + bol netto", f"=Verkopen!F{shop_tot_row}+Verkopen!G{shop_tot_row}/1.21+Verkopen!D{bol_tot_row}"),
        ("54", "Verschuldigde btw op verkopen", f"=Verkopen!H{shop_tot_row}+Verkopen!E{bol_tot_row}"),
        ("82", "Aankopen diensten en diverse goederen BE (maatstaf, incl. niet-aftrekbaar)", f"={som('I','BE21')[1:]}+{som('I','BE21NA')[1:]}+{som('I','GEEN')[1:]}"),
        ("88", "Diensten uit andere EU-landen (verlegd) — maatstaf", som("I", "EU")),
        ("55", "Btw op vak 88 (verlegd, verschuldigd)", som("J", "EU")),
        ("87", "Diensten van buiten de EU (verlegd) — maatstaf", som("I", "NONEU")),
        ("56", "Btw op vak 87 (verlegd, verschuldigd)", som("J", "NONEU")),
        ("59", "Aftrekbare btw: Belgische aankopen 21% + verlegde btw 55 + 56", f"={som('J','BE21')[1:]}+C8+C10"),
        ("", "Te betalen (54 + 55 + 56 − 59)", "=C5+C8+C10-C11"),
        ("", "Opgegeven door Pro-count (mail 22/10/2026)", 6873.24),
        ("", "Verschil voorbereiding − Pro-count", "=C12-C13"),
    ]
    tabel(b, 3, ["Vak", "Omschrijving", "Bedrag"], [[r[0], r[1], r[2]] for r in regels], [8, 70, 16], geld=(3,))
    b.cell(16, 1, "Niet in deze voorbereiding (zit bij Pro-count): invoer-btw van goederen uit China (invoeraangifte Widem, art. 41), btw-correcties,"
                  " en uitgaven van het type 'NAKIJKEN' (zie Aankopen).").font = Font(name=F, size=9, italic=True)
    b.cell(17, 1, "Ook alle NL-verkopen dragen nu Belgische btw (OSS-drempel €10.000 nog niet bereikt, zie OSS).").font = Font(name=F, size=9, italic=True)

    # --- 5. Bank
    bk = wb.create_sheet("Bankafstemming")
    bk["A1"] = f"Bankafstemming Q{k} {jaar}"; bk["A1"].font = bold
    rek = []
    nu = {f"{s_.get('rekening')}|{s_.get('munt')}": float(s_.get("saldo") or 0) for s_ in status["saldi"]}
    opgehaald = status["opgehaald"][:10]
    for bron, naam, munt, sleutel in (("KBC", "KBC zichtrekening BE84 7310 7076 0259", "EUR", "SMARTPAW VOF|EUR"),
                                      ("Revolut", "Revolut Business EUR", "EUR", "Main|EUR"), ("Revolut", "Revolut Business USD", "USD", "Main|USD")):
        tx = [r for r in g if r["bron"] == bron and r.get("munt", "EUR") == munt]
        na = sum(r["bedrag"] for r in tx if r["datum"] > tot)
        inq = [r for r in tx if van <= r["datum"] <= tot]
        eind = (nu.get(sleutel) or 0) - na
        mut = sum(r["bedrag"] for r in inq)
        rek.append([naam, munt, round(eind - mut, 2), round(sum(r["bedrag"] for r in inq if r["bedrag"] > 0), 2),
                    round(sum(r["bedrag"] for r in inq if r["bedrag"] < 0), 2), round(eind, 2), len(inq)])
    a5, z5 = tabel(bk, 3, ["Rekening", "Munt", "Beginsaldo", "In", "Uit", "Eindsaldo", "Verrichtingen"], rek, [38, 7, 14, 14, 14, 14, 13], geld=(3, 4, 5, 6))
    for i in range(a5, z5 + 1):
        bk.cell(i, 8, f"=C{i}+D{i}+E{i}-F{i}").number_format = eur
    bk.cell(3, 8, "Controle (moet 0 zijn)").font = h; bk.cell(3, 8).fill = hf
    bk.cell(z5 + 2, 1, f"Saldi teruggerekend vanaf de bankstand van {opgehaald} (Ponto/Revolut). KBC-kredietkaart: zie Aankopen (rekening 'KBC-kaart'); afrekening via de zichtrekening.").font = Font(name=F, size=9, italic=True)
    kaart = sum(-r["bedrag_eur"] for r in uit if r["bron"] == "KBC-kaart")
    bk.cell(z5 + 3, 1, "Kredietkaartuitgaven in dit kwartaal"); bk.cell(z5 + 3, 6, round(kaart, 2)).number_format = eur

    # --- 6. Ontbrekende documenten
    o = wb.create_sheet("Documenten")
    o["A1"] = "Per uitgave: is de factuur aanwezig in Lucy/Yuki? (automatisch af te vinken zodra de Yuki-koppeling werkt)"; o["A1"].font = bold
    tabel(o, 3, ["Datum", "Leverancier", "Bedrag", "Btw-type", "Status"], ontbrekend, [11, 40, 14, 10, 24], geld=(3,))

    # --- 7. OSS
    oss = wb.create_sheet("OSS")
    oss["A1"] = "Verkoop op afstand aan particulieren in andere EU-landen — drempel €10.000 per kalenderjaar (alle EU-landen samen, excl. btw)"; oss["A1"].font = bold
    rij = 3
    for jaar_lbl, landen in shop["oss_eu_b2c"].items():
        if jaar_lbl.startswith("_") or "per maand" in jaar_lbl:
            continue
        oss.cell(rij, 1, jaar_lbl).font = bold
        start = rij + 1
        for land, bedrag in landen.items():
            rij += 1; oss.cell(rij, 1, land).font = norm; oss.cell(rij, 2, bedrag).number_format = eur
        rij += 1
        oss.cell(rij, 1, "Totaal").font = bold; x = oss.cell(rij, 2, f"=SUM(B{start}:B{rij-1})"); x.number_format = eur; x.font = bold
        oss.cell(rij, 3, f'=IF(B{rij}>10000,"DREMPEL OVERSCHREDEN: btw van het land van de klant via OSS","onder de drempel: Belgische btw")').font = norm
        rij += 2
    oss.cell(rij, 1, "bol.com-verkopen naar NL zijn hier niet meegeteld (land per bestelling onbekend) — Pro-count: tellen die mee voor de drempel?").font = Font(name=F, size=9, italic=True)
    oss.column_dimensions["A"].width = 30; oss.column_dimensions["B"].width = 16; oss.column_dimensions["C"].width = 60

    # Samenvatting
    sam = [
        ("Verkopen Shopify (netto excl. btw)", f"=Verkopen!F{shop_tot_row}"),
        ("Verkopen bol.com (netto excl. btw)", f"=Verkopen!D{bol_tot_row}"),
        ("Btw op verkopen (vak 54)", "='Btw-voorbereiding'!C5"),
        ("Aftrekbare btw (vak 59)", "='Btw-voorbereiding'!C11"),
        ("Te betalen volgens voorbereiding", "='Btw-voorbereiding'!C12"),
        ("Te betalen volgens Pro-count", "='Btw-voorbereiding'!C13"),
        ("Verschil", "='Btw-voorbereiding'!C14"),
        ("Uitgaven met onzekere btw-behandeling (NAKIJKEN)", f'=COUNTIF(Aankopen!E{a4}:E{z4},"NAKIJKEN")'),
        ("Uitgaven zonder bevestigde factuur", f"=COUNTA(Documenten!A4:A{3+len(ontbrekend)})"),
    ]
    for i, (lbl, f) in enumerate(sam, 4):
        s.cell(i, 1, lbl).font = norm
        x = s.cell(i, 2, f); x.font = bold if "Te betalen" in lbl or lbl == "Verschil" else norm
        if i < 11: x.number_format = eur
    s.column_dimensions["A"].width = 52; s.column_dimensions["B"].width = 18
    s.cell(14, 1, "Tabbladen: Verkopen · Aankopen · Btw-voorbereiding · Bankafstemming · Documenten · OSS").font = Font(name=F, size=9, italic=True)

    out = B / "rapporten"; out.mkdir(exist_ok=True)
    pad = out / f"SmartPaw_Q{k}-{jaar}.xlsx"
    wb.save(pad)
    print(pad)


if __name__ == "__main__":
    main(*(int(x) for x in sys.argv[1:3])) if len(sys.argv) > 2 else main()
