"""Document in Yuki zetten (Archive.UploadDocumentWithData). Eerst enkel tonen wat de sleutel ziet (mappen, betaalwijzen).

Gebruik (in de GitHub Action, secrets YUKI_ACCESS_KEY / YUKI_ADMIN_ID):
  python yuki_upload.py kijk                       → mappen en betaalwijzen tonen, niets opladen
  python yuki_upload.py oplaad <pdf> <bedrag> <betaalwijze-woord> "<opmerking>"
Resultaat in data/yuki/upload_log.json (geen inhoud van het document).
"""
import base64, json, os, re, sys
from datetime import datetime
from pathlib import Path
from fetch_yuki import soap, HOSTS, NS

LOG = Path("data/yuki/upload_log.json")


def kinderen(res):
    """Elk element met een ID/naam als dict (alle niveaus): {tag, attrib..., tekst, kinderen-tekst}."""
    import xml.etree.ElementTree as ET
    if res is None:
        return []
    if res.text and res.text.strip().startswith("<"):
        res = ET.fromstring(res.text)
    out = []
    for it in res.iter():
        if it is res:
            continue
        d = {"_tag": it.tag.split('}')[-1], **it.attrib}
        if (it.text or "").strip():
            d["_tekst"] = it.text.strip()
        for c in it:
            if (c.text or "").strip() and not len(c):
                d[c.tag.split('}')[-1]] = c.text.strip()
        if len(d) > 1:
            out.append(d)
    return out


def wachtrij():
    """Stuur nieuwe 'te boeken'-documenten naar Yuki (één keer per pdf)."""
    B = Path("boekhouding"); N = B / "naar_yuki"
    inst = json.loads((N / "instellingen.json").read_text())
    verz = json.loads((N / "verzonden.json").read_text())
    groepen = {}
    for f in sorted((B / "dagboek").glob("aankoop_*.json")):
        for l in json.loads(f.read_text())["lijnen"]:
            a = l.get("asset_id")
            if l["status"] != "te boeken" or not a or a in verz or not (N / "pdf" / f"{a}.pdf").exists():
                continue
            if l["betaald_op"] < inst["vanaf"] and l["id"] not in inst["ook_versturen"]:
                continue
            g = groepen.setdefault(a, {"regels": [], "bedrag": 0.0, "l": l})
            g["regels"].append(l["id"]); g["bedrag"] = round(g["bedrag"] + l["incl"], 2)
    if not groepen:
        print("niets te versturen"); return
    key, admin = os.environ["YUKI_ACCESS_KEY"], os.environ.get("YUKI_ADMIN_ID", "")
    base = HOSTS[0]
    sess = soap(base, "Archive", "Authenticate", accessKey=key).text
    for a, g in groepen.items():
        l = g["l"]
        opm = (f"{l['leverancier']} {l['factuurnummer']} – {l['omschrijving'] or l['document']}. "
               f"Betaald {l['betaald_op']} via {l['betaald_via_naam']}. Voorstel: rekening {l['rekening']} {l['rekening_naam']}, btw {l['btw_uitleg']}. "
               f"Verstuurd door het SmartPaw-platform.")[:1000]
        try:
            res = soap(base, "Archive", "UploadDocumentWithData", sessionID=sess, fileName=f"{l['factuurdatum']}_{re.sub(r'[^A-Za-z0-9]+', '-', l['leverancier'])[:30]}_{g['bedrag']:.2f}.pdf",
                       data=base64.b64encode((N / "pdf" / f"{a}.pdf").read_bytes()).decode(), folder=inst["map_aankoop"], administrationID=admin,
                       currency="EUR", amount=f"{g['bedrag']:.2f}", costCategory="", paymentMethod=inst["betaalwijze"].get(l["betaald_via"], 4),
                       project="", remarks=opm.replace("&", "en").replace("<", "").replace(">", ""))
            doc = (res.text or "").strip() if res is not None else ""
            if not re.fullmatch(r"[0-9a-f-]{36}", doc):
                raise RuntimeError(f"onverwacht antwoord: {doc[:120]}")
            verz[a] = {"yuki_document": doc, "op": datetime.now().date().isoformat(), "regels": g["regels"], "bedrag": g["bedrag"],
                       "map": inst["map_aankoop"], "betaalwijze": inst["betaalwijze"].get(l["betaald_via"], 4)}
            print("verstuurd", l["leverancier"], g["bedrag"], doc)
        except Exception as e:
            print("MISLUKT", l["leverancier"], g["bedrag"], str(e)[:200])
        (N / "verzonden.json").write_text(json.dumps(verz, ensure_ascii=False, indent=1))


