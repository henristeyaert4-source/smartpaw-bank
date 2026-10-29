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

## Widem-maandfacturen en bestellingsmappen (26/10)
- winst/input/widem_maand.json: per maand de Widem-fulfilmentfactuur (excl. btw): storage, consumables, inbound, pick_pack, labeling (eenmalig), admin, parcels, totaal, factuur. profit.py gebruikt het echte totaal (min bol-fulfilment); maanden zonder factuur = tarieven × kalibratiefactor + opslag en admin van de laatste factuur.
- Widem stuurt de maandfactuur rond de 5e via peppol@widem.eu ("Invoice: 260xxxxx"). Ochtendcheck kan de bijlage NIET openen: zet dan een aandachtspunt 'anders' met kort "Widem-factuur <nr> ontvangen: pdf op bureaublad zetten" en tekst "Zet de pdf in Smartpaw Financieel/Widem maandfacturen op je bureaublad of stuur hem in de chat; dan kloppen fulfilment en resultaat van <maand>." Zelfde voor andere leveranciersmails met bijlagen die bij een bestelling horen.
- Bureaublad Henri (Mac, map Smartpaw Financieel) is enkel bereikbaar vanuit een chat die aan zijn computer gekoppeld is en terwijl de Mac aan staat met de Claude-app open; de ochtendcheck kan er niet aan. Lukt het niet: dat altijd duidelijk melden in plaats van stil over te slaan.
- Bestellingsmappen in Smartpaw Financieel: één map per bestelling ("Order <leverancier/product> <maand> <Widem-dossier WID…>" of "Air order …"). Bij DDP-bestellingen (forwarder van de fabriek) maakt Widem geen dossier: dan blijft de map zonder WID-code (eventueel het Alibaba-ordernummer). Alle documenten van die bestelling erin: PI, commercial invoice, packing list, telex/BL, Revolut-transferbevestigingen, Alibaba-ontvangstbewijzen, Widem-facturen, invoeraangifte.

## Vrije ruimte + te beslissen (26/10)
- Bovenaan Overzicht: "Vrije ruimte · 30 dagen" = kas + kredietruimte zonder `niet_gebruiken` (enkel KBC-budgetfaciliteit €5.000; kredietkaarten zijn voor Meta en tellen NIET mee) + verwacht uit verkoop (gemiddelde 28 dagen: omzet × 1,21 − betaalkosten − ads − vaste kosten) − alle `fin/prognose.items` die binnen 30 dagen vervallen (ook vervallen). Groen ≥ €1.000, oranje ≥ 0, rood < 0. Uitklapbare uitleg per post.
- `fin/prognose.items` velden: `uitgesteld:true` (legaal uitgesteld, bv. btw Q3 in 3 schijven), `beslissing:"open"` + `groep` (nog niet beslist, telt niet mee, getoond met "vrije ruimte erna"), `noot`.
- `fin/prognose.advies[]` {titel, bedrag?, uitleg}: legale manieren om ruimte te maken. Ochtendcheck houdt dit actueel: bij rood altijd concrete, legale uitstelopties voorstellen (afbetalingsplan FOD, betaaltermijnen leveranciers, Creazy-pauze met addendum, pre-orders, ads), nooit iets illegaals (btw niet aangeven, facturen niet boeken).
- Widem-facturen: factuur eind van de maand, betalen binnen 30 dagen → fulfilment van maand M vervalt eind M+1.
- Afspraken 26/10: btw Q3 in 3 schijven (eind nov/dec/jan, aan te vragen via MyMinfin); Compass €4.535 moet; vervallen Widem-factuur betalen; rekening mag tot −€5.000; kredietkaarten niet gebruiken (Meta). Bestelling Jess = te beslissen.

## Aankoopdagboek (29/10, v33–v34)
- `boekhouding/aankoopdagboek.py [JJJJ k ...]` → `boekhouding/dagboek/aankoop_<JJJJ>Q<k>.json` {kwartaal, telling{in Yuki, te boeken, factuur ontbreekt}, bedrag, per_rekening[], lijnen[{status, factuurdatum, betaald_op, leverancier, btw_nummer, factuurnummer, document, asset_id, rekening, rekening_naam, rekening_bron, btw_code, roosters, maatstaf, btw, verlegde_btw, incl, betaald_via (550000 KBC · 550001/550002 Revolut EUR/USD · 434000 MC Henri · 434001 MC Kaydee), nakijken}]}.
- Draait automatisch aan het einde van `regels.py` (nachtelijke GitHub Action + ochtendcheck) en wordt als veld `aankoop` in `boek/<JJJJ>Q<k>` meegeschreven; de pagina leest `aankoop/<JJJJ>Q<k>` of anders `boek/<Q>.aankoop` (de nieuwste wint).
- Grootboekrekening: eerst per leverancier zoals Pro-count die in Yuki boekte (Meta 616502, Google 616501, Findajob 617000 Uitzendkrachten, Widem 612730, bpost 611030, bol 615000, online abonnementen 611080, fabriek 604000, restaurant 616680 (0% aftrek), klein materiaal 611200, beroepsbijdragen 616651, standgeld 616620, verpakking 601000), anders per platformcategorie (rekeningen_koppeling.json).
- Status: "in Yuki" = Yuki-boeking met zelfde leverancier en bedrag (±2 ct, factuur −35…+75 d; fabriek ±2 % / ±7 d); "te boeken" = document bij ons, niet in Yuki; "factuur ontbreekt".
- Btw-codes: eigen codes (BE21, BE21NA, EUDV, NEUDV, EUG, INVOER, GEEN, ?) met roosters, tot Pro-count hun Yuki-btw-codes bezorgt; dan mapping toevoegen in BTW.
- Kwartaalpakket (`kwartaal.py`) heeft een tabblad "Aankoopdagboek" met dezelfde lijnen + totaal per rekening.
- Platform: Boekhouding → paneel "Aankoopdagboek" (tegels, filter te boeken / zonder factuur / in Yuki / nakijken, tabel, totaal per rekening).
