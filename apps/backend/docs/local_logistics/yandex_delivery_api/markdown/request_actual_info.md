# 3.05. Получение актуальной информации о доставке

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение актуальной даты и времени доставки |
| HTTP-метод | `GET` |

> **Примечание:** Метод актуален только для заказов в статусе, отличном от `DELIVERY_DELIVERED`, `ERROR` или `CANCELLED`.

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/actual_info` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/actual_info` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Да | ID заявки в логистической платформе | `77241d8009bb46d0bff5c65a73077bcd-udp` |

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `delivery_date` | string | Дата доставки в формате `YYYY-MM-DD` | `2023-10-20` |
| `delivery_interval` | [ActualDeliveryInterval](#actualdeliveryinterval) | Временной интервал доставки | — |

### ActualDeliveryInterval

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `from` | string | Начало интервала (время + часовой пояс) | `10:00+03:00` |
| `to` | string | Конец интервала (время + часовой пояс) | `23:00+03:00` |

#### Пример ответа

```json
{
  "delivery_date": "2023-10-20",
  "delivery_interval": {
    "from": "10:00+03:00",
    "to": "23:00+03:00"
  }
}
```

### 404 Not Found

Заявка не найдена в системе.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `not_found` |
| `message` | string | Человекочитаемые детали ошибки | `Order with ID some_id not found` |

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
| Предыдущая | 3.04. Получение информации о заявках во временном интервале | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestsinfo-post) |
| Следующая | 3.06. Редактирование заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestedit-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestactual_info-get](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestactual_info-get)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Получение актуальной информации о доставке
