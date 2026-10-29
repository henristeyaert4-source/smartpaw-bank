# SmartPaw Financiën — enige bron (vanaf 25 okt 2026)

**Werkchat (vanaf 29/10/2026, afspraak Henri):** het financiënplatform wordt verder gebouwd in de nieuwe chat in project SmartPaw die start met "Lees SmartPaw_Financien_Bron.md en SmartPaw_Financien_Platform.md en werk verder aan het financiënplatform". De oude chat "Smartpow financiële status en BMV-lening" is enkel nog archief (geschiedenis opzoeken mag, daar niet meer verder bouwen). Alles wat telt staat in deze docs, de repo henristeyaert4-source/smartpaw-bank en het platform.

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

## bpost-labels (afspraak 26/10)
- Labels via bpost.be (KMO-account SMARTPAW VOF sinds 19/8), betaald met de KBC-debetkaart. Bevestiging "Bevestiging van je bestelling / Confirmation of your order" komt van notify@bpost.be in info@smartpaw.be, met het label als PDF en het ordernummer, bedrag excl./incl. btw.
- Btw: pakjesverzending binnen België is bij bpost vrijgesteld; enkel de printkost (€0,75) draagt 21% (voorbeeld order 12897185 van 26/10: €7,85 pakje + €0,75 print = €8,60, waarvan btw €0,13). Dus NIET 21/121 van het bankbedrag aftrekken.
- Ochtendcheck: elke BPOST-bankregel koppelen aan de bevestigingsmail in info@ (zelfde bedrag, datum ±2 dagen) → koppelingen.json {soort:"mail", label:"bpost-bestelling <nr> (<datum>) – <ontvanger/order>", bedrag, btw:<btw uit mail>}. btw_lopend.py gebruikt dat `btw`-veld. Geen bevestiging gevonden (bv. aan het loket betaald) → in de todo vragen om het kasticket.
- Boeking: rekening 'Verzending & retours (overig)'; noteer waarvoor (vervangzending, retour klant, staal) zodat het aan een order hangt.

## Bestelling Jess PET2026102601 — definitief (27/10)
- Volledige order (PI 27/10): 102 TT003 camera-voerbak ($60), 600 TK-WF119L HydroBuddy ($14,50), 200 droogzakjes, 600 FF009L, 150 FF015 = $16.825 EXW. Voorschot 30% $5.047,50 betaald 27/10 via Revolut SWIFT USD naar 10100063999920 / CHASSGSGXXX (kosten voor ons $27,86; Revolut-koers ±0,897 EUR/USD), bewijs in map "1 Bestelling". Les: rechtstreeks via Revolut USD naar deze Alibaba-rekening ≈ even duur als Alibaba-SEPA in EUR (koers 0,904); vooraf de Revolut-koers checken; saldo $11.777,50 (±€10.153) vóór verzending, productie ±35 dagen → ±1/12.
- Eén productierun, twee verzendingen: LUCHT = de aantallen van de eerdere PI v2 (108 HydroBuddy, 300 FF009L, 150 FF015, 150 droogzakjes = $2.766; Jess-raming vracht $1.758) → offerte Widem (André) op basis van die aantallen. ZEE = de rest (102 TT003, 492 HydroBuddy, 300 FF009L, 50 droogzakjes = $14.059) → zeevrachtofferte Widem.
- Map bureaublad: "Order Jess okt 2026 PET2026102601" met submappen "1 Bestelling" (PI, betaalbewijzen), "2 Luchtvracht" en "3 Zeevracht" (elk: packing list, offerte Widem, B/L/AWB, factuur Widem; WID-code in de submapnaam zodra Widem een dossier opent). Oude map "Air order Hydrobuddy en filters 26:11" mag weg (Henri verwijdert). Zelfde opbouw voor toekomstige orders met lucht + zee.
- Landed cost per batch berekenen zodra vracht- en invoerkosten gekend zijn (winst/kostprijzen.json): lucht- en zeedeel apart.

## Widem opslag + admin = vaste kost (afspraak 27/10)
- Opslag + admin (nu €135 + €75 = €210/maand) zitten niet meer in fulfilment maar in de vaste kosten (`vaste_detail["Widem opslag + admin ..."]`), gelijk verdeeld per dag (dagen.py). Fulfilment = enkel kosten per bestelling (pick & pack, pakjes, dozen, labeling).
- Maand zonder factuur: raming = opslag + admin van de laatste factuur. Komt de factuur binnen: widem_maand.json aanvullen, profit.py + dagen.py + `winst/naar_platform.py <fin/maanden.json> <uitmap>` draaien en fin/maanden, fin/lijnen, fin/dagen overschrijven → de vorige maand wordt zo automatisch gecorrigeerd.

