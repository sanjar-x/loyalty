---
tags:
  - project/loyality
  - backend
  - order
  - analytics
  - reporting
  - admin
  - research
type: research
date: 2026-04-29
aliases: [Order Analytics, Admin Operations, KPI Marketplace, Order Dashboards]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (8) Analytics and Operations

> Дашборды для admin panel — метрики (AOV, conversion, cancel rate, fulfillment time, GMV, take rate), фильтры, taxonomy причин отмен, retention/cohort analysis. Что показывают в Shopify / Magento admin. Типичные marketplace KPI и CQRS-разделение operational vs business read-models.

## TL;DR — ключевые выводы

1. **KPI разбивается на 5 логических pillars:** Acquisition (трафик), Conversion (продажа), Merchandising (товар), Fulfillment (выполнение), Retention (повторные покупки). Не пытайтесь засунуть всё в один dashboard.
2. **Базовый KPI набор:** AOV, Conversion Rate, Cart Abandonment Rate, Cancellation Rate, Time-to-Ship, On-Time Delivery %, Return Rate, Repeat Purchase Rate, NPS, GMV.
3. **Marketplace-specific:** GMV, Take Rate, Net Take Rate, supplier liquidity, buyer liquidity, match rate, GMV per cohort.
4. **Retention via cohort analysis** — основной инструмент LTV прогноза. Месячные cohorts с retention curve. Healthy LTV:CAC ≥ 3:1.
5. **Cancellation reasons** — обязательно taxonomized enum, не free-text. Топ-причины: out-of-stock, customer mind change, slow delivery, unexpected costs.
6. **Cart abandonment rate** ~70% в индустрии — это норма, цель снизить ниже 60%. Главные триггеры: unexpected costs, account creation, complex checkout.
7. **Shopify Analytics** — reference UI: customizable dashboard, metrics library, live view, custom reports на Advanced plan.
8. **Magento** — built-in reports + ecosystem: базовый dashboard скудный, серьёзная analytics — через extensions (Mirasvit, Amasty, Mageplaza) или внешние BI.
9. **CQRS-разделение** write и read. Operational dashboard + business KPI dashboard — разные read models, разные refresh policies.
10. **Admin filters:** status, date range, customer, payment, fulfillment, channel. **Bulk actions:** cancel, fulfill, refund, tag, export.

---

## 1. Категории метрик — 5 pillars

### 1.1 Канонический KPI tree

```text
                  Business Health
                        │
      ┌─────────────────┼──────────────────┐
      ▼                 ▼                  ▼
 Acquisition       Conversion        Retention
 (traffic)        (purchase)         (repeat)
      │                 │                  │
      ├ Sessions        ├ CR               ├ Repeat purchase rate
      ├ Traffic source  ├ AOV              ├ Cohort retention
      ├ CAC             ├ Cart abandonment ├ LTV
      ├ Bounce rate     ├ Checkout drop-off├ NPS
                        ├ Add-to-cart rate ├ Churn rate
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
      Merchandising         Fulfillment
      (product)             (operations)
            │                       │
            ├ Best sellers          ├ Time-to-ship
            ├ Stock-out rate        ├ Cancel rate
            ├ Margin per SKU        ├ On-time delivery %
            ├ Cross-sell rate       ├ Split shipment rate
            ├ Discount depth        ├ Return rate
                                    ├ Refund rate
                                    ├ Damaged/lost rate
```

### 1.2 Acquisition pillar

| Метрика | Формула | Цель |
|---|---|---|
| Sessions | Уникальные user sessions | Расти по cohorts |
| Traffic Sources | Organic / Paid / Direct / Email / Social split | Diversification |
| CAC (Customer Acquisition Cost) | Marketing spend / new customers | Снижать или держать стабильно |
| Bounce Rate | % сессий без interaction | < 40% — хорошо |
| Channel Attribution | Multi-touch attribution к каналам | Optimize budget allocation |

### 1.3 Conversion pillar

| Метрика | Формула | Industry benchmark |
|---|---|---|
| Conversion Rate | Orders / Sessions × 100% | E-commerce 1-3%, premium 4-8% |
| AOV (Average Order Value) | Total Revenue / Order Count | Industry-зависимо ($50-$200 typical) |
| Cart Abandonment Rate | (Carts Created - Orders) / Carts Created | ~70% indust avg, цель < 60% |
| Checkout Abandonment Rate | (Checkouts Started - Orders) / Checkouts Started | < 50% — здорово |
| Add-to-Cart Rate | Carts Created / Sessions | 5-10% |
| Items per Order | Total items / Total orders | Влияет через cross-sell |

### 1.4 Merchandising pillar

