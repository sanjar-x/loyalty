---
tags:
  - project/loyality
  - backend
  - order
  - logistics
  - dobropost
  - api
  - reference
type: reference
date: 2026-04-30
aliases: [DobroPost API, ДоброПост Shipment API, Shipment API]
cssclasses: [reference]
status: active
parent: "[[Research - Order (6) Logistics Integration]]"
project: "[[Loyality Project]]"
component: backend
source: "API Шипменты 16.04.2025.pdf"
api_version: "2025-04-16"
---

# DobroPost Shipment API

> Markdown-перевод документации «API Шипменты 16.04.2025.pdf» (ДоброПост). Полный машиночитаемый OpenAPI 3.0-spec лежит рядом в [`openapi.json`](./openapi.json).

## Обзор

API ДоброПост (`https://api.dobropost.com`) предоставляет конечные точки для:

- авторизации и получения JWT-токена;
- управления Шипментами (создание, получение списка, обновление, удаление);
- получения webhook-уведомлений о валидации паспорта и обновлении статусов.

**Базовый URL:** `https://api.dobropost.com`

**Авторизация:** Bearer JWT в заголовке `Authorization: Bearer {token}`. Срок действия токена — **12 часов**.

## Сводная таблица методов

| # | Метод | URL | Назначение | Auth |
|---|-------|-----|------------|------|
| 1 | `POST` | `/api/shipment/sign-in` | Получение JWT-токена | – |
| 2 | `POST` | `/api/shipment` | Создание Шипмента | Bearer |
| 3 | `GET` | `/api/shipment` | Получение списка Шипментов | Bearer |
| 4 | `PUT` | `/api/shipment` | Обновление Шипмента | Bearer |
| 5 | `DELETE` | `/api/shipment/{id}` | Удаление Шипмента | Bearer |
| 6 | `POST` | `https://yourdomain.com/webhook` | Webhook-уведомление от ДоброПост на endpoint клиента | – |

---

## 1. Get Token

### Endpoint

- **URL:** `https://api.dobropost.com/api/shipment/sign-in`
- **Method:** `POST`

### Request Body

```json
{
  "email": "email",
  "password": "string"
}
```

### Response Body

```json
{
  "token": "string"
}
```

> **ПРИМЕЧАНИЕ:** Срок действия токена составляет **12 часов**.

---

## 2. Create Shipment

### Endpoint

- **URL:** `https://api.dobropost.com/api/shipment`
- **Method:** `POST`

### Request Headers

```http
Authorization: Bearer {token}
```

### Request Body

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

### Описание полей запроса

| Поле | Тип | Обяз. | Описание / правила валидации |
|------|-----|:-----:|------------------------------|
| `totalAmount` | Number | ✔ | Общая стоимость товаров Шипмента в юанях. Должно быть числовым значением. |
| `consigneeFamilyName` | String | ✔ | Фамилия получателя для таможни. Не должно быть пустым или нулевым. |
| `consigneeName` | String | ✔ | Имя получателя для таможни. Не должно быть пустым или нулевым. |
| `consigneeMiddleName` | String | – | Отчество получателя для таможни. Необязательное поле. |
| `consigneeBirthDate` | Date | (✔ для DP Ultra) | Дата рождения получателя. Обязательное **только для тарифа DP Ultra**. |
| `consigneePassportSerial` | String | ✔ | Серия паспорта получателя. Длина — **ровно 4 символа**. |
| `consigneePassportNumber` | String | ✔ | Номер паспорта получателя. Длина — **ровно 6 символов**. |
| `passportIssueDate` | Date | ✔ | Дата выдачи паспорта получателя. |
| `vatIdentificationNumber` | String | ✔ | ИНН получателя. Длина — **ровно 12 символов**. |
| `consigneeFullAddress` | String | ✔ | Полный адрес получателя для таможни. |
| `consigneeCity` | String | ✔ | Город проживания получателя для таможни. |
| `consigneeState` | String | ✔ | Область проживания получателя для таможни. |
| `consigneeZipCode` | String | ✔ | Почтовый индекс адреса получателя для таможни. |
| `consigneePhoneNumber` | String | ✔ | Номер телефона получателя для таможни. |
| `consigneeEmail` | String | ✔ | Адрес электронной почты получателя. Должен быть корректным email-адресом. |
| `itemDescription` | String | ✔ | Описание товара. Длина — **менее 60 символов**. |
| `numberOfItemPieces` | Number | ✔ | Количество единиц товара. Рекомендуется **не более 4 товаров**. |
| `itemPrice` | Number | ✔ | Цена за одну единицу товара в юанях. |
| `itemStoreLink` | String | ✔ | URL-адрес страницы товара. Должна быть корректной ссылкой (URL). |
| `dpTariffId` | Number | ✔ | Тариф доставки Шипмента. |
| `incomingDeclaration` | String | ✔ | Трек-номер Шипмента по Китаю. Длина — **менее 16 символов**. |
| `comment` | String | – | Комментарий партнёра, отображается на этикетке шипмента. Длина — **менее 60 символов**. |

