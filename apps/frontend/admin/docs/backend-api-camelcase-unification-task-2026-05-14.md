# Задача для Backend: унификация именования полей API в camelCase

**Дата:** 2026-05-14
**Инициатор:** `frontend-admin`
**Адресат:** Backend
**Тип:** cross-cutting, **breaking API change** — требует согласования и скоординированного релиза
**Цель:** привести JSON-поля **всех** эндпоинтов `/api/v1/*` к единой конвенции **camelCase**. Сейчас часть модулей сериализует ответы/запросы в `snake_case`, часть — в `camelCase`, иногда **в пределах одного модуля**.

> Это не «подгонка бэка под фронт», а устранение реального contract-долга: API-контракт сейчас непоследователен сам по себе. Решение об общей конвенции сериализации — архитектурное, его стоит зафиксировать отдельным **ADR** (`Projects/loyality/ADR-{NNN} API serialization convention.md`).

---

## 1. Контекст — почему

Снимок `apps/frontend/admin/openapi/openapi.json` (post-Sprint-4, 25 517 строк) показывает три разных состояния:

- **camelCase** (Pydantic `CamelModel`): Auth, IAM, Staff, Customers, Suppliers, Catalog (brands/categories/attributes/templates/products/variants/SKU/media), Pricing, Orders, Admin/Orders, Cart, Payments, Profile (кроме `SessionInfo`).
- **snake_case**: Geo (read models), вся Logistics (shipments + provider-accounts + pickup-points + rates + intakes + edit-tasks), Favorites, `SessionInfo`.
- **Несогласованность внутри модуля** — самый явный аргумент:
  - **Geo**: входные схемы уже camelCase (`CountryTranslationInput.langCode`, `CreateDistrictRequest.subdivisionCode`/`fiasGuid`/`isActive`), а read-модели — snake_case (`CountryTranslationReadModel.lang_code`, `DistrictReadModel.fias_guid`/`is_active`).
  - **IAM**: `RoleDetailResponse`/`RoleInfoResponse` → `isSystem`, а `RoleWithPermissions` (отдаётся из `GET /api/v1/admin/roles`) → `is_system`.
  - **Profile**: `ProfileResponse`/`UpdateProfileRequest` — camelCase, а `SessionInfo` (из `GET /api/v1/profile/sessions`) — snake_case.

Для фронта это значит: на каждый «snake_case-модуль» нужен отдельный маппинг-слой или ручные обращения `obj.provider_code` вместо общей конвенции `obj.providerCode`. См. предупреждение в `docs/logistics-providers-page-task-2026-05-14.md` §2.2 — там пришлось явно документировать «здесь snake_case, не доверяй догадкам».

---

## 2. Инвентаризация — что конкретно переводить

### 2.1 Geo — `apps/backend/src/modules/geo/**` (read models)

`CountryReadModel`, `CountryListReadModel`, `CountryTranslationReadModel`, `CountryCurrencyLinkReadModel`,
`CurrencyReadModel`, `CurrencyListReadModel`, `CurrencyTranslationReadModel`,
`LanguageReadModel`, `LanguageListReadModel`,
`SubdivisionReadModel`, `SubdivisionListReadModel`, `SubdivisionTranslationReadModel`,
`SubdivisionTypeReadModel`, `SubdivisionTypeListReadModel`, `SubdivisionTypeTranslationReadModel`,
`DistrictReadModel`, `DistrictListReadModel`, `DistrictTranslationReadModel`,
`DistrictTypeReadModel`, `DistrictTypeListReadModel`, `DistrictTypeTranslationReadModel`.

Поля: `lang_code`, `official_name`, `local_variant`, `is_active`, `sort_order`, `minor_unit`, `currency_code`, `is_primary`, `country_code`, `type_code`, `parent_code`, `subdivision_code`, `oktmo_prefix`, `fias_guid`, `iso639_1`, `iso639_2`, `iso639_3`, `name_en`, `name_native`.

### 2.2 Logistics — `apps/backend/src/modules/logistics/**` (целиком)

Shipments / rates / intakes / edit-tasks / returns:
`AddressSchema`, `ContactInfoSchema`, `ParcelSchema`, `DimensionsSchema`, `WeightSchema`, `GeoPositionSchema`,
`ShipmentResponse`, `AdminShipmentSummarySchema`, `AdminShipmentListResponse`,
`DeliveryQuoteSchema`, `ShippingRateSchema`, `CalculateRatesRequest`, `CalculateRatesResponse`,
`RateQuoteRequest`, `RateQuoteResponse`, `CreateShipmentRequest`, `BookShipmentResponse`, `CancelShipmentResponse`,
`PickupPointSchema`, `PickupPointsRequest`, `PickupPointsResponse`,
`CreateIntakeRequest`, `CreateIntakeResponse`, `IntakeStatusResponse`, `IntakeWindowSchema`,
`AvailableIntakeDaysRequest`, `AvailableIntakeDaysResponse`,
`DeliveryIntervalSchema`, `DeliveryIntervalsResponse`, `EstimatedDeliveryIntervalsRequest`,
`EditOrderRequest`, `EditOrderItemsRequest`, `EditPackagesRequest`, `EditPackageSchema`, `EditPackageItemSchema`,
`EditItemMarkingSchema`, `EditItemRemovalSchema`, `EditPlaceSwapSchema`, `RemoveOrderItemsRequest`,
`EditTaskResponse`, `EditTaskStatusResponse`,
`ClientReturnRequest`, `RefusalRequestSchema`, `ReturnResponse`,
`ReverseAvailabilityRequestSchema`, `ReverseAvailabilityResponse`,
`ActualDeliveryInfoResponse`, `ActualDeliveryInfoSchema`, `CashOnDeliverySchema`,
`TrackingResponse`, `TrackingEventSchema`, `CancelIntakeResponse`.

