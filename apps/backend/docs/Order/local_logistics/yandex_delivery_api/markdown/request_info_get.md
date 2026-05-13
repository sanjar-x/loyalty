# 3.03. Получение информации о заявке

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение информации о заявке и её текущем статусе |
| HTTP-метод | `GET` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/info` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/info` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Нет | ID заявки в логистической платформе | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `request_code` | string | Нет | Номер заказа в системе заказчика | `123bm` |
| `slim` | boolean | Нет | Флаг получения обновленной версии ответа | — |

> **Примечание:** Укажите `request_id` или `request_code` — один из двух параметров.

---

## Responses

### 200 OK

Успешный запрос.

#### Body (корневые поля)

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `request_id` | string | ID заказа в логистической платформе | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `request` | [BaseUserRequest](#baseuserrequest) + [AvailableActions](#availableactions) | Данные заказа с доступными действиями | — |
| `state` | [RequestState](#requeststate) | Текущий статус заказа | — |
| `full_items_price` | integer | Общая стоимость всех предметов в заказе | `0` |
| `sharing_url` | string | Ссылка на страницу с трекингом заказа для получателя | `https://dostavka.yandex.ru/route/ff60658e-...` |
| `courier_order_id` | string | Номер заказа в системе оператора | `786459112` |
| `self_pickup_node_code` | [SelfPickupNodeCode](#selfpickupnodecode) | Информация по коду получения | — |

---

## Модели данных (уникальные для этого метода)

### BaseUserRequest

Содержит полную копию данных заказа, аналогичную телу запроса метода [3.01. Создание заявки](yandex_delivery_other_day_offers_create.md). Включает:

| Имя | Тип | Описание |
|-----|-----|----------|
| `info` | [RequestInfo](#requestinfo) | Метаданные запроса |
| `source` | [SourceRequestNode](#sourcerequestnode) | Точка отправления |
| `destination` | [DestinationRequestNode](#destinationrequestnode) | Точка получения |
| `items` | [RequestResourceItem](#requestresourceitem)[] | Предметы в заказе |
| `places` | [ResourcePlace](#resourceplace)[] | Грузоместа |
| `billing_info` | [BillingInfo](#billinginfo) | Данные биллинга |
| `recipient_info` | [Contact](#contact) | Данные получателя |
| `last_mile_policy` | [LastMilePolicy](#lastmilepolicy) | Способ доставки |
| `particular_items_refuse` | boolean | Частичный выкуп |
| `forbid_unboxing` | boolean | Запрет вскрытия упаковки |
| `available_actions` | [AvailableActions](#availableactions) | Доступные изменения заказа |

> **Примечание:** Модели RequestInfo, PlatformStation, TimestampUNIX/UTC, TimeIntervalUTC, SourceRequestNode, LocationDetails, CustomLocation, DestinationRequestNode, ItemBillingDetails, ItemPhysicalDimensions, RequestResourceItem, PlacePhysicalDimensions, ResourcePlace, PaymentMethod, VariableDeliveryCostForRecipientItem, BillingInfo, Contact, LastMilePolicy — идентичны описанным в методе [3.01. Создание заявки](yandex_delivery_other_day_offers_create.md).

### AvailableActions

Доступные действия по изменению заказа.

| Имя | Тип | Описание |
|-----|-----|----------|
| `update_dates_available` | boolean | Доступность изменения даты доставки |
| `update_address_available` | boolean | Доступность изменения адреса доставки |
| `update_courier_to_pickup_available` | boolean | Доступность смены курьерской доставки на ПВЗ |
| `update_pickup_to_courier_available` | boolean | Доступность смены ПВЗ на курьерскую доставку |
| `update_pickup_to_pickup_available` | boolean | Доступность изменения пункта выдачи |
| `update_items` | boolean | Доступность изменения предметов в заказе |
| `update_recipient` | boolean | Доступность изменения данных получателя |
| `update_places` | boolean | Доступность изменения грузомест |

#### Пример

```json
{
  "update_dates_available": true,
  "update_address_available": true,
  "update_courier_to_pickup_available": true,
  "update_pickup_to_courier_available": true,
  "update_pickup_to_pickup_available": true,
  "update_items": true,
  "update_recipient": true,
  "update_places": true
}
```

### RequestState

Текущий статус заказа.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `status` | string | Статус заказа (см. [статусную модель](yandex_delivery_other_day_status_model.md)) | `CREATED` |
| `description` | string | Описание статуса | `Заказ создан в операторе` |
| `timestamp` | integer | Временная метка в формате UNIX | `1704056400` |
| `timestamp_utc` | string | Временная метка в формате UTC | `2021-10-25T15:00:00.000000Z` |
| `reason` | [CancelReason](#cancelreason) / [ChangeReason](#changereason) | Детальная причина события (отмены или переноса) | `SHOP_CANCELLED` |

#### Пример

```json
{
  "status": "CREATED",
  "description": "Заказ создан в операторе",
  "timestamp": 1704056400,
  "timestamp_utc": "2021-10-25T15:00:00.000000Z",
  "reason": "SHOP_CANCELLED"
}
```

### CancelReason / ChangeReason

Причина отмены или переноса заявки. Оба enum содержат одинаковый набор значений.

| Значение | Описание |
|----------|----------|
| `SHOP_CANCELLED` | Отправитель отменил заказ |
| `USER_CHANGED_MIND` | Покупатель передумал |
| `DELIVERY_PROBLEMS` | Возникли проблемы с доставкой |
| `ORDER_WAS_LOST` | Заказ был утерян |
| `ORDER_IS_DAMAGED` | Заказ был поврежден |
| `EXTRA_RESCHEDULING` | Заказ отменен из-за частых переносов |
| `BROKEN_ITEM` | Товар оказался бракованным |
| `DIMENSIONS_EXCEEDED` | Посылка слишком большая для способа доставки |
| `PICKUP_EXPIRED` | Срок хранения в пункте выдачи истек |
| `LAST_MILE_CHANGED_BY_USER` | Последняя миля изменена по инициативе пользователя |
| `CLIENT_REQUEST` | Получатель отменил заказ |
| `DELIVERY_DATE_UPDATED_BY_DELIVERY` | Задержка обработки заказа партнером |
| `DELIVERY_DATE_UPDATED_BY_SHOP` | По запросу от магазина |

### SelfPickupNodeCode

Информация по коду получения.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `type` | string | Тип кода | `pickup` |
| `code` | string | Код получения | `00000` |

#### Пример

```json
{
  "type": "pickup",
  "code": "00000"
}
```

---

## Пример полного ответа

```json
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
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.02. Подтверждение заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformoffersconfirm-post) |
| Следующая | 3.04. Получение информации о заявках во временном интервале | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestsinfo-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestinfo-get](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestinfo-get)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Получение информации о заявке
