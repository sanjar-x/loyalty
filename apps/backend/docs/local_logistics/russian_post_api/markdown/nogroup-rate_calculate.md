# Расчет стоимости пересылки

Рассчитывает стоимость пересылки в зависимости от указанных входных данных. Индекс ОПС точки отправления берется из профиля клиента. Возвращаемые значения указываются в копейках.

**Параметры запроса**

| Параметр | Значение |
|---|---|
| Локальный URL | **/1.0/tariff** |
| Тип | **POST** |

**Заголовки запроса**

| Заголовок | Значение |
|---|---|
| **Authorization** | **AccessToken {токен}** |
| **X-User-Authorization** | **Basic {ключ}** |
| **Content-Type** | **application/json;charset=UTF-8** |

**Тело запроса**

```json
{
  "completeness-checking": true,
  "contents-checking": true,
  "courier": true,
  "declared-value": 0,
  "delivery-point-index": "string",
  "dimension": {
    "height": 0,
    "length": 0,
    "width": 0
  },
  "dimension-type": "S",
  "entries-type": "GIFT",
  "fragile": true,
  "index-from": "string",
  "index-to": "string",
  "inventory": true,
  "mail-category": "SIMPLE",
  "mail-direct": 0,
  "mail-type": "UNDEFINED",
  "mass": 0,
  "notice-payment-method": "CASHLESS",
  "payment-method": "CASHLESS",
  "sms-notice-recipient": 0,
  "transport-type": "SURFACE",
  "vsd": true,
  "with-electronic-notice": true,
  "with-order-of-notice": true,
  "with-simple-notice": true
}
```

