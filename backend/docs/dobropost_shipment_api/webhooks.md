---
tags:
  - project/loyality
  - backend
  - logistics
  - dobropost
  - webhook
  - spec
type: spec
date: 2026-04-30
aliases: [DobroPost Webhooks, ДоброПост вебхуки]
status: active
parent: "[[DobroPost Shipment API]]"
project: "[[Loyality Project]]"
component: backend
---

# DobroPost — webhook contract (Loyality side)

> **Зачем этот файл:** ДоброПост посылает webhook по одному URL, но в **двух разных форматах** (passport-validation vs status-update), и без подписи в стандарте. Это документирует, как Loyality их различает, верифицирует, делает идемпотентными и связывает с Shipment / FSM Order.
>
> Реализовано в `src/modules/logistics/infrastructure/providers/dobropost/webhook_adapter.py` (адаптер `IWebhookAdapter`) + `src/modules/logistics/application/commands/handle_dobropost_passport_validation.py` (specialised command для passport-failure).

## Endpoint

```
POST {API_V1_STR}/logistics/webhooks/dobropost
Content-Type: application/json
```

Регистрируется в общем webhook-роутере `src/modules/logistics/presentation/router_webhooks.py:22` (`/logistics/webhooks/{provider_code}`), `provider_code = "dobropost"`. См. шаблон CDEK как пример регистрации в registry.

## Аутентификация

ДоброПост **не подписывает payload** в стандартной поставке. Loyality защищает endpoint через:

1. **Shared secret в HTTP-заголовке** — `X-Webhook-Secret: <secret>` (или `X-DobroPost-Secret`). Хранится в `ProviderAccountModel.config_json["webhook_secret"]`; comparison через `hmac.compare_digest`.
2. **IP allow-list** в `ProviderAccountModel.config_json["webhook_allowed_ips"]` — список CIDR / single IP. Проверяется по `X-Forwarded-For` / `X-Real-Ip`.
3. **TLS-only** (Railway даёт автоматически).

Если в config'е **ни** `webhook_secret`, **ни** `webhook_allowed_ips` — adapter fail-closed возвращает `False` на любой signature и router отвечает `401 UnauthorizedError`. Поэтому `CreateProviderAccountHandler` (через `validate_provider_account_input`) **отвергает** создание DobroPost-аккаунта без хотя бы одного auth-источника.

> Без подписи провайдером webhook **ОБЯЗАН** дополняться идемпотентностью (см. ниже).

## Различение payload по форме

```python
async def parse_events(
    self, body: bytes
) -> list[tuple[str, list[TrackingEvent]]]:
    payload = json.loads(body)
    if "passportValidationStatus" in payload:
        return self._parse_passport_validation(payload)
    if "DPTrackNumber" in payload and "status" in payload:
        return self._parse_status_update(payload)
    # Unknown payload shape — webhook router логирует accepted_no_tracking.
    return []
```

## Формат №1 — Passport validation

```json
{
  "shipmentId": 12345,
  "statusDate": "2025-02-04T14:30:00Z",
  "passportValidationStatus": false
}
```

### Loyality flow

1. Resolve `shipment_id` по `provider_code="dobropost"` + `provider_shipment_id=str(shipmentId)`.
2. **НЕ создаётся `TrackingEvent`** — passport validation это отдельная сигнализация, не carrier lifecycle.
3. Adapter возвращает `[]` из `parse_events` — generic `IngestTrackingHandler` тут не подходит.
4. Вместо него **отдельный `HandleDobroPostPassportValidation` consumer** на специализированный path: webhook router детектит формат и dispatch'ит в этот consumer (расширение over generic `parse_events`).

```python
# Псевдо-код consumer'а
async def handle_passport_validation(
    shipment_id: UUID,
    is_valid: bool,
    occurred_at: datetime,
) -> None:
    shipment = await repo.get_by_id(shipment_id)
    if shipment is None:
        log.warning("passport-validation for unknown shipment", ...)
        return
    if is_valid:
        # Информационное событие — записать в audit log; FSM не трогаем.
        log.info("passport validated", shipment_id=...)
        return
    # passport invalid → escalation
    shipment.failure_reason = "passport_validation_failed"
    await repo.update(shipment)
    # emit OrderRequiresCustomerAction — CS должен получить корректные данные.
    uow.register_aggregate(shipment)
    await uow.commit()
```

