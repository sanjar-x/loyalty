# Задача: страница менеджмента провайдерских аккаунтов логистики

**Дата:** 2026-05-14
**Компонент:** `frontend-admin`
**Цель:** создать в админ-панели страницу для CRUD-управления аккаунтами логистических провайдеров (CDEK, Yandex Delivery, DobroPost). Сейчас их можно настраивать только прямыми curl-вызовами к backend — операторам нужен UI.

---

## 1. Контекст

Backend хранит конфигурацию каждого логистического провайдера в таблице `provider_accounts`: учётные данные (OAuth-токены, логины) + произвольный `config` (адрес склада-отправителя, тестовый режим, тайм-ауты, webhook-секреты). От этих данных зависит расчёт стоимости доставки, бронирование, трекинг.

Сейчас, чтобы, например, прописать `default_origin` для Яндекса или сменить OAuth-токен CDEK, оператор вынужден дёргать API руками. Нужна страница **«Настройки → Провайдеры доставки»**.

Backend API уже полностью готов — 7 endpoints под `/api/v1/admin/logistics/provider-accounts`. Задача чисто фронтовая: BFF-прокси + FSD-слайсы + страница.

---

## 2. Backend API контракт

Все endpoints: префикс `/api/v1/admin/logistics/provider-accounts`, требуют permission **`logistics:admin`** (доступен только роли `admin`, не `manager`).

> ⚠️ **Все поля JSON в этом API — `snake_case`** (`provider_code`, `is_active`, `created_at`, `credential_fingerprints`...), и в запросах, и в ответах. Модуль `logistics` — единственный в проекте, который НЕ использует общий базовый класс `CamelModel`: его схемы (`schemas_admin.py`, `schemas.py`) наследуют голый `pydantic.BaseModel`. Остальные 12 модулей (`identity`, `catalog`, `order`, ...) через `CamelModel` отдают `camelCase`. Это backend-техдолг (нарушение конвенции из `src/shared/schemas.py`). **Запущена задача унификации всего API на camelCase** — `apps/backend/docs/api/api-camelcase-unification-task-2026-05-14.md`. Согласуй с backend порядок работ: если унификация выходит раньше этой страницы — сразу пиши клиент на camelCase; если позже — пиши на текущем `snake_case`, переходный период (backend на время принимает оба варианта на вход) даст окно на правку. Финальная истина по именам полей — `/openapi.json`.

### 2.1 Endpoints

| Метод    | Путь           | Назначение                                                    |
| -------- | -------------- | ------------------------------------------------------------- |
| `GET`    | `/`            | Список. Query: `provider_code` (фильтр), `only_active` (bool) |
| `GET`    | `/{id}`        | Один аккаунт                                                  |
| `POST`   | `/`            | Создать                                                       |
| `PUT`    | `/{id}`        | Частичное обновление                                          |
| `POST`   | `/{id}/active` | Активировать / деактивировать                                 |
| `DELETE` | `/{id}`        | Удалить (hard delete), `204 No Content`                       |
| `POST`   | `/refresh`     | Пересобрать in-memory registry провайдеров на worker'е        |

### 2.2 Схема ответа — `ProviderAccountResponse`

```jsonc
{
  "id": "uuid",
  "provider_code": "yandex_delivery",
  "name": "Yandex Delivery (production)",
  "is_active": true,
  "credential_fingerprints": {
    // на каждый ключ credentials — отпечаток, НЕ само значение
    "oauth_token": { "fingerprint": "a1b2c3d4", "length": 39 },
  },
  "config": {
    // произвольный JSON, см. раздел 3
    "test_mode": false,
    "default_origin": {
      "country_code": "RU",
      "city": "Москва",
      "metadata": { "platform_station_id": "..." },
    },
  },
  "created_at": "2026-05-14T...",
  "updated_at": "2026-05-14T...",
}
```

`GET /` возвращает `{ "items": [ProviderAccountResponse, ...] }`.

> ⚠️ **`credentials` НИКОГДА не возвращаются в открытом виде.** Только `credential_fingerprints` — первые 8 hex символов SHA-256 + длина значения. Это нужно показать в UI как индикатор «какой ключ сейчас стоит» (`oauth_token: a1b2c3d4 · 39 симв.`), но отредактировать значение можно только перезаписью целиком.

### 2.3 Тело `POST /` — `CreateProviderAccountRequest`