### Response Body

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
    "country": {
      "code": 0,
      "name": "string",
      "a2": "string",
      "a3": "string",
      "priority": 0
    },
    "currency": {
      "code": 0,
      "ccy": "string",
      "base": true
    },
    "name": "string",
    "description": "string",
    "minTariffPerMeasureQty": 0,
    "startDate": "2024-12-17T20:39:34.663Z",
    "amountUnits": {
      "id": 0,
      "name": "string",
      "caption": "string"
    }
  },
  "status": {
    "id": 0,
    "name": "string"
  },
  "vatidentificationNumber": "string",
  "incomingDeclaration": "string",
  "dptrackNumber": "string"
}
```

### Описание полей ответа (дополнительно к запросу)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Number | Уникальный идентификатор Шипмента. |
| `statusDate` | Date | Дата последнего обновления статуса (ISO 8601). |
| `dptrackNumber` | String | Трек-номер ДоброПост для отслеживания Шипмента. |
| `itemWeight` | Number | Вес одной единицы товара в килограммах. |
| `totalWeightKG` | Number | Общий вес Шипмента в килограммах. |

---

## 3. Get Shipments

### Endpoint

- **URL:** `https://api.dobropost.com/api/shipment`
- **Method:** `GET`

### Request Headers

```http
Authorization: Bearer {token}
```

### Query Parameters

| Параметр | Тип | Описание |
|----------|-----|----------|
| `page` | Number | Номер страницы для постраничного отображения. |
| `offset` | Number | Количество записей, которые необходимо пропустить для постраничного отображения. |
| `statusId` | Number | Идентификатор статуса отправления (см. справочник ниже). |

### Response Body

Обратитесь к ответу **Create Shipment** для получения подробной структуры отдельных отправлений в массиве `content`.

---

## 4. Update Shipment

### Endpoint

- **URL:** `https://api.dobropost.com/api/shipment`
- **Method:** `PUT`

### Request Headers

```http
Authorization: Bearer {token}
```

### Request Body

Структура идентична `POST /api/shipment` (см. раздел 2). Тело:

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

### Response Body

Обратитесь к ответу **Create Shipment** для получения подробной структуры.

---

## 5. Delete Shipment

### Endpoint

- **URL:** `https://api.dobropost.com/api/shipment/{id}`
- **Method:** `DELETE`

### Path Parameters

| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | Number | Уникальный идентификатор Шипмента. |

### Request Headers

```http
Authorization: Bearer {token}
```

---

## 6. Webhook API

### Обзор

Webhook-конечная точка используется для получения уведомлений о доставке. В зависимости от события может иметь одну из двух структур:

1. **Проверка актуальности паспорта** по базе данных DaData.
2. **Обновление статуса Шипмента**.

### Детали конечной точки

- **URL:** `https://yourdomain.com/webhook`
  *(Замените на фактический URL вашей конечной точки.)*
- **Метод:** `POST`
- **Content-Type:** `application/json`

### Формат полезной нагрузки № 1 — Проверка паспорта

Используется при обновлении статуса проверки паспорта Шипмента.

