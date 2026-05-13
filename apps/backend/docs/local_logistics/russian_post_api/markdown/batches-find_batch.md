# Поиск партии по наименованию

Возвращает параметры партии.

## Параметры запроса

| Параметр | Значение |
|----------|----------|
| Локальный URL | **/1.0/batch/{name}** |
| Тип | **GET** |

**name** -- Наименование партии.

## Заголовки запроса

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | **AccessToken {token}** |
| **X-User-Authorization** | **Basic {key}** |
| **Content-Type** | **application/json;charset=UTF-8** |

## Ответ на запрос

```json
{
  "accepted-count": 0,
  "batch-name": "string",
  "batch-status": "CREATED",
  "batch-status-date": "string",
  "bk-hash": 0,
  "branch-name": "string",
  "combined-batch-mail-types": ["UNDEFINED"],
  "courier-call-rate-with-vat": 0,
  "courier-call-rate-wo-vat": 0,
  "courier-order-statuses": ["NOT_REQUIRED"],
  "delivery-count": 0,
  "delivery-notice-payment-method": "CASHLESS",
  "document-download-status": "NEW_TRANSPORT_BLANK",
  "electronic-f103": true,
  "fragile-rate": 0,
  "fragile-rate-vat": 0,
  "group-name": "string",
  "hyper-local-status": "string",
  "international": true,
  "is-postoffice-ukd": true,
  "list-number": 0,
  "list-number-date": "string",
  "mail-category": "ORDERED",
  "mail-category-text": "string",
  "mail-rank": "WO_RANK",
  "mail-type": "UNDEFINED",
  "mail-type-text": "string",
  "notice-payment-method": "CASHLESS",
  "payment-method": "CASHLESS",
  "person-code": "string",
  "postmarks": ["WITHOUT_MARK"],
  "postoffice-address": "string",
  "postoffice-code": "string",
  "postoffice-name": "string",
  "pre-postal-preparation": true,
  "shipment-avia-rate-sum": 0,
  "shipment-avia-rate-vat-sum": 0,
  "shipment-completeness-checking-rate-sum": 0,
  "shipment-completeness-checking-rate-vat-sum": 0,
  "shipment-contents-checking-rate-sum": 0,
  "shipment-contents-checking-rate-vat-sum": 0,
  "shipment-count": 0,
  "shipment-functionality-checking-rate-sum": 0,
  "shipment-functionality-checking-rate-vat-sum": 0,
  "shipment-ground-rate-sum": 0,
  "shipment-ground-rate-vat-sum": 0,
  "shipment-insure-rate-sum": 0,
  "shipment-insure-rate-vat-sum": 0,
  "shipment-inventory-rate-sum": 0,
  "shipment-inventory-rate-vat-sum": 0,
  "shipment-mass": 0,
  "shipment-mass-rate-sum": 0,
  "shipment-mass-rate-vat-sum": 0,
  "shipment-notice-rate-sum": 0,
  "shipment-notice-rate-vat-sum": 0,
  "shipment-partial-redemption-rate-sum": 0,
  "shipment-partial-redemption-rate-vat-sum": 0,
  "shipment-pre-postal-preparation-rate-sum": 0,
  "shipment-pre-postal-preparation-rate-vat-sum": 0,
  "shipment-sms-notice-rate-sum": 0,
  "shipment-sms-notice-rate-vat-sum": 0,
  "shipment-with-fitting-rate-sum": 0,
  "shipment-with-fitting-rate-vat-sum": 0,
  "shipping-notice-type": "SIMPLE",
  "transport-type": "SURFACE",
  "ukd": true,
  "use-online-balance": true,
  "wo-mass": true
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| accepted-count | Целое число (Опционально) | Количество отправлений, прибывших в отделение связи (для БК) |
| batch-name | Строка | Номер партии |
| batch-status | Строка | Статус партии |
| batch-status-date | Строка | Дата обновления статуса |
| bk-hash | Целое число (Опционально) | Хэш-код бандероль-комплектов |
| branch-name | Строка (Опционально) | Идентификатор подразделения |
| combined-batch-mail-types | Массив (Опционально) | Типы отправлений в комбинированной партии |
| courier-call-rate-with-vat | Целое число (Опционально) | Плата за услугу "Курьерский сбор" с НДС |
| courier-call-rate-wo-vat | Целое число (Опционально) | Плата за услугу "Курьерский сбор" без НДС |
| courier-order-statuses | Массив (Опционально) | Статусы заявки на вызов курьера |
| delivery-count | Целое число (Опционально) | Количество отправлений, врученных адресату (для БК) |
| delivery-notice-payment-method | Строка (Опционально) | Способ оплаты уведомления о вручении РПО |
| document-download-status | Строка (Опционально) | Статус загрузки документов |
| electronic-f103 | Логические: true или false | Электронная ф103 |
| fragile-rate | Целое число (Опционально) | Плата за услугу "Осторожно, хрупкое, терморежим" без НДС |
| fragile-rate-vat | Целое число (Опционально) | Плата за услугу "Осторожно, хрупкое, терморежим" c НДС |
| group-name | Строка (Опционально) | Наименование группы (для Многоместных отправлений) |
| hyper-local-status | Строка (Опционально) | Статус по гиперлокальной доставке |
| international | Логические: true или false (Опционально) | Признак международной почты |
| is-postoffice-ukd | Логические: true или false | Является ли место приема УКД |
| list-number | Целое число (Опционально) | Номер документа для сдачи партии |
| list-number-date | Строка (Опционально) | Дата документа для сдачи партии (yyyy-MM-dd) |
| mail-category | Строка | Категория РПО |
| mail-category-text | Строка | Категория РПО (текст) |
| mail-rank | Строка (Опционально) | Код разряда партии |
| mail-type | Строка | Вид РПО |
| mail-type-text | Строка | Вид РПО (текст) |
| notice-payment-method | Строка (Опционально) | Способ оплаты уведомления |
| payment-method | Строка | Способ оплаты |
| person-code | Строка (Опционально) | Идентификатор пользователя |
| postmarks | Массив | Коды отметок внутренних и международных отправлений |
| postoffice-address | Строка | Адрес места приема |
| postoffice-code | Строка | Индекс места приема |
| postoffice-name | Строка | Наименование места приема |
| pre-postal-preparation | Логические: true или false (Опционально) | Предпочтовая подготовка |
| shipment-avia-rate-sum | Целое число (Опционально) | Сумма платы за авиа пересылку в копейках, без НДС |
| shipment-avia-rate-vat-sum | Целое число (Опционально) | НДС от суммы платы за авиа пересылку в копейках |
| shipment-completeness-checking-rate-sum | Целое число | Сумма платы за проверку комплектности в копейках, без НДС |
| shipment-completeness-checking-rate-vat-sum | Целое число | НДС от суммы платы за проверку комплектности в копейках |
| shipment-contents-checking-rate-sum | Целое число | Сумма платы за проверку вложений в копейках, без НДС |
| shipment-contents-checking-rate-vat-sum | Целое число | НДС от суммы платы за проверку вложений в копейках |
| shipment-count | Целое число (Опционально) | Количество заказов в партии |
| shipment-functionality-checking-rate-sum | Целое число | Сумма платы за проверку вложений с проверкой функциональности в копейках, без НДС |
| shipment-functionality-checking-rate-vat-sum | Целое число | НДС от суммы платы за проверку вложений с проверкой функциональности в копейках |
| shipment-ground-rate-sum | Целое число (Опционально) | Сумма платы за наземную пересылку в копейках, без НДС |
| shipment-ground-rate-vat-sum | Целое число (Опционально) | НДС от суммы платы за наземную пересылку в копейках |
| shipment-insure-rate-sum | Целое число (Опционально) | Сумма платы за объявленную ценность в копейках, без НДС |
| shipment-insure-rate-vat-sum | Целое число (Опционально) | НДС от суммы платы за объявленную ценность в копейках |
| shipment-inventory-rate-sum | Целое число | Сумма платы за опись вложения в копейках, без НДС |
| shipment-inventory-rate-vat-sum | Целое число | НДС от суммы платы за опись вложения в копейках |
| shipment-mass | Целое число (Опционально) | Общий вес в граммах |
| shipment-mass-rate-sum | Целое число (Опционально) | Сумма платы за пересылку в копейках, без НДС |
| shipment-mass-rate-vat-sum | Целое число (Опционально) | НДС от суммы платы за пересылку в копейках |
| shipment-notice-rate-sum | Целое число (Опционально) | Сумма надбавки за уведомление о вручении в копейках |
| shipment-notice-rate-vat-sum | Целое число (Опционально) | НДС от суммы надбавки за уведомление о вручении в копейках |
| shipment-partial-redemption-rate-sum | Целое число | Сумма платы за частичный выкуп в копейках, без НДС |
| shipment-partial-redemption-rate-vat-sum | Целое число | НДС от суммы платы за частичный выкуп в копейках |
| shipment-pre-postal-preparation-rate-sum | Целое число | Сумма платы за услугу 'Предпочтовая подготовка' в копейках, без НДС |
| shipment-pre-postal-preparation-rate-vat-sum | Целое число | НДС от суммы платы за услугу 'Предпочтовая подготовка' в копейках |
| shipment-sms-notice-rate-sum | Целое число | Сумма платы за смс нотификацию в копейках, без НДС |
| shipment-sms-notice-rate-vat-sum | Целое число | НДС от суммы платы за смс нотификацию в копейках |
| shipment-with-fitting-rate-sum | Целое число | Сумма платы за проверку вложений с примеркой в копейках, без НДС |
| shipment-with-fitting-rate-vat-sum | Целое число | НДС от суммы платы за проверку вложений с примеркой в копейках |
| shipping-notice-type | Строка | Категория уведомления о вручении РПО |
| transport-type | Строка | Вид транспортировки |
| ukd | Логические: true или false | УКД |
| use-online-balance | Логические: true или false (Опционально) | Признак использования онлайн-баланса |
| wo-mass | Логические: true или false (Опционально) | Без указания массы |
