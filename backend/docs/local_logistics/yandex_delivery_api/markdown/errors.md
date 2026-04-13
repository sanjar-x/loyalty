# API Доставки в другой день — Справочник ошибок

## Ошибки API

| Код | Текст ошибки | Описание |
|-----|-------------|----------|
| 400 | `Cannot parse destination info` | Система не может определить адрес доставки. Требуемый формат передачи адреса: `Город, улица, дом` |
| 400 | `There already was request with such code within this employer, request_id` | Дублирование номера заказа. Параметр `operator_request_id` должен быть уникальным для каждого заказа |
| 400 | `Cant get station id for point` | Не получилось определить станцию. Убедитесь, что передали корректные ID станций |
| 400 | `Payment on delivery option is not available for courier delivery` | В курьерской доставке отсутствует оплата при получении |
| 400 | `Сant calc routes because destination station is disabled` | Точка Б деактивирована |
| 400 | `Pickup point doesn't accept payment on delivery. Choose another pickup point or payment method` / `Pickup point doesn't accept prepaid orders. Choose another pickup point or payment method` | Способ оплаты на точке Б не поддерживается |
| 400 | `Particular items refuse is not allowed for courier delivery` | В курьерской доставке отсутствует частичный выкуп |
| 400 | `Fitting of items is not available for courier delivery` | В курьерской доставке отсутствует опция примерки |
| 400 | `Particular items refuse is not allowed for pickup point` | На точке Б отсутствует опция частичного выкупа |
| 400 | `Fitting of items is not available for pickup point` | На точке Б отсутствует опция примерки |
| 401 | `Access denied` | Проблемы с авторизацией. Проверьте токен |
| 404 | `No delivery options` | Нет доступных опций доставки для этого заказа. Возможные причины: для собственного склада — отсутствует график отгрузок в личном кабинете Яндекс Доставки; для доставки до ПВЗ — недоступен указанный метод оплаты на ПВЗ доставки; габариты грузомест не соответствуют правилам отгрузки; этот маршрут недоступен для доставки |
| 404 | `No dropoff available` | Недоступна отгрузка с этой станции. Возможные причины: отсутствует график отгрузки для собственного склада в личном кабинете Яндекс Доставки; для отгрузки с ПВЗ — невозможно отгрузить товар с этого ПВЗ; недостаточно средств на балансе |
| 404 | `Dimensions should not exceed limit` | Габариты превышают максимально допустимые. Убедитесь, что габариты соответствуют правилам отгрузки. Признак: `"available_for_dropoff": false` |

## Ошибки по категориям

### Ошибки валидации (400)

| Текст ошибки | Категория |
|-------------|-----------|
| `Cannot parse destination info` | Адрес |
| `There already was request with such code within this employer, request_id` | Дублирование |
| `Cant get station id for point` | Станция |
| `Payment on delivery option is not available for courier delivery` | Оплата |
| `Сant calc routes because destination station is disabled` | Станция |
| `Pickup point doesn't accept payment on delivery` | Оплата |
| `Pickup point doesn't accept prepaid orders` | Оплата |
| `Particular items refuse is not allowed for courier delivery` | Частичный выкуп |
| `Fitting of items is not available for courier delivery` | Примерка |
| `Particular items refuse is not allowed for pickup point` | Частичный выкуп |
| `Fitting of items is not available for pickup point` | Примерка |

### Ошибки авторизации (401)

| Текст ошибки | Категория |
|-------------|-----------|
| `Access denied` | Авторизация |

### Ошибки ресурсов (404)

| Текст ошибки | Категория |
|-------------|-----------|
| `No delivery options` | Опции доставки |
| `No dropoff available` | Отгрузка |
| `Dimensions should not exceed limit` | Габариты |

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | Статусная модель | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/status-model) |
| Следующая | Список методов | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/errors](https://yandex.com/support/delivery-profile/ru/api/other-day/errors)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > Справочник ошибок