```json
{
  "shipmentId": 0,
  "statusDate": "string",
  "passportValidationStatus": true
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `shipmentId` | Integer | Уникальный идентификатор отправления. |
| `statusDate` | String | Дата и время обновления статуса. Формат ISO 8601 (например, `2025-02-04T14:30:00Z`). |
| `passportValidationStatus` | Boolean | Прошёл ли паспорт проверку: `true` — да, `false` — нет. |

### Формат полезной нагрузки № 2 — Обновление статуса отправления

Используется при общем обновлении статуса отправления.

```json
{
  "shipmentId": 0,
  "DPTrackNumber": "string",
  "statusDate": "string",
  "status": "string"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `shipmentId` | Integer | Уникальный идентификатор Шипмента. |
| `DPTrackNumber` | String | Номер отслеживания, предоставленный ДоброПост. |
| `statusDate` | String | Дата и время обновления статуса. Формат ISO 8601. |
| `status` | String | Текстовое представление текущего статуса (например, `В пути`, `Доставлено`, `Задерживается`). |

### Ответы

**Успешный ответ:**
Конечная точка webhook возвращает `200 OK` с пустым телом при успешном получении и обработке запроса.

**Ответы при ошибках:**

| Код | Когда возвращается |
|-----|---------------------|
| `400 Bad Request` | В запросе отсутствуют обязательные поля или запрос неправильного формата. |
| `401 Unauthorized` | Токен не прошёл валидацию. |
| `500 Internal Server Error` | На стороне сервера произошла непредвиденная ошибка. |

---

## Список статусов

Полный справочник статусов Шипмента (поле `status.id` в ответе API и фильтр `?statusId=` в `GET /api/shipment`). Всего **40 статусов** в 4 логических группах.

### Базовая логистическая цепочка (9)

| id | Название |
|----|----------|
| 1 | Ожидается на складе |
| 2 | Получен от курьера |
| 3 | Обработан на складе |
| 4 | Добавлен в мешок |
| 5 | Добавлен в реестр |
| 6 | Покинул склад в Китае |
| 7 | Поступил на таможню в Китае |
| 8 | Поступил на таможню в России |
| 9 | Передан партнеру |

### Редактирование данных посылки (3)

| id | Название |
|----|----------|
| 270 | Запрос на редактирование данных посылки |
| 271 | Запрос на редактирование данных посылки отклонен |
| 272 | Произведено редактирование данных посылки |

### Таможенное оформление (19)

| id | Название |
|----|----------|
| 500 | Начало таможенного оформления |
| 510 | Требуется уплатить таможенные пошлины |
| 520 | Выпуск товаров без уплаты таможенных платежей |
| 521 | Выпуск товаров без уплаты таможенных платежей |
| 530 | Выпуск товаров (таможенные платежи уплачены) |
| 531 | Требуется уплатить таможенные пошлины |
| 532 | Выпуск товаров (таможенные платежи уплачены) |
| 540 | Ожидание обязательной оплаты таможенной пошлины |
| 541 | Отказ в выпуске посылки по причине признания партии коммерческой или не относящейся к товарам для личного пользования |
| 542 | Отказ в выпуске посылки в связи с отсутствием необходимых документов для целей таможенного контроля либо отсутствием документов, подтверждающих оплату таможенной пошлины |
| 543 | Отказ в выпуске посылки по причине некорректного заполнения информации о характеристиках товара |
| 544 | Отказ в выпуске посылки по причине отсутствия корректных паспортных данных |
| 545 | Отказ в выпуске посылки по причине отсутствия заявленных паспортных данных в списке достоверных паспортов |
| 546 | Отказ в выпуске посылки по другим причинам |
| 570 | Продление времени обработки |
| 591 | Начало таможенного оформления |
| 600 | Посылка не пришла |
| 648 | Подготовлено к отгрузке в доставку последней мили |
| 649 | Покинула таможню и передана на доставку по РФ |

### Развёрнутые отказы — с кодами причин (9)

| id | Название |
|----|----------|
| 590204 | Отказ в выпуске товаров с указанием кода причины отказа |
| 590401 | Отказ в выпуске товаров с указанием кода причины отказа |
| 590404 | Отказ в выпуске товаров с указанием кода причины отказа. Не представлены документы и сведения |
| 590405 | Отказ в выпуске товаров с указанием кода причины отказа |
| 590409 | Отказ в выпуске товаров с указанием кода причины отказа |
| 590410 | Отказ в выпуске товаров с указанием кода причины отказа. товар входит в перечень категорий товаров |
| 590413 | Отказ в выпуске товаров с указанием кода причины отказа. Не подана корректировка пп.2 п.1 ст.125 ТК ЕАЭС. |
| 590420 | Отказ в выпуске товаров с указанием кода причины отказа |
| 590592 | Отказ в выпуске товаров с указанием кода причины отказа. |

---

## Связанное

- [[Research - Order (6) Logistics Integration]] — общая архитектура интеграции с курьерскими сервисами; ДоброПост рассматривается как один из adapter'ов в Shipping BC.
- [[Research - Order (2) State Machine FSM]] — справочник статусов выше — это enum для FSM Shipment с раздельной нумерацией для логистики, редактирования и таможни.
- [[Research - Order (5) Payment Integration]] — webhook-паттерн (signature verification, idempotency, 2xx within 20s) применим и к webhook'ам ДоброПост.
- Файл рядом: [`openapi.json`](./openapi.json) — машиночитаемая OpenAPI 3.0-spec; можно открыть в Swagger Editor / Stoplight / Postman для генерации клиентов.
- Источник: «API Шипменты 16.04.2025.pdf» (исходный PDF лежит на уровень выше в той же папке).
