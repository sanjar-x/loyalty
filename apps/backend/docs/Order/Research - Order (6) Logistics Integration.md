---
tags:
  - project/loyality
  - backend
  - order
  - logistics
  - shipment
  - research
type: research
date: 2026-04-30
aliases: [Order Logistics, Shipment Integration, Order Shipment Relationship]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (6) Logistics Integration

> Связь Order ↔ Shipment, carrier-agnostic abstraction, aggregator vs direct integration (Shippo/EasyPost vs СДЭК/Yandex Delivery direct), tracking webhooks vs polling, canonical status mapping, async label generation, returns/RMA как reverse shipment.

## TL;DR — ключевые выводы

1. **Order : Shipment = 1 : N.** Один Order может породить несколько Shipments (multi-warehouse, partial fulfillment, multi-piece). Это первый принцип, на котором строится всё остальное.
2. **Carrier-agnostic abstraction обязательна.** Не делайте `if carrier == "cdek"` в коде — реализуйте Shipment BC с pluggable adapters для каждого carrier'а (ACL pattern из Темы 3).
3. **Aggregator vs Direct integration** — стратегический выбор. Aggregator: Shippo/EasyPost/ShipEngine — fast time-to-market, 100+ carriers. Direct: лучше control, нет middleman fees. В России — обычно direct (СДЭК/Yandex/Почта/Boxberry/ДоброПост), за рубежом — обычно aggregator.
4. **Четыре ключевых российских API** (см. §§5–7, §10) сильно отличаются по архитектуре: СДЭК — асинхронный с UUID-сущностями, OAuth2 + RPS-лимит 200, **9 типов webhook-событий**, идемпотентность по `number`. Yandex Delivery — Bearer-токен, **35 методов в 6 группах**, 2 ветки FSM (door / pickup-point), идемпотентность по `operator_request_id`. Почта России — двойная авторизация (`AccessToken` + `X-User-Authorization`), pipeline через **batch/shipment/checkin**, нет webhook'ов (только polling), идемпотентность по `order-num`. ДоброПост — **JWT с TTL 12h**, всего 5 методов + 2 типа webhook (passport-валидация через DaData + status-update), cross-border CN→RU c таможенным оформлением, валюта в API — **CNY**.
5. **Tracking webhooks > polling.** Каждый serious carrier поддерживает webhooks. Polling — fallback, не main path. **Исключение:** Почта России — без push, только polling.
6. **Canonical status mapping.** Единая внутренняя taxonomy (`Pending → InTransit → OutForDelivery → Delivered → Exception → Returned`), на которую mapping каждого carrier-specific статуса. У Почты статус — это пара `(OperType, OperAttr)` из 200+ значений; у СДЭК — пара `(status_code, code)` из 28 кодов; у Yandex — двухветочная FSM (door / pickup-point) с десятками детализирующих статусов; у ДоброПост — **40 статусов в 4 группах** (1–9 / 270–272 / 500–649 / 590xxx) с семантическим префиксом id.
7. **Label generation** — обычно async: запросил → получил `label_id` → polling/webhook → PDF готов. Не sync-PDF в response checkout'а. У Почты — pipeline через партию: `backlog → shipment → checkin (Ф103 в ОПС) → forms`.
8. **Идемпотентность carrier API часто слабая.** В отличие от PSPs, carriers редко дают `Idempotency-Key` header. Нужно своё дедуплицирование на стороне merchant'а через natural keys (`order_id`, `incomingDeclaration` у ДоброПост, или `external_id`).
9. **Returns** — отдельный shipment, со своим жизненным циклом. RMA → Reverse Shipment с собственным tracking number. Не модифицируйте forward shipment. У СДЭК — `has_reverse_order: true` или `clientReturn`; у Yandex — отдельная RETURN-ветка FSM; у Почты — `PUT /1.0/returns` (легкий возврат `EASY_RETURN`).
10. **Cross-border специфика (ДоброПост)** — first-class в API: обязательные паспорт получателя (4+6 символов), ИНН ФЛ (12 символов), китайский трек (`incomingDeclaration` <16 символов), валидация паспорта по DaData отдельным webhook'ом. Tracking-page customer'а должна показывать **dual track-numbers**: китайский (`incomingDeclaration`) + российский (`dptrackNumber`).
11. **Loyality flow (см. §16)** — это **cross-border dropship** без собственного склада. Пайплайн: Customer заказывает в РФ-каталоге (продукты скопированы из китайских маркетплейсов) → менеджер вручную выкупает в Китае и вставляет китайский трек → backend автоматически создаёт **Shipment #1 (DobroPost, cross-border CN→RU)** → на статусе 648/649 ДоброПост создаётся **Shipment #2 (российский last-mile carrier до ПВЗ покупателя)**. Order : Shipment = **1 : 2 минимум**, два leg'а связаны через `parentShipmentId`.

---

## 1. Shipment как отдельный bounded context

### 1.1 Структура Shipment BC

```text
┌────────────── Shipping BC ────────────────────┐
│                                               │
│   ┌─── Shipment (aggregate root) ────────┐    │
│   │  - id: ShipmentId                    │    │
│   │  - orderId: OrderId (id reference)   │    │
│   │  - carrier: Carrier (VO)             │    │
│   │  - service: ServiceLevel (VO)        │    │
│   │  - state: ShipmentState (FSM)        │    │
│   │  - origin: Address (VO)              │    │
│   │  - destination: Address (VO)         │    │
│   │  - items: List<ShipmentItem>         │    │
│   │  - parcels: List<Parcel>             │    │
│   │  - trackingNumber: String            │    │
│   │  - carrierShipmentId: String         │    │
│   │  - labelUrl: String                  │    │
│   │  - estimatedDelivery: Date           │    │
│   │  - cost: Money                       │    │
│   │                                      │    │
│   │  + book()                            │    │
│   │  + generateLabel()                   │    │
│   │  + cancel()                          │    │
│   │  + recordTrackingEvent(event)        │    │
│   └──────────────────────────────────────┘    │
│                                               │
│   ┌─── TrackingEvent (entity, separate aggr)┐ │
│   │  - id, shipmentId, status, location     │ │
│   │  - occurredAt, raw                      │ │
│   └─────────────────────────────────────────┘ │
│                                               │
│   ┌─── Parcel (entity) ────────────────────┐  │
│   │  - dimensions, weight                  │  │
│   │  - parcelTrackingNumber (часто = ship) │  │
│   └────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

### 1.2 Почему Shipment — отдельный aggregate, не часть Order

- **Lifecycle отличается.** Order может быть в Confirmed неделями, Shipment — короткий цикл на дни.
- **Mutability.** Order после ship — почти immutable. Shipment активно меняется (tracking events).
- **Concurrency.** Tracking events приходят параллельно от webhooks → high write rate. Если Shipment внутри Order aggregate — locking всего Order.
- **External integration.** Shipment плотно coupled с carrier API. Order — нет.
- **Vernon's Cargo Shipping example** (Тема 3): HandlingEvent выделен в отдельный aggregate именно по этой причине.

### 1.3 TrackingEvent — отдельный aggregate (по Эвансу)

> "Since all relationships in an aggregate must be handled synchronously, the HandlingEvent is put in an aggregate of its own to process events quickly and eliminate dead-locking situations."

То же самое для tracking webhooks:

- Тысячи событий в час.
- Никогда не модифицируют Shipment immutably (append-only log).
- Reads (показ tracking page customer'у) могут идти из materialized view.

```text
TrackingEvent (separate aggregate)
  - id, shipmentId (reference)
  - status, location, occurredAt
  - raw_carrier_payload (для debugging)
```

---

## 2. Order ↔ Shipment relationship

### 2.1 Cardinality 1 : N

Один Order — N Shipments. Это ключевая модель.

Источники split:

- Multi-warehouse fulfillment.
- Partial inventory availability.
- Multi-piece (большой/тяжёлый груз).
- Carrier weight/size limits.
- Cross-border + domestic mix.
- Pre-order + in-stock mix (разные lead times).
- Returns — каждый return = отдельный (reverse) shipment.

> "A single order can have more than one tracking ID if the packages are being shipped by different 3PL logistics partners or provided by different sellers, or even arriving on different dates."

### 2.2 Shipment : Parcel = 1 : N

Один Shipment может содержать несколько parcels (multi-piece shipment). Например, ёлка + игрушки в двух коробках, но один waybill.

```text
Order
  └── Shipment #1 (warehouse A)
        ├── Parcel A1 (small box)
        └── Parcel A2 (large box)
  └── Shipment #2 (warehouse B)
        └── Parcel B1
  └── Shipment #3 (return, reverse)
```

Каждый Parcel может иметь собственный tracking, или один tracking на весь Shipment (carrier-зависимо).

### 2.3 Связь по id, не по объекту

```text
Order (Ordering BC)              Shipment (Shipping BC)
  - id: OrderId                    - orderId: OrderId   ◄── reference
                                   - id: ShipmentId
                                   - carrierShipmentId
                                   - trackingNumber
```

**Anti-pattern:** включать Shipment как child entity в Order. Это нарушение Vernon's "small aggregates" rule.

### 2.4 Read model для customer view

Customer хочет видеть один order page со всеми shipments. Это read projection, генерируется из events:

```text
OrderTrackingView (read model):
  orderId: ...
  status: 'partially_shipped'
  shipments: [
    { id, trackingUrl, carrier, status, eta, items },
    { id, trackingUrl, carrier, status, eta, items },
  ]
```

Обновляется через подписку на `ShipmentDispatched`, `TrackingEventRecorded`, `ShipmentDelivered` events.

### 2.5 Tracking number ≠ Order ID

Распространённое заблуждение customer'ов. Order ID — внутренний идентификатор магазина, tracking number — идентификатор carrier'а на его стороне.

> "An order ID is a unique number assigned by the seller, while a tracking ID is provided by the courier. Order ID identifies the order in the seller's system; tracking ID identifies the parcel in the courier's system."

В UI обычно нужно показывать оба:

- Order ID для contact с support.
- Tracking number для tracking pages carrier'а.

---

## 3. Shipment FSM

### 3.1 Канонический Shipment FSM

```text
                ┌──────────────┐
                │  Pending     │ initial — shipment record создан
                └──────┬───────┘
                       │ generate label
                       ▼
                ┌──────────────┐
                │  Booked      │ label generated, awaiting pickup
                └──────┬───────┘
                       │ carrier picked up
                       ▼
                ┌──────────────┐
                │  In Transit  │
                └──────┬───────┘
                       │ at delivery point
                       ▼
                ┌──────────────────┐
                │ Out for Delivery │
                └──────┬───────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐  ┌─────────────┐  ┌──────────┐
   │Delivered│  │Failed Delivery│  │Exception │
   │  (T)    │  │  → retry      │  │          │
   └─────────┘  └───────────────┘  └──────────┘
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │Return to     │
                                   │Sender (T)    │
                                   └──────────────┘
```

### 3.2 Расширенная модель — pickup point flow

Для В России типичен flow с ПВЗ (пункт выдачи заказов):

```text
Pending → Booked → In Transit → Arrived at Pickup Point
                                      │
                              [waiting for customer]
                                      │
                  ┌───────────────────┼────────────────────┐
                  ▼                   ▼                    ▼
            ┌──────────┐        ┌──────────────┐    ┌──────────────┐
            │Delivered │        │Storage Expired│    │Customer      │
            │   (T)    │        │ → return (T)  │    │Refused (T)   │
            └──────────┘        └───────────────┘    └──────────────┘
```

Customer может прийти за заказом 7 дней (по умолчанию у CDEK), потом возврат.

### 3.3 State events as Tracking Events

Каждое state transition порождает TrackingEvent для customer:

- `Pending → Booked` → "Заказ создан"
- `Booked → InTransit` → "Принят в обработку"
- `InTransit → OutForDelivery` → "Передан курьеру"
- `OutForDelivery → Delivered` → "Доставлен"

Customer-facing tracking page показывает поток events, не FSM-state.

---

## 4. Canonical statuses — universal mapping

### 4.1 Зачем нужно

Каждый carrier имеет свою taxonomy:

- **CDEK:** статусы по `status_code` (numeric).
- **Почта России:** textual (приёмка, сортировка, вручение).
- **Yandex:** new, accepted, delivering, complete.
- **DHL:** pre-transit, transit, delivered, failure.

Если разрабатывать UI и downstream logic под каждого carrier'а отдельно — коду конец.

### 4.2 Универсальная taxonomy (DHL-style)

Хороший baseline — DHL Unified API status codes:

| Canonical status | Семантика |
|---|---|
| pre-transit | Shipment registered, не передан carrier'у |
| transit | Carrier принял, в пути |
| delivered | Доставлен (terminal) |
| failure | Не доставлен (terminal) |
| unknown | Нет updates от carrier'а |

### 4.3 Расширенная taxonomy (production-grade)

```text
PRE_TRANSIT
  - DRAFT          (label not generated yet)
  - LABEL_CREATED  (label generated, waiting pickup)
  - PICKED_UP      (carrier confirmed pickup)

IN_TRANSIT
  - SORTING        (at sorting facility)
  - IN_TRANSIT     (moving между hubs)
  - ARRIVED_HUB    (at destination hub)
  - OUT_FOR_DELIVERY (final-mile, courier on the way)
  - AT_PICKUP_POINT (готов к выдаче в ПВЗ)

DELIVERY_OUTCOMES
  - DELIVERED      (terminal-success)
  - DELIVERED_TO_NEIGHBOR
  - SIGNED         (signed-for delivery)

EXCEPTIONS
  - DELIVERY_ATTEMPTED (door not answered)
  - DELIVERY_FAILED    (после N attempts)
  - EXCEPTION          (damage, lost, customs)
  - HELD_AT_CUSTOMS

NEGATIVE_TERMINALS
  - REFUSED            (customer не принял)
  - RETURN_TO_SENDER
  - LOST               (terminal)
  - DAMAGED            (terminal)
