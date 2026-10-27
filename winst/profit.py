"""SmartPaw winstmotor — vervangt TrueProfit.

Rekent per maand (en per product) de echte winst uit:
  omzet (Shopify, excl. btw) + bol.com
  − kostprijs (landed, per SKU en per batch: winst/kostprijzen.json)
  − fulfilment Widem (per stuk inbound+picking, per order verpakking + doos + DPD klein/groot)
  − betaalkosten (echte fees)  − advertenties (Meta + Google)
  − vaste kosten (uit de bankindeling: software, boekhouder, verzekering, rente, …)

Invoer:  winst/input/maand_totalen.json, winst/input/shopify_sku_maand.json, data/kas-per-maand.json
Uitvoer: winst/winst-per-maand.json
"""
import json
from pathlib import Path

W = Path(__file__).resolve().parent
ROOT = W.parent

# Widem-tarieven 2026
INBOUND_PICK = 0.41 + 0.82   # per stuk
PACKING = 1.53               # per order
KLEIN = 1.30 + 7.07          # doos + DPD all-in (basis + brandstof-/security-/wegentoeslag, gem. BE/NL, Widem-specificatie jul–aug 2026)
GROOT = 1.55 + 7.07          # doos groot + DPD all-in
BOL_KOST_PCT = 45            # bol.com: geschatte kostprijs + fulfilment in % van netto uitbetaling (geen SKU-detail)

# vaste kosten uit de bankindeling; waarde = deler voor btw (1.21 = Belgische leverancier met btw)
VAST = {"Software & abonnementen": 1.0, "Boekhouder": 1.21, "Bankkosten": 1.0, "Verzekering": 1.0,
        "Administratie & lidmaatschappen": 1.0, "Materiaal": 1.21, "Representatie & reizen": 1.0,
        "Markten & events": 1.21, "Rente KBC-krediet": 1.0, "Personeel (student)": 1.21,
        "Marketing & content": 1.0, "Verzending & retours (overig)": 1.21, "Voorraad (verpakking & giveaways)": 1.21}


LIJNEN = ["FurVac", "Fonteinen", "Voerbakken", "Overig"]


def lijn(sku):
    s = sku.upper()
    if s.startswith(("FURVAC", "BASEUNIT", "NEEDLE", "DESHEDDING", "ANTI-STATIC", "MASSAGE", "2-1", "TRIMMER", "STACKING", "HEPA", "CARE")):
        return "FurVac"
    if s.startswith(("TK-WF", "WF315", "FF", "HB-", "JY-")):
        return "Fonteinen"
    if s.startswith(("PF0", "TT00", "DESBAG")) or s == "":
        return "Voerbakken"
    return "Overig"


def kost(tabel, sku, datum):
    t = tabel.get(sku)
    if not t:
        return None
    k = None
    for vanaf, waarde in t["kost"]:
        if datum >= vanaf:
            k = waarde
    return k


