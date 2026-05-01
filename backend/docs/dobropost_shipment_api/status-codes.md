---
tags:
  - project/loyality
  - backend
  - logistics
  - dobropost
  - reference
type: reference
date: 2026-04-30
aliases: [DobroPost Status Codes, ДоброПост статусы]
status: active
parent: "[[DobroPost Shipment API]]"
project: "[[Loyality Project]]"
component: backend
---

# DobroPost — справочник статусов

> Полный enum `status.id` для Шипмента ДоброПост: **40 значений в 4 группах**. Используется в фильтре `?statusId=` (`GET /api/shipment`) и в webhook'е (формат №2 присылает строковое `status`, которое Loyality матчит обратно в `status_id` через таблицы ниже). Источник — раздел «Список статусов» в `reference.md`.
>
> **Назначение этого файла** — единый source-of-truth для маппинга «ДоброПост → unified `TrackingStatus`» (домен `src.modules.logistics`). Поведение FSM Order при каждой группе статусов — в [`integration.md`](./integration.md).

## TL;DR — вотерлиния групп

| Группа                                  | Диапазон id | Значение для Loyality                                                            |
| --------------------------------------- | ----------- | -------------------------------------------------------------------------------- |
| Базовая логистическая цепочка           | 1–9         | Cross-border сегмент в работе. Order в `PROCURED`. Прогресс отображается customer'у. |
| Редактирование данных посылки           | 270–272     | Информационный — обычно после нашего `PUT /api/shipment` (исправление паспорта). |
| Таможенное оформление                   | 500–600     | Самая критичная группа. Здесь живут отказы (541–546, 590xxx) и **триггер 648/649** для создания last-mile shipment. |
| Развёрнутые отказы с кодами             | 590xxx      | Подмножество таможенных отказов с детализированной причиной.                      |

## Терминальные / non-terminal статусы

| Тип                                  | id'ы                                                            | Логика FSM Loyality                              |
| ------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------ |
| **Cross-border completed (триггер)** | `648`, `649`                                                    | Order → `ARRIVED_IN_RU`; **создаётся Shipment #2** (last-mile). |
| **Terminal failure (refund)**        | `541`, `542`, `543`, `544`, `545`, `546`, `590xxx`, `600`       | Order → `CANCELLED + REFUND`. Cross-border shipment → `FAILED`. |
| **Requires manual action**           | `510`, `531`, `540`                                             | Order остаётся в `PROCURED`, customer service нотифицируется. |
| **Passport check failed**            | `544`, `545` + webhook `passportValidationStatus=false`         | Order остаётся в `PROCURED`, шипмент **зависает** перед таможней. CS запрашивает корректные данные → `PUT /api/shipment`. |
| **Прочие (in-flight)**               | всё остальное                                                   | Информативные tracking events — обновляют прогресс. |

---

## 1. Базовая логистическая цепочка (9)

| id  | Название                     | TrackingStatus (Loyality)                          |
| --- | ---------------------------- | -------------------------------------------------- |
| 1   | Ожидается на складе          | `CREATED`                                          |
| 2   | Получен от курьера           | `ACCEPTED`                                         |
| 3   | Обработан на складе          | `IN_TRANSIT`                                       |
| 4   | Добавлен в мешок             | `IN_TRANSIT`                                       |
| 5   | Добавлен в реестр            | `IN_TRANSIT`                                       |
| 6   | Покинул склад в Китае        | `IN_TRANSIT`                                       |
| 7   | Поступил на таможню в Китае  | `CUSTOMS`                                          |
| 8   | Поступил на таможню в России | `CUSTOMS`                                          |
| 9   | Передан партнеру             | `IN_TRANSIT` *(промежуточный, до 648/649)*         |

## 2. Редактирование данных посылки (3)

| id  | Название                                         | TrackingStatus | Когда возникает                                 |
| --- | ------------------------------------------------ | -------------- | ----------------------------------------------- |
| 270 | Запрос на редактирование данных посылки          | (не маппится)  | После нашего `PUT /api/shipment`. Не triggers FSM. |
| 271 | Запрос на редактирование данных посылки отклонён | (не маппится)  | Customer service → новый `PUT` или эскалация.   |
| 272 | Произведено редактирование данных посылки        | (не маппится)  | Подтверждение применения нашего `PUT`.           |

## 3. Таможенное оформление (19)

### Информационные (in-flight)

| id  | Название                                       | TrackingStatus |
| --- | ---------------------------------------------- | -------------- |
| 500 | Начало таможенного оформления                  | `CUSTOMS`      |
| 591 | Начало таможенного оформления                  | `CUSTOMS`      |
| 570 | Продление времени обработки                    | `CUSTOMS`      |

### Требуют действия (manager / customer)

| id  | Название                                                | TrackingStatus | Действие                              |
| --- | ------------------------------------------------------- | -------------- | -------------------------------------- |
| 510 | Требуется уплатить таможенные пошлины                   | `CUSTOMS`      | CS уведомляет customer'а               |
| 531 | Требуется уплатить таможенные пошлины                   | `CUSTOMS`      | CS уведомляет customer'а               |
| 540 | Ожидание обязательной оплаты таможенной пошлины         | `CUSTOMS`      | CS уведомляет customer'а               |

### Успешный выпуск таможни

| id  | Название                                          | TrackingStatus  |
| --- | ------------------------------------------------- | --------------- |
| 520 | Выпуск товаров без уплаты таможенных платежей     | `IN_TRANSIT`    |
| 521 | Выпуск товаров без уплаты таможенных платежей     | `IN_TRANSIT`    |
| 530 | Выпуск товаров (таможенные платежи уплачены)      | `IN_TRANSIT`    |
| 532 | Выпуск товаров (таможенные платежи уплачены)      | `IN_TRANSIT`    |

