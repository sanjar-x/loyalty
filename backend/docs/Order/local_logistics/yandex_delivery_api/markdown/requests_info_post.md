# 3.04. Получение информации о заявках во временном интервале

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение информации о заявках, созданных в заданный временной интервал |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/requests/info` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/requests/info` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `from` | TimestampUTC / TimestampUNIX | Нет | Начало временного интервала создания заказов | `2021-10-25T15:00:00.000000Z` |
| `to` | TimestampUTC / TimestampUNIX | Нет | Конец временного интервала создания заказов | `2021-10-25T15:00:00.000000Z` |
| `request_ids` | string[] | Нет | Список идентификаторов заказов | `["77241d8009bb46d0bff5c65a73077bcd-udp"]` |

#### Пример тела запроса

```json
{
  "from": "2021-10-25T15:00:00.000000Z",
  "to": null,
  "request_ids": "77241d8009bb46d0bff5c65a73077bcd-udp"
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание |
|-----|-----|----------|
| `requests` | [RequestReport](#requestreport)[] | Массив заявок |

### RequestReport

Каждый элемент массива `requests` содержит полную информацию о заказе — идентичную ответу метода [3.03. Получение информации о заявке](yandex_delivery_other_day_request_info_get.md).

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `request_id` | string | ID заказа в логистической платформе | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `request` | [BaseUserRequest](yandex_delivery_other_day_offers_create.md) + [AvailableActions](yandex_delivery_other_day_request_info_get.md#availableactions) | Данные заказа с доступными действиями | — |
| `state` | [RequestState](yandex_delivery_other_day_request_info_get.md#requeststate) | Текущий статус заказа | — |
| `full_items_price` | integer | Общая стоимость всех предметов в заказе | `0` |
| `sharing_url` | string | Ссылка на трекинг заказа | `https://dostavka.yandex.ru/route/ff60658e-...` |
| `courier_order_id` | string | Номер заказа в системе оператора | `786459112` |
| `self_pickup_node_code` | [SelfPickupNodeCode](yandex_delivery_other_day_request_info_get.md#selfpickupnodecode) | Информация по коду получения | — |

> **Примечание:** Все вложенные модели (RequestInfo, SourceRequestNode, DestinationRequestNode, items, places, billing_info, recipient_info, AvailableActions, RequestState, CancelReason/ChangeReason, SelfPickupNodeCode) — идентичны описанным в методах [3.01](yandex_delivery_other_day_offers_create.md) и [3.03](yandex_delivery_other_day_request_info_get.md).

#### Пример ответа

```json
{
  "requests": [
    {
      "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp",
      "request": {
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
            "details": {}
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
        "forbid_unboxing": false,
        "available_actions": {
          "update_dates_available": true,
          "update_address_available": true,
          "update_courier_to_pickup_available": true,
          "update_pickup_to_courier_available": true,
          "update_pickup_to_pickup_available": true,
          "update_items": true,
          "update_recipient": true,
          "update_places": true
        }
      },
      "state": {
        "status": "CREATED",
        "description": "Заказ создан в операторе",
        "timestamp": 1704056400,
        "timestamp_utc": "2021-10-25T15:00:00.000000Z",
        "reason": "SHOP_CANCELLED"
      },
      "full_items_price": 0,
      "sharing_url": "https://dostavka.yandex.ru/route/ff60658e-d0f6-44bf-a22b-a77b08949e86",
      "courier_order_id": "786459112",
      "self_pickup_node_code": {
        "type": "pickup",
        "code": "00000"
      }
    }
  ]
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.03. Получение информации о заявке | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestinfo-get) |
| Следующая | 3.05. Получение актуальной информации о доставке | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestactual_info-get) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestsinfo-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestsinfo-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Получение информации о заявках во временном интервале
