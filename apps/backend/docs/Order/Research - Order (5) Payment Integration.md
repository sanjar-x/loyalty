---
tags:
  - project/loyality
  - backend
  - order
  - payment
  - checkout
  - research
type: research
date: 2026-04-29
aliases: [Order Payment, Payment Integration, Checkout Payment Flow]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (5) Payment Integration

> Интеграция платежей в checkout flow: СБП, российские эквайеры (ЮKassa, Tinkoff), Stripe Payment Intents, 3DS 2.x, idempotency keys, two-step authorize+capture, refunds, partial captures, BNPL и split-payments. Payment как отдельный bounded context.

## TL;DR — ключевые выводы

1. **Payment — это отдельный BC** и отдельный FSM, никогда не часть Order aggregate. Связь — по id.
2. **Two-step payment (authorize + capture)** — индустриальный стандарт. Authorize при checkout, capture при отгрузке. Уменьшает refunds и chargeback'и.
3. **Idempotency-Key** — обязательный header для всех платёжных мутаций. Stripe, ЮKassa, Tinkoff — все требуют. UUID v4, TTL 24h.
4. **3DS 2.x с PSD2 SCA** — стандарт в EU, в России пока 3DS 1.x доминирует, но Mir переходит на 3DS 2. Frictionless flow через 100+ data points.
5. **СБП (Россия)** — отдельный rail: QR-based, банк-к-банку, без card data, без 3DS. Главная альтернатива картам, низкие комиссии (0.4-0.7%).
6. **Webhooks** — primary integration point для async payment status. At-least-once delivery → required idempotent consumer + signature verification.
7. **PCI DSS scope reduction** через tokenization — никогда не храните PAN в своей инфраструктуре. SAQ A vs SAQ D — разница в десятки контролов.
8. **BNPL (Klarna / Долями / Сплит)** — отдельный payment method, мерчант получает 100% сразу, провайдер берёт risk и комиссию.
9. **Split payments по методам** (gift card + card + loyalty points) — реализуется через множество PaymentMethod объектов на одном Order. Каждый — отдельный authorization/capture lifecycle.

---

## 1. Payment как отдельный bounded context

### 1.1 Аргументы за изоляцию Payment BC

- **Domain language:** Authorize, Capture, Void, Refund, 3DS challenge — собственный язык, отличный от Order.
- **Lifecycle:** payment может жить дольше Order (chargebacks через 60+ дней).
- **External coupling:** Payment активно общается с PSP — ACL критичен.
- **Compliance:** PCI DSS касается только Payment BC. Order BC не должен быть в scope.
- **Multi-PSP:** Payment BC поддерживает несколько провайдеров, Order — нет.

### 1.2 Структура Payment aggregate

```text
┌─────────── Payment BC ────────────┐
│                                   │
│  ┌──── Payment (aggregate root)─┐ │
│  │  - id: PaymentId             │ │
│  │  - orderId: OrderId (ref)    │ │
│  │  - method: PaymentMethod     │ │
│  │  - state: PaymentState (FSM) │ │
│  │  - amount: Money             │ │
│  │  - capturedAmount: Money     │ │
│  │  - refundedAmount: Money     │ │
│  │  - idempotencyKey: UUID      │ │
│  │  - pspProvider: Provider     │ │
│  │  - pspPaymentId: String      │ │
│  │  - authorizations[]          │ │
│  │  - captures[]                │ │
│  │  - refunds[]                 │ │
│  │  + authorize()               │ │
│  │  + capture(amount?)          │ │
│  │  + void()                    │ │
│  │  + refund(amount, reason)    │ │
│  └──────────────────────────────┘ │
│                                   │
│  ┌── Authorization (entity) ────┐ │
│  │  - id, amount, expiresAt     │ │
│  │  - pspAuthCode               │ │
│  └──────────────────────────────┘ │
│                                   │
│  ┌── Capture (entity) ──────────┐ │
│  │  - id, amount, capturedAt    │ │
│  └──────────────────────────────┘ │
│                                   │
│  ┌── Refund (entity) ───────────┐ │
│  │  - id, amount, reason        │ │
│  │  - state: Pending/Completed  │ │
│  └──────────────────────────────┘ │
└───────────────────────────────────┘
```

### 1.3 Связь с Order через id

```text
Order (Ordering BC)              Payment (Payment BC)
  - id: OrderId                    - orderId: OrderId  ◄─── reference
  - paymentSummary (read model)    - amount, state, ...
  - state (own FSM)                - state (own FSM)
```

OrderSummary (Salesforce-style) или `Order.paymentStatus` — это denormalized read projection поверх Payment события. Это не делает Payment внутри Order aggregate.

---

## 2. FSM платежа (PaymentIntent-style)

### 2.1 Канонический Stripe FSM

