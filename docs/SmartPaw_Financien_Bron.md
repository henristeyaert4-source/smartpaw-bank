# SmartPaw Financiën — enige bron (vanaf 25 okt 2026)

Afspraak (Henri, 25/10): alles over SmartPaw-financiën komt uit het platform SmartPaw Financiën (https://claude.ai/artifact/W6M6FXVEXUvts8ntwJCa8A), de dagelijkse ochtendcheck en deze docs. Bij twijfel geldt: bankdata (Ponto/Revolut) > facturen > Shopify/TrueProfit > ramingen.

## Rekenregels (vast)

* Netto omzet = prijs incl. btw ÷ 1,21.
* Kostprijs = landed cost per batch (EXW-aandeel + FX + SWIFT + Widem-vracht + invoerrechten); invoer-btw is verlegd (art. 41), geen kaskost.
* Fulfilment Widem: inbound €0,41 + picking €0,82 per stuk; packing €1,53 per order; doos €1,30 klein / €1,55 groot; DPD BE €5,59 klein / €5,80 groot; retour €4,66 transport + €2,80 afhandeling.
* Betaalkosten 2,5% van incl. btw.
* Retours 2% van omzet.
* Max CPA = netto omzet − kostprijs − fulfilment − betaalkosten − retours. Break-even ROAS (incl. btw) = prijs incl. btw ÷ max CPA. Doel-CPA houdt 20% winstmarge (doel Henri & Kaydee, 26/10): doel-CPA = max CPA − 20% × netto prijs.
* Kostprijs in Shopify (25/10): gelijkgezet met winst/kostprijzen.json (de kostprijs die vandaag geldt; -PRE-sku's = batch 750). De ochtendcheck houdt dit dagelijks gelijk en schakelt de FurVac-sku's op 26/11 naar batch 750. Bundels zonder sku/onderdelen worden niet aangeraakt.
* TrueProfit "Gross Profit" trekt btw niet af → nooit campagnes op die kolom beoordelen; netto klopt wel.
* Kantoor €750/maand wordt door Creazy betaald, niet door SmartPaw. Hoort voorlopig niet in SmartPaw's winst.
* Vaste kosten ±€1.540/maand.

## Schulden en kas (stand 25/10)

* KBC-krediet €17.318 (€588,87 op de 16e van elke maand) · rekening-courant Henri €14.000 · Creazy €10.000 · Compass FurVac-saldo ±€4.535 · Widem 26016933 €1.221 (vervallen 24/10).
* Btw Q3 2026 (€6.873,24): bewust later betaald (wachten op kas).
* Budgetfaciliteit KBC €5.000.

## Aanvullingen 26/10
- Lening Creazy CommV (overeenkomst in platform, documenten/lening-creazy): €10.000, aanvang 25/06/2026, 3,5%/jaar, 3 maanden aflossingsvrij (rente €87,76 gekapitaliseerd), daarna 24 termijnen van €435,82 uiterlijk de laatste dag van de maand (1e: 31/10/2026, laatste: sep 2028) naar BE50 7380 5179 7618. In fin/balans.te_betalen als soort "aflossing" (telkens de volgende termijn) en in fin/prognose.items. Na betaling: volgende termijn inzetten, schuld verlagen volgens de aflossingstabel.
- Holo AI (UAB Holo LT, LT): facturen mrt–okt 2026 gekoppeld (USD, zonder klantgegevens); jan, feb en aug ontbreken. Abonnement stopgezet okt 2026.
- fin/balans: te_betalen-items krijgen `vervalt` (JJJJ-MM-DD); schulden met soort bank/vennoot/verbonden zijn langlopend (velden maandelijks, dag, rente, einde, start_bedrag, volgende, voorwaarden).
- Shopify-factuur ±€130/maand: Basic €32 · TrueProfit ±€31 · Kaching Bundles ±€24 · ReturnGO ±€20 · Yuki-app ±€14 · Kaching Subscriptions ±€8; jaarlijks Recomma Quiz €85 (18/7) en domein smartpaw.eu €12.
- Kaching Bundles NIET schrappen: levert de bundelblokken op de productpagina's van FeedMate, ChromeFeeder, FurVac, HydroBuddy, FlowMate, AquaPaw en de 3 filterpagina's (gecontroleerd 26/10). Kaching Subscriptions: abonnementsoptie op de 3 filterpagina's, 0 abonnementsorders in de laatste 250 orders; enkel weg na eerst de abonnementsbalk uit die Kaching-blokken te halen.
- TrueProfit opgezegd 26/10, loopt tot 19/11/2026. Vanaf 19/11 (en voor november volledig) de werkwijze "Zonder TrueProfit" uit de platformhandleiding gebruiken. Kaching Subscriptions uitgezet 26/10. Holo AI gestopt (uit vaste kosten).
- Bestelling Jess (PI PET2026102601, 26/10): 108 HydroBuddy + 300 FF009L + 150 FF015 + 100 droogzakjes = $2.741 EXW (30% voorschot, 70% vóór verzending). Plan: luchtvracht nu, grote zeebestelling over enkele weken. Wacht op aangepaste PI (op naam SmartPaw VOF) en vrachtoffertes (lucht DDP/DAP, trein). Daarna: voorschot, saldo en vracht in fin/balans.te_betalen en fin/prognose.items; nieuwe landed cost per batch in winst/kostprijzen.json.

## Widem-maandfactuur: elke maand controleren en verwerken (afspraak 26/10)
Zodra de Widem-factuur "Fulfilment <maand>" binnen is (mail/iCloud-map SmartPaw of bureaublad "Widem maandfacturen"):
1. Regels overnemen in `winst/input/widem_maand.json` (excl. btw: storage, consumables, inbound, pick_pack, labeling, admin, parcels, totaal, factuurnr).
2. `python winst/widem_controle.py` draaien: vergelijkt elke regel met orders × tarieven (pick €0,82/stuk + pack €1,53/order, doos €1,30/1,55, DPD €5,59/5,80, admin €75). Vlag bij >10 % én >€15 te veel, bij een gewijzigde opslag of admin, bij labeling, of als de regels niet optellen tot het totaal.
3. Vlag = melden aan Henri/Kaydee met het bedrag en een conceptmail aan Widem klaarzetten (nooit zelf versturen) met de vraag om het manifest/de verzendlijst van die maand. Een afwijking is een vraag, geen bewijs: pre-orders en annulaties verschuiven orders tussen maanden.
4. Daarna `winst/profit.py` en `winst/dagen.py` opnieuw draaien → fin/maanden, fin/lijnen, fin/dagen bijwerken (resultaat), factuur koppelen aan de bankbetaling in het kwartaalboek (boekhouder/Yuki) en de btw (21 % aftrekbaar) mee laten lopen in `btw_lopend`.
5. Maanden zonder factuur blijven een raming (tarieven × kalibratie + opslag + admin) en worden overschreven zodra de factuur er is.
Eerste controle (26/10): juni (+€435 pakjes, +€82 pick & pack), juli (+€180 pakjes) en augustus (+€169 pakjes) boven verwachting; mei juist ver onder (€2,80/order) → waarschijnlijk deels pre-orders van mei die in juni verstuurd zijn, maar ook mei+juni samen is €7,75/pakje vs tarief max €5,80. Manifesten juni–augustus opvragen. Opslag €45 → €67,50 (mei) → €135 (aug): navragen op basis van welke m²/pallets.
Aanvulling 26/10: geen mail sturen over de oude maanden; de controle start bij de volgende factuur (oktober).
Bij elke controle ook de mails nakijken op prijswijzigingen van Widem (André Goldstein, Marc Clément, Jessy Morel, cs@widem.eu …): diesel-/brandstoftoeslag, nieuwe tarieven, indexering, retourprijs. Mailboxen: info@smartpaw.be (Gmail), henristeyaert@smartpaw.be, iCloud-map "SmartPaw". Een gevonden wijziging → tarieven in `winst/widem_controle.py` en `winst/profit.py` aanpassen vanaf de ingangsdatum en melden. Stand 26/10: geen toeslag- of tariefmail gevonden sinds sep 2025.
Specificatie per maand: Widem stuurt "Invoicing SmartPaw <maand>.xlsx" (Marc Clément, mail "Facturatie 2026" van 4/9 aan info@, jan–aug 2026). Bijlagen kan ik niet uit de mail halen → bewaren in bureaublad "Smartpaw Financieel/Widem maandfacturen". Retour: €23/maand + €4,66 per retour (voorstel Henri 11/9, antwoord Widem niet gevonden).
Specificaties jan–aug 2026 verwerkt (26/10, map "Widem maandfacturen/Specificaties per maand"; samenvatting zonder klantgegevens in `winst/input/widem_spec.json`). Conclusie: pakjes en pick & pack kloppen tot op de cent met de facturen (aug: €10,60 verschil op pakjes). De "te hoge" pakjes in jun–aug kwamen door (1) verzonden ≠ besteld: in juni 31 oude pre-orders mee verstuurd (161 pakjes vs 134 Shopify-orders) en (2) DPD kost all-in meer dan het basistarief: basis BE €5,78–6,00 + brandstoftoeslag €1,00–1,40 (schommelt per maand = de dieseltoeslag) + security €0,12 + wegentaks €0,11 ≈ €7,0 BE, ±€8,8–9,3 NL. Tarief in platform (fin/instellingen dpd) en profit.py aangepast naar €7,07 all-in. Open vragen: opslag-sprongen (mei, aug) en consumables op factuur > dozen in specificatie (jun +€36, jul +€56, aug +€51).
Afspraak 26/10: opslag volgt de hoeveelheid stock (meer stock = duurder) en extra verbruiksmateriaal = dozen van Widem die we gebruiken. Beide zijn verklaard en geen reden om te vlaggen; enkel tonen. Vlaggen blijft voor pick & pack, pakjes, admin en regels die niet optellen.
