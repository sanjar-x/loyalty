---
tags:
  - project/loyality
  - backend
  - logistics
  - dobropost
  - api
  - reference
type: reference
date: 2026-04-30
aliases: [DobroPost API Reference, ДоброПост API Reference]
cssclasses: [reference]
status: active
parent: "[[DobroPost Shipment API]]"
project: "[[Loyality Project]]"
component: backend
source: "API Шипменты 16.04.2025.pdf"
api_version: "2025-04-16"
---

# DobroPost API — Reference

> Дословный перевод спецификации ДоброПост («API Шипменты 16.04.2025.pdf») в Markdown. **Только то, что отдаёт сам ДоброПост** — Loyality-специфичные решения здесь сознательно отсутствуют (они в [`integration.md`](./integration.md)). Машиночитаемая копия — [`openapi.json`](./openapi.json).
>
> Если ДоброПост обновит PDF — заменяется только этот файл и `openapi.json`. Остальные документы (integration / status-codes / webhooks) — стабильные между версиями.

## Базовая информация

- **Production:** `https://api.dobropost.com`
- **Авторизация:** `Authorization: Bearer {token}`
- **Срок действия токена:** **12 часов**
- **Content-Type:** `application/json`

## Сводная таблица

| #   | Метод    | URL                              | Назначение                     | Auth   |
| --- | -------- | -------------------------------- | ------------------------------ | ------ |
| 1   | `POST`   | `/api/shipment/sign-in`          | Получение JWT-токена           | –      |
| 2   | `POST`   | `/api/shipment`                  | Создание Шипмента              | Bearer |
| 3   | `GET`    | `/api/shipment`                  | Получение списка Шипментов     | Bearer |
| 4   | `PUT`    | `/api/shipment`                  | Обновление Шипмента            | Bearer |
| 5   | `DELETE` | `/api/shipment/{id}`             | Удаление Шипмента              | Bearer |
| 6   | `POST`   | `https://yourdomain.com/webhook` | Webhook-уведомление от системы | –      |

---

## 1. Get Token — `POST /api/shipment/sign-in`

### Request

```json
{
  "email": "email",
  "password": "string"
}
```

### Response

```json
{
  "token": "string"
}
```

> Срок действия токена — **12 часов**.

---

## 2. Create Shipment — `POST /api/shipment`

### Headers

```http
Authorization: Bearer {token}
```

### Request

```json
{
  "totalAmount": 0,
  "consigneeFamilyName": "string",
  "consigneeMiddleName": "string",
  "consigneeName": "string",
  "consigneeBirthDate": "2024-12-17",
  "consigneePassportSerial": "string",
  "consigneePassportNumber": "string",
  "passportIssueDate": "2024-12-17",
  "vatIdentificationNumber": "string",
  "consigneeFullAddress": "string",
  "consigneeCity": "string",
  "consigneeState": "string",
  "consigneeZipCode": "string",
  "consigneePhoneNumber": "string",
  "consigneeEmail": "string",
  "itemDescription": "string",
  "numberOfItemPieces": 0,
  "itemPrice": 0,
  "itemStoreLink": "string",
  "dpTariffId": 0,
  "incomingDeclaration": "string",
  "comment": "string"
}
```

### Поля запроса

