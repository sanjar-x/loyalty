### Запрос данных о сессиях

Запрашивает данные сессий (статус, состав для сессий в процессе, параметры для создания партий).

**Параметры запроса**

| Параметр | Описание |
|----------|----------|
| Локальный URL | `/1.0/user-session` |
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
[
  {
    "barcodes": ["string"],
    "batch-name": "string",
    "created-ts": "string",
    "errors-count": 0,
    "sending-date": "string",
    "session-type": "CREATE_BATCHES",
    "session-uuid": "string",
    "status": "CREATED",
    "successful-count": 0,
    "timezone-offset": 0,
    "use-online-balance": true
  }
]
```

| Поле | Тип | Описание |
|------|-----|----------|
| barcodes | Массив (Опционально) | ШПИ отправлений в партии |
| batch-name | Строка (Опционально) | Номер партии |
| created-ts | Строка | Время создания сессии |
| errors-count | Целое число | Количество ошибок в сессии |
| sending-date | Строка (Опционально) | Дата сдачи в почтовое отделение (yyyy-MM-dd) |
| session-type | Строка | Тип пользовательской сессии = ['CREATE_BATCHES', 'ADD_BACKLOGS_TO_BATCH'] |
| session-uuid | Строка | Идентификатор пользовательской сессии |
| status | Строка | Статус пользовательской сессии = ['CREATED', 'READY_TO_CLOSE', 'SAVE_SHIPMENTS', 'CLOSED'] |
| successful-count | Целое число | Количество успешно обработанных отправлений в сессии |
| timezone-offset | Целое число (Опционально) | Смещение даты сдачи от UTC в секундах |
| use-online-balance | Логический (Опционально) | Признак использования онлайн-баланса |
