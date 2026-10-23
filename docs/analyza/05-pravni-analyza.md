# A5 – Právní a compliance analýza

> **Nejde o právní poradenství.** Jde o orientační technický checklist pro školní prototyp. Pokud bude služba veřejně nabízena nebo bude zpracovávat reálné objednávky, provozovatel musí nechat role, právní základy, texty a procesy posoudit kvalifikovaným právníkem a pověřencem podle skutečných okolností.

## 1. Osobní údaje zjištěné v kódu

| Oblast | Zjištěná pole / zdroj | Poznámka |
|---|---|---|
| Účet | Django `User.username`, `email`, interní `password` hash, datum vytvoření/posledního přihlášení, `is_staff`. | Heslo se ukládá přes Django hashovací systém; raw password je jen při registraci. |
| Žádosti | `ProductRequest.requester`, text, stav a časové značky. | Vazba na účet a produkt. |
| Zprávy | `ProductMessage.sender`, `text`, čas a vazba na žádost. | Text může uživatel dobrovolně vložit a může obsahovat osobní údaje. |
| Soukromé koncepty | Název položky, popis, cena, náklady, poznámky, platforma, stav, datum a případný obrázek/URL. | Poznámky mohou nechtěně obsahovat osobní nebo obchodně citlivé údaje. |
| Veřejný katalog | `Product`, recenze s volným `username` a komentářem, `Trend`. | Demo seed nyní vytváří fiktivní názvy/recenze; musí být označeny jako demo. |
| Technické údaje | Session/CSRF cookies, serverové logy, IP/access metadata podle hostingu, obrázky v `media/` nebo S3. | Záleží na proxy, webserveru, CDN a logování; inventář údajů ověřit v konkrétním deploymentu. |
| Externí služby | eBay query s názvem produktu; Bootstrap, ikony a Google Fonts CDN. | CDN uvidí síťové údaje návštěvníka; eBay obdrží dotaz na produkt. Zkontrolovat poskytovatele a jejich podmínky. |

Kód neobsahuje model platebních karet, bankovních účtů, objednávek ani doručovacích adres. Přidání checkoutu by významně rozšířilo rozsah osobních/finančních dat a právních povinností.

## 2. GDPR – otázky, které musí provozovatel zodpovědět

- **Správce:** určit fyzickou/právnickou osobu, účel a prostředky zpracování. „Školní demo“ samo o sobě neurčuje právní roli, pokud bude veřejně dostupné.
- **Právní základy:** účet a skutečně poskytovaná služba mohou být nezbytné pro smlouvu (čl. 6 odst. 1 písm. b); bezpečnostní logy/ochrana proti zneužití mohou vyžadovat posouzení oprávněného zájmu (písm. f); zákonné účetní povinnosti mohou spadat pod písm. c, pokud by vznikly platby. Souhlas patří jen k účelům, pro které je skutečně dobrovolný; není univerzálním základem.
- **Minimalizace:** registrace nyní vyžaduje username a heslo, e-mail není povinný. Nepřidávat telefon, adresu, identifikační doklad ani polohu bez prokázané potřeby.
- **Transparentnost:** vysvětlit účely, právní základy, příjemce/zpracovatele, přenosy, retenční lhůty, práva a kontakt správce před sběrem údajů.
- **Retence:** stanovit konkrétní lhůty pro účet, žádosti, chat, logy, obrázky, zálohy a zákonné doklady. V aplikaci nejsou retenční joby ani mazání účtu. Django `on_delete=CASCADE` může odstranit některé relace, ale nepředstavuje ověřený export/erase workflow a nemaže automaticky soubory `ImageField`.
- **Práva osob:** vytvořit proces pro přístup, opravu, výmaz, omezení, námitku, přenositelnost a případné odvolání souhlasu. Výmaz může mít zákonné výjimky; nevydávat automatickou absolutní garanci.
- **Zpracovatelé:** sepsat seznam hostingu, eBay, e-mailu, storage, CDN/fontů, analytics/reklamy (pokud se přidají) a uzavřít potřebné smlouvy/DPA. Prověřit přenosy mimo EHP.
- **Bezpečnost:** řízení přístupů, minimální oprávnění, HTTPS, zálohy, incident plan, logy bez hesel/tokenů, retence a případná DPIA podle rizika.

## 3. Cookies a podobné technologie

Základní Django session a CSRF cookies jsou nezbytné pro přihlášení/ochranu formulářů a musí být vysvětleny v zásadách. Projekt nyní obsahuje externí fonty a CSS/JS z CDN, ale v `base.html` není preference banner. Před nasazením zjistit, zda se ukládají další cookies nebo identifikátory; nepovinné analytické/reklamní technologie nesmějí být spuštěny před platným souhlasem tam, kde jej vyžaduje aktuální právní režim. Odmítnutí nepovinných cookies musí být stejně dostupné jako přijetí; zaznamenat verzi a čas volby a umožnit změnu.

