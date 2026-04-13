# 4.02. Получение актов приема-передачи для отгрузки

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение актов приема-передачи для отгрузки |
| HTTP-метод | `POST` |
| Content-Type запроса | `application/json` |
| Content-Type ответа | `application/pdf` (по умолчанию) или `application/msword` (при `editable_format=true`) |

> **Примечание:** Необходимо передать хотя бы один из критериев включения заказов в акт:
> 1. Только заказы, которые ещё не были отгружены (`new_requests=true`)
> 2. Диапазон дат создания заказов (`created_since` / `created_until`)
> 3. Массив номеров заказов по `request_id` (query или body)
> 4. Номер заказа в системе заказчика (`request_code`)

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/get-handover-act` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/get-handover-act` |

---

## Request

### Query parameters

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `new_requests` | boolean | Нет | При `true` — в акт попадут все новые заказы, ещё не отгруженные | — |
| `created_since` | integer | Нет | Начало диапазона дат создания (UNIX). Приоритет выше UTC-версии. Min: `0` | — |
| `created_until` | integer | Нет | Конец диапазона дат создания (UNIX). Приоритет выше UTC-версии. Min: `0` | — |
| `created_since_utc` | string | Нет | Начало диапазона дат создания (UTC) | `2021-10-25T15:00:00.000000Z` |
| `created_until_utc` | string | Нет | Конец диапазона дат создания (UTC) | `2021-10-25T17:00:00.000000Z` |
| `request_ids` | string | Нет | В акт попадут указанные заказы (по `request_id`) | `77241d8009bb46d0bff5c65a73077bcd-udp` |
| `request_code` | string | Нет | В акт попадёт указанный заказ (по `request_code`) | `my_request_id_123` |
| `editable_format` | boolean | Нет | Генерация документа в формате Word вместо PDF | — |

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `request_ids` | string[] | Нет | Список `request_id` заказов для добавления в АПП (заказы не дублируются) | `["77241d8009bb46d0bff5c65a73077bcd-udp"]` |
| `request_codes` | string[] | Нет | Список `request_code` заказов для добавления в АПП (заказы не дублируются) | `["Kia-01", "Kia-02"]` |

#### Пример тела запроса

```json
{
  "request_ids": "77241d8009bb46d0bff5c65a73077bcd-udp",
  "request_codes": "Kia-01, Kia-02"
}
```

---

## Responses

### 200 OK

Успешная генерация акта приема-передачи.

#### Body

| Параметр | Значение |
|----------|----------|
| Тип | string |
| Формат | binary |
| Content-Type | `application/pdf` (по умолчанию) или `application/msword` (при `editable_format=true`) |
| Описание | PDF или Word документ с актом приема-передачи |

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 4.01. Получение ярлыков | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestgenerate-labels-post) |
| Следующая | 5.01. Регистрация мерчанта | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/5.-Upravlenie-merchantami/apib2bplatformmerchantregistrationinit-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestget-handover-act-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestget-handover-act-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 4. Ярлыки и акты приема-передачи > Получение актов приема-передачи
