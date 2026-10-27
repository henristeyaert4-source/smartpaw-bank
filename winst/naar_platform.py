"""Zet winst/winst-per-maand.json en winst/dagen.json om naar de platform-documenten fin/maanden, fin/lijnen en fin/dagen.

Gebruik: python winst/naar_platform.py <huidige fin/maanden.json> <uitmap>
Bewaart 'bronnen' en 'let_op' uit het huidige fin/maanden-document; rente staat apart van de vaste kosten.
"""
import json, sys, datetime as dt
from pathlib import Path

W = Path(__file__).resolve().parent


def eur(v):
    return "€" + f"{v:,.0f}".replace(",", ".")


def _kort(iso):
    m = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
    y, mm, d = iso.split("-")
    return f"{int(d)} {m[int(mm) - 1]} {y}"


def main(huidig, uit):
    w = json.loads((W / "winst-per-maand.json").read_text())
    oud = json.loads(Path(huidig).read_text())
    oud = oud.get("data", oud)
    rijen = []
    for r in w["maanden"]:
        det = dict(r.get("vaste_detail") or {})
        rente = det.pop("Rente KBC-krediet", 0.0)
        rij = {"maand": r["maand"], "orders": r["orders"], "omzet_shopify": r["omzet_shopify"], "omzet_bol": r["omzet_bol"],
               "omzet": round(r["omzet_shopify"] + (r["omzet_bol"] or 0), 2), "korting": r["korting"], "cogs": r["kostprijs"],
               "fulfilment": r["fulfilment"], "fulfilment_bron": r["fulfilment_bron"], "ads": round(r["ads_meta"] + r["ads_google"], 2),
               "betaalkosten": r["betaalkosten"], "vaste_kosten": round(sum(det.values()), 2),
               "vaste_bron": "bankuitgaven per categorie + Widem opslag/admin: " + ", ".join(f"{k} {eur(v)}" for k, v in det.items()),
               "vaste_detail": det, "rente": round(rente, 2), "resultaat": r["resultaat"], "trueprofit": r.get("trueprofit"), "bol": r.get("bol")}
        if r.get("fulfilment_widem"):
            rij["fulfilment_widem"] = r["fulfilment_widem"]
        rijen.append(rij)
    bronnen = oud.get("bronnen", "").replace("Fulfilment: Widem-tarieven per stuk en per order (klein/groot pakket).",
                                             "Fulfilment: echte Widem-factuur (pick & pack, pakjes, dozen, labeling) of tarieven tot de factuur er is. Widem opslag + admin bij de vaste kosten.")
    maanden = {"rijen": rijen, "bronnen": bronnen, "let_op": oud.get("let_op", []), "bron_motor": oud.get("bron_motor", ""),
               "bijgewerkt": dt.date.today().isoformat()}
    lijnen = {"lijnen": w["lijnen"], "producten": w["producten"], "aannames": w["aannames"], "periode": "okt 2025 – " + _kort(json.loads((W / "dagen.json").read_text())["tot"]),
              "bijgewerkt": dt.date.today().isoformat()}
    dagen = json.loads((W / "dagen.json").read_text())
    u = Path(uit); u.mkdir(parents=True, exist_ok=True)
    (u / "maanden.json").write_text(json.dumps(maanden, ensure_ascii=False))
    (u / "lijnen.json").write_text(json.dumps(lijnen, ensure_ascii=False))
    (u / "dagen.json").write_text(json.dumps(dagen, ensure_ascii=False))
    print(len(rijen), "maanden;", rijen[-1]["maand"], rijen[-1]["vaste_bron"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