```text
                ┌──────────────────────────┐
                │ requires_payment_method  │ initial
                └──────────┬───────────────┘
                           │ confirm with payment method
                           ▼
                ┌──────────────────────────┐
                │ requires_confirmation    │
                └──────────┬───────────────┘
                           │ confirm
                           ▼
                ┌──────────────────────────┐
                │ requires_action          │ ← 3DS challenge
                └──────────┬───────────────┘
                           │ customer completes 3DS
                           ▼
                ┌──────────────────────────┐
                │ processing               │
                └──────────┬───────────────┘
                           │
            ┌──────────────┼──────────────────┐
            ▼              ▼                  ▼
     ┌─────────┐  ┌────────────────┐  ┌──────────────┐
     │canceled │  │requires_capture│  │  succeeded   │
     │   (T)   │  │ (manual mode)  │  │     (T)      │
     └─────────┘  └────────┬───────┘  └──────────────┘
                           │ capture
                           ▼
                    ┌──────────────┐
                    │  succeeded   │
                    │     (T)      │
                    └──────────────┘
```

### 2.2 Tinkoff Acquiring FSM

| State | Семантика |
|---|---|
| NEW | Payment created (Init вызван) |
| FORM_SHOWED | Customer на payment form |
| AUTHORIZING | Checking 3DS, validating |
| 3DS_CHECKING | 3DS challenge in progress |
| AUTHORIZED | Funds frozen (after one-stage Init for 2-step flow) |
| CONFIRMING | Capture в процессе |
| CONFIRMED | Money debited (terminal-успех) |
| REVERSING | Cancel в процессе |
| REVERSED | Authorization cancelled (terminal) |
| REFUNDING | Refund в процессе |
| REFUNDED | Полный refund (terminal) |
| PARTIAL_REFUNDED | Частичный refund (можно ещё refund) |
| REJECTED | Отклонён банком (terminal) |
| CANCELED | Отменён до auth (terminal) |

### 2.3 Universal Payment FSM (наша абстракция)

```text
Created → Authorizing → Authorized → Capturing → Captured → (Refunded / PartiallyRefunded)
                ↓             ↓           ↓
            Failed        Voided      CaptureFailed
           (terminal)   (terminal)
```

Mapping в конкретные PSPs делает ACL слой Payment BC.

---

## 3. Two-step payment: Authorize + Capture

### 3.1 One-step vs Two-step

**One-step (auth+capture в одном):**

```text
POST /payment → AUTHORIZED + CAPTURED immediately
```

Используется когда товар отгружается мгновенно (digital goods, SaaS).

**Two-step (auth → capture отдельно):**

```text
POST /payment (auth) → AUTHORIZED (funds held)
... ship goods ...
POST /capture        → CAPTURED (funds debited)
```

### 3.2 Преимущества two-step

| Преимущество | Объяснение |
|---|---|
| Меньше refunds | Если Order cancelled до отгрузки — просто Void, не Refund. Refund имеет fee у некоторых PSPs. |
| Меньше chargebacks | Customer видит charge только после shipping → меньше "where's my order" disputes. |
| Авторизация expires | Auth держится 7-30 дней (зависит от issuer). Если не captured — auto-released. |
| Inventory alignment | Capture в момент когда stock реально уезжает customer'у. |
| Marketplace flows | Capture только когда seller отправил товар. Защищает buyer. |

### 3.3 Trade-offs two-step

- Auth expires (Visa 7 дней, Mastercard 30 дней). Если ship позже — нужен incremental authorization или новая authorization.
- Some banks reduce auth-hold inventory (issuer-side complications).
- Customer видит pending charge в банке, может позвонить с вопросом.
- 3DS done на auth. Capture не требует ещё одного 3DS.

### 3.4 Stripe реализация

```typescript
// 1. Create with manual capture
const intent = await stripe.paymentIntents.create({
  amount: 5000,
  currency: 'usd',
  capture_method: 'manual',  // <-- key flag
  payment_method: 'pm_xxx',
  confirm: true,
}, {
  idempotencyKey: orderUuid,
});
// → status: 'requires_capture' (после auth)

// 2. Later, after shipment
const captured = await stripe.paymentIntents.capture(intent.id, {
  amount_to_capture: 5000,  // can be less than authorized
}, {
  idempotencyKey: `capture-${orderUuid}`,
});
```

> "Uncaptured PaymentIntents are cancelled a set number of days (7 by default) after their creation."

### 3.5 Tinkoff реализация

```text
Init с TwoStage = true → returns paymentId, paymentUrl
Customer pays via paymentUrl
Webhook: status=AUTHORIZED
Confirm(paymentId, amount?) → status=CONFIRMED
Cancel(paymentId) → status=REVERSED (если до Confirm)
```

---

## 4. 3D Secure — аутентификация cardholder'а

### 4.1 Что это

3DS (Three-Domain Secure) — protocol для аутентификации cardholder'а в момент online purchase. Three domains: Issuer (банк-эмитент), Acquirer (банк-эквайер), Interoperability (Visa/Mastercard scheme).

Цель: shift liability fraud chargeback'ов с merchant на issuer (если 3DS пройден).

### 4.2 3DS 1.0 (legacy) vs 3DS 2.x

| Аспект | 3DS 1.0 | 3DS 2.x |
|---|---|---|
| UX | Iframe redirect, OTP/SMS challenge всегда | Risk-based, frictionless для low-risk |
| Data points отправляемых issuer'у | <10 | 100+ (device, behavior, billing match, etc.) |
| Mobile native | Плохо (web iframe) | Native SDK |
| Frictionless rate | ~0% | 60-80% (issuer-dependent) |
| PSD2 SCA compliant | Нет | Да |
| Status (2026) | Sunset в EU/UK | Доминирует |

