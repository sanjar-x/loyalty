### Поиск краткой информации об отделении ОПС по индексу

**Параметры запроса**

| Параметр | Описание |
|----------|----------|
| Локальный URL | `/postoffice/1.0/{postal-code}/brief` |
| Тип | **GET** |

Параметры URL:

| Параметр | Тип | Описание |
|----------|-----|----------|
| **postal-code** | Строка | Индекс почтового отделения |

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
  "phones": [
    {
      "is-fax": false,
      "phone-number": "string",
      "phone-town-code": "string",
      "phone-type-name": "string"
    }
  ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| address-source | Строка | Адрес почтового отделения |
| phones | Массив (Опционально) | Телефоны |
| phones[].is-fax | Логический (Опционально) | Fax признак |
| phones[].phone-number | Строка | Номер телефона |
| phones[].phone-town-code | Строка (Опционально) | Код города |
| phones[].phone-type-name | Строка (Опционально) | Тип телефонного номера |
