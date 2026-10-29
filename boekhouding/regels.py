"""Bewijsstatus per bankregel, per kwartaal → boekhouding/boek/<JJJJ>Q<k>.json (voor het platform, DB-doc boek/<JJJJ>Q<k>).

Elke regel (KBC, KBC-kaart, Revolut, PayPal) krijgt:
  verklaard  — geen factuur nodig (interne overschrijving, uitbetaling van Shopify/bol/PayPal, btw, lening, aflossing, rente, bankkosten)
  gekoppeld  — er hangt een document aan (koppelingen.json: upload in het platform, factuur uit de mail, Yuki/Peppol)
  ontbreekt  — nog geen document of uitleg
Gebruik: python boekhouding/regels.py [JJJJ k ...]   (zonder argumenten: lopend en vorig kwartaal)
"""
import json, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kwartaal import VAK, btw_type, kwartaal  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "boekhouding"

VERKLAARD = {
    "Omzet webshop (Shopify)": "uitbetaling Shopify Payments (verkopen in Shopify)",
    "Omzet bol.com": "uitbetaling bol.com (bol-factuur)",
    "Omzet overige kanalen": "uitbetaling PayPal/SumUp/Amazon/winkel (verkoop gedocumenteerd in het kanaal)",
    "Btw": "btw-betaling (aangifte)",
    "Aflossing KBC-krediet": "kredietovereenkomst KBC", "Rente KBC-krediet": "kredietovereenkomst KBC",
    "Bankkosten": "bankafschrift", "Financiering in (KBC-krediet)": "kredietovereenkomst KBC",
    "Lening Kaydee (in)": "lening vennoot", "Lening Kaydee (terug)": "lening vennoot", "Creazy": "lening/verrekening Creazy",
    "Sociale bijdragen vennoten": "sociale bijdragen vennoten (attest Acerta)",
    "Terugbetalingen aan klanten": "terugbetaling klant (order in Shopify)",
    "Overige ontvangsten": "terugbetaling inschrijving (Hogeschool Gent)",
    "Betaalkosten": "PayPal-kosten (PayPal-overzicht)",
}


STOP = {"factuur", "van", "bvba", "limited", "ireland", "betaling", "inc", "nv", "bv", "belgium", "via", "mollie"}


def _tok(s):
    return {w for w in re.findall(r"[a-z]{4,}", (s or "").lower()) if w not in STOP}


def _dagen(a, b):
    return (date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days


def yuki_koppel(regels):
    """Koppel ontbrekende regels aan facturen die al in Yuki geboekt zijn (Peppol, upload, Pro-count).
    Pas 1: zelfde leverancier + bedrag (±2 cent), factuur tot 75 d vóór of 35 d na de betaling.
    Pas 2: enkel bedrag (exact), factuur binnen 20 dagen. Elke Yuki-boeking wordt één keer gebruikt."""
    pad = ROOT / "data/yuki/openstaand.json"
    if not pad.exists():
        return
    yb = json.loads(pad.read_text()).get("leveranciers_boekingen", [])
    gebruikt = set()
    open_ = [r for r in regels if r["status"] == "ontbreekt"]
    for pas in (1, 2):
        for r in open_:
            if r["status"] != "ontbreekt":
                continue
            beste = None
            for e in yb:
                if e["id"] in gebruikt:
                    continue
                verschil = abs(abs(e["bedrag"]) - abs(r["bedrag"]))
                d = _dagen(r["datum"], e["datum"])  # >0: factuur vóór betaling
                if pas == 1:
                    ok = verschil <= 0.021 and -35 <= d <= 75 and (_tok(r["tegenpartij"] + " " + r["mededeling"]) & _tok(e["contact"]))
                else:
                    ok = verschil < 0.005 and abs(d) <= 20
                if ok and (beste is None or abs(d) < abs(_dagen(r["datum"], beste["datum"]))):
                    beste = e
            if beste:
                gebruikt.add(beste["id"])
                r["status"] = "gekoppeld"
                r["bewijs"] = {"soort": "yuki", "label": f"in Yuki: {beste['contact']} ({beste['datum']})", "yuki_id": beste["id"]}


def main(kwartalen):
    g = json.loads((ROOT / "data/gecategoriseerd.json").read_text())
    kop_pad = B / "koppelingen.json"
    kop = json.loads(kop_pad.read_text()) if kop_pad.exists() else {}
    (B / "boek").mkdir(exist_ok=True)
    for jaar, k in kwartalen:
        van, tot, _ = kwartaal(jaar, k)
        regels, telling = [], {"verklaard": 0, "gekoppeld": 0, "ontbreekt": 0}
        for r in sorted((r for r in g if van <= r["datum"] <= tot), key=lambda r: (r["datum"], r["id"]), reverse=True):
            cat = r["categorie"]
            if cat.startswith("Intern"):
                continue
            typ, uitleg = btw_type(r)
            rid = r["id"]
            if rid in kop:
                status, bewijs = "gekoppeld", kop[rid]
            elif cat in VERKLAARD:
                status, bewijs = "verklaard", {"soort": "regel", "label": VERKLAARD[cat]}
            else:
                status, bewijs = "ontbreekt", None
            telling[status] += 1
            regels.append({"id": rid, "datum": r["datum"], "bron": r["bron"],
                           "tegenpartij": (r.get("tegenpartij") or r.get("mededeling") or "")[:50],
                           "mededeling": (r.get("mededeling") or "")[:70], "bedrag": round(r["bedrag_eur"], 2),
                           "categorie": cat, "btw_type": typ, "vak": VAK[typ], "status": status, "bewijs": bewijs})
        yuki_koppel(regels)
        telling = {k: sum(1 for r in regels if r["status"] == k) for k in ("verklaard", "gekoppeld", "ontbreekt")}
        pakket = {}
        xl = B / "rapporten" / f"SmartPaw_Q{k}-{jaar}.xlsx"
        if xl.exists():
            pakket["bestand"] = xl.name
        inp = B / "input" / f"shopify_{jaar}Q{k}.json"
        if inp.exists():
            oss = json.loads(inp.read_text()).get("oss_eu_b2c", {})
            jr = [v for kk, v in oss.items() if kk.startswith(str(jaar)) and "per maand" not in kk]
            if jr:
                pakket["oss_eu"] = round(sum(jr[0].values()), 2)
        extra = B / "rapporten" / f"pakket_{jaar}Q{k}.json"  # btw-cijfer na herberekening (ochtendtaak)
        if extra.exists():
            pakket.update(json.loads(extra.read_text()))
        doc = {"kwartaal": f"{jaar}Q{k}", "van": van, "tot": tot, "telling": telling, "regels": regels,
               "pakket": pakket, "bijgewerkt": date.today().isoformat()}
        (B / "boek" / f"{jaar}Q{k}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        print(f"{jaar}Q{k}", telling)


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    if a:
        qs = list(zip(a[0::2], a[1::2]))
    else:
        t = date.today(); q = (t.month - 1) // 3 + 1
        qs = [(t.year, q), (t.year if q > 1 else t.year - 1, q - 1 if q > 1 else 4)]
    main(qs)