```jsonc
{
  "provider_code": "yandex_delivery", // snake_case! min 1, max 50
  "name": "Yandex Delivery (production)", // min 1, max 255
  "credentials": { "oauth_token": "y0__..." }, // непустой dict, провайдер-специфичный
  "config": { "test_mode": false }, // опционально, по умолчанию {}
  "is_active": true, // опционально, по умолчанию true
}
```

> Имена полей — **snake_case** и в `Create`/`Update`, и в ответах (см. предупреждение в начале раздела 2). Проверяй по `/openapi.json`, не доверяй догадкам.

### 2.4 Тело `PUT /{id}` — `UpdateProviderAccountRequest`

```jsonc
{
  "name": "string | null", // опционально
  "credentials": "dict | null", // опционально — ЗАМЕНЯЕТ целиком
  "config": "dict | null", // опционально
  "replace_config": false, // по умолчанию false
}
```

Все поля опциональны; отсутствующее = не менять.

### 2.5 Тело `POST /{id}/active` — `SetProviderAccountActiveRequest`

```jsonc
{ "is_active": true }
```

### 2.6 Ответ `POST /refresh` — `RefreshRegistryResponse`

```jsonc
{
  "registered_provider_codes": ["cdek", "yandex_delivery"],
  "note": "Registry refreshed on the worker that served this request...",
}
```

---

## 3. Провайдеры и их поля

Поддерживаются ровно **3** провайдера (по зарегистрированным фабрикам в `bootstrap.py`). `russian_post` существует как константа, но фабрики нет — **в список выбора не добавлять**.

### `cdek`

| Группа      | Поле              | Тип    | Обяз.                       |
| ----------- | ----------------- | ------ | --------------------------- |
| credentials | `client_id`       | string | да                          |
| credentials | `client_secret`   | string | да                          |
| config      | `test_mode`       | bool   | нет (default false)         |
| config      | `timeout_seconds` | number | нет (default 30)            |
| config      | `max_retries`     | number | нет (default 3)             |
| config      | `default_origin`  | object | нужен для расчёта (см. 3.1) |

### `yandex_delivery`

| Группа      | Поле                              | Тип    | Обяз.                                                |
| ----------- | --------------------------------- | ------ | ---------------------------------------------------- |
| credentials | `oauth_token`                     | string | да                                                   |
| config      | `test_mode`                       | bool   | нет                                                  |
| config      | `platform_station_id`             | string | нет (fallback, если нет в `default_origin.metadata`) |
| config      | `default_inn`                     | string | нет                                                  |
| config      | `default_nds`                     | number | нет                                                  |
| config      | `payment_method`                  | string | нет (`already_paid` / `card_on_receipt`)             |
| config      | `timeout_seconds` / `max_retries` | number | нет                                                  |
| config      | `default_origin`                  | object | нужен для расчёта (см. 3.1)                          |

### `dobropost`

| Группа      | Поле                              | Тип      | Обяз.                                    |
| ----------- | --------------------------------- | -------- | ---------------------------------------- |
| credentials | `email`                           | string   | **да** (backend вернёт 400 если пусто)   |
| credentials | `password`                        | string   | **да** (backend вернёт 400 если пусто)   |
| config      | `base_url`                        | string   | нет                                      |
| config      | `timeout_seconds` / `max_retries` | number   | нет                                      |
| config      | `webhook_secret`                  | string   | **либо это, либо `webhook_allowed_ips`** |
| config      | `webhook_allowed_ips`             | string[] | **либо это, либо `webhook_secret`**      |
| config      | `default_origin`                  | object   | нужен для расчёта                        |

> Для DobroPost backend валидирует на стороне сервера (`provider_validators.py`): `email`+`password` обязательны, и хотя бы одно из `webhook_secret` / `webhook_allowed_ips`. Нарушение → `400` с `error.code` `DOBROPOST_CREDENTIALS_INVALID` / `DOBROPOST_WEBHOOK_AUTH_REQUIRED`. Продублируй проверки на клиенте для UX, но финальный арбитр — backend.

### 3.1 Под-форма `default_origin` (адрес склада-отправителя)

```jsonc
{
  "country_code": "RU", // обязательно (backend-резолвер требует)
  "city": "Москва", // обязательно
  "region": "Москва", // опц.
  "postal_code": "125167", // опц.
  "street": "...", // опц.
  "house": "...", // опц.
  "latitude": 55.78, // опц.
  "longitude": 37.55, // опц.
  "metadata": {
    // провайдер-специфично:
    "platform_station_id": "...", // Yandex Delivery
    "cdek_pvz_code": "MSK1", // CDEK
    "cdek_city_code": "44", // CDEK
  },
}
```