> **Не маркируем Shipment FAILED здесь:** Order остаётся в `PROCURED`, шипмент **зависает** перед таможней. Если CS получит правильный паспорт → `PUT /api/shipment` на стороне ДоброПост → дальнейшие статусы пойдут нормально. Если нет → ДоброПост в итоге пришлёт 544/545 (паспорт rejected на таможне) → Order `CANCELLED + REFUND` через generic terminal-failure path.

## Формат №2 — Status update

```json
{
  "shipmentId": 12345,
  "DPTrackNumber": "DP123456789",
  "statusDate": "2025-02-04T14:30:00Z",
  "status": "В пути"
}
```

### Loyality flow

1. Resolve `shipment_id` по `(provider_code, provider_shipment_id=str(shipmentId))`.
2. Map текстовый `status` → `status_id` через таблицы в [`status-codes.md`](./status-codes.md):
   - Точное совпадение по полю «Название».
   - На miss — `provider_status_code = "unknown"`, `TrackingStatus = EXCEPTION`, **FSM не транзитим**, log.warning.
3. Создать `TrackingEvent`:
   ```python
   TrackingEvent(
       status=mapped_tracking_status,      # см. status-codes.md
       provider_status_code=str(status_id), # "648", "544", "unknown"
       provider_status_name=raw_status,    # "В пути"
       timestamp=parse_iso(payload["statusDate"]),
       location=None,                       # ДоброПост не отдаёт
       description=None,
   )
   ```
4. Generic `IngestTrackingHandler.handle(IngestTrackingCommand(...))`:
   - `Shipment.append_tracking_event` сделает дедуп по `(timestamp, status)` (одинаковый webhook ретрай → `NOOP`).
   - Auto-FSM transition: `LOST/EXCEPTION` → `mark_failed_from_tracking`; `CANCELLED` → `mark_cancelled_from_tracking`.
5. **Дополнительно**: после ingest detect status_id ∈ {648, 649} в текущем shipment'е → emit `CrossBorderArrivedEvent` (consumer создаёт last-mile shipment). Реализуется отдельным observer'ом в адаптере **до** делегации в generic handler.

## Идемпотентность (критично!)

ДоброПост **гарантирует** ретраи на любой не-2xx. Loyality защищается на трёх уровнях:

### Уровень 1 — DB constraint

`UniqueConstraint(shipment_id, timestamp, status)` на `shipment_tracking_events` (`models.py:218`). Дубликат webhook'а с тем же `(timestamp, status_id)` → `INSERT ... ON CONFLICT DO UPDATE` (см. `ShipmentRepository._sync_tracking_events`). Безопасно при concurrent webhook + tracking_poll.

### Уровень 2 — domain-level dedup

`Shipment.append_tracking_event` (`entities.py:429`) возвращает:
- `ADDED` — новое событие.
- `REPLACED` — duplicate, но webhook принёс более богатое описание (location/description).
- `NOOP` — точный дубликат.

`IngestTrackingHandler` коммитит UoW **только** при `added or replaced > 0` — иначе пустые tx-ы и outbox-события не плодятся.

### Уровень 3 — webhook router swallow

Если `ShipmentNotFoundError` или любая другая exception → `acknowledged + log.warning` (см. `router_webhooks.py:104-129`):

> ДоброПост ретраит на любой 4xx/5xx — мы **не возвращаем ошибку**, чтобы не запускать retry storm на наших pod'ах. Periodic `tracking_poll_task` (если ДоброПост даст `ITrackingPollProvider`) backfill'ит пропуск.

### Терминальные статусы и idempotency

`mark_failed_from_tracking` (`entities.py:387`) и `mark_cancelled_from_tracking` (`:406`) **idempotent** на уже-FAILED/CANCELLED shipment — `if self.status == TARGET: return`. Это критично для повторных webhook'ов 541–546.

