"""Dagcijfers voor het Overzicht (periodekeuze): winst/dagen.json → DB-doc fin/dagen.

Bronnen: winst/input/shopify_dag.txt (ShopifyQL per dag: datum orders net_sales excl. btw),
winst/input/meta_dag.json (Meta-spend per dag), winst/winst-per-maand.json (maandtotalen).
Kostprijs, fulfilment en betaalkosten per dag = maandtotaal × aandeel van die dag in de maandomzet.
bol, Google Ads en vaste kosten worden gelijk over de dagen van de maand verdeeld.
Elke rij: [datum, orders, omzet, brutomarge, ads, vaste_kosten] (euro, excl. btw).
"""
import calendar, json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

W = Path(__file__).resolve().parent
shop = {}
for l in (W / "input/shopify_dag.txt").read_text().split("\n"):
    if l.strip():
        d, n, v = l.split()
        shop[d] = (int(n), float(v))
meta = json.loads((W / "input/meta_dag.json").read_text())
M = {r["maand"]: r for r in json.loads((W / "winst-per-maand.json").read_text())["maanden"]}

netto_maand = defaultdict(float)
for d, (_, v) in shop.items():
    netto_maand[d[:7]] += v

start, eind = date(2025, 10, 1), date.fromisoformat(max(shop))
rijen, d = [], start
while d <= eind:
    k, ds = d.strftime("%Y-%m"), d.isoformat()
    m = M.get(k) or M[max(M)]
    dim = calendar.monthrange(d.year, d.month)[1]
    n, net = shop.get(ds, (0, 0.0))
    fac = (m["omzet_shopify"] / netto_maand[k]) if netto_maand.get(k) else 1
    omzet_shop = net * fac
    omzet = omzet_shop + m["omzet_bol"] / dim
    tot = m["omzet_shopify"] + m["omzet_bol"]
    aandeel = omzet / tot if tot else 0
    bruto = omzet - (m["kostprijs"] + m["fulfilment"] + m["betaalkosten"]) * aandeel
    ads = meta.get(ds, 0.0) + m["ads_google"] / dim
    vast = m["vaste_kosten"] / dim
    rijen.append([ds, n, round(omzet, 2), round(bruto, 2), round(ads, 2), round(vast, 2)])
    d += timedelta(days=1)

doc = {"dagen": rijen, "tot": eind.isoformat(), "bijgewerkt": date.today().isoformat(),
       "uitleg": "Omzet = Shopify per dag + bol (maand gelijk verdeeld). Kostprijs/fulfilment/betaalkosten volgens het aandeel van de dag in de maand. Ads = Meta per dag + Google (maand verdeeld). Vaste kosten = maand gelijk verdeeld."}
(W / "dagen.json").write_text(json.dumps(doc, separators=(",", ":")))
print(len(rijen), "dagen tot", eind, "· okt:", round(sum(r[2] for r in rijen if r[0] >= "2026-10"), 0))
