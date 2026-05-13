# Получение списка свободных таймслотов при перебронировании

Получение списка свободных таймслотов при перебронировании. Данный метод необходимо вызывать, когда заказ существует в системе на любых этапах обработки.

## Параметры запроса

| Параметр | Значение |
|----------|----------|
| Локальный URL | **/external/v1/timeslots-for-rebooking?uuidOrBarcode={uuidOrBarcode}&contractNumber={contractNumber}&plannedShippingDate={plannedShippingDate}** |
| Тип | **GET** |

**Query-параметры:**

| Параметр | Обязательность | Описание |
|----------|---------------|----------|
| uuidOrBarcode | Обязательный | UUID предварительного бронирования или ШПИ |
| contractNumber | Опционально | Номер договора |
| plannedShippingDate | Обязательный | Плановая дата в формате: yyyy-MM-dd |

## Заголовки запроса

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | **AccessToken {token}** |
| **X-User-Authorization** | **Basic {key}** |
| **Content-Type** | **application/json;charset=UTF-8** |

## Ответ на запрос

```json
{
  "timeslots": [
    {
      "id": 0,
      "date": "2023-02-06",
      "beginTime": "09:00",
      "endTime": "18:00",
      "capacity": 0
    }
  ]
}
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| timeslots | Массив | Список доступных слотов |
| timeslots[].id | Целое число | Идентификатор |
| timeslots[].date | Строка | Дата действия |
| timeslots[].beginTime | Строка | Время с которого действует |
| timeslots[].endTime | Строка | Время до которого действует |
| timeslots[].capacity | Целое число | Емкость таймслота |