### 4.3 Frictionless vs Challenge flow

**Frictionless flow:**

```text
Merchant → 3DS Server → ACS (Issuer)
                          │
            ACS analyzes 100+ data points
                          │
               "Confidence high enough"
                          │
            Returns successful auth without UX
                          │
Merchant continues with PaymentIntent
```

Customer не видит 3DS challenge. Время — миллисекунды.

**Challenge flow:**

```text
Merchant → 3DS Server → ACS
                          │
Customer prompted (OTP/biometric/banking app)
                          │
            Customer authenticates
                          │
Merchant receives auth result, continues
```

Customer видит OTP/biometric prompt. Время — десятки секунд + конверсия падает.

### 4.4 PSD2 SCA exemptions

Strong Customer Authentication обязательна в EU, но есть exemptions:

- **TRA (Transaction Risk Analysis)** — PSP fraud rate ниже EBA threshold.
- **Low-value** — < €30, не больше 5 транзакций подряд без SCA.
- **Trusted beneficiaries** — customer внёс merchant в whitelist.
- **MIT (Merchant-Initiated Transaction)** — recurring/subscription.
- **One-leg-out** — только одна сторона в EEA.

### 4.5 Российский контекст

- 3DS 1.0 доминирует в России (Сбер, Tinkoff, ВТБ — все поддерживают).
- 3DS 2.x для МИР — внедряется НСПК, но не повсеместно.
- СБП обходит 3DS полностью — это другой rail (банк-к-банку).
- PSD2 не применима — российская юрисдикция.

### 4.6 PaymentIntent + 3DS интеграция

Stripe абстрагирует сложность 3DS:

```typescript
const intent = await stripe.paymentIntents.create({...});

if (intent.status === 'requires_action') {
  // Frontend: stripe.handleNextAction(intent.client_secret)
  // → redirect или iframe для 3DS challenge
  // → после challenge: автоматически возвращается status='succeeded' or 'requires_capture'
}
```

`status === 'requires_action'` — это явный signal "нужен 3DS challenge". Frontend handles через Stripe.js.

---

## 5. СБП — Система Быстрых Платежей

### 5.1 Что это

СБП (Faster Payments System) — национальная платёжная система ЦБ РФ, запущенная в 2019 году. Ключевое отличие от карт: money flow банк-к-банку напрямую, без card schemes (Visa/MC), без 3DS, без card data.

### 5.2 Сценарии

| Сценарий | Описание |
|---|---|
| C2C (Consumer-to-Consumer) | Перевод по номеру телефона |
| C2B (Consumer-to-Business) | Платёж по QR-коду в магазине / онлайн |
| B2B | Между ЮЛ и ИП |
| B2C (выплаты) | Возврат денег от мерчанта |

E-commerce использует C2B (динамический QR).

### 5.3 C2B integration flow

1. Customer выбирает "Оплата СБП" на checkout
2. Merchant → Bank API: `createPayment(orderId, amount, returnUrl)`
   - desktop: returns dynamic QR code (data URL)
   - mobile: returns deep link for SBP app
3. Customer scans QR / clicks link
4. App открывает банк customer'а с pre-filled payment form
5. Customer подтверждает платёж
6. Bank-to-bank transfer происходит мгновенно
7. Webhook → merchant: `status = CONFIRMED`

### 5.4 Типы QR

- **Dynamic QR** — содержит amount и orderId, single-use.
- **Static QR** — re-usable, без amount (customer вводит).
- **B2B QR** — лимит 1М рублей за один QR.
- **Subscription QR** — recurring, через явное согласие.

### 5.5 API — типичные методы

Endpoints разных банков-эквайеров (ВТБ, Альфа, Точка, etc.) похожи:

```http
POST /sbp/c2b/qr/dynamic/get
  body: { merchantId, amount, currency='RUB', orderId, ttl }
  response: { qrId, qrCodeBase64, deeplink, status='READY' }

GET /sbp/c2b/qr/{qrId}/status
  response: { status: 'READY' | 'PROCESSING' | 'CONFIRMED' | 'EXPIRED' }

POST /sbp/c2b/refund
  body: { qrId, amount, reason }
```

### 5.6 Преимущества и trade-offs СБП

| Плюс | Минус |
|---|---|
| Низкая комиссия (0.4-0.7% vs 1.5-3% card) | Только Россия |
| Нет 3DS friction | Customer должен переключиться в мобильный банк |
| Мгновенное зачисление | Нет mass-storage method (для recurring сложно) |
| Без PCI DSS scope | Не для всех устройств user-friendly |
| Refund мгновенный | Limited fraud protection compared to cards |

### 5.7 Refunds в СБП

`POST /sbp/c2b/refund` — partial и full refund по `qrId`. B2C-payout возможен только в тот же банк customer'а. Refund period — несколько секунд.

---

## 6. Российские эквайеры — обзор

### 6.1 ЮKassa (YooMoney)

Принадлежит Сбербанку, исторически — Яндекс.Касса.

API:

- `POST /v3/payments` — создать платёж.
- `POST /v3/payments/{id}/capture` — capture (для two-step).
- `POST /v3/payments/{id}/cancel` — отменить authorization.
- `POST /v3/refunds` — создать refund.
- Webhooks для `payment.succeeded`, `payment.canceled`, `refund.succeeded`.

