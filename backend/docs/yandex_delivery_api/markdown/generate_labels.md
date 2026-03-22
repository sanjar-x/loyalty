# 4.01. Получение ярлыков

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Генерация ярлыков для указанных заказов |
| HTTP-метод | `POST` |
| Content-Type запроса | `application/json` |
| Content-Type ответа | `application/pdf` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/request/generate-labels` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/request/generate-labels` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Значение по умолчанию | Пример |
|-----|-----|--------------|----------|-----------------------|--------|
| `request_ids` | string[] | Да | Список ID заказов. Количество заказов не должно превышать предельно допустимого | — | `["77241d8009bb46d0bff5c65a73077bcd-udp"]` |
| `generate_type` | string | Нет | Формат генерации ярлыков: `one` — один ярлык на страницу; `many` — максимум ярлыков на страницу | `one` | `one` |
| `language` | string | Нет | Язык надписей на этикетке | `ru` | `ru` |

#### Пример тела запроса

```json
{
  "request_ids": "77241d8009bb46d0bff5c65a73077bcd-udp",
  "generate_type": "one",
  "language": "ru"
}
```

---

## Responses

### 200 OK

Успешная генерация ярлыков.

#### Body

| Параметр | Значение |
|----------|----------|
| Тип | string |
| Формат | binary |
| Content-Type | `application/pdf` |
| Описание | PDF-документ с ярлыками для указанных заказов |

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 3.15. Заявка на удаление товаров из заказа | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestitemsremove-post) |
| Следующая | 4.02. Получение актов приема-передачи для отгрузки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestget-handover-act-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestgenerate-labels-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestgenerate-labels-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 4. Ярлыки и акты приема-передачи > Получение ярлыков