| Метрика | Назначение |
|---|---|
| Best Sellers | Top-N SKUs по revenue / units |
| Stock-Out Rate | % SKUs в out-of-stock состоянии |
| Sell-Through Rate | Sold units / available units |
| Margin per SKU | Profit / SKU (для discounting decisions) |
| Cross-Sell Rate | Orders с N+ items / total orders |
| Discount Depth | Average discount % vs full-price sales |
| Promo ROI | Incremental revenue от promo / promo cost |

### 1.5 Fulfillment pillar

| Метрика | Формула | Цель |
|---|---|---|
| Time-to-Ship | Avg(shipped_at - paid_at) | < 24h для SLA "ship next day" |
| Cancellation Rate | Cancelled / Total Orders | < 3% типично |
| On-Time Delivery % | Delivered by promised date / total | > 95% |
| Split Shipment Rate | Multi-shipment orders / multi-item orders | 10-40% обычно |
| Return Rate | Returns / Total Orders | Industry varies (apparel 20-30%, electronics 5-10%) |
| Refund Rate | Refunds / Total Orders | < 5% типично |
| Fill Rate | Items shipped / Items ordered | > 98% |
| WISMO Contact Rate | "Where Is My Order?" tickets / Orders | < 1% — здорово |

### 1.6 Retention pillar

| Метрика | Формула |
|---|---|
| Repeat Purchase Rate | Returning customers / total customers (per period) |
| Customer LTV | Avg revenue per customer over relationship |
| Cohort Retention Curve | % customers в cohort'е, делающих покупку через N месяцев |
| NPS (Net Promoter Score) | Promoters % - Detractors % |
| CSAT | % positive customer satisfaction surveys |
| Churn Rate | (Customers lost / Customers at start) per period |

---

## 2. AOV, Conversion, Cancellation, Fulfillment time — детали

### 2.1 AOV (Average Order Value)

```text
AOV = Total Revenue / Order Count
```

Зачем:

- Indicator effectiveness upselling и cross-selling.
- Влияет на CAC payback period (выше AOV → быстрее окупается customer).
- Сегмент: AOV per channel, per customer cohort, per product category.

Pitfalls:

- AOV может расти за счёт цен, не за счёт quality (inflation).
- Median Order Value часто более полезна чем mean (outliers).
- Сравнивать AOV per cohort (новые vs returning).

Levers для роста:

- Cross-sell ("Customers also bought").
- Upsell ("Premium version").
- Free shipping threshold ("Бесплатно от 3000₽").
- Bundle pricing.
- Gift wrap, accessories.

### 2.2 Conversion Rate

```text
CR = Orders / Sessions × 100%
```

Сегментация critical:

- CR new visitors vs returning (returning обычно в 2-3x выше).
- CR mobile vs desktop (mobile обычно ниже).
- CR per traffic source (paid vs organic).
- CR per product category.
- CR по странам / городам.

Funnel breakdown:

```text
Sessions → Product View → Add to Cart → Checkout Start → Checkout Complete → Order Placed
   100%        40%           8%             5%                3%                2%
```

Каждый шаг — drop-off. Анализ показывает где UX issues.

### 2.3 Cancellation Rate

```text
Cancellation Rate = Cancelled Orders / Total Orders × 100%
```

Разбивка:

- **Customer-initiated** cancellations — customer передумал.
- **Merchant-initiated** cancellations — out-of-stock, fraud, payment issue.
- **Auto-cancellations** — payment timeout, address invalid.

Key insight: разные buckets cancellations требуют разных fixes:

- Customer-initiated → улучшить UX, expectations management.
- Merchant-initiated → real-time inventory, fraud detection.
- Auto-cancellations → checkout flow improvements.

### 2.4 Fulfillment Time

Несколько метрик:

| Метрика | Семантика |
|---|---|
| Order-to-Ship | `shipped_at - paid_at` |
| Pick-to-Pack | warehouse internal speed |
| Ship-to-Deliver | carrier transit time |
| Order-to-Deliver (total) | end-to-end customer experience |

Что показывать:

- Median + p95 (не average — outliers искажают).
- Per warehouse / DC.
- Per carrier.
- Trend over time (regression alerts).

---

## 3. Marketplace-specific KPIs

### 3.1 GMV (Gross Merchandise Value)

```text
GMV = Σ всех order totals за период
```

Зачем: indicator размера платформы, growth trend.
Не путать с revenue: marketplace получает только commission (take rate).

### 3.2 Take Rate

```text
Take Rate = Marketplace Revenue / GMV × 100%
```

Industry typical:

- Generic marketplace: 10-15% (Amazon 15%, eBay 10%)
- Verticals: до 30% (food delivery)
- B2B / wholesale: 1-5%

### 3.3 Net Take Rate (NTR)

```text
NTR = (GMV × Take Rate - Direct Variable Costs) / GMV × 100%
```

Direct variable costs: payment processing, fraud, customer support, fulfillment subsidies.
NTR — реальная маржинальность маркетплейса, в отличие от gross take rate.