def lees():
    """Leestest: recente documenten in de map Aankoop en wat er per document uit te halen is (geen inhoud bewaren)."""
    from datetime import timedelta
    key = os.environ["YUKI_ACCESS_KEY"]; base = HOSTS[0]
    sess = soap(base, "Archive", "Authenticate", accessKey=key).text
    t = datetime.now()
    res = soap(base, "Archive", "DocumentsInFolder", sessionID=sess, folderID=1, startDate=(t - timedelta(days=40)).strftime("%Y-%m-%dT00:00:00"),
               endDate=t.strftime("%Y-%m-%dT23:59:59"), numberOfRecords=10, startRecord=0)
    docs = [d for d in kinderen(res) if "ID" in d]
    print("documenten:", len(docs)); print(json.dumps(docs[:3], ensure_ascii=False)[:1500])
    for d in docs[:2]:
        for m in ("DocumentXMLDataAsString", "DocumentDownloadUrl"):
            try:
                r = soap(base, "Archive", m, sessionID=sess, documentID=d["ID"])
                txt = (r.text or "") if r is not None else ""
                print(m, len(txt), "IBAN" if re.search(r"\bBE\d{2}\s?\d{4}", txt) else "-", "OGM" if re.search(r"\d{3}/\d{4}/\d{5}|PaymentID", txt) else "-", txt[:80] if m.endswith("Url") else "")
            except Exception as e:
                print(m, "FOUT", str(e)[:150])


