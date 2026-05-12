# Customer App — API changes (2026-05)

> **Аудитория:** frontend main (Next.js 16 customer storefront), Telegram Mini App,
> любые внешние клиенты, использующие публичные endpoints Loyality.
>
> **Контекст:** часть рефакторинга из
> [`router-restructure-2026-05.md`](./router-restructure-2026-05.md). Этот
> документ — выжимка только тех изменений, которые касаются customer
> app. Если ты на admin-стороне — смотри основной документ.
>
> **Дата:** 2026-05-02 · **Окно совместимости:** 7 дней (до 2026-05-09)

---

## TL;DR

1. **`/api/v1/catalog/storefront/*` → `/api/v1/storefront/*`** — лишний `catalog/`
   сегмент удалён. Все storefront endpoints стали короче.
2. **`/api/v1/profile/me/{sessions,password}` → `/api/v1/profile/{sessions,password}`** —
   `/me` суффикс убран для sub-resources (профиль остаётся `/profile/me`).
3. **+6 новых публичных endpoints**: дерево категорий, список брендов, ПВЗ — ранее
   были admin-only или отсутствовали.
4. **Backward-compat**: 308 Permanent Redirect middleware на 7 дней. `fetch()`/`ky`
   следуют редиректам автоматически — старый код продолжит работать в переходный
   период.

---

## Раздел 1 — Переименованные URLs (было → стало)

### Storefront (12 endpoints)

| Метод  | Было                                                         | Стало                                                |
| ------ | ------------------------------------------------------------ | ---------------------------------------------------- |
| `GET`  | `/api/v1/catalog/storefront/products`                        | `/api/v1/storefront/products`                        |
| `GET`  | `/api/v1/catalog/storefront/products/{slug}`                 | `/api/v1/storefront/products/{slug}`                 |
| `GET`  | `/api/v1/catalog/storefront/products/{slug}/similar`         | `/api/v1/storefront/products/{slug}/similar`         |
| `GET`  | `/api/v1/catalog/storefront/products/{slug}/also-viewed`     | `/api/v1/storefront/products/{slug}/also-viewed`     |
| `GET`  | `/api/v1/catalog/storefront/search`                          | `/api/v1/storefront/search`                          |
| `GET`  | `/api/v1/catalog/storefront/search/suggest`                  | `/api/v1/storefront/search/suggest`                  |
| `GET`  | `/api/v1/catalog/storefront/trending`                        | `/api/v1/storefront/trending`                        |
| `GET`  | `/api/v1/catalog/storefront/for-you`                         | `/api/v1/storefront/for-you`                         |
| `GET`  | `/api/v1/catalog/storefront/categories/{id}/filters`         | `/api/v1/storefront/categories/{id}/filters`         |
| `GET`  | `/api/v1/catalog/storefront/categories/{id}/card-attributes` | `/api/v1/storefront/categories/{id}/card-attributes` |
| `GET`  | `/api/v1/catalog/storefront/categories/{id}/comparison-attributes` | `/api/v1/storefront/categories/{id}/comparison-attributes` |
| `GET`  | `/api/v1/catalog/storefront/categories/{id}/form-attributes` | `/api/v1/storefront/categories/{id}/form-attributes` |

> **Обоснование:** префикс `catalog/` дублировал смысл — `/storefront` уже
> означает «публичный витринный API каталога». Сегмент удалён.

### Profile / Account (2 endpoints)

| Метод   | Было                              | Стало                       |
| ------- | --------------------------------- | --------------------------- |
| `PUT`   | `/api/v1/profile/me/password`     | `/api/v1/profile/password`  |
| `GET`   | `/api/v1/profile/me/sessions`     | `/api/v1/profile/sessions`  |

> **Обоснование:** `/profile/me` означает «текущий пользователь» и применяется
> только к самому профилю (`GET/PATCH/DELETE /profile/me`). Sub-resources
> (sessions, password) не имеют коллекции — это всегда «мои», поэтому `/me`
> избыточен.

### Что НЕ переименовано

| Endpoint                                | Статус        |
| --------------------------------------- | ------------- |
| `GET /api/v1/profile/me`                | без изменений |
| `PATCH /api/v1/profile/me`              | без изменений |
| `DELETE /api/v1/profile/me` (GDPR)      | без изменений |
| `POST /api/v1/auth/*` (6 endpoints)     | без изменений |
| `GET /api/v1/invitations/{token}/*`     | без изменений |
| `* /api/v1/cart*` (11 endpoints)        | без изменений |
| `* /api/v1/favorites*` (9 endpoints)    | без изменений |
| `* /api/v1/orders*` (7 endpoints)       | без изменений |
| `* /api/v1/payments/intents/*`          | без изменений |
| `* /api/v1/recipients*` (5 endpoints)   | без изменений |
| `* /api/v1/geo*` (11 endpoints)         | без изменений |

