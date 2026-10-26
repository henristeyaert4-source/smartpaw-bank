# SmartPaw Financiën — platform en database

Platform: https://claude.ai/artifact/W6M6FXVEXUvts8ntwJCa8A (capabilities db + mcp + assets + downloads; bij herpublicatie capabilities weglaten).
Cockpit (operationeel): https://claude.ai/artifact/U8MxkvaC8qGJN6WrbKKJTv — de ochtendcheck schrijft daar enkel fin/samenvatting.

## Database (Financiën)

* fin/instellingen — btw, betaalkosten_pct (2,5), retour_pct (2), inbound/picking/packing, doos/DPD klein/groot, doelmarge_pct (10), pauzeregel_cpa (45).
* fin/maanden — {rijen:[{maand, orders, omzet_shopify, omzet_bol, omzet, korting, cogs, fulfilment, fulfilment_bron, ads, betaalkosten, vaste_kosten, vaste_bron, rente, resultaat, trueprofit, bol}], bronnen, let_op[], bijgewerkt}.
* fin/balans — {kas[], kredietruimte[], schulden[], te_betalen[], onderweg[], vaste_kosten[[naam,bedrag]], bijgewerkt}. te_betalen-items {wat, bedrag, wanneer, dringend, naam?, iban?, referentie?, bron ("Yuki"|"manueel"), betaald?}.
* fin/ochtend — {datum, bank_bijgewerkt, samenvatting, aandacht:[{soort, kort, tekst}]}.
* fin/dagen — uit winst/dagen.json.
* fin/lijnen — {periode, lijnen[], producten[], aannames[], bijgewerkt} uit winst/winst-per-maand.json.
* fin/prognose — {bijgewerkt, vaste_per_maand (zonder KBC), fulfilment_pct, betaalkosten_pct, fulfilment_vanaf, btw_q3_datum, btw_q3_bedrag, btw_q4_start, items:[{wat, bedrag, datum}]}.
* bank/kas — {maanden, groepen, onbekend, saldi, saldo_datum, bijgewerkt, recent}; bron data/kas-per-maand.json + data/gecategoriseerd.json.
* producten/<id> — {naam, groep, volgorde, product_id, variant_ids[], prijs, vergelijkprijs, kostprijs, kostprijs_bron, shopify_kostprijs, groot_pakket, voorraad, bijgewerkt}.
* boek/<JJJJ>Q<k> — kopie van boekhouding/boek/<JJJJ>Q<k>.json.
* documenten/<auto> — door de pagina: {soort "bestand"|"uitleg", asset_id?, bestandsnaam?, type?, regel_id|null, kwartaal, uitleg, status "nieuw"|"gelezen"|"gekoppeld"|"geen_match", opgeladen_door, op; door Claude: leverancier, datum, bedrag, btw, opmerking}.
* onkosten/<id> — voorgeschoten door een vennoot {wie, datum, leverancier, bedrag, lucy, terugbetaald}. Altijd if_version meegeven bij schrijven.

## Repo

* Bank: fetch_bank.py (Ponto KBC, Revolut, PayPal), fetch_bol.py, fetch_yuki.py, categorize.py; nachtelijke Action bank.yml.
* Boekhouding: boekhouding/regels.py (status verklaard/gekoppeld/ontbreekt per verrichting; koppelingen in boekhouding/koppelingen.json), kwartaal.py, afsluiting.py, invoer.json.
* Winst: winst/profit.py, winst/dagen.py, winst/kostprijzen.json, winst/ean.json, winst/input/*.
* Kredietkaart: data/kaart-2026.json (KBC-export).
* Meta-facturatie: data/meta/facturatie.json.

## Mail

Henri's SmartPaw-mail (smartpaw_mail_henri): facturen staan ook in de mappen Widem, Administratie, Archive en bol.com. Widem-facturen komen via peppol@widem.eu; het bedrag staat enkel in de pdf, de gestructureerde mededeling in de bank bevat het factuurnummer (bv. 002601543535 = 26015435).
Gmail info@smartpaw.be: hele mailbox.

## Zonder TrueProfit (na opzeggen)

ads_google = som bankverrichtingen categorie "Ads Google"; betaalkosten = 2,5% van omzet incl. btw; trueprofit_netto weglaten. Per afgesloten kwartaal betaalkosten nakijken: Shopify net_payments (ShopifyQL FROM payments, gateway shopify_payments) − Shopify-uitbetalingen op de bank (± enkele dagen verschuiving); wijkt dat >0,5% af van 2,5%, het percentage aanpassen. Shopify-API geeft geen fees (read_shopify_payments ontbreekt).

## Mailzoektocht: extra bron (26/10)
- Shopify-facturen (billing@shopify.com) en Alibaba-bestellingen komen binnen in Henri's iCloud (connector icloud_email_henri), map **SmartPaw**. Doorzoek die map ook bij stap 4c.
- Afgesloten kwartalen (26/10): fin/instellingen.afgesloten = {"2026Q3": "..."}. Q3 2026 is via Lucy bij Pro-count en aangegeven. Voor afgesloten kwartalen geen aandachtspunten meer over ontbrekende facturen; het platform toont ze als afgesloten. Focus vanaf Q4 2026: alles via het platform → Yuki.
- fin/bundels (26/10): bundels zoals ze online staan {verberg:[product-id's niet tonen in Marges], bundels:[{groep, naam, prijs (incl. btw, zoals de klant betaalt), bron, picks?, onderdelen:[{id (producten/<id>), qty}]}]}. Het platform rekent kostprijs, fulfilment (picks × €1,23 + 1× verpakken/doos/DPD), max CPA en doel-CPA per bundel. Bronnen: Kaching-blokken op de productpagina's (script.kaching-bundles-deal-block-settings: dealBars met discountValue %) en Shopify-bundels (requiresComponents). Op maandag nakijken of prijzen of kortingen veranderd zijn en fin/bundels bijwerken.
- Lopende btw (26/10): na stap 2 (winst) en 4 (boek) dagelijks `python boekhouding/btw_lopend.py <export van fin/balans>` draaien en fin/btw schrijven (set met file_path boekhouding/btw_lopend.json). Belgische leveranciersfacturen in fin/balans.te_betalen krijgen een veld `btw` (btw-bedrag op de factuur; bv. Widem fulfilment) zolang ze niet betaald zijn. fin/prognose.btw_q4_start = btw_lopend.te_betalen_tot_nu. Het platform toont "Btw opzij houden" op Vandaag en in Geld → Kas & schulden.