> "Для обеспечения идемпотентности запросов используется заголовок Idempotence-Key. Любое значение, уникальное для этой транзакции, максимальная длина — 64 символа. Рекомендуется использовать UUID версии 4. ЮKassa обеспечивает идемпотентность в течение 24 часов."

Партиальные refunds: да, минимальная сумма 1 рубль.

Поддерживаемые методы: карты (Visa/MC/МИР), СБП, ЮMoney wallet, Apple/Google/Mir Pay, Сбербанк Онлайн.

Чеки 54-ФЗ: автоматические через ЮKassa (фискализация). Это критично для российского рынка.

### 6.2 Tinkoff Acquiring

API endpoints:

- `POST /v2/Init` — создать платёж, получить PaymentId и PaymentURL.
- `POST /v2/Confirm` — capture (для two-step).
- `POST /v2/Cancel` — отменить (refund/void в зависимости от state).
- `POST /v2/GetState` — получить state.
- `POST /v2/Charge` — recurring charge по сохранённой карте.
- `POST /v2/FinishAuthorize` — завершить 3DS.

Состояния: `NEW → FORM_SHOWED → AUTHORIZING → 3DS_CHECKING → AUTHORIZED → CONFIRMING → CONFIRMED` + ветви `REVERSED`, `REFUNDED`, `PARTIAL_REFUNDED`, `REJECTED`.

Аутентификация: TerminalKey + Password, signing запросов.

TwoStage payment: `Init` с `TwoStage=true` → `status=AUTHORIZED` → `Confirm` → `CONFIRMED`. До Confirm можно Cancel.

### 6.3 Сбер (Sberbank Acquiring)

Старый эквайер с REST API. Часто используется в legacy интеграциях.

API:

- `POST /payment/rest/register.do` (one-step) — register order, return formUrl.
- `POST /payment/rest/registerPreAuth.do` (two-step) — register с hold.
- `POST /payment/rest/deposit.do` — capture.
- `POST /payment/rest/reverse.do` — отмена pre-auth (only до capture, only once).
- `POST /payment/rest/refund.do` — refund после capture.
- `POST /payment/rest/getOrderStatusExtended.do` — get current state.

Особенности: API устаревшее по дизайну (form-encoded), но стабильное и production-grade.

### 6.4 Альфа-Банк, ВТБ, и др.

Многие используют CMS RBS (Rapida Beat Software, Compass Plus) — той же платформы что у Сбера. API endpoints похожи как близнецы.

### 6.5 Сравнительная таблица

| Эквайер | API style | 2-step | СБП | Idempotency | 3DS 2.x |
|---|---|---|---|---|---|
| ЮKassa | Modern REST/JSON | ✔ | ✔ | Idempotence-Key header | ✔ |
| Tinkoff | REST/JSON | ✔ | ✔ | Через unique OrderId | ✔ |
| Сбер | Legacy REST/form | ✔ | ✔ | Через orderNumber | Частично |
| Альфа | Legacy RBS | ✔ | ✔ | Через orderNumber | Частично |
| СБП напрямую (НСПК) | REST | – | Native | Через qrId | – (не нужно) |

---

## 7. Stripe Payment Intents — современный standard

### 7.1 Зачем PaymentIntent

До PaymentIntents у Stripe был Charges API — single API call для платежа. С появлением SCA/PSD2 одного API call стало недостаточно: нужны были множественные round-trips для 3DS.

PaymentIntent — abstraction tracking lifecycle от создания до final state, автоматически обрабатывая 3DS, retries, и regional payment methods.

### 7.2 Lifecycle PaymentIntent

```text
requires_payment_method
      │ (attach payment method)
      ▼
requires_confirmation
      │ (confirm)
      ▼
requires_action ──── 3DS challenge required
      │ (handleNextAction)
      ▼
processing
      │
      ├─► requires_capture (manual capture mode)
      │       │ (capture)
      │       ▼
      ├─► succeeded (terminal)
      │
      └─► canceled (terminal)
```

### 7.3 Один PaymentIntent на shopping cart

> "Each PaymentIntent typically correlates with a single shopping cart or customer session in your application."

Это естественная idempotency — повторный confirm с тем же intent не создаст дубликат.

### 7.4 Retries и idempotency

```typescript
await stripe.paymentIntents.create({
  amount: 5000,
  currency: 'usd',
}, {
  idempotencyKey: 'order-uuid-12345',
});
```

> "Stripe's idempotency works by saving the resulting status code and body of the first request made for any given idempotency key."

### 7.5 Webhook events

Critical events:

- `payment_intent.created`
- `payment_intent.requires_action`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `payment_intent.canceled`
- `charge.refunded`
- `charge.dispute.created`

Webhook должен быть source of truth, не API response. API call может upset; webhook надёжно доставит финальный статус.

---

## 8. Idempotency Keys — детали

### 8.1 Зачем

Network unreliable. Client retry. Двойной charge — недопустим.

### 8.2 Как генерировать

