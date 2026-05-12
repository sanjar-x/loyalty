# Создание заказов

Перед формированием заказа необходимо воспользоваться сервисами нормализации (адрес, телефон, ФИО). Данные, прошедшие нормализацию, будут использоваться при формировании заказа.

#### Предварительная нормализация данных:

**Нормализация адреса:**

```
curl -X POST --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
-d '[
  {
    "id": "1",
    "original-address": "г. Москва, Варшавское шоссе, 37"
  }
]' "https://iplatform-extapi.test.russianpost.ru/1.0/clean/address"
```

Response body:

```json
[
  {
    "address-type": "DEFAULT",
    "house": "37",
    "id": "1",
    "index": "117105",
    "original-address": "г. Москва, Варшавское шоссе, 37",
    "place": "г Москва",
    "quality-code": "GOOD",
    "region": "г Москва",
    "room": "1",
    "street": "ш Варшавское",
    "valid": true,
    "validation-code": "VALIDATED"
  }
]
```

**Нормализация ФИО:**

```
curl -X POST --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
-d '[
  {
    "id": "1",
    "original-fio": "Иванов Иван Иванович"
  }
]' "https://iplatform-extapi.test.russianpost.ru/1.0/clean/physical"
```

Response body:

```json
[
  {
    "id": "1",
    "middle-name": "Иванович",
    "name": "Иван",
    "original-fio": "Иванов Иван Иванович",
    "quality-code": "EDITED",
    "surname": "Иванов",
    "valid": true
  }
]
```

**Нормализация телефона:**

```
curl -X POST --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
-d '[
  {
    "area": "г Москва",
    "id": "1",
    "original-phone": "956-20-67",
    "place": "Москва"
  }
]' "https://iplatform-extapi.test.russianpost.ru/1.0/clean/phone"
```

Response body:

```json
[
  {
    "id": "1",
    "original-phone": "956-20-67",
    "phone-city-code": "495",
    "phone-country-code": "7",
    "phone-extension": "",
    "phone-number": "9562067",
    "quality-code": "GOOD_CITY",
    "valid": true
  }
]
```

#### Создание заказа - посылка "нестандартная", тип отправления - обычный (без объявленной ценности и наложенного платежа):

```
curl -X PUT --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
-d '[
  {
    "address-type-to": "DEFAULT",
    "given-name": "Иван",
    "house-to": "37",
    "index-to": 117105,
    "mail-category": "ORDINARY",
    "mail-direct": 643,
    "mail-type": "POSTAL_PARCEL",
    "mass": 2000,
    "middle-name": "Иванович",
    "order-num": "заказ1",
    "place-to": "г Москва",
    "region-to": "г Москва",
    "street-to": "ш Варшавское",
    "surname": "Иванов",
    "tel-address": 79459562067
  }
]' "https://iplatform-extapi.test.russianpost.ru/1.0/user/backlog"
```

Response body:

```json
{
  "result-ids": [
    1657696
  ]
}
```

#### Создание заказа - посылка "нестандартная", тип отправления - c объявленной ценностью:

Добавлено поле insr-value, изменен тип отправления (WITH_DECLARED_VALUE)

```
curl -X PUT --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
-d '[
  {
    "address-type-to": "DEFAULT",
    "given-name": "Иван",
    "house-to": "37",
    "index-to": 117105,
    "insr-value": 150000,
    "mail-category": "WITH_DECLARED_VALUE",
    "mail-direct": 643,
    "mail-type": "POSTAL_PARCEL",
    "mass": 2000,
    "middle-name": "Иванович",
    "order-num": "заказ2",
    "place-to": "г Москва",
    "region-to": "г Москва",
    "street-to": "ш Варшавское",
    "surname": "Иванов",
    "tel-address": 79459562067
  }
]' "https://iplatform-extapi.test.russianpost.ru/1.0/user/backlog"
```

Response body:

```json
{
  "result-ids": [
    1657697
  ]
}
```

#### Создание заказа - посылка "нестандартная", тип отправления - c объявленной ценностью и наложенным платежом:

Добавлено поле payment, изменен тип отправления (WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY)

```
curl -X PUT --header "Content-Type: application/json"
--header "Accept: application/json;charset=UTF-8"
--header "Authorization: AccessToken 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
--header "X-User-Authorization: Basic bG9naW46cGFzc3dvcmQ="
-d '[
  {
    "address-type-to": "DEFAULT",
    "given-name": "Иван",
    "house-to": "37",
    "index-to": 117105,
    "insr-value": 150000,
    "mail-category": "WITH_DECLARED_VALUE_AND_CASH_ON_DELIVERY",
    "mail-direct": 643,
    "mail-type": "POSTAL_PARCEL",
    "mass": 2000,
    "middle-name": "Иванович",
    "order-num": "заказ3",
    "payment": 150000,
    "place-to": "г Москва",
    "region-to": "г Москва",
    "street-to": "ш Варшавское",
    "surname": "Иванов",
    "tel-address": 79459562067
  }
]' "https://iplatform-extapi.test.russianpost.ru/1.0/user/backlog"
```

Response body:

```json
{
  "result-ids": [
    1657698
  ]
}
```
