# A0 – Průzkum projektu

**Stav analýzy:** 21. 10. 2026. Posuzován je aktuální pracovní strom včetně lokálních, dosud necommitnutých oprav. Nejde o .NET solution.

## Co projekt dělá

ResaleAI je server-rendered webová aplikace pro přípravu prodeje věcí z druhé ruky. Veřejná část nabízí katalog produktů spravovaný administrátorem, vyhledávání a filtrování, trendy, hodnocení a žádosti zájemců. Přihlášený uživatel si může vytvořit soukromý koncept prodejní nabídky, nahrát jednu fotografii, získat orientační cenový odhad a textové návrhy, evidovat stav položky a porovnat očekávaný a realizovaný zisk.

Volitelné eBay Browse API dodává ceny aktivních nabídek. Nejde o historii skutečně dokončených prodejů. Aplikace nezveřejňuje uživatelské koncepty jako veřejné inzeráty a nemá nákupní košík, objednávku, platbu ani escrow. Označení „AI“ v UI je marketingové: výpočet probíhá pomocí lokálních pravidel a šablon, nikoli pomocí jazykového modelu.

## Technologie

| Technologie | Zjištěný stav | Úloha |
|---|---|---|
| Python | Kód používá syntaxi pro Python 3.10+; CI testuje Python 3.12. | Serverová logika. |
| Django | `Django>=5.2,<6.0`; v aktuálním virtuálním prostředí ověřeno Django 5.2.17. | URL routing, ORM, šablony, auth, admin a testy. |
| SQLite | Výchozí databáze lokálního běhu. | Vývoj a testy. |
| PostgreSQL | Volitelné nastavení přes `DB_ENGINE=postgresql`; závislost `psycopg[binary]`. | Alternativní databáze pro hosting. |
| HTML, Django Templates, CSS | Šablony v `templates/`, vlastní CSS v `static/css/custom.css`. | Serverově vykreslené rozhraní. |
| Bootstrap 5.3.2, Bootstrap Icons 1.11.3 | Načítají se z CDN v `templates/base.html`. | Responzivní layout a ikony. |
| DM Sans, Space Grotesk | Google Fonts CDN. | Typografie. |
| Pillow | Zpracování a validace nahrávané fotografie. | `ImageField` a formulář. |
| Requests | HTTP klient pro eBay OAuth a Browse API. | Externí ceny. |
| python-decouple | Závislost v `requirements.txt`. | Proměnné prostředí a lokální `.env`. |
| django-storages[s3] | Volitelné. | S3 kompatibilní úložiště. |
| GitHub Actions | `.github/workflows/ci.yml`, Python 3.12. | Check, migrace a testy na push/PR. |

Projekt nepoužívá .NET, ASP.NET, Blazor, Entity Framework Core, React, Vue, npm ani NuGet. Závislosti jsou uvedeny jako rozsahy verzí v `requirements.txt`; lockfile pro Python v repozitáři není.

## Architektura

Jedna Django aplikace `products` zajišťuje většinu funkcí. `resale_ai/` obsahuje nastavení, hlavní URL a WSGI entrypoint. Požadavek vede z `products/urls.py` do pohledu v `products/views.py`; formuláře validují vstup, modely ukládají data přes ORM, `ai_engine.py` počítá odhad a `services.py` volitelně komunikuje s eBay. Šablony odpověď vykreslí do HTML.

Jde o monolit s oddělenými soubory podle odpovědnosti, nikoli o vícevrstvou nebo distribuovanou architekturu. Dependency injection, repository a DTO vrstva zde nejsou potřeba ani implementovány.

## Hlavní funkce

- Veřejný katalog, hledání podle názvu/popisu, kategorie, řazení a stránkování.
- Detail katalogového produktu s odhadem, přehledem recenzí a návrhem textu pro Vinted/eBay.
- Registrace, přihlášení a odhlášení.
- Žádost registrovaného uživatele o katalogový produkt a komunikace mezi žadatelem a správcem.
- Soukromý generátor konceptu nabídky, volitelná fotografie nebo URL obrázku, cenové vstupy a návrh textů.
- Inventář soukromých konceptů se stavy připraveno/vystaveno/prodáno a finančním souhrnem.
- Volitelné načtení EUR cen aktivních nabídek eBay.de.
- Django admin pro katalog, trendy, recenze a žádosti.

## Struktura

```text
resale_ai/                 # nastavení projektu, URL, WSGI
products/                  # modely, formuláře, views, API služby, výpočty
  migrations/              # 7 migrací databázového schématu
  management/commands/     # seed_data pro demonstrační obsah
  tests.py                 # 27 testů v aktuálním pracovním stromu
templates/                 # veřejné stránky, auth, generátor, inventář
static/css/                # vlastní CSS
media/                     # lokální nahrané obrázky, mimo Git
.github/workflows/ci.yml   # automatické kontroly
README.md                  # návod a popis
requirements.txt           # Python závislosti
docs/                      # architektura a tato analýza
```

## Konfigurace a Git

Nastavení čte `DEBUG`, `SECRET_KEY`, hostitele, databázi, úložiště, eBay klíče a další hodnoty z prostředí nebo `.env`. `.env`, SQLite databáze, virtuální prostředí a `media/` jsou ignorovány Gitem. `.env.example` obsahuje vzorové, prázdné API klíče. Audit Git historie nenašel `.env` ani `db.sqlite3` mezi verzovanými soubory; jejich hodnoty nebyly čteny.

V této pracovní kopii je jediný commit `ed19097 Initial release: ResaleAI maturitni projekt`, větev `main` sleduje `origin/main`. V době analýzy existují necommitnuté lokální změny včetně opravy validace hesla, autorizace chatu, nastavení proxy, demo seedování, admin query a dokumentace. GitHub proto nemusí obsahovat aktuální pracovní stav.

## Testy a kontroly

Django testy pokrývají odhady, eBay API s mocky, ochranu POST/CSRF workflow, autorizaci, finanční výpočty, registraci, seed command, admin dotazy a stránkování. Poslední ověřený lokální běh: 27 testů prošlo; `manage.py check` a `makemigrations --check --dry-run` prošly. `manage.py check --deploy` hlásí šest produkčních varování kvůli lokálním výchozím hodnotám (`DEBUG`, `SECRET_KEY`, HTTPS/HSTS a secure cookies).

## Rozsah

Analýza popisuje prototyp a jeho aktuální pracovní strom. Právní poznámky jsou orientační, konkurence se může lišit podle země, účtu a data. Tento dokument ani zbytek složky `docs/analyza/` nenahrazuje právní posudek ani bezpečnostní audit externím specialistou.
