# A9 – Souhrn a návrh funkcí

## Souhrn

ResaleAI je aktuálně **nástroj pro přípravu přeprodeje**, nikoli hotové online tržiště. Umí katalog spravovaný správcem, vyhledávání, demo trendy, žádosti a zprávy ke katalogové položce, soukromé prodejní koncepty, cenový odhad, platformní texty a evidenci skutečného zisku. eBay Browse API doplňuje ceny aktivních EUR nabídek. Aplikace neumí publikovat veřejné uživatelské listingy, přijmout objednávku nebo platbu, zařídit dopravu ani řešit spor.

Technické skóre podle [01-technicka-analyza.md](01-technicka-analyza.md) je **5,4/10** (54 bodů z 10 oblastí). Hlavní silné stránky: Django auth/ORM/admin, vlastnictví soukromých záznamů, migrace, CI a 27 testů. Hlavní slabiny: vývojová produkční konfigurace, chybějící rate limit a procesy osobních údajů, zavádějící demo recenze, N+1 na katalogu, veřejné tržiště/objednávky chybí, produktová odlišitelnost je zatím omezená.

V pracovním stromu jsou lokální necommitnuté opravy z předchozích fází; veřejný GitHub commit může být starší. Fáze A nyní nekóduje aplikaci a po dokončení analýz se zastaví.

## Funkce, které už existují

| Funkce | Skutečný rozsah |
|---|---|
| Katalog, kategorie, hledání, řazení, stránkování | Funguje pro `Product`, který spravuje admin; není to veřejný katalog uživatelských nabídek. |
| Stav zboží | `Condition` je ve formuláři soukromého konceptu; textové atributy podle kategorie (značka, barva, velikost) chybí. |
| Obrázky | Jeden `ImageField` do 8 MB nebo URL obrázku; galerie, komprese a náhledy chybí. |
| Cenový odhad | Lokální pravidla; bez eBay náhodná přirážka. eBay poskytuje aktivní nabídky, ne sold listings. Historie ceny a automatické slevy nejsou. |
| Koncept a prodejní stavy | `ready/listed/sold` existují pro soukromý listing; není veřejný slug, rezervace ani viditelné zobrazení listingů kupujícím. |
| Zprávy | Konverzace je k žádosti o admin katalogový produkt; ne chat kupující ↔ vlastník veřejného inzerátu, bez unread notifikací. |
| Recenze | Katalogové `Review` s ručně zadaným username; nejsou svázány s účtem/dokončeným obchodem a seed recenze jsou demo. |
| Admin | Django admin spravuje katalog, trendy, recenze, žádosti a přehled soukromých listingů. Report queue/audit log neexistují. |
| Platby, doprava, objednávky | Neexistují. Zadaný poplatek je pouze vstup do výpočtu zisku. |

## Pořadí podle poměru přínos / složitost

„Přínos/složitost“ je relativní posouzení pro maturitní prototyp, ne přesný business case.