---

## Раздел 2 — Новые публичные endpoints

### 2.1 Storefront taxonomy (5 endpoints)

Раньше эти данные требовали admin-token (`catalog:read`-permission) или собирались
из mock-данных на frontend'е. Теперь — публичные, с агрессивным кэшем.

```
GET /api/v1/storefront/categories                — плоский список категорий
GET /api/v1/storefront/categories/tree           — дерево (навигация, sitemap, mega-dropdown)
    Query: ?max_depth={1..10}
GET /api/v1/storefront/categories/{id}           — детали категории (breadcrumbs)

GET /api/v1/storefront/brands                    — список брендов (brand-picker)
    Query: ?offset={int}&limit={1..500}
GET /api/v1/storefront/brands/{id}               — детали бренда (brand page)
```

**Cache-Control:** `public, max-age=300, s-maxage=3600` (5 мин на клиенте, 1 ч на CDN).

**Use cases:**
- Главное меню сайта / приложения
- Sitemap (SEO)
- Filter-дропдаун в PLP
- Breadcrumbs на PDP
- Brand-page (`/brands/{slug}`)
- Brand-picker в форме «Поиск по бренду»

**Пример (frontend main с `ky`):**

```ts
// lib/api-public.ts
import ky from 'ky';

const publicApi = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_API_URL + '/api/v1',
  cache: 'force-cache',          // используем browser HTTP cache
  next: { revalidate: 300 },     // ISR на Next.js 16: 5 мин
});

export const getCategoryTree = (maxDepth = 4) =>
  publicApi.get('storefront/categories/tree', {
    searchParams: { max_depth: maxDepth },
  }).json<CategoryTreeResponse[]>();

export const getBrands = (offset = 0, limit = 200) =>
  publicApi.get('storefront/brands', {
    searchParams: { offset, limit },
  }).json<BrandListResponse>();
```

### 2.2 Pickup points для checkout (1 endpoint)

```
POST /api/v1/storefront/logistics/pickup-points
```

**Назначение:** карта ПВЗ для customer на checkout. До рефакторинга этот endpoint
был только под `/admin/logistics/pickup-points` с `logistics:read`-permission.

**Body:**
```json
{
  "country_code": "RU",
  "city": "Москва",
  "postal_code": "101000",
  "latitude": 55.7558,
  "longitude": 37.6173,
  "radius_km": 5,
  "provider_code": "cdek",
  "delivery_type": "PICKUP_POINT"
}
```

**Validation:** обязательно либо `(latitude AND longitude)`, либо `city`.
`provider_code` опционален — без него возвращаются ПВЗ всех зарегистрированных
провайдеров.

**Response:** `PickupPointsResponse` — массив маркеров с координатами, расписанием
работы, лимитами по весу/габаритам. Подходит для карты на checkout.

---

## Раздел 3 — Backward compatibility (7 дней)

Backend включает middleware `LegacyRedirectsMiddleware` (см.
`src/api/middlewares/legacy_redirects.py`) на период 2026-05-02 → 2026-05-09.

Все старые URLs возвращают **HTTP 308 Permanent Redirect** на новые. Поведение:

| Источник                                          | Куда редиректит                            |
| ------------------------------------------------- | ------------------------------------------ |
| `/api/v1/catalog/storefront/*`                    | `/api/v1/storefront/*`                     |
| `/api/v1/profile/me/sessions`                     | `/api/v1/profile/sessions`                 |
| `/api/v1/profile/me/password`                     | `/api/v1/profile/password`                 |

**Что это значит для frontend:**

- ✅ `fetch()`, `ky`, `axios`, `XMLHttpRequest` — все следуют 308 автоматически. Код
  продолжит работать без изменений.
- ⚠️ Сетевые запросы получат **+1 round-trip** на старые URLs (308 → новый URL).
  Latency-чувствительные пути (PLP, search) лучше обновить раньше срока.
- ⚠️ HTTP-кэш ответа на 308 может закрепить старый URL → правильный URL у
  пользователя. Это OK для production, но в dev-tools легко спутать с реальным
  поведением — отключи cache при отладке.
- ❌ После 2026-05-09 middleware будет удалён → старые URLs начнут отдавать **404**.

---

## Раздел 4 — Что нужно сделать frontend main

### 4.1 Глобальный поиск-замена

