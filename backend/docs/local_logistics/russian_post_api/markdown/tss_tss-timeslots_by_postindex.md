# Получение списка свободных таймслотов

Получение списка свободных таймслотов с учетом плановой даты передачи груза на ОПС. Данный метод необходимо вызывать, когда заказ еще не создан.

## Параметры запроса

| Параметр | Значение |
|----------|----------|
| Локальный URL | **/external/v1/timeslots-by-postindex?postIndexFrom={postIndexFrom}&postIndexTo={postIndexTo}&contractNumber={contractNumber}&plannedShippingDate={plannedShippingDate}&address={address}&workTypeCode={workTypeCode}&mailTypeCode={mailTypeCode}&mailCtgCode={mailCtgCode}** |
| Тип | **GET** |

**Query-параметры:**

| Параметр | Обязательность | Описание |
|----------|---------------|----------|
| postIndexFrom | Обязательный | Почтовый индекс отправителя |
| postIndexTo | Обязательный | Почтовый индекс получателя |
| contractNumber | Опционально | Номер договора |
| plannedShippingDate | Обязательный | Плановая дата в формате: yyyy-MM-dd |
| address | Обязательный | Адрес получателя |
| workTypeCode | Обязательный | Код типа работ. В текущей реализации может принимать значение: delivery |
| mailTypeCode | Обязательный | Код типа отправления. В текущей реализации может принимать значение 24 (Курьер онлайн) |
| mailCtgCode | Обязательный | Код категории почтового отправления |

## Заголовки запроса

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | **AccessToken {token}** |
| **X-User-Authorization** | **Basic {key}** |
| **Content-Type** | **application/json;charset=UTF-8** |

## Ответ на запрос

```json
{
  "uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "timeslots": [
    {
      "id": 0,
      "date": "2022-12-07",
      "beginTime": "09:00",
      "endTime": "18:00",
      "capacity": 0
    }
  ]
}
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| uuid | Строка | Уникальный идентификатор для предварительного бронирования |
| timeslots | Массив | Список доступных слотов |
| timeslots[].id | Целое число | Идентификатор |
| timeslots[].date | Строка | Дата действия |
| timeslots[].beginTime | Строка | Время с которого действует (например, 09:00) |
| timeslots[].endTime | Строка | Время до которого действует (например, 18:00) |
| timeslots[].capacity | Целое число | Емкость таймслота |