`country_code` + `city` обязательны — иначе при расчёте доставки backend отдаёт `PROVIDER_UNAVAILABLE`.

---

## 4. Что создать (FSD-структура)

Следуй конвенциям из `docs/ARCHITECTURE.md`. Слайсы и их публичный контракт — только через `index.js`.

```
src/
├── app/
│   ├── api/logistics-providers/
│   │   ├── route.js                  # GET (список) + POST (создать)
│   │   ├── [id]/route.js             # GET + PUT + DELETE
│   │   ├── [id]/active/route.js      # POST
│   │   └── refresh/route.js          # POST
│   └── admin/settings/logistics-providers/
│       ├── page.jsx                  # страница (список + кнопки)
│       └── page.module.css           # если нужны кастомные стили
├── entities/logistics-provider/
│   ├── api/
│   │   ├── keys.js                   # TanStack query-key factory
│   │   ├── logistics-providers.js    # fetch/mutate функции через apiClient
│   │   ├── queries.js                # useProviderAccounts, useProviderAccount
│   │   └── mutations.js              # use{Create,Update,SetActive,Delete,Refresh}...
│   ├── lib/
│   │   └── provider-schema.js        # описание полей per provider_code (раздел 3)
│   ├── ui/
│   │   └── ProviderAccountCard.jsx   # карточка в списке
│   └── index.js
└── features/logistics-provider-form/
    ├── ui/
    │   ├── ProviderAccountFormModal.jsx    # create/edit modal
    │   └── DeleteProviderConfirmModal.jsx  # подтверждение удаления
    └── index.js
```

Маршрут страницы: `/admin/settings/logistics-providers` (раздел «Настройки», рядом с `suppliers`, `promocodes`, `roles`). Добавь ссылку в навигацию раздела settings (см. как сделаны соседние пункты в `src/app/admin/settings/`).

### 4.1 BFF routes

Используй фабрику `proxyToBackend` из `@/shared/api/bff` — она сама подставляет `Bearer` из cookie, проксирует тело и envelope ошибок. Пример из `src/app/api/suppliers/route.js`:

```js
// src/app/api/logistics-providers/route.js
import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: (_params, search) => {
    const qs = new URLSearchParams();
    const providerCode = search.get('providerCode');
    const onlyActive = search.get('onlyActive');
    if (providerCode) qs.set('provider_code', providerCode);
    if (onlyActive) qs.set('only_active', onlyActive);
    const s = qs.toString();
    return `/api/v1/admin/logistics/provider-accounts${s ? `?${s}` : ''}`;
  },
  forwardSearch: false,
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/logistics/provider-accounts',
  successStatus: 201,
});
```

```js
// src/app/api/logistics-providers/[id]/route.js
export const GET = proxyToBackend({
  pathFn: (p) => `/api/v1/admin/logistics/provider-accounts/${p.id}`,
});
export const PUT = proxyToBackend({
  method: 'PUT',
  pathFn: (p) => `/api/v1/admin/logistics/provider-accounts/${p.id}`,
});
export const DELETE = proxyToBackend({
  method: 'DELETE',
  pathFn: (p) => `/api/v1/admin/logistics/provider-accounts/${p.id}`,
});
```

```js
// src/app/api/logistics-providers/[id]/active/route.js
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: (p) => `/api/v1/admin/logistics/provider-accounts/${p.id}/active`,
});

// src/app/api/logistics-providers/refresh/route.js
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/logistics/provider-accounts/refresh',
});
```

> ⚠️ Edge proxy (`src/proxy.js`) уже покрывает `/api/*` своим matcher'ом — auth/refresh подхватятся автоматически, ничего отдельно делать не нужно.

### 4.2 Entity API слой

Повтори паттерн `entities/supplier/api/*`:

