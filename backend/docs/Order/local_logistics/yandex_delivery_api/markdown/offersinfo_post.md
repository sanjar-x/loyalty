# 1.03. Получение интервалов доставки #2

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение расписания вывозов в регионы. В качестве конечного пункта нужно указать либо `address` (строковый конечный адрес), либо `platform_station_id` (ID ПВЗ) |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/offers/info` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/offers/info` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание | Значение по умолчанию | Допустимые значения |
|-----|-----|--------------|----------|-----------------------|---------------------|
| `is_oversized` | boolean | Нет | Флаг КГТ (крупногабаритный товар) | — | — |
| `last_mile_policy` | [OffersInfoLastMilePolicy](#offersinfolastmilepolicy) | Нет | Требуемый способ доставки | `time_interval` | `time_interval` — доставка до двери в указанный интервал; `self_pickup` — доставка до пункта выдачи |
| `send_unix` | boolean | Нет | Формат в котором нужно отправить интервалы доставки (`true` — unix, `false` — utc) | — | — |

### Body

| Имя | Тип | Обязательный | Описание | Min items |
|-----|-----|--------------|----------|-----------|
| `source` | [OffersInfoSourceNode](#offersinfosourcenode) | Да | Информация о точке отправления заказа | — |
| `destination` | [OffersInfoDestinationNode](#offersinfodestinationnode) | Да | Информация о точке получения заказа. Заполните один из двух параметров | — |
| `places` | [OffersInfoResourcePlace](#offersinforesoурcеplace)[] | Да | Информация о местах в заказе | `1` |

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

### OffersInfoLastMilePolicy

Требуемый способ доставки.

| Параметр | Значение |
|----------|----------|
| Тип | string |
| По умолчанию | `time_interval` |

| Значение | Описание |
|----------|----------|
| `time_interval` | Доставка до двери в указанный интервал |
| `self_pickup` | Доставка до пункта выдачи |

### OffersInfoSourceNode

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

### OffersInfoDestinationNode

Информация о точке получения заказа. Заполните один из двух параметров.

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

### OffersInfoResourcePlace

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

| Имя | Тип | Описание | Min items |
|-----|-----|----------|-----------|
| `offers` | [OfferInfo](#offerinfo)[] | Массив доступных интервалов доставки | `0` |

### OfferInfo

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `from` | string | UTC время предлагаемого начала доставки | `2026-01-18T07:00:00.000000Z` |
| `to` | string | UTC время предлагаемого окончания доставки | `2026-01-18T15:00:00.000000Z` |

#### Пример ответа

```json
{
  "offers": [
    {
      "from": "2026-01-18T07:00:00.000000Z",
      "to": "2026-01-18T15:00:00.000000Z"
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
| Предыдущая | 1.02. Получение интервалов доставки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-get) |
| Следующая | 2.01. Получение идентификатора населенного пункта | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformlocationdetect-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 1. Подготовка заявки > Получение интервалов доставки #2
