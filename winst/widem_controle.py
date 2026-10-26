"""Controle van elke Widem-maandfactuur: klopt wat ze aanrekenen met wat we verstuurden?

Per maand: verwacht bedrag per factuurregel op basis van orders en stuks (Shopify + bol) × Widem-tarieven,
naast het gefactureerde bedrag. Een regel wordt gemarkeerd als hij meer dan 10 % én meer dan €15 boven de
verwachting ligt, of als een vaste post (admin, opslag) verandert zonder dat we weten waarom.

Let op: Shopify-orders = besteld, niet verzonden. Pre-orders en geannuleerde orders verschuiven tussen maanden,
dus een afwijking is een vraag, geen bewijs. Daarom altijd eerst de verzendlijst/CSV van Widem opvragen.

Gebruik: python winst/widem_controle.py → winst/widem_controle.json
"""
import json
from pathlib import Path

W = Path(__file__).resolve().parent
PICK, PACK = 0.82, 1.53            # per stuk / per order
DOOS = (1.30, 1.55)                # klein / groot
DPD = (6.99, 8.78)                 # all-in per pakje (basis + brandstof-, security- en wegentoeslag), BE / NL, stand juli–aug 2026
ADMIN, MARGE_PCT, MARGE_EUR = 75.0, 0.10, 15.0


def main():
    widem = {k: v for k, v in json.loads((W / "input/widem_maand.json").read_text()).items() if not k.startswith("_")}
    sp_pad = W / "input/widem_spec.json"
    spec = json.loads(sp_pad.read_text()) if sp_pad.exists() else {}
    wm = {r["maand"]: r for r in json.loads((W / "winst-per-maand.json").read_text())["maanden"]}
    uit, vorige = [], None
    for m in sorted(widem):
        f, r = widem[m], wm.get(m, {})
        b = r.get("bol") or {}
        sp = spec.get(m)  # Widem-specificatie (Invoicing SmartPaw <maand>.xlsx): echt verzonden orders/stuks
        orders = sp["orders"] if sp else (r.get("orders") or 0) + (b.get("orders") or 0)
        stuks = sp["stuks"] if sp else (r.get("stuks") or 0) + (b.get("stuks") or 0)
        verwacht = {
            "pick_pack": (stuks * PICK + orders * PACK, stuks * PICK + orders * PACK),
            "parcels": (orders * DPD[0], orders * DPD[1]),
            "consumables": (orders * DOOS[0], orders * DOOS[1]),
            "admin": (ADMIN, ADMIN),
        }
        regels, vlaggen = [], []
        for k, (lo, hi) in verwacht.items():
            g = f.get(k, 0) or 0
            over = g - hi
            vlag = over > MARGE_EUR and over > hi * MARGE_PCT
            regels.append({"regel": k, "gefactureerd": round(g, 2), "verwacht_min": round(lo, 2), "verwacht_max": round(hi, 2),
                           "verschil": round(over if over > 0 else min(0, g - lo), 2), "vlag": vlag})
            if vlag:
                vlaggen.append(f"{k}: €{g:.2f} gefactureerd, verwacht max €{hi:.2f} (+€{over:.2f})")
        if vorige and f.get("storage") != widem[vorige].get("storage"):
            pass  # opslag volgt de hoeveelheid stock (afspraak 26/10): geen vlag, enkel tonen
        f_info = []
        if vorige and f.get("storage") != widem[vorige].get("storage"):
            f_info.append(f"opslag €{widem[vorige]['storage']:.2f} → €{f['storage']:.2f} (meer/minder stock)")
        if f.get("labeling"):
            f_info.append(f"labeling €{f['labeling']:.2f} (eenmalig, nieuwe zending)")
        som = sum((f.get(k) or 0) for k in ("storage", "consumables", "inbound", "pick_pack", "admin", "parcels", "labeling"))
        if abs(som - f["totaal"]) > 0.05:
            vlaggen.append(f"regels tellen op tot €{som:.2f}, factuur zegt €{f['totaal']:.2f}")
        uit.append({"maand": m, "factuur": f["factuur"], "orders": orders, "stuks": stuks, "bron_aantallen": "Widem-specificatie" if sp else "Shopify + bol (besteld)", "totaal": f["totaal"],
                    "regels": regels, "vlaggen": vlaggen, "info": f_info, "status": "nakijken" if vlaggen else "ok"})
        vorige = m
    out = {"uitleg": __doc__.strip().splitlines()[0], "maanden": uit}
    (W / "widem_controle.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for u in uit:
        print(u["maand"], u["factuur"], u["orders"], "orders", u["stuks"], "stuks", "€", u["totaal"], u["status"])
        for v in u["vlaggen"]: print("   -", v)


if __name__ == "__main__":
    main()
