# Текущие настройки пользователя

## Параметры запроса

| Параметр | Значение |
|----------|----------|
| Локальный URL | **/1.0/settings** |
| Тип | **GET** |

## Заголовки запроса

| Заголовок | Значение |
|-----------|----------|
| **Authorization** | **AccessToken {token}** |
| **X-User-Authorization** | **Basic {key}** |
| **Content-Type** | **application/json;charset=UTF-8** |

## Ответ на запрос

| Параметр | Тип | Описание |
|----------|-----|----------|
| account-admin | Логическое | Признак администратора аккаунта |
| account-declaration-enabled | Логическое (Опционально) | Доступность подачи электронной декларации для сабаккаунта |
| account-erl-enabled | Логическое | Доступность функционала ЭЗП для сабаккаунта |
| account-esignature-enabled | Логическое (Опционально) | Флаг использования электронной подписи для сабаккаунта |
| accounts | Массив | Список компаний |
| accounts[].address | Тип адреса возврата (Опционально) | Адрес возврата |
| accounts[].blocked | Логическое | Признак блокировки |
| accounts[].email | Строка (Опционально) | Контактный email |
| accounts[].is-admin | Логическое (Опционально) | Признак администратора |
| accounts[].legal-hid | Строка (Опционально) | Идентификатор компании (ЮЛ) |
| accounts[].org-inn | Строка (Опционально) | ИНН |
| accounts[].org-name | Строка (Опционально) | Наименование |
| address | Тип адреса возврата (Опционально) | Адрес возврата |
| address.address-type | Строка | Тип адреса |
| address.area | Строка (Опционально) | Район |
| address.building | Строка (Опционально) | Часть здания: Строение |
| address.corpus | Строка (Опционально) | Часть здания: Корпус |
| address.hotel | Строка (Опционально) | Название гостиницы |
| address.house | Строка (Опционально) | Часть адреса: Номер здания |
| address.index | Строка | Почтовый индекс |
| address.letter | Строка (Опционально) | Часть здания: Литера |
| address.location | Строка (Опционально) | Микрорайон |
| address.manual-address-input | Логическое (Опционально) | Признак ручного ввода адреса |
| address.num-address-type | Строка (Опционально) | Номер для а/я, войсковая часть, войсковая часть ЮЯ, полевая почта |
| address.office | Строка (Опционально) | Часть здания: Офис |
| address.place | Строка | Населенный пункт |
| address.region | Строка | Область, регион |
| address.room | Строка (Опционально) | Часть здания: Номер помещения |
| address.slash | Строка (Опционально) | Часть здания: Дробь |
| address.street | Строка (Опционально) | Часть адреса: Улица |
| address.vladenie | Строка (Опционально) | Часть адреса: Владение |
| address-book-enabled | Логическое | Адресная книга включена |
| address-change-enabled | Логическое | Флаг разрешения функционала проверки изменения адреса получателя |
| admin-hid | Строка | Внутренний идентификатор администратора |
| agreement-date | Строка (Опционально) | Дата договора (yyyy-MM-dd) |
| agreement-kind | Строка (Опционально) | Вид договора. Возможные значения: `CONTRACT`, `PUBLIC_OFFER`, `CONTRACT_ELECTRONIC` |
| agreement-number | Строка (Опционально) | Номер договора |
| agreement-version | Строка (Опционально) | Версия договора |
| api_enabled | Логическое | Флаг доступа к API |
| apig_access_token | Строка | API Gateway access token |
| available-shipping-points | Массив (Опционально) | Все точки сдачи |
| available-shipping-points[].additional-operator-postcode | Строка (Опционально) | ДТИ (дополнительный технический индекс). Deprecated. Используйте `additional-operator-postcodes` |
| available-shipping-points[].additional-operator-postcodes | Массив (Опционально) | Список ДТИ (дополнительный технический индекс) |
| available-shipping-points[].available-additional-operator-postcodes | Массив (Опционально) | Список доступных ДТИ |
| available-shipping-points[].available-mail-types | Массив (Опционально) | Разрешенные почтовые типы отправлений |
| available-shipping-points[].available-products | Массив (Опционально) | Список доступных продуктов |
| available-shipping-points[].available-products[].mail-category | Строка | Категория почтового отправления |
| available-shipping-points[].available-products[].mail-type | Строка | Тип почтового отправления |
| available-shipping-points[].available-products[].product-type | Строка | Тип продукта |
| available-shipping-points[].available-products[].sms-notice-recipient-enabled | Логическое | Признак доступности услуги SMS уведомления получателя |
| available-shipping-points[].available-return-addresses | Массив (Опционально) | Доступные адреса возврата в точке сдачи |
| available-shipping-points[].available-return-addresses[].address | Тип адреса возврата (Опционально) | Адрес возврата |
| available-shipping-points[].available-return-addresses[].return-address-id | Целое число | Идентификатор адреса возврата |
| available-shipping-points[].courier-call | Логическое (Опционально) | Признак доступности услуги "Вызов курьера" |
| available-shipping-points[].enabled | Логическое (Опционально) | Признак активации |
| available-shipping-points[].operator-postcode | Строка | Индекс почтового отделения обслуживания |
| available-shipping-points[].ops-address | Строка (Опционально) | Адрес ОПС |
| available-shipping-points[].po-box | Строка (Опционально) | Номер абонентского ящика |
| available-shipping-points[].pre-postal-preparation | Логическое (Опционально) | Признак доступности услуги "Предпочтовая подготовка" |
