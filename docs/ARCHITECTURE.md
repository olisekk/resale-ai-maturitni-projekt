# Architektura aplikace

ResaleAI je serverová webová aplikace v Django. Hlavní projektová konfigurace je v `resale_ai/`; aplikace `products/` obsahuje veřejný katalog i soukromý pracovní postup prodejce.

## Zpracování nabídky

1. Přihlášený uživatel odešle formulář z `templates/generator/generate_listing.html`.
2. `products/views.py` ověří vstup pomocí `GeneratedListingForm` a případně zavolá `products/services.py` pro ceny aktivních nabídek z eBay Browse API.
3. `products/ai_engine.py` podle stavu, popisu a dostupných cenových údajů vypočítá orientační cenu, signál poptávky, titulek, text a cenový verdikt.
4. Výsledek se uloží do modelu `GeneratedListing` v `products/models.py`, vždy ve vazbě na vlastníka účtu.
5. Prodejce může položku upravovat přes přehled a detail; při označení jako prodaná zadá skutečnou cenu a případné skutečné náklady.

## Hlavní části

- `resale_ai/settings.py` načítá konfiguraci prostředí, databázi, statické soubory a lokální nebo S3 úložiště.
- `resale_ai/urls.py` zapojuje URL aplikace, administraci a vývojové servírování uživatelských obrázků.
- `products/models.py` definuje veřejné produkty, recenze, trendy, žádosti o produkty, zprávy a soukromé nabídky.
- `products/forms.py` validuje vstupy pro katalog, registraci a pracovní postup prodejce.
- `products/views.py` obsluhuje stránky, přihlášení, autorizaci a zpracování formulářů.
- `products/services.py` komunikuje s eBay Browse API; přístupový token se ukládá do Django cache.
- `products/ai_engine.py` obsahuje lokální heuristiky. Nevolá jazykový model ani externí AI službu.
- `templates/` vykresluje stránky, `static/css/custom.css` obsahuje vlastní vzhled.
- `products/tests.py` ověřuje cenové výpočty, API integraci, autorizaci a prodejní workflow.

## Cenová data a omezení

Odhad bez eBay vychází z pořizovací ceny, stavu a slov v popisu; část výpočtu používá náhodnou přirážku. Název a popis nabídky se skládají podle předem připravených pravidel a šablon, nejde o generativní AI. eBay Browse API vrací aktivní nabídkové ceny, nikoli potvrzené prodejní ceny. Aplikace pracuje s cenami v EUR a při nedostupnosti API pokračuje bez tržních dat.

Sazbu i pevnou část poplatku zadává uživatel. Odhadovaný čistý výsledek používá zadané náklady a sazby; realizovaný výsledek po prodeji může použít skutečnou dopravu a poplatek.

## Konfigurace

Lokální vývoj používá SQLite a ukládá obrázky do `media/`. Přehled proměnných prostředí je v `.env.example`. Pro eBay je nutné nastavit `EBAY_CLIENT_ID` a `EBAY_CLIENT_SECRET`. PostgreSQL se zapíná pomocí `DB_ENGINE=postgresql`; S3 úložiště pomocí `STORAGE_BACKEND=s3` a příslušných údajů o bucketu. Produkční provoz vyžaduje vlastní tajný klíč, správné povolené hostitele, HTTPS a zálohování databáze i souborů.

## Ověření

Z kořenové složky spusť:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

GitHub Actions používá stejné kontroly při pushi a pull requestu.
