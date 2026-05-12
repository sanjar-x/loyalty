# 2.01. Получение идентификатора населенного пункта

## Общие сведения

| Параметр | Значение |
|----------|----------|
| Описание | Получение идентификатора населенного пункта (`geo_id`) по адресу или его фрагменту |
| HTTP-метод | `POST` |
| Content-Type | `application/json` |

### URL

| Окружение | URL |
|-----------|-----|
| Тестовое | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/location/detect` |
| Production | `https://b2b-authproxy.taxi.yandex.net/api/b2b/platform/location/detect` |

---

## Request

### Body

| Имя | Тип | Обязательный | Описание | Пример |
|-----|-----|--------------|----------|--------|
| `location` | string | Да | Адрес или его фрагмент | `Москва` |

#### Пример тела запроса

```json
{
  "location": "Москва"
}
```

---

## Модели данных

### LocationDetectedVariant

Вариант определённого населенного пункта.

| Имя | Тип | Описание | Пример |
|-----|-----|----------|--------|
| `geo_id` | integer | Идентификатор населенного пункта (`geo_id`) | `213` |
| `address` | string | Вариант адреса | `Москва` |

#### Пример

```json
{
  "geo_id": 213,
  "address": "Москва"
}
```

---

## Responses

### 200 OK

Успешный запрос.

#### Body

| Имя | Тип | Описание |
|-----|-----|----------|
| `variants` | [LocationDetectedVariant](#locationdetectedvariant)[] | Массив вариантов определённых населенных пунктов |

#### Пример ответа

```json
{
  "variants": [
    {
      "geo_id": 213,
      "address": "Москва"
    }
  ]
}
```

---

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | 1.03. Получение интервалов доставки #2 | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-post) |
| Следующая | 2.02. Получение списка точек самопривоза и ПВЗ | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformpickup-pointslist-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformlocationdetect-post](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformlocationdetect-post)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > 2. Точки самопривоза и ПВЗ > Получение идентификатора населенного пункта
