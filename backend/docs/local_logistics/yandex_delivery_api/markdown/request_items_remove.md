# 3.15. Заявка на удаление товаров из заказа

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Создание заявки на удаление товаров из заказа |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

> **Примечание:** Принимает полный набор товаров с указанием нужного количества для каждого товара. Если новое количество товара будет больше старого, запрос завершится с ошибкой.

> **Асинхронная операция:** Редактирование происходит асинхронно. Для проверки статуса используйте метод [3.13](yandex_delivery_other_day_request_edit_status.md) `/api/b2b/platform/request/edit/status`.

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/items/remove` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/items/remove` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Да | ID заказа | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `items_to_remove` | [ItemToRemove](#itemtoremove)[] | Да | Список товаров с новым количеством. Min items: `1` | — |

#### Пример тела запроса

```json
{
  "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp",
  "items_to_remove": [
    {
      "item_barcode": "9f210a050a7282f353d9ab9ac9e27cb4",
      "remaining_count": 0
    }
  ]
}
```

---

## Модели данных

### ItemToRemove

Товар для удаления/уменьшения количества.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `item_barcode` | string | Штрихкод товара | `9f210a050a7282f353d9ab9ac9e27cb4` |
| `remaining_count` | integer | Остаток товара (новое количество). `0` — полное удаление | `0` |

#### Пример

```json
{
  "item_barcode": "9f210a050a7282f353d9ab9ac9e27cb4",
  "remaining_count": 0
}
```

---

## Responses

### 202 Accepted

Запрос на удаление принят.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `editing_task_id` | string | Идентификатор запроса для уточнения статуса | `51487d835c3444e9b157b1061567f10a` |

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
| Предыдущая | 3.14. Заявка на редактирование товаров заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestitems-instancesedit-post) |
| Следующая | 4.01. Получение ярлыков | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestgenerate-labels-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestitemsremove-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestitemsremove-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Заявка на удаление товаров из заказа
