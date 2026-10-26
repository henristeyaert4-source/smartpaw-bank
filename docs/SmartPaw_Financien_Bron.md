# SmartPaw Financiën — enige bron (vanaf 25 okt 2026)

Afspraak (Henri, 25/10): alles over SmartPaw-financiën komt uit het platform SmartPaw Financiën (https://claude.ai/artifact/W6M6FXVEXUvts8ntwJCa8A), de dagelijkse ochtendcheck en deze docs. Bij twijfel geldt: bankdata (Ponto/Revolut) > facturen > Shopify/TrueProfit > ramingen.

## Rekenregels (vast)

* Netto omzet = prijs incl. btw ÷ 1,21.
* Kostprijs = landed cost per batch (EXW-aandeel + FX + SWIFT + Widem-vracht + invoerrechten); invoer-btw is verlegd (art. 41), geen kaskost.
* Fulfilment Widem: inbound €0,41 + picking €0,82 per stuk; packing €1,53 per order; doos €1,30 klein / €1,55 groot; DPD BE €5,59 klein / €5,80 groot; retour €4,66 transport + €2,80 afhandeling.
* Betaalkosten 2,5% van incl. btw.
* Retours 2% van omzet.
* Max CPA = netto omzet − kostprijs − fulfilment − betaalkosten − retours. Break-even ROAS (incl. btw) = prijs incl. btw ÷ max CPA. Target CPA houdt 10% marge.
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
