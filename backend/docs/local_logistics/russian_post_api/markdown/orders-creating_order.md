# Создание заказа

Создает новый заказ. Автоматически рассчитывает и проставляет плату за пересылку.

## Параметры запроса

| Параметр | Значение |
|----------|----------|
| Локальный URL | **/1.0/user/backlog** |
| Тип | **PUT** |

## Заголовки запроса

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | **AccessToken {token}** |
| **X-User-Authorization** | **Basic {key}** |
| **Content-Type** | **application/json;charset=UTF-8** |

## Тело запроса

```json
[
  {
    "add-to-mmo": true,
    "address-from": { ... },
    "address-type-to": "DEFAULT",
    "area-to": "string",
    "branch-name": "string",
    "building-to": "string",
    "comment": "string",
    "completeness-checking": true,
    "compulsory-payment": 0,
    "corpus-to": "string",
    "courier": true,
    "customs-declaration": { ... },
    "delivery-to-door": true,
    "delivery-with-cod": true,
    "dimension": { ... },
    "dimension-type": "S",
    "easy-return": true,
    "ecom-data": { ... },
    "envelope-type": "C4",
    "farma": true,
    "fiscal-data": { ... },
    "fragile": true,
    "given-name": "string",
    "goods": { ... },
    "group-name": "string",
    "hotel-to": "string",
    "house-to": "string",
    "index-to": 0,
    "inner-num": "string",
    "insr-value": 0,
    "inventory": true,
    "letter-to": "string",
    "location-to": "string",
    "manual-address-input": true,
    "mail-category": "SIMPLE",
    "mail-direct": 0,
    "mail-type": "UNDEFINED",
    "mass": 0,
    "middle-name": "string",
    "no-return": true,
    "notice-payment-method": "CASHLESS",
    "num-address-type-to": "string",
    "office-to": "string",
    "order-num": "string",
    "payment": 0,
    "payment-method": "CASHLESS",
    "place-to": "string",
    "postoffice-code": "string",
    "pre-postal-preparation": true,
    "prepaid-amount": 0,
    "raw-address": "string",
    "recipient-name": "string",
    "region-to": "string",
    "room-to": "string",
    "sender-comment": "string",
    "sender-name": "string",
    "shelf-life-days": 0,
    "slash-to": "string",
    "sms-notice-recipient": 0,
    "str-index-to": "string",
    "street-to": "string",
    "surname": "string",
    "tariff-count": 1,
    "tel-address": 0,
    "tel-address-from": 0,
    "time-slot-id": 0,
    "tender": true,
    "transport-mode": "STANDARD",
    "transport-type": "SURFACE",
    "vladenie-to": "string",
    "vsd": true,
    "with-discount": true,
    "with-documents": true,
    "with-electronic-notice": true,
    "with-goods": true,
    "with-order-of-notice": true,
    "with-packaging": true,
    "with-simple-notice": true,
    "with-uzeuv-notice": true,
    "wo-mail-rank": true,
    "seller-id": "string",
    "payment-details": { ... }
  }
]
```

### Поля тела запроса