```

### 4.4 Mapping table для CDEK

| CDEK status_code | Canonical |
|---|---|
| 1 (Создан) | DRAFT |
| 3 (Принят на склад отправителя) | PICKED_UP |
| 4 (Выдан на отправку) | IN_TRANSIT |
| 5 (Сдан перевозчику) | IN_TRANSIT |
| 6 (Отправлен в город получателя) | IN_TRANSIT |
| 7 (Встречен в городе получателя) | ARRIVED_HUB |
| 12 (Готов к выдаче) | AT_PICKUP_POINT |
| 4-курьер (Передан курьеру) | OUT_FOR_DELIVERY |
| 11 (Вручен) | DELIVERED |
| 17 (Возврат отправителю) | RETURN_TO_SENDER |

### 4.5 Mapping table для Yandex Delivery

| Yandex status | Canonical |
|---|---|
| new | DRAFT |
| estimating | DRAFT |
| ready_for_approval | DRAFT |
| accepted | LABEL_CREATED |
| performer_lookup | LABEL_CREATED |
| pickup_arrived | PICKED_UP |
| delivering | OUT_FOR_DELIVERY |
| delivered_finish | DELIVERED |
| returning | RETURN_TO_SENDER |
| cancelled / failed | FAILURE |

### 4.6 Реализация mapping

```typescript
interface CarrierStatusMapper {
  toCanonical(carrierStatus: string): CanonicalStatus;
}

class CDEKStatusMapper implements CarrierStatusMapper { ... }
class YandexStatusMapper implements CarrierStatusMapper { ... }
class PochtaStatusMapper implements CarrierStatusMapper { ... }
```

Один mapper per carrier, изолированный в ACL слое.

---

## 5. CDEK API v2 — детально

> Источник: локальная копия `local_logistics/cdek_api/openapi.json` (Клиентский протокол интеграции с логистикой). Базовые URL: `https://api.cdek.ru` (рабочая среда), `https://api.edu.cdek.ru` (тестовая). Тестовая учётка общая: `Account=wqGwiQx0gg8mLtiEKsUinjVSICCjtTEP`, `Secure password=RmAmgvSgSl1yirlz9QupbzOJVqhCxcP5`.

### 5.1 Auth — OAuth 2.0

Метод: `POST /v2/oauth/token` с `grant_type=client_credentials`. Возвращает Bearer-токен (живёт 1 час). При работе тестового и боевого хоста используются разные пары `client_id` / `client_secret`.

> «Время жизни токена истекло» (`v2_token_expired`) — типовая ошибка для всех методов протокола; нужно перевыпускать токен по расписанию.

### 5.2 Режим работы — асинхронный с синхронным ответом

Все методы создания/изменения сущностей работают по схеме:

1. Клиент шлёт запрос → СДЭК делает первичную (статичную) валидацию структуры.
2. При успехе — `HTTP 202 ACCEPTED` + `entity.uuid`.
3. Параллельно запускается фоновая бизнес-валидация (маршрут, тариф, доступность, конкретные услуги).
4. Через 200–500 мс (при пиковой нагрузке до 30–60 секунд) `state` запроса переходит в `SUCCESSFUL` или `INVALID`.

Состояния запроса (поле `requests[].state`): `ACCEPTED` → `SUCCESSFUL` / `INVALID`. Статус «ACCEPTED» относится к запросу, **не к сущности**, и не гарантирует её создание. Реальный результат тянется методами «Информация о заказе по UUID/номеру» либо приходит через вебхук.

> Рекомендация СДЭК: ставить таймаут 2–3 секунды между регистрацией заказа и первым `GET /v2/orders/{uuid}`.

### 5.3 Лимиты и хранение

- Гарантированная производительность: **200 RPS** на все методы (синхронные и асинхронные).
- Хранение данных в базе Интеграции — **1 год**.
- Webhook timeout: 15 секунд. Лимит ретраев — **12 попыток за 75 минут**; превышение лимита автоматически отключает все подписки на проблемный URL. Если получен ответ ≠ 200 OK без таймаута — подписка удаляется через 24 часа.
- На клиента — не более **двух активных подписок** на вебхуки.

### 5.4 Полный список методов API v2

#### Авторизация и локации

| Endpoint | Назначение |
|---|---|
| `POST /v2/oauth/token` | Получение Bearer-токена (OAuth 2 client_credentials) |
| `GET /v2/location/suggest/cities` | Подбор локации по названию города (auto-complete) |
| `GET /v2/location/regions` | Список регионов |
| `GET /v2/location/cities` | Список населённых пунктов |
| `GET /v2/location/postalcodes` | Поиск по почтовому индексу |
| `GET /v2/location/coordinates` | Поиск по координатам |
| `GET /v2/deliverypoints` | Список офисов / ПВЗ / постаматов с фильтрами |

#### Калькулятор и проверки

| Endpoint | Назначение |
|---|---|
| `POST /v2/calculator/tariff` | Расчёт по конкретному коду тарифа |
| `POST /v2/calculator/tarifflist` | Расчёт по всем доступным тарифам |
| `POST /v2/calculator/alltariffs` | Список всех доступных тарифов договора |
| `POST /v2/calculator/tariffAndService` | Расчёт тарифа вместе с услугами |
| `POST /v2/check` | Проверка доступности доставки |
| `POST /v2/international/package/restrictions` | Ограничения международных заказов |
| `POST /v2/reverse/availability` | Проверка доступности реверса до создания прямого заказа |

#### Заказы

| Endpoint | Назначение |
|---|---|
| `POST /v2/orders` | Регистрация заказа (получаем `entity.uuid`) |
| `GET /v2/orders/{uuid}` | Информация о заказе по UUID |
| `PATCH /v2/orders/{uuid}` | Изменение заказа (только в статусах `CREATED`/`ACCEPTED`) |
| `DELETE /v2/orders/{uuid}` | Удаление заказа (только в статусе `Создан`) |
| `POST /v2/orders/{uuid}/refusal` | Регистрация отказа |
| `POST /v2/orders/{uuid}/clientReturn` | Клиентский возврат |
| `POST /v2/orders/{orderUuid}/intakes` | Создать заявку на курьера от уже созданного заказа |

#### Договорённости о доставке

| Endpoint | Назначение |
|---|---|
| `POST /v2/delivery` | Регистрация договорённости (door / warehouse / postamat) |
| `GET /v2/delivery/{uuid}` | Информация о договорённости |
| `POST /v2/delivery/intervals` | Получение доступных интервалов до создания заказа |
| `POST /v2/delivery/estimatedIntervals` | Прогноз интервалов |

#### Заявки на курьера

| Endpoint | Назначение |
|---|---|
| `POST /v2/intakes` | Регистрация заявки на вызов курьера |
| `GET /v2/intakes/{uuid}` | Информация о заявке |
| `DELETE /v2/intakes/{uuid}` | Удаление заявки |
| `GET /v2/intakes/availableDays` | Доступные даты вызова курьера для НП |

#### Печатные формы

| Endpoint | Назначение |
|---|---|
| `POST /v2/print/orders` | Запрос на формирование квитанции (форма Ф7п, async) |
| `GET /v2/print/orders/{uuid}` | Статус формирования квитанции |
| `GET /v2/print/orders/{uuid}.pdf` | Скачать PDF квитанции |
| `POST /v2/print/barcodes` | Запрос ШК места к заказу |
| `GET /v2/print/barcodes/{uuid}` | Статус ШК |
| `GET /v2/print/barcodes/{uuid}.pdf` | Скачать PDF ШК |

Статусы печатной формы: `ACCEPTED` → `PROCESSING` → `READY` (или `INVALID` / `REMOVED`).

#### Прочее

| Endpoint | Назначение |
|---|---|
| `POST /v2/prealert` | Преалерт (групповая передача заказов) |
| `GET /v2/prealert/{uuid}` | Информация о преалерте |
| `GET /v2/registries` | Реестры наложенных платежей |
| `POST /v2/passport` | Информация о паспортных данных |
| `POST /v2/photoDocument` | Фото документов |
| `POST /v2/webhooks` | Подписка на вебхуки |
| `GET /v2/webhooks/{uuid}` / `DELETE /v2/webhooks/{uuid}` | Управление подписками |

### 5.5 Lifecycle Order (СДЭК)

1. **Расчёт стоимости:** `POST /v2/calculator/tariff` с весом, габаритами, кодом тарифа, локациями отправителя/получателя.
2. **Регистрация заказа:** `POST /v2/orders` с обязательными полями `tariff_code`, `recipient`, `from_location`/`shipment_point` и `to_location`/`delivery_point`, `packages[]`. Ответ: `requests[0].state = ACCEPTED` + `entity.uuid`.
3. **Получение `cdek_number`:** через 0.2–0.5 с (или вебхук `ORDER_STATUS`) — `GET /v2/orders/{uuid}`. Это и есть tracking number.
4. **Печатные формы:** `POST /v2/print/orders` с массивом UUID → ждём webhook `PRINT_FORM` или периодически читаем `/v2/print/orders/{uuid}` → когда `READY`, скачиваем PDF.
5. **Договорённость о доставке** (опционально): `POST /v2/delivery` с типом `DOOR/WAREHOUSE/POSTAMAT` и временным интервалом.
6. **Tracking** идёт через вебхуки `ORDER_STATUS` или периодический `GET /v2/orders/{uuid}` (`statuses[]`).
7. Финальные коды (приложение 1): `4 DELIVERED` (вручен), `5 NOT_DELIVERED` (не вручен), `2 REMOVED` (удалён).

### 5.6 Вебхуки — типы событий

| Тип события | Когда приходит |
|---|---|
| `ORDER_STATUS` | Изменение статуса заказа (включая возвратные при `is_return=true`) |
| `PRINT_FORM` | Готовность квитанции (`type=WAYBILL`) или ШК (`type=BARCODE`) — приходит ссылка на PDF |
| `PREALERT_CLOSED` | Преалерт закрыт |
| `ACCOMPANYING_WAYBILL` | Информация о транспорте для СНТ (рейс, борт, ТС) |
| `OFFICE_AVAILABILITY` | Изменение доступности офиса (`AVAILABLE_OFFICE` / `UNAVAILABLE_OFFICE`) |
| `ORDER_MODIFIED` | Изменение заказа: `PLANED_DELIVERY_DATE_CHANGED` / `DELIVERY_SUM_CHANGED` / `DELIVERY_MODE_CHANGED` |
| `DELIV_AGREEMENT` | Новая договорённость о доставке |
| `DELIV_PROBLEM` | Проблема доставки (см. приложение 3 — коды 1, 9, 11, 13, 17, 19, 35–57) |
| `COURIER_INFO` | Назначен курьер (`task_type=DELIVERY` для заказа, `DEMAND` для заявки) |

Пример `ORDER_STATUS`:

```json
{
  "type": "ORDER_STATUS",
  "date_time": "2026-04-29T07:44:45+0000",
  "uuid": "72753031-1820-4f99-9240-aab139f05ca5",
  "attributes": {
    "is_return": false,
    "is_reverse": false,
    "is_client_return": false,
    "cdek_number": "1100285492",
    "number": "17011574744791",
    "code": "RECEIVED_AT_SHIPMENT_WAREHOUSE",
    "status_code": "3",
    "status_date_time": "2026-04-29T07:44:45+0000",
    "city_name": "Новосибирск",
    "city_code": "270",
    "deleted": false
  }
}
```

### 5.7 Канонические статусы заказа (приложение 1)

Полная таблица из openapi-спеки. Поле `code` (string) — основное, `status_code` (numeric) — устаревшее, оставлено для обратной совместимости.

| status_code | code | Статус | Терминальный |
|---|---|---|---|
| 0 | `ACCEPTED` | Принят, ждёт валидации | – |
| 1 | `CREATED` | Создан | – |
| 2 | `REMOVED` | Удалён | ✔ |
| 3 | `RECEIVED_AT_SHIPMENT_WAREHOUSE` | Принят на склад отправителя | – |
| 4 | `DELIVERED` | Вручен | ✔ |
| 5 | `NOT_DELIVERED` | Не вручен (отказ покупателя, возврат) | ✔ |
| 6 | `READY_FOR_SHIPMENT_IN_SENDER_CITY` | Готов к отправке в городе-отправителе | – |
| 7 | `TAKEN_BY_TRANSPORTER_FROM_SENDER_CITY` | Сдан перевозчику | – |
| 8 | `SENT_TO_RECIPIENT_CITY` | Отправлен в город-получатель | – |
| 9 | `ACCEPTED_IN_RECIPIENT_CITY` | Встречен в городе-получателе | – |
| 10 | `ACCEPTED_AT_RECIPIENT_CITY_WAREHOUSE` | Принят на склад доставки | – |
| 11 | `TAKEN_BY_COURIER` | Выдан на доставку | – |
| 12 | `ACCEPTED_AT_PICK_UP_POINT` | Принят на склад до востребования (ПВЗ) | – |
| 13 | `ACCEPTED_AT_TRANSIT_WAREHOUSE` | Принят на склад транзита | – |
| 16 | `RETURNED_TO_SENDER_CITY_WAREHOUSE` | Возвращён на склад отправителя | – |
| 17 | `RETURNED_TO_TRANSIT_WAREHOUSE` | Возвращён на склад транзита | – |
| 18 | `RETURNED_TO_RECIPIENT_CITY_WAREHOUSE` | Возвращён на склад доставки | – |
| 1000 | `IN_CUSTOMS_INTERNATIONAL` / `IN_CUSTOMS_LOCAL` / `CUSTOMS_COMPLETE` | Этапы таможенного оформления | – |
| 1000 | `POSTOMAT_POSTED` / `POSTOMAT_RECEIVED` / `POSTOMAT_SEIZED` | Заложен / выдан / изъят из постамата | – |
| 404 | `INVALID` | Некорректный заказ | ✔ |

> Терминальный набор для прямого заказа: `DELIVERED`, `NOT_DELIVERED`, `REMOVED`, `INVALID`. Внутри `NOT_DELIVERED` приходит `status_reason_code` (приложение 2) с детальной причиной (1–34): неверный адрес, отказ от получения, истёк срок хранения, утерян и т. д.

### 5.8 Причины задержки доставки (`delay_reasons`)

С 28 ноября 2025 в ответах методов получения информации о заказе возвращается массив `delay_reasons` с описанием причин задержек. Это ключ для построения admin-дашборда (тема 8).

### 5.9 Реверс / возвраты

- **Прямой реверс:** новый признак `has_reverse_order: true` при регистрации прямого заказа (старый способ через доп. услугу `REVERSE` остаётся для обратной совместимости, но заявлен deprecated).
- **Клиентский возврат:** `POST /v2/orders/{uuid}/clientReturn`.
- **Webhook отделяет прямую/обратную ветку:** `attributes.is_return` (`true` — обратное отправление), `is_reverse`, `is_client_return`. У возвратного отправления свой `cdek_number`. Через `related_entities` приходит ссылка на исходный прямой заказ (`type=direct_order` или `client_direct_order`).
- **Ограничения реверса:** максимальный вес — 30 кг; запрещено менять город/адрес отправителя если прямой заказ в конечном статусе.