| Подход | Pros / Cons |
|---|---|
| UUID v4 на client side | ✔ Random, безопасно. ❌ Client может потерять и retry с новым ключом → double charge |
| Cart ID или Order ID | ✔ Stable across retries. ⚠ Иногда не существует на момент idempotent operation |
| Composite: `{orderId}:{operation}:{retryAttempt}` | ✔ Debuggable, stable per intent |
| Random UUID v4 + persist в local DB до confirmation | ✔ Best-of-both |

Best practice (Stripe-recommended): UUID v4, сохранить в БД до отправки запроса, использовать тот же ключ для всех retry'ев одного логического intent'а.

### 8.3 Серверная сторона

```sql
CREATE TABLE idempotency_keys (
    key            VARCHAR(64) PRIMARY KEY,
    request_hash   VARCHAR(64) NOT NULL,
    response_status INT,
    response_body  JSONB,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMP NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
);

-- Index для cleanup старых
CREATE INDEX ON idempotency_keys(expires_at);
```

Algorithm:

1. Begin transaction
2. `SELECT * FROM idempotency_keys WHERE key = $idempotency_key FOR UPDATE`
   - if exists & request_hash matches: return cached `(response_status, response_body)`
   - if exists & request_hash differs: return 409 Conflict (same key, different params — bug)
   - if not exists: INSERT key with NULL response (lock acquired)
3. Execute operation
4. `UPDATE idempotency_keys SET response_status, response_body`
5. Commit transaction
6. Return response

### 8.4 TTL

24 часа — индустриальный стандарт (Stripe, ЮKassa). После TTL ключ может быть переиспользован — это считается новой операцией.

### 8.5 Anti-patterns

- ❌ Использовать email или customer_id как ключ — не unique per intent.
- ❌ Не сохранять request hash — невозможно detect "same key, different params" bug.
- ❌ Хранить ключ только в memory cache (Redis без persistence) — при restart теряется.
- ❌ TTL < 1 hour — недостаточно для long retry windows.
- ❌ Использовать timestamp как часть ключа — invalidates retry semantics.

---

## 9. Refunds — full и partial

### 9.1 Full refund

Customer вернул товар → возврат всей суммы:

```http
POST /v3/refunds (ЮKassa) или
POST /v2/Cancel (Tinkoff после CONFIRMED) или
POST /payment_intents/{id}/refund (Stripe)
```

После full refund: `Payment.state = Refunded` (terminal).

### 9.2 Partial refund

Сценарии:

- Customer вернул 1 из 3 items.
- Compensation за damaged goods (часть compensated).
- Discount post-checkout.

```typescript
// Stripe
await stripe.refunds.create({
  payment_intent: 'pi_xxx',
  amount: 1500,  // partial
  reason: 'requested_by_customer',
}, {
  idempotencyKey: 'refund-order123-line2',
});
```

После partial refund: `state = PartiallyRefunded`. Можно делать ещё refunds, пока `refundedAmount < capturedAmount`.

### 9.3 Refund невозможен — что делать

Иногда payment method не поддерживает refund (some cash payments, expired cards). Альтернативы:

- **Store credit** — внутренний credit balance customer'а.
- **Bank transfer** — через customer service.
- **Replacement** — отправить replacement product вместо refund.

### 9.4 Refund FSM на стороне Payment BC

```text
RefundRequested → RefundProcessing → RefundCompleted
                         │
                         └─► RefundFailed (rare, manual investigation)
```

Refund — отдельный entity внутри Payment aggregate, не просто atomic operation.

### 9.5 Idempotency для refunds

Каждый refund получает свой `idempotencyKey`. Если customer cancels несколько items одной операцией:

- Один refund на total amount, не N refunds на каждый item.
- Если N items в разное время — N refunds, каждый со своим key.

---

## 10. Webhooks — async source of truth

### 10.1 Зачем webhooks

API response ≠ final state. Customer может закрыть браузер, 3DS может зависнуть, charge может быть отклонён банком после initial OK. Webhook — единственный надёжный канал финального статуса.

### 10.2 Чему верить — API или webhook

- ✔ **API response:** для UI immediate feedback ("payment processing...").
- ✔ **Webhook:** для server-side state transitions (Order → CONFIRMED).
- ❌ Не делайте Order CONFIRMED по API response — он может оказаться stale.

### 10.3 Signature verification

Каждый PSP подписывает webhook payload своим секретом. Перед обработкой — проверить:

```typescript
function verifyWebhook(rawBody, signatureHeader, secret) {
  const expectedSignature = hmacSha256(rawBody, secret);
  if (!timingSafeEqual(expectedSignature, signatureHeader)) {
    return res.status(400).end();
  }
  // process event
}
```

Critical: verify используя raw body, не parsed JSON. JSON parsing меняет formatting — signature не сойдётся.

### 10.4 Idempotency webhook

Webhooks at-least-once. Endpoint должен быть idempotent.

```typescript
async function handleWebhook(event) {
  const exists = await db.findOne('webhook_events', { event_id: event.id });
  if (exists) {
    return 200;  // already processed
  }

  await db.transaction(async (tx) => {
    await tx.insert('webhook_events', { event_id: event.id });
    await processEvent(event);
  });
}
```

### 10.5 Async processing

> "Return a 2xx response within 20 seconds, or Stripe considers the delivery failed and will retry. For complex processing, return 200 immediately after signature verification, then process the event asynchronously using a queue or background job."

Pattern:

