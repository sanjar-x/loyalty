# API Доставки в другой день — Введение

## Описание

API Яндекс Доставки в другой день предоставляет возможность сделать заказ в другой день при помощи HTTP-запросов, а именно воспользоваться доставкой с классическим забором с вашего склада и доставкой до конечного получателя. Кроме того, возможен самопривоз товара в определенные точки отгрузки и доставка до ПВЗ.

## Схема процесса

![Схема процесса доставки](https://yastatic.net/s3/doc-binary/src/dev/logistics/ru/delivery-api/files/scheme-0.png)

## Сценарии доставки

| Сценарий | Описание |
|----------|----------|
| Классический забор | Забор с вашего склада с доставкой до конечного получателя |
| Самопривоз | Самопривоз товара в определённые точки отгрузки и доставка до ПВЗ |

## Окружения

### Тестовое окружение

Для работы в тестовом контуре используйте:

| Параметр | Значение |
|----------|----------|
| Host | `https://b2b.taxi.tst.yandex.net/api/b2b/platform/offers/create` |
| Токен (Bearer token) | `y2_AgAAAAD04omrAAAPeAAAAAACRpC94Qk6Z5rUTgOcTgYFECJllXYKFx8` |
| Склад отгрузки (`platform_station_id`) | `fbed3aa1-2cc6-4370-ab4d-59c5cc9bb924` |

### Боевое (Production) окружение

Для работы с API в боевой среде:

| Параметр | Значение |
|----------|----------|
| Host | `https://b2b-authproxy.taxi.yandex.net` |
| Bearer-токен | Получите в личном кабинете, раздел **Профиль** |
| Станция отгрузки (`platform_station_id`) | Выдаётся по запросу коммерческим менеджером |

## Следующие шаги

- Создайте заявку и отслеживайте состояние заказа с помощью API в соответствии со [статусной моделью](https://yandex.com/support/delivery-profile/ru/api/other-day/status-model).
- В случае возникновения каких-либо проблем свяжитесь с вашим менеджером Яндекс Доставки или со [службой поддержки](https://yandex.com/support/delivery-profile/ru/api/other-day/troubleshooting).

## Навигация по документации

| Раздел | Ссылка |
|--------|--------|
| Терминология | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/term) |
| Статусная модель | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/status-model) |
| Служба поддержки (Экспресс) | [Перейти](https://yandex.com/support/delivery-profile/ru/api/express/troubleshooting) |
| Служба поддержки (Другой день) | [Перейти](https://yandex.com/support/delivery-profile/ru/api/other-day/troubleshooting) |

## Источник

- **URL:** [https://yandex.com/support/delivery-profile/ru/api/other-day/](https://yandex.com/support/delivery-profile/ru/api/other-day/)
- **Сервис:** Яндекс Доставка
- **Раздел:** API > API Доставки в другой день > Введение
