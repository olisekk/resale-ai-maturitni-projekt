# A3 – Průvodce kódem pro obhajobu

Tento průvodce popisuje skutečné toky. Sekvence „objednávka“ a „platba“ nejsou nakresleny jako funkční části, protože v aplikaci neexistují.

## Mapa projektu

- `manage.py` – vstup pro příkazy Django.
- `resale_ai/settings.py` – konfigurace prostředí, middleware, databáze, auth, úložiště, logging.
- `resale_ai/urls.py` – admin, aplikační URL a vývojové servírování médií.
- `products/urls.py` – mapování cest na views.
- `products/models.py` – `Product`, `Review`, `Trend`, `ProductRequest`, `ProductMessage`, `GeneratedListing` a volby stavů/kategorií.
- `products/forms.py` – validace katalogu, registrace, uploadu a prodejního workflow.
- `products/views.py` – HTTP kontroléry a kontrola oprávnění.
- `products/ai_engine.py` – lokální cenové heuristiky a textové šablony.
- `products/services.py` – eBay OAuth a Browse API.
- `products/admin.py` – interní správa katalogu, recenzí, trendů a žádostí.
- `products/management/commands/seed_data.py` – demonstrační katalog.
- `products/migrations/` – verzované změny schématu.
- `templates/` – serverové HTML šablony; `static/css/custom.css` – styly.
- `products/tests.py` – unit a integrační testy.

## Toky

### 1. Registrace

`products/urls.py` → `register_view` → `UserRegistrationForm` → password validators → `set_password` → Django `User` → session login → přesměrování na dashboard.

```mermaid
sequenceDiagram
    actor Uživatel
    participant URL as products.urls
    participant V as register_view
    participant F as UserRegistrationForm
    participant DB as Django ORM
    participant Auth as Django session auth
    Uživatel->>URL: POST /register/
    URL->>V: register_view(request)
    V->>F: Validace dat
    F->>F: Shoda hesel, síla hesla, unikátní username
    F->>DB: User.set_password() a save()
    V->>Auth: login(request, user)
    V-->>Uživatel: redirect /dashboard/
```

### 2. Přihlášení a odhlášení

`login_view` použije Django `AuthenticationForm`; Django ověří hash hesla. Po loginu se bezpečně kontroluje `next`. Odhlášení přijímá pouze POST.

```mermaid
sequenceDiagram
    actor Uživatel
    participant V as login_view
    participant F as StyledLoginForm
    participant Auth as Django auth/session
    Uživatel->>V: POST username + password
    V->>F: Validace credentials
    F->>Auth: Ověřit hash hesla
    Auth-->>V: User nebo chyba
    V->>Auth: login(), vytvoření session
    V-->>Uživatel: bezpečný redirect
```

### 3. Katalog a vyhledávání

`product_list` čte query parametry `search`, `category`, `sort`, filtruje ORM queryset, řadí a použije `Paginator` po 12 položkách. Data jsou v `Product`, katalog ovládá admin.

```mermaid
sequenceDiagram
    actor Návštěvník
    participant URL as products.urls
    participant V as product_list
    participant ORM as Django ORM
    participant T as product_list.html
    Návštěvník->>URL: GET /products/?search=...&category=...
    URL->>V: product_list(request)
    V->>ORM: filtrování, anotace hodnocení, řazení
    V->>ORM: Paginator, stránka po 12 položkách
    ORM-->>T: products + filtry + page_obj
    T-->>Návštěvník: HTML seznam / empty state
```

Poznámka pro obhajobu: současná šablona kontroluje `product.review_count`, vlastnost, která dotazuje DB znovu. To je kandidát na další optimalizaci N+1.

### 4. Detail katalogové položky a žádost o produkt

Detail `product_detail` načte `Product`, recenze, seskupené počty hodnocení a podobné produkty. Přihlášený běžný uživatel odešle POST na `create_product_request`; vznikne `ProductRequest` a úvodní `ProductMessage`. Není to nákup ani objednávka.