1. Receive webhook
2. Verify signature
3. Insert into idempotency log + queue
4. Return 200
5. Background worker processes from queue

### 10.6 Retry behavior

- Stripe: retries up to 3 days с exponential backoff.
- ЮKassa: retries up to 24h.
- Tinkoff: retries 88 times за 24h.
- СБП эквайеры: различается, обычно несколько часов.

### 10.7 Webhook security checklist

- [ ] Signature verification на raw body
- [ ] Timing-safe comparison (constant-time hash)
- [ ] HTTPS only endpoint
- [ ] Webhook secret rotation policy
- [ ] IP whitelist (если PSP публикует ranges)
- [ ] Idempotency by event_id
- [ ] Event_id stored с TTL (drop после X days, иначе table растёт)
- [ ] 2xx within 20s, async processing
- [ ] Logging всех received webhooks для debug
- [ ] Alert on webhook signature failures (potential attack)
- [ ] Support replay из PSP dashboard для backfill

---

## 11. PCI DSS — что должен знать каждый интегратор

### 11.1 Что такое PCI DSS

Payment Card Industry Data Security Standard — обязателен для любой системы, которая stores/processes/transmits cardholder data.

12 верхнеуровневых требований, ~300 detailed controls.

### 11.2 SAQ levels

| SAQ | Когда применяется | Controls |
|---|---|---|
| SAQ A | Outsource всё PSP'у. Card data никогда не touches your systems | 22 controls |
| SAQ A-EP | Embedded iframe/redirect, но page hosts payment fields | ~140 |
| SAQ B | POS terminals only | ~40 |
| SAQ C | Payment app standalone | ~160 |
| SAQ D | Store/process/transmit card data | ~330 |

Goal: SAQ A. Это значит — никогда не trafficking card numbers через свою инфраструктуру.

### 11.3 Tokenization

> "Tokenization replaces sensitive card data with a randomly generated token: a surrogate value that has no exploitable meaning if stolen. Once data is tokenized, it is no longer considered cardholder data."

```text
[Customer browser] enters card data → PSP-hosted iframe / SDK
        │
        ▼
[PSP] generates token (e.g. tok_abc123)
        │
        ▼
[Merchant backend] uses token in API calls
        │
        ▼
[PSP] charges via token
```

Card data never touches merchant servers. Merchant — out of scope.

### 11.4 Required controls (даже для SAQ A)

- HTTPS на всех страницах с payment form (не только сама payment страница).
- Регулярный vulnerability scanning (ASV).
- Strong access control для admin staff.
- Logging и monitoring доступа к payment-related endpoints.
- Annual self-assessment.

### 11.5 Anti-patterns

- ❌ Card data логируется (даже частично). Mask должен быть на client side.
- ❌ Card data в URL params, error messages, screenshots.
- ❌ Storing CVV — категорически запрещено PCI DSS, даже PSPs не хранят.
- ❌ Email card numbers (даже в "test" environments).
- ❌ Forwarding card data между сервисами вместо token.

---

## 12. Split payments

### 12.1 Два разных значения "split payment"

1. **Split by payment method** — один Order оплачен gift card + credit card одновременно.
2. **BNPL (Buy Now Pay Later)** — customer платит частями provider'у (4 installments по 2 недели).

### 12.2 Split by payment method

#### 12.2.1 Сценарии

- Gift card $50 + credit card $30 = $80 order.
- Loyalty points $10 + Apple Pay $70.
- Корпоративная карта $500 + личная card $100.

#### 12.2.2 Реализация

```text
Order (total = $100)
  ├── Payment 1: gift_card, amount=$50, captured
  ├── Payment 2: credit_card, amount=$30, authorized
  └── Payment 3: loyalty_points, amount=$20, redeemed
```

Каждый Payment — отдельный aggregate с своим lifecycle. Order имеет invariant `sum(payments.amount) == order.total`.

#### 12.2.3 Сложности

- **Refund priority** — на какой method вернуть первым? Обычно: card → gift card → loyalty (в обратном order).
- **Partial refund** — нужно decompose по methods.
- **Failure isolation** — если credit card fails, gift card уже captured. Compensation: void gift card.

#### 12.2.4 Реальные примеры

- Amazon: gift card balance + 1 card, без multi-card splits.
- Target: до 2 cards split.
- B&H Photo: до 2 cards.
- Shopify: через apps; native — gift card + 1 card.

### 12.3 BNPL (Buy Now Pay Later)

#### 12.3.1 Как это работает с merchant'ом

```text
Customer выбирает BNPL на checkout
    │
    ▼
BNPL provider (Klarna/Долями/Сплит) approves customer
    │
    ▼
Merchant получает 100% suma immediately (минус комиссия 3-7%)
    │
    ▼
BNPL provider отвечает за получение денег от customer
    │
    ▼
Customer платит провайдеру в 4 части по 2 недели
```

С точки зрения merchant'а это обычный payment method. Risk берёт на себя provider.

#### 12.3.2 Klarna

Глобальный BNPL provider. Pay in 4 без процентов, financing с процентами для крупных сумм.
Integration: Klarna Payments API (REST).

#### 12.3.3 Долями (Tinkoff)

Россия. 4 части по 2 недели, первый charge сразу 25%, без процентов.
Integration: через Tinkoff Acquiring API как payment method.

