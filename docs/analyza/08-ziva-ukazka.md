# A8 – Příprava na živou ukázku

## Scénář na 9 minut

| Čas | Co ukázat | Co říct / důkaz |
|---|---|---|
| 0:00–0:40 | Cíl a úvodní stránku | „Je to nástroj pro přípravu přeprodeje; není to checkout marketplace.“ |
| 0:40–1:40 | Katalog: vyhledávání, kategorie, cena, stránkování | Ukázat query parametry a Django `Paginator`. |
| 1:40–2:30 | Detail demo produktu | Odhad, recenze označit jako fiktivní demo, vysvětlit aktivní eBay asking price. |
| 2:30–3:10 | Přihlášení / registrace připraveného demo účtu | Neukazovat skutečné heslo ani osobní e-mail; slabé heslo je validátorem odmítnuto. |
| 3:10–5:00 | Generátor konceptu: položka, stav, náklady, případně obrázek | Vysvětlit validaci formu, uložený owner, upload limit a lokální heuristiku. Pro stabilitu lze eBay síťovou část přeskočit. |
| 5:00–6:10 | Detail soukromého konceptu a texty Vinted/eBay | Zkopírovat text; demonstrovat, že jde o šablonu k ruční úpravě, nikoli automatické publikování. |
| 6:10–7:10 | Změna stavu na prodáno a skutečné náklady | Vložit cenu/dopravu/poplatek a vysvětlit `realized_net_profit`. |
| 7:10–8:00 | Dashboard/inventář | Ukázat počty stavů a součet čistého zisku. |
| 8:00–8:40 | Administrace a žádost/chat | Přihlásit staff demo účet, ukázat žádost a role žadatele vs správce. |
| 8:40–9:00 | Testy a shrnutí limitů | Spustit `manage.py test`; stručně uvést, že košík/platba/objednávky nejsou součástí scope. |

Neukazovat při obhajobě tajné `.env`, API klíče, skutečné osobní údaje ani eBay odpověď vydávanou za skutečnou prodejní historii.

## Rizika a záložní plán

| Riziko | Prevence | Záloha |
|---|---|---|
| Internet/eBay API nefunguje | EBay data jsou volitelná; zkontrolovat klíče předem, nikdy nevolat naživo poprvé při obhajobě. | Ukázat fallback bez tržních dat a připravený screenshot s časem/vzorkem. |
| DB prázdná nebo chybná | Předem izolovaná demo DB, `migrate`, `seed_data` v lokálním `DEBUG=True`; projít celý scénář. | Export/snapshot DB kopie, který neobsahuje osobní data. `seed_data --flush` nikdy nad cennou DB. |
| Zapomenuté heslo / role admina | Vytvořit separátní demo buyer/staff účty lokálně, ověřit login, uložit hesla bezpečně mimo prezentaci. | Předem přihlásit demo účty v oddělených prohlížečových profilech. Nepoužít produkční účet. |
| Nahrávání obrázku trvá | Malý lokální demo soubor s právy použití. | Použít `image_url` / vynechat fotku a vysvětlit fallback. |
| Vývojový server nebo statika selžou | Zkouška na témže počítači a síti; vypnout zbytečné programy. | Krátký offline videozáznam a screenshoty. Přiznat, že nejde o live běh. |
| Seed data působí jako reálné recenze | Viditelně označit „DEMO DATA – recenze nejsou ověřené“. | Před prezentací vypnout/nezobrazit hodnocení, pokud označení nelze doplnit. |
| Ukázka spustí destruktivní `--flush` | Neprovozovat flush na jediné kopii. | Obnovit demo databázi z neměnné kopie. |

## Návrh demonstračních dat

Použij smyšlené uživatele a jasně označené syntetické údaje:

- `demo_buyer_01@example.invalid` – běžný kupující; doména `.invalid` není doručitelná.
- `demo_seller_01@example.invalid` – prodejce s několika soukromými koncepty.
- `demo_admin` – lokální staff účet bez reálného e-mailu.
- Kategorie: elektronika, oblečení, sport, hry, knihy.
- Ukázkové položky: „Bezdrátová sluchátka – demo“, „Sportovní bunda – demo“, „Herní ovladač – demo“, „Fotoaparát – demo“.
- Vymyslet vlastní modelové názvy a fotografie vytvořené studentem nebo licencované pro demo; nepoužívat tvrzení o pravosti, sériová čísla, osobní adresy, skutečné kontakty ani neověřené recenze.
- U obrázků uvést zdroj/licenci v odděleném seznamu. Fotografie z demo seed nyní pocházejí z Unsplash a nemusejí odpovídat pojmenovanému branded produktu; pro obhajobu je vhodné vytvořit vlastní obrázky.

## Před startem

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Příkazy spouštět jen v lokálním demo prostředí. `DEBUG=False` záměrně blokuje `seed_data`.
