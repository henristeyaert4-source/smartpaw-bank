"""Lopende btw van het huidige kwartaal: hoeveel moet opzij voor de volgende btw-betaling.

Verschuldigd  = btw die klanten betaalden (Shopify 'taxes' per maand) + btw op bol-omzet (21%).
Aftrekbaar    = btw op Belgische aankopen (bankverrichtingen btw-type BE21: bedrag × 21/121)
                + btw op openstaande Belgische facturen van dit kwartaal (fin/balans.te_betalen met veld 'btw').
EU-/niet-EU-diensten en invoer (art. 41) zijn verlegd: verschuldigd én aftrekbaar, netto 0.
Prognose einde kwartaal: verkopen-btw per dag tot nu × resterende dagen, aftrekbaar idem.

Gebruik: python boekhouding/btw_lopend.py [balans.json]  → boekhouding/btw_lopend.json
"""
import json, sys, datetime as dt
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def main(balans_pad=None):
    vandaag = dt.date.today()
    k = (vandaag.month - 1) // 3 + 1
    jaar = vandaag.year
    start = dt.date(jaar, 3 * (k - 1) + 1, 1)
    einde = (dt.date(jaar + (k == 4), (3 * k) % 12 + 1, 1) - dt.timedelta(days=1))
    verval = dt.date(jaar + (k == 4), (3 * k) % 12 + 1, 20)
    maanden = [f"{jaar}-{m:02d}" for m in range(start.month, start.month + 3)]

    mt = json.load(open(R / "winst/input/maand_totalen.json"))
    shop_btw = sum(t for m, t in zip(mt["maanden"], mt["taxes"]) if m in maanden)
    wm = {r["maand"]: r for r in json.load(open(R / "winst/winst-per-maand.json"))["maanden"]}
    bol_btw = sum((wm.get(m, {}).get("omzet_bol") or 0) * 0.21 for m in maanden)

    q = f"{jaar}Q{k}"
    boek = json.load(open(R / f"boekhouding/boek/{q}.json")) if (R / f"boekhouding/boek/{q}.json").exists() else {"regels": []}
    be = [r for r in boek["regels"] if r.get("btw_type") == "BE21" and r["bedrag"] < 0]
    def btw_r(r):  # echte btw uit het bewijs als die er is (bv. bpost: verzending vrijgesteld, enkel btw op de printkost)
        bw = r.get("bewijs") or {}
        return bw["btw"] if isinstance(bw, dict) and bw.get("btw") is not None else -r["bedrag"] * 21 / 121
    aftrek_bank = sum(btw_r(r) for r in be)
    zonder_factuur = sum(btw_r(r) for r in be if r.get("status") == "ontbreekt")

    aftrek_open = 0.0
    if balans_pad and Path(balans_pad).exists():
        b = json.load(open(balans_pad)); b = b.get("data", b)
        aftrek_open = sum(t.get("btw") or 0 for t in b.get("te_betalen", []) if not t.get("betaald"))

    verschuldigd = shop_btw + bol_btw
    aftrekbaar = aftrek_bank + aftrek_open
    nu = verschuldigd - aftrekbaar
    dagen_tot = max(1, (vandaag - start).days)
    dagen_rest = (einde - vandaag).days + 1
    prognose = nu + (verschuldigd / dagen_tot - aftrek_bank / dagen_tot) * dagen_rest

    out = {"kwartaal": q, "van": str(start), "tot": str(vandaag - dt.timedelta(days=1)), "vervaldag": str(verval),
           "verschuldigd_verkopen": round(verschuldigd, 2), "waarvan_shopify": round(shop_btw, 2), "waarvan_bol": round(bol_btw, 2),
           "aftrekbaar": round(aftrekbaar, 2), "aftrekbaar_betaald": round(aftrek_bank, 2), "aftrekbaar_open_facturen": round(aftrek_open, 2),
           "aftrekbaar_zonder_factuur": round(zonder_factuur, 2),
           "te_betalen_tot_nu": round(nu, 2), "prognose_einde_kwartaal": round(prognose, 2),
           "uitleg": "Btw die klanten betaalden min btw op Belgische aankopen. Buitenlandse diensten en invoer zijn verlegd (netto 0). Aftrek mag enkel met factuur.",
           "bijgewerkt": vandaag.isoformat()}
    json.dump(out, open(R / "boekhouding/btw_lopend.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
