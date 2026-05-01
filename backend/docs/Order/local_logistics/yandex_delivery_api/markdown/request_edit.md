# 3.06. Редактирование заказа

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Заявка на редактирование заказа |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/edit` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/edit` |

### Что можно редактировать

| Действие | Флаг в `available_actions` |
|----------|---------------------------|
| Данные получателя | `update_recipient` |
| Интервал доставки для точки Б (destination) | `update_dates_available` |
| Грузоместа (штрих-код коробки и ВГХ) | `update_places` |

> **Примечание:** Для редактирования сроков доставки необходимо сначала запросить доступные интервалы с помощью метода [Получение интервалов доставки](https://yandex.ru/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-post). Возможность редактирования определяется полем `available_actions` метода [3.03](yandex_delivery_other_day_request_info_get.md).

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Да | ID заказа | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `recipient_info` | [Contact](#contact) | Нет | Данные о получателе | — |
| `destination` | [DestinationRequestNode](#destinationrequestnode) | Нет | Информация о точке получения заказа | — |
| `places` | [EditPlace](#editplace)[] | Нет | Данные о грузоместах | — |

#### Пример тела запроса

```json
{
  "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp",
  "recipient_info": {
    "first_name": "Василий",
    "last_name": "Пупкин",
    "patronymic": "Михайлович",
    "phone": "+79529999999",
    "email": "pupkin@mail.ru"
  },
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
  },
  "places": [
    {
      "barcode": "Kia-01",
      "place": {
        "physical_dims": {
          "weight_gross": 100,
          "dx": 10,
          "dy": 10,
          "dz": 10
        },
        "barcode": "Kia-01"
      }
    }
  ]
}
```

---

## Модели данных

### Contact

Данные получателя (идентична модели из [3.01](yandex_delivery_other_day_offers_create.md#contact)).

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `first_name` | string | Имя | `Василий` |
| `last_name` | string | Фамилия | `Пупкин` |
| `patronymic` | string | Отчество | `Михайлович` |
| `phone` | string | Номер телефона | `+79529999999` |
| `email` | string | Адрес электронной почты | `pupkin@mail.ru` |

### DestinationRequestNode

Информация о точке получения (идентична модели из [3.01](yandex_delivery_other_day_offers_create.md#destinationrequestnode)).

| Имя | Тип | Описание | Допустимые значения |
|-----|-----|----------|---------------------|
| `type` | string | Тип целевой точки | `platform_station`, `custom_location` |
| `platform_station` | [PlatformStation](yandex_delivery_other_day_offers_create.md#platformstation) | Станция платформы (для ПВЗ) | — |
| `custom_location` | [CustomLocation](yandex_delivery_other_day_offers_create.md#customlocation) | Произвольный адрес (для двери) | — |
| `interval_utc` | [TimeIntervalUTC](yandex_delivery_other_day_offers_create.md#timeintervalutc) | Временной интервал (UTC) | — |

### EditPlace

Редактируемое грузоместо. **Уникальная модель для этого метода.**

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `barcode` | string | Старый штрихкод грузоместа (идентификатор для поиска) | `Kia-01` |
| `place` | [ResourcePlace](#resourceplace) | Новое грузоместо (замена) | — |

#### Пример

```json
{
  "barcode": "Kia-01",
  "place": {
    "physical_dims": {
      "weight_gross": 100,
      "dx": 10,
      "dy": 10,
      "dz": 10
    },
    "barcode": "Kia-01"
  }
}
```

### ResourcePlace

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `physical_dims` | [PlacePhysicalDimensions](yandex_delivery_other_day_offers_create.md#placephysicaldimensions) | Физические параметры места (вес, длина, высота, ширина) | — |
| `barcode` | string | Штрихкод коробки | `Kia-01` |

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `edit_id` | string | ID операции редактирования | `efb951b3280b4924b46b61a5db20df85` |

#### Пример ответа

```json
{
  "edit_id": "efb951b3280b4924b46b61a5db20df85"
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.05. Получение актуальной информации о доставке | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestactual_info-get) |
| Следующая | 3.07. Получение интервалов доставки для текущего места получения заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestdatetime_options-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestedit-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestedit-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Редактирование заказа
