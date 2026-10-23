# A6 – Model hrozeb a zneužití

## Rozsah a aktiva

Analýza pokrývá současný monolit: Django session auth, veřejný katalog, žádosti/zprávy, soukromé `GeneratedListing`, obrázky, admin a externí eBay API. **Checkout, objednávky a platby nejsou implementovány**, proto jsou u abuse cases označeny jako budoucí návrhové riziko, ne jako existující zranitelnost.

Chráněná aktiva: hesla/session, osobní údaje účtu, obsah zpráv, soukromé listingy a poznámky, nahrané fotografie, integrita katalogu, eBay client secret/access token, dostupnost DB a reputace aplikace.

## STRIDE

| Část / hrozba | STRIDE | Současná opatření | Zbytkové riziko / návrh |
|---|---|---|---|
| Přihlášení a session | Spoofing, DoS, elevation | Django password hashing, session auth, password validators (lokálně), `next` redirect check, secure cookie při `DEBUG=False`. | Chybí rate limit, ověření/reset e-mailu, 2FA a detekce credential stuffing. Přidat throttling a bezpečný reset flow. |
| Soukromé listingy | Information disclosure, tampering | Queries detail/update/delete filtrují `owner=request.user`; cizí ID vrací 404. Form validuje workflow. | Testovat všechny nové endpointy; veřejné/objednávkové entity budou vyžadovat vlastní policy. |
| Katalogový produkt | Tampering, repudiation | Zápis omezen na staff/admin; ORM, CSRF, POST pro mutace. | Chybí audit log změn a historie moderace. |
| Žádosti a chat | Spoofing, tampering, information disclosure, DoS | Login required; `request_chat` povolí requester nebo staff; stav mění pouze staff; CSRF. | `TextField` přijímá text bez explicitního max length/rate limitu. `get_or_create` nemá v DB unique constraint `(product, requester)`, takže konkurenční POST může vytvořit duplicitní žádosti. Přidat formulář, unique constraint/migraci, abuse report a log zásahu. |
| Upload obrázků | Tampering, DoS, information disclosure | Django `ImageField`, Pillow validace a limit 8 MB; owner filtr privátních stránek. | Extrémní rozměry/decompression, storage exhaustion, osiřelé soubory, externí URL tracking; přidat rozměrový limit, transformaci, cleanup a CSP/host allowlist. |
| Admin | Elevation, repudiation | Django admin/staff decorators a standardní auth. | Chybí 2FA/přísnější admin session, audit log a oddělení superuser/staff rolí podle prostředí. |
| eBay API / secrets | Spoofing, information disclosure, DoS | Client credentials, token cache, timeout 10 s; klíče v env, `.env` gitignored. | API výpadek/rate limit/limit nákladů, cache proces-local, žádný circuit breaker. GitHub Actions secrets nejsou runtime konfigurace. Nezalogovat hlavičky/credential values. |
| Databáze a zálohy | Tampering, repudiation, availability | Migrations a ORM; lokální SQLite, volitelné PostgreSQL. | Bez automatických backup/restore testů, soft delete/audit trail; seed `--flush` je destruktivní. |
| Checkout budoucího marketplace | Spoofing, tampering, repudiation, DoS | Není implementováno. | Při implementaci webhook signature, idempotency key, transakční rezervace, stavy objednávky, audit a ochrana proti dvojímu prodeji jsou povinné. |

## Abuse cases

| Co když uživatel… | Dnešní stav | Opatření / důsledek |
|---|---|---|
| Změní cenu odeslanou ve formuláři | U generování se cena přijímá jako vstup a server ji validuje jako celé číslo >= 0. Není to závazná cena veřejného produktu. | Pokud vznikne veřejný listing/objednávka, server musí vždy znovu načíst aktuální cenu z DB; částka v prohlížeči není autorita. |
| Změní ID soukromého listing detail/update/delete | Query filtruje ID i owner. | Současně přidávat test cizího ID pro každý nový endpoint. |
| Změní ID requestu/chatu | Vyžaduje autentizaci a kontrolu requester/staff; cizí request vrací 404. | Zachovat object-level authorization i pro export, attachment a report endpoints. |
| Objedná už prodanou položku | Není checkout ani objednávkový endpoint; stav „sold“ se eviduje ručně. | Budoucí objednávku tvořit v atomic transakci s podmíněným přechodem `available -> reserved`, unikátní aktivní rezervací a idempotency. |
| Dvakrát klikne na zaplatit / webhook se zopakuje | Platby nejsou implementované. | Po výběru platební brány zpracovávat webhook idempotentně podle provider event ID; nespoléhat na redirect prohlížeče. |
| Nahraje škodlivý/obrovský soubor | `ImageField`/Pillow a 8 MB; chybí sken, dimenze, komprese, izolace storage. | Povolit jen potřebné rastrové formáty, limitovat pixely, překódovat obrázek, ukládat mimo webroot/private bucket a servírovat bezpečným content type. |
| Pošle extrémně dlouhou zprávu nebo spam | View čte `request.POST` přímo do `TextField`, bez explicitního formuláře/max length/throttle. | Limit těla, `max_length`, rate limit, antispam a bezpečný příznak/report. |
| Vloží HTML/JS do zprávy, recenze nebo názvu | Django template auto-escaping je výchozí a nebyl nalezen `|safe` v relevantních šablonách. | Nepřidávat `safe`/`mark_safe`; sanitizovat jen pokud bude potřeba povolené rich text. |
| Zkusí veřejně vystavit padělek/nelegální zboží | User-generated public listing neexistuje. | Před public listingem policy, report route, moderace, seller identity info a odůvodnění zásahu. |
| Paralelně odešle dvě stejné žádosti | `get_or_create` bez unikátního DB constraintu není zárukou uniqueness při race. | Přidat `UniqueConstraint(product, requester)` a migrační test duplicity. |

## Dvojí prodej / race condition budoucího checkoutu

Dnes žádný zákazník nekupuje `GeneratedListing`; race condition dvojí platby tudíž v současném kódu nevzniká. Při skutečném tržišti nesmí proces vypadat takto: `SELECT available`, potom `INSERT order` bez transakce. Dva requesty by oba mohly načíst `available`.

Bezpečnější postup v PostgreSQL: v atomic transakci zamknout/conditionálně aktualizovat listing na `reserved`, vytvořit objednávku s unikátním idempotency key, potvrdit rezervaci a teprve poté vytvořit payment intent. Platbu zachytit až podle ověřeného webhooku, ne klientského POSTu. Pokud payment timeoutne, použít expiraci rezervace a provider reconciliation. Je to budoucí návrh, ne současná implementace.

## Prioritní mitigace

1. **Před nasazením:** `DEBUG=False`, silný secret, TLS/HSTS po ověření proxy; secrets jen v runtime secret store.
2. **Zneužití:** rate-limit login/register/message, limity délky/request body, CAPTCHA až při riziku.
3. **Upload:** pixel/dimension limity, recompress, file cleanup, soukromé storage a bezpečné delivery headers.
4. **Integrita:** unique constraint pro request `(product, requester)`; transakční stavový automat před checkoutem.
5. **Důvěra:** report listing/user, moderační fronta, audit log rozhodnutí.
6. **Provoz:** monitoring 5xx/API errors, backup/restore test a postup pro rotaci eBay klíčů.
