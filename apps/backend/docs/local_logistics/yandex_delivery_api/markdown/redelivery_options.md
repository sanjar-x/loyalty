# 3.08. Получение интервалов доставки для нового места получения заказа

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение интервалов доставки для нового места получения заказа |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

> **Примечание:** Желаемые интервалы доставки в поле `destination.interval_utc` в этом методе игнорируются.

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/redelivery_options` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/redelivery_options` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Да | Идентификатор заказа | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `destination` | [DestinationRequestNode](#destinationrequestnode) | Да | Информация о новой точке получения заказа | — |

### DestinationRequestNode

Информация о точке получения (идентична модели из [3.01](yandex_delivery_other_day_offers_create.md#destinationrequestnode)).

| Имя | Тип | Описание | Допустимые значения |
|-----|-----|----------|---------------------|
| `type` | string | Тип целевой точки | `platform_station` — ПВЗ; `custom_location` — до двери |
| `platform_station` | [PlatformStation](yandex_delivery_other_day_offers_create.md#platformstation) | Станция платформы (для ПВЗ) | — |
| `custom_location` | [CustomLocation](yandex_delivery_other_day_offers_create.md#customlocation) | Произвольный адрес (для двери) | — |
| `interval_utc` | [TimeIntervalUTC](yandex_delivery_other_day_offers_create.md#timeintervalutc) | Временной интервал (игнорируется в этом методе) | — |

#### Пример тела запроса

```json
{
  "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp",
  "destination": {
    "type": "platform_station",
    "platform_station": {
      "platform_id": "e1139f6d-e34f-47a9-a55f-31f032a861a6"
    },
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
        "comment": "Станция метро Щукинская...",
        "full_address": "Москва, Пролетарский проспект, 19",
        "postal_code": "123182"
      }
    },
    "interval_utc": {
      "from": "2021-10-25T15:00:00.000000Z",
      "to": "2021-10-25T15:00:00.000000Z"
    }
  }
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание |
|-----|-----|----------|
| `options` | [TimeIntervalUTC](yandex_delivery_other_day_offers_create.md#timeintervalutc)[] | Возможные интервалы доставки для нового адреса |

#### Пример ответа

```json
{
  "options": [
    {
      "from": "2021-10-25T15:00:00.000000Z",
      "to": "2021-10-25T15:00:00.000000Z"
    }
  ]
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.07. Получение интервалов доставки для текущего места | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestdatetime_options-post) |
| Следующая | 3.09. История статусов заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesthistory-get) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestredelivery_options-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestredelivery_options-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Получение интервалов доставки для нового места
