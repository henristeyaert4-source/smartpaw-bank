"""Haalt openstaande leveranciersfacturen (crediteuren) en klantfacturen (debiteuren) op uit Yuki.

Alleen-lezen. Secret YUKI_ACCESS_KEY (Yuki → Instellingen → Web services → API-sleutel met rechten op Accounting),
optioneel YUKI_ADMIN_ID (anders de eerste administratie). Facturen die via Peppol/Lucy binnenkomen, staan in Yuki.

Uitvoer: data/yuki/openstaand.json {crediteuren[], debiteuren[], opgehaald, fouten[]}
"""
import json, os, sys
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

D = Path("data/yuki"); D.mkdir(parents=True, exist_ok=True)
NS = "http://www.theyukicompany.com/"
HOSTS = ["https://api.yukiworks.be/ws", "https://api.yukiworks.nl/ws"]
log = lambda *a: print(*a, file=sys.stderr)


def soap(base, service, method, **params):
    body = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())
    env = (f'<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
           f'<soap:Body><{method} xmlns="{NS}">{body}</{method}></soap:Body></soap:Envelope>')
    r = requests.post(f"{base}/{service}.asmx", data=env.encode(), timeout=60,
                      headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{NS}{method}"'})
    if r.status_code >= 400:
        raise RuntimeError(f"{method}: HTTP {r.status_code} {r.text[:300]}")
    root = ET.fromstring(r.content)
    res = root.find(f".//{{{NS}}}{method}Result")
    return res


def tekst(el, tag):
    x = el.find(tag)
    if x is None:
        x = el.find(f"{{{NS}}}{tag}")
    return (x.text or "").strip() if x is not None and x.text else ""


def items(res):
    """Resultaat kan XML als tekst bevatten of als kinderen."""
    if res is None:
        return []
    if res.text and res.text.strip().startswith("<"):
        res = ET.fromstring(res.text)
    out = []
    for it in res.iter():
        if it.tag.split("}")[-1] == "Item":
            g = lambda t: tekst(it, t)
            out.append({"id": it.get("ID"), "datum": g("Date")[:10], "vervaldag": g("DueDate")[:10],
                        "contact": g("Contact"), "omschrijving": g("Description"), "referentie": g("Reference"),
                        "open": float(g("OpenAmount") or 0), "origineel": float(g("OriginalAmount") or 0),
                        "betaalwijze": g("PaymentMethod")})
    return out


def main():
    key = os.environ.get("YUKI_ACCESS_KEY")
    if not key:
        log("yuki: geen YUKI_ACCESS_KEY, overgeslagen"); return
    st = {"fouten": [], "opgehaald": date.today().isoformat()}
    for base in HOSTS:
        try:
            sess = soap(base, "Accounting", "Authenticate", accessKey=key).text
            admin = os.environ.get("YUKI_ADMIN_ID")
            if not admin:
                res = soap(base, "Accounting", "Administrations", sessionID=sess)
                xml = ET.fromstring(res.text) if res is not None and res.text and res.text.strip().startswith("<") else res
                adm = [a for a in xml.iter() if a.tag.split("}")[-1] == "Administration"]
                st["administraties"] = [{"id": a.get("ID"), "naam": tekst(a, "Name")} for a in adm]
                admin = adm[0].get("ID")
            for soort, method in (("crediteuren", "OutstandingCreditorItems"), ("debiteuren", "OutstandingDebtorItems")):
                laatste = None
                for sort in ("DateAsc", "Date", "Contact"):
                    try:
                        st[soort] = items(soap(base, "AccountingInfo", method, sessionID=sess, administrationID=admin,
                                                includeBankTransactions="false", sortOrder=sort))
                        break
                    except Exception as e:
                        laatste = e
                else:
                    raise laatste
            st["host"] = base
            break
        except Exception as e:
            st["fouten"].append(f"{base}: {type(e).__name__}: {str(e)[:300]}")
    if st.get("host"):
        st["fouten"] = []
    (D / "openstaand.json").write_text(json.dumps(st, ensure_ascii=False, indent=1))
    log(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in st.items()}))


if __name__ == "__main__":
    main()
