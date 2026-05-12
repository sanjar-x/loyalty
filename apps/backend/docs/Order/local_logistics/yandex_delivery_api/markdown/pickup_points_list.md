# 2.02. Получение списка точек самопривоза и ПВЗ

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение списка точек самопривоза и самостоятельного получения заказа. Метод принимает пустое тело запроса — в этом случае вернутся все доступные точки самопривоза, ПВЗ и постаматы |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/pickup-points/list` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/pickup-points/list` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Значение по умолчанию | Допустимые значения |
|-----|-----|--------------|----------|-----------------------|---------------------|
| `pickup_point_ids` | string[] | Нет | Идентификаторы точек получения заказа | — | — |
| `geo_id` | integer | Нет | Идентификатор населенного пункта. Min value: `0` | — | — |
| `longitude` | [CoordinateInterval](#coordinateinterval) | Нет | Интервал для выбора всех объектов в отрезке по долготе | — | — |
| `latitude` | [CoordinateInterval](#coordinateinterval) | Нет | Интервал для выбора всех объектов в отрезке по широте | — | — |
| `type` | [PickupStationType](#pickupstationtype) | Нет | Тип точки приема/выдачи заказа | — | `pickup_point`, `terminal`, `warehouse` |
| `payment_method` | [PaymentMethod](#paymentmethod) | Нет | Тип оплаты в точке самостоятельного получения заказа | — | `already_paid`, `card_on_receipt`, `postpay` |
| `payment_methods` | [PaymentMethod](#paymentmethod)[] | Нет | Набор типов оплаты, которые должны быть доступны в точке получения заказа | — | `already_paid`, `card_on_receipt`, `postpay` |
| `available_for_dropoff` | boolean | Нет | Возможность отгрузки заказов в точку самопривоза. Для типа `warehouse` обязательно передавайте `true` | — | — |
| `is_yandex_branded` | boolean | Нет | Признак, брендированные ли ПВЗ | `false` | — |
| `is_not_branded_partner_station` | boolean | Нет | Признак, добавляющий партнерские ПВЗ | `false` | — |
| `operator_ids` | [OperatorId](#operatorid)[] | Нет | Фильтр по операторам ПВЗ. Если не указать, вернутся все пункты выдачи | — | `market_l4g`, `5post` |
| `pickup_services` | [PickupServices](#pickupservices) | Нет | Услуги с коробками/товарами, которые доступны на ПВЗ | — | — |

#### Пример тела запроса

```json
{
  "pickup_point_ids": "01946f4f013c7337874ec2fb848a58a4",
  "geo_id": 0,
  "longitude": {
    "from": 0.5,
    "to": 0.5
  },
  "latitude": null,
  "type": "pickup_point",
  "payment_method": "already_paid",
  "available_for_dropoff": true,
  "is_yandex_branded": false,
  "is_not_branded_partner_station": false,
  "payment_methods": [
    null
  ],
  "operator_ids": [
    "market_l4g",
    "5post"
  ],
  "pickup_services": {
    "is_fitting_allowed": true,
    "is_partial_refuse_allowed": true,
    "is_paperless_pickup_allowed": true,
    "is_unboxing_allowed": true
  }
}
```

---

## Модели данных (Request)

### CoordinateInterval

Интервал координат для геофильтрации.

| Имя | Тип | Описание |
|-----|-----|----------|
| `from` | number | Нижняя граница интервала |
| `to` | number | Верхняя граница интервала |

#### Пример

```json
{
  "from": 0.5,
  "to": 0.5
}
```

### PickupStationType

Тип точки приема/выдачи заказа.

| Значение | Описание |
|----------|----------|
| `pickup_point` | Пункт выдачи заказов |
| `terminal` | Постамат |
| `warehouse` | Сортировочный центр |

### PaymentMethod

Способ оплаты.

| Значение | Описание |
|----------|----------|
| `already_paid` | Уже оплачено |
| `card_on_receipt` | Оплата картой при получении |
| `postpay` | Постоплата |

### OperatorId

Идентификатор оператора ПВЗ.

| Значение | Описание |
|----------|----------|
| `market_l4g` | Пункты выдачи Яндекс Маркета и партнеров |
| `5post` | Пункты выдачи 5Post |

> **Примечание:** Если передать оба значения `["market_l4g", "5post"]` — появятся все пункты выдачи. Если передать только один — только соответствующие.

### PickupServices

Услуги, доступные на ПВЗ.

| Имя | Тип | Описание |
|-----|-----|----------|
| `is_fitting_allowed` | boolean | Разрешена ли примерка на ПВЗ |
| `is_partial_refuse_allowed` | boolean | Разрешен ли частичный выкуп на ПВЗ |
| `is_paperless_pickup_allowed` | boolean | Разрешена ли сдача без бумаг на ПВЗ |
| `is_unboxing_allowed` | boolean | Разрешено ли вскрытие транспортной упаковки |

#### Пример

```json
{
  "is_fitting_allowed": true,
  "is_partial_refuse_allowed": true,
  "is_paperless_pickup_allowed": true,
  "is_unboxing_allowed": true
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание |
|-----|-----|----------|
| `points` | [PickupStation](#pickupstation)[] | Массив точек самопривоза / ПВЗ / постаматов |

---

## Модели данных (Response)

### PickupStation

Точка забора/выдачи заказа.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `id` | string | Идентификатор точки. Используется при получении вариантов доставки в качестве конечной точки | `0198602de4a6749aba12e151bdf4caaa` |
| `operator_station_id` | string | Идентификатор точки в системе оператора | `10035218565` |
| `name` | string | Название точки забора заказа | `Пункт выдачи заказов Яндекс Маркета` |
| `type` | [PickupStationType](#pickupstationtype) | Тип точки | `pickup_point` |
| `position` | [GeoPoint](#geopoint) | Геокоординаты точки | — |
| `address` | [LocationDetails](#locationdetails) | Полный адрес точки забора заказа | — |
| `instruction` | string | Дополнительные указания, как добраться до точки | `Станция метро Щукинская...` |
| `payment_methods` | [PaymentMethod](#paymentmethod)[] | Возможные методы оплаты заказа при получении | `["already_paid"]` |
| `contact` | [StationContact](#stationcontact) | Данные для связи с точкой | — |
| `schedule` | [StationSchedule](#stationschedule) | Расписание работы точки | — |
| `is_yandex_branded` | boolean | Признак брендированного ПВЗ (default: `false`) | `false` |
| `is_market_partner` | boolean | Признак партнерского ПВЗ (default: `false`) | `false` |
| `is_dark_store` | boolean | Признак даркстора (default: `false`) | `false` |
| `pickup_services` | [PickupServices](#pickupservices) | Доступные услуги на ПВЗ | — |
| `deactivation_date` | string | Дата деактивации ПВЗ | `null` |
| `deactivation_date_predicted_debt` | string | Дата деактивации ПВЗ в случае неоплаты | `null` |
| `available_for_dropoff` | boolean | Доступен ли ПВЗ для сдачи юридическими лицами | `true` |
| `available_for_c2c_dropoff` | boolean | Доступен ли ПВЗ для сдачи физическими лицами | `true` |
| `dayoffs` | [DayOffs](#dayoffs)[] | Нерабочие дни ПВЗ | — |

### GeoPoint

Геокоординаты.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `latitude` | number | Широта | `55.666624` |
| `longitude` | number | Долгота | `37.51573` |

#### Пример

```json
{
  "latitude": 55.666624,
  "longitude": 37.51573
}
```

### LocationDetails

Адрес точки. Номер квартиры обязателен при наличии.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `geoId` | number | Идентификатор города | `213` |
| `country` | string | Страна | `Россия` |
| `region` | string | Регион | `Москва` |
| `subRegion` | string | Область | `Московская область` |
| `locality` | string | Населенный пункт | `Москва` |
| `street` | string | Улица | `Пролетарский проспект` |
| `house` | string | Номер дома | `19` |
| `housing` | string | Корпус | `1` |
| `building` | string | Строение | `1` |
| `apartment` | string | Номер квартиры | `2` |
| `comment` | string | Комментарий | `Станция метро Щукинская...` |
| `full_address` | string | Полный адрес | `Москва, Пролетарский проспект, 19` |
| `postal_code` | string | Индекс | `123182` |

#### Пример

```json
{
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
  "comment": "Станция метро Щукинская (4выход) второй дом слева...",
  "full_address": "Москва, Пролетарский проспект, 19",
  "postal_code": "123182"
}
```

### StationContact

Контактные данные точки.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `first_name` | string | Имя | `Василий` |
| `last_name` | string | Фамилия | `Пупкин` |
| `patronymic` | string | Отчество | `Михайлович` |
| `phone` | string | Номер телефона | `+74959999999` |
| `email` | string | Адрес электронной почты | `pupkin@mail.ru` |

#### Пример

```json
{
  "first_name": "Василий",
  "last_name": "Пупкин",
  "patronymic": "Михайлович",
  "phone": "+74959999999",
  "email": "pupkin@mail.ru"
}
```

### DayTime

Время дня.

| Имя | Тип | Описание | Ограничения |
|-----|-----|----------|-------------|
| `hours` | integer | Часы | Min: `0`, Max: `23` |
| `minutes` | integer | Минуты | Min: `0`, Max: `59` |

#### Пример

```json
{
  "hours": 0,
  "minutes": 0
}
```

### StationScheduleRestriction

Правило расписания работы.

| Имя | Тип | Описание |
|-----|-----|----------|
| `days` | integer[] | Номера дней недели (1 — понедельник, 2 — вторник, ..., 7 — воскресенье) |
| `time_from` | [DayTime](#daytime) | Время начала работы |
| `time_to` | [DayTime](#daytime) | Время окончания работы |

#### Пример

```json
{
  "days": [1],
  "time_from": {
    "hours": 0,
    "minutes": 0
  },
  "time_to": null
}
```

### StationSchedule

Расписание работы точки.

| Имя | Тип | Описание |
|-----|-----|----------|
| `time_zone` | integer | Часовая зона — смещение в часах относительно UTC |
| `restrictions` | [StationScheduleRestriction](#stationschedulerestriction)[] | Правила, задающие расписание работы |

#### Пример

```json
{
  "time_zone": 0,
  "restrictions": [
    {
      "days": [1],
      "time_from": {
        "hours": 0,
        "minutes": 0
      },
      "time_to": null
    }
  ]
}
```

### DayOffs

Нерабочие дни.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `date` | integer | Дата в формате UNIX | `1733356800` |
| `date_utc` | string | Дата в формате UTC | `2024-12-05T00:00:00+0000` |

#### Пример

```json
{
  "date": 1733356800,
  "date_utc": "2024-12-05T00:00:00+0000"
}
```

---

## Пример полного ответа

```json
{
  "points": [
    {
      "id": "0198602de4a6749aba12e151bdf4caaa",
      "operator_station_id": "10035218565",
      "name": "Пункт выдачи заказов Яндекс Маркета",
      "type": "pickup_point",
      "position": {
        "latitude": 55.666624,
        "longitude": 37.51573
      },
      "address": {
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
        "comment": "Станция метро Щукинская (4выход) второй дом слева...",
        "full_address": "Москва, Пролетарский проспект, 19",
        "postal_code": "123182"
      },
      "instruction": "Станция метро Щукинская (4выход) второй дом слева...",
      "payment_methods": ["already_paid"],
      "contact": {
        "first_name": "Василий",
        "last_name": "Пупкин",
        "patronymic": "Михайлович",
        "phone": "+74959999999",
        "email": "pupkin@mail.ru"
      },
      "schedule": {
        "time_zone": 0,
        "restrictions": [
          {
            "days": [1],
            "time_from": {"hours": 0, "minutes": 0},
            "time_to": null
          }
        ]
      },
      "is_yandex_branded": false,
      "is_market_partner": false,
      "is_dark_store": false,
      "pickup_services": {
        "is_fitting_allowed": true,
        "is_partial_refuse_allowed": true,
        "is_paperless_pickup_allowed": true,
        "is_unboxing_allowed": true
      },
      "deactivation_date": "null",
      "deactivation_date_predicted_debt": "null",
      "available_for_dropoff": true,
      "available_for_c2c_dropoff": true,
      "dayoffs": [
        {
          "date": 1733356800,
          "date_utc": "2024-12-05T00:00:00+0000"
        }
      ]
    }
  ]
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 2.01. Получение идентификатора населенного пункта | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformlocationdetect-post) |
| Следующая | 3.01. Создание заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformofferscreate-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformpickup-pointslist-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformpickup-pointslist-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 2. Точки самопривоза и ПВЗ > Получение списка точек самопривоза и ПВЗ