```mermaid
sequenceDiagram
    actor Kupující
    participant V as product_detail
    participant T as product_detail.html
    participant R as create_product_request
    participant DB as ProductRequest/ProductMessage
    Kupující->>V: GET /products/{id}/
    V-->>T: produkt, hodnocení, podobné produkty
    T-->>Kupující: detail + tlačítko Mám zájem
    Kupující->>R: POST se zprávou + CSRF
    R->>DB: get_or_create žádost a uložit zprávu
    R-->>Kupující: redirect na detail produktu
```

### 5. Chat k žádosti

`request_chat` vyžaduje přihlášení; povolí správce nebo původního žadatele. Žadatel může posílat zprávy, ale stav mění jen správce. Tento chat se váže na katalogový `ProductRequest`, ne na veřejný prodejní listing.

```mermaid
sequenceDiagram
    actor Žadatel
    participant V as request_chat
    participant DB as ProductRequest/ProductMessage
    Žadatel->>V: GET /dashboard/requests/{id}/
    V->>DB: Načíst žádost
    V->>V: Ověřit requester == user nebo is_staff
    V-->>Žadatel: konverzace
    Žadatel->>V: POST message
    V->>DB: uložit zprávu, stav mění jen staff
    V-->>Žadatel: aktualizovaná konverzace
```

### 6. Vytvoření soukromého prodejního konceptu

`generate_listing` validuje `GeneratedListingForm`, zkusí získat eBay data, zavolá `run_ai_generation`, uloží `GeneratedListing(owner=request.user, ...)` a přesměruje na detail. `ImageField` ukládá maximálně 8MB obrázek. Koncept zůstává soukromý.

```mermaid
sequenceDiagram
    actor Prodejce
    participant V as generate_listing
    participant F as GeneratedListingForm
    participant E as eBay service
    participant A as ai_engine
    participant DB as GeneratedListing
    Prodejce->>V: POST formulář + případný soubor
    V->>F: Validovat vstupy a obrázek
    F-->>V: cleaned_data
    V->>E: fetch_ebay_prices(název)
    E-->>V: EUR ceny nebo unavailable
    V->>A: run_ai_generation(vstupy, ceny)
    A-->>V: odhad, demand, titulek, popis, verdict
    V->>DB: uložit pod vlastníkem
    V-->>Prodejce: redirect na soukromý detail
```

### 7. eBay OAuth a cenové nabídky

`_get_ebay_access_token` nejprve zkusí Django cache; jinak použije client credentials. `fetch_ebay_prices` hledá maximálně 50 fixed-price položek, vybere EUR ceny, spočítá min/avg/max a zachytí síťové chyby s timeoutem. Výsledek tvoří nabídkové ceny, nikoli skutečné prodeje.

```mermaid
sequenceDiagram
    participant App as products.services
    participant Cache as Django cache
    participant OAuth as eBay OAuth
    participant API as Browse API
    App->>Cache: get token
    alt token není v cache
        App->>OAuth: POST client_credentials
        OAuth-->>App: access_token + expires_in
        App->>Cache: uložit token před expirací
    end
    App->>API: GET search, limit 50, fixed price
    API-->>App: itemSummaries
    App->>App: ponechat EUR a spočítat min/avg/max
```

### 8. Označení konceptu jako prodaného

`ai_listing_detail` a `update_ai_listing` filtrují podle ID i vlastníka. `ListingWorkflowForm` vyžaduje skutečnou prodejní cenu při statusu `sold`. View nastaví `sold_at` a model vypočítá skutečný čistý zisk. Neprobíhá blokace zásoby ani platba.

```mermaid
sequenceDiagram
    actor Prodejce
    participant V as update_ai_listing
    participant F as ListingWorkflowForm
    participant DB as GeneratedListing
    participant M as model profit properties
    Prodejce->>V: POST status=sold + skutečná cena/náklady
    V->>DB: get_object_or_404(pk, owner=user)
    V->>F: validovat změnu stavu
    F-->>V: validní data nebo chyby
    V->>DB: uložit status, sold_at, náklady
    M->>M: realized_net_profit
    V-->>Prodejce: redirect na detail
```