#### 12.3.4 Яндекс Сплит

Россия. Аналогично Долями: 4 части по 2 недели по 25%.
Integration: через Robokassa или Yandex.Pay напрямую.

#### 12.3.5 Подключение BNPL — общий шаблон

1. Merchant signs contract с BNPL provider, получает API keys.
2. На checkout добавить кнопку "Pay with X" или "Pay in 4 with X".
3. При выборе → API call: `createBNPLOrder(items, customer)`
4. Redirect customer на provider's flow.
5. Provider: KYC, credit check, approval.
6. Approved → provider sends webhook: `orderApproved`.
7. Merchant: confirms Order, customer redirected back.
8. Funds transferred (T+1 или T+2 в зависимости от provider'а).

#### 12.3.6 Refunds в BNPL

Refund идёт обратно к BNPL provider'у, не к customer'у напрямую.

- Если customer уже заплатил часть — provider refund'ит уплаченное.
- Оставшиеся installments cancelled.

Это сложнее обычного refund — нужна координация с provider'ом.

### 12.4 Split orders vs Split payments

Не путать:

- **Split shipment** — один Order разделён на N посылок (Тема 1).
- **Split payment by method** — один Order оплачен N методами.
- **BNPL** — один Order, customer платит provider'у в N installments.

Все три могут сосуществовать в одном Order.

---

## 13. Recurring payments / subscriptions

### 13.1 Особенности

- **Card-on-file:** customer authorize первый раз, последующие — без UI.
- **3DS:** первый раз обязателен, recurring — exempt (MIT — Merchant Initiated Transaction).
- **PCI:** token хранится у PSP, у merchant — только PSP token + customer ID.
- **Failed renewal handling:** dunning logic.

### 13.2 Stripe Subscriptions

```typescript
const subscription = await stripe.subscriptions.create({
  customer: 'cus_xxx',
  items: [{ price: 'price_xxx' }],
  payment_behavior: 'default_incomplete',
});
```

### 13.3 Российские эквайеры

- **Tinkoff Charge** — recurring через сохранённую карту.
- **ЮKassa autopayments** — invoice-based или card-on-file.
- **СБП subscriptions** — B2C subscription QR с пользовательским согласием.

---

## 14. Disputes / chargebacks

### 14.1 Что это

Customer оспаривает charge через своего банка → банк инициирует chargeback. Merchant теряет деньги + chargeback fee.

### 14.2 Жизненный цикл

```text
Charge succeeded
     │
     │ (60-120 days later)
     ▼
Customer disputes
     │
     ▼
Issuer creates chargeback
     │
     ▼
Merchant receives notification (webhook)
     │
     ├─► Accept chargeback (lose money)
     └─► Submit evidence (документация)
              │
              ├─► Win → reverse chargeback
              └─► Lose → permanent
```

### 14.3 Stripe API

- `charge.dispute.created` — webhook event.
- `dispute.update` для submission evidence (delivery proof, customer correspondence).

### 14.4 Что собирать как evidence

- Delivery confirmation, signature, tracking.
- Customer email/chat history.
- Refund offered.
- Terms of service acceptance.
- Device fingerprint match.

### 14.5 Prevention

- 3DS shifts liability на issuer (если authentication пройден).
- Clear billing descriptor (customer's bank statement должен показать узнаваемое имя).
- Email confirmations.
- Easy customer service для refund requests (предотвращает dispute).

---

## 15. Multi-PSP architecture

### 15.1 Зачем несколько PSPs

- Geographic coverage (Stripe для глобал, ЮKassa для РФ).
- Fallback при outages.
- Cost optimization (разные fee per method).
- Regulatory (PCI DSS, locally-required acquirers).

### 15.2 Архитектура

```text
Payment Service (orchestrator)
    │
    ├─► PSP Adapter Interface
    │
    ├──► Stripe Adapter ──► Stripe API
    ├──► YooKassa Adapter ─► YooKassa API
    ├──► Tinkoff Adapter ──► Tinkoff API
    ├──► SBP Adapter ──────► НСПК API
    └──► Klarna Adapter ───► Klarna API
```

Каждый adapter — Anti-Corruption Layer (Тема 3). Внутри Payment BC модель остаётся одной, PSP-specific детали изолированы в адаптерах.

### 15.3 Routing rules

```python
if order.currency == 'USD' and order.country in ['US', 'CA']:
    use Stripe
elif order.currency == 'RUB':
    if order.amount > 1_000_000:
        use Tinkoff
    else:
        use YooKassa
    elif customer chose 'СБП':
        use SBP
elif order.currency == 'EUR':
    if customer chose 'BNPL':
        use Klarna
    else:
        use Stripe
```

### 15.4 PSP failover

- **Active-active routing** — split traffic между PSPs (e.g. 70/30) для built-in resilience.
- **Active-passive failover** — if primary returns 5xx N times in M seconds, switch to secondary.
- **Per-transaction retry** — failed на PSP A → retry на PSP B (с тем же idempotency key — но per-PSP, ключи разные).

---

## 16. Связь с другими темами

- **Тема 1 (E-commerce gigants)** — каждая платформа имеет свой набор integrations (Stripe, Amazon Pay, etc.).
- **Тема 2 (OMS)** — payments handled outside OMS, но интегрируется через events. OMS не charges, оrchestrates.
- **Тема 3 (DDD)** — Payment — отдельный BC; ACL обязателен для каждого PSP.
- **Тема 4 (FSM)** — каждый Payment имеет свой FSM, orthogonal к Order FSM.
- **Тема 5 (Saga)** — payment authorize/capture — ключевые steps checkout saga; pivot transaction обычно на capture.
- **Тема 9 (Returns)** — refunds — это reverse cash flow Payment BC.

---

## 17. Чек-лист — payment integration

- [ ] Payment BC отделён от Order BC, общение через id и events
- [ ] Two-step payment (auth + capture) для физических товаров
- [ ] Capture происходит на ship event, не на checkout
- [ ] Idempotency-Key на всех POST/DELETE запросах в PSP
- [ ] UUID v4 как idempotency key, persisted в local DB до request
- [ ] Server-side idempotency table (key, request_hash, response, TTL=24h)
- [ ] Webhook signature verification на raw body
- [ ] Webhook idempotency by event_id
- [ ] 2xx within 20s, async processing background
- [ ] PSP adapters (ACL) для каждого provider'а
- [ ] Routing rules для multi-PSP
- [ ] Failover policy (active-passive или active-active)
- [ ] 3DS 2.x поддержка с frictionless flow
- [ ] СБП integration с QR generation + status polling/webhooks
- [ ] Refund FSM с partial refund support
- [ ] BNPL integration через separate adapter
- [ ] Split payment by method support
- [ ] Multi-tender invariant: `sum(payments) == order.total`
- [ ] PCI DSS SAQ A scope (no card data на merchant servers)
- [ ] Tokenization вместо raw PAN
- [ ] Audit log для всех payment operations с сохранением request/response
- [ ] Sensitive data masked в logs (no PAN, no CVV, masked email)
- [ ] Compliance: PCI DSS audit (annual для high-volume)
- [ ] Compliance: GDPR/152-ФЗ для customer payment data

---

## 18. Источники

### Stripe

- The Payment Intents API — Stripe Documentation
- How PaymentIntents and SetupIntents work — Stripe
- Capture a PaymentIntent — Stripe API Reference
- Authenticate with 3D Secure — Stripe
- Idempotent requests — Stripe API Reference
- Designing robust APIs with idempotency — Stripe Blog
- PaymentIntent object — Stripe API Reference
- Stripe Payment Intents Gateway Guide — Spreedly

### ЮKassa / YooMoney

- Format of interaction with YooMoney API
- Payment process — YooMoney API
- Refunds — YooMoney API
- Quick start — YooMoney API
- Чеки от ЮKassa при возвратах

### Tinkoff Acquiring

- Tinkoff Acquiring SDK — TypeScript
- Tinkoff Acquiring Go client
- Tinkoff Acquiring Rust client (with retry, idempotency, webhook validation)
- Tinkoff Kassa integration overview — TrueTech

### Sberbank Acquiring

- Sberbank API documentation for payment requests
- Sberbank payment gateway API — ecomtest
- Sberbank Acquiring PHP client

### 3DS / SCA / PSD2

- Guide to PSD2, SCA & 3D Secure — Ravelin
- Merchant guide to PSD2, SCA, 3DS — PXP
- 3-D Secure 2 FAQs — BlueSnap
- A Primer on SCA, PSD2, 3DS — ACI Worldwide
- 3D Secure & PSD2 SCA Guide for EU/UK PSPs — gpayments
- 3DS Explained — Nuvei Documentation
- 3D Secure for regulation compliance — Adyen
- Challenge vs Frictionless 3DS2 — 2accept
- PSD2 and Strong Customer Authentication — Chargebee

### PCI DSS

- PCI Compliance SAQ Types — Exabeam
- Tokenization for PCI Compliance Scope Reduction — Curbstone
- PCI and Tokenization — pcibooking

### Webhooks

- Handling Payment Webhooks Reliably — Sohail
- Stripe Webhook Security — DEV
- Webhook Processing at Scale — DEV
- Stripe Webhooks Complete Guide — MagicBell
- Stripe Webhooks Integration Example — codehooks
- Reliable Shopify Webhooks — DEV

### BNPL / Split Payments

- BNPL-сервисы в России: Долями, Сплит — Retail.ru
- BNPL-сервисы в России — Pilot.ru
- BNPL отличие от рассрочки — РБК Тренды
- Yandex Split BNPL — Robokassa
- Splitit vs Klarna BNPL Comparison
- Klarna Payment Gateway Integration 2026 — Synder
- BNPL France — Stripe Resources

### Multi-tender / Split by Method

- Split payment between multiple cards/gift cards — GoTab
- Split payments at checkout — Vagaro
- Split credit card payments online — CreditCards.com
- Split Payment on Amazon — Spocket

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (1) Domain-Driven Design]] — Payment как отдельный BC
- [[Research - Order (2) State Machine FSM]] — Payment FSM (Authorized → Captured → Refunded)
- [[Research - Order (7) Saga Pattern]] — Payment в saga checkout, idempotency-keys, compensation
- [[Research - Cart Architecture (4) Pricing and Payments]] — pricing/payment на стороне Cart
- [[Backend]] — backend dashboard
- [[Loyality Project]]