## Retry-стратегия со стороны ДоброПост

(зафиксировать при онбординге, нет в публичном PDF)

| Код Loyality          | Поведение ДоброПост               |
| --------------------- | --------------------------------- |
| `200`                 | Стоп.                             |
| `400 / 500`           | Ретраит — 5 раз, exp backoff.     |
| Timeout > 20s         | Ретраит как 500.                  |

**Loyality SLA для webhook handler'а:**

- `< 2s p95` (не блокирующий path: парсинг → DB upsert → outbox).
- Все тяжёлые операции (создание last-mile shipment, нотификации) — через outbox + TaskIQ async.

## Outbox events emitted

После успешного ingest webhook'а Shipment может эмитить (через UoW):

| Событие                                | Когда                                     | Subscriber                              |
| -------------------------------------- | ----------------------------------------- | --------------------------------------- |
| `ShipmentTrackingUpdatedEvent`         | Любой ADDED tracking event                | (нет — резерв)                          |
| `ShipmentDeliveryFailedEvent`          | Auto-transition в FAILED (LOST/EXCEPTION) | `OrderCompensationConsumer` (TBD): refund + Order → CANCELLED |
| `ShipmentCancelledEvent`               | Auto-transition в CANCELLED               | `OrderCompensationConsumer` (TBD)       |
| `CrossBorderArrivedEvent` *(новое)*    | status_id ∈ {648, 649}                    | `LastMileShipmentCreator` (TBD): создаёт Shipment #2 |
| `OrderRequiresCustomerAction` *(новое)* | passport_validation=false                 | `CustomerServiceNotifier` (TBD)         |

> События `CrossBorderArrivedEvent` и `OrderRequiresCustomerAction` — **специфичны для Loyality cross-border flow** и в текущем `events.py` отсутствуют. Их добавление — часть milestone «Order module».

## Roadmap

| # | Задача                                                            | Статус        |
| - | ----------------------------------------------------------------- | ------------- |
| 1 | Добавить `dobropost` в `_FACTORY_MAP` (`infrastructure/bootstrap.py:33`) | ✅ Done   |
| 2 | Реализовать `DobroPostProviderFactory + DobroPostWebhookAdapter`  | ✅ Done       |
| 3 | Реализовать `DobroPostBookingProvider` (POST `/api/shipment`)     | ✅ Done       |
| 4 | Реализовать `DobroPostTrackingPollProvider` (GET `/api/shipment`) | ✅ Done       |
| 5 | Добавить `dobropost` в `_PROVIDER_COVERAGE` (`services/routing.py:22`) | ❌ Не нужно — DobroPost админ-managed, не участвует в customer-facing rate fan-out (factory.create_rate_provider → None) |
| 6 | Добавить `CrossBorderArrivedEvent` + хук в `Shipment.append_tracking_event` (idempotent) | ✅ Done |
| 7 | `ShipmentPassportValidationFailedEvent` + `HandleDobroPostPassportValidationHandler` | ✅ Done |
| 8 | Order-side consumer для `CrossBorderArrivedEvent` (создание Shipment #2) | ⏳ Order module (Q3 2026) |
| 9 | Order-side consumer для `ShipmentPassportValidationFailedEvent` (CS escalation) | ⏳ Order module (Q3 2026) |
| 10 | Регресс-тесты на дубликат webhook (idempotency e2e)               | ⏳ TODO       |

## Связанное

- [[DobroPost Shipment API]] — index папки.
- [`reference.md`](./reference.md) — голая спецификация ДоброПост.
- [`status-codes.md`](./status-codes.md) — маппинг текстового `status` на TrackingStatus.
- [`integration.md`](./integration.md) — Loyality FSM Order, last-mile shipment creation, edge-cases.
- `src/modules/logistics/domain/interfaces.py` — `IWebhookAdapter` контракт.
- `src/modules/logistics/presentation/router_webhooks.py` — общий webhook-роутер.
- `src/modules/logistics/infrastructure/providers/cdek/webhook_adapter.py` — реализация-образец.