Provider Accounts:
`CreateProviderAccountRequest` (`provider_code`, `is_active`), `UpdateProviderAccountRequest` (`replace_config`),
`SetProviderAccountActiveRequest` (`is_active`), `ProviderAccountResponse` (`provider_code`, `is_active`, `credential_fingerprints`, `created_at`, `updated_at`), `ProviderAccountListResponse`, `RefreshRegistryResponse` (`registered_provider_codes`), `CredentialFingerprintSchema`.

### 2.3 Favorites — `apps/backend/src/modules/favorites/**`

`AddFavoriteItemRequest`, `AddFavoriteItemResponse`, `CreateFavoriteListRequest`, `CreateFavoriteListResponse`,
`RenameFavoriteListRequest`, `FavoriteListResponse`, `FavoriteListsResponse`,
`FavoriteItemResponse`, `FavoriteItemsPageResponse`, `FavoriteProductCardResponse`, `FavoriteBrandCardResponse`,
`MoveFavoriteItemRequest`, `CheckFavoritedRequest`, `CheckFavoritedResponse`.

Поля: `target_type`, `target_id`, `list_id`, `item_id`, `is_default`, `sort_order`, `item_count`, `created_at`, `updated_at`, `added_at`, `next_cursor`, `title_i18n`, `main_image_url`, `logo_url`, `src_list_id`, `dst_list_id`, `target_ids`.

### 2.4 Profile

`SessionInfo` (`ip_address`, `user_agent`, `created_at`, `expires_at`, `is_current`) — единственная snake_case-схема в модуле.

### 2.5 Два `MoneySchema` — отдельная проблема

| Схема                                                         | Поле валюты                       |
| ------------------------------------------------------------- | --------------------------------- |
| `src__shared__schemas__MoneySchema`                           | `currency` (camelCase-совместимо) |
| `src__modules__logistics__presentation__schemas__MoneySchema` | `currency_code`                   |

Решение для backend: либо привести логистический `MoneySchema` к `currencyCode`, либо (предпочтительно) **схлопнуть логистику на общий `src.shared.schemas.MoneySchema`** и убрать дубль.

### 2.6 Query / path параметры

Глобально snake_case: `sort_by`, `sort_order`, `role_id`, `is_active`, `provider_code`, `only_active`, `category_id`, `country_code`, `published_after`, `created_after`, `tracking_number_contains`, `max_depth` и т.д.

Рекомендация: вынести в **отдельную под-фазу** (см. §4, фаза 3). Менять их независимо breaking, FastAPI требует `Query(alias=...)`, и для path-параметров (`{product_id}`) выгода чисто косметическая — **path-параметры не трогать**.

---

## 3. Технический подход

Pydantic v2 — единый базовый класс в shared kernel, от которого наследуются **все** request/response-схемы:

```python
# apps/backend/src/shared/schemas/base.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,   # вход принимает И snake_case, И camelCase — на переходный период
    )
```

- **Ответы**: FastAPI сериализует по alias (`response_model_by_alias=True` — дефолт) → отдаётся camelCase.
- **Запросы**: `populate_by_name=True` → бэк продолжает принимать старый snake_case **и** новый camelCase. Это даёт окно, в котором клиенты мигрируют без флага «всё сломалось одномоментно». После миграции всех потребителей — `populate_by_name` можно убрать.
- Geo read-модели сейчас, судя по нейму (`*ReadModel`), не на `CamelModel` — их нужно перевести на общий базовый класс, не «латать» по полю.
- После мержа — **пересобрать снапшоты OpenAPI** во всех потребителях: `apps/frontend/admin/openapi/openapi.json` и снапшот mini-app.

---

## 4. Этапы

1. **Фаза 0 — ADR + базовый класс.** Зафиксировать конвенцию в ADR, добавить `CamelModel` в shared kernel, прогнать на одном модуле (Favorites — самый изолированный) как образец.
2. **Фаза 1 — тела ответов/запросов.** Geo read-models → Logistics → Provider Accounts → Favorites → `SessionInfo`. Параллельно — решение по двойному `MoneySchema` (§2.5).
3. **Фаза 2 — координация клиентов.** Обновить `frontend-admin`, `mini-app`, `telegram-bot`; пересобрать OpenAPI-снапшоты. Только после этого убрать `populate_by_name`.
4. **Фаза 3 (опционально, отдельным PR) — query-параметры.** `Query(alias=...)` для списочных эндпоинтов. Path-параметры не трогаем.

