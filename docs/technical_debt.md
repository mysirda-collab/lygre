# Technický audit projektu Lygre

## Kritické problémy

### 1. Migrace nebyly v produkčním prostředí spolehlivě použité
- Proč je problém: databázová struktura se v minulosti upravovala ručně (např. ALTER TABLE) místo spolehlivé migrace. To zvyšuje riziko nekompatibility mezi vývojem a produkčním prostředím.
- Jak vznikl: během zrychleného vývoje byly změny v tabulkách aplikovány přímo do DB, aby se rychle vyřešil běh aplikace.
- Jak správně opravit: v každé změně schématu vytvořit novou Alembic migraci a použít ji v každém prostředí. Počítat s tím, že všechny ručně provedené změny budou v DB sebrány do jedné migrace.

### 2. Schéma databáze není plně v synchronizaci s migracemi
- Proč je problém: v aktuálním prostředí byla tabulka uploads vytvořena ručně, protože migrace nezafungovala. To znamená, že vývojové prostředí může být odlišné od toho, co migrace deklarují.
- Jak vznikl: migrace se v dané fázi nepodařila spustit kvůli chybám v prostředí a zkratkou se zvolilo ruční vytvoření tabulky.
- Jak správně opravit: smazat ručně vytvořené objekty, znovu spustit celou migraci od nuly a ověřit, že každé prostředí používá stejná schémata.

### 3. Backend je citlivý na změny schématu a neobsahuje robustní startup kontrolu
- Proč je problém: aplikace se v minulosti rozbíjela při chybějící tabulce nebo chybějící koloně. To vede k výpadkům při startu nebo při prvním requestu.
- Jak vznikl: chybějící validace datových modelů a migrací v startup procesu.
- Jak správně opravit: přidat startup health check, kontrolu přítomnosti tabulek a explicitně vyhodnocovat migrace při startu v dev/CI prostředí.

## Vysoké problémy

### 4. V projektu zůstávají nevyužité example moduly a šablonové soubory
- Proč je problém: zvyšují složitost projektu a mohou vést k nejasnostem v architektuře.
- Jak vznikl: šablona projektu byla rozšířena o ukázkové komponenty, ale v průběhu vývoje nebyly odstraněny.
- Jak správně opravit: odstranit nevyužité example modely, CRUD a příslušné schémata, pokud nejsou součástí business logiky.

### 5. Endpointy pracují s daty bez jednotné validace a chybových strategií
- Proč je problém: některé endpointy vracejí jednoduché chyby a neobsahují společný pattern pro validaci vstupů a chybových odpovědí.
- Jak vznikl: backend byl rozšiřován iterativně bez sjednocení API kontraktů.
- Jak správně opravit: zavést společné response modely, standardní chybové odpovědi a validator pro každý endpoint.

### 6. Frontend obsahuje více ad-hoc přístupů ke komunikaci s API
- Proč je problém: fetch volání jsou rozptýlená a neobsahují společný wrapper ani centralizovanou správu chyb a loading stavů.
- Jak vznikl: rozvoj UI probíhal po modulech bez sjednoceného klienta pro API.
- Jak správně opravit: integrovat společný API client a jednotné hlášení chyb, loading a toast zpráv.

## Střední problémy

### 7. Docker Compose nemá plně robustní závislost na databázi
- Proč je problém: při startu může dojít k tomu, že backend začne dřív, než je DB připravena.
- Jak vznikl: v compose konfiguraci chyběl healthcheck a závislost s podmínkou.
- Jak správně opravit: pokračovat v použití healthchecků a při startu čekat na dostupnost databáze.

### 8. Upload modul ukládá soubory do pevně zakódované cesty
- Proč je problém: tato cesta je vhodná pro container, ale v hostitelském vývoji může být neintuitivní a obtížně spravovatelná.
- Jak vznikl: konfigurace byla doplněna během rychlého vývoje bez plného návrhu pro runtime prostředí.
- Jak správně opravit: přidat konfigurovatelnou cestu prostřednictvím environment proměnných a rozlišit host/kontejner cesty.

### 9. Chybí jednotné logování a monitoring pro operace
- Proč je problém: v případě chyb je obtížné zmapovat, co se stalo při nahrání nebo při práci s databází.
- Jak vznikl: logování bylo doplněno jen v omezené míře.
- Jak správně opravit: rozšířit strukturované logování a přidat operativní metriky.

## Nízké problémy

### 10. Projekt obsahuje některé zbytečné importy a nevyužitý kód
- Proč je problém: zhoršuje čitelnost a zvyšuje pravděpodobnost chyb při úpravách.
- Jak vznikl: v průběhu iterací byl kód přidáván bez pravidelného refaktoringu.
- Jak správně opravit: pravidelně vyčisťovat nevyužité moduly a importy.

### 11. Frontend nemá centralizované pracovní to-do / stavové komponenty
- Proč je problém: opakují se stejné prvky a chybí konsistentní UX.
- Jak vznikl: jednotlivé stránky byly implementovány samostatně bez společných komponent.
- Jak správně opravit: vytvořit sdílené UI komponenty pro formuláře, table a empty-state.