| Pořadí | Funkce | Přínos | Složitost | Dopad na obhajobu | Potřebné změny DB / API / UI |
|---:|---|---|---|---|---|
| 1 | **Označení demo dat + důvěryhodná recenze pouze po obchodu** | Vysoký | Nízká–střední | Vysoký: řeší zásadní důvěru a falešné hodnocení. | DB: transaction/order reference pro recenzi; API/view: oprávnění po dokončeném obchodu; UI: demo badge, formulář recenze. Pro okamžitý školní režim stačí označit seed recenze jako demo a nevydávat je za skutečné. |
| 2 | **Nahlášení nabídky/obsahu a moderační fronta** | Vysoký | Střední | Vysoký: ukazuje bezpečnostní lifecycle a zásah správce. | DB: Report + stav/důvod; API: POST endpoint, throttling, staff queue; UI: nahlásit, admin rozhodnutí a odůvodnění. |
| 3 | **Veřejný listing od prodejce** | Velmi vysoký | Střední–vysoká | Velmi vysoký: z „kalkulačky“ vytvoří jasně demonstrable resale workflow. | DB: samostatný public listing/visibility, slug, moderace; API: publish/unpublish a policy; UI: veřejný detail, profil prodávajícího, vyhledávání/filtrování. Soukromý koncept převádět do publikovaného záznamu řízeným stavem. |
| 4 | **Watchlist / oblíbené položky** | Střední–vysoký | Nízká–střední | Střední: snadno vysvětlitelná relace uživatel–listing. | DB: unikátní Favorite(user, listing); API: add/remove; UI: tlačítko a stránka uložených položek. |
| 5 | **Více fotografií s kompresí a náhledy** | Vysoký | Střední | Vysoký: viditelně zlepší inzerát a umožní vysvětlit upload pipeline. | DB: ListingImage FK, pořadí; API: validace typu, rozměrů a počtu; UI: galerie/preview; worker/storage: resize/compress. Začít bez asynchronní infrastruktury. |
| 6 | **Profily prodejce a verified email** | Vysoký | Střední | Vysoký: zlepšuje důvěru, bez přehnaně složité identity verifikace. | DB: SellerProfile a email-verified flag; API: verification token s expirací; UI: veřejný profil, stav ověření, kontaktní preference. Telefonní/KYC ověření až po právním a provozním posouzení. |
| 7 | **Uložené hledání a upozornění** | Střední | Střední | Střední | DB: SavedSearch; API: periodic task/e-mail provider; UI: uložit query a správa upozornění. |
| 8 | **Nabídka ceny / protinabídka** | Střední–vysoký | Střední–vysoká | Vysoký | DB: Offer se stavem a expirací; API: atomické accept/reject/counter; UI: historie nabídky a akce. Vyžaduje nejdříve veřejné listingy. |
| 9 | **Značka, velikost, barva a atributy kategorie** | Vysoký | Střední | Vysoký pro filtrování a kvalitu katalogu | DB: normalizované atributy nebo rozumné JSON/related schema; API: category-aware validace; UI: dynamický formulář a filtry. Vyhnout se volným duplicitním sloupcům bez taxonomie. |
| 10 | **Historie cen a automatické zlevnění** | Střední | Střední | Střední | DB: PriceHistory; scheduled task; UI: timeline a opt-in pravidlo. Odhadované asking prices jasně oddělit od sold prices. |
| 11 | **Ověření podobných prodaných položek pro odhad** | Vysoký | Vysoká | Velmi vysoký, pokud zdroj opravdu poskytuje dokončené transakce. | Zdroj/API s právem použití, normalizace produktu/stavu/měny, provenance a vzorek; model validace přes testovací dataset. Browse API active price samo o sobě to neřeší. |
| 12 | **Objednávky, testovací platba, doprava a ochrana kupujícího** | Velmi vysoký | Velmi vysoká | Velmi vysoký, ale vysoké riziko a náklady. | DB: order/payment/shipment/dispute stavové automaty; provider sandbox + webhook signature/idempotency; UI checkout a order tracking; právní podmínky, refund flow, audit. Nedělat escrow „na oko“ ani neukládat kartu. |
| 13 | **Boost / promoce inzerátu** | Střední | Střední–vysoká | Střední | Vyžaduje billing, pořadí, pravidla zobrazení, expiraci a transparentní označení reklamy; realizovat až po public listings. |
| 14 | **2FA, login providers, audit log, PWA, tmavý režim** | Různý | Střední až vysoká | Nízký až střední podle funkce | Bezpečnostní 2FA/audit mohou být přínosné, PWA/tmavý režim jsou až polish. Nezačínat dekorativními funkcemi před IDOR/rate limit/produkčním nastavením. |

## Výběr pěti nejlepších pro maturitní rozsah

1. **Nahlášení a moderační fronta** – konkrétní problém důvěry, přehledný DB/view/admin tok a testovatelná oprávnění.
2. **Veřejný listing z konceptu** – největší produktový posun; vytvoří skutečný kupujícím viditelný objekt, ale zatím bez platby.
3. **Galerie fotografií s kompresí** – vizuální přínos a vysvětlitelná validace/storage pipeline.
4. **Watchlist** – malá, dobře ohraničená relace a viditelná funkce pro kupujícího.
5. **Verified email + profil prodejce** – přidá důvěru s menšími riziky než telefonní KYC/2FA.

**Podmínka pořadí:** Nejprve rozhodnout, zda se projekt rozšíří z interní kalkulačky na veřejné tržiště. Pokud maturitní termín nedovolí bezpečně dokončit veřejný listing, zůstat u „resale assistant“ a dokončit moderaci demo dat, watchlist pro katalog a galerii soukromých konceptů. Platby/escrow, live chat SignalR, automatizované pricing modely a KYC ponechat do budoucna.

## Prioritizovaný plán oprav

1. **Bezpečnost / pravdivost:** označit demo recenze, rate-limit autentizaci a zprávy, přidat max length a report abuse; ověřit `check --deploy` pro zvolený hosting.
2. **Integrita:** opravit N+1 katalogu, doplnit unikátní omezení žádosti a explicitní test seed/flush.
3. **Architektura:** rozhodnout „prodejní nástroj vs marketplace“; teprve pak oddělit Draft/Public Listing/Order.
4. **Výkon a média:** dotazy měřit, doplnit indexy podle `EXPLAIN`, resize obrázků a úklid orphan souborů.
5. **UI / přístupnost:** sjednotit jazyk, label/error/empty/loading state, WCAG a SEO; přidat vlastní screenshoty.
6. **Dokumentace a obhajoba:** psaná práce, testovací scénáře, uživatelský návod, právně schválené texty a ukázkový scénář.

## Závěrečné upozornění

Tento návrh je úmyslně vhodný pro vysvětlení studentem. Každou zvolenou funkci dělat kompletně: datový model/migrace, validace, autorizace, UI, testy, seed a dokumentace. Nezavádět platební ani „escrow“ tvrzení bez ověřeného provider workflow a právního posouzení.
