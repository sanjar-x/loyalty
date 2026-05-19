# Задача для Frontend: синхронизация под camelCase (Фаза 2)

**Дата:** 2026-05-14
**Инициатор:** Backend
**Адресат:** `frontend-admin`, `mini-app`
**Тип:** breaking API change — реакция на backend-релиз
**Родительская задача:** `apps/backend/docs/api/api-camelcase-unification-task-2026-05-14.md` (= `apps/frontend/admin/docs/backend-api-camelcase-unification-task-2026-05-14.md`), [[ADR-009 API Serialization Convention]]

---

## 1. Что произошло на бэкенде

Backend завершил Фазы 1+3+4 унификации API в camelCase. Переведены модули, которые раньше отдавали `snake_case`:

- **Logistics** целиком — shipments, provider-accounts, rates, pickup-points, intakes, edit-tasks.
- **Geo** read-models — страны, валюты, языки, регионы, районы.
- **Favorites** целиком.
- **Profile** — `SessionInfo` (`GET /api/v1/profile/sessions`).
- Пропущенные одиночные схемы — `RoleWithPermissions` (`GET /api/v1/admin/roles`), `ForYouFeedResponse` (catalog for-you), `RecomputeSkuResponse` / `RecomputeFanoutResponse` (pricing recompute).
- **Error-envelope** всех модулей — `request_id` → `requestId`.
- **Query-параметры** списочных эндпоинтов — `snake_case` → `camelCase` (через `Query(alias=...)`).
- **Path-плейсхолдеры** — `{product_id}` → `{productId}` и т.д. во всех маршрутах (Фаза 4, `Path(alias=...)`).
- **`MoneySchema`** в logistics — поле `currency_code` → `currency` (схлопнут на общий shared-тип).

### 1.1 Что критично, что терпит

Backend оставил `populate_by_name=True` на **переходный период**:

| Что                                   | Срочность              | Почему                                                                                                                                                |
| ------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Чтение полей из ответов**           | 🔴 **Ломается сразу**  | Ответы теперь camelCase. `obj.provider_code` → `undefined`.                                                                                           |
| **Query-параметры** (что фронт шлёт)  | 🟡 Терпит временно     | Backend принимает и snake_case, и camelCase на вход. Но привести к camelCase нужно **до того, как backend снимет `populate_by_name`** (финал Фазы 2). |
| **Тела POST/PUT-запросов**            | 🟡 Терпит временно     | То же — `populate_by_name` принимает оба регистра.                                                                                                    |
| **Path-плейсхолдеры** (`{productId}`) | ⚪ Рантайм не затронут | Клиент подставляет в URL **значение**, не имя плейсхолдера — `/products/{uuid}` не меняется. Затронут только OpenAPI-codegen (см. ниже про mini-app). |

Вывод: **первым делом — чтение ответов**, иначе UI сломается сразу. Query/тела — в том же PR, но это «не горит». Path-плейсхолдеры рукописный код не ломают вовсе — но `mini-app` после регенерации получит camelCase-имена в arg-объектах эндпоинтов (`{ productId }` вместо `{ product_id }`); TypeScript-компилятор подсветит места, где аргумент собирался вручную.

---

## 2. mini-app — путь через codegen

`mini-app` генерирует RTK Query клиент и типы из `openapi.json` (`@rtk-query/codegen-openapi` + `openapi-typescript`). Это **сильно упрощает синхронизацию** — генератор сам перепишет типы, а TypeScript-компилятор покажет все места, где код обращается к старым полям.

### Шаги

1. **Заменить снапшот.** Положить свежий `openapi.json` (см. §4) в `apps/frontend/mini-app/openapi.json`.
2. **Регенерировать:**
   ```bash
   cd apps/frontend/mini-app
   npm run api:gen      # → lib/store/__generated__/api.ts (RTKQ endpoints + типы)
   npm run api:types    # → lib/store/__generated__/schema.d.ts
   ```
   Сгенерированные файлы коммитятся (drift проверяется `npm run api:check`). **Руками их не править.**
3. **Починить TS-ошибки.** `npm run build` (или `tsc`) подсветит каждое место, где код читал `provider_code` / `next_cursor` / `is_default` / `lang_code` / `request_id` и т.д. Пройтись по списку, переименовать на camelCase. Это и есть основная работа — компилятор сам составит список.
4. **Query-параметры / тела запросов.** RTKQ-аргументы эндпоинтов тоже перегенерируются в camelCase (`flattenArg: false` → typed arg-объекты). Места, где аргументы собираются вручную, компилятор подсветит.
5. **`api:check` должен быть зелёным** — `npm run api:check` (gen + types + `git diff --exit-code`).

