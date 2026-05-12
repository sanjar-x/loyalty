# Архитектура корзины покупок: Исследование крупнейших e-commerce платформ мира

**Версия:** 1.0
**Дата:** 2026-03-25
**Автор:** Enterprise Architecture Research Team
**Статус:** Завершено

---

## Оглавление

1. [Резюме](#1-резюме)
2. [Amazon — Dynamo и корзина в масштабе 300M+ пользователей](#2-amazon)
3. [Alibaba / Taobao / Tmall — Мультиселлерная корзина и Singles Day](#3-alibaba)
4. [Shopify — Cart API и модульный монолит](#4-shopify)
5. [Walmart — DDD и гексагональная архитектура корзины](#5-walmart)
6. [eBay — Stateless архитектура и горизонтальное масштабирование](#6-ebay)
7. [JD.com — Контейнеризация и Kubernetes в масштабе](#7-jdcom)
8. [Общие паттерны и сравнительный анализ](#8-общие-паттерны)
9. [Стратегии резервирования инвентаря](#9-стратегии-резервирования-инвентаря)
10. [Event Sourcing vs CRUD для корзины](#10-event-sourcing-vs-crud)
11. [Управление сессиями и слияние корзин](#11-управление-сессиями-и-слияние-корзин)
12. [Политики истечения и очистки корзин](#12-политики-истечения-и-очистки-корзин)
13. [Мультиселлерная корзина (Marketplace)](#13-мультиселлерная-корзина)
14. [Рекомендации для проектирования](#14-рекомендации)
15. [Источники](#15-источники)

---

## 1. Резюме

Данное исследование охватывает архитектуру корзины покупок (Shopping Cart) шести крупнейших e-commerce платформ мира: Amazon, Alibaba (Taobao/Tmall), Shopify, Walmart, eBay и JD.com. Совокупно эти платформы обслуживают более 2 миллиардов активных покупателей и обрабатывают триллионы транзакций ежегодно.

### Ключевые выводы

| Аспект                  | Доминирующий подход                                            |
| ----------------------- | -------------------------------------------------------------- |
| **Хранилище данных**    | Key-Value (DynamoDB) + In-Memory Cache (Redis/Tair)            |
| **Модель данных**       | Корзина как агрегат (Aggregate Root) с элементами (CartItem)   |
| **Архитектурный стиль** | Микросервисы с DDD (Walmart) или модульный монолит (Shopify)   |
| **Масштабирование**     | Горизонтальное шардирование по user_id/shop_id                 |
| **Консистентность**     | Eventually Consistent (Amazon) / Strong для критичных операций |
| **Кэширование**         | Write-through + Cache-aside с Redis/Tair                       |
| **Ценообразование**     | Живое ценообразование (live pricing) с кэшированием            |
| **Резервирование**      | Оптимистичная блокировка с soft reservation при checkout       |
| **TTL корзины**         | 1 день (гость) / 7-30 дней (аутентифицированный)               |
| **API дизайн**          | REST (Amazon, Walmart) / GraphQL (Shopify)                     |

---

## 2. Amazon

### 2.1 Историческая справка

В 2004-2005 годах Amazon столкнулся с критическими проблемами масштабирования реляционной базы данных. При обработке более 10 миллионов запросов в день корзина покупок стала узким местом, вызывая сбои в часы пиковой нагрузки. Анализ показал, что **70% операций требовали только простую модель ключ-значение**, что делало реляционную базу данных неэффективной.

Этот кризис привёл к созданию **Dynamo** — распределённого хранилища ключ-значение, специально спроектированного для корзины покупок. Dynamo впоследствии стал основой для публичного сервиса **Amazon DynamoDB**.

### 2.2 Архитектура Dynamo для корзины

```
┌─────────────────────────────────────────────────────────┐
│                    Amazon Cart Architecture             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌──────────┐    ┌──────────────┐    ┌──────────────┐  │
│   │  Client  │───>│  API Gateway │───>│ Cart Service │  │
│   │(Browser) │    │              │    │ (Lambda/EC2) │  │
│   └──────────┘    └──────────────┘    └──────┬───────┘  │
│                                              │          │
│                         ┌────────────────────┤          │
│                         │                    │          │
│                  ┌──────▼───────┐    ┌───────▼────────┐ │
│                  │   DynamoDB   │    │   Cognito      │ │
│                  │  (Cart Data) │    │ (Auth/Session) │ │
│                  └──────┬───────┘    └────────────────┘ │
│                         │                               │
│                  ┌──────▼───────┐                       │
│                  │   DynamoDB   │                       │
│                  │   Streams    │                       │
│                  └──────┬───────┘                       │
│                          │                              │
│                   ┌──────▼───────┐                      │
│                   │ Stream       │                      │
│                   │ Processor    │                      │
│                   │ (Aggregation)│                      │
│                   └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

### 2.3 Модель данных (DynamoDB Single-Table Design)

```
┌────────────────────────────────────────────────────────┐
│                    DynamoDB Table: Carts               │
├──────────────┬──────────────┬──────────────────────────┤
│ PK (Partition│  SK (Sort    │  Attributes              │
│ Key)         │  Key)        │                          │
├──────────────┼──────────────┼──────────────────────────┤
│ USER#<uuid>  │ CART#META    │ status, createdAt,       │
│              │              │ updatedAt, ttl           │
├──────────────┼──────────────┼──────────────────────────┤
│ USER#<uuid>  │ ITEM#<sku>   │ productId, quantity,     │
│              │              │ price, variantId, ttl    │
├──────────────┼──────────────┼──────────────────────────┤
│ USER#<uuid>  │ PROMO#<code> │ discountType, value,     │
│              │              │ appliedAt                │
└──────────────┴──────────────┴──────────────────────────┘

GSI: ProductIndex
  PK: productId
  SK: userId
  Projection: quantity
  (Для аналитики: сколько пользователей имеют товар X в корзине)
```

**Ключевые решения:**

- **Partition Key:** UUID пользователя (для анонимных — UUID из cookie)
- **Sort Key:** Идентификатор товара — обеспечивает эффективное получение конкретных позиций
- **TTL:** Встроенный механизм DynamoDB для автоматического удаления просроченных записей
  - Анонимные корзины: TTL = 1 день
  - Аутентифицированные: TTL = 7 дней

### 2.4 Консистентность и разрешение конфликтов

Amazon выбрал **Eventually Consistent** модель с техникой **sloppy quorum**:

```
R + W > N

Где:
  R = количество серверов, которые должны ответить на чтение
  W = количество серверов, которые должны ответить на запись
  N = фактор репликации
```

**Разрешение конфликтов корзины:**

1. **Векторные часы (Vector Clocks):** Отслеживают причинно-следственные связи между версиями данных
2. **Стратегия слияния:** При конфликте корзина выполняет **объединение содержимого** (union merge)
3. **Побочный эффект:** Удалённые товары могут "возвращаться" в корзину — это **сознательный компромисс** в пользу доступности записи

> *"Для корзины покупок лучше показать удалённый товар, чем потерять добавленный"*
> — Werner Vogels, Amazon CTO

### 2.5 Обработка отказов

| Механизм               | Назначение                                                          |
| ---------------------- | ------------------------------------------------------------------- |
| **Consistent Hashing** | Распределение данных по серверам с минимальной перебалансировкой    |
| **Virtual Nodes**      | Устранение проблемы hot shard через множественные позиции на кольце |
| **Hinted Handoff**     | Временная запись на здоровый сервер при недоступности целевого      |
| **Merkle Trees**       | Эффективная фоновая синхронизация реплик                            |
| **Gossip Protocol**    | Децентрализованное обнаружение членства в кластере                  |

### 2.6 Ключевые метрики

- **300M+** активных покупателей
- **Latency:** < 10ms для операций чтения/записи корзины (p99)
- **Доступность:** 99.995% (по условиям SLA DynamoDB)
- **Пропускная способность:** Автоматическое масштабирование от единиц до миллионов запросов в секунду

---

## 3. Alibaba

### 3.1 Масштаб проблемы

Alibaba (Taobao, Tmall) обслуживает рынок с уникальными вызовами:

- **1+ миллиард** SKU товаров
- **900+ миллионов** активных покупателей
- **Singles Day 11.11:** пик 583 000 транзакций/секунду
- **87 миллионов** запросов к базе данных в секунду в пиковые моменты
- **$1 миллиард** GMV за первые 68 секунд распродажи
- **Мультиселлерная корзина:** один покупатель — товары от десятков продавцов

### 3.2 Архитектура стека

```
┌───────────────────────────────────────────────────────────────┐
│                  Alibaba Cart Architecture                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────┐  ┌──────────────┐   ┌──────────────────────────┐ │
│  │ Taobao  │  │  API Gateway │   │   Cart Service (HSF →    │ │
│  │   App   │──│  (Tengine)   │───│   Dubbo3 RPC)            │ │
│  └─────────┘  └──────────────┘   └────────────┬─────────────┘ │
│                                               │               │
│                   ┌───────────────────────────┤               │
│                   │                           │               │
│            ┌──────▼──────┐           ┌────────▼──────────┐    │
│            │    Tair      │          │   OceanBase /     │    │
│            │ (In-Memory   │          │   POLARDB         │    │
│            │  Cache)      │          │   (Persistent)    │    │
│            │              │          │                   │    │
│            │ < 0.8ms      │          │   87M req/sec     │    │
│            │ latency      │          │   peak            │    │
│            └──────────────┘          └───────────────────┘    │
│                                                               │
│            ┌──────────────┐          ┌───────────────────┐    │
│            │  RocketMQ    │          │   Flink Streaming │    │
│            │(Async Events)│          │   (Analytics)     │    │
│            └──────────────┘          └───────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

### 3.3 Tair — Сердце кэширования корзины

Tair — собственная разработка Alibaba, Redis-совместимое распределённое in-memory хранилище:

**Архитектура Tair:**
```
┌────────────────────────────────────────┐
│            Tair Cluster                │
├────────────────────────────────────────┤
│                                        │
│  ┌──────────────┐                      │
│  │  ConfigServer│ ← Heartbeat ──┐      │
│  │  (Primary)   │               │      │
│  ├──────────────┤               │      │
│  │  ConfigServer│               │      │
│  │  (Standby)   │               │      │
│  └──────┬───────┘               │      │
│         │ Data Distribution     │      │
│         │ Table                 │      │
│  ┌──────▼───────┐               │      │
│  │  DataServer 1 │──────────────┤      │
│  │  DataServer 2 │──────────────┤      │
│  │  DataServer N │──────────────┘      │
│  └──────────────┘                      │
│                                        │
│  Client → ConfigServer (get routing)   │
│  Client → DataServer (read/write)      │
└────────────────────────────────────────┘
```

**Характеристики для корзины:**
- **Latency:** < 0.8 ms
- **Throughput:** Один кластер Tair поддерживает **100 GB/s** трафика
- **Технологии:** Connection Aggregation + Asynchronous Write
- **Сотни миллионов** вызовов в секунду во время Double 11

### 3.4 Middleware стек (HSF → Dubbo3)

Микросервисы корзины в Taobao исторически использовали **HSF (High-Speed Service Framework)** — собственный RPC фреймворк Alibaba. В 2020 году началась миграция на **Apache Dubbo3**, который к 2023 году полностью заменил HSF2.

**Ключевые характеристики:**
- Поддержка **миллионов** нод в кластере
- Используется в критических бизнес-потоках: Taobao, Tmall, Ele.me, 1688
- Единый фреймворк сервисов Alibaba Group

### 3.5 Подготовка к Singles Day

Alibaba использует детальное планирование ёмкости, моделируя:
- Долю товаров, добавленных в корзину
- Количество товаров в одном заказе
- Паттерны использования купонов
- Пропорцию корзин, доходящих до checkout

**Оптимизации:**
- **Pre-warming кэша** корзин перед началом распродажи
- **Batch processing** с time-trigger/record-trigger механизмами
- **Mini-batch sink** для группировой записи с настраиваемой задержкой
- **Stream computing** (Apache Flink) для реалтайм-аналитики с секундной задержкой

### 3.6 OceanBase для персистентного хранения

OceanBase — собственная распределённая СУБД Alibaba:
- Поддерживает критические бизнес-системы: транзакции Alipay, платежи, избранное Taobao/Tmall
- Мульти-тенантная архитектура
- Обработка сценариев высокой конкурентности (тысячи пользователей одновременно добавляют товары в корзины)
- Хранение **триллионов** записей заказов с петабайтами данных

---

## 4. Shopify

### 4.1 Философия: Модульный монолит

Shopify принципиально отличается от остальных платформ — вместо микросервисной архитектуры они используют **"Majestic Monolith"** — один большой Ruby on Rails монолит с модульной внутренней структурой.

**Масштаб:**
- **2.8 миллиона** строк кода в ядре (Shopify Core)
- **500 000+** коммитов
- **Black Friday 2024:** 173 миллиарда запросов, пик 284 миллиона req/min
- **12 TB** данных через edge-инфраструктуру каждую минуту

### 4.2 Pod Architecture (Шардирование)

```
┌──────────────────────────────────────────────────────┐
│                Shopify Pod Architecture              │
├──────────────────────────────────────────────────────┤
│                                                      │
│   ┌───────────────┐ ┌───────────────┐                │
│   │    Pod 1      │ │    Pod 2      │ ...Pod N       │
│   │ ┌───────────┐ │ │ ┌───────────┐ │                │
│   │ │ Shop A    │ │ │ │ Shop D    │ │                │
│   │ │ Shop B    │ │ │ │ Shop E    │ │                │
│   │ │ Shop C    │ │ │ │ Shop F    │ │                │
│   │ └───────────┘ │ │ └───────────┘ │                │
│   │               │ │               │                │
│   │ ┌───────────┐ │ │ ┌───────────┐ │                │
│   │ │ MySQL     │ │ │ │ MySQL     │ │                │
│   │ │ (Vitess)  │ │ │ │ (Vitess)  │ │                │
│   │ └───────────┘ │ │ └───────────┘ │                │
│   └───────────────┘ └───────────────┘                │
│                                                      │
│   Sharding Key: shop_id                              │
│   Крупные мерчанты → выделенный Pod                  │
│   100+ database shards с zero-downtime миграциями    │
└──────────────────────────────────────────────────────┘
```

**Ключевое решение:** Шардирование по `shop_id` обеспечивает:
- Полную изоляцию ресурсов между тенантами
- Локализацию "шумного соседа" (noisy neighbor)
- Независимую масштабируемость каждого пода

### 4.3 Cart API (GraphQL Storefront API)

Shopify предоставляет публичный GraphQL API для управления корзиной — один из наиболее хорошо задокументированных Cart API в индустрии.

**Объект Cart — полная схема:**

```graphql
type Cart implements Node & HasMetafields {
  id: ID!
  createdAt: DateTime!
  updatedAt: DateTime!
  checkoutUrl: URL!                        # URL для перехода к checkout
  totalQuantity: Int!                      # Общее количество товаров
  note: String                             # Заметка покупателя

  # Товарные позиции (с пагинацией)
  lines: BaseCartLineConnection!           # max 500 line items

  # Стоимость
  cost: CartCost!                          # totalAmount, subtotalAmount + currency

  # Идентификация покупателя
  buyerIdentity: CartBuyerIdentity!        # email, phone, country, preferences

  # Кастомные данные
  attributes: [Attribute!]!               # key-value пары (max 250)
  metafields: [Metafield]!               # типизированные кастомные поля (max 250)

  # Скидки и платежи
  discountCodes: [CartDiscountCode!]!     # Промокоды
  discountAllocations: [CartDiscountAllocation!]!
  appliedGiftCards: [AppliedGiftCard!]!

  # Доставка
  delivery: CartDelivery!
  deliveryGroups: CartDeliveryGroupConnection!  # до 20 адресов доставки
}
```

**Мутации корзины:**

| Мутация                    | Описание                              | Лимит         |
| -------------------------- | ------------------------------------- | ------------- |
| `cartCreate`               | Создать корзину с начальными товарами | —             |
| `cartLinesAdd`             | Добавить товары                       | 250 за запрос |
| `cartLinesUpdate`          | Обновить количество                   | 250 за запрос |
| `cartLinesRemove`          | Удалить товары                        | 250 за запрос |
| `cartBuyerIdentityUpdate`  | Привязка покупателя                   | —             |
| `cartDiscountCodesUpdate`  | Применить промокоды                   | —             |
| `cartGiftCardCodesUpdate`  | Применить подарочные карты            | —             |
| `cartAttributesUpdate`     | Обновить метаданные                   | 250 атрибутов |
| `cartNoteUpdate`           | Обновить заметку                      | —             |
| `cartMetafieldsSet`        | Кастомные метаполя                    | API v2023-04+ |
| `cartDeliveryAddressesAdd` | Добавить адрес доставки               | до 20 адресов |

**Безопасность Cart ID:**
```
Формат: <token>?key=<secret>

ВАЖНО: Секретная часть ID никогда не должна быть раскрыта.
Обращайтесь с ней как с паролем.
```

### 4.4 Технический стек

| Компонент     | Технология                    |
| ------------- | ----------------------------- |
| Backend       | Ruby on Rails + Puma          |
| Database      | MySQL + Vitess (шардирование) |
| Cache         | Memcached + Redis             |
| Events        | Kafka                         |
| Search        | Elasticsearch                 |
| Proxy         | Nginx + Lua                   |
| Orchestration | Kubernetes на Google Cloud    |
| Testing       | Toxiproxy (симуляция сбоев)   |

### 4.5 Resiliency паттерны

- **Toxiproxy:** TCP-прокси для симуляции сетевых условий в тестировании
- **Decorators вокруг data stores:** Автоматические fallback-механизмы
- **Canary deployment:** Изменения сначала на малый subset продакшена
- **Sub-100ms:** Время ответа для каждой операции с корзиной

---

## 5. Walmart

### 5.1 DDD и гексагональная архитектура

Walmart — единственная из исследованных платформ, которая публично и детально описала применение **Domain-Driven Design** и **Hexagonal Architecture** (Ports & Adapters) для сервиса корзины.

### 5.2 Bounded Contexts

```
┌───────────────────────────────────────────────────────────┐
│              Walmart Cart Bounded Contexts                │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐  Partnership   ┌─────────────┐           │
│  │   Cart      │◄──────────────►│   Pricing   │           │
│  │  Context    │  (Same team)   │   Context   │           │
│  │             │                │             │           │
│  │  Item ≠     │                │  Promotions │           │
│  │Catalog.Item │                │  Totals     │           │
│  └──────┬──────┘                └─────────────┘           │
│         │                                                 │
│         │ Customer-Supplier                               │
│         │ (ACL / Anti-Corruption Layer)                   │
│         ▼                                                 │
│  ┌─────────────┐                ┌─────────────┐           │
│  │  Catalog    │                │  Order      │           │
│  │  Context    │                │  Context    │           │
│  │             │  Conformist    │             │           │
│  │  (Другая    │◄───────────────│ (Подписка   │           │
│  │   команда)  │  (Events)      │  на события)│           │
│  └─────────────┘                └─────────────┘           │
└───────────────────────────────────────────────────────────┘
```

**Ключевой инсайт:** 4 разных bounded context участвуют в use case "добавить товар в корзину", и каждый контекст может принадлежать разной команде.

### 5.3 Гексагональная архитектура (Ports & Adapters)

```
┌────────────────────────────────────────────────────────────────┐
│                  Hexagonal Cart Architecture                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Primary Adapters          Core Domain     Secondary Adapters  │
│  (Driving)                                     (Driven)        │
│                                                                │
│  ┌────────────┐     ┌──────────────────┐   ┌────────────────┐  │
│  │ REST       │     │   Cart           │   │ CartRepository │  │
│  │ Controller │────>│   (Aggregate     │──>│ (DynamoDB/     │  │
│  │            │     │    Root)         │   │  MySQL)        │  │
│  ├────────────┤     │                  │   ├────────────────┤  │
│  │ gRPC       │     │ ┌──────────────┐ │   │ CatalogService │  │
│  │ Adapter    │────>│ │ CartItem     │ │──>│ Gateway        │  │
│  │            │     │ │ (Entity)     │ │   │ (Anti-         │  │
│  └────────────┘     │ └──────────────┘ │   │  Corruption    │  │
│                     │ ┌──────────────┐ │   │  Layer)        │  │
│  Command Objects    │ │ CartPrice    │ │   ├────────────────┤  │
│  ┌────────────┐     │ │ (Value Obj)  │ │   │ PriceCalc      │  │
│  │AddToCart   │     │ └──────────────┘ │   │ Gateway        │  │
│  │RemoveItem  │     │                  │   └────────────────┘  │
│  │UpdateQty   │     │ CartFactory      │                       │
│  └────────────┘     │ PriceDomainSvc   │                       │
│                     └──────────────────┘                       │
└────────────────────────────────────────────────────────────────┘
```

### 5.4 Доменная модель

**Cart (Aggregate Root):**
```
Cart {
  customerId: CustomerId
  items: List<CartItem>        // unmodifiable collection
  price: CartPrice
  status: CartStatus

  // Intention-revealing methods
  addItemToCart(item)          → validates MaxItemsLimit, QtyLimit
  removeItemFromCart(itemId)
  updateQuantity(itemId, qty)
  checkout()

  // Domain invariants
  validateMaxItemsLimit()
  isQtyWithinAllowedLimit()
}
```

**CartItem (Entity):**
```
CartItem {
  id: CartItemId              // уникальный идентификатор
  productId: ProductId
  variantId: VariantId
  quantity: Quantity
  catalogData: CatalogItem    // Value Object (из ACL)
  price: CartPrice            // Value Object
}
```

**Value Objects:**
```
CartPrice {                    // Immutable, validated
  amount: Decimal              // non-negative
  currency: Currency
}

CatalogItem {                  // From Anti-Corruption Layer
  name: String
  available: Boolean
  maxQuantity: Int
}
```

### 5.5 Пакетная структура

```
com.cart/
├── domain/
│   ├── Cart.java              (Aggregate Root)
│   ├── CartItem.java          (Entity)
│   ├── CartPrice.java         (Value Object)
│   ├── CatalogItem.java       (Value Object)
│   ├── ICartRepository.java   (Port — interface)
│   ├── CartFactory.java       (Complex creation)
│   └── PriceDomainService.java (Stateless domain logic)
├── application/
│   ├── CartApplicationService.java  (Use case orchestration)
│   └── commands/
│       ├── AddToCartCommand.java
│       ├── RemoveFromCartCommand.java
│       └── UpdateQuantityCommand.java
├── adapter/
│   ├── primary/
│   │   ├── CartController.java      (REST)
│   │   ├── CartRequest.java         (DTO — lives and dies here)
│   │   └── CartResponse.java        (DTO)
│   └── secondary/
│       ├── CartRepository.java       (Adapter impl)
│       ├── CatalogServiceGateway.java (ACL)
│       └── PriceCalculatorGateway.java
```

### 5.6 Ключевые принципы Walmart

1. **Non-Anemic Domain Models:** Модели содержат поведение, а не только getters/setters
2. **Ubiquitous Language:** "Item" в Cart Context ≠ "Item" в Catalog Context
3. **Anti-Corruption Layer:** Контракты внешних сервисов трансформируются в доменные Value Objects
4. **Unmodifiable Collections:** `getCartItems()` возвращает неизменяемый список
5. **Single Transaction Boundary:** Модификации агрегата сохраняются атомарно
6. **Command Pattern:** Внешние запросы преобразуются в domain-aware команды
7. **Dependency Inversion:** Application core не знает об имплементациях адаптеров

---

## 6. eBay

### 6.1 Архитектура платформы

eBay использует **3-tier stateless архитектуру**:

```
┌──────────────────────────────────────────────────────┐
│                  eBay Architecture                   │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Tier 1: Presentation                                │
│  ┌─────────────────────────────────────────┐         │
│  │  Browser / Mobile App                   │         │
│  └───────────────────┬─────────────────────┘         │
│                      │                               │
│  Tier 2: Application (15,000 серверов)               │
│  ┌─────────────────────────────────────────┐         │
│  │  ~100 функциональных групп              │         │
│  │  Java (J2EE + Servlets + JDBC)          │         │
│  │  WebSphere                              │         │
│  │  ПОЛНОСТЬЮ STATELESS                    │         │
│  │  (transient state → cookies/scratch DB) │         │
│  └───────────────────┬─────────────────────┘         │
│                      │                               │
│  Tier 3: Data Services                               │
│  ┌─────────────────────────────────────────┐         │
│  │  Oracle DB                              │         │
│  │  70+ функциональных инстансов           │         │
│  │  600+ production инстансов              │         │
│  │  100+ кластеров серверов                │         │
│  │  8 дата-центров                         │         │
│  │  3+ реплики на каждую БД                │         │
│  │  Lag: 15 мин — 4 часа                   │         │
│  └─────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────┘
```

### 6.2 Принципы масштабирования

eBay сформулировал набор практик, ставших каноническими:

| Принцип                               | Описание                                                            |
| ------------------------------------- | ------------------------------------------------------------------- |
| **Partition by Function**             | БД разделены функционально: accounts, items, feedback, transactions |
| **Split Horizontally**                | Данные внутри функции шардируются по ключу (modulo)                 |
| **Avoid Distributed Transactions**    | Нет распределённых транзакций — компромисс в пользу доступности     |
| **Decouple Functions Asynchronously** | Асинхронная связь между компонентами                                |
| **Move Processing Async**             | Вынос тяжёлых операций в асинхронные потоки                         |
| **Virtualize At All Levels**          | Виртуализация на всех уровнях                                       |
| **Cache Appropriately**               | Кэширование с учётом паттернов доступа                              |
| **No Stored Procedures**              | Процессинг на дешёвых app-серверах, а не на дорогих DB-серверах     |

### 6.3 Масштаб

- **26 миллиардов** SQL-запросов ежедневно
- **1 миллиард** просмотров страниц в день
- **100 миллионов** товаров
- **2 петабайта** данных
- **99.94%** доступность

### 6.4 Voyager — Real-Time Search

Собственная система реального времени для индексации товаров, которые меняют поисковые данные **5 раз до продажи**. Использует:
- Reliable multicast от primary DB к search-нодам
- In-memory search индексы
- Горизонтальную сегментацию: N slices × M instances

---

## 7. JD.com

### 7.1 Инфраструктура

JD.com — второй по величине e-commerce в Китае с уникальной моделью прямых поставок:

- **380+ миллионов** активных покупателей
- **90%** заказов доставляются в тот же или следующий день
- Собственная логистическая инфраструктура — крупнейшая в Китае для e-commerce

### 7.2 Контейнеризация

JD.com — один из крупнейших пользователей Kubernetes в мире:

```
┌──────────────────────────────────────────────┐
│           JD.com Infrastructure              │
├──────────────────────────────────────────────┤
│                                              │
│  ┌─────────────────┐                         │
│  │ Kubernetes      │  Все сервисы,           │
│  │ Platform        │  включая корзину,       │
│  │                 │  работают в             │
│  │ (Hyperscale     │  контейнерах            │
│  │  Containerized) │                         │
│  └────────┬────────┘                         │
│           │                                  │
│  ┌────────▼────────┐  ┌────────────────┐     │
│  │  Harbor         │  │  ChubaoFS      │     │
│  │  (Container     │  │  (Distributed  │     │
│  │   Registry)     │  │   File System) │     │
│  └─────────────────┘  └────────────────┘     │
│                                              │
│  Capabilities:                               │
│  - Full self-managed backend technology      │
│  - Supply chain management                   │
│  - Warehouse management                      │
│  - Transaction processing                    │
│  - Business intelligence                     │
└──────────────────────────────────────────────┘
```

### 7.3 ChubaoFS

Собственная open-source **распределённая файловая система** для cloud-native приложений:
- Масштабируемость
- Отказоустойчивое хранение
- Высокая производительность

---

## 8. Общие паттерны

### 8.1 Сравнительная таблица

| Характеристика      | Amazon                | Alibaba               | Shopify           | Walmart                | eBay             |
| ------------------- | --------------------- | --------------------- | ----------------- | ---------------------- | ---------------- |
| **Архитектура**     | Микросервисы          | Микросервисы (Dubbo3) | Модульный монолит | Микросервисы (DDD)     | 3-tier stateless |
| **Database**        | DynamoDB              | OceanBase + Tair      | MySQL + Vitess    | MySQL/NoSQL            | Oracle           |
| **Кэш**             | DAX (DynamoDB)        | Tair (Redis-like)     | Memcached + Redis | Redis                  | Custom           |
| **Шардирование**    | Consistent hashing    | User-based sharding   | shop_id pods      | —                      | Modulo on key    |
| **Консистентность** | Eventually Consistent | Strong (для корзины)  | Strong (per pod)  | Strong (per aggregate) | Lag-tolerant     |
| **API**             | REST                  | HSF/Dubbo3 RPC        | GraphQL           | REST/gRPC              | REST             |
| **TTL корзины**     | 1d/7d                 | Configurable          | Session-based     | —                      | Session-based    |
| **Максимум items**  | Unlimited (DDB)       | Configurable          | 500 line items    | Configurable           | —                |

### 8.2 Корзина как Bounded Context

Все исследованные платформы рассматривают корзину как **отдельный bounded context** в терминах DDD:

```
┌──────────────────────────────────────────────────────────┐
│              E-Commerce Bounded Contexts                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────┐ ┌───────────┐  ┌──────────┐  ┌─────────┐    │
│  │ Product │ │  Cart     │  │  Order   │  │ Payment │    │
│  │ Catalog │ │           │  │          │  │         │    │
│  │         │ │ Entities: │  │          │  │         │    │
│  │ Product │ │ Cart      │  │ Order    │  │ Payment │    │
│  │ Category│ │ CartItem  │  │ OrderItem│  │ Refund  │    │
│  │ Variant │ │ CartPrice │  │ Shipment │  │         │    │
│  └────┬────┘ └─────┬─────┘  └───┬──────┘  └────┬────┘    │
│       │            │            │              │         │
│       └────────────┴────────────┴──────────────┘         │
│                  Domain Events                           │
│       ItemAddedToCart, CartCheckedOut,                   │
│       OrderCreated, PaymentProcessed                     │
└──────────────────────────────────────────────────────────┘
```

**Ключевое наблюдение:** Один и тот же "товар" (Product/Item) имеет **разное представление** в каждом контексте:
- В **Catalog:** вес, срок годности, поставщик, полное описание
- В **Cart:** productId, quantity, price, variantId
- В **Order:** неизменяемый снимок (snapshot) на момент оформления

### 8.3 Универсальная доменная модель корзины

На основе анализа всех платформ, вот обобщённая доменная модель:

```
┌───────────────────────────────────────────────────┐
│                Cart (Aggregate Root)              │
├───────────────────────────────────────────────────┤
│                                                   │
│  id: CartId (UUID)                                │
│  customerId: CustomerId (nullable — для гостей)   │
│  sessionId: SessionId (UUID — для анонимных)      │
│  status: CartStatus (ACTIVE, MERGED, CHECKOUT,    │
│          ABANDONED, EXPIRED)                      │
│  items: List<CartItem>                            │
│  appliedDiscounts: List<Discount>                 │
│  note: String                                     │
│  createdAt: DateTime                              │
│  updatedAt: DateTime                              │
│  expiresAt: DateTime (TTL)                        │
│                                                   │
│  Methods:                                         │
│  + addItem(productId, variantId, qty)             │
│  + removeItem(itemId)                             │
│  + updateQuantity(itemId, qty)                    │
│  + applyDiscount(code)                            │
│  + merge(otherCart)                               │
│  + checkout()                                     │
│  + calculateTotals()                              │
│                                                   │
│  Invariants:                                      │
│  - maxItems <= 500 (Shopify) / configurable       │
│  - quantity > 0 && quantity <= maxPerItem         │
│  - status transitions are valid                   │
│                                                   │
├───────────────────────────────────────────────────┤
│               CartItem (Entity)                   │
├───────────────────────────────────────────────────┤
│  id: CartItemId                                   │
│  productId: ProductId                             │
│  variantId: VariantId                             │
│  sellerId: SellerId (для marketplace)             │
│  quantity: Quantity (Value Object)                │
│  unitPrice: Money (Value Object)                  │
│  totalPrice: Money (computed)                     │
│  attributes: Map<String, String>                  │
│  addedAt: DateTime                                │
│                                                   │
├───────────────────────────────────────────────────┤
│             Money (Value Object)                  │
├───────────────────────────────────────────────────┤
│  amount: Decimal (non-negative)                   │
│  currency: Currency (ISO 4217)                    │
└───────────────────────────────────────────────────┘
```

### 8.4 Доменные события

```
CartCreated            { cartId, customerId/sessionId, timestamp }
ItemAddedToCart         { cartId, itemId, productId, variantId, quantity, price }
ItemRemovedFromCart     { cartId, itemId }
ItemQuantityUpdated     { cartId, itemId, oldQty, newQty }
DiscountApplied         { cartId, discountCode, discountAmount }
CartMerged              { targetCartId, sourceCartId, mergedItems[] }
CartCheckedOut          { cartId, orderId, totalAmount }
CartAbandoned           { cartId, itemCount, totalValue }  // async event
CartExpired             { cartId }                          // TTL-triggered
```

---

## 9. Стратегии резервирования инвентаря

### 9.1 Три основных подхода

```
┌─────────────────────────────────────────────────────────────┐
│              Inventory Reservation Strategies               │
├─────────────┬───────────────────┬───────────────────────────┤
│  Optimistic │   Pessimistic     │   Soft Reservation        │
│  Locking    │   (Hard) Locking  │   (Hybrid)                │
├─────────────┼───────────────────┼───────────────────────────┤
│             │                   │                           │
│  Проверка   │  SELECT ... FOR   │  Создание "мягкой"        │
│  конфликта  │  UPDATE           │  резервации при           │
│  при записи │                   │  checkout с TTL           │
│  (version   │  Блокировка       │                           │
│  field)     │  строки на всё    │  Авто-освобождение        │
│             │  время            │  при timeout              │
│             │  транзакции       │                           │
│             │                   │  AvailableStock =         │
│  Retry      │  Bottleneck       │  TotalStock -             │
│  при        │  на популярных    │  ReservedStock            │
│  конфликте  │  товарах          │                           │
├─────────────┼───────────────────┼───────────────────────────┤
│ Подходит:   │ Подходит:         │ Подходит:                 │
│ Moderate    │ Flash sales,      │ Standard e-commerce,      │
│ contention  │ limited inventory │ cart → checkout flow      │
│ High read   │ Critical          │                           │
│ throughput  │ consistency       │                           │
└─────────────┴───────────────────┴───────────────────────────┘
```

### 9.2 Рекомендуемый гибридный подход

Большинство крупных платформ используют **гибридную стратегию:**

1. **При добавлении в корзину:** Никакого резервирования — только проверка наличия (read-only)
2. **При начале checkout:** Soft reservation с TTL (5-15 минут)
3. **При подтверждении оплаты:** Hard reservation (списание со склада)
4. **При timeout checkout:** Автоматическое освобождение soft reservation

```
Timeline:
  Add to Cart     Start Checkout    Payment OK      Timeout
      │                │                │               │
      ▼                ▼                ▼               ▼
  ┌────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐
  │No Lock │    │Soft Hold  │    │Hard Lock │    │Release    │
  │Check   │    │TTL=15min  │    │Committed │    │Rollback   │
  │avail   │    │Reserved=+1│    │Stock=-1  │    │Reserved=-1│
  └────────┘    └───────────┘    └──────────┘    └───────────┘
```

### 9.3 Redis для распределённой блокировки

Redis используется как промежуточный слой для:
- Кэширования уровня запасов
- Распределённой блокировки при конкурентном доступе к инвентарю
- Формула: `AvailableStock = TotalStock - ReservedStock`

---

## 10. Event Sourcing vs CRUD

### 10.1 Сравнение подходов

| Критерий                      | CRUD                  | Event Sourcing                 |
| ----------------------------- | --------------------- | ------------------------------ |
| **Сложность**                 | Низкая                | Высокая                        |
| **Производительность записи** | UPDATE (contention)   | APPEND (no contention)         |
| **Производительность чтения** | Прямой SELECT         | Replay/Projection              |
| **Аудит**                     | Дополнительная логика | Встроенный audit trail         |
| **Debugging**                 | Stack trace           | Replay exact event sequence    |
| **Масштабирование**           | Vertical primarily    | R/W scale independently        |
| **Порог входа**               | Низкий                | Высокий — steep learning curve |
| **Temporal queries**          | Сложно                | Нативно                        |

### 10.2 Event Sourcing для корзины: Реальная практика

**Типичные события корзины при ES:**
```
Stream: cart-{cartId}

1. CartCreated       { cartId, userId, timestamp }
2. ItemAdded         { cartId, productId, qty: 2, price: 100 }
3. ItemAdded         { cartId, productId2, qty: 1, price: 50 }
4. QuantityUpdated   { cartId, productId, oldQty: 2, newQty: 3 }
5. ItemRemoved       { cartId, productId2 }
6. DiscountApplied   { cartId, code: "SALE10", amount: 30 }
7. CartCheckedOut    { cartId, orderId, total: 270 }
```

**Восстановление состояния:**
```
Event 1: Cart = { items: [], total: 0 }
Event 2: Cart = { items: [{p1, qty:2, $100}], total: 200 }
Event 3: Cart = { items: [{p1, qty:2, $100}, {p2, qty:1, $50}], total: 250 }
Event 4: Cart = { items: [{p1, qty:3, $100}, {p2, qty:1, $50}], total: 350 }
Event 5: Cart = { items: [{p1, qty:3, $100}], total: 300 }
Event 6: Cart = { items: [{p1, qty:3, $100}], total: 270, discount: 30 }
```

### 10.3 Реальность production: Триада паттернов

Чистый Event Sourcing — скорее теоретический концепт. В production всегда используется триада:

1. **Event Sourcing** — write model (источник истины)
2. **Projections** — read models (оптимизированы для запросов)
3. **Snapshots** — оптимизация производительности write model

```
┌────────────────────────────────────────────────────────┐
│           Production Event Sourcing Triad              │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Command ──> Write Model ──> Event Store               │
│              (ES + Snapshots)    │                     │
│                                  │ Projection          │
│                                  ▼                     │
│  Query ───> Read Model ───> Materialized View          │
│             (Optimized for queries)                    │
│                                                        │
│  Snapshot каждые N событий (напр. каждые 100)          │
│  Projection обновляется асинхронно                     │
│  Read model eventually consistent                      │
└────────────────────────────────────────────────────────┘
```

### 10.4 Вердикт

**Для корзины покупок рекомендация: CRUD с доменными событиями**, а не полный Event Sourcing.

Причины:
- Корзина имеет **короткий жизненный цикл** (часы/дни, не годы)
- Количество событий на корзину **невелико** (5-50)
- Бизнес-требования к аудиту корзины **минимальны** (в отличие от заказов)
- Сложность ES не оправдана для данного домена
- **Доменные события** (ItemAddedToCart, etc.) достаточны для интеграции с другими bounded contexts

---

## 11. Управление сессиями и слияние корзин

### 11.1 Стратегия гостевых корзин

```
┌────────────────────────────────────────────────────────────┐
│          Guest vs Authenticated Cart Flow                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. Гость заходит на сайт                                  │
│     → Генерируется UUID cookie (session_id)                │
│     → Корзина привязывается к session_id                   │
│     → TTL = 1 день (Amazon) / 24 минуты (Magento default)  │
│                                                            │
│  2. Гость добавляет товары                                 │
│     → PK: SESSION#<uuid>, SK: ITEM#<sku>                   │
│                                                            │
│  3. Гость входит в аккаунт                                 │
│     → Запрос корзины по session_id                         │
│     → Миграция items к USER#<user_id>                      │
│     → Конфликт: СУММИРОВАНИЕ количества                    │
│     → Старые session items → SQS для async delete          │
│     → TTL корзины обновляется до 7 дней                    │
│                                                            │
│  4. Покупатель закрывает браузер и возвращается            │
│     → Корзина сохранена в DynamoDB                         │
│     → Персистентная корзина доступна только                │
│       для аутентифицированных пользователей                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 11.2 Алгоритм слияния (Cart Merge)

Реализация AWS Serverless Shopping Cart (эталонная):

```
merge(sessionCart, userCart):
  for each item in sessionCart:
    if item.productId exists in userCart:
      userCart.item.quantity += sessionCart.item.quantity   // СУММИРОВАНИЕ
    else:
      userCart.add(item)                                   // ПЕРЕНОС

  sessionCart.items → SQS queue for async deletion
  return userCart
```

**Amazon Dynamo подход (vector clocks):**
- При конфликте — **объединение** (union) содержимого обеих версий
- Удалённые товары могут "воскреснуть" — сознательный компромисс
- Философия: "лучше показать лишний товар, чем потерять добавленный"

### 11.3 Multi-device синхронизация

Для аутентифицированных пользователей все платформы обеспечивают синхронизацию корзины между устройствами через единый `user_id` как partition key. Корзина привязана к пользователю, а не к устройству/сессии.

---

## 12. Политики истечения и очистки корзин

### 12.1 TTL стратегии платформ

| Платформа            | Гостевая корзина    | Аутентифицированная | Механизм       |
| -------------------- | ------------------- | ------------------- | -------------- |
| **Amazon (AWS ref)** | 1 день              | 7 дней              | DynamoDB TTL   |
| **Magento**          | 24 минуты (session) | 30 дней (quotes)    | Cron job       |
| **WooCommerce**      | 48 часов            | Persistent          | Session expiry |
| **Shopify**          | Session-based       | Persistent          | Per-pod TTL    |

### 12.2 Row-Level TTL (CockroachDB подход)

Современные базы данных поддерживают row-level TTL для автоматической очистки:

```sql
-- Создание таблицы с TTL
CREATE TABLE cart_items (
  id UUID PRIMARY KEY,
  product_id UUID REFERENCES products(id),
  user_id UUID REFERENCES users(id),
  quantity INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expired_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '15 minutes'
);

-- Активация TTL
ALTER TABLE cart_items SET (
  ttl_expiration_expression = 'expired_at',
  ttl_job_cron = '*/5 * * * *'  -- проверка каждые 5 минут
);

-- ВАЖНО: Фильтрация в запросах
SELECT * FROM cart_items
WHERE user_id = $1 AND expired_at > NOW();
```

### 12.3 Статистика брошенных корзин

- **70.19%** — средний показатель abandonment rate (2025)
- **79.97%** — на мобильных устройствах
- **48%** покупателей бросают корзину из-за неожиданных расходов
- **18%** — из-за сложного процесса checkout
- Оптимальный checkout: **12-14 элементов формы** (7-8 полей)

### 12.4 Рекомендуемая стратегия очистки

```
┌────────────────────────────────────────────────────────┐
│            Cart Lifecycle Management                   │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ACTIVE ──(15min idle)──> IDLE                         │
│    │                        │                          │
│    │                        │──(2-4 hours)──> EMAIL_1  │
│    │                        │──(24 hours)───> EMAIL_2  │
│    │                        │──(72 hours)───> EMAIL_3  │
│    │                        │                          │
│    │──(checkout)──> CHECKOUT│──(30 days)────> EXPIRED  │
│    │               │                                   │
│    │               │──(payment)──> COMPLETED           │
│    │               │──(timeout)──> ACTIVE (restore)    │
│    │                                                   │
│    │──(merge)──> MERGED (soft delete)                  │
│                                                        │
│  Cleanup cron: daily                                   │
│  - Delete EXPIRED carts                                │
│  - Archive cart data for analytics (optional)          │
│  - Release any stale soft reservations                 │
└────────────────────────────────────────────────────────┘
```

---

## 13. Мультиселлерная корзина

### 13.1 Архитектура (Marketplace Model)

Для маркетплейсов (Taobao, eBay, Amazon Marketplace) корзина должна поддерживать товары от разных продавцов:

```
┌──────────────────────────────────────────────────────────┐
│           Multi-Seller Cart Architecture                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Cart (Aggregate)                                        │
│  ├── CartItem (Seller A)                                 │
│  │   ├── Product 1, qty: 2                               │
│  │   └── Product 2, qty: 1                               │
│  ├── CartItem (Seller B)                                 │
│  │   └── Product 3, qty: 3                               │
│  └── CartItem (Seller C)                                 │
│      └── Product 4, qty: 1                               │
│                                                          │
│  При checkout → Split на sub-orders per seller:          │
│                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ Sub-Order A  │ │ Sub-Order B  │ │ Sub-Order C  │      │
│  │ Seller A     │ │ Seller B     │ │ Seller C     │      │
│  │ Items: 1, 2  │ │ Items: 3     │ │ Items: 4     │      │
│  │ Shipping: $5 │ │ Shipping: $3 │ │ Shipping: $7 │      │
│  │ Tax: $2      │ │ Tax: $1      │ │ Tax: $1.5    │      │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘      │
│         │                │                │              │
│         ▼                ▼                ▼              │
│  ┌──────────────────────────────────────────────┐        │
│  │           Payment Processing                 │        │
│  │  Stripe Connect / Mangopay                   │        │
│  │  Split payments per seller                   │        │
│  │  Commission deduction                        │        │
│  └──────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────┘
```

### 13.2 Ключевые вызовы мультиселлерной корзины

| Вызов                    | Решение                                             |
| ------------------------ | --------------------------------------------------- |
| **Раздельная доставка**  | Расчёт shipping per seller, группировка по складам  |
| **Разные ставки налога** | Tax calculation engine с учётом seller jurisdiction |
| **Комиссии**             | Настраиваемые commission structures per seller      |
| **Валюты**               | Currency conversion для кросс-бордерных продаж      |
| **Промокоды**            | Seller-specific vs platform-wide промокоды          |
| **Возвраты**             | Per-seller return policies                          |
| **Split payments**       | Stripe Connect, Mangopay для автоматического split  |

### 13.3 Модель данных для мультиселлерной корзины

```
Cart {
  id: CartId
  customerId: CustomerId
  items: List<CartItem>

  // Группировка по продавцам
  getItemsBySeller(): Map<SellerId, List<CartItem>>

  // Расчёт по группам
  getSubtotalBySeller(): Map<SellerId, Money>
  getShippingBySeller(): Map<SellerId, Money>
  getTotalBySeller(): Map<SellerId, Money>

  // Общие итоги
  getGrandTotal(): Money
}

CartItem {
  id: CartItemId
  sellerId: SellerId           // ← ключевое поле для marketplace
  productId: ProductId
  variantId: VariantId
  quantity: Quantity
  unitPrice: Money
  shippingMethod: ShippingMethod
  deliveryEstimate: DateRange
}
```

---

## 14. Рекомендации

### 14.1 Для нашего проекта (Loyalty Platform)

На основании проведённого исследования, для нашей loyalty-платформы рекомендуются следующие архитектурные решения:

#### Уровень 1: Data Model

```
┌─────────────────────────────────────────────────────┐
│          Рекомендуемая архитектура корзины          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Подход: CRUD с доменными событиями                 │
│  Стиль: DDD (по примеру Walmart)                    │
│  Хранение: PostgreSQL + Redis кэш                   │
│  API: REST (FastAPI)                                │
│                                                     │
│  Cart (Aggregate Root)                              │
│  ├── id: UUID (PK)                                  │
│  ├── customer_id: UUID (FK, nullable)               │
│  ├── session_id: UUID (for guests)                  │
│  ├── status: CartStatus enum                        │
│  ├── expires_at: timestamp with TTL                 │
│  ├── created_at: timestamp                          │
│  ├── updated_at: timestamp                          │
│  │                                                  │
│  └── items: List<CartItem>                          │
│      ├── id: UUID (PK)                              │
│      ├── cart_id: UUID (FK)                         │
│      ├── product_id: UUID (FK)                      │
│      ├── variant_id: UUID (FK)                      │
│      ├── seller_id: UUID (FK) — если marketplace    │
│      ├── quantity: int (> 0)                        │
│      ├── unit_price: decimal                        │
│      ├── added_at: timestamp                        │
│      └── metadata: jsonb                            │
│                                                     │
│  Индексы:                                           │
│  - cart: (customer_id) — быстрый поиск по клиенту   │
│  - cart: (session_id) — поиск гостевой корзины      │
│  - cart: (expires_at) — для cleanup job             │
│  - cart_item: (cart_id, product_id) — уникальность  │
└─────────────────────────────────────────────────────┘
```

#### Уровень 2: Кэширование

```
Стратегия: Cache-Aside (Lazy Loading)

Read:
  1. Проверить Redis (key: cart:{cart_id})
  2. Cache miss → Загрузить из PostgreSQL
  3. Записать в Redis с TTL

Write:
  1. Обновить PostgreSQL (source of truth)
  2. Инвалидировать Redis cache
  3. Публиковать domain event

TTL в Redis: 1 час (auto-refresh при активности)
```

#### Уровень 3: API Design

```
REST API Endpoints:

GET    /api/v1/carts/current           → Получить текущую корзину
POST   /api/v1/carts                    → Создать корзину
POST   /api/v1/carts/{id}/items         → Добавить товар
PUT    /api/v1/carts/{id}/items/{itemId} → Обновить количество
DELETE /api/v1/carts/{id}/items/{itemId} → Удалить товар
POST   /api/v1/carts/{id}/merge         → Слить гостевую с аутентифицированной
POST   /api/v1/carts/{id}/checkout      → Начать checkout
DELETE /api/v1/carts/{id}               → Очистить корзину
```

#### Уровень 4: Domain Events

```
События для интеграции с другими bounded contexts:

CartCreated         → Analytics
ItemAddedToCart      → Recommendations, Analytics
ItemRemovedFromCart   → Analytics
CartCheckedOut       → Order Service, Inventory Service
CartAbandoned        → Notification Service (email recovery)
```

### 14.2 Паттерны для реализации (приоритет)

| #   | Паттерн                               | Приоритет       | Источник            |
| --- | ------------------------------------- | --------------- | ------------------- |
| 1   | Cart как Aggregate Root (DDD)         | **Критический** | Walmart             |
| 2   | Guest → Auth cart merge               | **Высокий**     | Amazon AWS ref      |
| 3   | TTL-based expiration                  | **Высокий**     | Amazon, CockroachDB |
| 4   | Cache-aside с Redis                   | **Высокий**     | Alibaba (Tair)      |
| 5   | Soft reservation при checkout         | **Средний**     | Industry standard   |
| 6   | Domain events для интеграции          | **Средний**     | Walmart, Shopify    |
| 7   | Anti-Corruption Layer для Catalog     | **Средний**     | Walmart             |
| 8   | Multi-seller split (если marketplace) | **Низкий**      | Taobao, eBay        |

---

## 15. Источники

### Официальные публикации и инженерные блоги

1. [Amazon's Dynamo — All Things Distributed (Werner Vogels, 2007)](https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html)
2. [Dynamo: Amazon's Highly Available Key-value Store — Cornell Paper](https://www.cs.cornell.edu/courses/cs5414/2017fa/papers/dynamo.pdf)
3. [How Amazon Scaled E-commerce Shopping Cart Data Infrastructure](https://newsletter.systemdesign.one/p/amazon-dynamo-architecture)
4. [A Deep Dive into Amazon DynamoDB Architecture — ByteByteGo](https://blog.bytebytego.com/p/a-deep-dive-into-amazon-dynamodb)
5. [Eventually Consistent — Werner Vogels (ACM Queue)](https://queue.acm.org/detail.cfm?id=1466448)

### Walmart

6. [Implementing Cart Microservice using DDD and Port/Adapter — Part 1](https://medium.com/walmartglobaltech/implementing-cart-service-with-ddd-hexagonal-port-adapter-architecture-part-1-4dab93b3fa9f)
7. [Implementing Cart Microservice using DDD and Port/Adapter — Part 2](https://medium.com/walmartglobaltech/implementing-cart-service-with-ddd-hexagonal-port-adapter-architecture-part-2-d9c00e290ab)
8. [Event Sourcing Design Pattern — Walmart Global Tech Blog](https://medium.com/walmartglobaltech/event-sourcing-design-pattern-a0d99ecd60cd)

### Shopify

9. [Shopify Storefront API — Cart Object](https://shopify.dev/docs/api/storefront/latest/objects/Cart)
10. [Create and Update a Cart with the Storefront API](https://shopify.dev/docs/storefronts/headless/building-with-the-storefront-api/cart/manage)
11. [Inside Shopify's Modular Monolith — Oleksiy Kovyrin](https://kovyrin.net/2024/06/16/interview-inside-shopify-monolith/)
12. [Under Deconstruction: The State of Shopify's Monolith](https://shopify.engineering/shopify-monolith)
13. [Horizontally Scaling the Rails Backend with Vitess](https://shopify.engineering/horizontally-scaling-the-rails-backend-of-shop-app-with-vitess)
14. [Building and Testing Resilient Ruby on Rails Applications](https://shopify.engineering/building-and-testing-resilient-ruby-on-rails-applications)
15. [Shopify Tech Stack — ByteByteGo](https://blog.bytebytego.com/p/shopify-tech-stack)
16. [Shopify's Modular Monolithic Architecture: A Deep Dive](https://mehmetozkaya.medium.com/shopifys-modular-monolithic-architecture-a-deep-dive-%EF%B8%8F-a2f88c172797)

### Alibaba / Taobao

17. [10 Years of Double 11: Evolution of Alibaba's Cloudification Architecture](https://www.alibabacloud.com/blog/594160)
18. [Capacity Planning for Alibaba's Double 11 Shopping Festival](https://www.alibabacloud.com/blog/capacity-planning-for-alibabas-double-11-shopping-festival_594164)
19. [Storing and Managing Taobao's Trillions of Orders](https://www.alibabacloud.com/blog/storing-and-managing-taobaos-trillions-of-orders_596766)
20. [Alibaba Upgrades Dubbo3 to Fully Replace HSF2](https://dubbo.apache.org/en/blog/2023/01/16/alibaba-upgrades-dubbo3-to-fully-replace-hsf2/)
21. [Tair — Alibaba Cloud](https://www.alibabacloud.com/en/product/tair)
22. [OceanBase — Distributed Database](https://en.oceanbase.com/)
23. [Fight Peak Data Traffic on 11.11: Secrets of Alibaba Stream Computing](https://102.alibaba.com/detail?id=35)

### eBay

24. [eBay Architecture — High Scalability](https://highscalability.com/ebay-architecture/)
25. [Scalability Best Practices: Lessons from eBay — InfoQ](https://www.infoq.com/articles/ebay-scalability-best-practices/)
26. [Managing Complex Dependencies with Distributed Architecture at eBay — InfoQ](https://www.infoq.com/news/2022/04/distributed-arch-ebay/)

### Миграции и case studies

27. [How Zalando Migrated Their Shopping Carts to DynamoDB from Cassandra](https://aws.amazon.com/blogs/database/how-zalando-migrated-their-shopping-carts-to-amazon-dynamodb-from-apache-cassandra/)
28. [How ZOZOTOWN Migrated Shopping Cart to DynamoDB](https://aws.amazon.com/blogs/database/how-amazon-dynamodb-supported-zozotowns-shopping-cart-migration-project/)
29. [AWS Serverless Shopping Cart — GitHub](https://github.com/aws-samples/aws-serverless-shopping-cart)

### Общие паттерны и System Design

30. [Scalable E-Commerce Architecture Part 2: Shopping Cart](https://dev.to/savyjs/scalable-e-commerce-architecture-part-2-shopping-cart-3blg)
31. [Shopping Cart Database Design for E-Commerce](https://dev.to/fabric_commerce/how-do-you-design-a-shopping-cart-database-for-e-commerce-4oeh)
32. [Building Reliable Shopping Carts: An Engineering Story](https://medium.com/@amrendravimal/building-reliable-shopping-carts-an-engineering-story-eb9a5d31f8e1)
33. [Inventory Reservation Patterns: How to Stop Overselling](https://stoalogistics.com/blog/inventory-reservation-patterns)
34. [Solving Abandoned Cart Problem with Row-Level TTL — CockroachDB](https://www.cockroachlabs.com/blog/abandoned-cart-problem/)
35. [Event Sourcing Explained: Pros, Cons & Strategic Use Cases](https://www.baytechconsulting.com/blog/event-sourcing-explained-2025)
36. [Cart Abandonment Rate Statistics 2026 — Baymard Institute](https://baymard.com/lists/cart-abandonment-rate)

### Патенты

37. [US7640193B2 — Distributed Electronic Commerce System with Centralized Virtual Shopping Carts](https://patents.google.com/patent/US7640193B2/en)
38. [US8190493B2 — Shopping Cart Service System and Method](https://patents.google.com/patent/US8190493)

### Multi-Vendor / Marketplace

39. [How to Build a Multi-Vendor Shopping Cart — Sharetribe](https://www.sharetribe.com/academy/multivendor-shopping-cart/)
40. [How to Build a Multi-Vendor Shopping Cart — Nautical Commerce](https://www.nauticalcommerce.com/blog/multi-vendor-shopping-cart)

---

*Документ подготовлен на основании анализа публичных инженерных блогов, научных статей, патентных заявок и open-source реализаций. Все данные актуальны на март 2026 года.*