## Update 29/10/2026 (boekhouding, bewijs, Meta-betaling)
- **Bronnen automatisch (elke ochtend):** KBC-zichtrekening (Ponto), Revolut, bol.com, Yuki (GitHub-workflow); Shopify-omzet en Meta-facturatielog (ochtendtaak). **Mastercards 2103 (Kaydee) en 6682 (Henri) NIET automatisch**: komen uit de KBC Touch-export die Henri/Kaydee zelf opladen (data/kaart-2026.json, laatste t/m 23/10). Maandelijks de kaartexport opladen.
- **Meta betaalt sinds 23/10 met Mastercard 2103** (Standaard in Meta). Tot 21/10 via KBC-debetkaart (= Mastercard ····6564 in Meta, "M4M – MDES" op het afschrift). Advies: 6564 verwijderen in Meta zodat er geen terugval naar KBC is; kaartlimiet 2103 checken (Meta ±€7–8k/m + Google).
- **Meta-meldingen:** er bestaat geen apart factuur-e-mailveld; meldingen "Updates voor advertentieaccount" staan sinds 29/10 op info@smartpaw.be.
- **regels.py koppelt nu ook aan Yuki** (data/yuki/openstaand.json → leveranciers_boekingen): pas 1 = leverancier + bedrag ±2 ct, factuur −35…+75 d; pas 2 = exact bedrag binnen 20 d. Bewijs soort "yuki".
- **koppelingen.json `_verwacht`**: documenten die vóór de betaling binnenkomen (bv. KBC-vervaldagbericht) met match {tegenpartij, bedrag, van, tot}; koppelen automatisch bij de betaling.
- **Revolut "Company Pro plan fee" (€35/m) = Bankkosten** (verklaard via uittreksel).
- Gekoppeld op 29/10: Compass-invoice FurVac 750 (CPS20260619, $21.784,75; betaald $6.535,43 + $10.000; saldo $5.249,32 ≈ €4.535 gepland 16/11), KBC BA-polis 37630975 vervaldagberichten (premie €18,47, vanaf 27/11 €19,05), Meta FBADS-210-106742402 (23/10, €621,34), Klaviyo T9T7QHZO-0015.
- Stand: Q3 164/182 (90%), 18 ontbrekend (Shopify 5, Google Ads 3, markten 3, horeca 3, POM, Packaging €360, ReturnGO, Meta Verified). Q4: enkel GoDaddy €167,76.
- Platform v32: "Nog te doen" bovenaan Boekhouding, per kwartaal en per leverancier met "waar vind je het".

## Update 29/10 middag: aankoopdagboek
- Nieuw: aankoopdagboek per kwartaal met boekingsvoorstel per factuur (grootboekrekening volgens Pro-count, btw-code, maatstaf, btw). Q3: 73 in Yuki, 11 te boeken (€4.906), 17 zonder factuur. Q4 tot nu: 8 in Yuki, 15 te boeken (€11.043, vooral Meta oktober + Jess-voorschot), 1 zonder factuur.
- Nog van Pro-count nodig: hun Yuki-btw-codes, en bevestiging van de rekeningkeuzes (o.a. Packaging Discounter/Drukbedrijf als intracommunautaire verwerving, standgeld markten, POM).

