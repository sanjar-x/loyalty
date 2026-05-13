# Нормализация адреса

Разделяет и помещает сущности переданных адресов (город, улица) в соответствующие поля возвращаемого объекта. Параметр id (идентификатор записи) используется для установления соответствия переданных и полученных записей, так как порядок сортировки возвращаемых записей не гарантируется. Метод автоматически ищет и возвращает индекс близлежащего ОПС по указанному адресу.

**Адрес считается корректным к отправке, если в ответе запроса:**

- [quality-code](#/enums-clean-address-quality)=GOOD, POSTAL_BOX, ON_DEMAND или UNDEF_05;
- [validation-code](#/enums-clean-address-validation)=VALIDATED, OVERRIDDEN или CONFIRMED_MANUALLY.

**Параметры запроса**

| Параметр | Значение |
|---|---|
| Локальный URL | **/1.0/clean/address** |
| Тип | **POST** |

**Заголовки запроса**

| Заголовок | Значение |
|---|---|
| **Authorization** | **AccessToken {токен}** |
| **X-User-Authorization** | **Basic {ключ}** |
| **Content-Type** | **application/json;charset=UTF-8** |

**Тело запроса**

```json
[
  {
    "id": "string",
    "original-address": "string"
  }
]
```

| Поле | Тип | Описание |
|---|---|---|
| id | Строка | Идентификатор записи |
| original-address | Строка | Оригинальные адрес одной строкой |

**Внимание!**
Анализируйте **код качества (quality-code)** и **код проверки (validation-code)** в ответах.

[Код качества](#/enums-clean-address-quality) должен быть: GOOD, POSTAL_BOX, ON_DEMAND или UNDEF_05.
[Код проверки](#/enums-clean-address-validation) должен быть: VALIDATED, OVERRIDDEN или CONFIRMED_MANUALLY.

Иначе нормализуемый адрес может быть неприемлем для доставки!

**Ответ на запрос**

```json
[
  {
    "address-type": "DEFAULT",
    "area": "string",
    "building": "string",
    "corpus": "string",
    "hotel": "string",
    "house": "string",
    "id": "string",
    "index": "string",
    "letter": "string",
    "location": "string",
    "num-address-type": "string",
    "original-address": "string",
    "place": "string",
    "quality-code": "GOOD",
    "region": "string",
    "room": "string",
    "slash": "string",
    "street": "string",
    "validation-code": "CONFIRMED_MANUALLY"
  }
]
```

| Поле | Тип | Описание |
|---|---|---|
| address-type | Строка | [Тип адреса](#/enums-base-address-type) |
| area | Строка (Опционально) | Район |
| building | Строка (Опционально) | Часть здания: Строение |
| corpus | Строка (Опционально) | Часть здания: Корпус |
| hotel | Строка (Опционально) | Название гостиницы |
| house | Строка (Опционально) | Часть адреса: Номер здания |
| id | Строка | Идентификатор записи |
| index | Строка | Почтовый индекс |
| letter | Строка (Опционально) | Часть здания: Литера |
| location | Строка (Опционально) | Микрорайон |
| num-address-type | Строка (Опционально) | Номер для а/я, войсковая часть, войсковая часть ЮЯ, полевая почта |
| original-address | Строка | Оригинальные адрес одной строкой |
| place | Строка | Населенный пункт |
| quality-code | Строка | [Код качества нормализации адреса](#/enums-clean-address-quality) |
| region | Строка | Область, регион |
| room | Строка (Опционально) | Часть здания: Номер помещения |
| slash | Строка (Опционально) | Часть здания: Дробь |
| street | Строка (Опционально) | Часть адреса: Улица |
| validation-code | Строка | [Код проверки нормализации адреса](#/enums-clean-address-validation) |
