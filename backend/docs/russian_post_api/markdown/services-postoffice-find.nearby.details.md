### Детальный поиск почтовых отделений по координатам

**Параметры запроса**

| Параметр | Описание |
|----------|----------|
| Локальный URL | `/postoffice/1.0/nearby.details` |
| Тип | **GET** |

Параметры URL:

| Параметр | Тип | Описание |
|----------|-----|----------|
| **latitude** | Число | Широта |
| **longitude** | Число | Долгота |
| **top** | Число (Опционально) | Количество ближайших почтовых отделений в результате поиска |
| **offset** | Число (Опционально) | Индекс первой записи |
| **filter** | Строка (Опционально) | Фильтр. Возможные значения: ROUND_THE_CLOCK (Круглосуточные), WORK_ON_SUNDAY (Работающие в воскресенье), RPO_CENTER (Центр выдачи и приёма посылок), BIG_PARCELS (Тяжёлые крупногабаритные посылки), EMS (Отправления EMS), FORSAGE (Почтовые переводы Форсаж), WESTERN_UNION (Переводы Western Union) |
| **search-radius** | Число (Опционально) | Радиус для поиска (в километрах) |
| **current-date-time** | Строка (Опционально) | Текущее время в формате yyyy-MM-dd'T'HH:mm:ss |
| **hide-private** | Логический (Опционально) | Исключать не публичные отделения. По умолчанию false. |
| **hide-temporary-closed** | Логический (Опционально) | Исключать временно закрытые отделения. По умолчанию false. |
| **full-address-only** | Логический (Опционально) | Показывать полный адрес. По умолчанию false. |
| **hide-not-available** | Логический (Опционально) | Исключать не действующие отделения. По умолчанию false. |

**Заголовки запроса**

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | AccessToken {token} |
| **X-User-Authorization** | Basic {key} |
| **Content-Type** | application/json;charset=UTF-8 |

**Ответ на запрос**

```json
[
  {
    "address-source": "string",
    "current-day-working-hours": {
      "lunches": [{}],
      "weekday-id": 0,
      "weekday-name": "string"
    },
    "distance": 0,
    "district": "string",
    "holidays": [
      {
        "date": "string",
        "schedule": {
          "lunches": [{}],
          "weekday-id": 0,
          "weekday-name": "string"
        }
      }
    ],
    "is-closed": false,
    "is-private-category": false,
    "is-temporary-closed": false,
    "latitude": 0,
    "longitude": 0,
    "nearest-office-postalcode": "string",
    "next-day-working-hours": {
      "lunches": [{}],
      "weekday-id": 0,
      "weekday-name": "string"
    },
    "postal-code": "string",
    "prescribed": false,
    "region": "string",
    "settlement": "string",
    "temporary-closed-reason": "string",
    "type-code": "string",
    "type-id": 0,
    "working-hours": [
      {
        "lunches": [{}],
        "weekday-id": 0,
        "weekday-name": "string"
      }
    ],
    "works-on-saturdays": false,
    "works-on-sundays": false
  }
]
```

| Поле | Тип | Описание |
|------|-----|----------|
| address-source | Строка | Адрес отделения |
| current-day-working-hours | Объект (Опционально) | Рабочие часы в текущее время |
| current-day-working-hours.lunches | Массив (Опционально) | Перерывы |
| current-day-working-hours.weekday-id | Целое число (Опционально) | Номер дня в неделе |
| current-day-working-hours.weekday-name | Строка (Опционально) | Наименование дня в неделе |
| distance | Число (Опционально) | Расстояние до отделения |
| district | Строка (Опционально) | Округ |
| holidays | Массив (Опционально) | Выходные |
| holidays[].date | Строка (Опционально) | Дата |
| holidays[].schedule | Объект (Опционально) | Рабочий день |
| is-closed | Логический (Опционально) | Признак 'закрыто' |
| is-private-category | Логический (Опционально) | Признак внутреннего отделения |
| is-temporary-closed | Логический (Опционально) | Признак 'временно закрыто' |
| latitude | Число | Широта |
| longitude | Число | Долгота |
| nearest-office-postalcode | Строка (Опционально) | Индекс ближайшего почтового отделения |
| next-day-working-hours | Объект (Опционально) | Рабочие часы в следующий рабочий день |
| postal-code | Строка | Индекс почтового отделения |
| prescribed | Логический (Опционально) | Предписанный |
| region | Строка (Опционально) | Область, край |
| settlement | Строка (Опционально) | Поселение |
| temporary-closed-reason | Строка (Опционально) | Причина 'временно закрыто' |
| type-code | Строка | Тип отделения |
| type-id | Целое число | Идентификатор типа отделения |
| working-hours | Массив (Опционально) | Рабочие часы |
| working-hours[].lunches | Массив (Опционально) | Перерывы |
| working-hours[].weekday-id | Целое число (Опционально) | Номер дня в неделе |
| working-hours[].weekday-name | Строка (Опционально) | Наименование дня в неделе |
| works-on-saturdays | Логический (Опционально) | Признак работы в субботу |
| works-on-sundays | Логический (Опционально) | Признак работы в воскресенье |