| Поле                      | Тип    |      Обяз.       | Описание / правила валидации                                              |
| ------------------------- | ------ | :--------------: | ------------------------------------------------------------------------- |
| `totalAmount`             | Number |        ✔         | Общая стоимость товаров Шипмента в юанях.                                 |
| `consigneeFamilyName`     | String |        ✔         | Фамилия получателя для таможни.                                           |
| `consigneeName`           | String |        ✔         | Имя получателя для таможни.                                               |
| `consigneeMiddleName`     | String |        –         | Отчество получателя.                                                      |
| `consigneeBirthDate`      | Date   | (✔ для DP Ultra) | Дата рождения. Обязательное **только для тарифа DP Ultra**.               |
| `consigneePassportSerial` | String |        ✔         | Серия паспорта. Длина — **ровно 4 символа**.                              |
| `consigneePassportNumber` | String |        ✔         | Номер паспорта. Длина — **ровно 6 символов**.                             |
| `passportIssueDate`       | Date   |        ✔         | Дата выдачи паспорта.                                                     |
| `vatIdentificationNumber` | String |        ✔         | ИНН получателя. Длина — **ровно 12 символов**.                            |
| `consigneeFullAddress`    | String |        ✔         | Полный адрес получателя для таможни.                                      |
| `consigneeCity`           | String |        ✔         | Город проживания получателя.                                              |
| `consigneeState`          | String |        ✔         | Область проживания получателя.                                            |
| `consigneeZipCode`        | String |        ✔         | Почтовый индекс адреса получателя.                                        |
| `consigneePhoneNumber`    | String |        ✔         | Номер телефона получателя.                                                |
| `consigneeEmail`          | String |        ✔         | Адрес электронной почты получателя.                                       |
| `itemDescription`         | String |        ✔         | Описание товара. Длина — **менее 60 символов**.                           |
| `numberOfItemPieces`      | Number |        ✔         | Количество единиц товара. Рекомендуется **не более 4 товаров**.           |
| `itemPrice`               | Number |        ✔         | Цена за одну единицу товара в юанях.                                      |
| `itemStoreLink`           | String |        ✔         | URL-адрес страницы товара.                                                |
| `dpTariffId`              | Number |        ✔         | Тариф доставки Шипмента.                                                  |
| `incomingDeclaration`     | String |        ✔         | Трек-номер Шипмента по Китаю. Длина — **менее 16 символов**.              |
| `comment`                 | String |        –         | Комментарий партнёра, отображается на этикетке. Длина — менее 60 символов. |

### Response

```json
{
  "id": 0,
  "totalAmount": 0,
  "currency": "string",
  "consigneeFamilyName": "string",
  "consigneeMiddleName": "string",
  "consigneeName": "string",
  "consigneeBirthDate": "2024-12-17",
  "consigneePassportSerial": "string",
  "consigneePassportNumber": "string",
  "passportIssueDate": "2024-12-17",
  "consigneeFullAddress": "string",
  "consigneeCity": "string",
  "consigneeState": "string",
  "consigneeZipCode": "string",
  "consigneePhoneNumber": "string",
  "consigneeEmail": "string",
  "itemDescription": "string",
  "numberOfItemPieces": 0,
  "itemPrice": 0,
  "itemWeight": 0,
  "itemStoreLink": "string",
  "statusDate": "2024-12-17T20:39:34.663Z",
  "deliveryTariff": {
    "id": 0,
    "measureQty": 0,
    "pricePerUnit": 0,
    "country": { "code": 0, "name": "string", "a2": "string", "a3": "string", "priority": 0 },
    "currency": { "code": 0, "ccy": "string", "base": true },
    "name": "string",
    "description": "string",
    "minTariffPerMeasureQty": 0,
    "startDate": "2024-12-17T20:39:34.663Z",
    "amountUnits": { "id": 0, "name": "string", "caption": "string" }
  },
  "status": { "id": 0, "name": "string" },
  "vatidentificationNumber": "string",
  "incomingDeclaration": "string",
  "dptrackNumber": "string"
}
```

### Дополнительные поля ответа

| Поле            | Тип    | Описание                                          |
| --------------- | ------ | ------------------------------------------------- |
| `id`            | Number | Уникальный идентификатор Шипмента в ДоброПост.    |
| `statusDate`    | Date   | Дата последнего обновления статуса (ISO 8601).    |
| `dptrackNumber` | String | Трек-номер ДоброПост для отслеживания Шипмента.   |
| `itemWeight`    | Number | Вес одной единицы товара в килограммах.           |
| `totalWeightKG` | Number | Общий вес Шипмента в килограммах.                 |

---

## 3. Get Shipments — `GET /api/shipment`

### Headers

```http
Authorization: Bearer {token}
```

### Query Parameters

| Параметр   | Тип    | Описание                                          |
| ---------- | ------ | ------------------------------------------------- |
| `page`     | Number | Номер страницы для постраничного отображения.     |
| `offset`   | Number | Количество записей, которые необходимо пропустить. |
| `statusId` | Number | Идентификатор статуса (см. [`status-codes.md`](./status-codes.md)). |

### Response

Структура отдельного элемента в `content[]` идентична ответу `POST /api/shipment` (см. раздел 2).

