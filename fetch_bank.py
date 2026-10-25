"""Haalt saldi en verrichtingen op bij Ponto (KBC) en Revolut Business en schrijft ze naar data/.

Draait elke nacht in GitHub Actions. Alle sleutels komen uit GitHub-secrets (omgevingsvariabelen),
nooit uit dit bestand. Alleen-lezen: dit script kan geen betalingen doen.
"""
import base64, hashlib, json, os, subprocess, sys, tempfile, time, uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

DATA = Path("data")
DATA.mkdir(exist_ok=True)
SINCE = (date.today() - timedelta(days=int(os.environ.get("DAYS_BACK", "10")))).isoformat()
log = lambda *a: print(*a, file=sys.stderr)


def save_secret(name, value):
    """Schrijf een nieuwe waarde terug naar een GitHub-secret (voor roterende refresh tokens)."""
    if not os.environ.get("GH_TOKEN"):
        log(f"GH_TOKEN ontbreekt: kan {name} niet bijwerken")
        return
    subprocess.run(["gh", "secret", "set", name, "--body", value], check=True)


def merge(path, new_rows, key="id"):
    """Voeg nieuwe verrichtingen toe aan een bestand zonder dubbels."""
    old = json.loads(path.read_text()) if path.exists() else []
    seen = {r[key]: r for r in old}
    for r in new_rows:
        seen[r[key]] = r
    rows = sorted(seen.values(), key=lambda r: (r["datum"], r[key]), reverse=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    return len(rows) - len(old)


# ---------------- Ponto (KBC) ----------------
def ponto():
    cid, secret = os.environ.get("PONTO_CLIENT_ID"), os.environ.get("PONTO_CLIENT_SECRET")
    if not cid:
        log("Ponto: geen PONTO_CLIENT_ID, overgeslagen")
        return [], []
    # Eigen (custom) integratie in Ponto: api.myponto.com, geen certificaat nodig.
    # Ibanity-partnerapplicatie: api.ibanity.com/ponto-connect met mTLS-certificaat.
    base = os.environ.get("PONTO_BASE") or (
        "https://api.ibanity.com/ponto-connect" if os.environ.get("PONTO_CERT") else "https://api.myponto.com")
    cert = None
    if os.environ.get("PONTO_CERT"):
        d = tempfile.mkdtemp()
        Path(d, "c.pem").write_text(os.environ["PONTO_CERT"])
        Path(d, "k.pem").write_text(os.environ["PONTO_KEY"])
        cert = (str(Path(d, "c.pem")), str(Path(d, "k.pem")))
        # versleutelde sleutel: ontsleutel met openssl
        if os.environ.get("PONTO_KEY_PASSPHRASE"):
            subprocess.run(["openssl", "pkey", "-in", cert[1], "-out", cert[1] + ".plain",
                            "-passin", "env:PONTO_KEY_PASSPHRASE"], check=True)
            cert = (cert[0], cert[1] + ".plain")
    s = requests.Session()
    s.cert = cert
    auth = (cid, secret)
    rt = os.environ.get("PONTO_REFRESH_TOKEN")
    if rt:
        r = s.post(f"{base}/oauth2/token", auth=auth,
                   data={"grant_type": "refresh_token", "refresh_token": rt})
        r.raise_for_status()
        tok = r.json()
        if tok.get("refresh_token") and tok["refresh_token"] != rt:
            save_secret("PONTO_REFRESH_TOKEN", tok["refresh_token"])  # tokens zijn eenmalig
    else:
        r = s.post(f"{base}/oauth2/token", auth=auth, data={"grant_type": "client_credentials"})
        r.raise_for_status()
        tok = r.json()
    s.headers["Authorization"] = f"Bearer {tok['access_token']}"
    s.headers["Accept"] = "application/vnd.api+json"

    acc = s.get(f"{base}/accounts", params={"page[limit]": 100})
    acc.raise_for_status()
    rows, balances = [], []
    for a in acc.json()["data"]:
        at = a["attributes"]
        naam = at.get("description") or at.get("reference")
        balances.append({"bron": "KBC (Ponto)", "rekening": naam, "iban": at.get("reference"),
                         "saldo": at.get("currentBalance"), "beschikbaar": at.get("availableBalance"),
                         "munt": at.get("currency"), "bijgewerkt_bank": at.get("synchronizedAt")})
        url = f"{base}/accounts/{a['id']}/transactions"
        params = {"page[limit]": 100}
        while url:
            r = s.get(url, params=params)
            r.raise_for_status()
            j = r.json()
            stop = False
            for t in j["data"]:
                ta = t["attributes"]
                d = (ta.get("executionDate") or ta.get("valueDate") or "")[:10]
                if d < SINCE:
                    stop = True
                    continue
                rows.append({"id": "ponto-" + t["id"], "bron": "KBC", "rekening": naam, "datum": d,
                             "bedrag": float(ta["amount"]), "munt": ta.get("currency", "EUR"),
                             "tegenpartij": ta.get("counterpartName") or "",
                             "tegenrekening": ta.get("counterpartReference") or "",
                             "mededeling": ta.get("remittanceInformation") or ta.get("description") or "",
                             "soort": ta.get("bankTransactionCode") or ""})
            nxt = j.get("links", {}).get("next")
            url, params = (None if stop else nxt), None
    return rows, balances


# ---------------- Revolut Business ----------------
def revolut():
    cid = os.environ.get("REVOLUT_CLIENT_ID")
    if not cid:
        log("Revolut: geen REVOLUT_CLIENT_ID, overgeslagen")
        return [], []
    import jwt  # PyJWT
    now = int(time.time())
    assertion = jwt.encode({"iss": os.environ["REVOLUT_ISS"], "sub": cid,
                            "aud": "https://revolut.com", "exp": now + 300},
                           os.environ["REVOLUT_PRIVATE_KEY"], algorithm="RS256")
    base = "https://b2b.revolut.com/api/1.0"
    r = requests.post(f"{base}/auth/token", data={
        "grant_type": "refresh_token", "refresh_token": os.environ["REVOLUT_REFRESH_TOKEN"],
        "client_id": cid, "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": assertion})
    r.raise_for_status()
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    balances = [{"bron": "Revolut", "rekening": a.get("name"), "saldo": a.get("balance"),
                 "munt": a.get("currency"), "bijgewerkt_bank": a.get("updated_at")}
                for a in requests.get(f"{base}/accounts", headers=h).json()]
    tx = requests.get(f"{base}/transactions", headers=h,
                      params={"from": SINCE, "count": 1000}).json()
    rows = []
    for t in tx:
        for leg in t.get("legs", []):
            rows.append({"id": f"rev-{t['id']}-{leg.get('leg_id')}", "bron": "Revolut",
                         "rekening": leg.get("currency"), "datum": (t.get("completed_at") or t["created_at"])[:10],
                         "bedrag": float(leg["amount"]), "munt": leg.get("currency"),
                         "tegenpartij": (leg.get("counterparty") or {}).get("name") or (t.get("merchant") or {}).get("name") or "",
                         "tegenrekening": "", "mededeling": t.get("reference") or leg.get("description") or "",
                         "soort": t.get("type", ""), "status": t.get("state")})
    return rows, balances


def main():
    all_rows, all_bal, fouten = [], [], []
    for naam, fn in (("Ponto", ponto), ("Revolut", revolut)):
        try:
            res = fn()
            if res and isinstance(res, tuple):
                all_rows += res[0]
                all_bal += res[1]
        except Exception as e:  # één bron mag de andere niet tegenhouden
            fouten.append(f"{naam}: {type(e).__name__}: {str(e)[:300]}")
            log(fouten[-1])
    per_maand = {}
    for r in all_rows:
        per_maand.setdefault(r["datum"][:7], []).append(r)
    nieuw = sum(merge(DATA / f"transacties-{m}.json", rows) for m, rows in per_maand.items())
    status = {"opgehaald": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "vanaf": SINCE, "nieuwe_verrichtingen": nieuw, "saldi": all_bal, "fouten": fouten}
    (DATA / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1))
    log(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