```js
// keys.js
export const providerAccountKeys = {
  all: ['logistics-providers'],
  lists: () => [...providerAccountKeys.all, 'list'],
  list: (filters) => [...providerAccountKeys.lists(), filters],
  details: () => [...providerAccountKeys.all, 'detail'],
  detail: (id) => [...providerAccountKeys.details(), id],
};

// logistics-providers.js — через apiClient из @/shared/api/client-fetch
export const fetchProviderAccounts = (filters) =>
  apiClient.get('/api/logistics-providers' + qs(filters));
export const fetchProviderAccount = (id) =>
  apiClient.get(`/api/logistics-providers/${id}`);
export const createProviderAccount = (payload) =>
  apiClient.post('/api/logistics-providers', payload);
export const updateProviderAccount = (id, payload) =>
  apiClient.put(`/api/logistics-providers/${id}`, payload);
export const setProviderAccountActive = (id, isActive) =>
  apiClient.post(`/api/logistics-providers/${id}/active`, {
    is_active: isActive,
  });
export const deleteProviderAccount = (id) =>
  apiClient.del(`/api/logistics-providers/${id}`);
export const refreshProviderRegistry = () =>
  apiClient.post('/api/logistics-providers/refresh');
```

Мутации (`mutations.js`) — `useMutation` + `qc.invalidateQueries({ queryKey: providerAccountKeys.lists() })` в `onSuccess`. `staleTime` для списка — `DEFAULT_STALE_TIME_MS` (это не reference data, а конфиг, который меняют редко, но и кэшировать на 5 минут нет смысла; 30 сек ок).

---

## 5. UI-спецификация

### 5.1 Страница (`page.jsx`)

- `'use client'`, обёртка `<section>`.
- Заголовок «Провайдеры доставки» + кнопка «Добавить провайдера».
- Опциональный фильтр по `providerCode` и тумблер «только активные».
- Список карточек `ProviderAccountCard` (см. 5.2). Состояния: loading → `Skeleton`, error → `ApiErrorState` (оба из `@/shared/ui`), пусто → пустой плейсхолдер с текстом.
- Модалки create/edit/delete — состояние открытия держит страница.

### 5.2 `ProviderAccountCard`

Показывает: `name`, бейдж `provider_code`, бейдж статуса (`Активен` / `Отключён` — компонент `Badge` из `@/shared/ui`), `updated_at` (формат через `formatDateTime` из `@/shared/lib/utils`).

Действия на карточке:

- **Редактировать** → открывает `ProviderAccountFormModal` в режиме edit.
- **Активировать / Отключить** → тумблер, дёргает `setProviderAccountActive`.
- **Удалить** → открывает `DeleteProviderConfirmModal`.

Под именем — компактный список fingerprint'ов credentials: `oauth_token · a1b2c3d4 · 39 симв.`. Это read-only индикатор.

### 5.3 `ProviderAccountFormModal` (create + edit)

Базируется на `Modal` из `@/shared/ui` (size `lg` или `xl`). Форма **динамическая по `provider_code`**:

1. **Шаг выбора провайдера** (только в режиме create): селект `cdek` / `yandex_delivery` / `dobropost`. В режиме edit — `provider_code` не меняется, показывается как read-only.
2. **`name`** — текстовое поле.
3. **Секция Credentials** — поля из таблицы раздела 3 в зависимости от `provider_code`.
   - **Create:** все credential-поля обязательны (по схеме провайдера).
   - **Edit:** показываем fingerprint'ы текущих значений как подпись; поля ввода **пустые и опциональные**. См. критичный нюанс 6.1.
4. **Секция Config** — `test_mode` (чекбокс), под-форма `default_origin` (раздел 3.1), плюс провайдер-специфичные поля. Числовые `timeout_seconds` / `max_retries` — опциональные.
   - Для **MVP допустимо**: ключевые поля (`test_mode`, `default_origin`, `platform_station_id`) — структурированными инпутами, а «хвост» config — одним JSON-textarea с валидацией `JSON.parse`. Полную типизированную форму можно доделать итерацией 2.
5. **`is_active`** — чекбокс (только create; в edit статус меняется тумблером на карточке).
6. Кнопка submit — `disabled` пока форма невалидна.

### 5.4 `DeleteProviderConfirmModal`

Подтверждение с явным текстом: «Удалить аккаунт “{name}” ({provider_code})? Действие необратимо». Паттерн — как `DeleteBrandConfirmModal` в `features/brand-form`.

---

## 6. Критичные нюансы (читать обязательно)

### 6.1 Credentials в режиме Edit — replace целиком, не merge

`credentials` при `PUT` **заменяют весь объект целиком** (backend не делает merge — by design). Поэтому:

