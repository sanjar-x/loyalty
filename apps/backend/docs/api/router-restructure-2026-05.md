# API Router restructure (2026-05)

> **Статус**: в работе. Этот документ — единственный источник правды для синхронизации
> frontend (admin + main) и любых внешних интеграций. Фиксирует **полный список изменений
> URL-путей** в формате «было → стало», и описывает принятый стандарт.

## TL;DR

* Все админ-эндпоинты переносятся под `/api/v1/admin/<module>/<resource>`.
* Customer/public эндпоинты остаются под `/api/v1/<resource>` без `/admin`.
* Все webhook-эндпоинты собираются под `/api/v1/webhooks/<provider>`.
* Файловая конвенция: один router-файл на одну аудиторию (`router_admin.py`,
  `router_customer.py`/`router_storefront.py`, `router_webhooks.py`).
* Tags в OpenAPI: `Admin / <Resource>`, `<Resource>`, `Webhooks / <Provider>`.

## Принятый стандарт (краткая версия)

См. backend/CLAUDE.md, раздел «Router naming convention». Ground truth для модулей —
`tests/architecture/test_boundaries.py:MODULES`. Ground truth для admin/customer
инварианта — `tests/architecture/test_router_audience.py` (новый).

## Migration map: было → стало

### Catalog (11 routers)

| Было                                                       | Стало                                                       | Аудитория |
| ---------------------------------------------------------- | ----------------------------------------------------------- | --------- |
| `GET /api/v1/catalog/brands`                                | `GET /api/v1/storefront/brands`                              | public    |
| `GET /api/v1/catalog/brands/{id}`                           | `GET /api/v1/storefront/brands/{id}`                         | public    |
| `POST/PATCH/DELETE /api/v1/catalog/brands*`                 | `POST/PATCH/DELETE /api/v1/admin/catalog/brands*`            | admin     |
| `GET /api/v1/catalog/categories*`                           | `GET /api/v1/storefront/categories*`                         | public    |
| `POST/PATCH/DELETE /api/v1/catalog/categories*`             | `POST/PATCH/DELETE /api/v1/admin/catalog/categories*`        | admin     |
| `GET /api/v1/catalog/categories/tree`                       | `GET /api/v1/storefront/categories/tree` (public) ИЛИ `GET /api/v1/admin/catalog/categories/tree` (staff) | public + admin |
| —                                                            | `GET /api/v1/storefront/categories` (public flat list)       | public    |
| —                                                            | `GET /api/v1/storefront/categories/{id}` (public detail)     | public    |
| —                                                            | `GET /api/v1/storefront/brands` (public list)                | public    |
| —                                                            | `GET /api/v1/storefront/brands/{id}` (public detail)         | public    |
| `* /api/v1/catalog/products*`                               | `* /api/v1/admin/catalog/products*`                          | admin     |
| `* /api/v1/catalog/products/{id}/variants*`                 | `* /api/v1/admin/catalog/products/{id}/variants*`            | admin     |
| `* /api/v1/catalog/products/{id}/variants/{vid}/skus*`      | `* /api/v1/admin/catalog/products/{id}/variants/{vid}/skus*` | admin     |
| `* /api/v1/catalog/attributes*`                             | `* /api/v1/admin/catalog/attributes*`                        | admin     |
| `* /api/v1/catalog/attribute-groups*`                       | `* /api/v1/admin/catalog/attribute-groups*`                  | admin     |
| `* /api/v1/catalog/attribute-templates*`                    | `* /api/v1/admin/catalog/attribute-templates*`               | admin     |
| `* /api/v1/catalog/products/{id}/attributes*`               | `* /api/v1/admin/catalog/products/{id}/attributes*`          | admin     |
| `* /api/v1/catalog/products/{id}/media*`                    | `* /api/v1/admin/catalog/products/{id}/media*`               | admin     |
| `GET /api/v1/catalog/storefront/products*`                  | `GET /api/v1/storefront/products*`                            | public    |
| `GET /api/v1/catalog/storefront/search*`                    | `GET /api/v1/storefront/search*`                              | public    |
| `GET /api/v1/catalog/storefront/trending`                   | `GET /api/v1/storefront/trending`                             | public    |
| `GET /api/v1/catalog/storefront/for-you`                    | `GET /api/v1/storefront/for-you`                              | public    |
| `GET /api/v1/catalog/storefront/categories/{id}`            | `GET /api/v1/storefront/categories/{id}`                      | public    |