| Поле | Тип | Описание |
|------|-----|----------|
| add-to-mmo | Логические: true или false (Опционально) | Отметка 'Добавить в многоместное отправление' |
| **address-from** | **Тип адреса возврата (Опционально)** | **Адрес забора заказа** |
| address-from.address-type | Строка | Тип адреса |
| address-from.area | Строка (Опционально) | Район |
| address-from.building | Строка (Опционально) | Часть здания: Строение |
| address-from.corpus | Строка (Опционально) | Часть здания: Корпус |
| address-from.hotel | Строка (Опционально) | Название гостиницы |
| address-from.house | Строка (Опционально) | Часть адреса: Номер здания |
| address-from.index | Строка | Почтовый индекс |
| address-from.letter | Строка (Опционально) | Часть здания: Литера |
| address-from.location | Строка (Опционально) | Микрорайон |
| address-from.num-address-type | Строка (Опционально) | Номер для а/я, войсковая часть, войсковая часть ЮЯ, полевая почта |
| address-from.office | Строка (Опционально) | Часть здания: Офис |
| address-from.place | Строка | Населенный пункт |
| address-from.region | Строка | Область, регион |
| address-from.room | Строка (Опционально) | Часть здания: Номер помещения |
| address-from.slash | Строка (Опционально) | Часть здания: Дробь |
| address-from.street | Строка (Опционально) | Часть адреса: Улица |
| address-from.vladenie | Строка (Опционально) | Часть адреса: Владение |
| address-type-to | Строка | Тип адреса |
| area-to | Строка (Опционально) | Район |
| branch-name | Строка (Опционально) | Идентификатор подразделения |
| building-to | Строка (Опционально) | Часть здания: Строение |
| comment | Строка (Опционально) | Комментарий к заказу |
| completeness-checking | Логические: true или false (Опционально) | Признак услуги проверки комплектности |
| compulsory-payment | Целое число (Опционально) | К оплате с получателя (копейки) |
| corpus-to | Строка (Опционально) | Часть здания: Корпус |
| courier | Логические: true или false (Опционально) | Отметка "Курьер" |
| **customs-declaration** | **Декларация (Опционально)** | **Таможенная декларация (для международных отправлений)** |
| customs-declaration.certificate-number | Строка (Опционально) | Сертификаты, сопровождающие отправление |
| customs-declaration.currency | Строка | Код валюты |
| customs-declaration.customs-code | Строка (Опционально) | Код таможенного органа |
| customs-declaration.customs-entries | Массив | Список вложений |
| customs-declaration.customs-entries[].amount | Целое число | Количество |
| customs-declaration.customs-entries[].country-code | Целое число (Опционально) | Код страны происхождения |
| customs-declaration.customs-entries[].description | Строка | Наименование товара |
| customs-declaration.customs-entries[].tnved-code | Строка | Код ТНВЭД |
| customs-declaration.customs-entries[].trademark | Строка (Опционально) | Торговая марка |
| customs-declaration.customs-entries[].value | Целое число (Опционально) | Цена за единицу товара в копейках (вкл. НДС) |
| customs-declaration.customs-entries[].weight | Целое число (Опционально) | Вес товара (в граммах) |
| customs-declaration.entries-type | Строка | Категория вложения |
| customs-declaration.invoice-number | Строка (Опционально) | Счет (номер счета-фактуры) |
| customs-declaration.ioss-code | Строка (Опционально) | Регистрационный код продавца |
| customs-declaration.license-number | Строка (Опционально) | Лицензии, сопровождающие отправление |
| customs-declaration.with-certificate | Логические: true или false (Опционально) | Приложенные документы: сертификат |
| customs-declaration.with-invoice | Логические: true или false (Опционально) | Приложенные документы: счет-фактура |
| customs-declaration.with-license | Логические: true или false (Опционально) | Приложенные документы: лицензия |
| delivery-to-door | Логические: true или false (Опционально) | Отметка 'Доставка до двери' |
| delivery-with-cod | Логические: true или false (Опционально) | Признак оплаты при получении |
| **dimension** | **Размеры (Опционально)** | **Линейные размеры** |
| dimension.height | Целое число (Опционально) | Линейная высота (сантиметры) |
| dimension.length | Целое число (Опционально) | Линейная длина (сантиметры) |
| dimension.width | Целое число (Опционально) | Линейная ширина (сантиметры) |
| dimension-type | Строка (Опционально) | Типоразмер |
| easy-return | Логические: true или false (Опционально) | Лёгкий возврат |
| **ecom-data** | **Данные ЕКОМ (Опционально)** | **Данные отправления ЕКОМ** |
| ecom-data.delivery-point-index | Строка (Опционально) | Идентификатор пункта выдачи заказов |
| ecom-data.identity-methods | Массив (Опционально) | Методы идентификации |
| ecom-data.services | Массив (Опционально) | Сервисы ЕКОМ |
| envelope-type | Строка (Опционально) | Тип конверта - ГОСТ Р 51506-99 |
| farma | Логические: true или false (Опционально) | Отметка 'Фарма' |
| **fiscal-data** | **Фискальные данные (Опционально)** | **Фискальные данные** |
| fiscal-data.customer-email | Строка (Опционально) | Адрес электронной почты плательщика |
| fiscal-data.customer-inn | Строка (Опционально) | ИНН юридического лица покупателя |
| fiscal-data.customer-name | Строка (Опционально) | Наименование юридического лица покупателя |
| fiscal-data.customer-phone | Целое число (Опционально) | Телефон плательщика |
| fiscal-data.payment-amount | Целое число (Опционально) | Сумма предоплаты (копейки) |
| fragile | Логические: true или false | Установлена ли отметка "Осторожно/Хрупкое/Терморежим"? |
| given-name | Строка | Имя получателя |
| **goods** | **Товарное вложение РПО (Опционально)** | **Товарное вложение РПО** |
| goods.items | Массив | Список вложений |
| goods.items[].code | Строка (Опционально) | Код (маркировка) товара |
| goods.items[].country-code | Целое число (Опционально) | Код страны происхождения |
| goods.items[].customs-declaration-number | Строка (Опционально) | Номер таможенной декларации |
| goods.items[].description | Строка | Наименование товара |
| goods.items[].excise | Целое число (Опционально) | Акциз (копейки) |
| goods.items[].good-id | Строка (Опционально) | Внутренний идентификатор товара у поставщика |
| goods.items[].goods-type | Строка (Опционально) | Признак товар или услуга |
| goods.items[].insr-value | Целое число (Опционально) | Объявленная ценность (копейки) |
| goods.items[].item-number | Строка (Опционально) | Номенклатура (артикул) товара |
| goods.items[].lineattr | Целое число (Опционально) | Признак предмета расчета |
| goods.items[].payattr | Целое число (Опционально) | Признак способа расчета |
| goods.items[].quantity | Число | Количество товара |
| goods.items[].service-type | Целое число (Опционально) | Вид сервиса для товара: 1 - без вскрытия (по умолчанию), 2 - с осмотром вложения, 3 - с примеркой |
| goods.items[].supplier-inn | Строка (Опционально) | ИНН поставщика товара |
| goods.items[].supplier-name | Строка (Опционально) | Наименование поставщика товара |
| goods.items[].supplier-phone | Строка (Опционально) | Телефон поставщика товара |
| goods.items[].value | Целое число (Опционально) | Цена за единицу товара в копейках (вкл. НДС) |
| goods.items[].vat-rate | Целое число (Опционально) | Ставка НДС: Без НДС(-1), 0, 10, 110, 20, 120 |
| goods.items[].weight | Целое число (Опционально) | Вес товара (в граммах) |
| group-name | Строка (Опционально) | Наименование группы (для Многоместных отправлений) |
| hotel-to | Строка (Опционально) | Название гостиницы |
| house-to | Строка | Часть адреса: Номер здания |
| index-to | Целое число | Почтовый индекс, для отправлений адресованных в почтомат или пункт выдачи, должен использоваться объект "ecom-data". Для отправления по РФ |
| inner-num | Строка (Опционально) | Дополнительный идентификатор отправления |
| insr-value | Целое число (Опционально) | Объявленная ценность (копейки) |
| inventory | Логические: true или false (Опционально) | Наличие описи вложения |
| letter-to | Строка (Опционально) | Часть здания: Литера |
| location-to | Строка (Опционально) | Микрорайон |
| manual-address-input | Логические: true или false (Опционально) | Признак ручного ввода адреса |
| mail-category | Строка | Категория РПО |
| mail-direct | Целое число | Код страны |
| mail-type | Строка | Вид РПО |
| mass | Целое число | Вес РПО (в граммах) |
| middle-name | Строка (Опционально) | Отчество получателя |
| no-return | Логические: true или false (Опционально) | Отметка "Возврату не подлежит" |
| notice-payment-method | Строка (Опционально) | Способ оплаты уведомления |
| num-address-type-to | Строка (Опционально) | Номер для а/я, войсковая часть, войсковая часть ЮЯ, полевая почта |
| office-to | Строка (Опционально) | Часть здания: Офис |
| order-num | Строка | Номер заказа. Внешний идентификатор заказа, который формируется отправителем |
| payment | Целое число (Опционально) | Сумма наложенного платежа (копейки) |
| payment-method | Строка (Опционально) | Способ оплаты |
| place-to | Строка | Населенный пункт |
| postoffice-code | Строка | Индекс места приема |
| pre-postal-preparation | Логические: true или false (Опционально) | Предпочтовая подготовка |
| prepaid-amount | Целое число (Опционально) | Сумма частичной предоплаты |
| raw-address | Строка (Опционально) | Необработанный адрес получателя |
| recipient-name | Строка | Наименование получателя одной строкой (ФИО, наименование организации) |
| region-to | Строка | Область, регион |
| room-to | Строка (Опционально) | Часть здания: Номер помещения |
| sender-comment | Строка (Опционально) | Комментарий отправителя для ЭУВ |
| sender-name | Строка (Опционально) | Наименование отправителя одной строкой (ФИО, наименование организации) |
| shelf-life-days | Целое число (Опционально) | Срок хранения отправления от 15 до 60 дней |
| slash-to | Строка (Опционально) | Часть здания: Дробь |
| sms-notice-recipient | Целое число (Опционально) | Признак услуги SMS уведомления |
| str-index-to | Строка | Почтовый индекс (буквенно-цифровой). Для международных отправлений |
| street-to | Строка | Часть адреса: Улица |
| surname | Строка | Фамилия получателя |
| tariff-count | Целое число | Количество тарифов: 1 - только полный тариф, 2 - полный и скидочный тарифы |
| tariff-discount-rate | Строка | Итоговая стоимость отправления со скидкой без учета НДС |
| tariff-discount-rate-vat | Строка | НДС итоговой стоимости отправления со скидкой |
| tariff-discount-rate-with-vat | Строка | Итоговая стоимость отправления со скидкой с учетом НДС |
| tariff-full-rate | Строка | Итоговая стоимость отправления без скидки без учета НДС |
| tariff-full-rate-vat | Строка | НДС итоговой стоимости отправления без скидки |
| tariff-full-rate-with-vat | Строка | Итоговая стоимость отправления без скидки с учетом НДС |
| tel-address | Целое число (Опционально) | Телефон получателя (может быть обязательным для некоторых типов отправлений) |
| tel-address-from | Целое число (Опционально) | Телефон отправителя |
| time-slot-id | Целое число (Опционально) | Идентификатор временного интервала |
| tender | Логические: true или false (Опционально) | Доступно только для отправлений «ЕКОМ Маркетплейс». Отметка указывает на перевозку грузоотправлений ЕКОМ Маркетплейс, принятых в рамках заключенных тендерных договоров |
| transport-mode | Строка (Опционально) | Возможный режим транспортировки (только для типа отправлений EMS Тендер) |
| transport-type | Строка (Опционально) | Возможный вид транспортировки (для международных отправлений) |
| vladenie-to | Строка (Опционально) | Часть здания: Владение |
| vsd | Логические: true или false (Опционально) | Возврат сопроводительных документов |
| with-discount | Логические: true или false (Опционально) | true - тариф со скидкой, false - тариф без скидки |
| with-documents | Логические: true или false (Опционально) | С документами (для ЕМС международного) |
| with-electronic-notice | Логические: true или false (Опционально) | Отметка 'С электронным уведомлением' |
| with-goods | Логические: true или false (Опционально) | С товарами (для ЕМС международного) |
| with-order-of-notice | Логические: true или false (Опционально) | Отметка 'С заказным уведомлением' |
| with-packaging | Логические: true или false (Опционально) | Отметка 'С упаковкой' |
| with-simple-notice | Логические: true или false (Опционально) | Отметка 'С простым уведомлением' |
| with-uzeuv-notice | Логические: true или false (Опционально) | Отметка 'С ЮЗЭУВ' |
| wo-mail-rank | Логические: true или false (Опционально) | Отметка "Без разряда" |
| seller-id | Строка (Опционально) | Идентификатор отправителя на торговой площадке |
| **payment-details** | **Реквизиты получателя наложенного платежа (Опционально)** | **Реквизиты получателя наложенного платежа** |
| payment-details.recipient-surname | Строка (Опционально) | Фамилия получателя наложенного платежа |
| payment-details.recipient-firstname | Строка (Опционально) | Имя получателя наложенного платежа |
| payment-details.recipient-middlename | Строка (Опционально) | Отчество получателя наложенного платежа |
| payment-details.bank-name | Строка (Опционально) | Наименование банка получателя наложенного платежа |
| payment-details.bank-bik | Строка (Опционально) | БИК банка получателя наложенного платежа |
| payment-details.bank-corr-account | Строка (Опционально) | Корреспондентский счет получателя наложенного платежа |
| payment-details.bank-account | Строка (Опционально) | Счет получателя наложенного платежа |
| payment-details.is-cash | Строка (Опционально) | Признак получения наложенного платежа наличными |

## Ответ на запрос

```json
{
  "errors": [
    {
      "error-codes": [
        {
          "code": "UNDEFINED",
          "description": "string",
          "details": "string",
          "position": 0
        }
      ],
      "position": 0
    }
  ],
  "result-ids": [
    0
  ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| errors | Массив (Опционально) | Список ошибок |
| errors[].error-codes | Массив | Список кодов ошибок |
| errors[].error-codes[].code | Строка | Код ошибки |
| errors[].error-codes[].description | Строка (Опционально) | Описание ошибки |
| errors[].error-codes[].details | Строка (Опционально) | Описание ошибки |
| errors[].error-codes[].position | Целое число (Опционально) | Индекс в массиве |
| errors[].position | Целое число (Опционально) | Индекс в массиве |
| result-ids | Массив (Опционально) | Список успешно созданных внутренних идентификаторов отправлений |
