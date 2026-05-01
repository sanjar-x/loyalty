# 3.09. История статусов заявки

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение информации об истории статусов заказа |
| HTTP-метод | `GET` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/history` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/history` |

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

| Имя | Тип | Описание |
|-----|-----|----------|
| `state_history` | [RequestState](#requeststate)[] | История изменения статусов заказа. Min items: `1` |

### RequestState

Состояние заказа на определённый момент времени (идентична модели из [3.03](yandex_delivery_other_day_request_info_get.md#requeststate)).

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `status` | string | Статус заказа (см. [статусную модель](yandex_delivery_other_day_status_model.md)) | `CREATED` |
| `description` | string | Описание статуса | `Заказ создан в операторе` |
| `timestamp` | integer | Временная метка в формате UNIX | `1704056400` |
| `timestamp_utc` | string | Временная метка в формате UTC | `2021-10-25T15:00:00.000000Z` |
| `reason` | [CancelReason / ChangeReason](yandex_delivery_other_day_request_info_get.md#cancelreason--changereason) | Детальная причина события (отмены или переноса) | `SHOP_CANCELLED` |

#### Пример ответа

```json
{
  "state_history": [
    {
      "status": "CREATED",
      "description": "Заказ создан в операторе",
      "timestamp": 1704056400,
      "timestamp_utc": "2021-10-25T15:00:00.000000Z",
      "reason": "SHOP_CANCELLED"
    }
  ]
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.08. Получение интервалов доставки для нового места | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestredelivery_options-post) |
| Следующая | 3.10. Отмена заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcancel-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesthistory-get](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesthistory-get)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > История статусов заявки
