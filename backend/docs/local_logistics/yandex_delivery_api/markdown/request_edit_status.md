# 3.13. Получение статуса запроса на редактирование

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение статуса запроса на редактирование по `editing_task_id` |
| HTTP-метод | `POST` |

> **Примечание:** Идентификатор `editing_task_id` возвращается методами [3.12. Редактирование грузомест заказа](yandex_delivery_other_day_request_places_edit.md) и [3.14. Заявка на редактирование товаров заказа](yandex_delivery_other_day_request_items_edit.md).

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/edit/status` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/edit/status` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `editing_task_id` | string | Да | Идентификатор запроса на редактирование | `51487d835c3444e9b157b1061567f10a` |

---

## Responses

### 200 OK

Статус запроса на редактирование.

#### Body

| Имя | Тип | Описание | Допустимые значения |
|-----|-----|----------|---------------------|
| `status` | [EditingRequestStatus](#editingrequeststatus) | Статус запроса на редактирование | `pending`, `execution`, `success`, `failure` |

### EditingRequestStatus

| Значение | Описание |
|----------|----------|
| `pending` | Ожидает выполнения |
| `execution` | Выполняется |
| `success` | Успешно выполнен |
| `failure` | В процессе выполнения произошла ошибка |

#### Пример ответа

```json
{
  "status": "pending"
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

### 404 Not Found

Запрос не найден.

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

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.12. Редактирование грузомест заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestplacesedit-post) |
| Следующая | 3.14. Заявка на редактирование товаров заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestitems-instancesedit-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesteditstatus-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesteditstatus-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Получение статуса запроса на редактирование