### 3.4 Liquidity metrics

| Метрика | Для чего |
|---|---|
| Buyer Liquidity | % searches, ending в покупке (на стороне покупателя) |
| Supplier Liquidity | % listings, продающихся в реасонабле time (на стороне продавца) |
| Match Rate | % ищущих, находящих to buy |
| Time to First Order | Avg time от регистрации customer до первой покупки |
| Time to First Sale | Avg time от seller signup до первой продажи |

### 3.5 Marketplace network effects

A16Z's "13 Metrics for Marketplace Companies":

- GMV growth
- Take rate
- Net revenue
- Active buyers / sellers
- Repeat usage
- Concentration (% revenue от top suppliers)
- Buyer-to-seller ratio
- Time to first transaction
- Geographic spread
- Mobile share

---

## 4. Cohort analysis — retention deep dive

### 4.1 Что это

Cohort = группа customers, объединённых временем первого events (обычно first purchase month).

```text
Месяц first purchase | Месяц 0 | Месяц 1 | Месяц 2 | Месяц 3 | Месяц 6
2025-01              |  100%   |  20%    |  15%    |  12%    |  9%
2025-02              |  100%   |  22%    |  18%    |  14%    |  ...
2025-03              |  100%   |  25%    |  20%    |  ...    |
```

Каждая ячейка — % customers cohort'а, сделавших purchase в данном месяце.

### 4.2 Retention curve

```text
%
100│●
   │
 80│
   │
 60│
   │ ●
 40│
   │
 20│  ●
   │     ●
   │        ●  ●  ●  ●  ●
   └────────────────────────► месяцы
       1  2  3  4  5  6  7  8
```

- **Healthy curve** — flattens out, не идёт в 0. Это значит "core engaged customers".
- **Unhealthy curve** — продолжает плавный спад → eventually 0 → нет retention base.

### 4.3 LTV via cohort

```text
Cumulative LTV(month N) = Σ revenue per customer, summed over N months
```

Cohort-based LTV — единственно правильный способ. Average LTV across all customers — мисленный (новые customers разводят showed mid).

### 4.4 LTV : CAC ratio

```text
LTV : CAC = LTV / CAC
```

- **Healthy:** ≥ 3:1
- **Marginal:** 2:1
- **Unhealthy:** < 1:1 (теряем деньги per customer)

> "Businesses that employ detailed cohort analysis have seen an average 30% improvement in customer retention rates and a 20% reduction in customer acquisition costs."

### 4.5 Behavioral cohorts

Помимо acquisition month, можно cohort'ить по:

- First product purchased.
- First channel (organic vs paid).
- First device (mobile vs desktop).
- AOV bucket первого order.
- Promo code use vs full-price.

Это раскрывает which acquisition channels reliably bring high-LTV customers.

---

## 5. Cart abandonment & checkout funnel

### 5.1 Indicator critical

> "Ecommerce funnel dropoffs typically cost businesses 60-85% of potential revenue."

> "Cart abandonment alone averages 70.19% across industries. A good cart abandonment rate is typically below 60%."

### 5.2 Funnel stages — детально

```text
Session Start
  ↓ (40-60% drop-off на product view)
Product View
  ↓ (80-90% drop-off на add-to-cart)
Add to Cart
  ↓ (40-60% drop-off "browsing carts")
Checkout Start (entered email/details)
  ↓ (20-40% drop-off на payment step)
Payment Step
  ↓ (10-20% drop-off на final confirmation)
Order Placed
```

### 5.3 Top causes of abandonment

1. **Unexpected costs** (shipping, taxes added at end) — top reason.
2. **Account creation forced** — гость должен зарегистрироваться.
3. **Complex checkout** — много полей, шагов.
4. **Trust concerns** — нет SSL/security badges, неизвестный merchant.
5. **Comparison shopping** — customer дальше изучать другие сайты.
6. **Slow loading** — особенно mobile.
7. **Limited payment methods** — нет Apple Pay / СБП / preferred метод.
8. **No clear delivery date** — 24% bail если no ETA.

### 5.4 Recovery tactics