### 9. Admin a demonstrační data

`ProductAdmin`, `TrendAdmin` a další registrace poskytují Django admin. V aktuálním pracovním stromu ProductAdmin annotuje `_review_count`, aby se vyhnul N+1 dotazu. `seed_data` přidá katalog, trendy a fiktivní recenze; lokální změna příkaz odmítá při `DEBUG=False`. Při `--flush` maže produkty, recenze a trendy, proto ho používej jen v oddělené demo databázi.

```mermaid
sequenceDiagram
    actor Správce
    participant Admin as Django admin
    participant ORM as Django ORM
    participant DB as SQLite/PostgreSQL
    Správce->>Admin: Přihlášení staff účtem
    Admin->>ORM: seznam produktů + Count(reviews)
    ORM->>DB: SELECT + agregace
    DB-->>Admin: řádky s _review_count
    Admin-->>Správce: admin seznam
```

## Co aplikace nedělá

Neexistuje veřejná registrace inzerátů od uživatelů, checkout, objednávka, platební brána, doprava/štítky, escrow, spor, reklamace ani refundace. Není tedy možné implementačně ukazovat „dvojí nákup“, „refund“ nebo platbu. Vhodná obhajoba je vysvětlit jejich absence a navrhnout jejich samostatné modely/stavy.

## Slovník

| Pojem | Jednoduché vysvětlení | Použití v projektu |
|---|---|---|
| Django view | Funkce obsluhující HTTP cestu. | `products/views.py`. |
| Django ORM | Python API, které skládá parametrizované SQL dotazy. | Modely/querysety. |
| Form | Validace nedůvěryhodného vstupu z HTML formuláře. | `products/forms.py`. |
| Middleware | Kód, který zpracuje každý požadavek před/po view. | CSRF, session, auth. |
| Migrace | Verze změny databázového schématu. | `products/migrations/`. |
| Session autentizace | Po loginu server vystaví cookie s identifikátorem session; heslo se při požadavcích neposílá znovu. | Django auth. |
| Hash hesla | Jednosměrný odvozený zápis hesla, který se používá k ověření. | `User.set_password`. |
| Foreign key | Odkaz řádku na související řádek jiné tabulky. | vlastník nabídky, zpráva žádosti. |
| OAuth client credentials | Serverový způsob, jak služba získá přístupový token bez interakce uživatele. | eBay Browse API. |
| Cache | Dočasné úložiště výsledků pro omezení opakovaných výpočtů/volání. | eBay access token. |
| Annotate | Přidá databázový vypočtený sloupec do výsledků querysetu. | Počet recenzí v adminu. |
| `@login_required` | Dekorátor, který vyžaduje přihlášenou session. | Soukromé views. |
| IDOR | Přístup k cizímu záznamu pouhou změnou ID. | Brání mu filtr `owner=request.user`. |

## Místa, která je nutné umět vysvětlit

1. Proč `GeneratedListing` zůstává soukromý a liší se od katalogového `Product`.
2. Co je přesně vstupem `calculate_estimated_price`, jak funguje fallback a proč je náhodný.
3. Proč eBay ceny nejsou completed sales a jak se filtruje měna.
4. Rozdíl `net_profit` versus `realized_net_profit`.
5. Jak owner filtr brání IDOR a proč se vrací 404.
6. Jak Django formulář validuje upload a kde je limit 8 MB.
7. Jak `ProductRequest` a `ProductMessage` tvoří konverzaci.
8. Co dělá `Count`, `Cast`, `Coalesce`, `ExpressionWrapper` v dashboardu.
9. Proč demo seed nesmí být spuštěn v produkci.
10. Která část eBay, SMTP, DB a media může selhat a jak se to projeví uživateli.
