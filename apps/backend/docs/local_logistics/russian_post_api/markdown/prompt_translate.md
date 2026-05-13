# Task: Translate russian_post_api.xml to English

## Context
File `../russian_post_api.xml` (275KB, 4288 lines) contains complete Russian Post API documentation in Russian.
Translate ALL Russian text to English. Save as `../russian_post_api_en.xml`.

## What to translate
- All `description="..."` attributes
- All `<description>` tag content
- All `<note>` tag content
- All `name="..."` in `<group>`, `<rule_group>`, `<enum>`, `<term>`, `<dictionary>`
- All `<title>` content
- All `<limitation>` content
- All `<rule>` text content
- XML comment text (<!-- ... -->)
- Section headers (SECTION 1: ... etc.)

## What NOT to translate (keep as-is)
- XML tags and structure
- Enum value `name=` (SIMPLE, ORDERED, DEFAULT, etc.) — these are API constants
- Model field `name=` (address-type-to, mass, etc.) — these are JSON field names
- `type=`, `required=`, `default=`, `min_value=`, `max_value=`, `unit=`
- `example=` values — keep original Russian test data (Иванов, Москва, etc.)
- JSON inside `<![CDATA[...]]>` — do NOT modify
- URLs, tokens, paths (/1.0/user/backlog etc.)
- HTTP method names (GET, POST, PUT, DELETE)
- `<source>` tag content (file references)
- Error code strings in `<error name=...>` or `text=` attributes

## Translation rules for postal terminology
1. РПО → Registered Postal Item (RPI)
2. ОПС → Post Office (OPS)
3. ШПИ → Tracking Number (barcode)
4. Партия → Batch
5. Отправление → Shipment/Item
6. Наложенный платеж → Cash on Delivery (COD)
7. Объявленная ценность → Declared Value
8. ФИО → Full Name (FIO)
9. Бандероль → Wrapper/Banderol
10. Посылка → Parcel
11. Письмо → Letter
12. ЕМС → EMS (keep as-is)
13. ЕКОМ → ECOM (keep as-is)
14. Маркетплейс → Marketplace
15. Почтомат → Parcel Locker
16. ПВЗ → Pickup Point (PVZ)
17. АПС → Automated Postal Station (parcel locker)
18. Вручение → Delivery/Handover
19. Засылка → Misrouted
20. Досылка → Forwarding
21. Трекинг → Tracking
22. Таможня → Customs
23. Франкирование → Franking
24. ММПО → International Mail Processing Center (MMPO)
25. ЦГП → Hybrid Processing Center
26. Курьер онлайн → Online Courier
27. Бизнес курьер → Business Courier
28. Копейки → kopecks
29. Граммы → grams
30. Сантиметры → centimeters
31. Миллиметры → millimeters
32. НДС → VAT
33. ИНН → Tax ID (INN)
34. БИК → Bank ID Code (BIK)
35. Сессия → Session
36. Рекламация → Claim
37. Гиперлокальная доставка → Hyperlocal delivery (same-day)
38. Легкий возврат → Easy Return
39. ВГПО → Internal Government Postal Item (VGPO)
40. ВСД → Accompanying Document Return (VSD)
41. Стикер ЗОО → Sticker ZOO (keep brand name)
42. Тестовая среда → Test environment
43. Боевая среда → Production environment
44. Онлайн-сервис «Отправка» → "Otpravka" (Shipping) Online Service

## Accuracy rules
- "10 минут" → "10 minutes" (exact, not "about 10 minutes")
- "обязательно" → "required" (not "recommended")
- "Опционально" → "Optional"
- Keep consistency: same Russian term → same English term everywhere
- All postal forms keep their numbers: Ф103 → Form F103, Ф7 → Form F7, Ф22 → Form F22, Ф112 → Form F112

## Workflow
1. Read `../russian_post_api.xml` fully
2. Translate ALL Russian text according to rules above
3. Save as `../russian_post_api_en.xml`
4. Validate XML is well-formed

## Validation
- [ ] XML well-formed (python xml.etree.ElementTree.parse)
- [ ] No Russian text in description attributes (grep -P 'description="[^"]*[а-яА-Я]')
- [ ] No Russian in XML comments
- [ ] No Russian in <note>, <rule>, <title>, <description> tags
- [ ] JSON in CDATA blocks unchanged
- [ ] example= values unchanged (Russian test data preserved)
- [ ] Enum value names unchanged (SIMPLE, ORDERED, etc.)
- [ ] Field names unchanged (address-type-to, mass, etc.)
- [ ] URLs and paths unchanged
- [ ] All 43 enums present
- [ ] All 69 endpoints present
- [ ] All 16 models present
- [ ] All business rules present
