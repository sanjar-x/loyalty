# Удаление отдельного возвратного отправления

Удаляет отдельное возвратное отправление.

## Параметры запроса

| Параметр | Значение |
|----------|----------|
| Локальный URL | **/1.0/returns/delete-separate-return?barcode={barcode}** |
| Тип | **DELETE** |

**barcode** -- ШПИ возвратного отправления.

## Заголовки запроса

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | **AccessToken {token}** |
| **X-User-Authorization** | **Basic {key}** |
| **Content-Type** | **application/json;charset=UTF-8** |

## Ответ на запрос

```json
{
  "code": "RETURN_SHIPMENT_NOT_FOUND",
  "description": "string"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| code | Строка | Код ошибки |
| description | Строка | Описание ошибки |
