# 3.11. Создание заказа

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Создание заказа на ближайшее доступное время |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

> **Примечание:** Этот метод — упрощённая альтернатива двухшаговому flow `offers/create` → `offers/confirm`. Создаёт заказ сразу, без предварительного получения и выбора оффера.

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/create` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/create` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание |
|-----|-----|--------------|----------|
| `send_unix` | boolean | Нет | Формат времени (`true` — unix, `false` — utc) |

### Headers

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `Accept-Language` | string | Нет | Язык ответа | `ru` |

### Body

Тело запроса идентично методу [3.01. Создание заявки](yandex_delivery_other_day_offers_create.md) — те же 10 параметров и модели данных.

| Имя | Тип | Обязательный | Описание | Значение по умолчанию |
|-----|-----|--------------|----------|-----------------------|
| `info` | [RequestInfo](yandex_delivery_other_day_offers_create.md#requestinfo) | Да | Базовый набор метаданных по запросу | — |
| `source` | [SourceRequestNode](yandex_delivery_other_day_offers_create.md#sourcerequestnode) | Да | Информация о точке отправления заказа | — |
| `destination` | [DestinationRequestNode](yandex_delivery_other_day_offers_create.md#destinationrequestnode) | Да | Информация о точке получения заказа | — |
| `items` | [RequestResourceItem](yandex_delivery_other_day_offers_create.md#requestresourceitem)[] | Да | Информация о предметах в заказе. Min items: `1` | — |
| `places` | [ResourcePlace](yandex_delivery_other_day_offers_create.md#resourceplace)[] | Да | Информация о местах в заказе. Min items: `1` | — |
| `billing_info` | [BillingInfo](yandex_delivery_other_day_offers_create.md#billinginfo) | Да | Данные для биллинга | — |
| `recipient_info` | [Contact](yandex_delivery_other_day_offers_create.md#contact) | Да | Данные о получателе | — |
| `last_mile_policy` | [LastMilePolicy](yandex_delivery_other_day_offers_create.md#lastmilepolicy) | Да | Требуемый способ доставки | — |
| `particular_items_refuse` | boolean | Нет | Разрешен ли частичный выкуп | `false` |
| `forbid_unboxing` | boolean | Нет | Запрет на вскрытие транспортной упаковки | `false` |

> **Примечание:** Все модели данных (RequestInfo, PlatformStation, TimestampUNIX/UTC, TimeIntervalUTC, SourceRequestNode, LocationDetails, CustomLocation, DestinationRequestNode, ItemBillingDetails, ItemPhysicalDimensions, RequestResourceItem, PlacePhysicalDimensions, ResourcePlace, PaymentMethod, VariableDeliveryCostForRecipientItem, BillingInfo, Contact, LastMilePolicy) — идентичны описанным в методе [3.01](yandex_delivery_other_day_offers_create.md).

#### Пример тела запроса

```json
{
  "info": {
    "operator_request_id": "lKF4565ml",
    "merchant_id": "290587090cfc4943856851c8c3b2eebf",
    "comment": "Комментарий"
  },
  "source": {
    "platform_station": {
      "platform_id": "e1139f6d-e34f-47a9-a55f-31f032a861a6"
    },
    "interval_utc": {
      "from": "2021-10-25T15:00:00.000000Z",
      "to": "2021-10-25T15:00:00.000000Z"
    }
  },
  "destination": {
    "type": "platform_station",
    "platform_station": null,
    "custom_location": {
      "latitude": 0.5,
      "longitude": 0.5,
      "details": {
        "geoId": 213,
        "country": "Россия",
        "region": "Москва",
        "subRegion": "Московская область",
        "locality": "Москва",
        "street": "Пролетарский проспект",
        "house": "19",
        "housing": "1",
        "apartment": "2",
        "building": "1",
        "full_address": "Москва, Пролетарский проспект, 19",
        "postal_code": "123182"
      }
    },
    "interval_utc": null
  },
  "items": [
    {
      "count": 1,
      "name": "Духи",
      "article": "YS2-2022",
      "billing_details": {
        "inn": "9715386101",
        "nds": 22,
        "unit_price": 100,
        "assessed_unit_price": 100
      },
      "physical_dims": {
        "dx": 10,
        "dy": 15,
        "dz": 10,
        "predefined_volume": 20
      },
      "place_barcode": "Kia-01",
      "cargo_types": ["80"],
      "fitting": false
    }
  ],
  "places": [
    {
      "physical_dims": {
        "weight_gross": 100,
        "dx": 10,
        "dy": 10,
        "dz": 10
      },
      "barcode": "Kia-01"
    }
  ],
  "billing_info": {
    "payment_method": "already_paid",
    "delivery_cost": 0,
    "variable_delivery_cost_for_recipient": [
      {
        "min_cost_of_accepted_items": 1,
        "delivery_cost": 0
      }
    ]
  },
  "recipient_info": {
    "first_name": "Василий",
    "last_name": "Пупкин",
    "patronymic": "Михайлович",
    "phone": "+79529999999",
    "email": "pupkin@mail.ru"
  },
  "last_mile_policy": "time_interval",
  "particular_items_refuse": false,
  "forbid_unboxing": false
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `request_id` | string | Идентификатор только что созданного заказа | `77241d8009bb46d0bff5c65a73077bcd-udp` |

#### Пример ответа

```json
{
  "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp"
}
```

### 400 Bad Request

Нет доступных вариантов доставки.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `no_delivery_options` |
| `message` | string | Человекочитаемые детали ошибки | `No delivery options for interval` |

#### Пример ответа

```json
{
  "code": "no_delivery_options",
  "message": "No delivery options for interval"
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.10. Отмена заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcancel-post) |
| Следующая | 3.12. Редактирование грузомест заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestplacesedit-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcreate-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcreate-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Создание заказа
