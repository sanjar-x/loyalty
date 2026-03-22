### Запрос данных по партиям сформированным в пользовательской сессии

Запрашивает данные по партиям сформированным в пользовательской сессии.

**Параметры запроса**

| Параметр | Описание |
|----------|----------|
| Локальный URL | `/1.0/user-session/{sessionUuid}/retrieve-batches-info` |
| Тип | **GET** |

**Заголовки запроса**

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | AccessToken {token} |
| **X-User-Authorization** | Basic {key} |
| **Content-Type** | application/json;charset=UTF-8 |

**Ответ на запрос**

```json
{
  "batches": [
    {
      "barcodes": ["string"],
      "batch-name": "string"
    }
  ],
  "session-status": "CREATED"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| batches | Массив | Информация о партии в сессии |
| batches[].barcodes | Массив | ШПИ отправлений в партии |
| batches[].batch-name | Строка | Номер партии |
| session-status | Строка | Статус пользовательской сессии = ['CREATED', 'READY_TO_CLOSE', 'SAVE_SHIPMENTS', 'CLOSED'] |
