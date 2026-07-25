# Návrh databáze pro Lygre

## 1. Cíl návrhu

Tento dokument popisuje kompletní logický databázový model budoucího ERP systému pro správu zakázek montážní firmy. Model je navržen tak, aby pokryl zákazníky, firmy, uživatele, role, zakázky, termíny, komunikaci, dokumenty, přílohy, fotografie, podpisy, notifikace, audit log, API klíče a systémová nastavení.

## 2. Základní principy modelu

- relační model v PostgreSQL,
- jasná separace master dat, provozních dat a auditních záznamů,
- každá hlavní entita má vlastní identitu a auditované časy,
- všechny změny jsou sledovatelné,
- model je připraven na budoucí rozšíření o workflow, integrace a reporting.

## 3. Hlavní oblasti dat

1. Organizační data
   - firmy
   - uživatelé
   - role
   - oprávnění

2. Zákazníci a adresy
   - zákazníci
   - adresy
   - kontaktní osoby

3. Zakázky a servisní proces
   - zakázky
   - typy služeb
   - položky zakázky
   - termíny
   - technici
   - kalendáře

4. Komunikace a dokumenty
   - SMS zprávy
   - notifikace
   - dokumenty
   - přílohy
   - fotografie
   - podpisy

5. Audit a nastavení
   - historie změn
   - audit log
   - API klíče
   - systémová nastavení

## 4. Databázové entity

### 4.1 companies
- id
- name
- legal_name
- tax_id
- registration_number
- phone
- email
- website
- address_line_1
- address_line_2
- city
- postal_code
- country
- is_active
- created_at
- updated_at

### 4.2 users
- id
- company_id
- email
- username
- password_hash
- full_name
- phone
- avatar_url
- is_active
- is_superuser
- last_login_at
- created_at
- updated_at

### 4.3 roles
- id
- company_id
- name
- description
- is_system_role
- created_at
- updated_at

### 4.4 permissions
- id
- code
- description
- created_at

### 4.5 role_permissions
- id
- role_id
- permission_id
- created_at

### 4.6 user_roles
- id
- user_id
- role_id
- assigned_at
- assigned_by

### 4.7 customers
- id
- company_id
- customer_number
- salutation
- first_name
- last_name
- company_name
- phone
- email
- notes
- is_active
- created_at
- updated_at

### 4.8 addresses
- id
- company_id
- customer_id
- label
- address_line_1
- address_line_2
- city
- postal_code
- country
- latitude
- longitude
- is_primary
- created_at
- updated_at

### 4.9 contact_people
- id
- company_id
- customer_id
- first_name
- last_name
- phone
- email
- position
- is_primary
- created_at
- updated_at

### 4.10 technicians
- id
- company_id
- user_id
- first_name
- last_name
- phone
- email
- specialty
- skills_json
- is_active
- is_available
- created_at
- updated_at

### 4.11 service_types
- id
- company_id
- name
- description
- default_duration_minutes
- default_price
- is_active
- created_at
- updated_at

### 4.12 orders
- id
- company_id
- customer_id
- service_type_id
- order_number
- title
- description
- status
- priority
- requested_at
- scheduled_from
- scheduled_to
- completed_at
- created_by
- assigned_technician_id
- total_amount
- currency
- notes
- is_archived
- created_at
- updated_at

### 4.13 order_items
- id
- order_id
- name
- description
- quantity
- unit_price
- total_price
- created_at
- updated_at

### 4.14 appointments
- id
- company_id
- order_id
- technician_id
- starts_at
- ends_at
- status
- location_address_id
- notes
- created_at
- updated_at

### 4.15 calendars
- id
- company_id
- name
- description
- color_code
- is_active
- created_at
- updated_at

### 4.16 calendar_events
- id
- calendar_id
- company_id
- related_order_id
- related_appointment_id
- title
- description
- starts_at
- ends_at
- event_type
- created_by
- created_at
- updated_at

### 4.17 technician_availability
- id
- technician_id
- company_id
- day_of_week
- start_time
- end_time
- is_available
- created_at
- updated_at