def betaalinfo():
    """Rekeningnummer + gestructureerde mededeling uit de factuur-pdf's in Yuki (map Aankoop) voor openstaande facturen.
    → data/yuki/betaalgegevens.json {referentie: {contact, iban, ogm, bedrag, datum}}. De pdf's zelf worden niet bewaard."""
    import io, requests
    from datetime import timedelta
    from pypdf import PdfReader
    D = Path("data/yuki"); uit_p = D / "betaalgegevens.json"
    bekend = json.loads(uit_p.read_text()) if uit_p.exists() else {}
    open_ = {c.get("referentie"): c for c in json.loads((D / "openstaand.json").read_text()).get("crediteuren", [])
             if (c.get("open") or 0) > 0 and c.get("referentie")}
    key = os.environ["YUKI_ACCESS_KEY"]; base = HOSTS[0]
    sess = soap(base, "Archive", "Authenticate", accessKey=key).text
    t = datetime.now(); docs = []
    for start in range(0, 600, 100):
        res = soap(base, "Archive", "DocumentsInFolder", sessionID=sess, folderID=1, startDate=(t - timedelta(days=150)).strftime("%Y-%m-%dT00:00:00"),
                   endDate=t.strftime("%Y-%m-%dT23:59:59"), numberOfRecords=100, startRecord=start)
        deel = [d for d in kinderen(res) if d.get("_tag") == "Document"]
        docs += deel
        if len(deel) < 100:
            break
    n = 0
    for d in docs:
        ref = d.get("Reference", "")
        hit = next((r for r in open_ if r and (r == ref or re.sub(r"\D", "", r) == re.sub(r"\D", "", ref) != "")), None)
        if not hit or (hit in bekend and bekend[hit].get("iban")):
            continue
        try:
            url = (soap(base, "Archive", "DocumentDownloadUrl", sessionID=sess, documentID=d["ID"]).text or "").strip()
            inhoud = requests.get(url, timeout=60).content
            if inhoud.lstrip()[:5] in (b"<?xml", b"<Invo"):  # Peppol/UBL
                x = inhoud.decode("utf-8", "ignore")
                acc = re.search(r"PayeeFinancialAccount>.*?<cbc:ID[^>]*>([^<]+)<", x, re.S)
                pid = re.search(r"<cbc:PaymentID[^>]*>([^<]+)<", x)
                txt = (f"{acc.group(1)} " if acc else "") + (f"+++{re.sub(r'[^0-9]', '', pid.group(1))[:3]}/{re.sub(r'[^0-9]', '', pid.group(1))[3:7]}/{re.sub(r'[^0-9]', '', pid.group(1))[7:12]}+++" if pid and len(re.sub(r'[^0-9]', '', pid.group(1))) == 12 else "")
            else:
                txt = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(inhoud)).pages)
        except Exception as e:
            print("niet gelezen", ref, str(e)[:120]); continue
        ibans = [i.replace(" ", "") for i in re.findall(r"\bBE\d{2}(?: ?\d{4}){3}\b|\bBE\d{14}\b", txt)]
        ibans = [i for i in ibans if i not in ("BE84731070760259",)]  # eigen KBC-rekening
        og = re.search(r"[+*]{3}\s?(\d{3})\s?/\s?(\d{4})\s?/\s?(\d{5})\s?[+*]{3}", txt)
        bekend[hit] = {"contact": open_[hit]["contact"], "iban": ibans[0] if ibans else None,
                       "ogm": "".join(og.groups()) if og else None, "bedrag": open_[hit]["open"], "datum": open_[hit]["datum"], "yuki_document": d["ID"]}
        n += 1
    uit_p.write_text(json.dumps(bekend, ensure_ascii=False, indent=1))
    print(f"{len(docs)} documenten bekeken, {n} nieuwe betaalgegevens")
    for k, v in bekend.items():
        print(k, v["contact"], v["iban"], v["ogm"])


def main():
    key, admin = os.environ["YUKI_ACCESS_KEY"], os.environ.get("YUKI_ADMIN_ID", "")
    base = HOSTS[0]
    sess = soap(base, "Archive", "Authenticate", accessKey=key).text
    uit = {"op": datetime.now().isoformat(timespec="seconds"), "actie": sys.argv[1]}
    mappen = kinderen(soap(base, "Archive", "DocumentFolders", sessionID=sess))
    betaal = kinderen(soap(base, "Archive", "PaymentMethods", sessionID=sess))
    uit["mappen"], uit["betaalwijzen"] = mappen, betaal
    print(json.dumps(uit, ensure_ascii=False, indent=1))
    if sys.argv[1] == "oplaad":
        pdf, bedrag, bw, opm = Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
        def zoek(lijst, pat):
            for m in lijst:
                if "ID" in m and re.search(pat, m.get("Description", ""), re.I):
                    return next((m[k] for k in ("ID", "Id", "id") if k in m), None)
        folder = zoek(mappen, r"aankoop|inkoop|purchase")
        pm = zoek(betaal, bw)
        res = soap(base, "Archive", "UploadDocumentWithData", sessionID=sess, fileName=pdf.name,
                   data=base64.b64encode(pdf.read_bytes()).decode(), folder=folder or 1, administrationID=admin,
                   currency="EUR", amount=bedrag, costCategory="", paymentMethod=pm or 0, project="", remarks=opm)
        uit["upload"] = {"bestand": pdf.name, "map": folder, "betaalwijze": pm, "antwoord": (res.text or "")[:300] if res is not None else None}
        print(json.dumps(uit["upload"], ensure_ascii=False))
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    log.append(uit); LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"wachtrij": wachtrij, "lees": lees, "betaalinfo": betaalinfo}.get(sys.argv[1], main)()