- Если оператор в Edit **не трогал** ни одного поля credentials → **не отправлять ключ `credentials` вообще** (оставить `undefined`). Иначе перезатрёшь рабочий токен пустотой.
- Если оператор заполнил **хотя бы одно** поле → нужно отправить **все credential-поля этого провайдера разом** (например, для CDEK — и `client_id`, и `client_secret`). Иначе незаполненные пропадут.
- В UI это лучше оформить как явное действие: чекбокс / кнопка «Сменить учётные данные», которая раскрывает полный набор полей. Без неё — credentials не трогаются.

### 6.2 Config — shallow-merge только верхнего уровня

`PUT` с `replace_config: false` (дефолт) делает `{...старый_config, ...новый_config}` — **merge только на верхнем уровне**. Вложенный `default_origin` при этом **заменяется целиком**: если отправить `config: { default_origin: { metadata: {...} } }`, потеряются `country_code` и `city`.

**Рекомендация:** на Edit всегда грузи полный `config` из `GET /{id}`, давай редактировать его целиком в форме, и отправляй **весь объект `config` с `replace_config: true`**. Так фронт всегда оперирует полным состоянием и нет сюрпризов с частичным merge.

### 6.3 Обязательный `refresh` после мутаций

In-memory registry провайдеров на backend строится **при старте процесса**. После `create` / `update` / `delete` / `active` изменения в БД есть, но работающий backend их **не подхватит**, пока не вызвать `POST /refresh` или не передеплоить.

- После успешной мутации — автоматически дёргай `refreshProviderRegistry()` и показывай тост вроде «Сохранено. Реестр провайдеров обновлён».
- ⚠️ На production несколько процессов с этим registry (**web** + **core-worker**). Запрос через публичный домен попадёт только в web-инстанс. Честно покажи это оператору: тост-предупреждение «Изменения применены на web-инстансе. Для полного применения может потребоваться передеплой backend». Текст `note` из ответа `/refresh` можно показать как есть.

### 6.4 Permission `logistics:admin` → обработка 403

Endpoints требуют `logistics:admin` (только роль `admin`). `useAuth()` сейчас не отдаёт список permissions — поэтому:

- Не пытайся прятать страницу заранее по правам (нечем проверить).
- Обрабатывай `403` от API: показывай понятный экран «Недостаточно прав — нужен доступ logistics:admin», а не общую ошибку.
- (Опционально, если будет backend-доработка отдавать permissions в `/api/auth/me` — тогда прятать пункт меню. Сейчас — не блокер.)

### 6.5 Конфликты single-active (409)

Нельзя иметь **2 активных аккаунта одного `provider_code`** одновременно. Backend вернёт `409` с `error.code` `CONFLICT` при попытке:

- создать активный аккаунт, когда активный того же провайдера уже есть;
- активировать второй аккаунт того же провайдера.

Обрабатывай `409` отдельным понятным сообщением: «Для провайдера {X} уже есть активный аккаунт. Сначала отключите его». `error.details.existing_account_id` / `conflicting_account_id` содержит id конфликтующей записи — можно дать ссылку на неё.

### 6.6 Маппинг ошибок backend

`apiClient` уже бросает `ApiError` с `.code` / `.status` / `.message` / `.details`. Заведи code-keyed словарь переводов (паттерн `translationsByCode` в `client-fetch.js`):

| `error.code`                      | Сообщение оператору                                          |
| --------------------------------- | ------------------------------------------------------------ |
| `CONFLICT`                        | «Активный аккаунт для этого провайдера уже существует»       |
| `DOBROPOST_CREDENTIALS_INVALID`   | «DobroPost требует непустые email и пароль»                  |
| `DOBROPOST_WEBHOOK_AUTH_REQUIRED` | «Укажите webhook_secret или хотя бы один webhook_allowed_ip» |
| `VALIDATION_ERROR`                | показать `details` (per-field)                               |
| `NOT_FOUND`                       | «Аккаунт не найден (возможно, удалён в другой вкладке)»      |
| `FORBIDDEN` / 403                 | «Недостаточно прав: нужен доступ logistics:admin»            |

---

## 7. Acceptance criteria