### Особые точки внимания в mini-app

- Основные потребители snake_case-модулей: **Favorites**, **pickup-points / rates** (checkout flow), сессии профиля.
- `lib/store/baseApi.js` — если error-handling читает `error.details.request_id` из envelope, поправить на `requestId`.
- mini-app сейчас в активной перестройке (flat `app/` + `components/` + `lib/`) — синхронизацию делать **после** того, как структура устоялась, иначе конфликты.

---

## 3. frontend-admin — ручная правка

`admin` НЕ использует codegen — `openapi/openapi.json` лежит как справочный снимок. Поэтому правки точечные. Ниже — найденные точки (список **не исчерпывающий**, обязательно прогрепать самим, см. §3.3).

### 3.1 Чтение ответов (🔴 критично)

| Файл                                                       | Сейчас                                                                            | Должно стать                                              |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `src/shared/ui/ApiErrorState.jsx`                          | `error?.details?.request_id` (стр. ~59), label `request_id:` (стр. ~71)           | `error?.details?.requestId`, label `requestId:`           |
| `src/shared/api/geo/geo.js`                                | `t.lang_code` (стр. ~9)                                                           | `t.langCode`                                              |
| `src/features/order-actions/ui/ChangePickupPointModal.jsx` | `p.provider_code`, `p.external_id`, `selected.provider_code` (стр. ~74, 152, 154) | `p.providerCode`, `p.externalId`, `selected.providerCode` |

`ApiErrorState.jsx` — самый широкий: error-envelope общий для **всех** модулей, сейчас перестанет показывать request id в любой ошибке.

### 3.2 Query-параметры и тела запросов (🟡 в том же PR)

**BFF `allowedParams` whitelists** — пропускают query-параметры к backend. Поскольку фронт начнёт слать camelCase, whitelist должен пропускать camelCase:

| Файл                                                           | Сейчас                                                          | Должно стать                                                                  |
| -------------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `src/app/api/catalog/attributes/route.js`                      | `'group_id', 'is_dictionary', 'is_filterable', 'is_searchable'` | `'groupId', 'isDictionary', 'isFilterable', 'isSearchable'`                   |
| `src/app/api/catalog/attributes/[attributeId]/values/route.js` | `'is_active', 'value_group'`                                    | `'isActive', 'value_group'` _(`value_group` — проверить, входит ли в Фазу 3)_ |
| `src/app/api/pricing/contexts/route.js`                        | `'is_active', 'is_frozen'`                                      | `'isActive', 'isFrozen'`                                                      |
| `src/app/api/catalog/products/route.js`                        | `'sort_by', 'published_after'`                                  | `'sortBy', 'publishedAfter'`                                                  |

**Entity/feature api — сборка query** (`params.set('snake_case', ...)`):

| Файл                                         | Параметр                                       |
| -------------------------------------------- | ---------------------------------------------- |
| `src/entities/product/api/products.js`       | `sort_by` → `sortBy`                           |
| `src/entities/staff/api/staff.js`            | `sort_by` → `sortBy`, `is_active` → `isActive` |
| `src/entities/user/api/customers.js`         | `sort_by` → `sortBy`, `is_active` → `isActive` |
| `src/entities/user/api/identities.js`        | `sort_by` → `sortBy`, `is_active` → `isActive` |
| `src/entities/attribute-value/api/values.js` | `is_active` → `isActive`                       |
| `src/features/pricing/api/formulas.js`       | `category_id` → `categoryId`                   |

**Тела запросов** — `ChangePickupPointModal.jsx` строит body `{country_code, provider_code, ...}` для pickup-points. Backend примет (populate_by_name), но привести к `{countryCode, providerCode}` в этом же PR.

### 3.3 Обязательно прогрепать самим

Список выше собран grep'ом и **может быть неполным**. Прогоните по `apps/frontend/admin/src`:

