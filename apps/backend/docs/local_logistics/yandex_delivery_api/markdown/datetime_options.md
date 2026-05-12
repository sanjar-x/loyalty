# 3.07. Получение интервалов доставки для текущего места получения заказа

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение интервалов доставки для нового места получения заказа |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/datetime_options` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/datetime_options` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_id` | string | Да | ID заказа в логистической платформе | `77241d8009bb46d0bff5c65a73077bcd-udp` |

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

| Имя | Тип | Описание |
|-----|-----|----------|
| `options` | [TimeIntervalUTC](#timeintervalutc)[] | Возможные интервалы доставки |

### TimeIntervalUTC

Интервал времени в формате UTC.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `from` | TimestampUNIX / string | UTC timestamp для нижней границы интервала | `2021-10-25T15:00:00.000000Z` |
| `to` | TimestampUTC / string | UTC timestamp для верхней границы интервала | `2021-10-25T15:00:00.000000Z` |

#### Пример ответа

```json
{
  "options": [
    {
      "from": "2021-10-25T15:00:00.000000Z",
      "to": "2021-10-25T15:00:00.000000Z"
    }
  ]
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.06. Редактирование заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestedit-post) |
| Следующая | 3.08. Получение интервалов доставки для нового места получения заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestredelivery_options-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestdatetime_options-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestdatetime_options-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Получение интервалов доставки для текущего места