### 4.18 sms_messages
- id
- company_id
- order_id
- recipient_phone
- direction
- content
- status
- provider_name
- provider_message_id
- sent_at
- delivered_at
- response_payload
- created_at
- updated_at

### 4.19 notifications
- id
- company_id
- user_id
- title
- body
- notification_type
- is_read
- related_entity_type
- related_entity_id
- created_at
- read_at

### 4.20 documents
- id
- company_id
- order_id
- document_type
- title
- file_name
- storage_path
- mime_type
- file_size_bytes
- checksum
- created_by
- created_at
- updated_at

### 4.21 attachments
- id
- company_id
- order_id
- related_entity_type
- related_entity_id
- file_name
- storage_path
- mime_type
- file_size_bytes
- created_by
- created_at
- updated_at

### 4.22 photos
- id
- company_id
- order_id
- caption
- file_name
- storage_path
- mime_type
- file_size_bytes
- taken_at
- created_by
- created_at
- updated_at

### 4.23 customer_signatures
- id
- company_id
- order_id
- customer_id
- signature_image_path
- signed_at
- created_by
- created_at
- updated_at

### 4.24 change_history
- id
- company_id
- entity_type
- entity_id
- changed_by
- change_type
- old_value
- new_value
- created_at

### 4.25 audit_logs
- id
- company_id
- user_id
- entity_type
- entity_id
- action
- ip_address
- user_agent
- payload
- created_at

### 4.26 api_keys
- id
- company_id
- user_id
- name
- key_hash
- key_prefix
- expires_at
- last_used_at
- is_active
- created_at
- updated_at

### 4.27 system_settings
- id
- company_id
- key
- value
- description
- created_at
- updated_at

## 5. Vazby mezi tabulkami

- companies 1:N users
- companies 1:N roles
- roles 1:N role_permissions
- permissions 1:N role_permissions
- users 1:N user_roles
- roles 1:N user_roles
- companies 1:N customers
- customers 1:N addresses
- customers 1:N contact_people
- companies 1:N technicians
- users 1:N technicians
- companies 1:N service_types
- companies 1:N orders
- customers 1:N orders
- service_types 1:N orders
- users 1:N orders (created_by)
- technicians 1:N orders (assigned_technician_id)
- orders 1:N order_items
- companies 1:N appointments
- orders 1:N appointments
- technicians 1:N appointments
- addresses 1:N appointments
- companies 1:N calendars
- calendars 1:N calendar_events
- orders 1:N calendar_events
- appointments 1:N calendar_events
- companies 1:N technician_availability
- technicians 1:N technician_availability
- companies 1:N sms_messages
- orders 1:N sms_messages
- companies 1:N notifications
- users 1:N notifications
- companies 1:N documents
- orders 1:N documents
- companies 1:N attachments
- companies 1:N photos
- orders 1:N photos
- companies 1:N customer_signatures
- customers 1:N customer_signatures
- orders 1:N customer_signatures
- companies 1:N change_history
- companies 1:N audit_logs
- users 1:N audit_logs
- companies 1:N api_keys
- users 1:N api_keys
- companies 1:N system_settings

## 6. Doporučené indexy

- customers(company_id, phone)
- orders(company_id, status, scheduled_from)
- appointments(technician_id, starts_at, ends_at)
- sms_messages(order_id, status)
- audit_logs(company_id, created_at)
- change_history(entity_type, entity_id, created_at)
- api_keys(key_hash)
- system_settings(company_id, key)

## 7. Důležité designové poznámky

- všechny tabulky by měly mít timestampy created_at a updated_at, pokud to má smysl,
- pro citlivá pole jako hesla a API klíče se používá hashování a never storage v čisté podobě,
- PDF dokumenty, fotografie a podpisy by měly být ukládány do objektového úložiště a v databázi jen odkazy,
- audit a historie změn by měly být odděleny od běžných datových tabulek, aby se zachovala čistota provozních dat,
- model je navržen tak, aby v budoucnu podporoval multi-tenant prostředí pro více firem.