```bash
grep -rnE '\b(provider_code|is_active|is_default|next_cursor|tracking_number|delivery_type|quoted_cost|external_id|list_id|target_type|target_id|added_at|item_count|sort_order|lang_code|fias_guid|country_code|subdivision_code|official_name|minor_unit|ip_address|user_agent|is_current|request_id|credential_fingerprints|currency_code|sort_by|only_active|category_id|max_depth|include_inactive|include_total|include_facets|price_min|price_max|in_stock|published_after|created_after|brand_id|group_id|role_id)\b' src --include='*.js' --include='*.jsx'
```

Каждое попадание — кандидат на переименование. Различайте: **чтение ответа** (критично) vs **отправка query/body** (терпит, но в этом же PR). Доменные значения enum'ов (`yandex_delivery`, `pickup_point`, `customer_changed_mind`) — **НЕ трогать**, это values, а не ключи (см. §6 родительского документа).

### 3.4 Обновить снапшот

Заменить `apps/frontend/admin/openapi/openapi.json` свежим (см. §4). Это справочный файл — на рантайм не влияет, но должен быть актуальным.

---

## 4. Как получить свежий openapi.json

Снять с живого backend:

```bash
# поднять backend локально
cd apps/backend && docker compose up -d && uv run uvicorn main:app --port 8080 &
# снять снапшот
curl -s http://127.0.0.1:8080/openapi.json | python -m json.tool > openapi.json
```

Положить в:

- `apps/frontend/mini-app/openapi.json`
- `apps/frontend/admin/openapi/openapi.json`

**Проверка снапшота** — в `components.schemas` не должно остаться snake_case-полей (кроме осознанных исключений §6 родительского документа):

```bash
grep -nE '"[a-z]+_[a-z]' openapi.json | grep -v webhook
# ожидаемо: только enum values и webhook-payload'ы
```

---

## 5. Acceptance criteria

- [ ] **mini-app:** `npm run api:gen && npm run api:types` выполнены на свежем `openapi.json`; `npm run api:check` зелёный; `npm run build` проходит без TS-ошибок; `npm run lint` чист.
- [ ] **mini-app:** smoke ключевых флоу — favorites, pickup-points/checkout, профиль (сессии) — данные отображаются.
- [ ] **frontend-admin:** все точки из §3.1 (чтение ответов) переведены на camelCase.
- [ ] **frontend-admin:** `allowedParams` whitelists и сборка query (§3.2) переведены на camelCase.
- [ ] **frontend-admin:** grep из §3.3 не даёт необработанных попаданий (кроме enum values).
- [ ] **frontend-admin:** `ApiErrorState` снова показывает `requestId` при ошибке (проверить на любом 4xx).
- [ ] **frontend-admin:** smoke — логистика (provider accounts, pickup-points в ChangePickupPointModal), гео-справочники, error-states.
- [ ] Оба снапшота `openapi.json` пересобраны и закоммичены.
- [ ] После мержа обоих фронтов — **сообщить backend**, чтобы сняли `populate_by_name=True` (финал Фазы 2).

---

## 6. Порядок работ

1. **Backend поднимает свежий `openapi.json`** и кладёт в оба фронта (или даёт фронту — фронт снимает сам по §4).
2. **mini-app** — codegen-путь (§2): регенерация → починка TS-ошибок → `api:check` зелёный. Делать после стабилизации flat-структуры.
3. **frontend-admin** — ручные правки (§3): сперва §3.1 (чтение ответов, критично), затем §3.2 (query/body).
4. Оба фронта смоук-тестируются против backend с `populate_by_name=True` (ещё принимает оба регистра — безопасное окно).
5. После мержа обоих — backend снимает `populate_by_name`, и контракт становится строго camelCase.

> ⚠️ Не снимайте `populate_by_name` на backend, пока **оба** фронта (и `telegram-bot`, если он потребляет затронутые эндпоинты) не смержены и не проверены. Это единственная страховка переходного периода.

---

## 7. Справочные файлы

- `apps/backend/docs/api/api-camelcase-unification-task-2026-05-14.md` — полная инвентаризация изменённых схем (§2 родительского документа: точные имена всех полей по модулям).
- [[ADR-009 API Serialization Convention]] — решение и его обоснование.
- `apps/frontend/mini-app/openapi.config.cjs` — конфиг codegen mini-app.
- `apps/frontend/admin/src/shared/api/bff.js` — `proxyToBackend`, `allowedParams`.
- `apps/frontend/admin/src/shared/api/client-fetch.js` — `apiClient`, `ApiError` (error-envelope парсится здесь — проверить, не читает ли `request_id`).