Zákon č. 127/2005 Sb. v § 89 odst. 3 upravuje ukládání/získání přístupu k údajům v koncovém zařízení a výjimku pro nezbytné účely. Konkrétní aplikovatelnost na každý tracker ověřit s odborníkem.

## 4. DSA a online tržiště

Nařízení (EU) 2022/2065 (DSA) rozlišuje různé typy zprostředkovatelských služeb a povinnosti závisejí na roli, velikosti a konkrétních funkcích. Pokud ResaleAI umožní spotřebitelům uzavírat na dálku smlouvy s obchodníky, mohou být relevantní zejména povinnosti online tržišť včetně získávání/ověřování informací o obchodnících (čl. 30), přístupu k informacím o produktu/smlouvě a compliance-by-design (čl. 31), oznámení nezákonného obsahu (čl. 16), odůvodnění zásahů a interních stížností. U školního prototypu bez veřejných uživatelských inzerátů a checkoutu nelze bez dalšího tvrdit, že všechny povinnosti plně dopadají; klasifikaci musí posoudit provozovatel právně.

Technické minimum pro zamýšlené tržiště: tlačítko pro nahlášení nabídky/obsahu, formulář s URL/ID a důvodem, potvrzení příjmu, moderátorská fronta, odůvodnění zásahu, proces odvolání, auditní záznam a kontaktní místo. DSA není obecná licence ignorovat jiná spotřebitelská/GDPR pravidla.

## 5. Spotřebitel: podnikatel versus soukromá osoba

U nákupu od podnikatele přes prostředek komunikace na dálku se typicky uplatní spotřebitelská informační povinnost a zákonné právo odstoupit (obvykle 14 dní s výjimkami) a práva z vadného plnění. U soukromého prodeje se tyto zvláštní spotřebitelské režimy neuplatní stejně; stále platí obecné občanské právo a zákaz klamání/podvodu. Platforma musí před dokončením transakce rozpoznat a zobrazit, zda prodává podnikatel, nebo soukromá osoba, a nesmí kupujícímu slíbit práva, která systém neposkytuje.

Pokud provozovatel vybírá provizi, řídí transakci, určuje ranking, zpracovává platby nebo nabízí vlastní ochranu, jeho role a informační povinnosti mohou být jiné než u prostého inzertního prostředníka. Neopisovat podmínky konkurentů bez právního posouzení.

## 6. Obsah, zakázané zboží a bezpečnost spotřebitele

Dnešní app nemá veřejné user-generated listings, oznamovací tlačítko ani policy enforcement. Veřejný seed obsahuje luxusní značky a popisuje autenticitu; seed obrázky jsou externí Unsplash URL a nemusejí zobrazovat skutečný produkt. To je pro demo zavádějící a pro veřejný katalog rizikové.

Před veřejným publikováním definovat seznam zakázaného/omezeného obsahu: padělky a nelegální kopie, zbraně/střelivo, léky a léčiva, alkohol/tabák, nebezpečné výrobky, odcizené zboží, identity/doklady a další položky vyžadující zvláštní povolení. Konkrétní seznam připravit podle cílových kategorií, právních předpisů a platebního/dopravního partnera. Sbazar/Bazoš zveřejňují vlastní konkrétní pravidla; nejsou automaticky přenositelná na ResaleAI.

## 7. Licence, zdroje a značky

| Součást | Stav / ověřený údaj | Co udělat |
|---|---|---|
| Vlastní kód | Repo má MIT licenci. | Ujasnit, že MIT se vztahuje na projektový kód, nikoli automaticky na cizí fotky, značky nebo obsah. |
| Django 5.2 | BSD 3-Clause. | Zachovat copyright/licenční oznámení při redistribuci zdrojů. |
| Requests | Apache 2.0. | Uchovat licenční text a upozornění při distribuci balíčku. |
| Pillow | MIT-CMU licence. | Uchovat podmínky distribuce včetně copyrightu. |
| python-decouple | MIT. | Zachovat copyright/license. |
| psycopg | Aktuální upstream uvádí LGPL-3.0; přesnou licenci konkrétní verze/binárního wheel ověřit v dodaném balíčku. | Pro veřejnou distribuci přidat SBOM/licence dependency scan; binary variantu posoudit zvlášť. |
| django-storages | Licence konkrétní nainstalované verze nebyla primární stránkou spolehlivě potvrzena v tomto průzkumu. | Ověřit metadatový `License` a LICENSE ve wheelu instalované verze. |
| Bootstrap + Bootstrap Icons | MIT. | Zachovat notice pro případ bundlování. |
| DM Sans + Space Grotesk | SIL Open Font License 1.1 podle Google Fonts. | U zachování fontových souborů přibalit OFL a názvy; při CDN ověřit síťové/privacy dopady. |
| Fotografie | `seed_data.py` odkazuje na `images.unsplash.com`; Unsplash licence dovoluje běžné použití za svých podmínek, attribution není obecně povinná. | Uchovat URL/zdroj, neprodávat samotnou fotku, nepoužít je jako důkaz autenticity konkrétního branded produktu. |
| Značky a text | Demo položky uvádějí Apple, Rolex, Nike, Louis Vuitton aj. | Používat jen jako popis kompatibility/demo; nepředstírat autorizaci, autenticitu ani skutečnou nabídku. Ověřit práva k ochranným známkám a reálným produktovým snímkům. |

