"""Haalt bestellingen, facturen (commissie + kosten) en retouren op bij bol.com (Retailer API v10).

Alleen-lezen. Sleutels uit GitHub-secrets BOL_CLIENT_ID / BOL_CLIENT_SECRET
(bol Partnerplatform → Instellingen → API-instellingen → Retailer API).

Uitvoer in data/bol/:
  orders.json          alle bestellingen met orderregels (EAN, aantal, prijs, commissie)
  facturen/<id>.json   factuurspecificatie per factuur (omzet, commissie, labels, …)
  retouren.json        retouren
  overzicht.json       per maand: orders, stuks, omzet incl. btw, commissie, andere bol-kosten, uitbetaald (raming)
"""
import json, os, sys, time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

D = Path("data/bol"); (D / "facturen").mkdir(parents=True, exist_ok=True)
API = "https://api.bol.com/retailer"
V10 = "application/vnd.retailer.v10+json"
START = date(2025, 10, 1)
log = lambda *a: print(*a, file=sys.stderr)


class Bol:
    def __init__(self):
        r = requests.post("https://login.bol.com/token?grant_type=client_credentials",
                          auth=(os.environ["BOL_CLIENT_ID"], os.environ["BOL_CLIENT_SECRET"]),
                          headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        self.h = {"Authorization": "Bearer " + r.json()["access_token"], "Accept": V10}

    def get(self, path, params=None, accept=V10):
        for poging in range(6):
            r = requests.get(API + path, params=params, headers={**self.h, "Accept": accept}, timeout=60)
            if r.status_code == 429:  # rate limit: wacht wat bol vraagt
                time.sleep(int(r.headers.get("Retry-After", "5")) + 1); continue
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            return r.json() if r.content else {}
        raise RuntimeError(f"rate limit bleef op {path}")


def load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def orders(bol):
    path = D / "orders.json"
    have = {o["orderId"]: o for o in load(path, [])}
    page, nieuw = 1, 0
    while True:
        j = bol.get("/orders", {"status": "ALL", "fulfilment-method": "ALL", "page": page})
        lst = j.get("orders", [])
        if not lst:
            break
        for o in lst:
            oid = o["orderId"]
            if oid in have and have[oid].get("_volledig"):
                continue
            det = bol.get(f"/orders/{oid}") or o
            land = (det.get("shipmentDetails") or {}).get("countryCode")
            for k in ("shipmentDetails", "billingDetails"):
                det.pop(k, None)  # geen klantgegevens in de repo
            if land:
                det["land"] = land  # enkel het land (voor OSS), geen adres
            det["_volledig"] = True
            have[oid] = det; nieuw += 1
        page += 1
        if page > 50:
            break
    path.write_text(json.dumps(sorted(have.values(), key=lambda o: o.get("orderPlacedDateTime", ""), reverse=True), ensure_ascii=False, indent=1))
    return list(have.values()), nieuw


def facturen(bol):
    """Facturen per venster van max. 32 dagen; bij de eerste keer vanaf START."""
    gekend = {p.stem for p in (D / "facturen").glob("*.json")}
    van = START if not gekend else date.today() - timedelta(days=60)
    nieuw = 0
    while van < date.today():
        tot = min(van + timedelta(days=30), date.today())
        j = bol.get("/invoices", {"period-start-date": van.isoformat(), "period-end-date": tot.isoformat()})
        for inv in j.get("invoiceListItems", []) or j.get("invoices", []):
            iid = str(inv.get("invoiceId"))
            if not iid or iid in gekend:
                continue
            spec, page = [], 1
            while True:
                s = bol.get(f"/invoices/{iid}/specification", {"page": page})
                rijen = s.get("invoiceSpecification") or s.get("invoiceSpecifications") or s.get("transactions") or []
                if not rijen:
                    break
                spec += rijen; page += 1
                if page > 100:
                    break
            (D / "facturen" / f"{iid}.json").write_text(json.dumps({"factuur": inv, "specificatie": spec}, ensure_ascii=False, indent=1))
            gekend.add(iid); nieuw += 1
        van = tot + timedelta(days=1)
    return nieuw


def retouren(bol):
    alle = []
    for handled in ("false", "true"):
        page = 1
        while page <= 20:
            j = bol.get("/returns", {"handled": handled, "fulfilment-method": "FBR", "page": page})
            lst = j.get("returns", [])
            if not lst:
                break
            alle += lst; page += 1
    (D / "retouren.json").write_text(json.dumps(alle, ensure_ascii=False, indent=1))
    return len(alle)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def overzicht(alle_orders):
    """Per maand uit de factuurspecificaties (bron van waarheid, 2 jaar terug): omzet, commissie, retouren, bol-ads, labels."""
    m = defaultdict(lambda: {"orders": set(), "stuks": 0, "omzet_incl": 0.0, "commissie": 0.0, "bol_ads": 0.0,
                             "retourlabels": 0.0, "andere_kosten": 0.0, "per_ean": {}})
    for p in (D / "facturen").glob("*.json"):
        f = json.loads(p.read_text())
        per = (f["factuur"].get("invoicePeriod") or {}).get("startDate") or f["factuur"].get("issueDate")
        maand = datetime.fromtimestamp(per / 1000, timezone.utc).strftime("%Y-%m") if isinstance(per, (int, float)) else str(per)[:7]
        for t in f.get("specificatie", []):
            parts = t["id"].split("#"); typ = parts[-1]
            bedrag = num((t.get("lineExtensionAmount") or {}).get("value"))
            q = num((t.get("invoicedQuantity") or {}).get("value"))
            r = m[maand]
            if typ in ("TURNOVER", "CORRECTION_TURNOVER"):
                omz = -bedrag  # bol rekent omzet negatief (= naar ons)
                r["omzet_incl"] += omz
                ean = parts[1] if len(parts) > 2 else "?"
                e = r["per_ean"].setdefault(ean, {"stuks": 0, "omzet_incl": 0.0})
                sign = 1 if typ == "TURNOVER" else -1
                e["stuks"] += sign * int(q); e["omzet_incl"] += omz
                r["stuks"] += sign * int(q)
                if typ == "TURNOVER":
                    r["orders"].add(parts[0])
            elif typ in ("COMMISSION", "CORRECTION_COMMISSION"):
                r["commissie"] += bedrag
            elif typ == "SPONSORED_PRODUCTS_ADS":
                r["bol_ads"] += bedrag
            elif "LABEL" in typ:
                r["retourlabels"] += bedrag
            else:
                r["andere_kosten"] += bedrag
    rows = []
    for k in sorted(m):
        r = m[k]
        rows.append({"maand": k, "orders": len(r["orders"]), "stuks": r["stuks"], "omzet_incl": round(r["omzet_incl"], 2),
                     "commissie": round(r["commissie"], 2), "bol_ads": round(r["bol_ads"], 2),
                     "retourlabels": round(r["retourlabels"], 2), "andere_kosten": round(r["andere_kosten"], 2),
                     "per_ean": {e: {**v, "omzet_incl": round(v["omzet_incl"], 2)} for e, v in r["per_ean"].items()}})
    (D / "overzicht.json").write_text(json.dumps({"_uitleg": "Bedragen excl. btw behalve omzet_incl. Commissie/ads/labels zijn kosten (positief).", "maanden": rows}, ensure_ascii=False, indent=1))


def main():
    if not os.environ.get("BOL_CLIENT_ID"):
        log("bol: geen BOL_CLIENT_ID, overgeslagen"); return
    status = {"fouten": []}
    try:
        bol = Bol()
        o, n = orders(bol); status["orders_nieuw"] = n
        status["facturen_nieuw"] = facturen(bol)
        status["retouren"] = retouren(bol)
        overzicht(o)
    except Exception as e:
        status["fouten"].append(f"{type(e).__name__}: {str(e)[:300]}"); log(status["fouten"][-1])
    status["opgehaald"] = date.today().isoformat()
    (D / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1))
    log(json.dumps(status))


if __name__ == "__main__":
    main()
