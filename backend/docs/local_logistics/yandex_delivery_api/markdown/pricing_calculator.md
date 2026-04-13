# 1.01. Предварительная оценка стоимости доставки

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Расчет стоимости доставки на основании переданных параметров заказа |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/pricing-calculator` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/pricing-calculator` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание |
|-----|-----|--------------|----------|
| `is_oversized` | boolean | Нет | Флаг КГТ (крупногабаритный товар) |

### Body

| Имя | Тип | Обязательный | Описание | Значение по умолчанию | Допустимые значения |
|-----|-----|--------------|----------|-----------------------|---------------------|
| `source` | [PricingSourceNode](#pricingsourcenode) | Да | Информация о точке отправления заказа | — | — |
| `destination` | [PricingDestinationNode](#pricingdestinationnode) | Да | Информация о точке получения заказа. В объекте два параметра — заполните один из них | — | — |
| `tariff` | string | Да | Тариф доставки | — | `time_interval` — доставка до двери в интервал; `self_pickup` — доставка до ПВЗ |
| `total_weight` | integer | Да | Суммарный вес посылки в граммах | — | — |
| `total_assessed_price` | integer | Нет | Суммарная оценочная стоимость посылок в копейках | `0` | — |
| `client_price` | integer | Нет | Сумма к оплате с получателя в копейках | `0` | — |
| `payment_method` | string | Нет | Способ оплаты товаров | `already_paid` | `already_paid` — уже оплачено; `card_on_receipt` — оплата картой при получении |
| `places` | [PricingResourcePlace](#pricingresourceplace)[] | Нет | Информация о местах в заказе. Min items: `0` | — | — |

#### Пример тела запроса

```json
{
  "source": {
    "platform_station_id": "fbed3aa1-2cc6-4370-ab4d-59c5cc9bb924"
  },
  "destination": {
    "platform_station_id": "e1139f6d-e34f-47a9-a55f-31f032a861a6",
    "address": "Санкт-Петербург, Большая Монетная улица, 1к1А"
  },
  "tariff": "time_interval",
  "total_weight": 0,
  "total_assessed_price": 0,
  "client_price": 0,
  "payment_method": "already_paid",
  "places": [
    {
      "physical_dims": {
        "weight_gross": 100,
        "dx": 10,
        "dy": 10,
        "dz": 10
      }
    }
  ]
}
```

---

## Модели данных

### PricingSourceNode

Информация о точке отправления заказа.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `platform_station_id` | string | ID склада отправки, зарегистрированного в платформе | `fbed3aa1-2cc6-4370-ab4d-59c5cc9bb924` |

#### Пример

```json
{
  "platform_station_id": "fbed3aa1-2cc6-4370-ab4d-59c5cc9bb924"
}
```

### PricingDestinationNode

Информация о точке получения заказа. В объекте два параметра — заполните один из них.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `address` | string | Адрес получения с указанием города, улицы и номера дома. Номер квартиры, подъезда и этаж указывать не нужно | `Санкт-Петербург, Большая Монетная улица, 1к1А` |
| `platform_station_id` | string | ID ПВЗ или постамата, зарегистрированного в платформе, в который нужна доставка | `e1139f6d-e34f-47a9-a55f-31f032a861a6` |

#### Пример

```json
{
  "platform_station_id": "e1139f6d-e34f-47a9-a55f-31f032a861a6",
  "address": "Санкт-Петербург, Большая Монетная улица, 1к1А"
}
```

### PlacePhysicalDimensions

Весогабаритные характеристики грузомест.

| Имя | Тип | Единица измерения | Описание |
|-----|-----|-------------------|----------|
| `weight_gross` | integer | граммы | Вес брутто |
| `dx` | integer | сантиметры | Длина |
| `dy` | integer | сантиметры | Высота |
| `dz` | integer | сантиметры | Ширина |

#### Пример

```json
{
  "weight_gross": 100,
  "dx": 10,
  "dy": 10,
  "dz": 10
}
```

### PricingResourcePlace

Информация о месте в заказе.

| Имя | Тип | Описание |
|-----|-----|----------|
| `physical_dims` | [PlacePhysicalDimensions](#placephysicaldimensions) | Физические параметры места. Весогабаритные характеристики грузомест |

#### Пример

```json
{
  "physical_dims": {
    "weight_gross": 100,
    "dx": 10,
    "dy": 10,
    "dz": 10
  }
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `pricing_total` | string | Суммарная стоимость доставки с учетом дополнительных услуг (с НДС) | `225.7 RUB` |
| `delivery_days` | integer | Расчетное количество дней доставки | `7` |

#### Пример ответа

```json
{
  "pricing_total": "225.7 RUB",
  "delivery_days": 7
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | Список методов | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/) |
| Следующая | 1.02. Получение интервалов доставки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-get) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformpricing-calculator-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformpricing-calculator-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 1. Подготовка заявки > Предварительная оценка стоимости доставки
