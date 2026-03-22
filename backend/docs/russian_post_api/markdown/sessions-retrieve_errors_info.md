### Запрос ошибок по заказам в пользовательской сессии

Запрашивает данные по ошибкам в пользовательской сессии.

**Параметры запроса**

| Параметр | Описание |
|----------|----------|
| Локальный URL | `/1.0/user-session/{sessionUuid}/retrieve-errors-info` |
| Тип | **GET** |

Параметры URL:

| Параметр | Тип | Описание |
|----------|-----|----------|
| **size** | Число (Опционально) | Количество записей на странице |
| **page** | Число (Опционально) | Номер страницы (0..N) |

**Заголовки запроса**

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | AccessToken {token} |
| **X-User-Authorization** | Basic {key} |
| **Content-Type** | application/json;charset=UTF-8 |

**Ответ на запрос**

```json
{
  "session-errors": [
    {
      "barcode": "string",
      "errors": ["ALL_SHIPMENTS_SENT"]
    }
  ],
  "session-status": "CREATED"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| session-errors | Массив | Информация об ошибках в рамках сессии |
| session-errors[].barcode | Строка (Опционально) | ШПИ отправления |
| session-errors[].errors | Массив | Код ошибки (см. справочник ошибок) |
| session-status | Строка | Статус пользовательской сессии = ['CREATED', 'READY_TO_CLOSE', 'SAVE_SHIPMENTS', 'CLOSED'] |