- [ ] Страница `/admin/settings/logistics-providers` открывается, есть ссылка в навигации «Настройки».
- [ ] Список показывает все аккаунты с провайдером, статусом, fingerprint'ами credentials, датой обновления; состояния loading / error / empty обработаны.
- [ ] Создание аккаунта для каждого из 3 провайдеров (`cdek`, `yandex_delivery`, `dobropost`) с провайдер-специфичными полями работает.
- [ ] Редактирование `name` и `config` (включая `default_origin`) работает; `config` отправляется полным объектом с `replace_config: true`.
- [ ] Редактирование БЕЗ смены credentials не отправляет ключ `credentials` и не затирает токен.
- [ ] Смена credentials отправляет полный набор полей провайдера.
- [ ] Активация / деактивация через тумблер работает; попытка активировать второй аккаунт того же провайдера показывает понятное сообщение про конфликт (409).
- [ ] Удаление с подтверждением работает (`204`).
- [ ] После любой мутации автоматически вызывается `/refresh`, оператор видит тост с результатом и предупреждением про multi-worker.
- [ ] Ошибки `400` (DobroPost-валидация), `403`, `404`, `409` показываются понятными русскими сообщениями, а не сырым кодом.
- [ ] ESLint проходит (слайс-границы FSD, импорты только через `index.js`).
- [ ] a11y: модалки на базе `Modal` из `@/shared/ui` (focus-trap, Esc, aria уже встроены).

---

## 8. Рекомендуемая последовательность

1. **BFF routes** (`app/api/logistics-providers/**`) — 4 файла, ~10 строк каждый. Сразу проверь через браузер/Postman, что проксирование работает (нужен залогиненный admin).
2. **Entity слой** (`entities/logistics-provider/`) — keys, fetch-функции, `provider-schema.js` с описанием полей per provider, queries, mutations.
3. **Страница + карточка** — список с loading/error/empty, без форм. Уже можно смотреть данные.
4. **Form modal** — динамическая форма create/edit. Самая объёмная часть; начни с `cdek` (2 credential-поля), потом `yandex_delivery`, `dobropost`.
5. **Delete confirm + active toggle + refresh-after-mutation + маппинг ошибок.**
6. Прогон smoke: создать тестовый аккаунт CDEK в `test_mode`, отредактировать config, деактивировать, удалить — каждый шаг с проверкой `/refresh`.

Оценка: BFF + entity ~0.5 дня, страница+карточка ~0.5 дня, форма ~1–1.5 дня, полировка ошибок/refresh/a11y ~0.5 дня. Итого ~3 дня.

---

## 9. Справочные файлы

**Backend (контракт — не менять):**

- `apps/backend/src/modules/logistics/presentation/router_admin.py` — endpoints
- `apps/backend/src/modules/logistics/presentation/schemas_admin.py` — Pydantic-схемы запросов/ответов
- `apps/backend/src/modules/logistics/application/commands/manage_provider_accounts.py` — поведение (merge, конфликты)
- `apps/backend/src/modules/logistics/application/commands/provider_validators.py` — серверная валидация DobroPost
- `apps/backend/src/modules/logistics/infrastructure/providers/{cdek,yandex_delivery,dobropost}/factory.py` — точные имена полей credentials/config (docstring каждой фабрики)
- `apps/backend/src/modules/logistics/infrastructure/adapters/origin_address_resolver.py` — структура `default_origin`
- Swagger backend `/docs` и `/openapi.json` — финальная истина по именам полей
- `apps/backend/docs/api/api-camelcase-unification-task-2026-05-14.md` — связанная backend-задача: перевод всего API (включая эти эндпоинты) на camelCase

**Frontend (паттерны — копировать):**

- `src/app/api/suppliers/route.js` — образец BFF route с `proxyToBackend`
- `src/entities/supplier/` — образец entity-слайса (keys / queries / mutations / index)
- `src/shared/api/bff.js`, `src/shared/api/client-fetch.js` — `proxyToBackend`, `apiClient`, `ApiError`
- `src/shared/ui/Modal.jsx` — базовая модалка
- `src/features/brand-form/ui/` — образец form modal + delete confirm
- `src/app/admin/settings/promocodes/page.jsx` — образец реализованной CRUD-страницы в settings
- `src/shared/query/defaults.js` — staleTime windows
- `docs/ARCHITECTURE.md` — правила FSD-слоёв и «куда класть новый код»

---

Если по ходу всплывут вопросы по backend-контракту (точные имена полей, поведение при edge-кейсах) — лучше уточнить, чем гадать: контракт в коде выше + Swagger. Менять backend под фронт без согласования не нужно — API уже рабочий.
