# 1.02. Получение интервалов доставки

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение расписания вывозов в регионы. В качестве конечного пункта нужно указать либо `full_address` (строковый конечный адрес), либо `self_pickup_id` (ID ПВЗ) |
| HTTP-метод | `GET` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/offers/info` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/offers/info` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание | Значение по умолчанию | Допустимые значения | Пример |
|-----|-----|--------------|----------|-----------------------|---------------------|--------|
| `station_id` | string | Да | ID станции (склада) отгрузки | — | — | `fbed3aa1-2cc6-4370-ab4d-59c5cc9bb924` |
| `full_address` | string | Нет | Полный адрес с указанием города, улицы и номера дома. Номер квартиры, подъезда и этаж указывать не нужно | — | — | `Санкт-Петербург, Большая Монетная улица, 1к1А` |
| `self_pickup_id` | string | Нет | ID ПВЗ в логплатформе | — | — | `01946f4f013c7337874ec2fb848a58a4` |
| `last_mile_policy` | [OffersInfoLastMilePolicy](#offersинfolaлstmilepolicy) | Нет | Требуемый способ доставки | `time_interval` | `time_interval` — доставка до двери в указанный интервал; `self_pickup` — доставка до пункта выдачи | — |
| `is_oversized` | boolean | Нет | Флаг КГТ (крупногабаритный товар) | — | — | — |
| `send_unix` | boolean | Нет | Формат в котором нужно отправить интервалы доставки (`true` — unix, `false` — utc) | — | — | — |

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

### OfferInfo

Информация об интервале доставки.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `from` | string | UTC время предлагаемого начала доставки | `2026-01-18T07:00:00.000000Z` |
| `to` | string | UTC время предлагаемого окончания доставки | `2026-01-18T15:00:00.000000Z` |

#### Пример

```json
{
  "from": "2026-01-18T07:00:00.000000Z",
  "to": "2026-01-18T15:00:00.000000Z"
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание |
|-----|-----|----------|
| `offers` | [OfferInfo](#offerinfo)[] | Массив доступных интервалов доставки. Min items: `0` |

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
| Предыдущая | 1.01. Предварительная оценка стоимости доставки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformpricing-calculator-post) |
| Следующая | 1.03. Получение интервалов доставки #2 | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-get](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-get)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 1. Подготовка заявки > Получение интервалов доставки
