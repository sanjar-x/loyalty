# 3.12. Редактирование грузомест заказа

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Создание заявки на редактирование грузомест заказа |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

> **Примечание:** Принимает полный набор новых коробок с товарами внутри. Позволяет как удалить, так и добавить новое грузоместо. Если товары в заказе и запросе не совпадут, редактирование завершится с ошибкой.

> **Асинхронная операция:** Редактирование происходит асинхронно. Для проверки статуса используйте метод [3.13. Получение статуса запроса на редактирование](yandex_delivery_other_day_request_edit_status.md) `/api/b2b/platform/request/edit/status`.

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/places/edit` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/places/edit` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Да | Идентификатор заказа в системе | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `places` | [PlacesEditRequestPlace](#placeseditrequeстplace) | Да | Информация о местах в заказе | — |

#### Пример тела запроса

```json
{
  "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp",
  "places": {
    "dimensions": {
      "weight_gross": 1,
      "dx": 1,
      "dy": 1,
      "dz": 1
    },
    "barcode": "Kia-01",
    "items": [
      {
        "count": 0,
        "item_barcode": "9f210a050a7282f353d9ab9ac9e27cb4"
      }
    ]
  }
}
```

---

## Модели данных

### PlacesEditRequestPlace

Грузоместо с товарами.

> **Примечание:** По умолчанию штрихкод грузоместа подменяется на уникальный на стороне Яндекс Доставки. Для собственных штрихкодов обратитесь к менеджеру. Актуальные штрихкоды — через метод [3.03](yandex_delivery_other_day_request_info_get.md).

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `barcode` | string | Штрихкод коробки | `Kia-01` |
| `dimensions` | [PlaceDimensions](#placedimensions) | Физические параметры места | — |
| `items` | [PlacesEditRequestItems](#placeseditrequestitems)[] | Товары в коробке | — |

#### Пример

```json
{
  "dimensions": {
    "weight_gross": 1,
    "dx": 1,
    "dy": 1,
    "dz": 1
  },
  "barcode": "Kia-01",
  "items": [
    {
      "count": 0,
      "item_barcode": "9f210a050a7282f353d9ab9ac9e27cb4"
    }
  ]
}
```

### PlaceDimensions

Весогабаритные характеристики грузоместа.

| Имя | Тип | Единица измерения | Описание | Min value |
|-----|-----|-------------------|----------|-----------|
| `weight_gross` | integer | граммы | Вес брутто | `1` |
| `dx` | integer | сантиметры | Длина | `1` |
| `dy` | integer | сантиметры | Высота | `1` |
| `dz` | integer | сантиметры | Ширина | `1` |

#### Пример

```json
{
  "weight_gross": 1,
  "dx": 1,
  "dy": 1,
  "dz": 1
}
```

### PlacesEditRequestItems

Привязка товара к коробке.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `count` | integer | Количество товара в коробке | `0` |
| `item_barcode` | string | Штрихкод товара, который находится в этой коробке | `9f210a050a7282f353d9ab9ac9e27cb4` |

#### Пример

```json
{
  "count": 0,
  "item_barcode": "9f210a050a7282f353d9ab9ac9e27cb4"
}
```

---

## Responses

### 202 Accepted

Запрос на редактирование принят.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `editing_task_id` | string | Идентификатор запроса на редактирование для уточнения статуса | `51487d835c3444e9b157b1061567f10a` |

#### Пример ответа

```json
{
  "editing_task_id": "51487d835c3444e9b157b1061567f10a"
}
```

### 400 Bad Request

Ошибка в данных запроса.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `bad_request` |
| `message` | string | Детали ошибки | `Missing field request_id` |

#### Пример ответа

```json
{
  "code": "bad_request",
  "message": "Missing field request_id"
}
```

### 403 Forbidden

Не хватает прав.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `customer_order_not_found` |
| `message` | string | Детали ошибки | `There is no customer_order with such ID in platform, the order belongs to another employer` |

#### Пример ответа

```json
{
  "code": "customer_order_not_found",
  "message": "There is no customer_order with such ID  in platform, the order belongs to another employer"
}
```

### 404 Not Found

Заявка не найдена.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `not_found` |
| `message` | string | Детали ошибки | `Order with ID some_id not found` |

#### Пример ответа

```json
{
  "code": "not_found",
  "message": "Order with ID  some_id not found"
}
```

### 409 Conflict

Конфликт с другим запросом на редактирование.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `conflict` |
| `message` | string | Детали ошибки | `Another editing request with conflict data execution` |

#### Пример ответа

```json
{
  "code": "conflict",
  "message": "Another editing request with conflict data execution"
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.11. Создание заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcreate-post) |
| Следующая | 3.13. Получение статуса запроса на редактирование | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesteditstatus-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestplacesedit-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestplacesedit-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Редактирование грузомест заказа
