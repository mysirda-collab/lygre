# Architektonický návrh systému Lygre

## 1. Cíl řešení

Systém má sloužit jako centralizované operační centrum pro montážní firmu. Umožní evidovat zakázky, spravovat zákazníky, plánovat techniky a komunikovat se zákazníky prostřednictvím SMS.

## 2. Architektura

### 2.1 Hlavní vrstvy

- Frontend: Next.js + React + TypeScript
  - responzivní webová aplikace pro administrátory, dispečery a techniky
- Backend API: FastAPI
  - REST API pro práci s daty, autentizaci, workflow zakázek a integrace
- Databáze: PostgreSQL
  - hlavní zdroj pravd
- ORM: SQLAlchemy
  - modelování dat a přístup k databázi
- Infrastructure: Docker Compose
  - lokální vývojové prostředí a jednoduchá nasaditelnost

### 2.2 Vývojové principy

- rozdělení na doménové moduly,
- jasné oddělení API vrstvy, služeb a datové vrstvy,
- použití migrací pro databázové změny,
- nízká vazba mezi moduly,
- bezpečnost a auditovatelnost operací.

## 3. Hlavní moduly

- Autentizace a oprávnění
- Správa zákazníků
- Správa zakázek
- Rezervace termínů
- Plánování techniků
- SMS komunikace
- Administrace a nastavení
- Reporting a výstupy

## 4. Průběh zakázky

1. Vytvoření zakázky
2. Přiřazení zákazníka a typu služby
3. Výběr vhodného termínu
4. Plánování technika
5. Odeslání SMS potvrzení/aktualizace
6. Uzavření zakázky a archivace

## 5. Bezpečnostní a provozní požadavky

- autentizace uživatelů,
- role-based access control,
- logování auditních událostí,
- ochrana citlivých dat,
- konfigurace prostředí přes proměnné,
- plánovaná integrace monitoringu a logů.

## 6. Doporučená struktura deploymentu

- lokální vývoj: Docker Compose
- testovací prostředí: stejné komponenty s odděleným databázovým úložištěm
- produkce: kontejnerová nasazení s reverse proxym a PostgreSQL