---

## 4. Update Shipment — `PUT /api/shipment`

### Headers

```http
Authorization: Bearer {token}
```

### Request

Структура идентична `POST /api/shipment`. **Идентификация Шипмента — по `incomingDeclaration`** (китайскому трек-номеру).

### Response

Структура идентична `POST /api/shipment`.

> **Loyality использует этот метод** только для исправления паспортных данных при `passportValidationStatus=false` — см. сценарий **Passport validation failed** в [`integration.md`](./integration.md#edge-cases).

---

## 5. Delete Shipment — `DELETE /api/shipment/{id}`

### Path Parameters

| Параметр | Тип    | Описание                          |
| -------- | ------ | --------------------------------- |
| `id`     | Number | Уникальный идентификатор Шипмента (поле `id` из ответа `POST`). |

### Headers

```http
Authorization: Bearer {token}
```

> **Loyality НЕ использует этот метод**: после успешного создания Shipment жизненный цикл управляется через статусы карьера. Удаление допустимо только до начала логистики (status_id ∈ {1, 2}); проще держать Order в `CANCELLED` локально.

---

## 6. Webhook — `POST {your_webhook_url}`

ДоброПост шлёт два формата с одинаковым URL — Loyality-side контракт и idempotency-стратегия описаны в [`webhooks.md`](./webhooks.md).

### Формат №1 — Passport validation

```json
{
  "shipmentId": 0,
  "statusDate": "string",
  "passportValidationStatus": true
}
```

| Поле                       | Тип     | Описание                                                  |
| -------------------------- | ------- | --------------------------------------------------------- |
| `shipmentId`               | Integer | DobroPost id Шипмента (поле `id` из ответа `POST`).       |
| `statusDate`               | String  | Дата и время обновления (ISO 8601, e.g. `2025-02-04T14:30:00Z`). |
| `passportValidationStatus` | Boolean | `true` — паспорт валиден, `false` — отклонён DaData.      |

### Формат №2 — Status update

```json
{
  "shipmentId": 0,
  "DPTrackNumber": "string",
  "statusDate": "string",
  "status": "string"
}
```

| Поле            | Тип     | Описание                                                       |
| --------------- | ------- | -------------------------------------------------------------- |
| `shipmentId`    | Integer | DobroPost id Шипмента.                                          |
| `DPTrackNumber` | String  | Тот же `dptrackNumber` из ответа создания.                      |
| `statusDate`    | String  | ISO 8601.                                                       |
| `status`        | String  | Текстовый статус (`В пути`, `Доставлено`, `Задерживается`...). |

> **Внимание:** ДоброПост передаёт `status` как **строку**, а не `status_id`. Loyality парсит строковое представление и матчит на `status_id` через справочник в [`status-codes.md`](./status-codes.md). Сохраняется raw `status` в `tracking_events.provider_status_name` для аудита.

### Ответы webhook'а

| Код                         | Семантика                                                                                                |
| --------------------------- | -------------------------------------------------------------------------------------------------------- |
| `200 OK`                    | Webhook принят. Тело пустое.                                                                              |
| `400 Bad Request`           | Отсутствуют обязательные поля или payload неверного формата. **ДоброПост ретраит** — Loyality этот код не возвращает (см. webhooks.md). |
| `401 Unauthorized`          | Подпись/секрет не прошёл валидацию.                                                                       |
| `500 Internal Server Error` | Серверная ошибка на стороне получателя.                                                                   |

---

## Связанное

- [[DobroPost Shipment API]] — index файлов в этой папке.
- [`integration.md`](./integration.md) — как ДоброПост встраивается в Loyality (FSM, 1:2 ratio, manager actions, edge-cases).
- [`status-codes.md`](./status-codes.md) — справочник 40 status_id + маппинг на `src.modules.logistics.domain.value_objects.TrackingStatus`.
- [`webhooks.md`](./webhooks.md) — webhook-контракт со стороны Loyality (signature, idempotency, retry-стратегия).
- [`openapi.json`](./openapi.json) — машиночитаемая OpenAPI 3.0-spec.
- [[Research - Order (6) Logistics Integration]] — общая архитектура Shipping BC; ДоброПост — один из adapter'ов.
