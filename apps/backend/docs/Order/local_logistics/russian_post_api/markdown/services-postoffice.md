### Поиск почтового отделения по индексу

**Параметры запроса**

| Параметр | Описание |
|----------|----------|
| Локальный URL | `/postoffice/1.0/{postal-code}` |
| Тип | **GET** |

Параметры URL:

| Параметр | Тип | Описание |
|----------|-----|----------|
| **postal-code** | Строка | Индекс почтового отделения |
| **latitude** | Число (Опционально) | Широта |
| **longitude** | Число (Опционально) | Долгота |
| **current-date-time** | Строка (Опционально) | Текущее время в формате yyyy-MM-dd'T'HH:mm:ss |
| **filter-by-office-type** | Логический (Опционально) | Фильтр по типам объектов в ответе. true: ГОПС, СОПС, ПОЧТОМАТ. false: все. Значение по умолчанию true. |
| **ufps-postal-code** | Логический (Опционально) | true: добавлять в ответ индекс УФПС для найдённого отделения, false: не добавлять. Значение по умолчанию false. |

**Заголовки запроса**

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | AccessToken {token} |
| **X-User-Authorization** | Basic {key} |
| **Content-Type** | application/json;charset=UTF-8 |

**Ответ на запрос**

```json
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
  "nearest-postoffice": {
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
  },
  "next-day-working-hours": {
    "lunches": [{}],
    "weekday-id": 0,
    "weekday-name": "string"
  },
  "phones": [
    {
      "is-fax": false,
      "phone-number": "string",
      "phone-town-code": "string",
      "phone-type-name": "string"
    }
  ],
  "postal-code": "string",
  "prescribed": false,
  "region": "string",
  "service-groups": [
    {
      "group-id": 0,
      "group-name": "string"
    }
  ],
  "settlement": "string",
  "temporary-closed-reason": "string",
  "type-code": "string",
  "type-id": 0,
  "ufps-code": "string",
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
| nearest-postoffice | Объект (Опционально) | Ближайшее почтовое отделение (структура аналогична основному объекту) |
| next-day-working-hours | Объект (Опционально) | Рабочие часы в следующий рабочий день |
| phones | Массив (Опционально) | Телефоны |
| phones[].is-fax | Логический (Опционально) | Fax признак |
| phones[].phone-number | Строка | Номер телефона |
| phones[].phone-town-code | Строка (Опционально) | Код города |
| phones[].phone-type-name | Строка (Опционально) | Тип телефонного номера |
| postal-code | Строка | Индекс почтового отделения |
| prescribed | Логический (Опционально) | Предписанный |
| region | Строка (Опционально) | Область, край |
| service-groups | Массив (Опционально) | Группы сервисов |
| service-groups[].group-id | Целое число | Идентификатор группы |
| service-groups[].group-name | Строка (Опционально) | Наименование группы |
| settlement | Строка (Опционально) | Поселение |
| temporary-closed-reason | Строка (Опционально) | Причина 'временно закрыто' |
| type-code | Строка | Тип отделения |
| type-id | Целое число | Идентификатор типа отделения |
| ufps-code | Строка (Опционально) | Код ЮФПС |
| working-hours | Массив (Опционально) | Рабочие часы |
| working-hours[].lunches | Массив (Опционально) | Перерывы |
| working-hours[].weekday-id | Целое число (Опционально) | Номер дня в неделе |
| working-hours[].weekday-name | Строка (Опционально) | Наименование дня в неделе |
| works-on-saturdays | Логический (Опционально) | Признак работы в субботу |
| works-on-sundays | Логический (Опционально) | Признак работы в воскресенье |