### 5.10 Тарифы и режимы доставки

Тарифы передаются в `tariff_code` при регистрации заказа. Группы тарифов (приложение 4):

- **«Посылка»** (для ИМ, до 50 кг): 136 С-С, 137 С-Д, 138 Д-С, 139 Д-Д, 366 Д-Постамат, 368 С-Постамат.
- **«Экономичная посылка»** (наземная, до 50 кг): 231 Д-Д, 232 Д-С, 233 С-Д, 234 С-С, 378 С-Постамат.
- **«Экспресс»**: 480 Д-Д, 481 Д-С, 482 С-Д, 483 С-С + варианты с постаматом 485, 486, 605, 606, 607.
- **«Магистральный экспресс»** (LTL): 62, 121, 122, 123.
- **«Сборный груз»** (от 70 кг): 748–751 (требует `additional_order_types=[2]`).
- **«Супер-экспресс до Х»** (срочная): 3, 57–61, 676–719, 722, 777–806.
- **«E-com Express» / «E-com Standard»** (международные для ЮЛ).
- **Доп. тариф** «Доставка день в день» (2360), «Один офис ИМ» (2536), «Фулфилмент выдача» (358).

Коды режимов доставки (приложение 15): `1` Д-Д, `2` Д-С, `3` С-Д, `4` С-С, `6` Д-П, `7` С-П, `8` П-Д, `9` П-С, `10` П-П.

### 5.11 Дополнительные услуги (выборка из приложения 6)

| Код услуги | Назначение |
|---|---|
| `INSURANCE` | Страхование (для ИМ — авто на основе объявленной стоимости) |
| `TAKE_SENDER` / `DELIV_RECEIVER` | Забор у отправителя / доставка получателю при тарифе со склада |
| `TRYING_ON` | Примерка (только ИМ, не для постаматов; несовместима с `BAN_ATTACHMENT_INSPECTION`) |
| `PART_DELIV` | Частичная доставка (только ИМ, не для постаматов) |
| `BAN_ATTACHMENT_INSPECTION` | Запрет осмотра вложения |
| `DANGER_CARGO` | Опасный груз (×1.5 к стоимости) |
| `SMS` / `NOTIFY_ORDER_CREATED` / `NOTIFY_ORDER_DELIVERY` | СМС-уведомления |
| `THERMAL_MODE` | Тепловой режим (ограниченные направления, только С-С) |
| `CARTON_BOX_*`, `XL_BOX_INNER_CRATE`, `BUBBLE_WRAP`, `WASTE_PAPER` | Упаковка |
| `GET_UP_FLOOR_BY_HAND` / `GET_UP_FLOOR_BY_ELEVATOR` | Подъём на этаж (взаимоисключающие) |
| `ADULT_GOODS` | 18+ (по признаку договора) |
| `CUSTOMS_CLEARANCE`, `EXP_REGIST*`, `CUSTOM_CLEARENCE_FOR_*` | Таможенное оформление (B2B 200/200+/1000+, last-mile) |
| `PHOTO_OF_DOCUMENTS` | Фото документов с идентификацией получателя |

### 5.12 Идемпотентность и типичные ошибки

В СДЭК нет отдельного `Idempotency-Key`. Ключ идемпотентности — поле `number` (номер заказа в ИС клиента) при регистрации. Повторная регистрация с тем же `number` отдаёт ошибку `error_validate_im_dep_number_has_already_had_integration` («Введённый номер отправления ИМ не уникальный»).

Часто встречающиеся ошибки (полный список в openapi-спеке):

- `v2_internal_error` — системная ошибка, ретрай.
- `v2_similar_request_still_processed` — предыдущий запрос ещё обрабатывается.
- `v2_update_forbidden` — заказ уже принят, изменения запрещены (только в `CREATED`/`ACCEPTED`).
- `v2_token_expired` / `v2_authorization_incorrect` — обновить токен.
- `v2_sender_location_not_recognized` / `v2_recipient_location_not_recognized` — не определена локация (передавать пару «индекс + НП» или fias_guid).
- `v2_shipment_address_multivalued` / `v2_delivery_address_multivalued` — нельзя одновременно ПВЗ и адрес.
- `error_validate_postamat_package_count` / `error_validate_postamat_package_weight` — для постамата только 1 место и до 15 кг.

### 5.13 Проблемы доставки (приложение 3)

Через `DELIV_PROBLEM` приходят коды (1, 9, 11, 13, 17, 19, 35–57): «Телефон неверный», «Груз не готов», «Отказ от оплаты», «Самозабор», «Постамат переполнен», «Адрес не существует», «Опасный груз», «Изменение интервала по согласованию» и др. Используется для admin-дашборда «Cancellation drilldown» (тема 8).

---

## 6. Yandex Delivery (другой день) — детально

> Источник: локальная копия `local_logistics/yandex_delivery_api/markdown/`. Это **B2B Platform API «Доставка в другой день»** (NDD-сегмент с собственным складом или самопривозом и доставкой до двери / ПВЗ / постамата). Для городской «такси-style» Express существует отдельный `b2b/cargo/integration/v2/claims/*` API — он не покрывается этой документацией.

### 6.1 Окружения и Auth