---

## 5. Влияние на потребителей

| Потребитель                            | Что ломается                                                                                                                                         | Действие                                                                                                         |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `frontend-admin`                       | `shared/api/geo/*` (geo read-models); BFF-прокси проксируют JSON «как есть» — поломаются entity/feature-слои, читающие snake_case-поля логистики/гео | Обновить чтение полей; пересобрать `openapi/openapi.json`                                                        |
| `frontend-admin` (logistics-providers) | Страница ещё не реализована (`docs/logistics-providers-page-task-2026-05-14.md`) — **выиграет**: можно сразу писать на camelCase                     | Согласовать порядок: либо backend-унификация раньше, либо страница принимает текущий snake_case и правится потом |
| `mini-app`                             | Favorites, pickup-points, rates/quote, checkout-flow — основные потребители snake_case-модулей                                                       | Координация с командой mini-app обязательна                                                                      |
| `telegram-bot`                         | Зависит от того, какие эндпоинты использует                                                                                                          | Проверить и обновить                                                                                             |

> Webhooks (`/api/v1/webhooks/*`) потребители backend, а не наши — payload диктуют внешние провайдеры (CDEK / Yandex / DobroPost / PSP). См. §6.

---

## 6. Что НЕ трогать

- **Payload вебхуков** `/api/v1/webhooks/{logistics,payments,dobropost}` — это `additionalProperties: true`, форму задаёт внешний провайдер. Конвертация сломает приём вебхуков.
- **Значения enum'ов** — это **values**, не ключи полей. `CancellationReason` (`customer_changed_mind`), `HoldReason` (`passport_invalid`), `provider_code` (`yandex_delivery`), `delivery_type` (`pickup_point`), `pricing_status` и т.п. остаются как есть — это доменные строковые константы, многие лежат в БД. Их конвертация — это отдельная, гораздо более глубокая миграция, **в эту задачу не входит**.
- **Path-параметры** (`{product_id}`, `{provider_code}`) — в рантайме это позиционные сегменты URL, имя — просто плейсхолдер. Выгоды нет.
- **Сгенерированное FastAPI** — `ValidationError`, `HTTPValidationError`, `operationId`, `loc`/`msg`/`type` в 422-конверте.
- **Error-envelope** `{ error: { code, message, details, request_id } }` — `request_id` уже устоявшийся контракт; если меняем на `requestId` — то явно и одной строкой в ADR.
- `i18n`-ключи (`ru` / `en`) и сами `*I18N`-поля — уже корректны.

---

## 7. Acceptance criteria

- [ ] Принят ADR с конвенцией «все JSON-поля API — camelCase».
- [ ] Все схемы из §2.1–§2.4 сериализуются в camelCase; в `openapi.json` не осталось snake_case-полей в телах запросов/ответов (кроме исключений §6).
- [ ] Дубль `MoneySchema` устранён или оба варианта camelCase (§2.5).
- [ ] На переходный период вход принимает оба варианта (`populate_by_name=True`).
- [ ] `grep -nE '"[a-z]+_[a-z]'` по `components.schemas` в свежем `openapi.json` даёт только осознанные исключения.
- [ ] Снапшоты OpenAPI пересобраны в `frontend-admin` и `mini-app`.
- [ ] Backend-тесты на сериализацию обновлены и зелёные.
- [ ] Потребители (`frontend-admin`, `mini-app`, `telegram-bot`) обновлены и проверены смоуком до снятия `populate_by_name`.

---

## 8. Открытые вопросы для backend

1. `request_id` в error-envelope → `requestId` или оставляем? (влияет на обработку ошибок во всех клиентах).
2. Двойной `MoneySchema`: переименовать поле в логистическом или схлопнуть на общий `src.shared.schemas.MoneySchema`?
3. Фаза 3 (query-параметры) — в этой задаче или отдельным треком после релиза основной унификации?
4. Порядок с `logistics-providers` страницей админки: ждать унификацию или писать страницу на текущем snake_case и править потом?
5. Гео read-модели — на каком базовом классе сейчас и нет ли причины, по которой их специально оставили snake_case (внешние интеграции, кэш)?

---

## 9. Справочные файлы

- `apps/frontend/admin/openapi/openapi.json` — текущий снапшот контракта (источник инвентаризации §2).
- `apps/backend/src/shared/schemas/` — где живёт общий `MoneySchema`, туда же `CamelModel`.
- `apps/frontend/admin/docs/logistics-providers-page-task-2026-05-14.md` §2.2 — пример боли от snake_case на стороне фронта.
- `apps/frontend/admin/docs/CONVENTIONS.md` — «Backend контракт — не менять без согласования»; этот документ и есть запрос на согласование.