def main():
    tabel = json.loads((W / "kostprijzen.json").read_text())
    tot = json.loads((W / "input/maand_totalen.json").read_text())
    rows = json.loads((W / "input/shopify_sku_maand.json").read_text())
    kas = {m["maand"]: m for m in json.loads((ROOT / "data/kas-per-maand.json").read_text())["maanden"]}
    pct_onb = tabel.get("_onbekend_zonder_sku_pct", 50)
    bp = ROOT / "data/bol/overzicht.json"
    bol_api = {r["maand"]: r for r in json.loads(bp.read_text())["maanden"]} if bp.exists() else {}
    ean_sku = json.loads((W / "ean.json").read_text())
    wp = W / "input/widem_maand.json"
    widem = {k: v for k, v in json.loads(wp.read_text()).items() if not k.startswith("_")} if wp.exists() else {}

    per_maand, per_product, ontbreekt = {}, {}, set()
    for maand, sku, qty, net in rows:
        m = maand[:7]; qty = int(qty); net = float(net)
        d = per_maand.setdefault(m, {"cogs": 0.0, "stuks": 0, "groot": 0})
        midden = m + "-15"
        if sku == "":
            c = net * pct_onb / 100 if net > 0 else 0.0
            groot = True
        else:
            k = kost(tabel, sku, midden)
            if k is None:
                ontbreekt.add(sku); k = 0.0
            c = qty * k
            groot = tabel.get(sku, {}).get("groot", False)
        d["cogs"] += c
        if qty > 0:
            d["stuks"] += qty
            if groot:
                d["groot"] += qty
        L = d.setdefault("lijn", {k: {"omzet": 0.0, "kost": 0.0, "stuks": 0, "hoofd": 0} for k in LIJNEN})[lijn(sku)]
        L["omzet"] += net; L["kost"] += c
        if qty > 0:
            L["stuks"] += qty
            hoofd = groot or (sku or "").upper().startswith(("TK-WF", "WF315"))
            if hoofd:
                L["hoofd"] += qty
        p = per_product.setdefault(sku or "(oud, zonder SKU)", {"stuks": 0, "omzet": 0.0, "kostprijs": 0.0})
        p["stuks"] += qty; p["omzet"] += net; p["kostprijs"] += c

    ads_lijn = json.loads((W / "input/ads_lijn_maand.json").read_text())

    def bol_ful(m):
        b = bol_api.get(m)
        return (b["orders"] * (PACKING + KLEIN) + max(b.get("stuks", 0), 0) * INBOUND_PICK) if b else 0.0

    def ful_calc(i, m):
        d = per_maand.get(m, {"cogs": 0, "stuks": 0, "groot": 0}); o = tot["orders"][i]; g = min(o, d["groot"])
        return d["stuks"] * INBOUND_PICK + o * PACKING + g * GROOT + (o - g) * KLEIN

    # kalibratie: echte variabele Widem-kost (zonder opslag, admin, labeling, bol) ÷ berekend, laatste 3 gefactureerde maanden
    gef = [m for m in tot["maanden"] if m in widem][-3:]
    num = sum(widem[m]["totaal"] - widem[m]["storage"] - widem[m]["admin"] - widem[m].get("labeling", 0) - bol_ful(m) for m in gef)
    den = sum(ful_calc(tot["maanden"].index(m), m) for m in gef)
    KAL = round(num / den, 3) if den else 1.0
    laatste = widem[max(widem)] if widem else {"storage": 0, "admin": 0}
    uit, lijnen_tot = [], {k: {"omzet": 0.0, "kostprijs": 0.0, "fulfilment": 0.0, "betaalkosten": 0.0, "ads": 0.0, "stuks": 0} for k in LIJNEN}
    for i, m in enumerate(tot["maanden"]):
        d = per_maand.get(m, {"cogs": 0, "stuks": 0, "groot": 0})
        orders = tot["orders"][i]
        groot = min(orders, d["groot"])
        fulfil_calc = d["stuks"] * INBOUND_PICK + orders * PACKING + groot * GROOT + (orders - groot) * KLEIN
        # opslag + admin van Widem = vaste kost (gelijk per dag), niet per bestelling (afspraak 26/10)
        if m in widem:
            opslag_admin = widem[m]["storage"] + widem[m]["admin"]
            fulfil = max(0.0, widem[m]["totaal"] - bol_ful(m) - opslag_admin)
            ful_bron = f"Widem-factuur {widem[m]['factuur']} (excl. btw, zonder bol-orders, zonder opslag en admin)"
            oa_bron = f"Widem opslag + admin (factuur {widem[m]['factuur']})"
        else:
            opslag_admin = laatste["storage"] + laatste["admin"]
            fulfil = fulfil_calc * KAL
            ful_bron = f"raming: tarieven × {KAL} (gekalibreerd op de laatste Widem-facturen); opslag en admin bij de vaste kosten"
            oa_bron = "Widem opslag + admin (raming, tot de factuur er is)"
        ful_factor = fulfil / fulfil_calc if fulfil_calc else 1.0
        omzet_shop = tot["net_sales"][i] + tot["shipping"][i] / 1.21
        if m in bol_api:  # echte bol-data: omzet − commissie − andere bol-kosten; kostprijs per EAN
            b = bol_api[m]
            bol_net = b["omzet_incl"] / 1.21 - b["commissie"] - b.get("bol_ads", 0) - b.get("retourlabels", 0) - b.get("andere_kosten", 0)
            bol_kost = 0.0
            for ean, e in b["per_ean"].items():
                sku = ean_sku.get(str(ean).lstrip("0").zfill(13))
                k = kost(tabel, sku, m + "-15") if sku else None
                product = e["stuks"] * k if k is not None else max(e["omzet_incl"], 0) / 1.21 * .35  # onbekende (oude) EAN: 35% van omzet
                bol_kost += product + max(e["stuks"], 0) * INBOUND_PICK
            bol_kost += b["orders"] * (PACKING + KLEIN)
        else:  # raming uit de bankuitbetalingen
            bol_net = kas.get(m, {}).get("Omzet bol.com", 0) / 1.21
            bol_kost = bol_net * BOL_KOST_PCT / 100
        ads = tot["ads_meta"][i] + tot["ads_google"][i]
        fees = tot["betaalkosten"][i]
        vast_det = {k: round(-kas.get(m, {}).get(k, 0) / deler, 2) for k, deler in VAST.items() if kas.get(m, {}).get(k)}
        vast_det[oa_bron] = round(opslag_admin, 2)
        vast = sum(vast_det.values())
        brutomarge = omzet_shop - d["cogs"] - fulfil - fees + bol_net - bol_kost
        # per productlijn: fulfilment per stuk + orderkosten via 'hoofdproducten' (FurVac, voerbak, fontein); rest van de orders = losse filters/accessoires
        LL = d.get("lijn", {k: {"omzet": 0.0, "kost": 0.0, "stuks": 0, "hoofd": 0} for k in LIJNEN})
        hoofd_tot = sum(v["hoofd"] for v in LL.values())
        rest_orders = max(0, orders - hoofd_tot)
        omz_tot = sum(max(v["omzet"], 0) for v in LL.values()) or 1
        adsL = dict(ads_lijn.get(m, {}))
        alg = adsL.pop("Algemeen", 0) + tot["ads_google"][i] + (tot["ads_meta"][i] - sum(ads_lijn.get(m, {}).values()))
        if "Fonteinen & voerbakken" in adsL:
            fv = adsL.pop("Fonteinen & voerbakken"); o_f, o_v = max(LL["Fonteinen"]["omzet"], 0), max(LL["Voerbakken"]["omzet"], 0)
            adsL["Fonteinen"] = adsL.get("Fonteinen", 0) + fv * (o_f / (o_f + o_v) if o_f + o_v else .5)
            adsL["Voerbakken"] = adsL.get("Voerbakken", 0) + fv * (o_v / (o_f + o_v) if o_f + o_v else .5)
        for k, v in LL.items():
            orders_k = min(v["hoofd"], orders) + (rest_orders if k == "Fonteinen" else 0)
            per_order = PACKING + (GROOT if k in ("FurVac", "Voerbakken") else KLEIN)
            T = lijnen_tot[k]
            T["omzet"] += v["omzet"]; T["kostprijs"] += v["kost"]; T["stuks"] += v["stuks"]
            T["fulfilment"] += (v["stuks"] * INBOUND_PICK + orders_k * per_order) * ful_factor
            T["betaalkosten"] += fees * max(v["omzet"], 0) / omz_tot
            T["ads"] += adsL.get(k, 0) + alg * max(v["omzet"], 0) / omz_tot
        resultaat = brutomarge - ads - vast
        uit.append({
            "maand": m, "orders": orders, "stuks": d["stuks"],
            "omzet_shopify": round(omzet_shop, 2), "omzet_bol": round(bol_net, 2),
            "bol": ({"bron": "bol-API", "orders": bol_api[m]["orders"], "stuks": bol_api[m]["stuks"], "omzet_incl": bol_api[m]["omzet_incl"],
                     "commissie": bol_api[m]["commissie"], "bol_ads": bol_api[m].get("bol_ads", 0), "retourlabels": bol_api[m].get("retourlabels", 0),
                     "kostprijs_fulfilment": round(bol_kost, 2), "bijdrage": round(bol_net - bol_kost, 2)} if m in bol_api else
                    {"bron": "raming uit bankuitbetalingen", "omzet_netto": round(bol_net, 2), "kostprijs_fulfilment": round(bol_kost, 2), "bijdrage": round(bol_net - bol_kost, 2)}),
            "korting": round(-tot["discounts"][i], 2), "retours": round(-tot["returns"][i], 2),
            "kostprijs": round(d["cogs"] + bol_kost, 2), "fulfilment": round(fulfil, 2), "fulfilment_bron": ful_bron, "fulfilment_widem": widem.get(m), "betaalkosten": round(fees, 2),
            "brutomarge": round(brutomarge, 2), "ads_meta": tot["ads_meta"][i], "ads_google": tot["ads_google"][i],
            "vaste_kosten": round(vast, 2), "vaste_detail": vast_det, "resultaat": round(resultaat, 2),
            "roas": round(tot["total_sales"][i] / ads, 2) if ads else None,
            "trueprofit": tot["trueprofit_netto"][i], "verschil_tp": round(resultaat - tot["trueprofit_netto"][i], 2),
        })
    prod = [{"sku": k, "stuks": v["stuks"], "omzet": round(v["omzet"], 2), "kostprijs": round(v["kostprijs"], 2),
             "marge_voor_fulfilment": round(v["omzet"] - v["kostprijs"], 2)} for k, v in per_product.items()]
    prod.sort(key=lambda x: -x["omzet"])
    lijnen = []
    for k, T in lijnen_tot.items():
        if not T["stuks"] and not T["omzet"]:
            continue
        voor_ads = T["omzet"] - T["kostprijs"] - T["fulfilment"] - T["betaalkosten"]
        lijnen.append({"lijn": k, "stuks": T["stuks"], "omzet": round(T["omzet"], 2), "kostprijs": round(T["kostprijs"], 2),
                       "fulfilment": round(T["fulfilment"], 2), "betaalkosten": round(T["betaalkosten"], 2),
                       "marge_voor_ads": round(voor_ads, 2), "ads": round(T["ads"], 2), "na_ads": round(voor_ads - T["ads"], 2),
                       "roas_nodig": round(T["omzet"] * 1.21 / voor_ads, 2) if voor_ads > 0 else None,
                       "roas": round(T["omzet"] * 1.21 / T["ads"], 2) if T["ads"] else None})
    out = {"maanden": uit, "lijnen": lijnen, "producten": prod, "ontbrekende_kostprijs": sorted(ontbreekt),
           "aannames": [f"Fulfilment = echte Widem-maandfactuur (verbruiksmateriaal, pick & pack, pakjes, labeling) waar die er is; anders Widem-tarieven (€{INBOUND_PICK:.2f}/stuk, €{PACKING}/order, doos+DPD €{KLEIN:.2f}/€{GROOT:.2f}) × {KAL}. Opslag en admin van Widem staan bij de vaste kosten (gelijk per dag; raming tot de factuur er is, daarna gecorrigeerd).",
                        f"Oude producten zonder SKU (feeders okt 2025–feb 2026): kostprijs {pct_onb}% van de omzet.",
                        f"bol.com: netto uitbetaling ÷ 1,21; kostprijs + fulfilment geschat op {BOL_KOST_PCT}%.",
                        "Vaste kosten = echte bankuitgaven per categorie (zonder Meta/Google, die apart tellen; zonder kantoor, dat Creazy betaalt).",
                        "Retourkosten (transport + afhandeling) nog niet meegeteld."]}
    (W / "winst-per-maand.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    t = lambda k: round(sum(r[k] for r in uit), 0)
    for l in lijnen:
        print(l)
    print("resultaat", t("resultaat"), "trueprofit", t("trueprofit"), "ontbreekt", sorted(ontbreekt))
    for r in uit:
        print(r["maand"], r["omzet_shopify"], r["omzet_bol"], r["kostprijs"], r["fulfilment"], r["betaalkosten"], r["ads_meta"] + r["ads_google"], r["vaste_kosten"], "→", r["resultaat"], "| TP", r["trueprofit"])


if __name__ == "__main__":
    main()