> Префикс `/catalog` исчезает: чистый домен `catalog` уже отражён в имени модуля; на URL-уровне
> используется `storefront` (для покупателя) или `admin/catalog` (для staff). Это короче и
> снимает повторение `/catalog/storefront/*`.

### Pricing (9 routers — все admin)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `* /api/v1/pricing/variables*`                              | `* /api/v1/admin/pricing/variables*`                         |
| `* /api/v1/pricing/contexts*`                               | `* /api/v1/admin/pricing/contexts*`                          |
| `* /api/v1/pricing/contexts/{id}/formula*`                  | `* /api/v1/admin/pricing/contexts/{id}/formula*`             |
| `POST /api/v1/pricing/preview`                              | `POST /api/v1/admin/pricing/preview`                         |
| `* /api/v1/pricing/products*`                               | `* /api/v1/admin/pricing/products*`                          |
| `* /api/v1/pricing/suppliers/{id}/pricing*`                 | `* /api/v1/admin/pricing/suppliers/{id}*`                    |
| `* /api/v1/pricing/supplier-type-mapping*`                  | `* /api/v1/admin/pricing/supplier-type-mapping*`             |
| `* /api/v1/pricing/categories/{id}/pricing*`                | `* /api/v1/admin/pricing/categories/{id}*`                   |
| `POST /api/v1/pricing/recompute*`                           | `POST /api/v1/admin/pricing/recompute*`                      |

> Двойной `pricing` (`/pricing/categories/{id}/pricing`) убираем — после `/admin/pricing/`
> второй `pricing` — шум.

### Supplier (1)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `* /api/v1/suppliers*`                                      | `* /api/v1/admin/suppliers*`                                 |

### Logistics (3)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `* /api/v1/logistics/quotes`                                | `POST /api/v1/admin/logistics/quotes`                        |
| `* /api/v1/logistics/shipments*`                            | `* /api/v1/admin/logistics/shipments*`                       |
| `* /api/v1/admin/logistics/provider-accounts*`              | `* /api/v1/admin/logistics/provider-accounts*` (без изменений) |
| `POST /api/v1/logistics/webhooks/{provider}`                | `POST /api/v1/webhooks/logistics/{provider}`                 |
| `POST /api/v1/admin/logistics/pickup-points` (admin only)   | + добавлен публичный `POST /api/v1/storefront/logistics/pickup-points` для checkout map |

### Identity (6)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `POST /api/v1/auth/*`                                       | `POST /api/v1/auth/*` (без изменений)                        |
| `GET/POST /api/v1/admin/identities*`, `/admin/roles*`, `/admin/permissions*` | без изменений |
| `* /api/v1/admin/staff*`                                    | без изменений                                                |
| `* /api/v1/admin/customers*`                                | без изменений                                                |
| `GET /api/v1/profile/me/sessions`                           | `GET /api/v1/profile/sessions` (объединение namespace `/profile/`) |
| `PUT /api/v1/profile/me/password`                           | `PUT /api/v1/profile/password`                               |
| `POST /api/v1/invitations/{token}/*`                        | без изменений                                                |

### User (1)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `GET /api/v1/profile/me`                                    | `GET /api/v1/profile/me` (без изменений)                     |
| `PATCH /api/v1/profile/me`                                  | `PATCH /api/v1/profile/me`                                   |
| `DELETE /api/v1/profile/me`                                 | `DELETE /api/v1/profile/me`                                  |

> `user.router_profile` и `identity.router_account` оба монтировались на `/profile`.
> Теперь они объединены в одном namespace, но в разных файлах. Конфликтов путей нет.

### Order (3)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `* /api/v1/orders*` (customer)                              | без изменений                                                |
| `* /api/v1/admin/orders*`                                   | без изменений                                                |
| `POST /api/v1/orders/webhooks/dobropost/{token}`            | `POST /api/v1/webhooks/dobropost/{token}`                    |

### Payment (1)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `GET  /api/v1/payments/intents/{id}`                        | без изменений                                                |
| `POST /api/v1/payments/intents/{id}/_simulate-capture`      | без изменений (gated by ENVIRONMENT + PAYMENT_SIMULATION_ENABLED) |
| `POST /api/v1/payments/webhooks/{provider}`                 | `POST /api/v1/webhooks/payments/{provider}` (унификация webhooks namespace) |

### Recipient (1)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `* /api/v1/recipients*`                                     | без изменений                                                |

