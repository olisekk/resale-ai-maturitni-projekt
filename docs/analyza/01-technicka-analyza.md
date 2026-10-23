# A1 – Technická analýza

**Skóre popisují současný stav projektu, nikoli stav po doporučených budoucích opravách.** Veřejný commit může zaostávat za pracovním stromem: níže zohledňuji lokální necommitnuté opravy a tuto skutečnost uvádím u nálezů.

## Skóre

| Oblast | Skóre | Odůvodnění |
|---|---:|---|
| Architektura | 6/10 | Jeden srozumitelný Django monolit; oddělené soubory pro views, modely, formuláře a služby. `views.py` ale kombinuje autentizaci, katalog, komunikaci, workflow i SQL agregace. Vzhledem k velikosti není víceprojektová architektura potřebná. |
| Kvalita kódu | 6/10 | ORM, pojmenované modely, formuláře a základní komentáře. V souborech je nekonzistentní formátování/jazyk a některé dlouhé views. Použití `ExpressionWrapper`, `Cast` a vnořené databázové výrazy v souhrnu zisku je funkční, ale student musí umět vysvětlit typy a fallbacky. |
| Bezpečnost | 6/10 | Django auth hashování, CSRF middleware/tokeny, validace hesel v lokálním stromu, kontrola vlastníka soukromého listingu, POST pro změny a timeout API. Chybí rate limit, ověření e-mailu, reset hesla, ochrana proti spamu a produkční nastavení. |
| Databáze | 6/10 | Relace jsou čitelné, migrace existují a ORM používá parametrizované dotazy. Chybí samostatné transakční entity, soft delete, deduplikace reportů a vhodné indexy pro růst. `seed_data --flush` je destruktivní pro katalogová data. |
| Výkon | 5/10 | Katalog a inventář jsou stránkované, eBay token se cachuje, souhrny používají agregace. Katalogový template přesto čte `product.review_count`, což může spustit další dotaz pro každý produkt; admin N+1 je opraven pouze v aktuálním lokálním diffu. Obrázky se nekomprimují a velikosti se nemění. |
| UI/UX a přístupnost | 5/10 | Responzivní Bootstrap, validační chyby, empty state katalogu a lazy loading obrázků. Část UI je anglicky, některé JS chyby používají `alert`, chybí cookie preference pro nepovinné trackery a systematický WCAG/SEO audit. |
| Resale business logika | 3/10 | Funguje příprava nabídky a evidence nákladů, nikoli kompletní tržiště. Soukromý `GeneratedListing` není veřejný inzerát; neexistují objednávky, platby, doprava, rezervace, spory ani ověřené transakční recenze. |
| Testování | 7/10 | 27 unit/integration testů; mockované externí API, testy IDOR a finanční logiky, test počtu dotazů v adminu. Chybí browser/e2e, UI accessibility, zátěžové testy, testy proti externímu staging API a samostatné testy některých validačních hran. |
| Dokumentace a údržba | 6/10 | Český README, architektura s ER diagramem, `.gitignore`, CI a MIT licence. Chybí několik uživatelských/technických příruček a skutečné screenshoty. Historie obsahuje zatím jediný úvodní commit; lokální změny nejsou commitnuté. |
| Nasazení | 4/10 | Proměnné prostředí, konfigurovatelná DB/S3, console logging a CI. Není deployment workflow ani hosting konfigurace, produkční check má šest varování, nejsou readiness/health endpointy, monitoring, zálohovací automatizace ani řízení migrací při nasazení. |
| **Celkem** | **5,4/10** | Aritmetický průměr; silný školní prototyp, nikoli produkční marketplace. |

## Nálezy

