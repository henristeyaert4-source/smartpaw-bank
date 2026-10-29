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
                if any(re.search(pat, str(v), re.I) for v in m.values()):
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
    main()