```bash
# В frontend/main/src/, frontend/main/e2e/, и т.д.

# Storefront — убрать /catalog/ префикс
grep -rln "/catalog/storefront/" frontend/main/src
# → заменить /catalog/storefront/ → /storefront/ во всех найденных файлах

# Profile sub-resources
grep -rln "/profile/me/sessions\|/profile/me/password" frontend/main/src
# → заменить /profile/me/sessions → /profile/sessions
# → заменить /profile/me/password → /profile/password
```

### 4.2 Обновить server-side кэширование (Next.js 16)

Storefront endpoints теперь стабильны → можно использовать ISR более агрессивно:

```ts
// app/(storefront)/page.tsx
export const revalidate = 300;  // 5 минут — тот же TTL что и backend Cache-Control
```

### 4.3 Удалить локальные mock-данные навигации

Если у вас лежат hardcoded категории/бренды в `src/mocks/`, можно удалить — теперь
есть публичный API. См. раздел 2.1.

### 4.4 Обновить openapi.json snapshot

`frontend/main/openapi.json` — пересинхронизировать после деплоя backend (если
используется для типогенерации).

### 4.5 Обновить Playwright e2e-тесты

Если e2e-сценарии хардкодят URL-paths (а не роуты Next.js) — обновить.

---

## Раздел 5 — Что НЕ должен делать frontend main

- **Не менять auth-flow.** JWT в httpOnly cookies, refresh через
  `POST /api/v1/auth/refresh` — без изменений.
- **Не менять error-handling.** Envelope
  `{"error": {"code", "message", "details", "request_id"}}` — без изменений.
- **Не менять Telegram Mini App auth.** `POST /api/v1/auth/telegram` (HMAC-SHA256
  init_data validation) — без изменений.
- **Не трогать `/cart`, `/favorites`, `/orders`, `/payments`, `/recipients`,
  `/geo`** — они как были, так и остались (URL не менялись).
- **Не использовать `_simulate-capture`** в production. Endpoint
  `POST /api/v1/payments/intents/{id}/_simulate-capture` существует, но gated
  через `ENVIRONMENT != "prod"` + `PAYMENT_SIMULATION_ENABLED=true`. Вне dev
  он возвращает `PaymentSimulationDisabledError`.

---

## Раздел 6 — Контракты ответов (что РЕАЛЬНО изменилось в payload'ах)

**Важно: изменений в response-payload'ах нет.** Только URL-paths.

| Endpoint               | Schema                              | Изменилось?     |
| ---------------------- | ----------------------------------- | --------------- |
| `/storefront/products` | `StorefrontProductsResponse`        | НЕТ             |
| `/storefront/search`   | `StorefrontSearchResponse`          | НЕТ             |
| `/profile/me`          | `ProfileResponse`                   | НЕТ             |
| `/profile/sessions`    | `list[SessionInfo]`                 | НЕТ (был тот же) |
| `/cart`, `/favorites`, `/orders`, etc. | (без изменений)             | НЕТ             |

Если используются typed-clients (`zod` / `t3-env` / OpenAPI generator) — пересборка
типов даст identity-diff на storefront endpoints.

---

## Раздел 7 — Чеклист релиза для frontend main

- [ ] Запустить grep по `/catalog/storefront/` и `/profile/me/(sessions|password)`,
      найти и заменить пути.
- [ ] Если используются хардкодные mock-категории/бренды — удалить, переключить
      на `GET /storefront/categories/tree` и `GET /storefront/brands`.
- [ ] Обновить `frontend/main/openapi.json` (если используется для type-gen).
- [ ] Запустить Playwright e2e локально против обновлённого backend'а.
- [ ] Деплой в staging, smoke-test навигации (меню, breadcrumbs, поиск, PDP).
- [ ] Сравнить latency p50/p95 storefront endpoints до и после (убедиться, что
      нет 308-петель на критическом пути).
- [ ] Убедиться, что frontend main не получает 308 редиректы на новых путях.
- [ ] Production deploy окно: до 2026-05-09 (когда удаляется legacy middleware).

---

## Раздел 8 — Контакты и эскалация

- Backend ground truth: `tests/architecture/test_router_audience.py:_ALLOWED_PREFIX_ROOTS`.
- Полная карта изменений (admin + customer): [`router-restructure-2026-05.md`](./router-restructure-2026-05.md).
- Стандарт naming: `backend/CLAUDE.md` § *Router naming convention*.
- При обнаружении 404 после миграции — проверить, что путь **точно**
  совпадает с одной из строк в разделе 1 этого документа (новая колонка).
- При обнаружении 308 на новом пути — баг в backend, эскалировать.
