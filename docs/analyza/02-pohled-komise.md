# A2 – Pohled maturitní komise

## Předběžné posouzení

Projekt je vhodný základ praktické maturitní práce z IT, pokud písemná část jasně vymezí, že jde o **prodejní nástroj/prototyp**, nikoli o hotové tržiště. Má vlastní datový model, autentizaci, formuláře, administraci, integraci s externím API, výpočty zisku, migrace, CI a testy. To poskytuje dost témat pro technickou obhajobu.

Co zatím není doloženo v samotném repozitáři: samostatné zadání/cíle práce od školy, požadavky a jejich trasování do testů, uživatelská dokumentace, screenshots, plán nasazení a především skutečný nákupní tok. E-shopové prvky nelze obhajovat tvrzením, že aplikace zprostředkovává transakce.

| Kategorie | Odhad | Zdůvodnění |
|---|---:|---|
| Technická náročnost | 6/10 | Django monolit, auth, několik relací, API OAuth, upload, migrace a finanční výpočty. Bez plateb, deploymentu a veřejných prodejů nejde o plnohodnotný marketplace. |
| Originalita | 5/10 | Generování textu a orientační ceny jsou známý koncept; zajímavější je evidence nákladů a srovnání očekávaného/realizovaného zisku. |
| Kvalita provedení | 5/10 | Základní workflow a testy fungují, ale demo recenze, anglické texty, N+1 v katalogu, chybějící rate limit a produkční varování snižují dojem. |
| Dokumentace | 6/10 | README a architektura existují; analytické, uživatelské a testovací materiály teprve vznikají. |
| Připravenost k obhajobě | 5/10 | Lze obhájit Django a cenovou logiku, pokud student umí přiznat limity, vysvětlit každé pravidlo a předvede stabilní lokální dataset. |

## Deset pravděpodobných otázek / slabých míst

1. **„Co přesně znamená AI ve vašem projektu?“** Odpověď: žádný ML ani LLM se nepoužívá; jde o deterministická pravidla, slovník klíčových slov a šablony. Doporučení: v obhajobě i UI používat přesný termín „automatický návrh/heuristika“.
2. **„Kupuje se zde zboží a probíhá platba?“** Ne. Veřejný `Product` je katalog spravovaný adminem; `GeneratedListing` je soukromý prodejní koncept. Ukázat modely a vysvětlit, co by vyžadovala objednávka.
3. **„Jsou recenze skutečné?“** V seed datech jsou fiktivní demo recenze. Jasně je označit jako demo a neprezentovat je jako ověřené nákupy.
4. **„Odkud máte ceny eBay a co dokazují?“** Browse API poskytuje aktivní nabídky, nikoli uzavřené prodeje. Ukázat měnu, vzorek a čas načtení; říct, že odhad není garance.
5. **„Jak je chráněno soukromí inzerátu proti změně ID v URL?“** Pohledy filtrují `GeneratedListing` podle vlastníka; cizí záznam vrací 404. Objednávková IDOR kontrola zatím neexistuje, protože objednávkový model chybí.
6. **„Jak se počítá zisk?“** Prodejní cena minus pořizovací cena, doprava a procentní/pevný poplatek; realizované hodnoty mají přednost, pokud byly zadány. Uvést, že zadané poplatky aplikace neověřuje.
7. **„Co se stane, když eBay neodpoví?“** Request má timeout a služba vrátí nedostupná data; generování může pokračovat lokálně. Cena bez eBay je částečně náhodná, proto není reprodukovatelná.
8. **„Může uživatel nahrát libovolný soubor?“** `ImageField`/Pillow validuje obraz a formulář má limit 8 MB; nejsou implementovány komprese, antivirová kontrola ani úplná ochrana proti extrémním rozměrům.
9. **„Proč SQLite a co při více uživatelích?“** Je vhodná pro školní lokální běh; nastavení podporuje PostgreSQL. Veřejný provoz by potřeboval spravovanou DB, migrace, zálohy, monitoring a zátěžové testy.
10. **„Jak doložíte, že práce funguje a je bezpečná?“** 27 testů pokrývá hlavní workflow a CI je spouští na push/PR. Test suite není bezpečnostní audit ani browser/e2e test; uvést přesný rozsah a chybějící části.

## Kód, který může působit příliš složitě

| Místo | Posouzení | Jak ho vysvětlit nebo zjednodušit |
|---|---|---|
| `products/views.py::_seller_listing_summary` – `Cast`, `Coalesce`, `ExpressionWrapper`, `F`, `Sum` | Je to pokročilá ORM agregace čistého zisku v databázi. Má smysl pro součet mnoha položek bez načtení všech řádků do Pythonu. | Student by měl nakreslit výraz „prodejní cena − pořizovací cena − doprava − poplatek“. Pokud to nedokáže vysvětlit, rozdělit na menší pojmenované funkce a pokrýt konkrétními testy; nepřidávat generickou reporting framework abstrakci. |
| `products/services.py` – OAuth token cache a parsing API výjimek | Standardní integrační kód, ne zbytečná architektura. | Umět popsat client-credentials, cache TTL, timeout, měnu EUR a fallback. |
| `products/ai_engine.py` – heuristická cena a texty | Krátký, pochopitelný algoritmus; složitost je nízká, ale náhodná přirážka ztěžuje reprodukovatelnost. | Vysvětlit multiplikátory stavu, interval nabídek a náhodnou část; pro obhajobu lze použít pevný seed/odstranit náhodnost jako budoucí zlepšení. |
| Django ORM anotace `Count`, `Avg` a filtry | Běžný Django způsob práce s databází. | Ukázat ekvivalentní SQL koncept; není důvod ručně psát SQL. |

V projektu nebyla nalezena reflexe, pokročilé generiky, složité LINQ, JWT ani vlastní dependency-injection kontejner. Nepřidávat je jen kvůli dojmu „enterprise“.

## Příprava obhajoby

- Naučit se nakreslit požadavek od URL přes view/form až k ORM a template.
- Umět bez prezentace vysvětlit jednu položku zisku ručně na číselném příkladu.
- Přiznat: privátní koncept ≠ veřejný inzerát; aktivní cena ≠ prodejní cena; šablonový odhad ≠ generativní AI; demo recenze ≠ ověřené hodnocení.
- Předem spustit testy, migrace a demo seed na oddělené lokální databázi; připravit screenshoty, kdyby síť nefungovala.
- Připravit jednu jednoduchou architektonickou mapu a ukázat skutečné testy, ne pouze slidy.
