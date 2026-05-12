# Возврат партии из архива

## Параметры запроса

| Параметр | Значение |
|----------|----------|
| Локальный URL | **/1.0/archive/revert** |
| Тип | **POST** |

## Заголовки запроса

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | **AccessToken {token}** |
| **X-User-Authorization** | **Basic {key}** |
| **Content-Type** | **application/json;charset=UTF-8** |

## Тело запроса

`Array[string]` -- Список с именами партий

## Ответ на запрос

```json
[
  {
    "batch-name": "string",
    "error-code": "UNDEFINED"
  }
]
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| batch-name | Строка (Опционально) | Наименование партии |
| error-code | Строка (Опционально) | Ошибка. Возможные значения: `UNDEFINED`, `BARCODE_ERROR`, `ILLEGAL_MAIL_TYPE`, `ILLEGAL_MAIL_CATEGORY`, `RESTRICTED_MAIL_CATEGORY`, `SENDING_MAIL_FAILED`, `NOT_FOUND`, `PAST_DUE_DATE`, `ILLEGAL_POSTCODE`, `READONLY_STATE`, `ALL_SHIPMENTS_SENT`, `DIFFERENT_TRANSPORT_TYPE`, `DIFFERENT_POSTMARK`, `NO_AVAILABLE_POSTOFFICES`, `ILLEGAL_POSTOFFICE_CODE`, `EMPTY_POSTOFFICE_CODE` |