## Yuki-crediteuren in "Te betalen" (afspraak 29/10, gaat vóór stap 1b van de ochtendcheck)
Yuki toont veel facturen als "open" die al betaald zijn (kaartbetalingen die Pro-count niet tegen de factuur boekte, en bol.com-facturen die bol verrekent met de uitbetaling). Zet daarom een Yuki-crediteur enkel in fin/balans.te_betalen als ALLES hieronder klopt:
- factuurdatum ≤ 120 dagen geleden;
- contact is niet bol.com, Meta, Google, Shopify, Klaviyo, Higgsfield, Canva, Amazon, Appsumo, ReturnGO, Manychat, KBC Bank of een andere leverancier die per kaart of automatisch betaald wordt (die zijn betaald; hoogstens ontbreekt de koppeling in Yuki);
- geen uitgaande verrichting (KBC, Revolut of kaart) met hetzelfde bedrag (±€0,05) sinds 7 dagen vóór de factuurdatum;
- open > 0 (creditnota's niet).
Stand 29/10: zo kwamen erbij Findajob F001/202600701 (€149,01) en F001/202600711 (€158,95), Almost 3000 (€314,60), Thomas More (€75), Proximus (€10), bpost 268565664 (€6,78), Pro-count 270345 (€242). Yuki-data komt pas sinds 29/10 08:35 binnen; de ochtendcheck van 29/10 (07:16) had ze nog niet.
De oude "open" posten in Yuki (37 stuks, €4.851, vooral kaartbetalingen eind 2025) en de bol-verrekening zijn een opkuis voor Pro-count, niet iets om te betalen.
- QR overal (29/10): elk te_betalen-item met een Belgische leverancier krijgt `iban` + `referentie` = de gestructureerde mededeling van de factuur (+++xxx/xxxx/xxxxx+++, uit Lucy/Peppol-pdf; anders het factuurnummer). IBAN's staan in data/iban-leveranciers.json (aangevuld 29/10 met Findajob, Almost 3000, Thomas More, Proximus, bpost, Pro-count BE28 0689 0720 1520, Belgian Doggos, Creazy). Geen QR voor USD-betalingen (Compass, Jess via Revolut SWIFT), de KBC-domiciliëring en ramingen zonder factuur.
- Gestructureerde mededeling zonder Lucy (29/10): Yuki geeft factuurnummer, bedrag en vervaldag, maar geen IBAN of mededeling. IBAN komt uit data/iban-leveranciers.json. Mededeling = 10 cijfers + controle (10 cijfers mod 97, 0 → 97), te berekenen uit het factuurnummer voor:
  · Widem: "00" + factuurnr (8 cijfers) → 26017495 → +++002/6017/49558+++
  · Findajob: "001" + factuurnr zonder de eerste 2 cijfers → 202600711 → +++001/2600/71123+++
  · bpost: "0" + factuurnr (9 cijfers) → 268565664 → +++026/8565/66418+++
  · Thomas More: "22" + cijfers van TMM-nr → TMM-62204778 → +++226/2204/77872+++
  · Proximus: geen gestructureerde mededeling; gebruik het factuurnummer.
  Andere leveranciers (Pro-count, Almost 3000, Belgian Doggos, nieuwe): mededeling staat enkel op de factuur-pdf. Staat de pdf in de mail of in het platform, lees ze daar; anders QR met het factuurnummer als vrije mededeling en vermeld in de todo "mededeling nakijken op de factuur". Nieuwe leverancier zonder IBAN: geen QR, 1 aandachtspunt "IBAN van <leverancier> nodig".
- Meta-kwitanties als pdf (29/10): Henri/Kaydee laden maandelijks de zip uit Meta (Facturering → Betalingsactiviteit → downloaden) op in de chat. Elke pdf → asset in het platform + boekhouding/meta_kwitanties.json {transactie_id: asset_id, bestand, datum, bedrag}. Ochtendcheck stap 4b: bij een Meta-koppeling het asset_id/bestand uit meta_kwitanties.json meegeven. Zip okt (30/9–29/10): 12 kwitanties; 7 gekoppeld; open: 25/10 en 28/10 (€800, Mastercard 2103 → koppelen met de kaartafrekening) en 3 kleine bedragen (7–8/10: €3,11, €0,74, €0,10) die nog niet op een rekening of kaartexport staan.

## Documenten naar Yuki (test geslaagd 29/10, met akkoord van Shany)
- De Yuki-sleutel mag documenten opladen (Archive.UploadDocumentWithData). Test: GoDaddy-ontvangstbewijs €167,76 → map 1 "Aankoop", betaalwijze 5 "Zakelijke Credit card"; Yuki-document-ID b6c4ece3-4d15-4cac-badd-2f756b90420c.
- Mappen: 1 Aankoop, 2 Verkoop, 3 Bank, 4 Personeel, 5 Belasting, 6 Verzekering, 7 Uitzoeken Yuki, 8 Overig financieel, 0 Overig, 100 Zelf te ordenen. Betaalwijzen: 4 Zakelijke Bancontact, 5 Zakelijke Credit card, 3 Uit bedrijfskas, 10 Privé betaald (onkosten nota).
- Workflow "Document naar Yuki (test)" (yuki_upload.yml, enkel manueel). Nog niets automatisch: eerst bevestiging van Shany dat het goed binnenkwam en leesbaar is.
- Automatisch naar Yuki (29/10, live): de nachtelijke Action stuurt na regels.py elke lijn "te boeken" met een pdf in boekhouding/naar_yuki/pdf/<asset_id>.pdf (betaald vanaf 29/10/2026) naar Yuki-map Aankoop (betaalwijze: kaart 434000/434001 → 5 Zakelijke Credit card, KBC/Revolut → 4), met in de opmerking leverancier, factuurnr, betaaldatum en voorstel rekening/btw. Bijgehouden in boekhouding/naar_yuki/verzonden.json (nooit twee keer); het aankoopdagboek zet die lijnen op "In Yuki". Achterstand van vóór 29/10 enkel na akkoord: regel-id's in boekhouding/naar_yuki/instellingen.json → ook_versturen.
- Ochtendcheck: elk document dat gekoppeld wordt (upload in het platform, Meta-kwitantie, pdf uit de mail) ook opslaan als boekhouding/naar_yuki/pdf/<asset_id>.pdf en committen (Artifact read met path = asset_id, out_dir = die map), zodat de Action het kan versturen. Pdf's uit de mail eerst als asset opladen.
- Betaalgegevens uit Yuki (29/10, live): de Action leest elke nacht de factuur-pdf/Peppol van openstaande facturen in Yuki → data/yuki/betaalgegevens.json {referentie: {contact, iban, ogm}}. Ochtendcheck stap 1b: iban + referentie (+++ogm+++) voor te_betalen eerst daaruit, anders data/iban-leveranciers.json + de formules hierboven.
- Achterstand verstuurd (29/10, akkoord Henri): 17 documenten (okt: 7 Meta, Jess-PI PET2026102601 = overall proforma $16.825 met 30%-voorschot, Alibaba-filterorder €1.112,10, Klaviyo, Holo, KBC; Q3: KBC ×3, Holo ×2). Shany bevestigde dat ze binnenkwamen. Nog zonder document: Meta 27/9 en 30/9 (zitten in Lucy), Klaviyo jul–sep, Packaging Discounter €665, Shopify okt €129,20, bpost €8,60.
- Opkuis oude open posten in Yuki: gevraagd aan Shany (29/10), 32 posten vóór okt, €6.198,24, met de vraag wat ze nodig heeft (kaartafrekeningen, bol-/Amazon-afrekeningen).

## Gesprek Peter 29/10 (zie SmartPaw_Gesprek_Peter_29_okt.md)
- 50/50, Becrazy = handelsnaam van SmartPaw VOF voor de UGC-dienstverlening (overgenomen uit Creazy). SmartPaw moet op elke Becrazy-factuur staan. Eerste factuur eind nov (€6.600).
- Lucy weg = verkoopfacturen via Yuki met Peppol versturen. Gevraagd aan Shany (concept 29/10): komt Peppol nu via Lucy binnen (één aansluiting per bedrijf), laat ons pakket versturen toe (Minimal kan niet), registratie in Yuki voor ontvangen + versturen.

## Verkoopfacturen (platform v38, 29/10)
- Boekhouding → Verkoopfacturen. db: `klanten/<id>` {naam, btw, straat, gem, land BE/NL/FR/DE/LU/EU/X, mail, contact}; `verkoopfacturen/<id>` {klant_id, klant (kopie), handelsnaam Becrazy|SmartPaw, datum, termijn, vervaldag, periode, ref, opm, lijnen[{oms, aantal, prijs excl, btw BE21|BE6|VERL|BUITEN}], totaal{excl, btw, incl, per_tarief[]}, status concept|klaar|verzonden|fout, nummer, ogm, verzonden_op, via, yuki_id, fout}; `fin/facturatie` {peppol_actief, sinds, uitleg, afzender{...}}.
- Afzender: SmartPaw VOF, Handelsdokkaai 9 bus 401, 9000 Gent, btw BE 1028.566.224, RPR Gent afdeling Gent, IBAN BE84 7310 7076 0259 (KREDBEBB). Btw-vermeldingen: VERL = art. 196 Richtlijn 2006/112/EG, BUITEN = art. 21 §2 W.BTW.
- Concept heeft geen nummer; Yuki geeft het nummer bij verwerken (geen eigen nummering, zodat de reeks doorlopend blijft). Pdf-download van een concept draagt "CONCEPT".
- Versturen (nog niet actief): zodra Pro-count Peppol in Yuki aanzet → `fin/facturatie.peppol_actief = true`. Dan: elke factuur met status "klaar" via Yuki Sales.ProcessSalesInvoices (Process = true) aanmaken (contact op btw-nummer, lijnen met grootboek omzet diensten en btw-code volgens Pro-count), Yuki boekt en verstuurt via Peppol. Daarna nummer, ogm, yuki_id, verzonden_op en status "verzonden" terugschrijven; bij een fout status "fout" + tekst. Eerst één testfactuur met akkoord van Henri/Kaydee en Shany.