- **Abandoned cart emails** — open rate ~41%, CTR ~9.5%, conversion 5-15%.
- **Exit-intent popups** — discount при попытке закрыть страницу.
- **Retargeting ads** — followup на social/Google.
- **SMS recovery** — особенно для мобильных пользователей.
- **Push notifications** (если у customer'а есть приложение).

### 5.5 Что измерять

| Метрика | Описание |
|---|---|
| Cart Creation Rate | Carts Created / Sessions |
| Cart Abandonment Rate | (Created - Completed) / Created |
| Checkout Abandonment Rate | (Started Checkout - Completed) / Started |
| Recovery Rate | Recovered orders / Abandoned orders |
| Recovery Revenue | $ recovered |
| Step-by-Step Drop-off | Per-stage % |

---

## 6. Cancellation reasons taxonomy

### 6.1 Зачем структурированный enum

Free-text "why cancelled" приводит к бесполезной аналитике (дубликаты, ошибки, разные формулировки одного). Enum + optional details — стандарт.

### 6.2 Топ-уровневая taxonomy

```text
CUSTOMER_INITIATED:
  - CHANGED_MIND          (~45% всех cancellations)
  - FOUND_BETTER_PRICE
  - WRONG_ITEM_SELECTED
  - WRONG_QUANTITY
  - WRONG_ADDRESS
  - DELIVERY_TOO_SLOW     (~35%)
  - DUPLICATE_ORDER
  - GIFT_NO_LONGER_NEEDED
  - DECIDED_INSTORE_BUY

MERCHANT_INITIATED:
  - OUT_OF_STOCK          (top merchant reason)
  - PRICE_ERROR
  - FRAUD_SUSPECTED
  - PAYMENT_FAILED
  - INVALID_ADDRESS
  - REGION_NOT_SERVED
  - ITEM_DISCONTINUED
  - LISTING_ERROR

SYSTEM_INITIATED:
  - PAYMENT_TIMEOUT
  - INVENTORY_TIMEOUT
  - 3DS_ABANDONED
  - CART_EXPIRED

LOGISTICS_INITIATED:
  - LOST_IN_TRANSIT
  - DAMAGED_BEFORE_DELIVERY
  - REFUSED_BY_CUSTOMER
  - UNDELIVERABLE_ADDRESS
```

### 6.3 Структура данных

```sql
CREATE TABLE order_cancellations (
    order_id        BIGINT PRIMARY KEY,
    cancelled_at    TIMESTAMP NOT NULL,
    reason_category VARCHAR(32) NOT NULL, -- top-level
    reason_code     VARCHAR(64) NOT NULL, -- specific code
    reason_details  TEXT,                 -- optional free-text
    initiated_by    VARCHAR(16) NOT NULL, -- 'customer'/'merchant'/'system'/'logistics'
    actor_id        VARCHAR(64),
    refund_required BOOLEAN NOT NULL,
    inventory_released BOOLEAN NOT NULL
);

CREATE INDEX ON order_cancellations(reason_category, cancelled_at);
```

### 6.4 Reason taxonomy — practical Ozon example

Из Темы 1: Ozon `cancel_reason_id` — справочник с `type_id: "buyer" | "seller"`. Это production-grade taxonomy enum:

```text
GET /v2/posting/.../cancel-reason/list
[
  { id: 352, title: "Product is out of stock", type_id: "seller" },
  { id: 361, title: "Other", type_id: "buyer" },
  ...
]
```

### 6.5 Analytics на reasons

Dashboard "Cancellation Drilldown":

- Reasons stacked bar chart по времени.
- Top-N reasons sorted by frequency.
- Cancellation rate per reason / per category / per channel.
- Cohort impact: cancelled customers retention rate (часто хуже non-cancelled).

---

## 7. Shopify Analytics — reference UI

### 7.1 Структура

Shopify Analytics состоит из 3 компонентов:

1. **Overview Dashboard** — главная страница с metrics cards.
2. **Reports** — детальные built-in отчёты.
3. **Live View** — real-time monitoring.

### 7.2 Overview Dashboard

> "The customizable dashboard on the Analytics page is a collection of data cards, known as metrics, each offering you a quick sum or value about a particular business indicator, such as Net sales by channel or Sessions by device type."

Default metric cards:

- Total sales / Net sales
- Orders
- Sessions
- Conversion rate
- Returning customer rate
- AOV
- Total sales by channel
- Top products
- Top traffic sources
- Online store sessions by device

User может добавлять/удалять cards из Metrics library.

### 7.3 Reports (built-in)

Категории reports:

- **Acquisition** — visitors, sessions, traffic sources.
- **Behavior** — bounce, top searches, devices.
- **Marketing** — channels, campaigns ROI.
- **Sales** — net sales, gross sales, taxes, discounts, gift cards.
- **Profit** — gross margin, COGS-aware.
- **Customers** — first-time, returning, churn.
- **Inventory** — units sold, days of inventory remaining.
- **Finance** — full P&L, balance sheet adjacent.

Custom reports на Advanced+ plans — drag-and-drop builder.

### 7.4 Live View

> "Shopify's Live View provides merchants with real-time store activity metrics and a world map highlighting global visitor locations. Live View displays real-time visitor behavior. Teams can see geographic distribution, page navigation, cart additions, and completed checkouts as they occur."

Обычно used during peak events (Black Friday, marketing campaigns) для real-time signal "что работает сейчас".

### 7.5 Multi-store analytics (Plus)

Shopify Plus organization-level reporting: cross-store comparison, consolidated revenue, brand-level KPIs. Critical для multi-brand companies.

---

## 8. Magento / Adobe Commerce admin

### 8.1 Built-in reports

Reports menu в admin panel:

- **Marketing** — coupons usage, abandoned carts.
- **Sales** — Orders, Tax, Invoiced, Shipping, Refunds, Coupons.
- **Reviews** — by product, by customer.
- **Customers** — by group, by orders, by reviews.
- **Products** — bestsellers, viewed, low stock, ordered.

### 8.2 Filters

Каждый report support:

- Date / Period (day, month, year).
- From/To range.
- Order Status filter.
- Other params (store view, product, customer group).

Export: CSV или XML.

### 8.3 Limitations

Built-in аналитика Magento часто критикуется за:

- Slow on large datasets.
- Limited customization.
- No real-time / live view.
- Скудный default dashboard.
- Отсутствие cohort analysis natively.

### 8.4 Ecosystem extensions

Production Magento обычно дополняется:

- **Mirasvit Advanced Reports** — replacement dashboard.
- **Amasty Advanced Reports** — analytics by category, customer group.
- **Mageplaza Order Reports** — order-focused metrics.
- **Aheadworks Advanced Reports**.
- **SavvyCube** — cloud BI for Magento.

### 8.5 Adobe Commerce Cloud

В enterprise edition — Advanced Reporting на базе Adobe Analytics (originally Snowflake-backed). Включает:

- Pre-built business intelligence.
- Visualizations.
- Cohort и behavioral analysis.

Это уже отдельная BI-платформа поверх Magento.

---

## 9. Admin operations — orders management UI

### 9.1 Order list

Базовый интерфейс:

```text
[Filters bar]
  [Status: All ▾] [Date: Last 30 days ▾] [Channel: All ▾] [Search: ____]
  [More filters ▾]: payment, fulfillment, customer, tag, country, total range

[Bulk actions]
  ☑ Select all  [▾ Bulk action]: Cancel | Fulfill | Tag | Export | Print labels

[Table]
  ☑ | Order # | Date    | Customer | Total | Payment    | Fulfillment | Tags
  ─────────────────────────────────────────────────────────────────────────
  ☐ | #1234   | Apr 28  | John D.  | $99   | Paid       | Unfulfilled | VIP
  ☐ | #1235   | Apr 28  | Mary S.  | $145  | Pending    | -           |
  ...

[Pagination] [Items per page: 25 ▾]
```

### 9.2 Filter taxonomy

| Filter type | Examples |
|---|---|
| Status | Open / Closed / Cancelled / Archived |
| Date | Today / Last 7d / Last 30d / Custom range |
| Payment | Paid / Pending / Refunded / Voided / Authorized |
| Fulfillment | Unfulfilled / Partially / Fulfilled / Restocked |
| Channel | Web / Mobile App / Marketplace / POS |
| Customer | New / Returning / VIP / Specific email |
| Tag | Custom labels (Wholesale, Gift, Subscription) |
| Region | Country / state / postal range |
| Risk level | Low / Medium / High (fraud) |
| Total range | $X - $Y |
| Items count | Single item / 2-3 / 4+ |

### 9.3 Search

Universal search bar:

- Order number (exact match).
- Customer email / name (partial match).
- Tracking number.
- SKU.
- Address fragments.

### 9.4 Bulk actions

| Action | Когда применяется |
|---|---|
| Cancel | Mass cancellation (например, unable to fulfill batch) |
| Fulfill | Mark shipped (если carrier label generated externally) |
| Capture payment | Capture authorized payments в batch |
| Refund | Mass refund (rare, обычно per-order) |
| Tag | Apply tag для grouping/filtering |
| Print labels | Generate batch shipping labels |
| Print picking lists | Warehouse ops |
| Export CSV/Excel | For external reporting |
| Send email | Custom communication |
| Archive | Hide completed orders из default view |

### 9.5 Single order detail page

Standardized layout:

- **Header:** Order #, status badges (financial + fulfillment), customer link.
- **Timeline:** events (paid, shipped, delivered, refunded) с timestamps.
- **Items:** list с photos, SKUs, quantity, price, fulfillment status per line.
- **Totals:** subtotal, discounts, taxes, shipping, total.
- **Customer:** contact, addresses, customer history link.
- **Payment:** method, transactions, refunds.
- **Fulfillment:** shipments, tracking, delivery status.
- **Notes:** internal staff notes + customer-visible notes.
- **Actions:** Cancel, Refund, Fulfill, Edit, Duplicate, Print invoice/label.

---

## 10. Data architecture для analytics

### 10.1 CQRS — separation read и write

**OLTP database (transactional):**

- Optimized для writes (Order create, FSM transitions).
- Normalized schema.
- Single-row queries.

**OLAP database (analytical):**

- Optimized для reads (aggregations, joins).
- Denormalized fact tables.
- Columnar storage (ClickHouse, BigQuery, Snowflake, Redshift).

Между ними: ETL/CDC (Debezium → Kafka → DWH).

### 10.2 Star schema для orders

```text
fact_orders (огромная таблица)
  ├── order_id
  ├── customer_id (FK)
  ├── product_id (FK)
  ├── time_id (FK)
  ├── channel_id (FK)
  ├── geo_id (FK)
  ├── revenue
  ├── quantity
  ├── discount_amount
  ├── tax_amount
  ├── ...

dim_customer (атрибуты customer'а)
dim_product (атрибуты product'а)
dim_time (день, неделя, месяц, год, holiday flag)
dim_channel (online/mobile/POS/marketplace)
dim_geo (city, region, country)
```

Aggregation queries — fast благодаря star schema.

### 10.3 Real-time vs batch

- **Real-time** (live view, current orders): из OLTP или streaming через Kafka → KSQL/Flink.
- **Daily/hourly batch** (KPI dashboards): out of OLAP DWH через scheduled jobs (Airflow).
- **On-demand reports** (custom queries): OLAP с caching layer.

### 10.4 Materialized views

Frequent dashboards = cached aggregations:

```sql
CREATE MATERIALIZED VIEW daily_kpi_summary AS
SELECT
    date_trunc('day', placed_at) AS day,
    channel,
    COUNT(*) AS orders_count,
    SUM(total) AS gmv,
    AVG(total) AS aov,
    COUNT(*) FILTER (WHERE state = 'cancelled') AS cancelled_count,
    COUNT(*) FILTER (WHERE state = 'cancelled') * 100.0 / COUNT(*) AS cancel_rate
FROM orders
GROUP BY 1, 2;

REFRESH MATERIALIZED VIEW daily_kpi_summary; -- nightly
```

---

## 11. Dashboard design — best practices

### 11.1 Tiered dashboards

**Tier 1: Executive (CEO/COO/VP)**

- 5-7 top KPIs
- Trend (vs last period, YoY)
- One-glance health check

**Tier 2: Functional (Marketing, Ops, Finance)**

- Pillar-specific metrics
- Drilldowns
- Filters per team domain

**Tier 3: Operational (Warehouse, Customer Service)**

- Real-time view
- Action-oriented (today's orders to ship, today's tickets)
- Alerts on outliers

**Tier 4: Analytical (Data team)**

- Ad-hoc queries
- Cohort analysis
- Custom reports

### 11.2 Dashboard составляющие

Каждый dashboard component:

- **Title** — clear description.
- **Current value** — main number.
- **Change indicator** — vs comparison period (Δ% green/red).
- **Sparkline** — micro trend.
- **Optional drilldown** — click чтобы зайти deeper.

### 11.3 Anti-patterns

- ❌ "Dashboard of everything" — 50+ metrics на экране.
- ❌ Vanity metrics (sessions без CR context).
- ❌ Static numbers без trend.
- ❌ No comparison period (число без context'а).
- ❌ Real-time когда нужен trend (наоборот тоже плохо).
- ❌ Mixed time granularities (одна card hourly, другая monthly).
- ❌ Dashboard без owner — нет ответственного за accuracy.

### 11.4 Self-service vs guided

- **Guided dashboards** — pre-built, fixed layout. Для не-technical stakeholders.
- **Self-service BI** (Looker/Metabase/Tableau/Superset) — power users могут строить свои queries.

Лучший подход: tiered access.

---

## 12. Alerts & anomaly detection

### 12.1 Что мониторить с alerting

- [ ] Conversion rate drop > 20% (за час)
- [ ] Cart abandonment rate spike > 75% (за час)
- [ ] Cancellation rate spike > 5% (за час)
- [ ] Time-to-ship >> SLA (per warehouse)
- [ ] Orders per minute drop (signal что что-то сломано — pixels, search)
- [ ] Failed payment rate > X% (signal PSP issue)
- [ ] Stock-out rate spike (важные SKU)
- [ ] Inventory reservation backlog (не отпускаемые)
- [ ] Webhook backlog (если retries не processed)
- [ ] Refund rate spike (issue с product quality?)

### 12.2 Smart alerts

Не просто threshold, а:

- **Seasonality-aware** (Sunday traffic ≠ weekday).
- **Trend-aware** (gradual decline vs sudden drop).
- **Channel-segmented** (paid traffic drop ≠ overall drop).
- **Anomaly detection ML** (Datadog/Grafana ML, AWS CloudWatch Anomaly).

### 12.3 Action workflows

Каждый alert связывается с runbook:

- **Conversion drop** → check landing page, check checkout, check payment provider.
- **Stock-out spike** → check inventory feed, contact warehouse.
- **Cancellation spike** → check fraud signals, check carrier issues.

---

## 13. Compliance & audit reporting

### 13.1 Финансовая отчётность

- **Daily revenue close** — total sales по channels, для accounting.
- **Tax reports** — per region, для VAT/sales tax filings.
- **Refund reports** — для chargeback monitoring.
- **GMV reconciliation** — Order BC vs Payment BC vs ERP.

### 13.2 Российский context

- **Чеки 54-ФЗ** — ОФД integration logs.
- **Маркировка (CRPT)** — товары с маркировкой, audit trail.
- **Bank reconciliation** — daily reconcile с bank account.

### 13.3 GDPR / 152-ФЗ

- **PII access log** — кто из admins видел customer data.
- **Right to erasure report** — track customer data deletion.
- **Data export report** — DSAR fulfillment.

---

## 14. Anti-patterns admin UX и analytics

| Anti-pattern | Описание | Правильно |
|---|---|---|
| Free-text cancel reasons | "Why?: ___" без структуры | Enum + optional details |
| Counting cancellations after pivot | Refund != cancellation | Distinguish cancel (pre-ship) vs return (post-ship) |
| AOV без segmentation | Single AOV для всего бизнеса | По channel, cohort, category |
| CR без segmentation | One CR for everyone | New vs returning, mobile vs desktop |
| Average LTV | Mean across all customers | Cohort-based LTV |
| Real-time orders count как KPI | Live count != business metric | Trends + comparison periods |
| No drilldown | Только high-level numbers | Click → детали |
| Stale data без disclaimer | Customer думает live, реально 24h old | Show "Last updated: HH:MM" |
| Dashboard для каждого stakeholder | Один dashboard per person | Tiered, role-based |
| Mixing currencies без normalization | $ + ₽ + € в одном | Single base currency для aggregate |
| No baseline / benchmark | "AOV 10 000₽" без контекста | "AOV 10 000₽ (vs target 12 000₽, vs LY 9500₽)" |

---

## 15. Чек-лист — admin analytics & ops

- [ ] Tiered dashboards: executive / functional / operational / analytical
- [ ] 5 pillars covered: Acquisition / Conversion / Merchandising / Fulfillment / Retention
- [ ] AOV, CR, Cart abandonment, Cancellation rate — на executive dashboard
- [ ] Time-to-ship, On-time delivery — на operational dashboard
- [ ] Cohort retention curve — отдельная analytical view
- [ ] LTV : CAC ratio tracked per cohort
- [ ] Cancellation reasons — taxonomized enum, не free-text
- [ ] Cancellation reasons split: customer / merchant / system / logistics
- [ ] CQRS: separate OLTP (writes) и OLAP (reads)
- [ ] Star schema fact_orders + dimensions
- [ ] Materialized views для frequent aggregations
- [ ] Real-time live view для current activity
- [ ] Daily / weekly / monthly / quarterly comparison toggles
- [ ] Drilldown navigation от KPI к individual orders
- [ ] Order list: фильтры по status, date, payment, fulfillment, channel
- [ ] Bulk actions: cancel, fulfill, tag, export, print labels
- [ ] Single order page: timeline, items, customer, payment, fulfillment, notes
- [ ] Search: order #, customer, tracking, SKU
- [ ] Export: CSV, Excel, PDF
- [ ] Alerts: anomaly-aware, channel-segmented, runbook-linked
- [ ] Marketplace KPIs (если applicable): GMV, take rate, NTR, liquidity
- [ ] Cohort analysis tool (built-in или внешний)
- [ ] Funnel analysis: stages, drop-off rates
- [ ] Compliance reports: daily revenue close, tax, audit trail
- [ ] Multi-currency normalization
- [ ] Multi-region / multi-store consolidation (для multi-brand)
- [ ] PII access logging (GDPR/152-ФЗ)
- [ ] Dashboard owner и refresh-policy документированы

---

## 16. Связь с другими темами

- **Тема 1 (E-commerce gigants)** — Shopify Analytics — reference UI; Amazon Brand Analytics для sellers; Wildberries аналитика воронки продаж.
- **Тема 2 (OMS)** — IBM Sterling, Manhattan включают operational dashboards. Analytics — отдельный layer (BI).
- **Тема 3 (DDD)** — analytics — read-side CQRS. Materialized views generated from domain events.
- **Тема 4 (FSM)** — cancellation reasons как часть FSM transition metadata.
- **Тема 5 (Saga)** — saga visibility metrics: completion rate, compensation rate, latency.
- **Тема 6 (Payment)** — payment-specific KPIs: success rate per PSP, 3DS friction rate, refund rate.
- **Тема 7 (Logistics)** — fulfillment KPIs: on-time delivery, split shipment rate, return rate per carrier.
- **Тема 9 (Returns)** — return-specific analytics: reason taxonomy, restock rate, inspection time.

---

## 17. Источники

### General KPIs

- Commerce Analytics: KPIs Every Ecommerce Leader Should Track — FastSlowMotion
- eCommerce KPIs and Metrics — SPX Commerce
- Track These eCommerce KPIs — ArcherPoint
- Ecommerce Dashboard KPIs — Fusedash
- Ecommerce KPIs: Formulas, Benchmarks — NetSuite
- Top ecommerce KPIs every business should track in 2026 — Usermaven
- 14 Crucial Ecommerce KPIs — Flowspace
- Ecommerce Metrics in 2026 — BigCommerce
- 5 KPIs to track ecommerce store success — Klipfolio
- Ecommerce KPI Dashboard Top Metrics — Databrain

### Shopify

- Shopify Help — Analytics overview dashboard
- Shopify Help — Shopify analytics
- Shopify Analytics Dashboard explained — Luca
- Shopify Analytics Comprehensive Guide — Saras Analytics
- Shopify Analytics: Reports, Dashboards — Plausible
- Store Performance Dashboard — Shopify Retail
- Shopify Help — Organization analytics
- Shopify Analytics 2026 Step-by-Step — TrueProfit
- Ultimate Shopify Dashboard Guide — Improvado

### Magento

- Magento 2 Reports — Mageplaza
- Magento Reports: Sales, Marketing — Magefan
- Magento Reporting Tool — Whatagraph
- Magento 2 Advanced Reports — Mirasvit
- Magento 2 Advanced Reports — Aheadworks
- Magento 2 Reports Extension — Amasty
- Reports menu — Adobe Commerce docs
- Magento Order Management Reports archive
- Magento Analytics — SavvyCube

### Marketplace KPIs

- Marketplace metrics: 14 key metrics — Stripe
- 13 Metrics for Marketplace Companies — Andreessen Horowitz
- Marketplace metrics: 26 key metrics — Sharetribe
- Top marketplace KPIs — ChannelEngine
- Cheat sheet Key Metrics for Marketplaces — Samaipata
- How to Measure eCommerce Marketplace Success — CS-Cart
- E-Commerce Marketplace KPIs CAC LTV Take-Rate — Financial Models Lab
- 10 marketing metrics for marketplace — Rademade Wiki

### Cohort & LTV/CAC

- Cohort Retention Analysis — Saras Analytics
- Cohort LTV in Excel for e-commerce/SaaS — Glencoyne
- Cohort Analysis 101 — Peel Insights
- Shopify LTV and CAC Cohort Analysis — Sparkco
- Cohort Analysis to Calculate Customer LTV — NudgeNow
- Cohort Analysis for Lifetime Value Estimation — Growth-onomics
- Cohort Analysis in eCommerce — Promodo
- Retention Cohort Analysis — Waveup
- Why cohort analysis beats other LTV approaches — Amp

### Cancellation & Returns

- Order Cancellation overview — WallStreetMojo
- How to Reduce Order Cancellation Rates — Fluent Commerce
- "Customer Canceled" Top Reasons — Hubifi
- How to Avoid Order Cancellation — Pollfish
- Top reasons why customers cancel — Moxo
- Why Customers Cancel — Chargebee
- Tips For Handling Order Cancellations — airisX

### Cart Abandonment & Funnel

- Ecommerce Funnel Dropoffs Analysis — Heatmap
- Understanding Cart Abandonment Rates Benchmarks — Wallid
- Cart Abandonment Rate Formula Stats — Count.co
- Funnel drop-off rate — Lifesight
- Analyze Cart Abandonment in GA4 — Webstar Research
- Hidden Funnel Drop-off Points — SlashExperts
- Cart Abandonment Analysis — Kissmetrics
- Track Shopping Cart Abandonment in Google Analytics — Barilliance
- Cart Abandonment Funnel Shopify Guide — Growth Suite
- Checkout Abandonment Right Metric — Data8

### Admin operations

- WooCommerce Order Management with Filters — Admin Columns
- Smart Filtering — Admin Columns
- Manage Orders — Blink Help Center
- orders query — Shopify GraphQL Admin
- Apply Bulk Actions to Orders — Extensiv
- Magento 2 Order Collection Filters — Mageplaza
- Shopify Help — Filtering orders
- Orders Overview Bulk Management — WooCommerce
- Magento 2 Bulk Order Processing — Land of Coder

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (3) E-commerce Giants]] — что показывают Shopify / Magento admin UI
- [[Research - Order (4) OMS Platforms]] — agent UI и operational dashboards в OMS
- [[Research - Order (2) State Machine FSM]] — фильтры по statuses требуют чистую FSM
- [[Backend]] — модуль `activity` для retention/cohort
- [[Loyality Project]]
