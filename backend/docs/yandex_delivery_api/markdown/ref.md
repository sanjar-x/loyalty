# API Доставки в другой день — Список методов

## Содержание

- [1. Подготовка заявки](#1-подготовка-заявки)
- [2. Точки самопривоза и ПВЗ](#2-точки-самопривоза-и-пвз)
- [3. Основные запросы](#3-основные-запросы)
- [4. Ярлыки и акты приема-передачи](#4-ярлыки-и-акты-приема-передачи)
- [5. Управление мерчантами](#5-управление-мерчантами)
- [6. Управление складами и отгрузками](#6-управление-складами-и-отгрузками)

---

## 1. Подготовка заявки

| HTTP-метод | Эндпоинт | Описание | Документация |
|------------|----------|----------|--------------|
| POST | `/api/b2b/platform/pricing-calculator` | Расчет стоимости доставки на основании переданных параметров заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformpricing-calculator-post) |
| GET | `/api/b2b/platform/offers/info` | Получение расписания вывозов в регионы | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-get) |
| POST | `/api/b2b/platform/offers/info` | Получение расписания вывозов в регионы | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformoffersinfo-post) |

## 2. Точки самопривоза и ПВЗ

| HTTP-метод | Эндпоинт | Описание | Документация |
|------------|----------|----------|--------------|
| POST | `/api/b2b/platform/location/detect` | Получение идентификатора населенного пункта (`geo_id`) по адресу или его фрагменту | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformlocationdetect-post) |
| POST | `/api/b2b/platform/pickup-points/list` | Получение списка точек самопривоза и самостоятельного получения заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/2.-Tochki-samoprivoza-i-PVZ/apib2bplatformpickup-pointslist-post) |

## 3. Основные запросы

| HTTP-метод | Эндпоинт | Описание | Документация |
|------------|----------|----------|--------------|
| POST | `/api/b2b/platform/offers/create` | Получение вариантов доставки (офферов) для переданного заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformofferscreate-post) |
| POST | `/api/b2b/platform/offers/confirm` | Бронирование выбранного варианта доставки (оффера) | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformoffersconfirm-post) |
| GET | `/api/b2b/platform/request/info` | Получение информации о заявке и ее текущем статусе | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestinfo-get) |
| POST | `/api/b2b/platform/requests/info` | Получение информации о заявках, созданных в заданный временной интервал | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestsinfo-post) |
| GET | `/api/b2b/platform/request/actual_info` | Получение актуальной даты и времени доставки | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestactual_info-get) |
| POST | `/api/b2b/platform/request/edit` | Заявка на редактирование заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestedit-post) |
| POST | `/api/b2b/platform/request/datetime_options` | Получение интервалов доставки для нового места получения заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestdatetime_options-post) |
| POST | `/api/b2b/platform/request/redelivery_options` | Получение интервалов доставки для нового места получения заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestredelivery_options-post) |
| GET | `/api/b2b/platform/request/history` | Получение информации об истории статусов заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesthistory-get) |
| POST | `/api/b2b/platform/request/cancel` | Отмена заявки, созданной в логистической платформе | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcancel-post) |
| POST | `/api/b2b/platform/request/create` | Создание заказа на ближайшее доступное время | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestcreate-post) |
| POST | `/api/b2b/platform/request/places/edit` | Редактирование грузомест заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestplacesedit-post) |
| POST | `/api/b2b/platform/request/edit/status` | Получение статуса запроса на редактирование | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequesteditstatus-post) |
| POST | `/api/b2b/platform/request/items-instances/edit` | Заявка на редактирование товаров заказа | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/3.-Osnovnye-zaprosy/apib2bplatformrequestitems-instancesedit-post) |

## 4. Ярлыки и акты приема-передачи

| HTTP-метод | Эндпоинт | Описание | Документация |
|------------|----------|----------|--------------|
| POST | `/api/b2b/platform/request/generate-labels` | Генерация ярлыков для указанных заказов | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestgenerate-labels-post) |
| POST | `/api/b2b/platform/request/get-handover-act` | Получение актов приема-передачи для отгрузки | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/4.-Yarlyki-i-akty-priema-peredachi/apib2bplatformrequestget-handover-act-post) |

## 5. Управление мерчантами

| HTTP-метод | Эндпоинт | Описание | Документация |
|------------|----------|----------|--------------|
| POST | `/api/b2b/platform/merchant/register` | Начало регистрации мерчанта | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/5.-Upravlenie-merchantami/apib2bplatformmerchantregister-post) |
| GET | `/api/b2b/platform/merchant/register` | Проверить статус регистрации мерчанта и получить его идентификатор | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/5.-Upravlenie-merchantami/apib2bplatformmerchantregister-get) |
| GET | `/api/b2b/platform/merchant/info` | Получить информацию о мерчанте | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/5.-Upravlenie-merchantami/apib2bplatformmerchantinfo-get) |
| POST | `/api/b2b/platform/merchant/search` | Найти мерчантов | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/5.-Upravlenie-merchantami/apib2bplatformmerchantsearch-post) |
| POST | `/api/b2b/platform/merchant/delete` | Удалить мерчанта | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/5.-Upravlenie-merchantami/apib2bplatformmerchantdelete-post) |
| POST | `/api/b2b/platform/merchant/update` | Обновить информацию о мерчанте | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/5.-Upravlenie-merchantami/apib2bplatformmerchantupdate-post) |

## 6. Управление складами и отгрузками

| HTTP-метод | Эндпоинт | Описание | Документация |
|------------|----------|----------|--------------|
| POST | `/api/b2b/platform/warehouses/create` | Создание склада | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformwarehousescreate-post) |
| POST | `/api/b2b/platform/warehouses/list` | Получение списка складов клиента | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformwarehouseslist-post) |
| POST | `/api/b2b/platform/warehouses/retrieve` | Получение информации о складе | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformwarehousesretrieve-post) |
| POST | `/api/b2b/platform/pickups/pickup-options` | Получить опции отгрузки для склада | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformpickupspickup-options-post) |
| POST | `/api/b2b/platform/pickups/create` | Создать отгрузку | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformpickupscreate-post) |
| POST | `/api/b2b/platform/pickups/cancel` | Отмена отгрузки | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformpickupscancel-post) |
| POST | `/api/b2b/platform/pickups/scheduled/list` | Получение списка запланированных отгрузок | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformpickupsscheduledlist-post) |
| POST | `/api/b2b/platform/pickups/retrieve` | Получение информации об отгрузке | [Подробнее](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/6.-Upravlenie-skladami-i-otgruzkami/apib2bplatformpickupsretrieve-post) |

## Сводная таблица

| № | Группа | Кол-во методов |
|---|--------|----------------|
| 1 | Подготовка заявки | 3 |
| 2 | Точки самопривоза и ПВЗ | 2 |
| 3 | Основные запросы | 14 |
| 4 | Ярлыки и акты приема-передачи | 2 |
| 5 | Управление мерчантами | 6 |
| 6 | Управление складами и отгрузками | 8 |
| | **Итого** | **35** |

## Базовый хост

| Окружение | Хост |
|-----------|------|
| Production | `https://b2b-authproxy.taxi.yandex.net` |
| Тестовое | `https://b2b.taxi.tst.yandex.net` |

## Навигация

| Направление | Раздел | Ссылка |
|-------------|--------|--------|
| Предыдущая | Справочник ошибок | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/errors) |
| Следующая | 1.01. Предварительная оценка стоимости доставки | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/1.-Podgotovka-zayavki/apib2bplatformpricing-calculator-post) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/ref/](https://yandex.com/support/delivery-profile/ru/api/other-day/ref/)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > Список методов