| Поле | Тип | Описание |
|---|---|---|
| completeness-checking | Логическое (Опционально) | Признак услуги проверки комплектности |
| contents-checking | Логическое (Опционально) | Признак услуги проверки вложения |
| courier | Логическое (Опционально) | Отметка "Курьер" |
| declared-value | Целое число (Опционально) | Объявленная ценность |
| delivery-point-index | Строка (Опционально) | Идентификатор пункта выдачи заказов |
| dimension | Размеры (Опционально) | Линейные размеры |
| dimension.height | Целое число (Опционально) | Линейная высота (сантиметры) |
| dimension.length | Целое число (Опционально) | Линейная длина (сантиметры) |
| dimension.width | Целое число (Опционально) | Линейная ширина (сантиметры) |
| dimension-type | Строка (Опционально) | [Типоразмер](#/enums-dimension-type) |
| entries-type | Строка | Категория вложения (для международных отправлений). См. [Категория вложения](#/enums-base-entries-type) |
| fragile | Логическое (Опционально) | Отметка "Осторожно/Хрупкое/Терморежим" |
| index-from | Строка (Опционально) | Почтовый индекс объекта почтовой связи места приема |
| index-to | Строка (Опционально) | Почтовый индекс объекта почтовой связи места назначения |
| inventory | Логическое | Опись вложения |
| mail-category | Строка | [Категория РПО](#/enums-base-mail-category) |
| mail-direct | Целое число (Опционально) | Код страны назначения. См. [Код страны](#/dictionary-countries) |
| mail-type | Строка | [Вид РПО](#/enums-base-mail-type) |
| mass | Целое число | Масса отправления в граммах |
| notice-payment-method | Строка (Опционально) | Способ оплаты уведомления. См. [Способ оплаты](#/enums-payment-methods) |
| payment-method | Строка (Опционально) | Способ оплаты. См. [Способ оплаты](#/enums-payment-methods) |
| sms-notice-recipient | Целое число (Опционально) | Признак услуги SMS уведомления |
| transport-type | Строка (Опционально) | [Вид транспортировки](#/enums-base-transport-type) |
| vsd | Логическое (Опционально) | Возврат сопроводительных документов |
| with-electronic-notice | Логическое (Опционально) | Отметка "С электронным уведомлением" |
| with-order-of-notice | Логическое | Отметка "С заказным уведомлением" |
| with-simple-notice | Логическое | Отметка "С простым уведомлением" |

**Ответ на запрос**

```json
{
  "avia-rate": { "rate": 0, "vat": 0 },
  "completeness-checking-rate": { "rate": 0, "vat": 0 },
  "contents-checking-rate": { "rate": 0, "vat": 0 },
  "delivery-time": { "max-days": 0, "min-days": 0 },
  "fragile-rate": { "rate": 0, "vat": 0 },
  "ground-rate": { "rate": 0, "vat": 0 },
  "insurance-rate": { "rate": 0, "vat": 0 },
  "inventory-rate": { "rate": 0, "vat": 0 },
  "notice-payment-method": "CASHLESS",
  "notice-rate": { "rate": 0, "vat": 0 },
  "oversize-rate": { "rate": 0, "vat": 0 },
  "payment-method": "CASHLESS",
  "sms-notice-recipient-rate": { "rate": 0, "vat": 0 },
  "total-rate": 0,
  "total-vat": 0,
  "vsd-rate": { "rate": 0, "vat": 0 }
}
```

| Поле | Тип | Описание |
|---|---|---|
| avia-rate | Тариф (Опционально) | Плата за Авиа-пересылку (коп) |
| avia-rate.rate | Целое число | Тариф без НДС (коп) |
| avia-rate.vat | Целое число (Опционально) | НДС (коп) |
| completeness-checking-rate | Тариф (Опционально) | Плата за "Проверку комплектности" (коп) |
| completeness-checking-rate.rate | Целое число | Тариф без НДС (коп) |
| completeness-checking-rate.vat | Целое число (Опционально) | НДС (коп) |
| contents-checking-rate | Тариф (Опционально) | Плата за "Проверку вложений" (коп) |
| contents-checking-rate.rate | Целое число | Тариф без НДС (коп) |
| contents-checking-rate.vat | Целое число (Опционально) | НДС (коп) |
| delivery-time | Примерные сроки доставки (Опционально) | Время доставки |
| delivery-time.max-days | Целое число | Максимальное время доставки (дни) |
| delivery-time.min-days | Целое число (Опционально) | Минимальное время доставки (дни) |
| fragile-rate | Тариф (Опционально) | Надбавка за отметку "Осторожно/Хрупкое/Терморежим" |
| fragile-rate.rate | Целое число | Тариф без НДС (коп) |
| fragile-rate.vat | Целое число (Опционально) | НДС (коп) |
| ground-rate | Тариф (Опционально) | Плата за пересылку (коп) |
| ground-rate.rate | Целое число | Тариф без НДС (коп) |
| ground-rate.vat | Целое число (Опционально) | НДС (коп) |
| insurance-rate | Тариф (Опционально) | Плата за объявленную ценность (коп) |
| insurance-rate.rate | Целое число | Тариф без НДС (коп) |
| insurance-rate.vat | Целое число (Опционально) | НДС (коп) |
| inventory-rate | Тариф | Плата за "Опись вложения" (коп) |
| inventory-rate.rate | Целое число | Тариф без НДС (коп) |
| inventory-rate.vat | Целое число (Опционально) | НДС (коп) |
| notice-payment-method | Строка (Опционально) | Способ оплаты уведомления. См. [Способ оплаты](#/enums-payment-methods) |
| notice-rate | Тариф (Опционально) | Надбавка за уведомление о вручении |
| notice-rate.rate | Целое число | Тариф без НДС (коп) |
| notice-rate.vat | Целое число (Опционально) | НДС (коп) |
| oversize-rate | Тариф (Опционально) | Надбавка за негабарит при весе более 10кг |
| oversize-rate.rate | Целое число | Тариф без НДС (коп) |
| oversize-rate.vat | Целое число (Опционально) | НДС (коп) |
| payment-method | Строка (Опционально) | Способ оплаты. См. [Способ оплаты](#/enums-payment-methods) |
| sms-notice-recipient-rate | Тариф (Опционально) | Плата за "Пакет смс получателю" (коп) |
| sms-notice-recipient-rate.rate | Целое число | Тариф без НДС (коп) |
| sms-notice-recipient-rate.vat | Целое число (Опционально) | НДС (коп) |
| total-rate | Целое число | Плата всего (коп) |
| total-vat | Целое число | Всего НДС (коп) |
| vsd-rate | Тариф | Плата за "Возврат сопроводительных документов" (коп) |
| vsd-rate.rate | Целое число | Тариф без НДС (коп) |
| vsd-rate.vat | Целое число (Опционально) | НДС (коп) |