`LICENSE` projektu neuděluje práva k obchodním známkám, seed fotografiím, fontům ani každé závislosti. Nepodařilo se spolehlivě načíst všechny primární licence; před distribucí vytvořit SBOM nebo použít scanner a ručně zkontrolovat sporné balíčky.

## 8. Co chybí a návrhy vzorových stránek

Chybí: zásady ochrany osobních údajů, cookies politika/volby, obchodní podmínky platformy, pravidla inzerce/zakázaného zboží, informace o kontaktech provozovatele a transparentní označení demo dat. Pokud aplikace zůstane neveřejným školním demem, viditelně to napsat a nepoužívat skutečné údaje uživatelů.

### Vzorová osnova zásad ochrany osobních údajů

1. Správce, kontakt a datum/verze.
2. Údaje a účely: účet, soukromé koncepty, žádosti/zprávy, bezpečnostní logy, soubory.
3. Právní základ zvlášť pro každý účel; nikoli jeden plošný souhlas.
4. Zpracovatelé/příjemci, hosting, eBay, CDN a případné přenosy mimo EHP.
5. Konkrétní retenční lhůty a kritéria pro zálohy/logy.
6. Práva subjektů a postup kontaktování; možnost stížnosti ÚOOÚ.
7. Bezpečnost a oznámení změn dokumentu.

### Vzorová osnova obchodních podmínek

1. Identita a kontakt provozovatele, popis služby a věkové omezení.
2. Role platformy versus kupující/prodejce; zda platforma uzavírá kupní smlouvu.
3. Registrace, správnost údajů, podnikatel/soukromá osoba.
4. Povinný obsah inzerátu, zakázané zboží, práva k fotkám, moderace a odvolání.
5. Poplatky, ranking/boost, platby, doprava a případné refundace – jen pokud jsou implementovány.
6. Reklamace, spory, ukončení účtu, odpovědnost v mezích práva.
7. Rozhodné právo, mimosoudní řešení a verze podmínek.

### Vzorová osnova cookies stránky

Vyjmenovat konkrétní cookies/local storage/CDN requests, účel, poskytovatele, dobu, právní základ, způsob odmítnutí/změny souhlasu a kontakt. Nepovinné analytické/reklamní cookies neaktivovat před souhlasem, pokud se na ně souhlas vztahuje. Neuvádět cookies, které aplikace skutečně nemá.

### Vzor pravidel inzerce

Zakázat nelegální/padělané/nebezpečné zboží, ukradené věci, klamavý popis a cizí fotografie; stanovit přesný proces reportu, dočasného skrytí, důvodů zásahu, odvolání a opakovaného porušení. U každé kategorie konzultovat platné právo a podmínky dopravce/platební brány.

Tyto osnovy nejsou hotové právní dokumenty; musí je doplnit správce, skutečný hosting, retenční lhůty, poskytovatelé a zamýšlený obchodní model.

## Zdroje

- [GDPR – nařízení (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [Digital Services Act – nařízení (EU) 2022/2065](https://eur-lex.europa.eu/eli/reg/2022/2065/oj)
- [Směrnice 2011/83/EU o právech spotřebitelů](https://eur-lex.europa.eu/eli/dir/2011/83/oj)
- [Občanský zákoník č. 89/2012 Sb.](https://e-sbirka.gov.cz/sb/2012/89)
- [Zákon č. 127/2005 Sb. – § 89, koncová zařízení/cookies](https://e-sbirka.gov.cz/sb/2005/127)
- [ÚOOÚ](https://uoou.gov.cz/)
- [Bazoš podmínky](https://www.bazos.cz/podminky.php), [Sbazar podmínky](https://o-seznam.cz/napoveda/sbazar/jak-inzerovat/smluvni-podminky/smluvni-podminky-sbazar-a-v-mobilni-aplikaci/)
- [Unsplash licence](https://unsplash.com/license), [Google Fonts DM Sans](https://fonts.google.com/specimen/DM+Sans/license), [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk/license)
- [Django licence](https://github.com/django/django/blob/stable/5.2.x/LICENSE), [Requests licence](https://github.com/psf/requests/blob/main/LICENSE), [Pillow licence](https://github.com/python-pillow/Pillow/blob/main/LICENSE), [Bootstrap licence](https://github.com/twbs/bootstrap/blob/main/LICENSE)

Právní předpisy a podmínky se mění. Před skutečným provozem ověř aktuální znění a konkrétní použitelnost u právníka.