### **Триггер last-mile shipment** ⚡

| id  | Название                                                | TrackingStatus | Действие                                    |
| --- | ------------------------------------------------------- | -------------- | ------------------------------------------- |
| 648 | Подготовлено к отгрузке в доставку последней мили       | `IN_TRANSIT`   | **Создать Shipment #2 (last-mile)**        |
| 649 | Покинула таможню и передана на доставку по РФ           | `IN_TRANSIT`   | **Создать Shipment #2** если не создан 648 |

> **Конкретное поведение:** при первом получении 648 ИЛИ 649 (через webhook) Loyality emit'ит domain event `CrossBorderArrived`, consumer создаёт Shipment #2 для last-mile carrier'а (см. [`integration.md` §Shipment-2-creation](./integration.md#shipment-2-last-mile-creation)). Order → `ARRIVED_IN_RU` → `IN_LAST_MILE` после booking #2.

### Терминальные отказы (refund)

| id  | Название                                                                 | TrackingStatus | Reason для refund                |
| --- | ------------------------------------------------------------------------ | -------------- | -------------------------------- |
| 541 | Отказ — партия признана коммерческой / не для личного пользования        | `EXCEPTION`    | `customs_commercial`             |
| 542 | Отказ — отсутствуют документы для тамож. контроля / оплаты пошлины       | `EXCEPTION`    | `customs_missing_documents`      |
| 543 | Отказ — некорректное заполнение информации о товаре                       | `EXCEPTION`    | `customs_invalid_product_info`   |
| 544 | Отказ — отсутствие корректных паспортных данных                          | `EXCEPTION`    | `customs_invalid_passport`       |
| 545 | Отказ — паспортных данных нет в списке достоверных паспортов              | `EXCEPTION`    | `customs_passport_not_in_registry` |
| 546 | Отказ по другим причинам                                                  | `EXCEPTION`    | `customs_other`                  |
| 600 | Посылка не пришла                                                         | `LOST`         | `parcel_lost`                    |

> Все эти статусы → **Order `CANCELLED + REFUND`** + Shipment `FAILED` (carrier-side terminal). См. `mark_failed_from_tracking` в `src/modules/logistics/domain/entities.py:369`.

## 4. Развёрнутые отказы с кодами причин (9)

Все маппятся на `TrackingStatus.EXCEPTION` + reason `customs_<код>`. Подмножество отказов из группы 3 с детализацией для аудита.

| id     | Название                                                                                                  |
| ------ | --------------------------------------------------------------------------------------------------------- |
| 590204 | Отказ в выпуске товаров с указанием кода причины отказа                                                   |
| 590401 | Отказ в выпуске товаров с указанием кода причины отказа                                                   |
| 590404 | Отказ в выпуске товаров. Не представлены документы и сведения                                              |
| 590405 | Отказ в выпуске товаров с указанием кода причины отказа                                                   |
| 590409 | Отказ в выпуске товаров с указанием кода причины отказа                                                   |
| 590410 | Отказ в выпуске товаров. Товар входит в перечень категорий товаров                                         |
| 590413 | Отказ в выпуске товаров. Не подана корректировка пп.2 п.1 ст.125 ТК ЕАЭС                                  |
| 590420 | Отказ в выпуске товаров с указанием кода причины отказа                                                   |
| 590592 | Отказ в выпуске товаров с указанием кода причины отказа                                                   |

---

## Маппинг строкового `status` (webhook формат №2) → status_id

ДоброПост в webhook'е присылает **только** строку `status` (например, `"В пути"`, `"Доставлено"`, `"Задерживается"`). Loyality матчит её через нечёткое сравнение по полю «Название» в таблицах выше. Если совпадения нет:

- Сохраняем raw строку в `tracking_events.provider_status_name`.
- `provider_status_code` = `"unknown"`.
- `TrackingStatus` = `EXCEPTION` (видимо, что-то пошло не так), но **FSM Shipment не транзитим** — статус добавляется как информативный.
- Logger.warning с raw payload для последующего обновления словаря.

## Терминальные tracking-status'ы для FSM Shipment

В терминах `src.modules.logistics.domain.value_objects`:

```python
# Из value_objects.py:102 и 111
TERMINAL_FAILURE_TRACKING_STATUSES = frozenset({TrackingStatus.LOST, TrackingStatus.EXCEPTION})
TERMINAL_CANCEL_TRACKING_STATUSES = frozenset({TrackingStatus.CANCELLED})
```

ДоброПост статусы 541–546 / 590xxx / 600 → попадают в `TERMINAL_FAILURE_TRACKING_STATUSES` через маппинг выше → **`Shipment.append_tracking_event` автоматически вызывает `mark_failed_from_tracking(reason)`** (см. [`integration.md`](./integration.md#fsm-shipment-cross-border)).

## Связанное

- [[DobroPost Shipment API]] — index папки.
- [`reference.md`](./reference.md) — голая спецификация ДоброПост (раздел «Список статусов»).
- [`integration.md`](./integration.md) — поведение FSM Order/Shipment при разных группах статусов.
- [`webhooks.md`](./webhooks.md) — webhook payload и matching.
- `src/modules/logistics/domain/value_objects.py:79` — `TrackingStatus` enum.
- `src/modules/logistics/domain/entities.py:369` — `mark_failed_from_tracking`.
