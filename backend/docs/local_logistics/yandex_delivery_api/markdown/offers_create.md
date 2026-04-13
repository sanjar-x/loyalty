# 3.01. Создание заявки

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение вариантов доставки (офферов) для переданного заказа |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

> **Примечание:** При передаче нескольких идентичных товарных позиций необходимо передавать количество в параметре `count`. В противном случае в системе будет записано количество 1.

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/offers/create` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/offers/create` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание |
|-----|-----|--------------|----------|
| `send_unix` | boolean | Нет | Формат времени, в котором нужно отправить интервалы доставки (`true` — unix, `false` — utc) |

### Body

| Имя | Тип | Обязательный | Описание | Значение по умолчанию |
|-----|-----|--------------|----------|-----------------------|
| `info` | [RequestInfo](#requestinfo) | Да | Базовый набор метаданных по запросу | — |
| `source` | [SourceRequestNode](#sourcerequestnode) | Да | Информация о точке отправления заказа | — |
| `destination` | [DestinationRequestNode](#destinationrequestnode) | Да | Информация о точке получения заказа | — |
| `items` | [RequestResourceItem](#requestresourceitem)[] | Да | Информация о предметах в заказе. Min items: `1` | — |
| `places` | [ResourcePlace](#resourceplace)[] | Да | Информация о местах в заказе. Min items: `1` | — |
| `billing_info` | [BillingInfo](#billinginfo) | Да | Данные для биллинга | — |
| `recipient_info` | [Contact](#contact) | Да | Данные о получателе | — |
| `last_mile_policy` | [LastMilePolicy](#lastmilepolicy) | Да | Требуемый способ доставки | — |
| `particular_items_refuse` | boolean | Нет | Разрешен ли частичный выкуп (`true` — разрешен, `false` — недоступен) | `false` |
| `forbid_unboxing` | boolean | Нет | Запрет на вскрытие транспортной упаковки | `false` |

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
        "comment": "Станция метро Щукинская...",
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
      "marking_code": "0104640126996984...",
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

## Модели данных (Request)

### RequestInfo

Базовый набор метаданных по запросу.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `operator_request_id` | string | Идентификатор заказа у отправителя, должен быть уникальным | `lKF4565ml` |
| `merchant_id` | string | ID мерчанта-отправителя (доступен после регистрации через метод «Статус регистрации мерчанта») | `290587090cfc4943856851c8c3b2eebf` |
| `comment` | string | Опциональный комментарий | `Комментарий` |

### PlatformStation

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `platform_id` | string | Идентификатор станции в Логистической платформе (склад отгрузки или ПВЗ) | `e1139f6d-e34f-47a9-a55f-31f032a861a6` |

### TimestampUNIX

| Параметр | Значение |
|----------|----------|
| Тип | integer |
| Описание | Временная метка в формате UNIX |

### TimestampUTC

| Параметр | Значение |
|----------|----------|
| Тип | string |
| Описание | Временная метка в формате UTC |
| Пример | `2021-10-25T15:00:00.000000Z` |

### TimeIntervalUTC

Интервал времени в формате UTC.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `from` | TimestampUNIX / string | UTC timestamp для нижней границы интервала | `2021-10-25T15:00:00.000000Z` |
| `to` | TimestampUTC / string | UTC timestamp для верхней границы интервала | `2021-10-25T15:00:00.000000Z` |

### SourceRequestNode

Информация о точке отправления заказа.

| Имя | Тип | Описание |
|-----|-----|----------|
| `platform_station` | [PlatformStation](#platformstation) | Описание целевой станции, зарегистрированной в платформе |
| `interval_utc` | [TimeIntervalUTC](#timeintervalutc) | Временной интервал (в UTC) |

### LocationDetails

Адрес. Номер квартиры обязателен при наличии.

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

### CustomLocation

Информация о произвольной точке. Может быть задана координатами (`latitude`, `longitude`) или адресом.

| Имя | Тип | Описание |
|-----|-----|----------|
| `latitude` | number | Широта |
| `longitude` | number | Долгота |
| `details` | [LocationDetails](#locationdetails) | Дополнительная информация о расположении |

### DestinationRequestNode

Информация о точке получения заказа.

| Имя | Тип | Описание | Допустимые значения |
|-----|-----|----------|---------------------|
| `type` | string | Тип целевой точки | `platform_station` — доставка до ПВЗ; `custom_location` — доставка до двери |
| `platform_station` | [PlatformStation](#platformstation) | Описание целевой станции (для ПВЗ) | — |
| `custom_location` | [CustomLocation](#customlocation) | Полное описание целевого адреса (для двери) | — |
| `interval_utc` | [TimeIntervalUTC](#timeintervalutc) | Временной интервал (в UTC) | — |

### ItemBillingDetails

Данные по биллингу для предмета.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `inn` | string | ИНН | `9715386101` |
| `nds` | integer | Значение НДС. Допустимые значения: `0`, `5`, `7`, `10`, `22`. Без НДС: `-1` | `22` |
| `unit_price` | integer | Цена за единицу товара (в копейках) | `100` |
| `assessed_unit_price` | integer | Оценочная цена за единицу товара (в копейках) | `100` |

### ItemPhysicalDimensions

Физические параметры товара. Указываются либо габариты (`dx`, `dy`, `dz`), либо объем (`predefined_volume`).

| Имя | Тип | Единица измерения | Описание |
|-----|-----|-------------------|----------|
| `dx` | integer | сантиметры | Длина |
| `dy` | integer | сантиметры | Высота |
| `dz` | integer | сантиметры | Ширина |
| `predefined_volume` | integer | см³ | Объем |

### RequestResourceItem

Информация о предмете в заказе.

| Имя | Тип | Описание | Значение по умолчанию | Пример |
|-----|-----|----------|-----------------------|--------|
| `count` | integer | Количество | — | `1` |
| `name` | string | Название | — | `Духи` |
| `article` | string | Артикул | — | `YS2-2022` |
| `marking_code` | string | Код маркировки | — | `01046401269969842...` |
| `billing_details` | [ItemBillingDetails](#itembillingdetails) | Данные по биллингу | — | — |
| `physical_dims` | [ItemPhysicalDimensions](#itemphysicaldimensions) | Физические параметры | — | — |
| `place_barcode` | string | Штрихкод коробки, к которой относится товар | — | `Kia-01` |
| `cargo_types` | string[] | Типы товаров (напр. `["80"]` — ювелирное изделие). Min items: `1` | — | `["80"]` |
| `fitting` | boolean | Разрешена ли примерка товара. Если `particular_items_refuse=true`, то `fitting` также по умолчанию `true` | `false` | `false` |

### PlacePhysicalDimensions

Весогабаритные характеристики грузомест.

| Имя | Тип | Единица измерения | Описание |
|-----|-----|-------------------|----------|
| `weight_gross` | integer | граммы | Вес брутто |
| `dx` | integer | сантиметры | Длина |
| `dy` | integer | сантиметры | Высота |
| `dz` | integer | сантиметры | Ширина |

### ResourcePlace

Информация о месте в заказе.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `physical_dims` | [PlacePhysicalDimensions](#placephysicaldimensions) | Физические параметры места | — |
| `barcode` | string | Штрихкод коробки. По умолчанию подменяется на уникальный на стороне Яндекс Доставки. Для собственных штрихкодов обратитесь к менеджеру | `Kia-01` |

### PaymentMethod

| Значение | Описание |
|----------|----------|
| `already_paid` | Заказ уже оплачен |
| `card_on_receipt` | Оплата картой при получении (вкл. postpay) |
| `postpay` | Оплата картой при получении в приложении Go или по ссылке из СМС |

### VariableDeliveryCostForRecipientItem

| Имя | Тип | Описание | Ограничения |
|-----|-----|----------|-------------|
| `min_cost_of_accepted_items` | integer | Стоимость выкупленных товаров, при достижении которой применяется скидка | Min: `1` |
| `delivery_cost` | integer | Стоимость доставки после применения скидки (в копейках) | Min: `0` |

### BillingInfo

Данные для биллинга.

| Имя | Тип | Описание |
|-----|-----|----------|
| `payment_method` | [PaymentMethod](#paymentmethod) | Метод оплаты |
| `delivery_cost` | integer | Сумма, которую нужно взять с получателя за доставку (актуально для `card_on_receipt` / `postpay`) |
| `variable_delivery_cost_for_recipient` | [VariableDeliveryCostForRecipientItem](#variabledeliverycostforrecipientitem)[] | Список стоимостей доставки в зависимости от суммы выкупленных товаров (скидки, только для постоплаты с частичным выкупом) |

### Contact

Данные получателя.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `first_name` | string | Имя | `Василий` |
| `last_name` | string | Фамилия | `Пупкин` |
| `patronymic` | string | Отчество | `Михайлович` |
| `phone` | string | Номер телефона | `+79529999999` |
| `email` | string | Адрес электронной почты | `pupkin@mail.ru` |

### LastMilePolicy

Способ доставки последней мили.

| Значение | Описание |
|----------|----------|
| `time_interval` | Доставка до двери в указанный интервал |
| `self_pickup` | Доставка до пункта выдачи |

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание |
|-----|-----|----------|
| `offers` | [Offer](#offer)[] | Массив вариантов доставки (офферов). Min items: `1` |

### Offer

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `offer_id` | string | Идентификатор оффера | `c1b139dbd76b4ee3b39b19180b516119` |
| `expires_at` | TimestampUTC / TimestampUNIX | Timestamp окончания действия оффера (UTC) | `2021-10-25T15:00:00.000000Z` |
| `offer_details` | [OfferDetails](#offerdetails) | Подробности оффера | — |

### OfferDetails

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `delivery_interval` | [DeliveryIntervalUTC](#deliveryintervalutc) | Интервал доставки | — |
| `pickup_interval` | [PickupInterval](#pickupinterval) / [PickupIntervalUTC](#pickupintervalutc) | Интервал забора | — |
| `pricing` | string | Стоимость доставки с НДС | `192.15 RUB` |
| `pricing_commission_on_delivery_payment` | string | Процент комиссии | `2.2%` |
| `pricing_commission_on_delivery_payment_amount` | string | Сумма комиссии | `9.43 RUB` |
| `pricing_total` | string | Стоимость доставки с НДС и комиссией | `1400.96 RUB` |

### DeliveryIntervalUTC

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `min` | string | Нижняя граница интервала доставки (UTC) | `2021-10-25T15:00:00.000000Z` |
| `max` | string | Верхняя граница интервала доставки (UTC) | `2021-10-25T15:00:00.000000Z` |
| `policy` | [LastMilePolicy](#lastmilepolicy) | Политика доставки последней мили | `time_interval` |

### PickupInterval

| Имя | Тип | Описание |
|-----|-----|----------|
| `min` | integer | Нижняя граница интервала забора (UNIX Timestamp) |
| `max` | integer | Верхняя граница интервала забора (UNIX Timestamp) |

### PickupIntervalUTC

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `min` | string | Нижняя граница интервала забора (UTC) | `2021-10-25T15:00:00.000000Z` |
| `max` | string | Верхняя граница интервала забора (UTC) | `2021-10-25T15:00:00.000000Z` |

#### Пример ответа

```json
{
  "offers": [
    {
      "offer_id": "c1b139dbd76b4ee3b39b19180b516119",
      "expires_at": "2021-10-25T15:00:00.000000Z",
      "offer_details": {
        "delivery_interval": {
          "min": "2021-10-25T15:00:00.000000Z",
          "max": "2021-10-25T15:00:00.000000Z",
          "policy": "time_interval"
        },
        "pickup_interval": {
          "min": "2021-10-25T15:00:00.000000Z",
          "max": "2021-10-25T15:00:00.000000Z"
        },
        "pricing": "192.15 RUB",
        "pricing_commission_on_delivery_payment": "2.2%",
        "pricing_commission_on_delivery_payment_amount": "9.43 RUB",
        "pricing_total": "1400.96 RUB"
      }
    }
  ]
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
| Предыдущая | 2.02. Получение списка точек самопривоза и ПВЗ | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformpickup-pointslist-post) |
| Следующая | 3.02. Подтверждение заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformoffersconfirm-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformofferscreate-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformofferscreate-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Создание заявки
