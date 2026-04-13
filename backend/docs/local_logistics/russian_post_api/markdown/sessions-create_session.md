### Создание пользовательской сессии

Создает пользовательскую сессию для создания партий и добавления заказов в партию.

**Параметры запроса**

| Параметр | Описание |
|----------|----------|
| Локальный URL | `/1.0/user-session` |
| Тип | **POST** |

**Заголовки запроса**

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | AccessToken {token} |
| **X-User-Authorization** | Basic {key} |
| **Content-Type** | application/json;charset=UTF-8 |

**Тело запроса**

```json
{
  "batch-name": "string",
  "session-type": "CREATE_BATCHES"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| batch-name | Строка (Опционально) | Номер партии |
| session-type | Строка | Тип пользовательской сессии = ['CREATE_BATCHES', 'ADD_BACKLOGS_TO_BATCH'] |

**Ответ на запрос**

```json
{
  "error": "EMPTY_BATCH_NAME",
  "session-uuid": "string"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| error | Строка (Опционально) | Ошибка создания сессии = ['EMPTY_BATCH_NAME', 'ILLEGAL_BATCH_NAME', 'BATCH_DOESNT_EXIST'] |
| session-uuid | Строка (Опционально) | Идентификатор пользовательской сессии |