| Závažnost | Soubor a řádek | Problém | Proč je to problém | Jak opravit |
|---|---|---|---|---|
| Vysoká před nasazením | [settings.py](../../resale_ai/settings.py#L8-L22) | Výchozí `DEBUG=True`, vývojový `SECRET_KEY`, vypnuté HTTPS/HSTS a cookies. `check --deploy` hlásí W004, W008, W009, W012, W016, W018. | Ve veřejném provozu mohou být odhaleny interní chyby a oslabena ochrana session/CSRF. Výchozí hodnoty jsou přijatelné jen lokálně. | Při nasazení vynutit `DEBUG=False`, tajný klíč z prostředí, povolené hostitele, TLS, secure cookies a HSTS až po ověření domény/HTTPS. Zopakovat `check --deploy`. |
| Střední | [product_list.html](../../templates/products/product_list.html), [views.py](../../products/views.py#L90) | **Opraveno lokálně:** template používá anotované `review_total` místo `product.review_count`. | Původní vlastnost prováděla dotaz na recenze pro každý produkt. | Změna je v pracovním stromu; doplněný test hlídá dotazy adminu, katalogový query budget zůstává doporučeným dalším testem. |
| Střední | [seed_data.py](../../products/management/commands/seed_data.py) | Seed vytváří fiktivní recenze s uživatelskými jmény a tvrzeními vypadajícími jako skutečné. | Veřejnost může být uvedena v omyl a testovací data znehodnotí důvěru v hodnocení. Lokální necommitnutá oprava blokuje příkaz při `DEBUG=False`, ale samotná data nejsou viditelně označena jako demo. | Vždy zobrazit demo štítek, oddělit demo DB a před produkcí odstranit fikční recenze. Seed nikdy nepoužívat nad produkční DB. |
| Střední | [models.py](../../products/models.py#L64-L252), [views.py](../../products/views.py#L264) | Prodejní koncepty jsou soukromé a nemají kupní workflow. | Aplikace nemůže provést nákup, přijmout platbu, rezervovat kus ani synchronizovat prodání. | Pokud je cílem marketplace, nejdřív navrhnout veřejný Listing odděleně od konceptu, poté objednávku a stavový automat. |
| Střední | [services.py](../../products/services.py#L37-L166), [ai_engine.py](../../products/ai_engine.py#L50-L81) | Odhad z eBay používá maximálně 50 aktivních nabídek a filtruje EUR; bez dat používá náhodnou přirážku. | Vzorek nemusí být srovnatelný (stav, model, příslušenství); opakované lokální odhady nemusejí být reprodukovatelné. | Ukládat zdroj, čas, měnu a velikost vzorku, srovnávat více atributů a odhad testovat deterministicky. Výsledek označovat jako orientační. |
| Střední | [forms.py](../../products/forms.py#L103), [models.py](../../products/models.py#L238) | Upload má limit 8 MB, ale aplikace obrázky nedimenzuje ani nekomprimuje. | Velké rozměry zatěžují paměť, úložiště a přenos; smazání modelu nemusí odstranit fyzický soubor. | Ověřit rozměry, generovat náhledy, komprimovat, omezit typy a uklízet osiřelé soubory. |
| Střední | [views.py](../../products/views.py#L173-L237), [models.py](../../products/models.py#L171-L200) | Zprávy přijímají přímo POST text do `TextField`; není formulář s délkou/limitem četnosti. | Zprávy lze spamovat a posílat nepřiměřeně velké payloady; neexistuje moderace/blokování. | Formulář s `max_length`, rate limit, report abuse a moderátorská fronta. |
| Nízká | [models.py](../../products/models.py#L151-L160) | Recenze mají volně zadané `username`, nejsou navázané na účet ani dokončenou transakci. | Demo hodnocení nejsou důkazem obchodní zkušenosti. | V marketplace modelu navázat hodnocení na dokončenou objednávku a profil uživatele. |
| Nízká | [settings.py](../../resale_ai/settings.py#L145-L160), [.github/workflows/ci.yml](../../.github/workflows/ci.yml) | Console logging a CI existují, ale chybí produkční deployment, error monitoring, health checks a backup proces. | Selhání se těžko diagnostikují a obnova není ověřena. | Doplnit log context/request ID, monitoring, health/readiness a dokumentovaný test obnovy. |
| Nízká | [base.html](../../templates/base.html#L6-L9), [README.md](../../README.md) | CDN závislosti bez SRI, smíšený jazyk a dosud chybějící skutečné screenshoty. | Omezuje odolnost, přístupnost a prezentační kvalitu; externí zdroj může být nedostupný. | SRI nebo lokální assety, sjednotit češtinu, přidat bezpečně anonymizované screenshoty a WCAG kontrolu. |

## Bezpečnostní kontroly

- **SQL injection:** nenalezeno ručně sestavované SQL; Django ORM parametrizuje dotazy.
- **XSS:** Django templates standardně escapují proměnné; v prohlédnutých relevantních šablonách nebyl nalezen `|safe`. Dynamické HTML v eBay AJAX je však vhodné dál důsledně escapovat.
- **CSRF:** middleware a CSRF tokeny jsou přítomné; odhlášení, žádost, update i eBay refresh používají POST.
- **Autentizace:** Django session auth; heslo se ukládá přes `set_password` a registrační formulář v lokálním stromu používá password validators. Chybí ověření e-mailu, reset hesla a rate limiting.
- **Autorizace/IDOR:** soukromé listingy jsou načítané filtrem `owner=request.user`, cizí ID vrací 404; chat žádosti povolí správce nebo autora. Objednávky neexistují, IDOR pro objednávku tedy není relevantní.
- **Upload:** Pillow `ImageField`, limit 8 MB; chybí komprese, rozměrové limity, antivirová kontrola a automatický úklid osiřelých souborů.
- **Tajemství:** `.env` je ignorovaný a nebyl nalezen v Git historii; jeho obsah nebyl čten. Veřejný `.env.example` má prázdné eBay hodnoty. GitHub secrets nejsou samy o sobě runtime konfigurací aplikace.
- **Proxy:** aktuální lokální změna vypíná důvěru v `X-Forwarded-Proto`, dokud není explicitně nastaveno `TRUST_PROXY_SSL_HEADER=True`; proxy musí příchozí hlavičku vždy přepisovat.

## Doporučené pořadí

1. Před veřejným nasazením uzavřít produkční konfiguraci a otestovat `check --deploy`.
2. Opravit katalogový N+1, zprávy limitovat a označit demo recenze jako demo.
3. Rozhodnout, zda je cíl „nástroj pro přípravu přeprodeje“, nebo marketplace. Jen druhý cíl vyžaduje veřejné nabídky, objednávky a platby.
4. Přidat reportování obsahu, e-mail verifikaci a procesy exportu/výmazu účtu.
5. Teprve podle profilování řešit indexy, kompresi obrázků a externí monitoring.