| Параметр | Тестовое | Production |
|---|---|---|
| Host | `https://b2b.taxi.tst.yandex.net` | `https://b2b-authproxy.taxi.yandex.net` |
| Bearer-token | общий: `y2_AgAAAAD04omrAAAPeAAAAAACRpC94Qk6Z5rUTgOcTgYFECJllXYKFx8` | получить в [личном кабинете](https://dostavka.yandex.ru/account) → раздел **Интеграция** → **Получить токен** |
| `platform_station_id` | склад: `fbed3aa1-2cc6-4370-ab4d-59c5cc9bb924` | выдаётся коммерческим менеджером |

Токен бессрочный; **инвалидируется при смене пароля** в личном кабинете. Передача:

```http
Authorization: Bearer <OAuth-токен>
```

> Тестовая среда поддерживает только адреса по г. Москва (МСК) — для курьера, ПВЗ и почтовых отделений.

Рекомендованные тестовые ПВЗ:

| Направление | Адрес | platform_station_id |
|---|---|---|
| Откуда | Москва, Ленинградский проспект 27 | `e1139f6d-e34f-47a9-a55f-31f032a861a6` |
| Куда | Москва, Ленинградский проспект 37 к9 | `01946f4f013c7337874ec2fb848a58a4` |

### 6.2 Полный список методов API (35 методов в 6 группах)

#### Группа 1. Подготовка заявки (3 метода)

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/api/b2b/platform/pricing-calculator` | Расчёт стоимости доставки |
| GET | `/api/b2b/platform/offers/info` | Получение расписания вывозов в регионы |
| POST | `/api/b2b/platform/offers/info` | То же, через POST |

#### Группа 2. Точки самопривоза и ПВЗ (2 метода)

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/api/b2b/platform/location/detect` | `geo_id` по адресу или его фрагменту |
| POST | `/api/b2b/platform/pickup-points/list` | Список ПВЗ / постаматов / точек самопривоза |

#### Группа 3. Основные запросы — заявки и заказы (14 методов)

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/api/b2b/platform/offers/create` | Получение вариантов доставки (офферов) |
| POST | `/api/b2b/platform/offers/confirm` | Бронирование выбранного оффера |
| POST | `/api/b2b/platform/request/create` | Создание заказа на ближайшее время (упрощённая альтернатива двухшаговому flow) |
| GET | `/api/b2b/platform/request/info` | Информация о заявке + текущий статус |
| POST | `/api/b2b/platform/requests/info` | Список заявок за интервал |
| GET | `/api/b2b/platform/request/actual_info` | Актуальная дата и время доставки |
| POST | `/api/b2b/platform/request/edit` | Заявка на редактирование заказа |
| POST | `/api/b2b/platform/request/edit/status` | Статус запроса на редактирование |
| POST | `/api/b2b/platform/request/datetime_options` | Интервалы доставки для нового места получения |
| POST | `/api/b2b/platform/request/redelivery_options` | Интервалы доставки при переносе |
| GET | `/api/b2b/platform/request/history` | История статусов заказа |
| POST | `/api/b2b/platform/request/cancel` | Отмена заявки |
| POST | `/api/b2b/platform/request/places/edit` | Редактирование грузомест |
| POST | `/api/b2b/platform/request/items-instances/edit` | Редактирование товаров заказа |

#### Группа 4. Ярлыки и акты приёма-передачи (2 метода)

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/api/b2b/platform/request/generate-labels` | Генерация ярлыков для указанных заказов |
| POST | `/api/b2b/platform/request/get-handover-act` | Получение актов приёма-передачи отгрузки |

#### Группа 5. Управление мерчантами (6 методов)

| Метод | Endpoint | Назначение |
|---|---|---|
| POST / GET | `/api/b2b/platform/merchant/register` | Регистрация мерчанта / проверка статуса |
| GET | `/api/b2b/platform/merchant/info` | Информация о мерчанте |
| POST | `/api/b2b/platform/merchant/search` | Поиск мерчантов |
| POST | `/api/b2b/platform/merchant/update` | Обновление |
| POST | `/api/b2b/platform/merchant/delete` | Удаление |

#### Группа 6. Управление складами и отгрузками (8 методов)

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/api/b2b/platform/warehouses/create` / `list` / `retrieve` | Управление складами клиента |
| POST | `/api/b2b/platform/pickups/pickup-options` | Опции отгрузки для склада |
| POST | `/api/b2b/platform/pickups/create` / `cancel` / `retrieve` | Управление отгрузкой |
| POST | `/api/b2b/platform/pickups/scheduled/list` | Список запланированных отгрузок |

### 6.3 Два flow создания заказа

#### 6.3.1 Двухшаговый flow (с явным выбором оффера)

```text
POST /pricing-calculator      → ориентировочная стоимость
POST /offers/create           → список офферов (доступные варианты)
POST /offers/confirm          → бронирование выбранного оффера → request_id
```

#### 6.3.2 Упрощённый flow

```text
POST /request/create          → создаёт заказ на ближайшее доступное время → request_id
```

Тело запроса идентично `offers/create` (10 параметров: `info`, `source`, `destination`, `items`, `places`, `billing_info`, `recipient_info`, `last_mile_policy`, `particular_items_refuse`, `forbid_unboxing`).

Идемпотентность: натуральный ключ — `info.operator_request_id` (внешний ID мерчанта). Дубликат → 400 `There already was request with such code within this employer, request_id`.

Минимальный пример:

```json
{
  "info": {
    "operator_request_id": "lKF4565ml",
    "merchant_id": "290587090cfc4943856851c8c3b2eebf",
    "comment": "Комментарий"
  },
  "source": {
    "platform_station": { "platform_id": "e1139f6d-e34f-47a9-a55f-31f032a861a6" },
    "interval_utc": { "from": "2026-04-30T15:00:00.000000Z", "to": "2026-04-30T17:00:00.000000Z" }
  },
  "destination": {
    "type": "platform_station",
    "platform_station": null,
    "custom_location": {
      "latitude": 55.6, "longitude": 37.6,
      "details": { "geoId": 213, "country": "Россия", "locality": "Москва", "street": "Пролетарский проспект", "house": "19", "postal_code": "123182" }
    }
  },
  "items": [{ "count": 1, "name": "Духи", "article": "YS2-2022", "billing_details": { "inn": "9715386101", "nds": 22, "unit_price": 100, "assessed_unit_price": 100 }, "physical_dims": { "dx": 10, "dy": 15, "dz": 10 }, "place_barcode": "Kia-01", "cargo_types": ["80"], "fitting": false }],
  "places": [{ "physical_dims": { "weight_gross": 100, "dx": 10, "dy": 10, "dz": 10 }, "barcode": "Kia-01" }],
  "billing_info": { "payment_method": "already_paid", "delivery_cost": 0 },
  "recipient_info": { "first_name": "Василий", "last_name": "Пупкин", "phone": "+79529999999", "email": "pupkin@mail.ru" },
  "last_mile_policy": "time_interval",
  "particular_items_refuse": false,
  "forbid_unboxing": false
}
```

Ответ:

```json
{ "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp" }
```

### 6.4 Статусная модель — две ветки

Жирным помечены **основные** статусы логистической цепочки; остальные — детализация. У Яндекса для NDD-сегмента две независимые ветки FSM в зависимости от способа доставки.

#### 6.4.1 Доставка «до двери»

**Happy path (основные):**

```text
DRAFT → CREATED → SORTING_CENTER_AT_START → DELIVERY_DELIVERED
```

Между ними — детализирующие статусы (десятки): `VALIDATING`, `VALIDATING_ERROR`, `DELIVERY_PROCESSING_STARTED`, `DELIVERY_TRACK_RECIEVED`, `SORTING_CENTER_PROCESSING_STARTED`, `SORTING_CENTER_TRACK_RECEIVED`, `SORTING_CENTER_TRACK_LOADED`, `DELIVERY_LOADED`, `SORTING_CENTER_LOADED`, `SORTING_CENTER_PREPARED`, `SORTING_CENTER_TRANSMITTED`, `DELIVERY_AT_START`, `DELIVERY_AT_START_SORT`, `DELIVERY_TRANSPORTATION_RECIPIENT`, `DELIVERY_TRANSMITTED_TO_RECIPIENT`, `DELIVERY_ATTEMPT_FAILED`.

**Отмена:** `CANCELLED` (одна из причин — `CANCELLED_BY_RECIPIENT`, `CANCELLED_USER`, `CANCELLED_IN_PLATFORM`, `SORTING_CENTER_CANCELLED`).

**Возврат (основные):**

```text
RETURN_PREPARING → RETURN_TRANSPORTATION_STARTED → RETURN_ARRIVED_DELIVERY → RETURN_TRANSMITTED_FULFILMENT → RETURN_READY_FOR_PICKUP → RETURN_RETURNED
```

**Перенос доставки:** `DELIVERY_UPDATED_BY_SHOP` / `DELIVERY_UPDATED_BY_RECIPIENT` / `DELIVERY_UPDATED_BY_DELIVERY`.

#### 6.4.2 Доставка до ПВЗ или постамата

**Happy path (основные):**

```text
DRAFT → CREATED → SORTING_CENTER_AT_START → PARTICULARLY_DELIVERED → DELIVERY_DELIVERED
```

Детализация добавляет: `DELIVERY_TRANSPORTATION`, `DELIVERY_ARRIVED_PICKUP_POINT`, `DELIVERY_TRANSMITTED_TO_RECIPIENT`, `DELIVERY_STORAGE_PERIOD_EXPIRED`, `DELIVERY_STORAGE_PERIOD_EXTENDED`, `CONFIRMATION_CODE_RECEIVED`, `FINISHED`.

**Возврат (основные):** `RETURN_TRANSPORTATION_STARTED → RETURN_ARRIVED_DELIVERY → RETURN_READY_FOR_PICKUP → RETURN_RETURNED`.

> Полный статус-граф (с детализацией) должен идти в маппер ACL отдельным таблицей — наглядных переходов в API нет, событий приходит много, важно фильтровать «основные» от «детализации».

### 6.5 Маппинг Yandex → каноническая taxonomy (DHL-style)

| Yandex | Canonical |
|---|---|
| `DRAFT`, `VALIDATING`, `VALIDATING_ERROR` | `DRAFT` |
| `CREATED`, `DELIVERY_TRACK_RECIEVED`, `DELIVERY_PROCESSING_STARTED` | `LABEL_CREATED` |
| `SORTING_CENTER_*`, `DELIVERY_LOADED` | `IN_TRANSIT` (хаб) |
| `SORTING_CENTER_AT_START`, `SORTING_CENTER_PREPARED`, `SORTING_CENTER_TRANSMITTED` | `ARRIVED_HUB` / `IN_TRANSIT` |
| `DELIVERY_AT_START`, `DELIVERY_TRANSPORTATION_RECIPIENT`, `DELIVERY_TRANSPORTATION` | `OUT_FOR_DELIVERY` |
| `DELIVERY_ARRIVED_PICKUP_POINT` | `AT_PICKUP_POINT` |
| `DELIVERY_TRANSMITTED_TO_RECIPIENT`, `DELIVERY_DELIVERED`, `FINISHED` | `DELIVERED` |
| `PARTICULARLY_DELIVERED` | `DELIVERED` (частично — нужна доп. логика) |
| `DELIVERY_ATTEMPT_FAILED` | `DELIVERY_ATTEMPTED` |
| `DELIVERY_STORAGE_PERIOD_EXPIRED` | `RETURN_TO_SENDER` (по истечении срока) |
| `CANCELLED` (любая причина) | `FAILURE` |
| `RETURN_*` (основные) | `RETURN_*` (отдельная ветка reverse shipment) |

### 6.6 Справочник ошибок (выборка)

| Код | Текст | Категория |
|---|---|---|
| 400 | `Cannot parse destination info` | Адрес не распознан — нужен формат «Город, улица, дом» |
| 400 | `There already was request with such code within this employer, request_id` | Дубликат `operator_request_id` |
| 400 | `Cant get station id for point` | Не определена станция (некорректный `platform_station_id`) |
| 400 | `Сant calc routes because destination station is disabled` | Точка Б деактивирована |
| 400 | `Pickup point doesn't accept payment on delivery` / `Pickup point doesn't accept prepaid orders` | Способ оплаты не поддерживается на ПВЗ |
| 400 | `Particular items refuse is not allowed for courier delivery` / `for pickup point` | Частичный выкуп недоступен на этом канале |
| 400 | `Fitting of items is not available for courier delivery` / `for pickup point` | Примерка недоступна |
| 400 | `Payment on delivery option is not available for courier delivery` | Курьерская не поддерживает оплату при получении |
| 401 | `Access denied` | Проблемы с авторизацией — проверить токен |
| 404 | `No delivery options` | Нет доступных опций доставки (нет графика отгрузок, не та оплата на ПВЗ, превышены габариты, маршрут недоступен) |
| 404 | `No dropoff available` | Невозможно отгрузить (нет графика, нет средств на балансе) |
| 404 | `Dimensions should not exceed limit` | Превышены габариты, `available_for_dropoff: false` |

### 6.7 Webhooks и опрос статусов

Yandex поддерживает callback URL, настраиваемый в личном кабинете (push-уведомления о смене статуса). В качестве fallback используется поллинг:

- `GET /request/info?request_id=...` — текущий снэпшот статуса.
- `GET /request/history?request_id=...` — append-only журнал статусов.

Для batch-процесса — `POST /requests/info` с временным интервалом.

### 6.8 Терминология

| Термин | Определение |
|---|---|
| **Оффер** | Вариант доставки или маршрут, подобранный по параметрам заказа |
| **Заказ** | Оформленное задание на доставку с отправителем, услугами, получателем, отправлением |
| **Ярлык** | Сопроводительный документ-наклейка с информацией об отправителе/получателе и штрих-кодом |
| **Акт приёма-передачи** | Документ, подтверждающий передачу товаров при заборе |
| **ПВЗ** | Пункт выдачи заказов |

---

## 7. Почта России (Otpravka API) — детально

> Источник: локальная копия `local_logistics/russian_post_api/markdown/`. Это **API онлайн-сервиса «Отправка»** (`otpravka.pochta.ru`). REST + JSON, обмен по HTTPS.

### 7.1 Двойная авторизация

Каждый запрос требует **двух** заголовков:

```http
Authorization: AccessToken {token}
X-User-Authorization: Basic {base64(login:password)}
Content-Type: application/json;charset=UTF-8
```

| Параметр | Что это |
|---|---|
| **AccessToken** (Authorization) | Токен приложения, выдаётся после активации API на email; обновляется через ЛК → «Обновить токен» |
| **X-User-Authorization** | `Basic <base64(login:password)>`, где `login:password` — учётка `passport.pochta.ru` |

### 7.2 Pipeline создания отправлений (5 этапов)

```text
[1] Подготовка данных (опц.)
       │  - Нормализация адреса:    POST /1.0/clean/address
       │  - Нормализация телефона:  POST /1.0/clean/phone
       │  - Нормализация ФИО:       POST /1.0/clean/physical
       ▼
[2] Создание отправления → получаем ШПИ + result-id
       │  - PUT  /1.0/user/backlog       (v1)
       │  - PUT  /2.0/user/backlog       (v2 — авто-расчёт платы за пересылку)
       ▼
[3] Создание партии (Shipment / Batch)
       │  - POST /1.0/user/shipment      (создать партию из N заказов)
       │  - POST /1.0/batch/{name}/shipment    (добавить заказы в партию)
       ▼
[4] Отправка электронной Ф103 в ОПС → подтверждение партии
       │  - POST /1.0/batch/{name}/checkin
       ▼
[5] Получение документов и ярлыков
       - GET /1.0/forms/{id}/forms              (ярлык конкретного отправления)
       - POST /1.0/forms/backlog                (формы для бэклога)
       - POST /1.0/forms/{batchName}/...        (документы партии: F103, F112, F22, F7, опись)
```

### 7.3 Полный список endpoint'ов (otpravka.pochta.ru)

#### Создание и редактирование отправлений

| Endpoint | Назначение |
|---|---|
| `PUT /1.0/user/backlog` | Создать заказ (v1) — без авто-расчёта тарифа |
| `PUT /2.0/user/backlog` | Создать заказ (v2) — автоматический расчёт платы за пересылку |
| `PUT /1.0/backlog/{id}` | Редактировать заказ |
| `DELETE /1.0/backlog` | Удалить заказы из бэклога |
| `POST /1.0/user/backlog` | Поиск заказов |
| `GET /1.0/backlog/{id}` | Поиск заказа по идентификатору |
| `GET /1.0/backlog/group/{name}` | Заказы по имени группы |
| `POST /1.0/shipment` | Перенос отправления в бэклог |

#### Партии (Batches / Shipments)

| Endpoint | Назначение |
|---|---|
| `POST /1.0/user/shipment` | Создание партии из N заказов (автоматически присваивает ШПИ) |
| `PUT /1.0/batch/{name}/shipment` | Добавить заказы в партию |
| `POST /1.0/batch/{name}/shipment` | Перенести заказы в партию |
| `DELETE /1.0/shipment` | Удалить отправление из партии |
| `GET /1.0/batch/{name}` | Поиск партии по имени |
| `GET /1.0/shipment` | Поиск всех партий |
| `GET /1.0/shipment/search` | Партии с фильтрацией |
| `GET /1.0/batch/{name}/shipment` | Информация о заказах в партии |
| `GET /1.0/shipment/barcode/{barcode}` | Найти заказы по штрих-коду |
| `POST /1.0/batch/{name}/sending-date` | Установить дату сдачи в ОПС |
| `POST /1.0/batch/{name}/checkin` | Подготовка и отправка электронной формы Ф103 в ОПС |

Параметры в `POST /1.0/user/shipment`:

- `sending-date` — дата сдачи в ОПС (`yyyy-MM-dd`).
- `timezone-offset` — смещение от UTC в секундах.
- `use-online-balance` — использовать онлайн-баланс.

#### Документы (PDF-формы)

| Endpoint | Что генерируется |
|---|---|
| `GET /1.0/forms/{id}/forms` | Ярлыки заказа (Ф7п для посылок, Е-1 для EMS, конверт для писем) + опц. Ф112ЭК (наложенный платёж), Ф22 (посылка-онлайн), уведомление, опись вложения |
| `POST /1.0/forms/backlog` | Формы для всего бэклога |
| `GET /1.0/forms/{batch}/f103pdf` | Форма Ф103 (партионный список) |
| `GET /1.0/forms/{batch}/f112` | Ф112ЭК (наложенный платёж) |
| `GET /1.0/forms/{batch}/comp-checking-form` | Чек-лист «Проверка комплектности» |
| `GET /1.0/forms/{batch}/f7-f22` | Объединённые формы Ф7п + Ф22 |
| `GET /1.0/forms/easy-return/{id}` | Лёгкий возврат (PDF) |
| `GET /1.0/forms/{batch}/all-docs` | Архив со всеми документами партии |

Тип печати (param `print-type`): `PAPER` (А5 14.8×21 см лазер/струйка) / `THERMO` (А6 10×15 см термопечать).

#### Архив и долгосрочное хранение

| Endpoint | Назначение |
|---|---|
| `POST /1.0/batch/archive/{batch}` | Перенести партию в архив |
| `POST /1.0/batch/revert-archive/{batch}` | Вернуть партию из архива |
| `GET /1.0/batch/archive/search` | Поиск архивных партий |
| `GET /1.0/long-term-archive/shipments` | Поиск отправлений из долгосрочного архива |

#### Сессии (для multi-step transactions)

| Endpoint | Назначение |
|---|---|
| `POST /1.0/user-session` | Создать пользовательскую сессию (`session-type=CREATE_BATCHES` / `ADD_BACKLOGS_TO_BATCH`) |
| `GET /1.0/user-session/{uuid}` / `GET /1.0/user-session` | Получить сессию(и) |
| `POST /1.0/user-session/{uuid}/backlog` / `DELETE` | Управление backlog'ами в сессии |
| `POST /1.0/user-session/{uuid}/close` | Закрыть сессию |
| `DELETE /1.0/user-session/{uuid}` | Удалить сессию |
| `GET /1.0/user-session/{uuid}/batches` | Партии сессии |
| `GET /1.0/user-session/{uuid}/errors` | Ошибки сессии |

#### Возвраты

| Endpoint | Назначение |
|---|---|
| `PUT /1.0/returns` | Создать возвратное отправление (ЛВ) для существующего ШПИ |
| `PUT /1.0/returns/return-without-direct` | Создать возврат без привязки к прямому |
| `PUT /1.0/returns/separate` | Обновить отдельный возврат |
| `DELETE /1.0/returns/delete-separate-return` | Удалить отдельный возврат |

Тело: `{ "direct-barcode": "string", "mail-type": "POSTAL_PARCEL" }`. Ответ: `{ "return-barcode": "string" }`.

#### Расчёты, справочники, ОПС

| Endpoint | Назначение |
|---|---|
| `POST /1.0/tariff` | Расчёт стоимости пересылки (возвращает в копейках) |
| `GET /1.0/dictionary/countries` | Справочник стран |
| `GET /1.0/dictionary/currencies` | Справочник валют |
| `GET /postoffice/1.0/{postal-code}` | Информация об ОПС |
| `GET /postoffice/1.0/{postal-code}/brief` | Краткая информация |
| `GET /postoffice/1.0/by-address` | Поиск ОПС по адресу |
| `GET /postoffice/1.0/nearby` | Ближайшие ОПС |
| `GET /postoffice/1.0/by-settlement/{name}` | ОПС по населённому пункту |
| `GET /postoffice/1.0/{postal-code}/services-groups` | Группы услуг ОПС |

#### Таймслоты гиперлокальной доставки (TSS)

| Endpoint | Назначение |
|---|---|
| `GET /external/v1/timeslots-by-postindex` | Свободные таймслоты по индексу (до создания заказа) |
| `GET /external/v1/timeslots-by-postindex/{uuid}` | Таймслоты по UUID |
| `POST /external/v1/booking-by-postindex` | Бронирование таймслота |
| `PATCH /external/v1/rebooking-by-postindex` | Пере-бронирование |
| `DELETE /external/v1/booking-by-postindex/{uuid}` | Отмена брони |
| `GET /external/v1/timeslots-for-rebooking` | Таймслоты для перебронирования |

Параметры таймслотов: `postIndexFrom`, `postIndexTo`, `plannedShippingDate`, `address`, `workTypeCode=delivery`, `mailTypeCode=24` (Курьер Онлайн), `mailCtgCode`.

#### Дополнительные услуги и заявления

| Endpoint | Назначение |
|---|---|
| `POST /1.0/claims/create` | Оформление заявления (например, досрочный возврат — `EARLY_RETURN`) |
| `GET /1.0/postoffice-passport/{...}` | Паспорт ОПС |
| `GET /1.0/settings/shipping-points` | Точки сдачи отправителя |
| `GET /1.0/settings/user-settings` | Настройки пользователя |
| `GET /1.0/count-request-api` | Счётчик использованных запросов API |

### 7.4 Ключевые enum'ы (полный набор в `enums-all.md`)

#### Категория РПО (`mail-category`)

`SIMPLE` (простое), `ORDERED` (заказное), `ORDINARY` (обыкновенное), `WITH_DECLARED_VALUE`, `WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY`, `WITH_DECLARED_VALUE_AND_COMPULSORY_PAYMENT`, `WITH_COMPULSORY_PAYMENT`, `COMBINED_*`.

#### Вид РПО (`mail-type`)

`POSTAL_PARCEL`, `ONLINE_PARCEL`, `ONLINE_COURIER`, `EMS`, `EMS_OPTIMAL`, `EMS_RT`, `EMS_TENDER`, `LETTER`, `LETTER_CLASS_1`, `BANDEROL`, `BANDEROL_CLASS_1`, `BUSINESS_COURIER`, `BUSINESS_COURIER_ES`, `PARCEL_CLASS_1`, `VGPO_CLASS_1`, `SMALL_PACKET`, `EASY_RETURN`, `VSD`, `ECOM`, `ECOM_MARKETPLACE`, `HYPER_CARGO`, `COMBINED`.

#### Статусы партии (`shipment.status`)

| Значение | Описание |
|---|---|
| `CREATED` | Партия создана |
| `FROZEN` | В процессе приёма, редактирование запрещено |
| `ACCEPTED` | Принята в отделении связи |
| `SENT` | По заказам есть данные в трекинге |
| `ARCHIVED` | В архиве |

#### Типоразмер (`dimension-type`)

`S` (≤ 260×170×80 мм), `M` (≤ 300×200×150), `L` (≤ 400×270×180), `XL` (530×260×220), `OVERSIZED` (Σ ≤ 1200 мм, любая сторона ≤ 600).

#### Способы оплаты (`payment-method`)

`CASH`, `CASHLESS`, `FREE`, `PLASTIC_CARD`, `POSTAGE_STAMPS_SIGNS`, `ADVANCE_PAYMENT`, `PAID_INTERNATIONAL_OPERATOR`, `PAID_RECIPIENT` (наложенный платёж), `POSTAGE_STAMPS_FRANKING`.

#### Тип адреса (`address-type-to`)

`DEFAULT` (улица, дом, квартира), `PO_BOX` (а/я), `DEMAND` (до востребования), `UNIT` (войсковая часть).

### 7.5 Tracking-events: пара `OperType` + `OperAttr`

API «Отправка» отдаёт операции трекинга как пары `(operType, operAttr)`. Пример канонических кодов — выборка из 200+ значений в `enums-all.md`:

**`OperType` (тип операции):** `ACCEPTING`, `GIVING`, `RETURNING`, `DELIVERING`, `SKIPPING`, `STORING`, `HOLDING`, `PROCESSING`, `IMPORTING`, `EXPORTING`, `CUSTOM_ACCEPTING`, `TRYING`, `REGISTERING`, `CUSTOM_LEGALIZING`, `OPENING`, `CANCELLATION`, `ID_ASSIGNMENT`, `PARTIAL_DELIVERY`.

**`OperAttr` (атрибут уточнения):** `SINGLE_ACCEPTING`, `PARTIAL_ACCEPTING`, `GIVING_RECIPIENT`, `GIVING_RECIPIENT_IN_PO` (выдано в почтомате), `GIVING_RECIPIENT_COURIER`, `RETURNING_BY_EXPIRED_STORING` (истёк срок хранения), `RETURNING_BY_RECEPIENT_REJECT`, `RETURNING_BY_WRONG_ADRESS`, `LOST`, `SORTED`, `ARRIVED`, `OUT_FOR_DELIVERY` (нет такого, фактически — `GIVEN_TO_COURIER`), `DELIVERED_TO_PO` (заложен в почтомат), `EXPIRED_PO_STORING`, `ARRIVED_IN_RUSSIA`, `IMPORTED`, `ACCEPTED_BY_CUSTOM`, `CUSTOM_HOLDING`, `LEGALIZED`, `REJECTED_BY_CUSTOM`, `FAILED_BY_*` (множество причин неудачной попытки вручения).

Маппинг в каноническую модель — отдельная большая таблица в ACL: `(OperType, OperAttr) → CanonicalStatus`. Без этой таблицы интеграция нечитаема.

### 7.6 Маппинг Почта России → каноническая taxonomy

| `OperType` / `OperAttr` | Canonical |
|---|---|
| `ID_ASSIGNED` / `REGISTERED` | `LABEL_CREATED` |
| `ACCEPTING` (`SINGLE_ACCEPTING`, `PARTIAL_ACCEPTING`) | `PICKED_UP` |
| `SORTING`, `SORTED`, `SENT`, `EN_ROUTE` | `IN_TRANSIT` |
| `ARRIVED` (в место вручения) | `ARRIVED_HUB` |
| `GIVEN_TO_COURIER`, `COURIER_ORDERED` | `OUT_FOR_DELIVERY` |
| `DELIVERED_TO_PO` | `AT_PICKUP_POINT` (постамат) |
| `GIVING_RECIPIENT*` (любая ветка) | `DELIVERED` |
| `TRYING` (неудачная попытка) | `DELIVERY_ATTEMPTED` |
| `STORING`, `HOLDING`, `TEMPORAL_STORING`, `EXPIRED_PO_STORING` | `EXCEPTION` (ждёт) |
| `RETURNING_*` (любая причина) | `RETURN_TO_SENDER` |
| `LOST`, `CONFISCATED`, `DESTROYED` | `LOST` / `DAMAGED` |
| `IN_CUSTOMS_*`, `CUSTOM_HOLDING`, `REJECTED_BY_CUSTOM` | `HELD_AT_CUSTOMS` |
| `CANCELLATION` (`CANCELED_BY_SENDER`, `CANCELED_BY_OPERATOR`) | `FAILURE` |

### 7.7 Расчёт стоимости пересылки

`POST /1.0/tariff` — возвращает плату в копейках, разделённую по тарифам:

- `ground-rate` — наземная пересылка
- `avia-rate` — авиа
- `insurance-rate` — объявленная ценность
- `inventory-rate` — опись вложения
- `notice-rate` — уведомление о вручении
- `oversize-rate` — надбавка за негабарит (>10 кг)
- `fragile-rate` — отметка «Осторожно/Хрупкое/Терморежим»
- `vsd-rate` — возврат сопроводительных документов
- `completeness-checking-rate`, `contents-checking-rate`, `sms-notice-recipient-rate`
- `total-rate` + `total-vat`
- `delivery-time` (`min-days` / `max-days`)

Для тарифов «Курьер онлайн» (`mail-type=ONLINE_COURIER`) — также таймслоты через TSS.

### 7.8 Особенности и ограничения

- **Webhooks**: API «Отправка» — без push-вебхуков, статусы партии и трекинг доступны через polling.
- **Tracking API** (отдельный сервис `tracking.pochta.ru`): анонимный режим лимитирован (~100 RPS), полный доступ — только клиентам с договором; batch-trace до 3000 ШПИ за один запрос.
- **Ярлыки**: тип печати `PAPER` (А5) или `THERMO` (А6); скачиваются через `GET /1.0/forms/.../...`.
- **Идемпотентность**: натуральный ключ — `order-num` (внешний номер заказа). Повторное создание с тем же `order-num` ошибка `error_validate_online_shop_number_departure_is_not_unique`.
- **Возвраты**: легкий возврат (`EASY_RETURN`) и «возврат отправителю» — поддерживаются явными методами `/1.0/returns`.
- **Маркетплейс / 54-ФЗ**: при наложенном платеже требуется `compulsory-payment`, чеки фискализируются, `goods.items[]` обязателен.

### 7.9 Типичные ошибки

Полный набор — `BatchError`, `OrderValidationError`, `TariffErrorCode`, `CreateReturnError` (см. `enums-all.md`):

- `EMPTY_MAIL_CATEGORY`, `EMPTY_MAIL_TYPE`, `EMPTY_INDEX_TO`, `EMPTY_REGION_TO`, `EMPTY_PLACE_TO` — обязательные поля.
- `ILLEGAL_*` — некорректное значение поля (адрес, индекс, ФИО, способ пересылки и т. п.).
- `INSR_VALUE_EXCEEDS_MAX` — объявленная ценность превышает лимит.
- `RESTRICTED_MAIL_CATEGORY` — для наложенного платежа нужен номер ЕСПП в настройках сервиса.
- `DIFFERENT_TRANSPORT_TYPE` / `DIFFERENT_MAIL_TYPE` / `DIFFERENT_MAIL_CATEGORY` — несовпадение параметров при добавлении в партию.
- `ABSENT_*_POSTMARK` / `UNEXPECTED_*_POSTMARK` — несовпадение отметок отправления и партии.
- `READONLY_STATE` — партия в статусе `FROZEN`/`ACCEPTED`, изменения недопустимы.
- `BARCODE_ERROR` — сбой при выдаче ШПИ.
- `TARIFF_ERROR` / `CODE_1372` (доставка по маршруту не осуществляется).
- `DIRECT_SHIPMENT_NOT_FOUND` (возврат по несуществующему ШПИ), `RETURN_ALREADY_EXIST`, `EASY_RETURN_NOT_SUPPORTED`, `EASY_RETURN_DISABLED`.

---

## 8. DPD API — детально

### 8.1 Особенности DPD Russia

DPD Russia использует REST API с типичным набором endpoints:

- Create shipment.
- Get rates.
- Tracking by parcel number.
- Print label.

DPD как international carrier имеет глобальный API + регионально-специфичные variations.

### 8.2 Tracking integration

> "DPD Russia tracking API allows merchants or developers to integrate real-time tracking information into e-commerce sites or internal systems, enabling tracking of shipment locations, in-transit movements, estimated delivery times, and exceptions."

Webhooks доступны через AfterShip, TrackingMore (third-party aggregators) или прямым integration через DPD developer portal (`dpd.com/developers`).

### 8.3 Use case

DPD сильна в B2B-сегменте, для крупных грузов, и для cross-border (Restored European-network). Для типового B2C российского e-commerce — реже выбирается, чем CDEK/Yandex.

---

## 9. Boxberry — пункты выдачи

### 9.1 Особенности

Boxberry — крупная сеть ПВЗ в России, используется как budget-friendly альтернатива СДЭК.

`api.boxberry.ru` — REST endpoints:

- `ListPoints` — список ПВЗ с фильтрами по городу.
- `ParselCreate` — создать отправление.
- `ParselSend` — list of waiting shipments.
- `OrdersBalance` — финансовый баланс.
- `ListStatuses` — статусы по tracking number.
- `ListServices` — список сервисов с прайсами.
- `LabelGenerator` — generate label PDF.

### 9.2 Integration pattern

Standard CRM/CMS integration — autotransfer information about shipment after order status change, automatic label generation, customer-side tracking.

Boxberry часто используется через aggregator'ы (ApiShip, Cdek-Pickpoint, Shiptor) для упрощения multi-carrier logic.

---

## 10. ДоброПост (DobroPost) — детально

> Источник: локальная копия документации в `dobropost_shipment_api/` ([`README.md`](dobropost_shipment_api/README.md) + машиночитаемый [`openapi.json`](dobropost_shipment_api/openapi.json)). Версия API: **2025-04-16** («API Шипменты 16.04.2025.pdf»). Базовый URL: `https://api.dobropost.com`.

ДоброПост — **российский cross-border оператор** для доставки товаров из Китая в РФ с прохождением таможенного оформления. В отличие от СДЭК/Yandex/Почты России, которые работают на внутреннем рынке, ДоброПост — это нишевый адаптер для интернет-магазинов, выкупающих товары в Китае и доставляющих их конечному получателю с растаможкой по упрощённой процедуре (товары для личного пользования).

### 10.1 Auth — JWT с TTL 12 часов

В отличие от OAuth 2 client_credentials у СДЭК или Bearer-токена с неограниченным сроком у Yandex, ДоброПост использует **JWT-токен** с **жёстким TTL 12 часов**.

```http
POST /api/shipment/sign-in
Content-Type: application/json

{ "email": "partner@example.com", "password": "S3cretPa$$word" }
```

Ответ: `{ "token": "eyJhbGciOi..." }`. Все защищённые методы — с `Authorization: Bearer {token}`.

**Практический вывод для backend:** в адаптере DobroPost нужен фоновый refresh токена каждые 11 часов (с запасом до истечения), либо ленивая ре-аутентификация на 401 с автоматическим retry.

### 10.2 Полный список endpoint'ов

| Метод | URL | Назначение | Auth |
|---|---|---|---|
| `POST` | `/api/shipment/sign-in` | Получение JWT-токена (TTL 12h) | – |
| `POST` | `/api/shipment` | Создание Шипмента | Bearer |
| `GET` | `/api/shipment` | Список Шипментов с пагинацией (`page`, `offset`, `statusId`) | Bearer |
| `PUT` | `/api/shipment` | Обновление Шипмента | Bearer |
| `DELETE` | `/api/shipment/{id}` | Удаление Шипмента | Bearer |
| `POST` | `https://yourdomain.com/webhook` | Webhook от ДоброПост на endpoint клиента | – |

Только 5 методов основного API + 1 webhook-callback — это **самое компактное API** среди разобранных в §§5–9.

### 10.3 Структура Shipment (cross-border specific)

В отличие от обобщённой shipment-модели, у ДоброПост в обязательных полях запроса присутствуют **таможенно-специфичные поля**, которых нет у СДЭК/Yandex/Почты:

| Поле | Почему обязательно |
|---|---|
| `consigneePassportSerial` (ровно 4 символа) | Таможня РФ требует паспорт получателя для cross-border |
| `consigneePassportNumber` (ровно 6 символов) | -//- |
| `passportIssueDate` | -//- |
| `consigneeBirthDate` | Обязательно **только для тарифа DP Ultra** (специальный тариф с расширенными требованиями) |
| `vatIdentificationNumber` (ровно 12 символов) | ИНН для деклараций (ФЛ — это ИНН физлица) |
| `incomingDeclaration` (<16 символов) | Трек-номер посылки **по Китаю** — нужен для связки с китайским отправителем |
| `dpTariffId` | Тариф доставки (например, DP Ultra с курьером до двери, стандартный с ПВЗ) |

Все денежные поля (`totalAmount`, `itemPrice`) — **в юанях (CNY)**, конвертация в рубли — на стороне ДоброПост.

Рекомендация ДоброПост: **не более 4 единиц товара (`numberOfItemPieces`)** в одном Шипменте — иначе таможня может квалифицировать как коммерческую партию (статус 541).

### 10.4 Ответ Create Shipment — что возвращается

Ответ — расширенная структура с вложенными объектами:

```text
ShipmentResponse
├── id, statusDate, dptrackNumber           ← присвоенные системой
├── itemWeight, totalWeightKG               ← рассчитанные на стороне ДоброПост
├── deliveryTariff
│   ├── id, name, description, measureQty, pricePerUnit
│   ├── minTariffPerMeasureQty, startDate
│   ├── country (code, name, a2, a3, priority)
│   ├── currency (code, ccy, base)
│   └── amountUnits (id, name, caption)
├── status (id, name)                       ← из 40-значного справочника
├── vatidentificationNumber                 ← в ответе со строчной 'i'!
├── incomingDeclaration                     ← оригинальный китайский трек
└── dptrackNumber                           ← российский трек ДоброПост
```

> **Важная орфографическая ловушка:** в **request** поле называется `vatIdentificationNumber` (заглавная `I`), а в **response** — `vatidentificationNumber` (строчная `i`). Это видимо bug API, но он стабилен — учитывайте в маппере ACL.

### 10.5 Webhooks — два формата payload

ДоброПост — единственный из разобранных carriers с **двумя различными webhook-форматами**, дискриминируемыми по набору полей:

#### 10.5.1 Проверка паспорта (DaData)

```json
{
  "shipmentId": 12345,
  "statusDate": "2025-02-04T14:30:00Z",
  "passportValidationStatus": true
}
```

ДоброПост проверяет паспортные данные получателя через **DaData** и присылает результат отдельным webhook'ом. Если `passportValidationStatus = false` — посылку нельзя растаможить, нужно запросить корректные данные у customer'а.

#### 10.5.2 Обновление статуса

```json
{
  "shipmentId": 12345,
  "DPTrackNumber": "DP123456789RU",
  "statusDate": "2025-02-04T14:30:00Z",
  "status": "В пути"
}
```

`status` — **текстовый** (не `id`!) — это локализованное название из справочника (`В пути`, `Доставлено`, `Задерживается` и т. п.). Маппер ACL должен делать обратное соответствие текст → `canonical status`.

#### 10.5.3 Контракт ответа клиента

| Код | Когда |
|---|---|
| `200 OK` (с пустым телом) | Успешная обработка |
| `400 Bad Request` | Отсутствуют обязательные поля или неправильный формат |
| `401 Unauthorized` | Токен не прошёл валидацию |
| `500 Internal Server Error` | Непредвиденная ошибка на стороне клиента |

**Без подписи и без явной идемпотентности.** Дедупликация — на стороне клиента по композитному ключу `(shipmentId, statusDate, status)` или `(shipmentId, statusDate, passportValidationStatus)`.

### 10.6 Справочник статусов — 40 значений в 4 группах

Уникальная особенность ДоброПост: **id статуса несёт семантическую группу** (порядковый префикс). Это удобно для FSM-фильтров:

| Диапазон | Группа | Кол-во | Примеры |
|---|---|---|---|
| `1–9` | Базовая логистическая цепочка | 9 | Ожидается на складе → Передан партнеру |
| `270–272` | Редактирование данных посылки | 3 | Запрос/отклонение/исполнение редактуры |
| `500–649` | Таможенное оформление | 19 | Начало → выпуск товаров с/без оплаты пошлин → отказы 541–546 |
| `590xxx` | Развёрнутые отказы с кодами причин | 9 | 590204, 590401, 590404, 590405, 590409, 590410, 590413, 590420, 590592 |

**Терминальные статусы:**

- ✔ `649` (Покинула таможню и передана на доставку по РФ) — happy-path выход в last-mile.
- ❌ `541–546`, `590xxx` — отказы таможни (не подлежат доставке).
- ❌ `600` (Посылка не пришла) — потеря на участке Китай → РФ.

> **Особенность:** есть **дубли названий** для разных id (`520` и `521` оба = «Выпуск товаров без уплаты таможенных платежей»; `530` и `532` оба = «Выпуск товаров (таможенные платежи уплачены)»; `510` и `531` оба = «Требуется уплатить таможенные пошлины»). Скорее всего это разные реальные событий из систем таможни (ФТС vs МПП), маппящиеся на одинаковые читаемые тексты. В FSM ACL — обработать оба id одинаково.

### 10.7 Маппинг ДоброПост → каноническая taxonomy

| ДоброПост `status.id` | Canonical |
|---|---|
| `1` (Ожидается на складе) | `LABEL_CREATED` |
| `2` (Получен от курьера) | `PICKED_UP` |
| `3` (Обработан на складе), `4`, `5` (Добавлен в мешок/реестр) | `IN_TRANSIT` (хаб Китая) |
| `6` (Покинул склад в Китае) | `IN_TRANSIT` |
| `7`, `8` (Поступил на таможню в Китае/России) | `HELD_AT_CUSTOMS` |
| `500`, `591` (Начало таможенного оформления) | `HELD_AT_CUSTOMS` |
| `510`, `531`, `540` (Требуется/ожидание оплаты пошлин) | `EXCEPTION` (требует действия customer'а) |
| `520`, `521`, `530`, `532` (Выпуск товаров) | `IN_TRANSIT` (после таможни) |
| `541`–`546`, `590xxx` (Отказы) | `FAILURE` (terminal) |
| `570` (Продление времени обработки) | `EXCEPTION` |
| `600` (Посылка не пришла) | `LOST` (terminal) |
| `648` (Подготовлено к отгрузке в last mile) | `OUT_FOR_DELIVERY` |
| `649` (Покинула таможню и передана на доставку по РФ) | `OUT_FOR_DELIVERY` (передача партнёру last-mile) |
| `9` (Передан партнеру) | `OUT_FOR_DELIVERY` (Шипмент уходит партнёру для last-mile, дальше треки в их системе) |
| `270`–`272` (Редактирование) | внутренние события, не маппятся в canonical |

### 10.8 Чек-лист интеграции ДоброПост

- [ ] Background-job на refresh JWT-токена каждые ~11h (с буфером до истечения).
- [ ] Lazy re-auth на 401 с авто-retry оригинального запроса.
- [ ] Idempotency на стороне merchant: натуральный ключ — `incomingDeclaration` (трек по Китаю) или внутренний `order_id`.
- [ ] Webhook endpoint c discriminator-логикой по полю: `passportValidationStatus` → DaData-payload, `DPTrackNumber + status` → status-payload.
- [ ] Webhook idempotency через `(shipmentId, statusDate, ...)` composite key.
- [ ] Маппер `status.id (40 значений) → canonical status` (см. §10.7).
- [ ] Конверсия валют: API оперирует **CNY**, в Order BC — рубли (хранить курс на момент создания шипмента).
- [ ] Валидация на стороне merchant'а до отправки: паспорт 4+6 символов, ИНН 12 символов, `itemDescription` <60, `incomingDeclaration` <16, `comment` <60, `numberOfItemPieces` ≤ 4.
- [ ] Обработка `passportValidationStatus = false` → флаг в Order, escalation в customer service для запроса корректных паспортных данных.
- [ ] Алертинг на статусы 541–546 и 590xxx — это таможенные отказы, требующие manual intervention.
- [ ] Tracking-page customer'а — показывать `dptrackNumber` (российский) и `incomingDeclaration` (китайский) одновременно.

### 10.9 Сравнение с CDEK/Yandex/Почтой

| Аспект | ДоброПост | СДЭК | Yandex | Почта России |
|---|---|---|---|---|
| Auth | JWT (TTL 12h) | OAuth2 (TTL 1h) | Bearer (бессрочный) | `AccessToken` + `X-User-Authorization` |
| Кол-во endpoints | **5 + webhook** | 40+ | 35 | 70+ |
| Валюта | **CNY** | RUB и др. | RUB | RUB |
| Покрытие | Cross-border CN→RU | Внутри РФ + СНГ | Внутри РФ | Внутри РФ + международное |
| Таможня в API | **first-class** (passport, ИНН, китайский трек) | через спец. услуги | – | через `customs-declaration` |
| Webhooks | 2 типа (passport + status) | 9 типов | callback URL | нет, только polling |
| Идемпотентность | без `Idempotency-Key`, через natural keys | через `number` (ИМ) | `operator_request_id` | `order-num` |
| Dual track-numbers | ✔ (`dptrackNumber` + `incomingDeclaration`) | один `cdek_number` | `request_id` | один ШПИ |
| Статусов в FSM | 40 | 28 | ~50 (две ветки) | 200+ пар (operType × operAttr) |

**Когда выбирать ДоброПост в архитектуре:**

- Loyality-маркетплейс с **cross-border выкупом** товаров в Китае (Poizon-like flow).
- Нужна **готовая таможенная очистка** для товаров личного пользования (без необходимости получения статуса участника ВЭД).
- Покупатель в РФ, поставщик в КНР, нет собственной экспедиторской цепочки.

**Когда не подходит:**

- Внутренние российские отправления (там СДЭК/Yandex/Почта дешевле и быстрее).
- B2B-партии (ДоброПост заточен на товары для личного пользования, есть лимит ≤ 4 единиц).

---

## 11. Multi-carrier abstraction

### 11.1 Зачем

Зайти в продакшн с одним carrier'ом — стартовая позиция. Через 6 месяцев нужны 3-5 carriers (regional coverage, fallback, cost optimization). Если интеграция сделана прямо в Order BC — refactoring catastrophe.

### 11.2 Adapter pattern

```text
        ┌────────────────────────────┐
        │     Order Service          │
        │     (Ordering BC)          │
        └────────────┬───────────────┘
                     │ "I need to ship this Order"
                     ▼
        ┌────────────────────────────┐
        │   Shipping Service          │
        │   (Shipping BC)             │
        │                             │
        │   ┌─────────────────────┐   │
        │   │ CarrierAdapter (IF) │   │
        │   └─────────┬───────────┘   │
        │             │               │
        │ ┌───────────┼─────────────┐ │
        │ ▼           ▼             ▼ │
        │ CDEKAdapter YandexAdapter   │
        │             PochtaAdapter   │
        │             BoxberryAdpr    │
        │             DPDAdapter      │
        │             DobroPostAdapter│
        │             ShippoAdapter   │
        └─────────────┼───────────────┘
                      │
                      ▼
                  External APIs
```

### 11.3 Common interface

```typescript
interface CarrierAdapter {
  getRates(shipment: ShipmentRequest): Promise<Rate[]>;
  createShipment(shipment: ShipmentRequest, service: ServiceLevel): Promise<CarrierShipment>;
  generateLabel(shipmentId: string): Promise<Label>;
  cancelShipment(shipmentId: string): Promise<void>;
  getTracking(trackingNumber: string): Promise<TrackingEvent[]>;
  parseWebhook(payload: any, signature: string): TrackingEvent;
}

interface CarrierShipment {
  carrierShipmentId: string;
  trackingNumber: string;
  estimatedDelivery: Date;
  cost: Money;
}
```

### 11.4 ACL: что преобразуется на границе

В каждом adapter'е происходит:

- Address format normalization (РП требует индекс, CDEK — `city_code`, и т.д.).
- Item dimensions перевод unit (граммы vs кг).
- Service level mapping ("Express" → CDEK service 137).
- Status mapping (см. §4).
- Auth token management.
- Error normalization (carrier-specific errors → unified error codes).
- Webhook signature verification per carrier.

### 11.5 Routing engine

Над adapter'ами — routing logic, определяющая какой carrier выбрать для конкретного Order:

```python
def select_carrier(shipment: ShipmentRequest) -> Carrier:
    # 1. Region constraints
    if shipment.destination.country != 'RU':
        return select_international(shipment)

    # 2. Rate shopping
    rates = get_rates_from_all_carriers(shipment)

    # 3. Service level filter
    rates = filter_by_sla(rates, max_days=shipment.requested_eta_days)

    # 4. Customer preference
    if shipment.customer_preferred_pickup_point:
        rates = filter_by_pickup_point_availability(rates)

    # 5. Cost optimization (or smart routing by past success rate)
    return min(rates, key=lambda r: r.cost)
```

### 11.6 Aggregators vs Direct

| Aspect | Direct integration | Aggregator (Shippo/EasyPost/ShipEngine/ApiShip) |
|---|---|---|
| Time-to-market | Slow (1 carrier per integration) | Fast (один integration, 80+ carriers) |
| Cost | Только carrier rates | + aggregator fees |
| Control | Полный | Limited to aggregator features |
| Carriers | Whatever you integrate | 80-1500+ carriers depending |
| Status mapping | Своими руками | Уже сделан unified |
| Webhooks | Per-carrier setup | Unified webhook |
| Best for | Tier-1 retail с 3-5 carriers | Mid-market, fast scaling |

В России типично direct integration (CDEK/Yandex/Почта/Boxberry — local players, нет хорошего aggregator с полным coverage). Глобально — Shippo/EasyPost/ShipEngine популярны.

### 11.7 Российские aggregators и cross-border carriers

**Aggregators (multi-carrier):**

- **ApiShip** — coverage CDEK, СДЭК, Почта, DPD, IML, Boxberry, PickPoint и др.
- **Shiptor** — fulfillment + delivery aggregator.
- **Cdek-Pickpoint** — старый aggregator (часто legacy).

**Cross-border direct carriers:**

- **ДоброПост** (см. §10) — single-carrier, специализация **CN→RU** с таможенным оформлением товаров для личного пользования (паспорт + ИНН ФЛ обязательны). Не aggregator; интегрируется как обычный CarrierAdapter, но с special-case полями для таможни (`vatIdentificationNumber`, `incomingDeclaration`, `passportIssueDate`).

---

## 12. Tracking webhooks — реализация

### 12.1 Архитектура webhook receiver

```text
[Carrier]
   │ POST /webhooks/cdek
   ▼
[Webhook receiver]
   │ 1. Verify signature
   │ 2. Insert raw event into DB (audit)
   │ 3. Enqueue to processing queue
   │ 4. Return 200 immediately
   │
   ▼
[Background worker]
   │ 1. Pop event from queue
   │ 2. Parse via CDEK adapter
   │ 3. Map to canonical TrackingEvent
   │ 4. Idempotency check (event_id from carrier or natural key)
   │ 5. Update Shipment FSM if needed
   │ 6. Append TrackingEvent
   │ 7. Publish domain event (TrackingEventRecorded)
```

### 12.2 Idempotency у carriers

Carriers редко дают clean idempotency key (как Stripe). Реализация дедупликации:

- **CDEK:** `(uuid, status_code, status_date_time)` — composite key.
- **Yandex:** journal-based, monotonic position numbers.
- **Почта:** `(barcode, oper_type, oper_date)` — composite.

```sql
CREATE TABLE tracking_events (
    id              UUID PRIMARY KEY,
    shipment_id     UUID NOT NULL,
    carrier         VARCHAR(32) NOT NULL,
    carrier_status  VARCHAR(64) NOT NULL,
    canonical_status VARCHAR(32) NOT NULL,
    occurred_at     TIMESTAMP NOT NULL,
    raw_payload     JSONB NOT NULL,

    UNIQUE (shipment_id, carrier_status, occurred_at)
);
```

UNIQUE constraint = idempotency.

### 12.3 Replay & backfill

Если webhook downstream broken на N часов:

1. CDEK retries — обычно 24 часа.
2. После — нужен backfill через `GET /v2/orders/{uuid}` для всех active shipments.
3. Сравнение local tracking history с carrier history → дополнить gap.

Регулярный nightly reconciliation job — best practice. Webhooks для real-time, polling для catch-up.

### 12.4 Polling fallback

Для carriers без webhooks (Почта России):

```python
def polling_loop():
    while True:
        active_shipments = db.query(
            "SELECT * FROM shipments WHERE state IN ('IN_TRANSIT','OUT_FOR_DELIVERY')"
        )
        for batch in chunks(active_shipments, 1000):
            tracking_responses = pochta_api.batch_track(
                [s.tracking_number for s in batch]
            )
            for resp in tracking_responses:
                process_tracking_update(resp)
        sleep(15 minutes)
```

Каденция: 15-30 минут для active shipments, реже для long-tail.

### 12.5 Customer-facing tracking page

```text
Order page → /tracking/{order_id}
   ├─ Render OrderTrackingView (read model)
   ├─ For each shipment:
   │   ├─ Carrier name + tracking number
   │   ├─ Canonical status badge
   │   ├─ Timeline of TrackingEvents
   │   └─ Link на carrier-native page (deep link)
   └─ Optionally: real-time updates via SSE/WebSocket
```

Не показывать carrier-specific status codes customer'у. Только canonical labels на ubiquitous language ("В пути", "Готов к выдаче", "Доставлен").

---

## 13. Label generation

### 13.1 Sync vs Async

**Sync (rare):** API call returns PDF immediately. Хорошо для небольших volumes.

**Async (typical):**

1. Submit print request → returns `print_uuid`.
2. Poll или webhook → label ready.
3. Download PDF.

CDEK — async с polling. Yandex — sync (label в response create-claim для некоторых scenarios).

### 13.2 Batch labels

Для warehouse operations нужно print labels пачками:

```http
POST /v2/print/orders
body: { orders: [uuid1, uuid2, uuid3, ...] }
→ returns { print_uuid }
... wait ...
GET /v2/print/orders/{print_uuid}
→ returns single PDF с N labels (по 1 на страницу)
```

CDEK поддерживает до X labels в одном batch.

### 13.3 Label types

- **Shipping label** — основной ярлык с trackingnumber/barcode.
- **Invoice / waybill** — товарно-транспортная накладная.
- **Customs declaration** — для cross-border (CN22/CN23).
- **Return label** — pre-paid для customer'а.

### 13.4 Storage

Labels часто храним в S3 / object storage. URL — short-lived signed (10 минут+ для warehouse worker'а).

```sql
shipments table:
  label_url       TEXT,         -- s3://bucket/labels/{shipment_id}.pdf
  label_generated_at TIMESTAMP,
  label_format    VARCHAR(8),   -- 'pdf', 'zpl' (zebra printer)
```

### 13.5 Label format

- **PDF** — для печати на A4/A6.
- **ZPL** (Zebra Programming Language) — для thermal printers (warehouse).
- **EPL** — старый Eltron format.

Some carriers поддерживают только PDF (СДЭК), others — multiple (EasyPost все три).

---

## 14. Pickup point (ПВЗ) integration

### 14.1 Зачем

Доставка до ПВЗ:

- Дешевле для customer'а.
- Удобнее (большие приёмные часы).
- Дешевле для merchant'а (carrier берёт меньше).
- Часто preferred способ в России (40-60% e-commerce).

### 14.2 Integration

1. Customer на checkout выбирает "Доставка в ПВЗ"
2. Frontend → carrier API: GET pickup points near `{address}`
   - returns list `{ id, name, address, lat/lng, work_hours }`
3. Customer выбирает pickup point на map
4. Frontend сохраняет `pickup_point_id` в order
5. На ship: create shipment с `deliveryPoint = pickup_point_id`
6. Carrier delivers to that PUDO
7. Customer notification: "Заказ готов к выдаче в ПВЗ X"
8. Customer приходит, забирает (по коду или паспорту)
9. Carrier webhook: `status = DELIVERED`

### 14.3 API endpoints

- **CDEK:** `GET /v2/deliverypoints?country_code=RU&city_code=44`
- **Yandex:** pickup points бывают для NDD (Next Day Delivery) сегмента.
- **Boxberry:** `ListPoints` с filters.
- **Почта России:** индекс отделений.

### 14.4 Customer UX

Map view с pinned PUDO points + filters (work hours, fitting room, delivery time, cash payment available). Это сложный UI компонент — обычно используются готовые widgets от carrier'а или third-party (DadaCity, GeoMap).

---

## 15. Returns / RMA / refusals

### 15.1 RMA flow

1. Customer requests return → RMA created (Returns BC, Тема 9)
2. Generate return label (pre-paid):
   - `POST /v2/orders` с `is_return_order: true` (CDEK)
   - returns reverse tracking number
3. Send label PDF + instructions to customer (email)
4. Customer drops off package в ПВЗ или calls courier pickup
5. Reverse Shipment FSM:
   `PENDING → PICKED_UP → IN_TRANSIT → ARRIVED → INSPECTED → RESTOCKED`
6. After inspection: RMA → APPROVED/REJECTED
7. On APPROVED: trigger refund (Тема 6)

### 15.2 Return Shipment — отдельная сущность

```text
ForwardShipment
  - id
  - orderId
  - direction: 'forward'

ReverseShipment
  - id
  - orderId (same)
  - rmaId (reference to RMA aggregate)
  - direction: 'reverse'
  - originalShipmentId  (optional)
```

Не модифицируйте forward shipment для returns. Создайте новый shipment.

### 15.3 Refusal at delivery

Customer может отказаться на доставке:

- Не открыл дверь / не пришёл в ПВЗ за 7 дней.
- Передумал.
- Damaged packaging.

Carrier авто-генерирует return shipment к merchant'у. Customer не платит.

CDEK webhook покажет `is_return: true` + status code типа 17 (Возврат отправителю).

### 15.4 Partial returns

Customer вернул 1 из 3 items. Reverse Shipment содержит только returned items. Forward order остаётся Delivered, RMA отдельно tracks return progress.

### 15.5 Refusal vs Cancellation timing

- **Cancel before pickup:** shipment cancellation API. Зависит от carrier — обычно бесплатно.
- **Cancel during transit:** redirect или return-to-sender. Часто платно.
- **Cancel at delivery:** refusal — customer отказывается, return-to-sender автоматический.
- **Cancel after delivery:** returns flow, RMA.

Каждый сценарий — разный API call и разные fees.

---

## 16. Loyality-специфика: cross-border dropship через ДоброПост + last-mile

> Это конкретный архитектурный паттерн, реализуемый в Loyality. Он отличается от классического retail-flow тем, что **товара нет на собственном складе на момент создания Order'а** — товар выкупается менеджером в китайском маркетплейсе после оплаты, а доставка состоит из **двух последовательных Shipment-сегментов**: cross-border (Китай → склад в РФ) и last-mile (склад в РФ → ПВЗ покупателя).

### 16.1 Бизнес-flow Loyality

```text
[Customer]
   │ 1. Просматривает каталог (продукты скопированы из китайского маркетплейса)
   │ 2. Выбирает товар, выбирает российский ПВЗ (СДЭК/Yandex/Boxberry/Почта)
   │ 3. Оформляет Order, оплачивает
   ▼
[Order: PENDING → PAID] ─── публикует OrderPlaced event
   │
   ▼
[Admin Panel: Manager dashboard]
   │ 4. Менеджер видит новый Order в admin-панели (filter status=PAID)
   │ 5. Менеджер вручную идёт на китайский маркетплейс (Poizon / Taobao / 1688)
   │ 6. Выкупает товар, получает китайский трек-номер
   │ 7. Вставляет китайский трек в форму "Tracking Number" в админке Order'а
   ▼
[Order: PAID → PROCURED]   ─── китайский трек = поле incomingDeclaration
   │
   │ 8. Backend: на событие OrderProcured автоматически создаёт DobroPost shipment
   ▼
[Cross-border Shipment #1 (carrier=DOBROPOST)]
   │  POST /api/shipment к ДоброПост с incomingDeclaration = китайский трек
   │  → получаем dptrackNumber (российский трек ДоброПост)
   │
   │  Lifecycle (40 статусов из §10):
   │  1 (Ожидается на складе) → 2 → 3 (Обработан) → 6 (Покинул склад в Китае)
   │  → 7 (Таможня Китая) → 8 (Таможня РФ) → 500 (Начало ТО) → 530 (Выпуск ТО)
   │  → 648 (Подготовлено к last-mile) → 649 (Передано на доставку по РФ)
   │
   │  При status_id ∈ {648, 649} — публикуется CrossBorderArrived event
   ▼
[Order: PROCURED → ARRIVED_IN_RU]
   │
   │ 9. Backend: автоматически создаёт last-mile Shipment у российского carrier'а
   ▼
[Last-Mile Shipment #2 (carrier=CDEK / YANDEX)]
   │  Выбор carrier'а — по customer.preferred_pickup_point на момент checkout'а
   │  POST /v2/orders (CDEK) / pickups/create (Yandex)
   │  → получаем национальный tracking_number
   │
   │  Lifecycle: PRE_TRANSIT → IN_TRANSIT → AT_PICKUP_POINT → DELIVERED
   ▼
[Order: ARRIVED_IN_RU → IN_LAST_MILE → DELIVERED]
```

### 16.2 Карта shipments на один Order

```text
Order
  │
  ├── Shipment #1 (direction=forward, leg=cross_border, carrier=DOBROPOST)
  │     ├── carrierShipmentId = dobropost.id
  │     ├── dptrackNumber       (российский трек ДоброПост)
  │     ├── incomingDeclaration (китайский трек, заполняет менеджер)
  │     └── lifecycle: 40 статусов ДоброПост (§10)
  │
  └── Shipment #2 (direction=forward, leg=last_mile, carrier=CDEK|YANDEX)
        ├── carrierShipmentId   (uuid/posting_number/ШПИ)
        ├── trackingNumber      (cdek_number / claim_id / barcode)
        ├── parentShipmentId    → Shipment #1 (явная связь между leg'ами)
        └── lifecycle: канонический FSM PRE_TRANSIT → DELIVERED
```

**Ключевые принципы:**

- Order : Shipment = **1 : 2 (минимум)** в Loyality, всегда. Не один shipment на весь путь Китай→ПВЗ.
- Shipment #2 (last-mile) **создаётся не в момент checkout'а**, а на event'е `CrossBorderArrived` (status_id = 648/649 от ДоброПост). До этого момента last-mile carrier даже не выбран как конкретный shipment у себя.
- Customer на странице tracking'а видит **3 трек-номера**: китайский (`incomingDeclaration`), российский ДоброПост (`dptrackNumber`), последняя миля (`trackingNumber` российского carrier'а).

### 16.3 Manager actions — admin-панель

В админке менеджер выполняет **4 ручных действия** в типовом flow Loyality:

| # | Действие | Endpoint backend'а | Side effect |
|---|----------|---------------------|-------------|
| 1 | Открыть Order в статусе `PAID` | `GET /admin/orders?status=PAID` | – |
| 2 | Нажать «Выкупить» → перейти на китайский маркетплейс (внешняя ссылка из карточки товара) | – | – |
| 3 | После выкупа вставить китайский трек | `POST /admin/orders/{id}/procure` body `{ incomingDeclaration }` | Order → `PROCURED`, async создаётся DobroPost shipment |
| 4 | (Опционально) изменить ПВЗ доставки если customer запросил | `PATCH /admin/orders/{id}/pickup-point` | Только до status_id=648 (last-mile ещё не создан) |

Всё остальное автоматизируется по событиям carrier-вебхуков:

- DobroPost webhook (status-update) → обновление прогресса cross-border shipment + автосоздание last-mile shipment при `status_id ∈ {648, 649}`.
- DobroPost webhook (passport-validation) → если `passportValidationStatus=false`, escalation в customer service.
- Russian carrier webhook → обновление прогресса last-mile до `DELIVERED`.

### 16.4 FSM Order (Loyality cross-border-dropship)

См. подробно [[Research - Order (2) State Machine FSM]] §15.

```text
PENDING ──► PAID ──► PROCURED ──► ARRIVED_IN_RU ──► IN_LAST_MILE ──► DELIVERED
   │          │          │              │                 │
   ▼          ▼          ▼              ▼                 ▼
CANCELLED  CANCELLED  CANCELLED   CANCELLED + REFUND    NOT_DELIVERED
                      + REFUND   + RECALL/RESHIP        (refusal at pickup)
```

Ключевые состояния:

- **`PROCURED`** — менеджер выкупил товар в Китае, китайский трек привязан, DobroPost shipment создан. До этого товара физически не существует в нашей цепочке.
- **`ARRIVED_IN_RU`** — DobroPost закончил cross-border сегмент (status_id ∈ {648, 649}), товар на российском складе ДоброПост, last-mile shipment создан.
- **`IN_LAST_MILE`** — последняя миля начата, customer получает tracking российского carrier'а в email.

### 16.5 Edge-cases

| Сценарий | Решение |
|---|---|
| Менеджер не нашёл товар в Китае (sold out) | Order → `CANCELLED` с reason=`OUT_OF_STOCK_AT_SUPPLIER`, refund customer'у |
| Китайский маркетплейс прислал не тот товар, поставщик не отгружает | Order остаётся в `PROCURED`, китайский трек никогда не получит status; nightly job алертит «застрявшие в PROCURED > 14 дней» |
| Таможня вернула посылку (статус 541–546 у ДоброПост) | Order → `CANCELLED + REFUND`. Менеджер должен закрыть DobroPost-возврат вручную через customer service |
| Customer передумал после `PROCURED` | Возврат **только после получения** (через RMA в last-mile, тема 9). До получения отказаться нельзя — товар уже выкуплен и едет |
| Customer хочет сменить ПВЗ во время cross-border | Можно: до создания Shipment #2 (status_id < 648 у DobroPost). После — нужно отдельно править у российского carrier'а через update-метод |
| Failed delivery в ПВЗ (срок хранения истёк) | Российский carrier шлёт return-to-sender event → reverse last-mile shipment → товар возвращается в РФ-склад → требуется возвратный cross-border (rare, обычно списание) |
| Passport validation failed (DaData webhook) | Order остаётся в `PROCURED`, но cross-border shipment **зависает** перед таможней. Customer service запрашивает корректные паспортные данные → `PUT /api/shipment` обновляет шипмент у ДоброПост |

### 16.6 Specific требования к Adapter-коду

```typescript
interface LoyalityShipmentChain {
  // Создаётся на event OrderProcured
  createCrossBorderLeg(order: Order, chineseTrackingNumber: string): Promise<DobroPostShipment>;

  // Создаётся на event CrossBorderArrived (status_id=648/649 от DobroPost)
  createLastMileLeg(
    order: Order,
    crossBorderShipment: DobroPostShipment,
    russianCarrier: CarrierAdapter
  ): Promise<RussianShipment>;

  // Customer-facing: показать всю цепочку треков
  getTrackingChain(orderId: OrderId): Promise<{
    chinese: string,         // incomingDeclaration
    crossBorder: string,     // dptrackNumber
    lastMile: string | null, // trackingNumber российского carrier'а (null до создания)
  }>;
}
```

Routing-engine для last-mile (§11.5) **не вызывается на checkout** в Loyality. Он вызывается на событии `CrossBorderArrived`:

```python
def select_last_mile_carrier(order: Order, dobropost_shipment: DobroPostShipment) -> Carrier:
    # 1. Customer preference (выбирал ПВЗ при checkout)
    if order.preferred_pickup_point.carrier:
        return order.preferred_pickup_point.carrier

    # 2. Routing по cost/SLA от российского склада ДоброПост
    return rate_shop_russian_carriers(
        from_address=dobropost_shipment.ru_warehouse_address,
        to_address=order.shipping_address,
        weight=dobropost_shipment.totalWeightKG,
    )
```

### 16.7 Anti-patterns специфичные для Loyality flow

| Anti-pattern | Почему плохо | Правильно |
|---|---|---|
| Создавать DobroPost shipment на checkout | Товар ещё не выкуплен, китайского трека нет — DobroPost откажет | Создание на event `OrderProcured` после ввода трека менеджером |
| Создавать last-mile shipment на checkout | До прибытия в РФ shipment не имеет смысла; carrier откажет (нет адреса забора) | Создание на event `CrossBorderArrived` (status 648/649 от ДоброПост) |
| Один объединённый Shipment с двумя trackingNumber | Нарушает «1 shipment = 1 tracking» (§15 в антипаттернах) | Два отдельных Shipment с явной связью `parentShipmentId` |
| Customer видит сырые статусы ДоброПост (`status_id=541`) | «Отказ в выпуске посылки по причине...» — не для customer'а | Canonical статусы в UI: «На таможне», «Доставлено в РФ», «В пути к ПВЗ» |
| Менеджер вручную создаёт last-mile shipment | Возможны ошибки + рассинхрон с автомат. routing | Auto-create на webhook event; менеджер только overrides ПВЗ если нужно |
| Полагаться только на DobroPost webhook без polling | Webhook может быть пропущен; cross-border 1–2 недели в пути | Nightly reconciliation: `GET /api/shipment?statusId=...` для всех shipments в активных статусах |
| Закрывать Order после `status_id=649` (передан партнёру РФ) | На этом этапе товар у российского carrier'а, ещё не доставлен | Order → `DELIVERED` только после webhook российского carrier'а с `delivered` |

---

## 17. Антипаттерны интеграции

| Антипаттерн | Описание | Правильно |
|---|---|---|
| Sync API call в checkout | "Сейчас создадим shipment у carrier'а" — checkout зависит от carrier latency | Async: confirm Order, then schedule shipment creation |
| Carrier-specific код в Order BC | `if order.carrier == 'cdek': cdek_api.create(...)` | Adapter pattern |
| Polling без webhook fallback | Periodic polling всех shipments каждые 5 min | Webhooks primary, polling backfill только |
| Shipment как child Order'а | `Order.shipments[]` как inner collection | Separate aggregate, id reference |
| Один FSM Order и Shipment | Order статус = Shipment статус | Two FSMs (как Shopify financial+fulfillment) |
| Direct save Shipment во время checkout | Создание Shipment атомарно с Order | OrderConfirmed event → async Shipment create |
| Carrier statuses в UI | "Status code 5" customer'у | Canonical mapping → human label |
| Один tracking number на N shipments | Re-use tracking для multiple parcels | Один shipment = один tracking |
| Игнорирование reverse shipments | "is_return webhook? skip" | Отдельный flow для returns |
| No idempotency на webhooks | Same webhook 5x → 5 status updates | Dedup by composite key |
| PDF labels хранятся в БД как BLOB | postgres bytea колонка | S3 / object storage с signed URL |
| Customer ждёт label generation | UX: "Печатаем... 30 sec spinner" | Async, label готов когда готов |
| Не reconcile с carrier | Trust webhooks 100% | Nightly reconciliation против carrier API |

---

## 18. Связь с другими темами

- **Тема 1 (E-commerce gigants)** — каждая платформа имеет встроенную интеграцию carriers (Shopify Shipping, Amazon FBA, Wildberries DBS).
- **Тема 2 (OMS)** — IBM Sterling/Manhattan имеют carrier integration модули как часть suite.
- **Тема 3 (DDD)** — Shipment BC и TrackingEvent aggregate — direct application Cargo Shipping example Эванса.
- **Тема 4 (FSM)** — Shipment FSM — отдельный, со своими transitions.
- **Тема 5 (Saga)** — CreateShipment — это step в checkout saga, после Pivot transaction.
- **Тема 9 (Returns)** — Reverse Shipment — central concept returns flow.

---

## 19. Чек-лист — production-grade Logistics integration

- [ ] Shipping BC отделён от Ordering BC, communication via id + events
- [ ] Order : Shipment = 1:N, не пытаться втиснуть в 1:1
- [ ] Shipment : Parcel = 1:N если нужен multi-piece support
- [ ] CarrierAdapter interface, по одному адаптеру per carrier
- [ ] ACL преобразует carrier-specific поля в canonical модель
- [ ] Canonical status taxonomy (DHL-style) определена
- [ ] Status mapping table per carrier
- [ ] TrackingEvent — отдельный aggregate (не child Shipment)
- [ ] Webhook endpoint per carrier с signature verification
- [ ] Webhook idempotency (composite natural keys)
- [ ] Webhook returns 2xx within 5s, async processing
- [ ] Polling fallback для carriers без webhooks (Почта России)
- [ ] Nightly reconciliation против carrier API
- [ ] Label generation async, PDFs хранятся в object storage
- [ ] Pickup point selection UI integrated
- [ ] Routing engine (по cost/SLA/coverage)
- [ ] Multi-carrier rate shopping
- [ ] Failover: если primary carrier down, route к secondary
- [ ] Returns: отдельный ReverseShipment, не модификация forward
- [ ] Customer-facing tracking page с canonical statuses
- [ ] Customer-facing tracking page с deep link на carrier site
- [ ] Tracking events stored с raw_payload (для debugging)
- [ ] Audit log всех carrier API calls (request + response)
- [ ] Carrier API rate limit handling (backoff, queue)
- [ ] Cross-border: customs declarations (CN22/CN23) auto-generated
- [ ] Cross-border CN→RU (ДоброПост): obligatory passport (4+6 chars) + ИНН ФЛ (12 chars) + китайский трек (`incomingDeclaration` <16) на стороне merchant
- [ ] Cross-border CN→RU: handle DaData passport-validation webhook отдельно от status-update webhook (две формы payload)
- [ ] JWT-based carrier (ДоброПост): background-refresh токена за ~1 час до истечения (TTL 12h) + lazy re-auth on 401
- [ ] Tracking page показывает dual track-numbers (китайский + российский) для cross-border заказов
- [ ] Multi-currency в carrier API: ДоброПост оперирует CNY — учитывать конверсию в Order BC

---

## 20. Источники

### CDEK / СДЭК

- **Локальная копия OpenAPI** (рабочая среда `https://api.cdek.ru`, тестовая `https://api.edu.cdek.ru`): `local_logistics/cdek_api/openapi.json` — полный протокол v2 с 35+ endpoint'ами, 9 типами вебхуков, статусной моделью (приложение 1), причинами недозвона, тарифами (приложение 4), доп. услугами (приложение 6).
- Apidoc СДЭК: <https://apidoc.cdek.ru/>
- Personal cabinet: <https://lk.cdek.ru/integration/index>
- Тестовая учётная запись (общая): `Account=wqGwiQx0gg8mLtiEKsUinjVSICCjtTEP`, `Secure password=RmAmgvSgSl1yirlz9QupbzOJVqhCxcP5`
- Сервис «Отслеживание» (Tracing): для доступа — запрос на `integrator@cdek.ru`
- CDEK SDK v2 (PHP) — AntistressStore
- CDEK API client (TypeScript) — shevernitskiy
- CdekSDK PHP — Read the Docs

### Yandex Delivery

- **Локальная копия документации API «Доставка в другой день»**: `local_logistics/yandex_delivery_api/markdown/` — `api.md`, `access.md`, `terminology.md`, `status_model.md`, `errors.md`, `ref.md` (35 методов), все детальные методы (`offers_create`, `offers_confirm`, `request_create`, `request_cancel`, `request_history`, `request_info_get`, `requests_info_post`, `request_actual_info`, `request_edit`, `request_edit_status`, `request_items_edit`, `request_items_remove`, `request_places_edit`, `pricing_calculator`, `offersinfo_*`, `pickup_points_list`, `location_detect`, `datetime_options`, `redelivery_options`, `generate_labels`, `handover_act`, `faq.md`)
- Базовый URL прода: <https://b2b-authproxy.taxi.yandex.net>
- Тестовый URL: <https://b2b.taxi.tst.yandex.net>
- Личный кабинет: <https://dostavka.yandex.ru/account>
- Поддержка: <https://yandex.com/support/delivery-profile/ru/api/other-day/troubleshooting>

### Почта России

- **Локальная копия документации Otpravka API**: `local_logistics/russian_post_api/markdown/` — 70+ файлов: `main.md`, `flow.md`, `authorization-token.md`, `authorization-key.md`, методы по группам (`orders-*`, `batches-*`, `sessions-*`, `documents-*`, `services-*`, `tss_tss-*`, `returns-*`, `archive-*`, `claims-*`, `nogroup-*`), `enums-all.md` (200+ enum'ов), use-cases (`usecases-*`).
- Базовый URL: <https://otpravka-api.pochta.ru>
- Tracking API: <https://tracking.pochta.ru>
- ЛК «Отправка»: <https://otpravka.pochta.ru>
- Russian Post SDK — lapaygroup GitHub
- Russian Post integration via ApiShip

### DPD

- DPD developer portal
- DPD Russia Tracking API — AfterShip
- DPD Russia Tracking API & Integration — TrackingMore
- DPD Tracking API — Ship24
- DPD courier integration for Shopify

### Boxberry

- Boxberry SDK (PHP) — iamwildtuna
- Boxberry Tracking API — TrackingMore
- Boxberry API — Shippo
- Boxberry — nopCommerce

### ДоброПост (DobroPost)

- **Локальная копия документации** (версия 2025-04-16): [`dobropost_shipment_api/README.md`](dobropost_shipment_api/README.md) — полный markdown-перевод PDF с описанием 5 endpoint'ов, webhook-форматов и справочника из 40 статусов.
- **Машиночитаемая OpenAPI 3.0 spec**: [`dobropost_shipment_api/openapi.json`](dobropost_shipment_api/openapi.json) — 13 component schemas (`SignInRequest`, `ShipmentRequest`, `ShipmentResponse`, `DeliveryTariff`, `Country`, `Currency`, `AmountUnits`, `ShipmentStatus`, `WebhookPassportPayload`, `WebhookStatusPayload` и др.), enum-список из 40 status id, Bearer JWT security scheme.
- **Исходный PDF**: `API Шипменты 16.04.2025.pdf` (внутренняя документация ДоброПост).
- Базовый URL: <https://api.dobropost.com>
- TTL JWT-токена: 12 часов.

### Multi-carrier aggregators

- EasyPost — Simple Shipping API
- EasyPost API Docs
- Shippo Multi-Carrier Shipping API
- Shippo vs EasyPost comparison
- Multi-Piece Shipment Support — Shippo blog
- ShipEngine vs EasyPost comparison
- 8 Best Multi-carrier shipping APIs — ELEX
- 10 Best Shipping APIs — ReachShip
- Ultimate Guide to Shipping APIs — ClickPost
- Best Unified API for Shipping — Unified.to

### Tracking / Status mapping

- DHL Shipment Tracking Unified API status codes
- DHL Shipment Tracking Unified API
- TrackingMore Multi-Carrier Tracking API
- ts-shipment-tracking — unified FedEx/UPS/USPS
- NetSuite Shipment Tracking Carrier Webhooks — Houseblend

### Order ID vs Tracking ID / Split shipment

- Order ID vs Tracking ID Number — TataNexarc
- Order ID and Tracking ID Differences — Bigship
- Order ID and Tracking ID Best Practices — NimbusPost
- What is Partial Shipment in Logistics — PackageX
- Split Shipment Tracking Guide — ParcelPanel

### Returns / RMA

- What is RMA — LoopReturns
- Return Material Authorization — Propel Glossary
- Return Labels — ShipEngine
- What Are RMA Labels — Sellercloud
- RMA Meaning — ReturnLogic
- What is RMA — R2 Logistics
- Returns RMA Reverse Logistics — SG Systems

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (1) Domain-Driven Design]] — Shipment как отдельный BC, TrackingEvent как aggregate
- [[Research - Order (2) State Machine FSM]] — Shipment FSM (отдельная от Order)
- [[Research - Order (3) E-commerce Giants]] — multi-shipment patterns Amazon/Shopify
- [[Research - Order (4) OMS Platforms]] — sourcing rules / ship-from-store
- [[Research - Order (7) Saga Pattern]] — pivot transaction (передача курьеру)
- [[Backend]] — backend dashboard, модуль `logistics`
- [[Loyality Project]]
