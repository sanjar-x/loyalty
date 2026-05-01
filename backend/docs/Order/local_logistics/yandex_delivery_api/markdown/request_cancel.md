# 3.10. Отмена заявки

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Отмена заявки, созданной в логистической платформе |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

> **Примечание:** Отменить заявку с типом доставки курьером можно до получения статуса `DELIVERY_TRANSPORTATION_RECIPIENT`.

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/cancel` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/cancel` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Да | ID заявки в логистической платформе | `77241d8009bb46d0bff5c65a73077bcd-udp` |

#### Пример тела запроса

```json
{
  "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp"
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание | Допустимые значения | Пример |
|-----|-----|----------|---------------------|--------|
| `status` | string | Статус отмены заявки | `CREATED` — отмена инициирована; `SUCCESS` — отмена выполнена; `ERROR` — запрос завершился с ошибкой | `CREATED` |
| `reason` | string | Код причины отмены | — | `already_cancelled` |
| `description` | string | Комментарий к результату выполнения запроса | — | `Заказ отменен` |

#### Пример ответа

```json
{
  "status": "CREATED",
  "reason": "already_cancelled",
  "description": "Заказ отменен"
}
```

### 403 Forbidden

Не хватает прав для отмены.

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

Заявка не найдена в системе.

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

### 500 Internal Server Error

Внутренняя ошибка.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `conflict` |
| `message` | string | Детали ошибки | `Internal Server Error` |

#### Пример ответа

```json
{
  "code": "conflict",
  "message": "Internal Server Error"
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.09. История статусов заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesthistory-get) |
| Следующая | 3.11. Создание заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcreate-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcancel-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcancel-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Отмена заявки
