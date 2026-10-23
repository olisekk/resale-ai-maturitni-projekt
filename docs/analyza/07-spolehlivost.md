# A7 – Spolehlivost, škálovatelnost a kvalita dat

## Chování při výpadku závislostí

| Závislost | Současné chování | Riziko / zlepšení |
|---|---|---|
| SQLite/PostgreSQL | DB view neobslouží; bez vlastního produkčního 500 handleru uživatel podle `DEBUG`/hostingu uvidí obecnou nebo debug chybu. | Monitoring dostupnosti, zálohy, migrační runbook, vlastní bezpečná 500 stránka, test obnovy. |
| eBay OAuth/Browse API | `requests` používá timeout 10 s; service vrátí `available=False`, generátor pokračuje s lokálním odhadem. | Uložit strukturovaný důvod/metrics, retry jen pro bezpečné transient chyby s backoff, circuit breaker/kvóty, nezobrazovat raw exception text. |
| e-mail | V projektu není e-mail backend/workflow pro verifikaci ani reset hesla. | Nejde o momentální degradaci: funkce vůbec není. Přidat jen s nastaveným SMTP/providerem a retry/outbox. |
| S3 | Volitelný backend; špatná konfigurace bucketu může způsobit chybu upload/download. | Ověřit access policy, versioning, retry, lifecycle, backup a alarmy; S3 credentials nevkládat do repozitáře. |
| Lokální `media/` | Uploady jsou na disku hostitele, není vidět záloha ani automatický úklid po smazání modelu. | Výpadek/obnova stroje může ztratit média; přidat bucket, zálohu a orphan cleanup. |
| Bootstrap/Fonts CDN | Bez internetu mohou chybět styly, ikony nebo fonty. | Pro obhajobu držet lokální fallback, případně vendorovat schválené assety a přidat SRI. |
| GitHub Actions | CI testuje zdroj; neprokazuje dostupnost deploy hostingu ani eBay credentials. | Oddělit build/test od deploy, přidat staging smoke check, žádné produkční secrets do fork PR workflow. |

## 10 000 položek / 1 000 uživatelů

- **Katalog:** stránkuje 12 záznamů, ale `icontains` přes `name/description` typicky dělá scan bez fulltext/index strategie. Count a agregace hodnocení přidají práci. Template v aktuálním stromu volá `product.review_count` pro položku; to je N+1 navzdory anotovanému `review_total`.
- **Katalogový detail:** recenze a související produkty se načítají odděleně; limit recenzí není vidět. Produkt s tisíci recenzemi může generovat velkou HTML odpověď. Přidat stránkování recenzí nebo agregace bez načtení všech.
- **Soukromý dashboard:** `_seller_listing_summary` provádí agregace SQL výrazem, což je vhodnější než načíst všechny nabídky. Výrazy jsou ale náročnější na vysvětlení a potřeba je testovat na SQLite i PostgreSQL.
- **Trendy:** `trends.first()` a `trends.exists()` jsou samostatná vyhodnocení querysetu; změnit na jeden načtený objekt/query nebo anotaci. Dopad je malý, ale jednoduchá optimalizace.
- **DB:** filtry podle owner/status/created_at a produkt/category/created_at nemají zjevně navržené indexy. Při PostgreSQL změřit `EXPLAIN ANALYZE`, následně přidat indexy/migrace. Nepředpokládat, že index pomůže `icontains '%text%'`.
- **Obrázky:** maximum uploadu 8 MB omezuje velikost souboru, ne rozměry/počet. Bez recompress a thumbnail variant roste storage i traffic.
- **API:** eBay limit 50 je omezený vzorek; token cache je Django cache a default lokální backend není sdílený mezi procesy/serverem.
- **1 000 uživatelů:** samotný počet účtů nemusí být problém; kritické jsou paralelní zápisy, session/cache/DB nastavení, spam a objem obrázků. Bez load testu nelze slíbit kapacitu.

## Konzistence, retence a obnova

- Migrace jsou verzované; `makemigrations --check --dry-run` kontroluje necommitnuté změny modelů.
- Foreign keys používají `CASCADE`. Smazání uživatele může smazat listingy, žádosti a zprávy; politika zachování důkazů/mazání osobních údajů není stanovena.
- Django `FileField` nezaručuje odstranění fyzického souboru při smazání DB řádku; může vznikat orphan media.
- `seed_data` je idempotentní jen částečně díky `get_or_create`; extra usernames/comments jsou náhodné. `--flush` maže všechny katalogové Product/Review/Trend záznamy, ne pouze vlastní demo záznamy. Proto se nesmí spouštět proti uživatelské/prod DB.
- Soft delete, outbox, transakční objednávky a audit log neexistují.
- `.gitignore` vynechává `db.sqlite3`, `media/` a `.env`; žádný zálohovací skript/CI job není doložen.

### Doporučený backup plán pro budoucí provoz

1. Zvolit PostgreSQL a S3/objektové úložiště pro média.
2. Denní šifrovaný backup DB a verzování/backup objektů; retenční interval podle provozovatele.
3. Uložit kopii mimo účet/region produkce a chránit přístup.
4. Čtvrtletně obnovit do izolovaného prostředí a ověřit migrace, počet řádků i otevření obrázků.
5. Sepsat RPO/RTO a kontakty pro výpadek.

Čísla RPO/RTO se stanovují podle reálného provozu, nikoli odhadem do školní práce.

## Logování a monitoring

Aktuální `LOGGING` má root logger na konzoli a úroveň podle `LOG_LEVEL`. Není zde Sentry/APM, structured JSON, alerty, health endpoint ani request/correlation ID. Při výpadku může Django zapsat traceback do server logu; produkční uživatel má dostat obecnou bezpečnou stránku 500. Nikdy nelogovat hesla, session cookie, eBay client secret ani Authorization headers.

Minimální před-obhajobní diagnostika: umět spustit `manage.py check`, zkontrolovat server log, stav DB, počet produktů a přítomnost upload directory; pro eBay vysvětlit fallback bez zveřejnění klíčů.