### Geo (2)

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `GET /api/v1/geo/*`                                         | без изменений                                                |
| `* /api/v1/admin/geo/*`                                     | без изменений                                                |

### Cart, Favorites, Activity — без изменений

| Было                                                       | Стало                                                       |
| ---------------------------------------------------------- | ----------------------------------------------------------- |
| `* /api/v1/cart*`                                           | без изменений                                                |
| `* /api/v1/favorites*`                                      | без изменений                                                |
| `GET /api/v1/admin/analytics/*`                             | без изменений                                                |

## Сводка по namespace'ам после рефакторинга

```
/api/v1/
├── auth/                       — auth.login/refresh/logout (public + JWT exit)
├── profile/                    — текущий пользователь (PII + sessions + password)
├── invitations/                — staff invitation accept (public + token)
│
├── storefront/                 — публичный каталог
│   ├── brands/
│   ├── categories/
│   ├── products/
│   ├── search/
│   ├── trending/
│   ├── for-you/
│
├── cart/                       — customer cart
├── favorites/                  — customer multi-list favorites
├── orders/                     — customer's own orders
├── payments/                   — customer payment intents
├── recipients/                 — customer customs recipients
├── geo/                        — public geo reference
│
├── admin/                      — staff-only
│   ├── catalog/
│   │   ├── brands/
│   │   ├── categories/
│   │   ├── products/
│   │   ├── attributes/
│   │   ├── attribute-groups/
│   │   ├── attribute-templates/
│   │   └── products/{id}/{variants,attributes,media,...}
│   ├── pricing/
│   │   ├── variables/
│   │   ├── contexts/
│   │   ├── products/
│   │   ├── suppliers/{id}/
│   │   ├── categories/{id}/
│   │   ├── supplier-type-mapping/
│   │   ├── recompute/
│   │   └── preview
│   ├── suppliers/
│   ├── logistics/
│   │   ├── provider-accounts/
│   │   ├── shipments/
│   │   └── quotes (POST)
│   ├── orders/
│   ├── identities/             — identity admin actions
│   ├── roles/
│   ├── permissions/
│   ├── staff/
│   ├── customers/
│   ├── geo/
│   └── analytics/
│
└── webhooks/                   — server-to-server
    ├── dobropost/{token}
    └── logistics/{provider}
```

## Frontend sync — checklist

### `frontend/admin/`

* `src/shared/api/api-client.js` — `backendFetch()` без изменений (URL формируется в каждом
  `services/*.js`, `entities/*/api/*.js`).
* Найти все обращения к `/catalog/brands`, `/catalog/categories`, `/catalog/products`,
  `/catalog/attributes*`, `/catalog/attribute-groups`, `/catalog/attribute-templates`,
  `/pricing/*`, `/suppliers`, `/logistics/*` и заменить на `/admin/...` варианты.
* `app/api/*` BFF-routes — убедиться, что server-side маршрут также обновлён.
* `openapi/backend.json` и `openapi/backend-mini.json` — пересинхронизировать после деплоя бэка.

### `frontend/main/`

* Обращения через `lib/api-client.ts` (browser) и `lib/api-server.ts` (BFF):
  * `/catalog/storefront/*` → `/storefront/*` (минус префикс `/catalog`)
  * `/catalog/brands`, `/catalog/categories/tree` → `/storefront/brands`,
    `/storefront/categories/tree`.
* `app/api/*` BFF — обновить server-side маршрут.

### Внешние интеграции (S2S)

* DobroPost webhook URL в их кабинете: было `https://.../api/v1/orders/webhooks/dobropost/{token}`
  → стало `https://.../api/v1/webhooks/dobropost/{token}`. **Согласовать с DobroPost.**
* CDEK / Yandex webhook URLs: было `/logistics/webhooks/{provider}` → стало
  `/webhooks/logistics/{provider}`. Обновить в кабинетах провайдеров.

## Backwards compat / deployment

Этот рефактор — breaking change. Деплой требует синхронного обновления fronts. План:

1. Деплой бэка с **обоими** наборами URL (старые → 308 Permanent Redirect на новые) — окно 7 дней.
2. Деплой фронтов на новые URL.
3. Удаление redirect-shim'ов через 7 дней.

Implementation: добавить middleware с `RedirectResponse(status_code=308)` для каждого старого
пути на новый. См. `src/api/middlewares/legacy_redirects.py` (создаётся в этом рефакторе).
