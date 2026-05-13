# 3.02. Подтверждение заявки

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Бронирование выбранного варианта доставки (оффера) |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/offers/confirm` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/offers/confirm` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `offer_id` | string | Да | Идентификатор предложения маршрутного листа | `c1b139dbd76b4ee3b39b19180b516119` |

#### Пример тела запроса

```json
{
  "offer_id": "c1b139dbd76b4ee3b39b19180b516119"
}
```

---

## Responses

### 200 OK

Успешное бронирование.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `request_id` | string | Идентификатор только что созданного заказа | `77241d8009bb46d0bff5c65a73077bcd-udp` |

#### Пример ответа

```json
{
  "request_id": "77241d8009bb46d0bff5c65a73077bcd-udp"
}
```

### 400 Bad Request

Ошибка в данных пользователя.

#### Body

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `code` | string | Код ошибки | `bad_request` |
| `message` | string | Детали ошибки | `Missing required field 'offer_id'` |

#### Пример ответа

```json
{
  "code": "bad_request",
  "message": "Missing required field 'offer_id'"
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.01. Создание заявки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformofferscreate-post) |
| Следующая | 3.03. Получение информации о заявке | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestinfo-get) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformoffersconfirm-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformoffersconfirm-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 3. Основные запросы > Подтверждение заявки
