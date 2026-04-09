# Управление состоянием и архитектура данных в Next.js App Router (2025-2026)

> **Контекст проекта:** Frontend-only Next.js приложение, часть большой системы с отдельными
> бэкенд-сервисами. Next.js выступает как BFF (Backend for Frontend) / proxy-слой.
> ORM, прямая работа с БД и серверная бизнес-логика — на стороне бэкенд-сервисов.
>
> Полное исследование: RSC-паттерны, TanStack Query v5, Zustand/Jotai, React Hook Form + Zod,
> Server Actions (как proxy к бэкенду), многоуровневое кэширование, real-time данные
> и рекомендуемый enterprise-стек для Next.js 15+ App Router.

---

## Содержание

### Часть 1 — RSC и серверное состояние (TanStack Query v5)

1. [Server Components vs Client Components](#1-server-components-vs-client-components)
2. [Паттерны композиции RSC](#2-паттерны-композиции-rsc)
3. [Streaming и Suspense](#3-streaming-и-suspense)
4. [React.use() и серверные промисы](#4-reactuse-и-серверные-промисы)
5. [TanStack Query v5: полная настройка](#5-tanstack-query-v5-полная-настройка-для-nextjs-app-router)
6. [Query Key Factory](#6-query-key-factory)
7. [Prefetch-паттерны](#7-prefetch-паттерны)
8. [Optimistic Updates](#8-optimistic-updates)
9. [Infinite Scroll и курсорная пагинация](#9-infinite-scroll-и-курсорная-пагинация)
10. [Обработка ошибок с TanStack Query](#10-обработка-ошибок)
11. [~~TanStack Query vs SWR~~](#11-tanstack-query-vs-swr) _(сокращено)_

### Часть 2 — Управление клиентским состоянием

- [3.1 Архитектура состояния: что куда помещать](#31-архитектура-состояния-что-куда-помещать)
- [3.2 Zustand v5: детальные паттерны](#32-zustand-v5-детальные-паттерны)
- [3.3 Jotai v2: атомарный подход](#33-jotai-v2-атомарный-подход)
- [~~3.4 Миграция с Redux на Zustand~~](#34-миграция-с-redux-на-zustand) _(не актуально — greenfield)_
- [3.5 Тестирование store (Vitest)](#35-тестирование-store-vitest)
- [3.6 Антипаттерны и частые ошибки](#36-антипаттерны-и-частые-ошибки)
- [3.7 Итоговые рекомендации](#37-итоговые-рекомендации)

### Часть 3 — Формы, валидация и API-слой

- [4.1 React Hook Form: продвинутые паттерны](#41-react-hook-form-продвинутые-паттерны)
- [4.2 Продвинутые Zod-паттерны](#42-продвинутые-zod-паттерны)
- [4.3 Conform.js: серверно-ориентированные формы](#43-conformjs-серверно-ориентированные-формы)
- [5.1 API-клиент: продвинутая конфигурация](#51-api-клиент-продвинутая-конфигурация)
- [5.2 Централизованная обработка ошибок](#52-централизованная-обработка-ошибок)
- [5.3 File Upload с прогрессом](#53-file-upload-с-прогрессом)

### Часть 4 — Server Actions и кэширование

- [6.1 Server Actions: архитектура безопасности (DAL)](#61-server-actions-архитектура-безопасности)
- [6.2 React 19: useActionState](#62-react-19-useactionstate)
- [6.3 useOptimistic (React 19)](#63-useoptimistic-react-19)
- [6.4 Rate Limiting Server Actions](#64-rate-limiting-server-actions)
- [7.1 Next.js 15: изменения в кэшировании](#71-nextjs-15-изменения-в-кэшировании)
- [7.2 Tag-based кэш инвалидация](#72-tag-based-кэш-инвалидация)
- [7.3 unstable_cache vs fetch cache](#73-unstable_cache-vs-fetch-cache)
- [7.4 Многоуровневый кэш: полная картина](#74-многоуровневый-кэш-полная-картина)
- [7.5 Стратегия для enterprise](#75-стратегия-для-enterprise)

### Часть 5 — Real-time данные и рекомендуемый стек

- [8.1 Сравнение подходов real-time](#81-сравнение-подходов)
- [8.2 SSE с переподключением](#82-sse-с-автоматическим-переподключением-и-типами-событий)
- [8.3 WebSocket (Socket.IO + Next.js)](#83-websocket-интеграция-socketio--nextjs)
- [~~8.4 PartyKit для совместной работы~~](#84-partykit-для-совместной-работы) _(вне роадмапа)_
- [~~8.5 AI-стриминг (Vercel AI SDK)~~](#85-ai-стриминг-vercel-ai-sdk--readablestream) _(вне роадмапа)_
- [8.6 Управляемые сервисы: Pusher vs Ably vs Soketi](#86-управляемые-real-time-сервисы-pusher-vs-ably-vs-soketi)
- [8.7 Оптимизация поллинга](#87-оптимизация-поллинга-адаптивный-exponential-backoff)
- [8.8 Optimistic Updates для real-time](#88-optimistic-updates-для-real-time-ощущения)
- [8.9 Стоимостной анализ real-time сервисов](#89-стоимостной-анализ-real-time-сервисов)
- [8.10 Пути миграции между технологиями](#810-пути-миграции-между-технологиями)
- [9.1 Дерево решений по state management](#91-дерево-решений-по-state-management)
- [9.2 Полная enterprise-архитектура](#92-полная-enterprise-архитектура)
- [9.3 Финальный стек с альтернативами](#93-финальный-стек-с-альтернативами)
- [9.4 Мониторинг производительности](#94-мониторинг-производительности) _(см. отдельные документы)_
- [9.5 Архитектура проекта](#95-архитектура-проекта)

---

## 1. Server Components vs Client Components

### Полная таблица сравнения

| Критерий                                   | Server Component       | Client Component (`'use client'`) |
| ------------------------------------------ | ---------------------- | --------------------------------- |
| **Fetch данных**                           | Напрямую (async/await) | Через хуки (useQuery, useSWR)     |
| **Доступ к БД / файлам / secrets**         | Да (прямой)            | Нет (только через API)            |
| **Интерактивность (onClick, onChange)**    | Нет                    | Да                                |
| **React hooks (useState, useEffect)**      | Нет                    | Да                                |
| **Browser API (localStorage, геолокация)** | Нет                    | Да                                |
| **JS отправляется клиенту**                | 0 KB (только HTML)     | Да (полный JS bundle)             |
| **Streaming / Suspense**                   | Полная поддержка       | Частично (через Suspense)         |
| **SEO**                                    | Полный HTML на сервере | Требует SSR/гидрации              |
| **Первоначальная загрузка (TTFB)**         | Быстрая                | Зависит от bundle size            |
| **React.use()**                            | Не нужен (async/await) | Да (для promise-пропсов)          |
| **По умолчанию в Next.js 15**              | Да                     | Требует директиву `'use client'`  |

### Ментальная модель: где проходит граница

В Next.js 15 **каждый компонент является Server Component по умолчанию**. Директива `'use client'` создаёт **client boundary** — границу, ниже которой все компоненты становятся клиентскими.

```
Серверная территория (по умолчанию)
│
├── layout.tsx          ← Server Component
├── page.tsx            ← Server Component
│   ├── Header.tsx      ← Server Component
│   ├── Sidebar.tsx     ← Server Component
│   └── Dashboard.tsx   ← 'use client' ← CLIENT BOUNDARY
│       ├── Chart.tsx   ← Client Component (неявно!)
│       └── Filter.tsx  ← Client Component (неявно!)
```

**Критически важно:** когда вы ставите `'use client'`, **все дочерние импорты** этого модуля тоже становятся клиентскими. Это не ошибка — это механизм работы module graph. Именно поэтому нужно сдвигать `'use client'` как можно ниже в дереве компонентов.

### Правило: "Leaves First"

Клиентские компоненты должны быть **листьями** дерева компонентов, а не корнями. Это минимизирует объём JavaScript, отправляемого в браузер.

```typescript
// BAD: 'use client' на верхнем уровне — весь поддерев становится клиентским
// app/dashboard/page.tsx
'use client'; // Делает ВСЕ дочерние компоненты клиентскими

export default function DashboardPage() {
  const [tab, setTab] = useState('overview');
  return (
    <div>
      <HeavyDataTable />     {/* Мог бы быть Server Component, но теперь клиентский */}
      <StaticSidebar />      {/* Тоже стал клиентским без причины */}
      <TabSelector tab={tab} onSelect={setTab} />
    </div>
  );
}
```

```typescript
// GOOD: 'use client' только на интерактивном компоненте
// app/dashboard/page.tsx — Server Component (по умолчанию)
import { HeavyDataTable } from '@/components/heavy-data-table';    // Server
import { StaticSidebar } from '@/components/static-sidebar';        // Server
import { TabSelector } from '@/components/tab-selector';            // Client

export default async function DashboardPage() {
  const data = await fetchDashboardData(); // Прямой fetch на сервере
  return (
    <div>
      <HeavyDataTable data={data} />
      <StaticSidebar />
      <TabSelector />  {/* Только этот компонент — 'use client' */}
    </div>
  );
}
```

---

## 2. Паттерны композиции RSC

### 2.1 Donut Pattern (паттерн "пончика")

**Проблема:** клиентский компонент не может импортировать серверный компонент напрямую (ограничение module graph). Но что если нужна клиентская обёртка вокруг серверного контента?

**Решение:** передать серверный компонент через `children` или другие пропсы.

Метафора "пончика": клиентский компонент — это тесто (обёртка с интерактивностью), а дырка в середине — серверный контент, переданный через `children`.

```typescript
// components/modal.tsx — Клиентский "пончик" (обёртка)
'use client';

import { useState, type ReactNode } from 'react';

interface ModalProps {
  trigger: ReactNode;
  children: ReactNode;  // <-- "дырка" для серверного контента
}

export function Modal({ trigger, children }: ModalProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div onClick={() => setIsOpen(true)}>{trigger}</div>
      {isOpen && (
        <div className="modal-overlay" onClick={() => setIsOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            {children}  {/* Серверный контент рендерится здесь */}
          </div>
        </div>
      )}
    </>
  );
}
```

```typescript
// app/products/page.tsx — Server Component
import { Modal } from '@/components/modal';
import { ProductDetails } from '@/components/product-details'; // Server Component

export default async function ProductsPage() {
  const products = await api.get<Product[]>('/products');

  return (
    <ul>
      {products.map((product) => (
        <li key={product.id}>
          <Modal trigger={<button>View {product.name}</button>}>
            {/* Server Component внутри Client Component через children */}
            <ProductDetails productId={product.id} />
          </Modal>
        </li>
      ))}
    </ul>
  );
}
```

```typescript
// components/product-details.tsx — Server Component (без 'use client')
interface ProductDetailsProps {
  productId: string;
}

export async function ProductDetails({ productId }: ProductDetailsProps) {
  // Запрос к бэкенд-сервису — Server Component может делать fetch напрямую
  const product = await api.get<Product>(`/products/${productId}`);

  return (
    <div>
      <h2>{product.name}</h2>
      <p>{product.description}</p>
      <p>Reviews: {product.reviews.length}</p>
    </div>
  );
}
```

### 2.2 Slot Pattern (паттерн слотов)

Расширение donut pattern: вместо одного `children` используется несколько именованных слотов.

```typescript
// components/dashboard-layout.tsx
'use client';

import { useState, type ReactNode } from 'react';

interface DashboardLayoutProps {
  sidebar: ReactNode;    // Слот для серверного сайдбара
  header: ReactNode;     // Слот для серверного хедера
  children: ReactNode;   // Слот для основного контента
}

export function DashboardLayout({ sidebar, header, children }: DashboardLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div className="flex">
      {isSidebarOpen && <aside className="w-64">{sidebar}</aside>}
      <div className="flex-1">
        <nav className="flex items-center justify-between p-4">
          {header}
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
            Toggle Sidebar
          </button>
        </nav>
        <main className="p-4">{children}</main>
      </div>
    </div>
  );
}
```

```typescript
// app/dashboard/page.tsx — Server Component
import { DashboardLayout } from '@/components/dashboard-layout';
import { ServerSidebar } from '@/components/server-sidebar';
import { ServerHeader } from '@/components/server-header';
import { ServerMetrics } from '@/components/server-metrics';

export default async function DashboardPage() {
  return (
    <DashboardLayout
      sidebar={<ServerSidebar />}    {/* Server Component в слоте */}
      header={<ServerHeader />}      {/* Server Component в слоте */}
    >
      <ServerMetrics />              {/* Server Component в children */}
    </DashboardLayout>
  );
}
```

### 2.3 Паттерн: серверный контейнер + клиентский презентер

Разделение ответственностей: серверный компонент загружает данные, клиентский отображает с интерактивностью.

```typescript
// app/analytics/page.tsx — Server Component (контейнер)
import { AnalyticsChart } from '@/components/analytics-chart';

export default async function AnalyticsPage() {
  // Все данные загружаются на сервере — 0 KB JS для этой логики
  const [revenue, users, orders] = await Promise.all([
    fetchRevenue(),
    fetchActiveUsers(),
    fetchOrders({ last: 30 }),
  ]);

  return (
    <section>
      <h1>Analytics</h1>
      {/* Клиентский компонент получает готовые данные */}
      <AnalyticsChart
        revenue={revenue}
        users={users}
        orders={orders}
      />
    </section>
  );
}
```

```typescript
// components/analytics-chart.tsx — Client Component (презентер)
'use client';

import { useState } from 'react';

interface AnalyticsChartProps {
  revenue: number[];
  users: number[];
  orders: { date: string; count: number }[];
}

export function AnalyticsChart({ revenue, users, orders }: AnalyticsChartProps) {
  const [metric, setMetric] = useState<'revenue' | 'users' | 'orders'>('revenue');
  const [dateRange, setDateRange] = useState<'7d' | '30d'>('30d');

  // Интерактивная фильтрация на клиенте без дополнительных запросов
  const filteredOrders = dateRange === '7d' ? orders.slice(-7) : orders;

  return (
    <div>
      <div className="flex gap-2">
        <button onClick={() => setMetric('revenue')}>Revenue</button>
        <button onClick={() => setMetric('users')}>Users</button>
        <button onClick={() => setMetric('orders')}>Orders</button>
      </div>
      {/* Рендер графика с выбранной метрикой */}
    </div>
  );
}
```

---

## 3. Streaming и Suspense

### 3.1 Проблема водопадов (Waterfalls)

Последовательные запросы создают "водопад" — каждый следующий запрос ждёт завершения предыдущего:

```typescript
// BAD: Waterfall — каждый await блокирует следующий
export default async function DashboardPage() {
  const user = await fetchUser();           // 200ms
  const orders = await fetchOrders();       // 300ms
  const notifications = await fetchNotifications(); // 150ms
  // Итого: 650ms (последовательно)

  return <Dashboard user={user} orders={orders} notifications={notifications} />;
}
```

### 3.2 Параллельная загрузка с Promise.all

```typescript
// BETTER: Параллельный fetch — но весь контент ждёт самый медленный запрос
export default async function DashboardPage() {
  const [user, orders, notifications] = await Promise.all([
    fetchUser(),           // 200ms ─┐
    fetchOrders(),         // 300ms ─┤ параллельно
    fetchNotifications(),  // 150ms ─┘
  ]);
  // Итого: 300ms (время самого медленного)

  return <Dashboard user={user} orders={orders} notifications={notifications} />;
}
```

### 3.3 Множественные Suspense Boundaries (лучший подход)

Каждая секция загружается независимо, контент появляется по мере готовности:

```typescript
// BEST: Независимые Suspense Boundaries — каждая секция грузится и отображается отдельно
import { Suspense } from 'react';

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Хедер появляется через 200ms */}
      <Suspense fallback={<UserHeaderSkeleton />}>
        <UserHeader />
      </Suspense>

      {/* Заказы появляются через 300ms (независимо от хедера) */}
      <Suspense fallback={<OrdersTableSkeleton />}>
        <OrdersTable />
      </Suspense>

      {/* Уведомления появляются через 150ms (первыми!) */}
      <Suspense fallback={<NotificationsSkeleton />}>
        <NotificationsFeed />
      </Suspense>
    </div>
  );
}

// Каждый компонент загружает данные самостоятельно
async function UserHeader() {
  const user = await fetchUser(); // 200ms
  return <header><h1>Welcome, {user.name}</h1></header>;
}

async function OrdersTable() {
  const orders = await fetchOrders(); // 300ms
  return (
    <table>
      {orders.map((order) => (
        <tr key={order.id}><td>{order.title}</td></tr>
      ))}
    </table>
  );
}

async function NotificationsFeed() {
  const notifications = await fetchNotifications(); // 150ms
  return (
    <ul>
      {notifications.map((n) => (
        <li key={n.id}>{n.message}</li>
      ))}
    </ul>
  );
}
```

**Механизм:** когда React встречает Suspense boundary с pending-данными, он приостанавливает этот компонент и продолжает рендерить остальные части страницы. Сервер стримит HTML-чанки по мере их готовности — это и есть **streaming SSR**.

### 3.4 Вложенные Suspense Boundaries (приоритизация)

Для критичных и некритичных секций используются вложенные границы:

```typescript
import { Suspense } from 'react';

export default function ProductPage({ params }: { params: { id: string } }) {
  return (
    <div>
      {/* Критичный контент — показывается первым */}
      <Suspense fallback={<ProductInfoSkeleton />}>
        <ProductInfo id={params.id} />

        {/* Менее критичный — загружается после основной информации */}
        <Suspense fallback={<ReviewsSkeleton />}>
          <ProductReviews productId={params.id} />
        </Suspense>
      </Suspense>

      {/* Полностью независимая секция */}
      <Suspense fallback={<RecommendationsSkeleton />}>
        <Recommendations productId={params.id} />
      </Suspense>
    </div>
  );
}
```

### 3.5 Partial Prerendering (PPR) — Next.js 15

PPR позволяет **статически отрендерить оболочку страницы** при билде, а динамические части стримить при запросе:

```typescript
// next.config.ts
import type { NextConfig } from 'next';

const config: NextConfig = {
  experimental: {
    ppr: true, // Включение Partial Prerendering
  },
};

export default config;
```

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react';
import { StaticNav } from '@/components/static-nav';   // Статика — рендерится при билде

export default function DashboardPage() {
  return (
    <div>
      {/* Статическая оболочка — мгновенно из CDN */}
      <StaticNav />
      <h1>Dashboard</h1>

      {/* Динамический контент — стримится при запросе */}
      <Suspense fallback={<MetricsSkeleton />}>
        <DynamicMetrics />  {/* async fetch внутри */}
      </Suspense>
    </div>
  );
}
```

---

## 4. React.use() и серверные промисы

### Паттерн: инициация fetch на сервере, чтение на клиенте

`React.use()` позволяет передать **незавершённый промис** из Server Component в Client Component — данные стримятся по мере готовности:

```typescript
// app/users/page.tsx — Server Component
import { UserList } from '@/components/user-list';

export default function UsersPage() {
  // Промис создаётся, но НЕ ожидается (нет await)
  const usersPromise = fetchUsers();

  return (
    <Suspense fallback={<UserListSkeleton />}>
      {/* Передаём промис как проп */}
      <UserList usersPromise={usersPromise} />
    </Suspense>
  );
}
```

```typescript
// components/user-list.tsx — Client Component
'use client';

import { use } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
}

interface UserListProps {
  usersPromise: Promise<User[]>;
}

export function UserList({ usersPromise }: UserListProps) {
  // React.use() подписывается на промис и интегрируется с Suspense
  const users = use(usersPromise);

  return (
    <ul>
      {users.map((user) => (
        <li key={user.id}>
          {user.name} — {user.email}
        </li>
      ))}
    </ul>
  );
}
```

**Когда использовать `use()` vs `async/await`:**

| Сценарий                                            | Подход                    |
| --------------------------------------------------- | ------------------------- |
| Server Component загружает данные для себя          | `async/await`             |
| Server Component передаёт данные в Client Component | `use()` через промис-проп |
| Client Component с Suspense                         | `use()`                   |
| Чтение контекста в любом компоненте                 | `use(Context)`            |

**Ключевое отличие:** `async/await` продолжает рендеринг с точки вызова `await`, а `use()` **перерендеривает** компонент полностью после разрешения промиса.

---

## 5. TanStack Query v5: полная настройка для Next.js App Router

### 5.1 QueryClient Factory с поддержкой SSR

```typescript
// lib/query-client.ts
import { QueryClient, defaultShouldDehydrateQuery, isServer } from '@tanstack/react-query';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // На сервере: данные всегда свежие (нет смысла refetch)
        // На клиенте: 60 секунд — данные считаются свежими
        staleTime: 60 * 1000,
        // Время жизни неиспользуемого кэша — 5 минут
        gcTime: 5 * 60 * 1000,
        // 2 попытки при ошибке (не для 4xx ошибок)
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status < 500) return false;
          return failureCount < 2;
        },
        // Отключаем refetch при фокусе на окно — для enterprise это чаще мешает
        refetchOnWindowFocus: false,
      },
      dehydrate: {
        // Дегидратация pending-запросов для streaming
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) || query.state.status === 'pending',
      },
    },
  });
}

// Singleton на клиенте, новый инстанс на каждый серверный запрос
let browserQueryClient: QueryClient | undefined = undefined;

export function getQueryClient() {
  if (isServer) {
    // Сервер: всегда новый клиент (запросы не должны протекать между пользователями)
    return makeQueryClient();
  }
  // Браузер: singleton для сохранения кэша между навигациями
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}
```

### 5.2 Provider с DevTools

```typescript
// app/providers.tsx
'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { getQueryClient } from '@/lib/query-client';
import type { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  // getQueryClient() вернёт singleton в браузере
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
      )}
    </QueryClientProvider>
  );
}
```

### 5.3 Root Layout

```typescript
// app/layout.tsx — Server Component
import { Providers } from './providers';
import type { ReactNode } from 'react';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### 5.4 Experimental: Streaming без ручного prefetch

```typescript
// app/providers.tsx — альтернативный вариант с автоматическим streaming
'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryStreamedHydration } from '@tanstack/react-query-next-experimental';
import { getQueryClient } from '@/lib/query-client';
import type { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {/* Автоматический streaming: useSuspenseQuery работает без prefetch */}
      <ReactQueryStreamedHydration>
        {children}
      </ReactQueryStreamedHydration>
    </QueryClientProvider>
  );
}
```

**Компромисс:** `ReactQueryStreamedHydration` избавляет от ручного prefetch, но может ухудшить TTFB (Time to First Byte), так как HTML не отправляется до разрешения данных без Suspense boundary. Рекомендуется для проектов, где скорость итерации важнее максимальной производительности.

---

## 6. Query Key Factory

### 6.1 Ручная реализация (рекомендуемый подход)

Иерархическая структура: от общего к конкретному, с типобезопасностью.

```typescript
// lib/query-keys.ts

export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: { role?: string; status?: string }) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
  profile: (id: string) => [...userKeys.detail(id), 'profile'] as const,
  settings: (id: string) => [...userKeys.detail(id), 'settings'] as const,
} as const;

export const productKeys = {
  all: ['products'] as const,
  lists: () => [...productKeys.all, 'list'] as const,
  list: (filters: { category?: string; minPrice?: number; maxPrice?: number }) =>
    [...productKeys.lists(), filters] as const,
  details: () => [...productKeys.all, 'detail'] as const,
  detail: (id: string) => [...productKeys.details(), id] as const,
  reviews: (productId: string) => [...productKeys.detail(productId), 'reviews'] as const,
  infinite: (filters: { category?: string }) => [...productKeys.all, 'infinite', filters] as const,
} as const;

export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (filters: { status?: string; dateFrom?: string }) =>
    [...orderKeys.lists(), filters] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
} as const;
```

**Почему иерархия важна:** `invalidateQueries` поддерживает fuzzy matching. Инвалидация `userKeys.all` инвалидирует **все** запросы пользователей (списки, детали, профили). Инвалидация `userKeys.lists()` — только списки, не затрагивая детальные запросы.

```typescript
// Примеры инвалидации с разной гранулярностью
const queryClient = useQueryClient();

// Инвалидировать ВСЕ данные пользователей
queryClient.invalidateQueries({ queryKey: userKeys.all });

// Инвалидировать только списки пользователей
queryClient.invalidateQueries({ queryKey: userKeys.lists() });

// Инвалидировать конкретного пользователя
queryClient.invalidateQueries({ queryKey: userKeys.detail('user-123') });

// Инвалидировать все списки с конкретным фильтром
queryClient.invalidateQueries({
  queryKey: userKeys.list({ role: 'admin' }),
});
```

### 6.2 Библиотека @lukemorales/query-key-factory

Для крупных проектов можно использовать библиотеку с встроенной типобезопасностью и поддержкой queryFn:

```typescript
// lib/query-keys.ts
import { createQueryKeyStore } from '@lukemorales/query-key-factory';
import { api } from '@/lib/api-client';

export const queries = createQueryKeyStore({
  users: {
    all: null,
    detail: (userId: string) => ({
      queryKey: [userId],
      queryFn: () => api.get<User>(`/users/${userId}`),
    }),
    list: (filters: UserFilters) => ({
      queryKey: [{ filters }],
      queryFn: () => api.get<User[]>('/users', { params: filters }),
    }),
  },
  products: {
    all: null,
    detail: (productId: string) => ({
      queryKey: [productId],
      queryFn: () => api.get<Product>(`/products/${productId}`),
    }),
    list: (filters: ProductFilters) => ({
      queryKey: [{ filters }],
      queryFn: (ctx) =>
        api.get<PaginatedResponse<Product>>('/products', {
          params: { ...filters, cursor: ctx.pageParam },
        }),
    }),
  },
});

// Использование: queries.users.detail('123').queryKey -> ['users', 'detail', '123']
```

**Рекомендация:** для проектов до 20 сущностей — ручная реализация (нулевой overhead, полный контроль). Для 20+ — `@lukemorales/query-key-factory` ради consistency.

---

## 7. Prefetch-паттерны

### 7.1 prefetchQuery vs ensureQueryData

| Характеристика                 | `prefetchQuery`                               | `ensureQueryData`                    |
| ------------------------------ | --------------------------------------------- | ------------------------------------ |
| **Возвращает**                 | `Promise<void>`                               | `Promise<TData>`                     |
| **Бросает ошибки**             | Нет (глотает)                                 | Да                                   |
| **Рекомендация для RSC**       | Да (основной подход)                          | Осторожно                            |
| **Поведение при stale данных** | Всегда перезапрашивает (если staleTime истёк) | Возвращает из кэша, если данные есть |
| **Блокирует рендер**           | Нет (фоновый fetch)                           | Да (ждёт данные)                     |

### 7.2 prefetchQuery в Server Component (рекомендуемый)

```typescript
// app/products/page.tsx — Server Component
import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/query-client';
import { productKeys } from '@/lib/query-keys';
import { ProductList } from '@/components/product-list';

export default async function ProductsPage() {
  const queryClient = getQueryClient();

  // prefetchQuery — не возвращает данные, не бросает ошибки
  // Это правильно: Server Component не должен использовать данные напрямую
  await queryClient.prefetchQuery({
    queryKey: productKeys.list({}),
    queryFn: () => api.get<Product[]>('/products'),
  });

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ProductList />
    </HydrationBoundary>
  );
}
```

```typescript
// components/product-list.tsx — Client Component
'use client';

import { useQuery } from '@tanstack/react-query';
import { productKeys } from '@/lib/query-keys';

export function ProductList() {
  const { data: products, isLoading, error } = useQuery({
    queryKey: productKeys.list({}),
    queryFn: () => api.get<Product[]>('/products'),
  });

  if (isLoading) return <ProductListSkeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <ul>
      {products?.map((p) => (
        <li key={p.id}>{p.name} — ${p.price}</li>
      ))}
    </ul>
  );
}
```

### 7.3 Параллельный prefetch нескольких запросов

```typescript
// app/dashboard/page.tsx — Server Component
import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/query-client';

export default async function DashboardPage() {
  const queryClient = getQueryClient();

  // Параллельный prefetch — все запросы стартуют одновременно
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: userKeys.profile('current'),
      queryFn: () => api.get('/users/me'),
    }),
    queryClient.prefetchQuery({
      queryKey: orderKeys.list({ status: 'pending' }),
      queryFn: () => api.get('/orders', { params: { status: 'pending' } }),
    }),
    queryClient.prefetchQuery({
      queryKey: ['notifications', 'unread'],
      queryFn: () => api.get('/notifications/unread'),
    }),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <DashboardContent />
    </HydrationBoundary>
  );
}
```

### 7.4 ensureQueryData — когда серверу нужны данные

```typescript
// app/users/[id]/page.tsx — Server Component
import { getQueryClient } from '@/lib/query-client';

export default async function UserPage({ params }: { params: { id: string } }) {
  const queryClient = getQueryClient();

  // ensureQueryData — ВОЗВРАЩАЕТ данные, нужен когда
  // серверу необходимо использовать данные (например, для metadata)
  const user = await queryClient.ensureQueryData({
    queryKey: userKeys.detail(params.id),
    queryFn: () => api.get<User>(`/users/${params.id}`),
  });

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {/* Используем данные на сервере для SEO */}
      <h1>{user.name}</h1>
      <UserProfileClient userId={params.id} />
    </HydrationBoundary>
  );
}

// generateMetadata тоже может использовать ensureQueryData
export async function generateMetadata({ params }: { params: { id: string } }) {
  const queryClient = getQueryClient();
  const user = await queryClient.ensureQueryData({
    queryKey: userKeys.detail(params.id),
    queryFn: () => api.get<User>(`/users/${params.id}`),
  });

  return { title: `${user.name} — Profile` };
}
```

**Итог:** используйте `prefetchQuery` по умолчанию. `ensureQueryData` — только когда серверу нужно работать с данными (metadata, условный рендеринг).

---

## 8. Optimistic Updates

### 8.1 Cache-Level Optimism (основной enterprise-паттерн)

Обновление кэша TanStack Query до ответа сервера с автоматическим откатом при ошибке:

```typescript
// hooks/use-update-todo.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

interface UpdateTodoInput {
  id: string;
  title?: string;
  completed?: boolean;
}

export function useUpdateTodo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UpdateTodoInput) => api.patch<Todo>(`/todos/${input.id}`, input),

    // 1. Вызывается ДО mutationFn
    onMutate: async (newTodo) => {
      // Отменяем исходящие refetch-запросы, чтобы они не перезаписали оптимистичное обновление
      await queryClient.cancelQueries({ queryKey: ['todos', 'list'] });

      // Сохраняем снимок текущего состояния для отката
      const previousTodos = queryClient.getQueryData<Todo[]>(['todos', 'list']);

      // Оптимистично обновляем кэш
      queryClient.setQueryData<Todo[]>(['todos', 'list'], (old) =>
        old?.map((todo) => (todo.id === newTodo.id ? { ...todo, ...newTodo } : todo)),
      );

      // Возвращаем контекст для отката в onError
      return { previousTodos };
    },

    // 2. Вызывается при ОШИБКЕ — откат к предыдущему состоянию
    onError: (_error, _newTodo, context) => {
      if (context?.previousTodos) {
        queryClient.setQueryData(['todos', 'list'], context.previousTodos);
      }
    },

    // 3. Вызывается ВСЕГДА (успех или ошибка) — синхронизация с сервером
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['todos', 'list'] });
    },
  });
}
```

### 8.2 Оптимистичное добавление в список

```typescript
// hooks/use-create-todo.ts
export function useCreateTodo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { title: string }) => api.post<Todo>('/todos', input),

    onMutate: async (newTodoInput) => {
      await queryClient.cancelQueries({ queryKey: ['todos', 'list'] });

      const previousTodos = queryClient.getQueryData<Todo[]>(['todos', 'list']);

      // Создаём временный объект с фейковым ID
      const optimisticTodo: Todo = {
        id: `temp-${Date.now()}`,
        title: newTodoInput.title,
        completed: false,
      };

      queryClient.setQueryData<Todo[]>(['todos', 'list'], (old) =>
        old ? [optimisticTodo, ...old] : [optimisticTodo],
      );

      return { previousTodos };
    },

    onError: (_error, _input, context) => {
      if (context?.previousTodos) {
        queryClient.setQueryData(['todos', 'list'], context.previousTodos);
      }
    },

    onSettled: () => {
      // После успеха или ошибки — синхронизация с сервером
      // Фейковый ID будет заменён реальным
      queryClient.invalidateQueries({ queryKey: ['todos', 'list'] });
    },
  });
}
```

### 8.3 Оптимистичное удаление

```typescript
// hooks/use-delete-todo.ts
export function useDeleteTodo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (todoId: string) => api.delete(`/todos/${todoId}`),

    onMutate: async (todoId) => {
      await queryClient.cancelQueries({ queryKey: ['todos', 'list'] });
      const previousTodos = queryClient.getQueryData<Todo[]>(['todos', 'list']);

      // Оптимистично убираем элемент из списка
      queryClient.setQueryData<Todo[]>(['todos', 'list'], (old) =>
        old?.filter((todo) => todo.id !== todoId),
      );

      return { previousTodos };
    },

    onError: (_error, _todoId, context) => {
      if (context?.previousTodos) {
        queryClient.setQueryData(['todos', 'list'], context.previousTodos);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['todos', 'list'] });
    },
  });
}
```

### 8.4 UI-Level Optimism (упрощённый паттерн)

Для простых случаев, когда не нужно обновлять глобальный кэш — через `useMutation.variables`:

```typescript
// components/todo-item.tsx
'use client';

import { useUpdateTodo } from '@/hooks/use-update-todo';

export function TodoItem({ todo }: { todo: Todo }) {
  const updateTodo = useUpdateTodo();

  // Используем variables мутации как оптимистичное состояние UI
  const isOptimisticCompleted =
    updateTodo.isPending && updateTodo.variables?.id === todo.id
      ? updateTodo.variables.completed
      : todo.completed;

  return (
    <li style={{ opacity: updateTodo.isPending ? 0.7 : 1 }}>
      <input
        type="checkbox"
        checked={isOptimisticCompleted ?? todo.completed}
        onChange={() =>
          updateTodo.mutate({ id: todo.id, completed: !todo.completed })
        }
      />
      {todo.title}
    </li>
  );
}
```

---

## 9. Infinite Scroll и курсорная пагинация

### 9.1 Типы и API-контракт

```typescript
// types/pagination.ts
interface CursorPaginatedResponse<T> {
  data: T[];
  nextCursor: string | null; // null = последняя страница
  prevCursor: string | null;
  total: number;
}

interface Product {
  id: string;
  name: string;
  price: number;
  category: string;
  createdAt: string;
}
```

### 9.2 Hook с useInfiniteQuery

```typescript
// hooks/use-infinite-products.ts
import { useInfiniteQuery } from '@tanstack/react-query';
import { productKeys } from '@/lib/query-keys';
import { api } from '@/lib/api-client';

interface UseInfiniteProductsOptions {
  category?: string;
  limit?: number;
}

export function useInfiniteProducts(options: UseInfiniteProductsOptions = {}) {
  const { category, limit = 20 } = options;

  return useInfiniteQuery({
    queryKey: productKeys.infinite({ category }),
    queryFn: async ({ pageParam }): Promise<CursorPaginatedResponse<Product>> => {
      return api.get('/products', {
        params: {
          cursor: pageParam,
          limit,
          ...(category && { category }),
        },
      });
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    getPreviousPageParam: (firstPage) => firstPage.prevCursor,
  });
}
```

### 9.3 Компонент бесконечного скролла

```typescript
// components/infinite-product-list.tsx
'use client';

import { useInfiniteProducts } from '@/hooks/use-infinite-products';
import { useInView } from 'react-intersection-observer';
import { useEffect } from 'react';

interface InfiniteProductListProps {
  category?: string;
}

export function InfiniteProductList({ category }: InfiniteProductListProps) {
  const {
    data,
    error,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
    status,
  } = useInfiniteProducts({ category });

  // Intersection Observer — автозагрузка при скролле
  const { ref: loadMoreRef, inView } = useInView({ threshold: 0 });

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (status === 'pending') {
    return <ProductGridSkeleton />;
  }

  if (status === 'error') {
    return <ErrorMessage error={error} />;
  }

  // Объединяем все страницы в плоский массив
  const allProducts = data.pages.flatMap((page) => page.data);
  const totalCount = data.pages[0]?.total ?? 0;

  return (
    <div>
      <p className="text-sm text-gray-500">
        Показано {allProducts.length} из {totalCount}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {allProducts.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>

      {/* Триггер для Intersection Observer */}
      <div ref={loadMoreRef} className="h-10">
        {isFetchingNextPage && <LoadingSpinner />}
        {!hasNextPage && allProducts.length > 0 && (
          <p className="text-center text-gray-400">All products loaded</p>
        )}
      </div>

      {/* Фоновый индикатор обновления (при refetch) */}
      {isFetching && !isFetchingNextPage && (
        <div className="fixed bottom-4 right-4">
          <span className="text-sm">Updating...</span>
        </div>
      )}
    </div>
  );
}
```

### 9.4 Prefetch infinite query на сервере

```typescript
// app/products/page.tsx — Server Component
import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/query-client';
import { productKeys } from '@/lib/query-keys';
import { InfiniteProductList } from '@/components/infinite-product-list';

export default async function ProductsPage() {
  const queryClient = getQueryClient();

  // Prefetch первой страницы infinite query
  await queryClient.prefetchInfiniteQuery({
    queryKey: productKeys.infinite({}),
    queryFn: () => api.get('/products', { params: { limit: 20 } }),
    initialPageParam: null as string | null,
  });

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <h1>Products</h1>
      <InfiniteProductList />
    </HydrationBoundary>
  );
}
```

---

## 10. Обработка ошибок

### 10.1 Глобальный обработчик ошибок

```typescript
// lib/query-client.ts — расширенная версия с обработкой ошибок
import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { toast } from 'sonner';

function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        // Показываем toast только для запросов с данными в кэше
        // (т.е. когда пользователь уже видел данные, но refetch упал)
        if (query.state.data !== undefined) {
          toast.error(`Background update failed: ${error.message}`);
        }
      },
    }),
    mutationCache: new MutationCache({
      onError: (error) => {
        // Глобальный обработчик ошибок мутаций
        if (error instanceof ApiError) {
          switch (error.status) {
            case 401:
              toast.error('Session expired. Please log in again.');
              // redirect to login
              break;
            case 403:
              toast.error('You do not have permission for this action.');
              break;
            case 429:
              toast.error('Too many requests. Please try again later.');
              break;
            default:
              toast.error(`Error: ${error.message}`);
          }
        }
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        gcTime: 5 * 60 * 1000,
        retry: (failureCount, error) => {
          // Не повторяем клиентские ошибки (4xx)
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
            return false;
          }
          return failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
      },
    },
  });
}
```

### 10.2 QueryErrorResetBoundary + React Error Boundary

```typescript
// components/query-error-boundary.tsx
'use client';

import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { ErrorBoundary, type FallbackProps } from 'react-error-boundary';
import type { ReactNode } from 'react';

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6">
      <h3 className="text-lg font-semibold text-red-800">Something went wrong</h3>
      <p className="mt-2 text-sm text-red-600">{error.message}</p>
      <button
        onClick={resetErrorBoundary}
        className="mt-4 rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
      >
        Try again
      </button>
    </div>
  );
}

export function QueryErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary onReset={reset} FallbackComponent={ErrorFallback}>
          {children}
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}
```

```typescript
// Использование — оборачиваем компоненты с useSuspenseQuery
import { Suspense } from 'react';
import { QueryErrorBoundary } from '@/components/query-error-boundary';

export default function ProductsPage() {
  return (
    <QueryErrorBoundary>
      <Suspense fallback={<ProductListSkeleton />}>
        <ProductList />
      </Suspense>
    </QueryErrorBoundary>
  );
}
```

### 10.3 Retry с учётом типа ошибки

```typescript
// hooks/use-products.ts — retry только для серверных ошибок
export function useProducts(filters: ProductFilters) {
  return useQuery({
    queryKey: productKeys.list(filters),
    queryFn: () => api.get<Product[]>('/products', { params: filters }),
    retry: (failureCount, error) => {
      // 404 — ресурс не найден, retry бессмысленно
      if (error instanceof ApiError && error.status === 404) return false;
      // 401/403 — авторизация, retry бессмысленно
      if (error instanceof ApiError && error.status === 401) return false;
      if (error instanceof ApiError && error.status === 403) return false;
      // 429 — rate limit, retry с задержкой (до 3 раз)
      if (error instanceof ApiError && error.status === 429) return failureCount < 3;
      // 5xx — серверные ошибки, retry до 2 раз
      return failureCount < 2;
    },
    retryDelay: (attemptIndex, error) => {
      // Если сервер отдал Retry-After, используем его
      if (error instanceof ApiError && error.retryAfter) {
        return error.retryAfter * 1000;
      }
      // Иначе — exponential backoff
      return Math.min(1000 * 2 ** attemptIndex, 30000);
    },
  });
}
```

---

## 11. TanStack Query vs SWR

TanStack Query v5 — выбранное решение для серверного состояния. SWR не рассматривается.

---

## Архитектура файлов для enterprise-проекта

```
src/
├── app/
│   ├── layout.tsx                # Server Component — root layout
│   ├── providers.tsx             # 'use client' — QueryClientProvider
│   ├── (dashboard)/
│   │   ├── page.tsx              # Server Component — prefetch + HydrationBoundary
│   │   └── loading.tsx           # Suspense fallback для streaming
│   └── products/
│       ├── page.tsx              # Server Component — prefetchInfiniteQuery
│       └── [id]/
│           └── page.tsx          # Server Component — ensureQueryData + metadata
├── components/
│   ├── query-error-boundary.tsx  # QueryErrorResetBoundary обёртка
│   ├── product-list.tsx          # 'use client' — useQuery
│   ├── infinite-product-list.tsx # 'use client' — useInfiniteQuery
│   └── modal.tsx                 # 'use client' — donut pattern
├── hooks/
│   ├── use-products.ts           # useQuery + useMutation хуки
│   ├── use-infinite-products.ts  # useInfiniteQuery хук
│   └── use-update-todo.ts       # useMutation + optimistic update
├── lib/
│   ├── query-client.ts           # getQueryClient() singleton/factory
│   ├── query-keys.ts             # Query key factory (иерархия)
│   └── api-client.ts             # HTTP-клиент (ky / ofetch)
└── types/
    └── pagination.ts             # CursorPaginatedResponse<T>
```

---

## Источники

- [Next.js Docs: Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [Next.js Docs: Composition Patterns](https://nextjs.org/docs/14/app/building-your-application/rendering/composition-patterns)
- [Delicious Donut Components — Frontend at Scale](https://frontendatscale.com/blog/donut-components/)
- [Making Sense of React Server Components — Josh W. Comeau](https://www.joshwcomeau.com/react/server-components/)
- [React.dev: use() API](https://react.dev/reference/react/use)
- [React.dev: Suspense](https://react.dev/reference/react/Suspense)
- [React.dev: Server Components](https://react.dev/reference/rsc/server-components)
- [TanStack Query v5: Advanced Server Rendering](https://tanstack.com/query/v5/docs/react/guides/advanced-ssr)
- [TanStack Query v5: SSR & Hydration](https://tanstack.com/query/v5/docs/framework/react/guides/ssr)
- [TanStack Query v5: Prefetching](https://tanstack.com/query/v5/docs/react/guides/prefetching)
- [TanStack Query v5: Optimistic Updates](https://tanstack.com/query/v5/docs/react/guides/optimistic-updates)
- [TanStack Query v5: Infinite Queries](https://tanstack.com/query/v5/docs/framework/react/guides/infinite-queries)
- [TanStack Query v5: Suspense](https://tanstack.com/query/latest/docs/framework/react/guides/suspense)
- [TanStack Query v5: Comparison](https://tanstack.com/query/latest/docs/framework/react/comparison)
- [Effective React Query Keys — TkDodo](https://tkdodo.eu/blog/effective-react-query-keys)
- [GitHub: @lukemorales/query-key-factory](https://github.com/lukemorales/query-key-factory)
- [TanStack Query vs SWR vs Apollo Client 2026 — PkgPulse](https://www.pkgpulse.com/blog/tanstack-query-vs-swr-vs-apollo-2026)
- [React Query vs SWR 2025 Performance Comparison — MarkAICode](https://markaicode.com/react-query-vs-swr-2025-performance-comparison/)
- [Data Fetching in 2025: Streaming, Suspense, Deferred — Medium](https://medium.com/better-dev-nextjs-react/data-fetching-in-2025-streaming-suspense-and-deferred-fetching-in-next-js-app-router-d0658f2d835d)
- [Next.js 15 Streaming Handbook — FreeCodeCamp](https://www.freecodecamp.org/news/the-nextjs-15-streaming-handbook/)
- [Next.js Partial Prerendering](https://nextjs.org/docs/15/app/getting-started/partial-prerendering)
- [9 React 19 Suspense Patterns That Reduce Waterfalls — Medium](https://medium.com/@sparknp1/9-react-19-suspense-patterns-that-reduce-waterfalls-d1449512887c)

---

---

# Часть 2 — Управление клиентским состоянием

> Расширенный анализ Zustand v5, Jotai v2, Redux Toolkit и паттернов enterprise state management.

---

## 3.1 Архитектура состояния: что куда помещать

```
┌─────────────────────────────────────────────────────────┐
│                    Типы состояния                       │
├──────────────────┬──────────────────────────────────────┤
│ URL State        │ searchParams, pathname               │
│                  │ → useSearchParams, usePathname       │
├──────────────────┼──────────────────────────────────────┤
│ Server Cache     │ Данные с API/БД                      │
│                  │ → TanStack Query, SWR, RSC fetch     │
├──────────────────┼──────────────────────────────────────┤
│ Global UI State  │ Theme, sidebar, modals, toasts       │
│                  │ → Zustand                            │
├──────────────────┼──────────────────────────────────────┤
│ Local UI State   │ Form inputs, toggles, hover          │
│                  │ → useState, useReducer               │
├──────────────────┼──────────────────────────────────────┤
│ Form State       │ Поля, валидация, dirty/touched       │
│                  │ → React Hook Form + Zod              │
├──────────────────┼──────────────────────────────────────┤
│ Persisted State  │ Настройки, preferences               │
│                  │ → Zustand persist middleware         │
└──────────────────┴──────────────────────────────────────┘
```

**Правило:** если данные приходят с сервера — это **не** клиентское состояние. Не дублируйте серверные данные в Zustand/Redux. Используйте TanStack Query как кэш серверных данных.

---

## 3.2 Zustand v5: детальные паттерны

### Базовый store

```typescript
// stores/ui-store.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  locale: string;
}

interface UIActions {
  toggleSidebar: () => void;
  setTheme: (theme: UIState['theme']) => void;
  setLocale: (locale: string) => void;
}

export const useUIStore = create<UIState & UIActions>()(
  devtools(
    persist(
      (set) => ({
        // State
        sidebarOpen: true,
        theme: 'system',
        locale: 'ru',

        // Actions
        toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
        setTheme: (theme) => set({ theme }),
        setLocale: (locale) => set({ locale }),
      }),
      { name: 'ui-store' },
    ),
    { name: 'UIStore' },
  ),
);
```

### Slices Pattern для больших store

Разделение store на независимые "слайсы" для масштабируемости:

```typescript
// stores/slices/auth-slice.ts
import type { StateCreator } from 'zustand';

export interface AuthSlice {
  user: { id: string; email: string; role: string } | null;
  token: string | null;
  login: (user: AuthSlice['user'], token: string) => void;
  logout: () => void;
}

export const createAuthSlice: StateCreator<
  AuthSlice & UISlice, // все слайсы для cross-slice доступа
  [],
  [],
  AuthSlice
> = (set) => ({
  user: null,
  token: null,
  login: (user, token) => set({ user, token }),
  logout: () => set({ user: null, token: null }),
});

// stores/slices/ui-slice.ts
export interface UISlice {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const createUISlice: StateCreator<AuthSlice & UISlice, [], [], UISlice> = (set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
});

// stores/app-store.ts — сборка
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { createAuthSlice, type AuthSlice } from './slices/auth-slice';
import { createUISlice, type UISlice } from './slices/ui-slice';

type AppStore = AuthSlice & UISlice;

export const useAppStore = create<AppStore>()(
  devtools((...a) => ({
    ...createAuthSlice(...a),
    ...createUISlice(...a),
  })),
);
```

### createSelectors — авто-генерация селекторов

```typescript
// lib/create-selectors.ts
import type { StoreApi, UseBoundStore } from 'zustand';

type WithSelectors<S> = S extends { getState: () => infer T }
  ? S & { use: { [K in keyof T]: () => T[K] } }
  : never;

export function createSelectors<S extends UseBoundStore<StoreApi<object>>>(_store: S) {
  const store = _store as WithSelectors<typeof _store>;
  store.use = {};
  for (const k of Object.keys(store.getState())) {
    (store.use as Record<string, unknown>)[k] = () => store((s) => s[k as keyof typeof s]);
  }
  return store;
}

// Использование:
import { createSelectors } from '@/lib/create-selectors';

export const useUIStore = createSelectors(useUIStoreBase);

// В компоненте — автоматический селектор, минимум ре-рендеров:
const theme = useUIStore.use.theme();
const sidebarOpen = useUIStore.use.sidebarOpen();
```

### Zustand + Immer для иммутабельных обновлений

```typescript
// stores/cart-store.ts
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartState {
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'quantity'>) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
  total: () => number;
}

export const useCartStore = create<CartState>()(
  immer((set, get) => ({
    items: [],

    addItem: (item) =>
      set((state) => {
        const existing = state.items.find((i) => i.id === item.id);
        if (existing) {
          existing.quantity += 1;
        } else {
          state.items.push({ ...item, quantity: 1 });
        }
      }),

    removeItem: (id) =>
      set((state) => {
        state.items = state.items.filter((i) => i.id !== id);
      }),

    updateQuantity: (id, quantity) =>
      set((state) => {
        const item = state.items.find((i) => i.id === id);
        if (item) item.quantity = Math.max(0, quantity);
      }),

    clearCart: () => set({ items: [] }),

    total: () => get().items.reduce((sum, item) => sum + item.price * item.quantity, 0),
  })),
);
```

### Zustand + Next.js: SSR-safe гидратация

Проблема: Zustand persist читает из localStorage, что вызывает hydration mismatch.

```typescript
// hooks/use-store-hydration.ts
import { useEffect, useState } from 'react';

export function useStoreHydration() {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  return hydrated;
}

// Использование в компоненте:
function Sidebar() {
  const hydrated = useStoreHydration();
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);

  if (!hydrated) {
    return <SidebarSkeleton />; // SSR fallback
  }

  return sidebarOpen ? <FullSidebar /> : <CollapsedSidebar />;
}
```

Альтернатива — onRehydrateStorage callback:

```typescript
export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      /* ... */
    }),
    {
      name: 'ui-store',
      onRehydrateStorage: () => (state) => {
        // Вызывается после гидратации из storage
        console.log('Store hydrated:', state);
      },
    },
  ),
);
```

### Per-request store (SSR Context Pattern)

Для серверного рендера — store на каждый запрос:

```typescript
// stores/create-store.ts
import { createStore } from 'zustand';

export interface AppState {
  user: { id: string; name: string } | null;
}

export const createAppStore = (initialState?: Partial<AppState>) =>
  createStore<AppState>()(() => ({
    user: null,
    ...initialState,
  }));

// providers/store-provider.tsx
'use client';

import { createContext, useContext, useRef, type ReactNode } from 'react';
import { useStore, type StoreApi } from 'zustand';
import { createAppStore, type AppState } from '@/stores/create-store';

const StoreContext = createContext<StoreApi<AppState> | null>(null);

export function StoreProvider({
  children,
  initialState,
}: {
  children: ReactNode;
  initialState?: Partial<AppState>;
}) {
  const storeRef = useRef<StoreApi<AppState>>(undefined);
  if (!storeRef.current) {
    storeRef.current = createAppStore(initialState);
  }

  return (
    <StoreContext.Provider value={storeRef.current}>
      {children}
    </StoreContext.Provider>
  );
}

export function useAppStore<T>(selector: (state: AppState) => T): T {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useAppStore must be used within StoreProvider');
  return useStore(store, selector);
}
```

---

## 3.3 Jotai v2: атомарный подход

### Когда Jotai лучше Zustand

| Сценарий                             | Zustand   | Jotai     |
| ------------------------------------ | --------- | --------- |
| Глобальный UI state (theme, sidebar) | **Лучше** | Подходит  |
| Множество независимых фильтров       | Подходит  | **Лучше** |
| Spreadsheet-подобные вычисления      | Сложно    | **Лучше** |
| DevTools / debugging                 | **Лучше** | Слабее    |
| Формы с зависимыми полями            | Подходит  | **Лучше** |
| Простой глобальный store             | **Лучше** | Overkill  |

---

## 3.4 Миграция с Redux на Zustand

Проект greenfield — миграция с Redux не требуется. Zustand v5 — единственный state manager.

---

## 3.5 Тестирование store (Vitest)

```typescript
// stores/__tests__/cart-store.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useCartStore } from '../cart-store';

describe('CartStore', () => {
  beforeEach(() => {
    // Сброс store перед каждым тестом
    useCartStore.setState({ items: [] });
  });

  it('should add item', () => {
    useCartStore.getState().addItem({ id: '1', name: 'Widget', price: 10 });

    const { items } = useCartStore.getState();
    expect(items).toHaveLength(1);
    expect(items[0]).toEqual({ id: '1', name: 'Widget', price: 10, quantity: 1 });
  });

  it('should increment quantity for existing item', () => {
    const { addItem } = useCartStore.getState();
    addItem({ id: '1', name: 'Widget', price: 10 });
    addItem({ id: '1', name: 'Widget', price: 10 });

    expect(useCartStore.getState().items[0].quantity).toBe(2);
  });

  it('should calculate total', () => {
    const { addItem } = useCartStore.getState();
    addItem({ id: '1', name: 'A', price: 10 });
    addItem({ id: '2', name: 'B', price: 20 });

    expect(useCartStore.getState().total()).toBe(30);
  });

  it('should remove item', () => {
    useCartStore.getState().addItem({ id: '1', name: 'A', price: 10 });
    useCartStore.getState().removeItem('1');

    expect(useCartStore.getState().items).toHaveLength(0);
  });
});
```

---

## 3.6 Антипаттерны и частые ошибки

| Антипаттерн                           | Проблема                      | Решение                                          |
| ------------------------------------- | ----------------------------- | ------------------------------------------------ |
| Весь store в одном селекторе          | Ре-рендер при любом изменении | Гранулярные селекторы: `useStore(s => s.field)`  |
| Серверные данные в Zustand            | Дублирование, рассинхрон      | TanStack Query для серверного кэша               |
| `set({ ...get(), field: value })`     | Нет нужды spread'ить          | `set({ field: value })` — Zustand мержит shallow |
| Store в `useEffect` для инициализации | Race condition, лишний рендер | `useRef` + `createStore` или SSR initialState    |
| Огромный монолитный store             | Сложность, конфликты          | Slices pattern или отдельные stores по домену    |
| Zustand для form state                | Лишняя сложность              | React Hook Form для форм                         |

---

## 3.7 Итоговые рекомендации

| Задача                                 | Решение                                |
| -------------------------------------- | -------------------------------------- |
| Глобальный UI (theme, sidebar, toasts) | **Zustand v5** + persist               |
| Auth state (user, token)               | **Zustand v5** + persist               |
| Серверные данные (products, users)     | **TanStack Query v5** (НЕ Zustand)     |
| Множество фильтров с зависимостями     | **Jotai v2**                           |
| Формы                                  | **React Hook Form** (НЕ state manager) |
| URL state (search, page, sort)         | **nuqs** или `useSearchParams`         |
| Локальный UI (toggle, hover)           | **useState**                           |

---

## Источники

- [Zustand v5 Documentation](https://github.com/pmndrs/zustand)
- [Zustand Slices Pattern](https://zustand.docs.pmnd.rs/guides/slices-pattern)
- [Jotai v2 Documentation](https://jotai.org/)
- [TkDodo: Practical React Query](https://tkdodo.eu/blog/practical-react-query)
- [Zustand vs Jotai vs Valtio Performance Guide 2025](https://www.reactlibraries.com/blog/zustand-vs-jotai-vs-valtio-performance-guide-2025)
- [State Management in 2026 — DEV Community](https://dev.to/jsgurujobs/state-management-in-2026-zustand-vs-jotai-vs-redux-toolkit-vs-signals-2gge)

---

---

# Часть 3 — Формы, валидация и архитектура API-слоя

> Расширенный анализ React Hook Form, Zod, HTTP-клиентов и паттернов enterprise API layer.

---

## 4.1 React Hook Form: продвинутые паттерны

### Multi-step Form Wizard

```typescript
// components/multi-step-form.tsx
'use client';

import { useForm, FormProvider, useFormContext } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { z } from 'zod';

// Общая схема
const wizardSchema = z.object({
  // Step 1: Personal
  firstName: z.string().min(2),
  lastName: z.string().min(2),
  email: z.string().email(),
  // Step 2: Address
  street: z.string().min(5),
  city: z.string().min(2),
  zipCode: z.string().regex(/^\d{6}$/),
  // Step 3: Payment
  cardNumber: z.string().regex(/^\d{16}$/),
  expiry: z.string().regex(/^\d{2}\/\d{2}$/),
});

type WizardData = z.infer<typeof wizardSchema>;

const STEPS = [
  { fields: ['firstName', 'lastName', 'email'] as const, title: 'Personal Info' },
  { fields: ['street', 'city', 'zipCode'] as const, title: 'Address' },
  { fields: ['cardNumber', 'expiry'] as const, title: 'Payment' },
];

export function MultiStepForm() {
  const [step, setStep] = useState(0);
  const methods = useForm<WizardData>({
    resolver: zodResolver(wizardSchema),
    mode: 'onTouched',
  });

  const nextStep = async () => {
    const fields = STEPS[step].fields;
    const valid = await methods.trigger(fields);
    if (valid) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const prevStep = () => setStep((s) => Math.max(s - 1, 0));

  const onSubmit = methods.handleSubmit(async (data) => {
    await submitWizard(data);
  });

  return (
    <FormProvider {...methods}>
      <form onSubmit={onSubmit}>
        <div>Step {step + 1} of {STEPS.length}: {STEPS[step].title}</div>

        {step === 0 && <PersonalStep />}
        {step === 1 && <AddressStep />}
        {step === 2 && <PaymentStep />}

        <div>
          {step > 0 && <button type="button" onClick={prevStep}>Back</button>}
          {step < STEPS.length - 1 && (
            <button type="button" onClick={nextStep}>Next</button>
          )}
          {step === STEPS.length - 1 && (
            <button type="submit">Submit</button>
          )}
        </div>
      </form>
    </FormProvider>
  );
}

function PersonalStep() {
  const { register, formState: { errors } } = useFormContext<WizardData>();
  return (
    <>
      <input {...register('firstName')} placeholder="First Name" />
      {errors.firstName && <span>{errors.firstName.message}</span>}
      <input {...register('lastName')} placeholder="Last Name" />
      <input {...register('email')} placeholder="Email" />
    </>
  );
}
```

### useFieldArray для динамических полей

```typescript
// components/invoice-form.tsx
'use client';

import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const lineItemSchema = z.object({
  description: z.string().min(1),
  quantity: z.coerce.number().min(1),
  unitPrice: z.coerce.number().min(0),
});

const invoiceSchema = z.object({
  clientName: z.string().min(2),
  items: z.array(lineItemSchema).min(1, 'At least one item required'),
});

type InvoiceData = z.infer<typeof invoiceSchema>;

export function InvoiceForm() {
  const { register, control, handleSubmit, watch } = useForm<InvoiceData>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: {
      items: [{ description: '', quantity: 1, unitPrice: 0 }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'items',
  });

  const items = watch('items');
  const total = items?.reduce((sum, item) =>
    sum + (item.quantity || 0) * (item.unitPrice || 0), 0) || 0;

  return (
    <form onSubmit={handleSubmit(console.log)}>
      <input {...register('clientName')} placeholder="Client Name" />

      {fields.map((field, index) => (
        <div key={field.id}>
          <input {...register(`items.${index}.description`)} placeholder="Description" />
          <input {...register(`items.${index}.quantity`)} type="number" />
          <input {...register(`items.${index}.unitPrice`)} type="number" step="0.01" />
          {fields.length > 1 && (
            <button type="button" onClick={() => remove(index)}>Remove</button>
          )}
        </div>
      ))}

      <button type="button" onClick={() => append({ description: '', quantity: 1, unitPrice: 0 })}>
        Add Item
      </button>

      <div>Total: ${total.toFixed(2)}</div>
      <button type="submit">Create Invoice</button>
    </form>
  );
}
```

---

## 4.2 Продвинутые Zod-паттерны

### Discriminated Unions

```typescript
// schemas/payment.ts
import { z } from 'zod';

const creditCardSchema = z.object({
  method: z.literal('credit_card'),
  cardNumber: z.string().regex(/^\d{16}$/),
  expiry: z.string().regex(/^\d{2}\/\d{2}$/),
  cvv: z.string().regex(/^\d{3,4}$/),
});

const bankTransferSchema = z.object({
  method: z.literal('bank_transfer'),
  iban: z.string().min(15).max(34),
  bic: z.string().min(8).max(11),
});

const cryptoSchema = z.object({
  method: z.literal('crypto'),
  walletAddress: z.string().min(26).max(62),
  network: z.enum(['ethereum', 'bitcoin', 'solana']),
});

export const paymentSchema = z.discriminatedUnion('method', [
  creditCardSchema,
  bankTransferSchema,
  cryptoSchema,
]);

export type PaymentData = z.infer<typeof paymentSchema>;
```

### Transform и Preprocess

```typescript
// schemas/product.ts
import { z } from 'zod';

export const productSchema = z.object({
  name: z
    .string()
    .min(1)
    .transform((s) => s.trim()),

  // Preprocess: string из input -> number
  price: z.preprocess(
    (val) => (typeof val === 'string' ? parseFloat(val) : val),
    z.number().positive(),
  ),

  // Transform: cents для хранения
  priceInCents: z
    .number()
    .positive()
    .transform((val) => Math.round(val * 100)),

  // Refinement: кастомная валидация
  slug: z
    .string()
    .min(3)
    .regex(/^[a-z0-9-]+$/, 'Only lowercase letters, numbers, and hyphens')
    .refine(
      async (slug) => {
        const exists = await checkSlugExists(slug);
        return !exists;
      },
      { message: 'Slug already taken' },
    ),

  tags: z.array(z.string()).default([]),

  // Coerce: автоматическое приведение типов
  publishedAt: z.coerce.date(),
});
```

---

## 4.3 Conform.js: серверно-ориентированные формы

Альтернатива RHF для Server-Action-first подхода.

| Критерий                | React Hook Form         | Conform                       |
| ----------------------- | ----------------------- | ----------------------------- |
| Подход                  | Client-first            | Server-first                  |
| Server Actions          | Через `startTransition` | Нативная интеграция           |
| Bundle size             | ~9 KB                   | ~5 KB                         |
| Progressive enhancement | Нет (нужен JS)          | Да (работает без JS)          |
| DevTools                | Да                      | Нет                           |
| Экосистема              | Огромная                | Малая                         |
| **Рекомендация**        | SPA, сложные формы      | Server Actions, простые формы |

---

## 5.1 API-клиент: продвинутая конфигурация

### ky с refresh token rotation

```typescript
// lib/api-client.ts
import ky from 'ky';

let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const res = await ky
    .post('/api/auth/refresh', {
      json: { refreshToken: getRefreshToken() },
    })
    .json<{ accessToken: string }>();

  setAccessToken(res.accessToken);
  return res.accessToken;
}

export const apiClient = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_API_URL,
  timeout: 15_000,
  retry: { limit: 2, methods: ['get'], statusCodes: [408, 500, 502, 503] },
  hooks: {
    beforeRequest: [
      async (request) => {
        let token = getAccessToken();

        if (isTokenExpired(token)) {
          if (!isRefreshing) {
            isRefreshing = true;
            refreshPromise = refreshAccessToken().finally(() => {
              isRefreshing = false;
              refreshPromise = null;
            });
          }
          token = await refreshPromise!;
        }

        request.headers.set('Authorization', `Bearer ${token}`);
      },
    ],
    afterResponse: [
      async (request, options, response) => {
        if (response.status === 401) {
          // Token was invalid even after refresh — force logout
          logout();
          window.location.href = '/login';
        }
      },
    ],
  },
});
```

### OpenAPI TypeScript code generation

Автоматическая типизация API из OpenAPI спецификации:

```bash
# Установка
pnpm add -D openapi-typescript openapi-fetch

# Генерация типов
pnpm openapi-typescript https://api.example.com/openapi.json -o src/types/api.d.ts
```

```typescript
// lib/api-client.ts
import createClient from 'openapi-fetch';
import type { paths } from '@/types/api';

export const api = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL,
  headers: { Authorization: `Bearer ${getToken()}` },
});

// Использование — полная типобезопасность:
const { data, error } = await api.GET('/products/{id}', {
  params: { path: { id: '123' } },
});
// data автоматически типизирован на основе OpenAPI schema
```

---

## 5.2 Централизованная обработка ошибок

```typescript
// lib/errors.ts
export class AppError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string,
    public details?: Record<string, string[]>,
  ) {
    super(message);
    this.name = 'AppError';
  }

  get isUnauthorized() {
    return this.statusCode === 401;
  }
  get isForbidden() {
    return this.statusCode === 403;
  }
  get isNotFound() {
    return this.statusCode === 404;
  }
  get isValidation() {
    return this.statusCode === 422;
  }
  get isServerError() {
    return this.statusCode >= 500;
  }
}

// lib/handle-api-error.ts
import { toast } from 'sonner';
import { AppError } from './errors';

export function handleApiError(error: unknown) {
  if (error instanceof AppError) {
    if (error.isUnauthorized) {
      window.location.href = '/login';
      return;
    }
    if (error.isValidation && error.details) {
      Object.values(error.details)
        .flat()
        .forEach((msg) => toast.error(msg));
      return;
    }
    if (error.isServerError) {
      toast.error('Server error. Please try again later.');
      return;
    }
    toast.error(error.message);
    return;
  }

  toast.error('An unexpected error occurred');
}
```

### TanStack Query глобальный обработчик

```typescript
// lib/query-client.ts
import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { handleApiError } from './handle-api-error';

export function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => handleApiError(error),
    }),
    mutationCache: new MutationCache({
      onError: (error) => handleApiError(error),
    }),
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        retry: (failureCount, error) => {
          if (error instanceof AppError && error.statusCode < 500) return false;
          return failureCount < 2;
        },
      },
    },
  });
}
```

---

## 5.3 File Upload с прогрессом

```typescript
// lib/upload.ts
export async function uploadFile(
  file: File,
  onProgress: (percent: number) => void,
): Promise<{ url: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Upload failed')));

    const formData = new FormData();
    formData.append('file', file);

    xhr.open('POST', '/api/upload');
    xhr.setRequestHeader('Authorization', `Bearer ${getToken()}`);
    xhr.send(formData);
  });
}

// hooks/use-file-upload.ts
('use client');

import { useState, useCallback } from 'react';
import { uploadFile } from '@/lib/upload';

export function useFileUpload() {
  const [progress, setProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const upload = useCallback(async (file: File) => {
    setIsUploading(true);
    setProgress(0);
    try {
      const result = await uploadFile(file, setProgress);
      return result;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return { upload, progress, isUploading };
}
```

---

## Источники

- [React Hook Form Documentation](https://react-hook-form.com/)
- [Zod Documentation](https://zod.dev/)
- [Conform Documentation](https://conform.guide/)
- [ky Documentation](https://github.com/sindresorhus/ky)
- [openapi-typescript + openapi-fetch](https://openapi-ts.dev/)
- [Next.js: How to create forms with Server Actions](https://nextjs.org/docs/app/guides/forms)

---

---

# Часть 4 — Server Actions и стратегии кэширования

> Расширенный анализ Server Actions как BFF-proxy, Data Access Layer, React 19 хуков и многоуровневого кэширования в Next.js 15+.
> В нашей архитектуре Server Actions проксируют запросы к бэкенд-сервисам, а не обращаются к БД напрямую.

---

## 6.1 Server Actions: архитектура безопасности

### Data Access Layer (DAL) — адаптация для BFF/Proxy

Рекомендованный Vercel паттерн — авторизация на уровне доступа к данным, а не на уровне маршрутов.
В нашем случае (frontend-only, Next.js как BFF) DAL проверяет auth и проксирует запросы к бэкенд-сервисам:

```typescript
// lib/dal.ts (Data Access Layer — BFF proxy)
import 'server-only';
import { cache } from 'react';
import { getSession } from '@/lib/auth';
import { apiServer } from '@/lib/api-server';

export const getCurrentUser = cache(async () => {
  const session = await getSession();
  if (!session?.user) return null;
  return session.user;
});

export const requireAuth = cache(async () => {
  const user = await getCurrentUser();
  if (!user) throw new Error('Unauthorized');
  return user;
});

export const requireRole = cache(async (role: string) => {
  const user = await requireAuth();
  if (user.role !== role) throw new Error('Forbidden');
  return user;
});
```

```typescript
// lib/data/products.ts — proxy к products-сервису
import 'server-only';
import { requireAuth, requireRole } from '@/lib/dal';
import { apiServer } from '@/lib/api-server';

export async function getProducts() {
  const user = await requireAuth();
  // Proxy к бэкенд-сервису с передачей токена авторизации
  return apiServer.get<Product[]>('/products', {
    headers: { Authorization: `Bearer ${user.token}` },
  });
}

export async function deleteProduct(id: string) {
  const user = await requireRole('admin');
  return apiServer.delete(`/products/${id}`, {
    headers: { Authorization: `Bearer ${user.token}` },
  });
}
```

```typescript
// app/actions/products.ts — Server Action (proxy к бэкенду)
'use server';

import { z } from 'zod';
import { revalidateTag } from 'next/cache';
import { deleteProduct } from '@/lib/data/products';

const deleteSchema = z.object({ id: z.string().uuid() });

export async function deleteProductAction(input: unknown) {
  const { id } = deleteSchema.parse(input);
  await deleteProduct(id); // DAL проверяет auth + проксирует к бэкенду
  revalidateTag('products');
  return { success: true };
}
```

**Почему DAL, а не middleware?**

- Middleware можно обойти (CVE-2025-29927 — обход через заголовок `x-middleware-subrequest`)
- DAL проверяет авторизацию и формирует запрос к бэкенду в одном месте
- `cache()` из React дедуплицирует вызовы в одном request
- Бэкенд-сервис **также** проверяет авторизацию (defence in depth), но DAL предотвращает лишние сетевые запросы

---

## 6.2 React 19: useActionState

Замена устаревшего `useFormState`:

```typescript
// components/create-post-form.tsx
'use client';

import { useActionState } from 'react';
import { createPost } from '@/app/actions/posts';

interface ActionState {
  success?: boolean;
  error?: string;
  errors?: Record<string, string[]>;
}

export function CreatePostForm() {
  const [state, formAction, isPending] = useActionState<ActionState, FormData>(
    createPost,
    { success: false },
  );

  return (
    <form action={formAction}>
      <input name="title" placeholder="Title" />
      {state.errors?.title && <span>{state.errors.title[0]}</span>}

      <textarea name="content" placeholder="Content" />
      {state.errors?.content && <span>{state.errors.content[0]}</span>}

      <button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create Post'}
      </button>

      {state.error && <div className="error">{state.error}</div>}
      {state.success && <div className="success">Post created!</div>}
    </form>
  );
}
```

```typescript
// app/actions/posts.ts
'use server';

import { z } from 'zod';
import { requireAuth } from '@/lib/dal';
import { revalidateTag } from 'next/cache';

const postSchema = z.object({
  title: z.string().min(3).max(200),
  content: z.string().min(10),
});

export async function createPost(prevState: unknown, formData: FormData) {
  const user = await requireAuth();

  const parsed = postSchema.safeParse({
    title: formData.get('title'),
    content: formData.get('content'),
  });

  if (!parsed.success) {
    return {
      success: false,
      errors: parsed.error.flatten().fieldErrors,
    };
  }

  // Proxy к бэкенд-сервису
  await apiServer.post('/posts', {
    json: { ...parsed.data, authorId: user.id },
    headers: { Authorization: `Bearer ${user.token}` },
  });

  revalidateTag('posts');
  return { success: true };
}
```

---

## 6.3 useOptimistic (React 19)

```typescript
// components/todo-list.tsx
'use client';

import { useOptimistic, useTransition } from 'react';
import { toggleTodo } from '@/app/actions/todos';

interface Todo {
  id: string;
  text: string;
  completed: boolean;
}

export function TodoList({ todos }: { todos: Todo[] }) {
  const [isPending, startTransition] = useTransition();

  const [optimisticTodos, setOptimisticTodos] = useOptimistic(
    todos,
    (state: Todo[], updatedId: string) =>
      state.map((todo) =>
        todo.id === updatedId ? { ...todo, completed: !todo.completed } : todo,
      ),
  );

  const handleToggle = (id: string) => {
    startTransition(async () => {
      setOptimisticTodos(id); // Мгновенное обновление UI
      await toggleTodo(id);   // Серверная мутация
    });
  };

  return (
    <ul>
      {optimisticTodos.map((todo) => (
        <li key={todo.id}>
          <label>
            <input
              type="checkbox"
              checked={todo.completed}
              onChange={() => handleToggle(todo.id)}
            />
            <span style={{ opacity: isPending ? 0.7 : 1 }}>
              {todo.text}
            </span>
          </label>
        </li>
      ))}
    </ul>
  );
}
```

---

## 6.4 Rate Limiting Server Actions

```typescript
// lib/rate-limit.ts
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_URL!,
  token: process.env.UPSTASH_REDIS_TOKEN!,
});

export const rateLimit = new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(10, '60 s'), // 10 requests per 60s
  analytics: true,
});

// lib/safe-action.ts
import { headers } from 'next/headers';
import { rateLimit } from './rate-limit';

export async function rateLimitByIp() {
  const headersList = await headers();
  const ip = headersList.get('x-forwarded-for') ?? 'anonymous';
  const { success, limit, remaining } = await rateLimit.limit(ip);

  if (!success) {
    throw new Error(`Rate limit exceeded. Try again later.`);
  }

  return { limit, remaining };
}

// Использование в Server Action:
export async function submitContactAction(data: ContactData) {
  await rateLimitByIp();
  await requireAuth();
  // ... бизнес-логика
}
```

---

## 7.1 Next.js 15: изменения в кэшировании

**Критическое изменение:** в Next.js 15 `fetch()` **больше не кэшируется по умолчанию**. Нужно явно указывать:

```typescript
// Next.js 14 — кэшировалось автоматически
const data = await fetch('https://api.example.com/data');

// Next.js 15 — НЕ кэшируется по умолчанию. Нужно явно:
const data = await fetch('https://api.example.com/data', {
  next: { revalidate: 3600 }, // Кэш на 1 час
});

// Или force-cache:
const data = await fetch('https://api.example.com/data', {
  cache: 'force-cache',
});

// Или на уровне segment:
export const revalidate = 3600; // Все fetch на этой странице
```

### Таблица решений по кэшированию

| Тип данных                       | Стратегия                 | Настройка                                 |
| -------------------------------- | ------------------------- | ----------------------------------------- |
| Статический контент (about, FAQ) | Static Generation         | `export const dynamic = 'force-static'`   |
| Каталог товаров                  | ISR                       | `export const revalidate = 300`           |
| Профиль пользователя             | No cache + TanStack Query | `cache: 'no-store'` + `staleTime: 60_000` |
| Dashboard метрики                | TanStack Query polling    | `refetchInterval: 30_000`                 |
| Результаты поиска                | No cache                  | `cache: 'no-store'`                       |
| Blog posts                       | ISR + on-demand           | `revalidate: 3600` + `revalidateTag()`    |

---

## 7.2 Tag-based кэш инвалидация

```typescript
// lib/data/products.ts
export async function getProducts(categoryId?: string) {
  const res = await fetch(`${API_URL}/products?category=${categoryId}`, {
    next: {
      tags: [
        'products', // Все продукты
        categoryId ? `products:${categoryId}` : '', // По категории
      ].filter(Boolean),
      revalidate: 300,
    },
  });
  return res.json();
}

export async function getProduct(id: string) {
  const res = await fetch(`${API_URL}/products/${id}`, {
    next: {
      tags: ['products', `product:${id}`], // Конкретный продукт
      revalidate: 300,
    },
  });
  return res.json();
}

// Инвалидация:
// revalidateTag('products')       — все продукты и все категории
// revalidateTag('products:shoes') — только категория shoes
// revalidateTag('product:123')    — только продукт 123
```

### Webhook для on-demand revalidation

```typescript
// app/api/webhooks/cms/route.ts
import { revalidateTag } from 'next/cache';
import { headers } from 'next/headers';

export async function POST(request: Request) {
  const headersList = await headers();
  const secret = headersList.get('x-webhook-secret');

  if (secret !== process.env.WEBHOOK_SECRET) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const body = await request.json();

  switch (body.event) {
    case 'product.created':
    case 'product.updated':
    case 'product.deleted':
      revalidateTag('products');
      revalidateTag(`product:${body.data.id}`);
      break;

    case 'category.updated':
      revalidateTag(`products:${body.data.categoryId}`);
      break;
  }

  return Response.json({ revalidated: true });
}
```

---

## 7.3 unstable_cache vs fetch cache

```typescript
import { unstable_cache } from 'next/cache';
import { apiServer } from '@/lib/api-server';

// unstable_cache — для кэширования ответов бэкенд-сервисов
// (полезно когда нужен tag-based revalidation для non-fetch вызовов)
const getCachedProducts = unstable_cache(
  async (categoryId: string) => {
    return apiServer.get<Product[]>('/products', {
      params: { categoryId, include: 'category' },
    });
  },
  ['products'],                    // Cache key prefix
  {
    tags: ['products'],            // For revalidateTag()
    revalidate: 300,               // TTL in seconds
  },
);

// Использование в Server Component:
export default async function ProductsPage({ params }: { params: { categoryId: string } }) {
  const products = await getCachedProducts(params.categoryId);
  return <ProductList products={products} />;
}
```

> **Примечание для BFF-архитектуры:** в большинстве случаев предпочтительнее использовать
> `fetch()` c `next: { tags, revalidate }` вместо `unstable_cache`, так как запросы к бэкенд-сервисам
> и так идут через HTTP. `unstable_cache` полезен для кэширования результатов, требующих
> пост-обработки нескольких API-вызовов.

| Критерий           | `fetch` cache             | `unstable_cache`                             | TanStack Query                |
| ------------------ | ------------------------- | -------------------------------------------- | ----------------------------- |
| Среда              | Server                    | Server                                       | Client (+ SSR prefetch)       |
| Источник           | HTTP endpoints            | Любые async функции (API-вызовы, вычисления) | HTTP endpoints                |
| Tag invalidation   | Да                        | Да                                           | Через `invalidateQueries`     |
| Persistence        | Data Cache (disk)         | Data Cache (disk)                            | In-memory (browser)           |
| DevTools           | Нет                       | Нет                                          | Да (отличные)                 |
| Optimistic updates | Нет                       | Нет                                          | Да                            |
| **Когда**          | Запросы к бэкенд-сервисам | Составные API-вызовы, вычисления             | Клиентские данные, интерактив |

---

## 7.4 Многоуровневый кэш: полная картина

```
Запрос пользователя
        │
        ▼
┌─ CDN / Edge Cache ──────────────────┐
│  Cache-Control: s-maxage=300        │
│  stale-while-revalidate=600         │
│  HIT → мгновенный ответ             │
└──────────┬──────────────────────────┘
           │ MISS
           ▼
┌─ Full Route Cache (ISR) ────────────┐
│  export const revalidate = 300      │
│  Статическая HTML-страница          │
│  HIT → ответ без рендера            │
└──────────┬──────────────────────────┘
           │ MISS / STALE
           ▼
┌─ Data Cache (fetch / unstable_cache)┐
│  next: { tags: [...], revalidate }  │
│  Кэш отдельных запросов             │
│  HIT → рендер с кэшированными       │
│        данными                      │
└──────────┬──────────────────────────┘
           │ MISS
           ▼
┌─ Backend Services (Origin) ─────────┐
│  Реальный запрос к бэкенд-сервису   │
│  Результат кэшируется на всех       │
│  уровнях выше                       │
└─────────────────────────────────────┘

        На клиенте:
┌─ TanStack Query Cache ─────────────┐
│  In-memory, staleTime: 60_000      │
│  Background refetch при фокусе     │
│  Optimistic updates при мутациях   │
└────────────────────────────────────┘
```

---

## 7.5 Стратегия для enterprise

| Сценарий            | Серверный кэш          | Клиентский кэш                              | Инвалидация                      |
| ------------------- | ---------------------- | ------------------------------------------- | -------------------------------- |
| **Маркетинг/блог**  | ISR `revalidate: 3600` | Нет (SSG)                                   | Webhook `revalidateTag`          |
| **Каталог товаров** | ISR `revalidate: 300`  | TQ `staleTime: 60s`                         | Server Action + `revalidateTag`  |
| **Dashboard**       | No cache               | TQ `staleTime: 30s`, `refetchInterval: 30s` | `invalidateQueries` при мутации  |
| **Профиль**         | `fetch` cache + tags   | TQ `staleTime: 5min`                        | Server Action + tag + invalidate |
| **Поиск**           | No cache               | TQ `staleTime: 0`                           | Нет (всегда свежий)              |
| **Чат/нотификации** | No cache               | TQ + SSE invalidation                       | Push-based                       |

---

## Источники

- [Next.js: Caching](https://nextjs.org/docs/app/building-your-application/caching)
- [Next.js: Server Actions and Mutations](https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations)
- [Next.js: Data Access Layer Security](https://nextjs.org/blog/security-nextjs-server-components-actions)
- [React 19: useActionState](https://react.dev/reference/react/useActionState)
- [React 19: useOptimistic](https://react.dev/reference/react/useOptimistic)
- [Upstash Rate Limiting](https://upstash.com/docs/oss/sdks/ts/ratelimit)
- [CVE-2025-29927: Next.js Middleware Bypass](https://zhero-web-sec.github.io/research-and-things/nextjs-middleware-auth-bypass)
- [Next.js 15 Caching Changes](https://nextjs.org/blog/next-15)

---

---

# Часть 5 — Real-time данные и Рекомендуемый стек

> Глубокое исследование real-time паттернов, управляемых WebSocket-сервисов, AI-стриминга,
> мониторинга производительности и полных архитектурных рекомендаций для enterprise Next.js (App Router) 2025-2026.

---

## 8. Real-time данные

### 8.1 Сравнение подходов

| Подход                       | Направление             | Latency            | Сложность | Serverless (Vercel) | Масштабирование        | Стоимость      |
| ---------------------------- | ----------------------- | ------------------ | --------- | ------------------- | ---------------------- | -------------- |
| **Polling (TanStack Query)** | Pull                    | Средняя (интервал) | Низкая    | Да                  | Линейно с клиентами    | Низкая         |
| **Adaptive Polling**         | Pull (умный)            | Средняя-Низкая     | Средняя   | Да                  | Хорошее                | Низкая         |
| **Long Polling**             | Pull (задержанный)      | Средняя            | Средняя   | Частично            | Среднее                | Низкая         |
| **SSE (Server-Sent Events)** | Push (server -> client) | Низкая             | Средняя   | Да (Route Handlers) | Хорошее                | Низкая         |
| **WebSocket (Socket.IO)**    | Bidirectional           | Очень низкая       | Высокая   | Нет (свой сервер)   | Требует инфраструктуру | Средняя        |
| **PartyKit**                 | Bidirectional (edge)    | Очень низкая       | Средняя   | Да (свой edge)      | Автоматическое         | Средняя        |
| **Managed (Pusher/Ably)**    | Bidirectional           | Низкая             | Низкая    | Да                  | Автоматическое         | Высокая        |
| **AI Streaming (AI SDK)**    | Push (stream)           | Реальное время     | Средняя   | Да                  | По модели              | Зависит от LLM |

### 8.2 SSE с автоматическим переподключением и типами событий

#### Сервер: Route Handler с именованными событиями и Last-Event-ID

```typescript
// app/api/events/route.ts
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

interface SSEEvent {
  id: string;
  type: 'notification' | 'order-update' | 'price-change' | 'heartbeat';
  data: unknown;
}

export async function GET(request: Request) {
  const encoder = new TextEncoder();

  // Поддержка возобновления потока: клиент отправляет Last-Event-ID
  const lastEventId = request.headers.get('Last-Event-ID');

  const stream = new ReadableStream({
    async start(controller) {
      let eventCounter = parseInt(lastEventId ?? '0', 10);

      const send = (event: Omit<SSEEvent, 'id'>) => {
        eventCounter++;
        const id = String(eventCounter);
        // SSE-формат: id, event (тип), data, retry (мс до переподключения)
        const message = [
          `id: ${id}`,
          `event: ${event.type}`,
          `data: ${JSON.stringify(event.data)}`,
          `retry: 3000`, // клиент переподключится через 3с
          '',
          '', // пустая строка = конец сообщения
        ].join('\n');
        controller.enqueue(encoder.encode(message));
      };

      // Heartbeat каждые 30с для поддержания соединения (прокси/балансеры)
      const heartbeat = setInterval(() => {
        send({ type: 'heartbeat', data: { ts: Date.now() } });
      }, 30_000);

      // Подписка на источник данных (Redis Pub/Sub, DB change stream и т.д.)
      const unsubscribe = await subscribeToEvents(
        (event) => send(event),
        { afterId: lastEventId }, // отправляем пропущенные события
      );

      // Очистка при отключении клиента
      request.signal.addEventListener('abort', () => {
        clearInterval(heartbeat);
        unsubscribe();
        controller.close();
      });
    },
  });

  // ВАЖНО: Response возвращается немедленно, стриминг идёт асинхронно
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-store, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no', // отключить буферизацию Nginx
    },
  });
}
```

#### Клиент: хук с автоматическим переподключением и диспетчеризацией типов

```typescript
// hooks/use-sse.ts
'use client';

import { useEffect, useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface UseSSEOptions {
  url: string;
  onNotification?: (data: unknown) => void;
  onOrderUpdate?: (data: unknown) => void;
  onPriceChange?: (data: unknown) => void;
  maxRetries?: number;
  enabled?: boolean;
}

interface SSEState {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  retryCount: number;
  lastEventId: string | null;
}

export function useSSE({
  url,
  onNotification,
  onOrderUpdate,
  onPriceChange,
  maxRetries = 10,
  enabled = true,
}: UseSSEOptions) {
  const queryClient = useQueryClient();
  const sourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const [state, setState] = useState<SSEState>({
    status: 'disconnected',
    retryCount: 0,
    lastEventId: null,
  });

  const connect = useCallback(() => {
    if (!enabled) return;

    // EventSource автоматически отправляет Last-Event-ID при переподключении
    const source = new EventSource(url);
    sourceRef.current = source;
    setState((s) => ({ ...s, status: 'connecting' }));

    source.addEventListener('open', () => {
      retryCountRef.current = 0;
      setState((s) => ({ ...s, status: 'connected', retryCount: 0 }));
    });

    // Именованные события — каждый тип обрабатывается отдельно
    source.addEventListener('notification', (e) => {
      const data = JSON.parse(e.data);
      setState((s) => ({ ...s, lastEventId: e.lastEventId }));
      onNotification?.(data);
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    });

    source.addEventListener('order-update', (e) => {
      const data = JSON.parse(e.data);
      setState((s) => ({ ...s, lastEventId: e.lastEventId }));
      onOrderUpdate?.(data);
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    });

    source.addEventListener('price-change', (e) => {
      const data = JSON.parse(e.data);
      setState((s) => ({ ...s, lastEventId: e.lastEventId }));
      onPriceChange?.(data);
      queryClient.setQueryData(['prices'], (old: unknown[]) => (old ? [...old, data] : [data]));
    });

    source.addEventListener('heartbeat', () => {
      // Heartbeat — ничего не делаем, просто подтверждаем живое соединение
    });

    source.addEventListener('error', () => {
      source.close();
      // Exponential backoff с jitter для переподключения
      if (retryCountRef.current < maxRetries) {
        const baseDelay = Math.min(1000 * 2 ** retryCountRef.current, 30_000);
        const jitter = Math.random() * 1000;
        const delay = baseDelay + jitter;
        retryCountRef.current++;
        setState((s) => ({
          ...s,
          status: 'error',
          retryCount: retryCountRef.current,
        }));
        setTimeout(connect, delay);
      } else {
        setState((s) => ({ ...s, status: 'disconnected' }));
      }
    });
  }, [url, enabled, maxRetries, queryClient, onNotification, onOrderUpdate, onPriceChange]);

  useEffect(() => {
    connect();
    return () => sourceRef.current?.close();
  }, [connect]);

  return state;
}
```

**Ключевые принципы SSE в Next.js:**

1. `export const dynamic = 'force-dynamic'` — отключает кэширование Route Handler.
2. `Response` возвращается **немедленно** — стриминг идёт через `ReadableStream` асинхронно.
3. `X-Accel-Buffering: no` — критически важно для Nginx-прокси, иначе события буферизуются.
4. `retry: 3000` — указывает браузеру интервал автоматического переподключения.
5. `Last-Event-ID` — позволяет серверу отправить пропущенные события после reconnect.
6. Heartbeat каждые 30с предотвращает таймаут прокси/балансеров.

---

### 8.3 WebSocket-интеграция (Socket.IO + Next.js)

**Ограничение:** Vercel не поддерживает WebSocket-соединения. Socket.IO требует отдельного сервера
(Node.js, Docker, Railway, Fly.io и т.д.).

#### Архитектура: отдельный WebSocket-сервер + Next.js клиент

```
┌─────────────────┐    HTTP/SSR     ┌─────────────────┐
│   Next.js App   │◄──────────────►│   Vercel / CDN   │
│   (App Router)  │                │                  │
└────────┬────────┘                └──────────────────┘
         │
         │  WebSocket (wss://)
         ▼
┌─────────────────┐    Redis Pub/Sub  ┌──────────────┐
│  Socket.IO      │◄────────────────►│  Redis        │
│  Server         │                  │  (Upstash/    │
│  (Railway/Fly)  │                  │   Valkey)     │
└─────────────────┘                  └──────────────┘
```

#### Socket.IO сервер (отдельный процесс)

```typescript
// ws-server/index.ts
import { createServer } from 'http';
import { Server } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { createClient } from 'redis';

const httpServer = createServer();
const io = new Server(httpServer, {
  cors: {
    origin: process.env.NEXT_PUBLIC_APP_URL,
    methods: ['GET', 'POST'],
    credentials: true,
  },
  // Fallback на long-polling если WebSocket недоступен
  transports: ['websocket', 'polling'],
  pingTimeout: 60_000,
  pingInterval: 25_000,
});

// Redis adapter для горизонтального масштабирования
const pubClient = createClient({ url: process.env.REDIS_URL });
const subClient = pubClient.duplicate();
await Promise.all([pubClient.connect(), subClient.connect()]);
io.adapter(createAdapter(pubClient, subClient));

// Middleware: аутентификация
io.use(async (socket, next) => {
  const token = socket.handshake.auth.token;
  try {
    const user = await verifyToken(token);
    socket.data.user = user;
    next();
  } catch {
    next(new Error('Authentication failed'));
  }
});

// Пространства имён (namespaces) для разделения логики
const chatNs = io.of('/chat');
const dashNs = io.of('/dashboard');

chatNs.on('connection', (socket) => {
  const userId = socket.data.user.id;

  socket.on('join-room', (roomId: string) => {
    socket.join(roomId);
    chatNs.to(roomId).emit('user-joined', { userId, roomId });
  });

  socket.on('message', async (payload: { roomId: string; text: string }) => {
    const message = await saveMessage(payload);
    chatNs.to(payload.roomId).emit('new-message', message);
  });

  socket.on('typing', (roomId: string) => {
    socket.to(roomId).emit('user-typing', { userId });
  });

  socket.on('disconnect', () => {
    // cleanup
  });
});

httpServer.listen(3001, () => console.log('WS server on :3001'));
```

#### Next.js клиент: реюзабельный хук

```typescript
// hooks/use-socket.ts
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { io, type Socket } from 'socket.io-client';
import { useAuthStore } from '@/stores/auth-store';

interface UseSocketOptions {
  namespace?: string;
  enabled?: boolean;
}

interface SocketState {
  isConnected: boolean;
  transport: string | null;
}

export function useSocket({ namespace = '/', enabled = true }: UseSocketOptions = {}) {
  const socketRef = useRef<Socket | null>(null);
  const token = useAuthStore((s) => s.token);
  const [state, setState] = useState<SocketState>({
    isConnected: false,
    transport: null,
  });

  useEffect(() => {
    if (!enabled || !token) return;

    const socket = io(`${process.env.NEXT_PUBLIC_WS_URL}${namespace}`, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 30_000,
      randomizationFactor: 0.5, // jitter
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setState({
        isConnected: true,
        transport: socket.io.engine.transport.name,
      });
    });

    socket.on('disconnect', (reason) => {
      setState({ isConnected: false, transport: null });
      // Если сервер принудительно отключил — не переподключаемся
      if (reason === 'io server disconnect') {
        socket.connect();
      }
    });

    socket.io.engine.on('upgrade', (transport) => {
      setState((s) => ({ ...s, transport: transport.name }));
    });

    return () => {
      socket.disconnect();
    };
  }, [namespace, enabled, token]);

  const emit = useCallback(<T>(event: string, data: T) => socketRef.current?.emit(event, data), []);

  const on = useCallback(<T>(event: string, handler: (data: T) => void) => {
    socketRef.current?.on(event, handler);
    return () => {
      socketRef.current?.off(event, handler);
    };
  }, []);

  return { ...state, emit, on, socket: socketRef.current };
}
```

---

### 8.4 PartyKit для совместной работы

PartyKit (collaborative editing) не входит в текущий роадмап проекта.

---

### 8.5 AI-стриминг (Vercel AI SDK + ReadableStream)

AI-стриминг не входит в текущий роадмап проекта.

---

### 8.6 Управляемые real-time сервисы: Pusher vs Ably vs Soketi

| Характеристика             | Pusher Channels               | Ably                                      | Soketi (self-hosted)           |
| -------------------------- | ----------------------------- | ----------------------------------------- | ------------------------------ |
| **Тип**                    | Managed cloud                 | Managed cloud                             | Open-source, self-hosted       |
| **Протокол**               | WebSocket + fallback          | WebSocket + fallback                      | WebSocket (Pusher-совместимый) |
| **Глобальная сеть**        | Один дата-центр               | Множество дата-центров                    | Зависит от хостинга            |
| **Free tier**              | 100 connections, 200K msg/day | 200 connections, 100K msg/day (6M msg/mo) | Бесплатно (свой сервер)        |
| **Starter цена**           | $49/mo (500 conn, 30M msg)    | $29/mo (более гибкие лимиты)              | $5-10/mo (облачный VPS)        |
| **Масштабирование**        | Автоматическое                | Автоматическое + global                   | Ручное (горизонтальное)        |
| **Latency (глобально)**    | Средняя (один ДЦ)             | Низкая (edge-сеть)                        | Зависит от размещения          |
| **Pusher-совместимый SDK** | Нативный                      | Нет (свой SDK)                            | Да (drop-in замена)            |
| **Message ordering**       | Не гарантируется              | Гарантируется                             | Не гарантируется               |
| **Message history**        | Нет (только real-time)        | Да (до 72ч)                               | Нет                            |
| **Webhooks**               | Да                            | Да                                        | Да                             |
| **Присутствие (presence)** | Да                            | Да                                        | Да                             |
| **TypeScript SDK**         | Да                            | Да                                        | Pusher SDK                     |

#### Когда что выбирать

| Сценарий                                   | Рекомендация | Обоснование                                               |
| ------------------------------------------ | ------------ | --------------------------------------------------------- |
| MVP / стартап (скорость выхода)            | **Pusher**   | Простейшее API, обширная документация, быстрая интеграция |
| Enterprise / глобальная аудитория          | **Ably**     | Гарантия доставки, глобальная edge-сеть, message history  |
| Бюджетный проект / full control            | **Soketi**   | Бесплатно, Pusher-совместимый, полный контроль            |
| Уже используется Pusher, нужно удешевить   | **Soketi**   | Drop-in замена, тот же SDK, минимальные изменения         |
| Высокие требования к latency в Азии/Европе | **Ably**     | Мульти-регионная инфраструктура                           |

#### Пример: Pusher в Next.js

```typescript
// lib/pusher-server.ts
import Pusher from 'pusher';

export const pusherServer = new Pusher({
  appId: process.env.PUSHER_APP_ID!,
  key: process.env.NEXT_PUBLIC_PUSHER_KEY!,
  secret: process.env.PUSHER_SECRET!,
  cluster: process.env.NEXT_PUBLIC_PUSHER_CLUSTER!,
  useTLS: true,
});
```

```typescript
// lib/pusher-client.ts
import PusherClient from 'pusher-js';

export const pusherClient = new PusherClient(process.env.NEXT_PUBLIC_PUSHER_KEY!, {
  cluster: process.env.NEXT_PUBLIC_PUSHER_CLUSTER!,
  authEndpoint: '/api/pusher/auth',
  authTransport: 'ajax',
});
```

```typescript
// hooks/use-pusher-channel.ts
'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { pusherClient } from '@/lib/pusher-client';

export function usePusherChannel(channelName: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const channel = pusherClient.subscribe(channelName);

    channel.bind('order-created', (data: unknown) => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    });

    channel.bind('order-updated', (data: unknown) => {
      queryClient.setQueryData(['orders', (data as { id: string }).id], data);
    });

    return () => {
      channel.unbind_all();
      pusherClient.unsubscribe(channelName);
    };
  }, [channelName, queryClient]);
}
```

---

### 8.7 Оптимизация поллинга (адаптивный, exponential backoff)

Даже при наличии push-технологий, поллинг остаётся важным fallback и основным подходом для
простых сценариев. Оптимизация критична для снижения нагрузки на сервер.

#### Адаптивный поллинг с TanStack Query

```typescript
// hooks/use-adaptive-polling.ts
'use client';

import { useQuery } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import { api } from '@/lib/api-client';

interface UseAdaptivePollingOptions {
  queryKey: readonly string[];
  url: string;
  minInterval: number; // мс — минимальный интервал (активная вкладка)
  maxInterval: number; // мс — максимальный интервал (при отсутствии изменений)
  backoffFactor: number; // множитель увеличения интервала
}

export function useAdaptivePolling<T>({
  queryKey,
  url,
  minInterval = 3_000,
  maxInterval = 60_000,
  backoffFactor = 1.5,
}: UseAdaptivePollingOptions) {
  const [interval, setInterval] = useState(minInterval);
  const [unchangedCount, setUnchangedCount] = useState(0);

  const adjustInterval = useCallback(
    (hasChanges: boolean) => {
      if (hasChanges) {
        // Данные изменились — сбрасываем на минимальный интервал
        setInterval(minInterval);
        setUnchangedCount(0);
      } else {
        // Данные не изменились — увеличиваем интервал (exponential backoff)
        setUnchangedCount((prev) => prev + 1);
        setInterval((prev) => Math.min(prev * backoffFactor, maxInterval));
      }
    },
    [minInterval, maxInterval, backoffFactor],
  );

  let previousDataHash: string | null = null;

  return useQuery({
    queryKey,
    queryFn: async () => {
      const data = await api.get<T>(url);
      const currentHash = JSON.stringify(data);
      const hasChanges = previousDataHash !== null && previousDataHash !== currentHash;
      previousDataHash = currentHash;
      adjustInterval(hasChanges);
      return data;
    },
    refetchInterval: () => {
      // Добавляем jitter для предотвращения "стада" (thundering herd)
      const jitter = Math.random() * interval * 0.2; // ±20%
      return interval + jitter;
    },
    // Не поллим когда вкладка неактивна
    refetchIntervalInBackground: false,
    // Refetch при фокусе окна
    refetchOnWindowFocus: true,
  });
}
```

#### Стратегия: выбор интервала поллинга

```
┌─────────────────────────────────────────────────┐
│            ДЕРЕВО РЕШЕНИЙ ПОЛЛИНГА              │
├─────────────────────────────────────────────────┤
│                                                 │
│  Данные меняются каждую секунду?                │
│  ├── Да → SSE или WebSocket (не поллинг)        │
│  └── Нет ↓                                      │
│                                                 │
│  Пользователь активно смотрит на данные?        │
│  ├── Да (фокус) → 3-10с интервал                │
│  └── Нет (фон) → отключить поллинг              │
│                                                 │
│  Данные часто меняются (каталог, биржа)?        │
│  ├── Да → Адаптивный: 5с → 15с → 30с            │
│  └── Нет ↓                                      │
│                                                 │
│  Данные редко меняются (настройки, профиль)?    │
│  ├── Да → 60с+ или invalidate после мутаций     │
│  └── Нет → 15-30с базовый интервал              │
│                                                 │
│  Много одновременных пользователей?             │
│  ├── Да → Jitter обязателен (+10-20% random)    │
│  └── Нет → Фиксированный интервал достаточен    │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

### 8.8 Optimistic Updates для real-time ощущения

React 19 `useOptimistic` в сочетании с Server Actions и TanStack Query создаёт мгновенный отклик UI.

#### useOptimistic + Server Action

```typescript
// components/message-list.tsx
'use client';

import { useOptimistic, useTransition } from 'react';
import { sendMessage } from '@/app/actions/chat';

interface Message {
  id: string;
  text: string;
  userId: string;
  createdAt: string;
  pending?: boolean;
}

export function MessageList({ messages }: { messages: Message[] }) {
  const [isPending, startTransition] = useTransition();

  const [optimisticMessages, addOptimistic] = useOptimistic(
    messages,
    (state: Message[], newMessage: Message) => [
      ...state,
      { ...newMessage, pending: true },
    ],
  );

  const handleSend = (text: string) => {
    const tempMessage: Message = {
      id: `temp-${Date.now()}`,
      text,
      userId: 'current-user',
      createdAt: new Date().toISOString(),
      pending: true,
    };

    startTransition(async () => {
      // Мгновенно показываем сообщение (optimistic)
      addOptimistic(tempMessage);
      // Server Action отправляет на сервер + revalidatePath
      await sendMessage(text);
      // После завершения — React заменит optimistic на реальные данные
    });
  };

  return (
    <div>
      {optimisticMessages.map((msg) => (
        <div key={msg.id} className={msg.pending ? 'opacity-60' : ''}>
          {msg.text}
          {msg.pending && <span className="text-xs text-gray-400"> sending...</span>}
        </div>
      ))}
    </div>
  );
}
```

#### TanStack Query optimistic mutation

```typescript
// hooks/use-toggle-like.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

interface Post {
  id: string;
  title: string;
  likes: number;
  isLiked: boolean;
}

export function useToggleLike(postId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post(`/posts/${postId}/like`),

    // Optimistic update: обновляем UI до ответа сервера
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['posts', postId] });
      const previous = queryClient.getQueryData<Post>(['posts', postId]);

      queryClient.setQueryData<Post>(['posts', postId], (old) =>
        old
          ? {
              ...old,
              likes: old.isLiked ? old.likes - 1 : old.likes + 1,
              isLiked: !old.isLiked,
            }
          : old,
      );

      return { previous };
    },

    // Rollback при ошибке
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['posts', postId], context.previous);
      }
    },

    // Всегда синхронизируем с сервером
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['posts', postId] });
    },
  });
}
```

---

### 8.9 Стоимостной анализ real-time сервисов

| Сервис                   | Free tier               | ~1K пользователей | ~10K пользователей   | ~100K пользователей |
| ------------------------ | ----------------------- | ----------------- | -------------------- | ------------------- |
| **SSE (свой сервер)**    | --                      | $10-20/mo (VPS)   | $50-100/mo (2-3 VPS) | $200-500/mo (k8s)   |
| **Pusher**               | 100 conn / 200K msg/day | ~$49/mo           | ~$299/mo             | $999+/mo            |
| **Ably**                 | 200 conn / 6M msg/mo    | ~$29-99/mo        | ~$199-399/mo         | Индивидуально       |
| **Soketi (self-hosted)** | Безлимит                | $5-10/mo (VPS)    | $30-60/mo (кластер)  | $100-300/mo (k8s)   |
| **PartyKit**             | 1K conn бесплатно       | ~$25/mo           | ~$100/mo             | Индивидуально       |
| **Socket.IO (свой)**     | --                      | $10-20/mo (VPS)   | $50-100/mo (+ Redis) | $200-500/mo (k8s)   |

**Формула оценки:** для managed-сервисов стоимость растёт с количеством одновременных подключений
и объёмом сообщений. Для self-hosted — с требованиями к серверам и инфраструктуре (Redis, мониторинг).

---

### 8.10 Пути миграции между технологиями

```
┌────────────────────────────────────────────────────────────────────────┐
│                    ПУТИ МИГРАЦИИ REAL-TIME                             │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ЭТАП 1 (MVP / Простые уведомления):                                   │
│  ┌─────────────────┐                                                   │
│  │  Polling         │  refetchInterval: 5000                           │
│  │  (TanStack Query)│  Минимум кода, работает везде                    │
│  └────────┬────────┘                                                   │
│           │ Нужен push (задержка неприемлема)                          │
│           ▼                                                            │
│  ЭТАП 2 (Push-уведомления):                                            │
│  ┌─────────────────┐                                                   │
│  │  SSE             │  Route Handler + EventSource                     │
│  │  (Server-Sent)   │  + TanStack Query invalidation                   │
│  └────────┬────────┘                                                   │
│           │ Нужна двусторонняя связь (чат, совместное ред.)            │
│           ▼                                                            │
│  ЭТАП 3a (Быстрый старт):      ЭТАП 3b (Полный контроль):              │
│  ┌─────────────────┐           ┌─────────────────┐                     │
│  │  Pusher / Ably  │           │  Socket.IO      │                     │
│  │  (Managed)      │           │  (свой сервер)  │                     │
│  └────────┬────────┘           └────────┬────────┘                     │
│           │ Расходы растут              │ Нужна коллаборация           │
│           ▼                             ▼                              │
│  ЭТАП 4 (Оптимизация):         ┌─────────────────┐                     │
│  ┌──────────────────┐          │  PartyKit       │                     │
│  │  Soketi          │          │  (edge + CRDT)  │                     │
│  │  (self-hosted    │          └─────────────────┘                     │
│  │   Pusher-замена) │                                                  │
│  └──────────────────┘                                                  │
│                                                                        │
│  ПРИНЦИП: начинайте с простого, мигрируйте по необходимости            │
│  Pusher → Soketi: замена SDK не нужна (совместимый протокол)           │
│  Polling → SSE: замена refetchInterval на useSSE + invalidation        │
│  SSE → WebSocket: добавление ws-сервера, SSE остаётся для уведомлений  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Рекомендуемый стек

### 9.1 Дерево решений по state management

```
┌────────────────────────────────────────────────────────────────────────┐
│               ДЕРЕВО РЕШЕНИЙ: STATE MANAGEMENT                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─ Какие данные нужно хранить?                                        │
│  │                                                                     │
│  ├─► СЕРВЕРНЫЕ данные (API, БД, внешние сервисы)                       │
│  │   │                                                                 │
│  │   ├─ Нужны DevTools + optimistic updates + prefetch?                │
│  │   │  ├── Да → TanStack Query v5                                     │
│  │   │  └── Нет, проект маленький → SWR v2 (4 KB)                      │
│  │   │                                                                 │
│  │   ├─ Данные только для Server Components?                           │
│  │   │  └── Да → async/await + fetch (0 KB, встроенный)                │
│  │   │                                                                 │
│  │   └─ Real-time обновления?                                          │
│  │      ├── Уведомления → SSE + TanStack Query invalidation            │
│  │      ├── Чат/коллаборация → WebSocket / PartyKit                    │
│  │      └── Дашборд → Adaptive polling (TanStack Query)                │
│  │                                                                     │
│  ├─► КЛИЕНТСКИЕ данные (UI state, формы, настройки)                    │
│  │   │                                                                 │
│  │   ├─ Глобальный стейт (auth, theme, sidebar)?                       │
│  │   │  ├── Простой проект / 1-5 разработчиков → Zustand v5            │
│  │   │  ├── Много независимых атомов (фильтры, UI) → Jotai v2          │
│  │   │  └── Большая команда (10+), строгие стандарты → Redux Toolkit   │
│  │   │                                                                 │
│  │   ├─ Локальный стейт компонента?                                    │
│  │   │  └── useState / useReducer (всегда предпочтительно)             │
│  │   │                                                                 │
│  │   ├─ Стейт доступен за пределами React?                             │
│  │   │  └── Zustand (единственный выбор — getState() вне компонентов)  │
│  │   │                                                                 │
│  │   └─ Нужна персистенция (localStorage)?                             │
│  │      ├── Zustand → persist middleware                               │
│  │      └── Jotai → atomWithStorage                                    │
│  │                                                                     │
│  └─► ФОРМЫ (ввод, валидация, отправка)                                 │
│      │                                                                 │
│      ├─ Сложные формы (много полей, вложенные массивы)?                │
│      │  └── React Hook Form + Zod                                      │
│      │                                                                 │
│      ├─ Простая форма (1-3 поля)?                                      │
│      │  └── useActionState + Zod (встроенный React 19)                 │
│      │                                                                 │
│      └─ Нужен optimistic UI при отправке?                              │
│         └── useOptimistic + Server Action                              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Краткая таблица решений

| Сценарий                             | Решение                     | Bundle impact |
| ------------------------------------ | --------------------------- | ------------- |
| Один компонент, простой стейт        | `useState` / `useReducer`   | 0 KB          |
| Серверные данные, кэш, мутации       | TanStack Query v5           | ~13 KB        |
| Серверные данные, минимальный бандл  | SWR v2                      | ~4 KB         |
| Серверные данные в Server Components | `fetch()` + ISR             | 0 KB          |
| Глобальный клиентский стейт          | Zustand v5                  | ~1.2 KB       |
| Множество независимых атомов         | Jotai v2                    | ~2.1 KB       |
| Строгие паттерны, большая команда    | Redux Toolkit               | ~13.8 KB      |
| Сложные формы                        | React Hook Form + Zod       | ~10 KB        |
| Простые формы                        | `useActionState` (React 19) | 0 KB          |
| Обмен данными: Server → Client       | props / `HydrationBoundary` | 0 KB          |
| Context для DI (не для стейта)       | React Context               | 0 KB          |

---

### 9.2 Полная enterprise-архитектура

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ENTERPRISE NEXT.JS ARCHITECTURE                         │
│                          (App Router 2025-2026)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─── CDN / EDGE ──────────────────────────────────────────────────────┐    │
│  │  Vercel Edge Network / Cloudflare                                   │    │
│  │  ├── Static assets (ISR pages, images, fonts)                       │    │
│  │  ├── Edge Middleware (auth check, geo-redirect, A/B test)           │    │
│  │  └── Cache-Control headers (stale-while-revalidate)                 │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                           │
│  ┌─── NEXT.JS APP (SSR/RSC) ────┴──────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  ┌── Server Layer ──────────────────────────────────────────────┐   │    │
│  │  │  Server Components (async/await, 0 KB JS)                    │   │    │
│  │  │  ├── page.tsx — fetch + prefetchQuery + HydrationBoundary    │   │    │
│  │  │  ├── layout.tsx — auth session, shared data                  │   │    │
│  │  │  └── loading.tsx — Suspense fallback (streaming)             │   │    │
│  │  │                                                              │   │    │
│  │  │  Server Actions ('use server') — BFF proxy                   │   │    │
│  │  │  ├── Мутации → proxy к бэкенд-сервисам + Zod-валидация       │   │    │
│  │  │  ├── AI streaming (AI SDK 6 streamText)                      │   │    │
│  │  │  └── createSafeAction — auth + validation wrapper            │   │    │
│  │  │                                                              │   │    │
│  │  │  Route Handlers (app/api/)                                   │   │    │
│  │  │  ├── SSE endpoints (text/event-stream)                       │   │    │
│  │  │  ├── Webhook receivers (Stripe, GitHub)                      │   │    │
│  │  │  └── File upload / download endpoints                        │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  │                                                                     │    │
│  │  ┌── Client Layer ─────────────────────────────────────────────┐    │    │
│  │  │  Client Components ('use client')                           │    │    │
│  │  │  ├── TanStack Query (server state, cache, mutations)        │    │    │
│  │  │  ├── Zustand (client state: auth, UI, settings)             │    │    │
│  │  │  ├── React Hook Form + Zod (forms)                          │    │    │
│  │  │  ├── useSSE / useSocket / useParty (real-time)              │    │    │
│  │  │  └── useOptimistic + useTransition (instant feedback)       │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                 │                                           │
│  ┌─── BFF / PROXY LAYER ────────┴──────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  Data Access Layer (lib/data/) — proxy к бэкенд-сервисам            │    │
│  │  ├── Auth checks + token forwarding (не middleware!)                │    │
│  │  ├── HTTP-клиент (ky / ofetch) → бэкенд-сервисы                     │    │
│  │  └── Zod schemas — shared validation (client + server)              │    │
│  │                                                                     │    │
│  │  ┌── Backend Services ─────┐  ┌── Real-time Infra ──────────────┐   │    │
│  │  │  Auth Service           │  │  Redis / Valkey (Pub/Sub, cache)│   │    │
│  │  │  Products Service       │  │  SSE Route Handlers             │   │    │
│  │  │  Users Service          │  │  Socket.IO / PartyKit (ws)      │   │    │
│  │  │  (DB, ORM — на их       │  │                                 │   │    │
│  │  │   стороне)              │  │                                 │   │    │
│  │  └─────────────────────────┘  └─────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─── OBSERVABILITY ───────────────────────────────────────────────────┐    │
│  │  OpenTelemetry (traces, spans)                                      │    │
│  │  ├── Sentry (errors + performance)                                  │    │
│  │  ├── Vercel Analytics / Speed Insights (Web Vitals)                 │    │
│  │  └── Custom metrics (TanStack Query timing, SSE health)             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 9.3 Финальный стек с альтернативами

| Слой                  | Основной выбор              | Альтернатива 1       | Альтернатива 2          | Когда альтернатива                                              |
| --------------------- | --------------------------- | -------------------- | ----------------------- | --------------------------------------------------------------- |
| **Server state**      | TanStack Query v5           | SWR v2               | fetch (встроен)         | SWR: минимальный бандл; fetch: только RSC                       |
| **Client state**      | Zustand v5                  | Jotai v2             | Redux Toolkit           | Jotai: атомарный UI; RTK: команда 10+                           |
| **Формы**             | React Hook Form + Zod       | useActionState + Zod | Conform                 | useActionState: простые формы; Conform: progressive enhancement |
| **HTTP-клиент**       | ky                          | ofetch (unjs)        | fetch (нативный)        | ofetch: edge runtimes; fetch: без зависимостей                  |
| **Мутации**           | Server Actions (proxy) + TQ | tRPC                 | GraphQL (urql)          | tRPC: fullstack TS monorepo; GraphQL: сложные связи данных      |
| **Кэширование**       | ISR + TQ cache              | fetch cache + tags   | SWR cache               | По сложности приложения                                         |
| **Real-time (push)**  | SSE + TQ invalidation       | Pusher / Ably        | PartyKit                | Pusher: быстрый старт; PartyKit: коллаборация                   |
| **Real-time (bidir)** | Socket.IO + Redis           | PartyKit             | Ably                    | PartyKit: edge + CRDT; Ably: managed + global                   |
| **AI streaming**      | Vercel AI SDK 6             | Raw ReadableStream   | LangChain.js            | Raw: без vendor lock-in; LangChain: complex chains              |
| **Валидация**         | Zod                         | Valibot              | ArkType                 | Valibot: tree-shakeable (~1 KB); ArkType: performance           |
| **Auth**              | Auth.js (NextAuth v5)       | Clerk                | Lucia                   | Clerk: managed + UI; Lucia: lightweight                         |
| **Стилизация**        | Tailwind CSS v4             | CSS Modules          | Panda CSS               | CSS Modules: без runtime; Panda: type-safe tokens               |
| **Мониторинг**        | Sentry + Vercel Analytics   | Datadog              | OpenTelemetry + Grafana | Datadog: enterprise APM; OTel: self-hosted                      |

> **Примечание:** ORM (Drizzle, Prisma) — ответственность бэкенд-сервисов, не Next.js.
> Next.js работает как BFF/proxy через HTTP-клиент (ky/ofetch) к бэкенд API.

---

### 9.4 Мониторинг производительности

Мониторинг и Web Vitals — см. `04-dx-tooling.md` (Часть 3) и `05-auth-security-performance.md` (Часть 2, секция 4).

---

### 9.5 Архитектура проекта

```
src/
├── app/                              # Next.js App Router
│   ├── (auth)/                       # Route group: аутентификация
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/                  # Route group: основное приложение
│   │   ├── layout.tsx                # Sidebar, nav (Server Component)
│   │   ├── page.tsx                  # Dashboard home
│   │   ├── orders/
│   │   │   ├── page.tsx              # SSR + prefetchQuery
│   │   │   ├── [id]/page.tsx         # Dynamic route
│   │   │   └── loading.tsx           # Streaming skeleton
│   │   └── settings/page.tsx
│   ├── api/                          # Route Handlers
│   │   ├── events/route.ts           # SSE endpoint
│   │   ├── webhooks/stripe/route.ts  # Webhook receiver
│   │   ├── pusher/auth/route.ts      # Pusher auth endpoint
│   │   └── metrics/route.ts          # Custom metrics receiver
│   ├── actions/                      # Server Actions
│   │   ├── orders.ts
│   │   ├── chat.ts                   # AI streaming
│   │   └── auth.ts
│   ├── providers.tsx                 # QueryClient, Theme, WebVitals
│   └── layout.tsx                    # Root layout
├── components/
│   ├── ui/                           # Базовые (Button, Input, Modal, Card)
│   ├── features/                     # Бизнес-компоненты (OrderTable, ChatWindow)
│   └── providers/                    # Context providers
├── hooks/
│   ├── queries/                      # TanStack Query hooks (use-orders.ts)
│   ├── mutations/                    # TanStack Mutation hooks (use-create-order.ts)
│   ├── use-sse.ts                    # SSE подключение
│   ├── use-socket.ts                 # WebSocket подключение
│   ├── use-party.ts                  # PartyKit подключение
│   └── use-adaptive-polling.ts       # Адаптивный поллинг
├── stores/                           # Zustand stores
│   ├── auth-store.ts                 # Аутентификация
│   ├── ui-store.ts                   # UI state (sidebar, modals)
│   └── settings-store.ts            # Пользовательские настройки
├── lib/
│   ├── api-client.ts                 # ky instance — клиентский HTTP (браузер)
│   ├── api-server.ts                 # ky instance — серверный HTTP (BFF proxy к бэкенду)
│   ├── query-client.ts               # TanStack Query client factory
│   ├── pusher-server.ts              # Pusher server instance
│   ├── pusher-client.ts              # Pusher client instance
│   ├── schemas/                      # Zod-схемы (клиент + сервер)
│   │   ├── order.ts
│   │   ├── user.ts
│   │   └── common.ts
│   ├── safe-action.ts                # Обёртка безопасных Server Actions
│   └── data/                         # Data Access Layer (proxy к бэкенд-сервисам)
│       ├── orders.ts                 # Auth check + proxy к orders-сервису
│       └── users.ts                  # Auth check + proxy к users-сервису
├── types/                            # Общие TypeScript типы
│   ├── api.ts                        # API response types
│   └── domain.ts                     # Domain entities
└── instrumentation.ts                # OpenTelemetry setup
```

---

## Источники

- [Server-Sent Events don't work in Next API routes — GitHub Discussion](https://github.com/vercel/next.js/discussions/48427)
- [Real-Time Notifications with SSE in Next.js — Pedro Alonso](https://www.pedroalonso.net/blog/sse-nextjs-real-time-notifications/)
- [Fixing Slow SSE Streaming in Next.js and Vercel — Medium](https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996)
- [Using SSE to stream LLM responses in Next.js — Upstash Blog](https://upstash.com/blog/sse-streaming-llm-responses)
- [How to use with Next.js — Socket.IO](https://socket.io/how-to/use-with-nextjs)
- [How to Handle WebSocket in Next.js — OneUptime](https://oneuptime.com/blog/post/2026-01-24-nextjs-websocket-handling/view)
- [PartyKit — Real-time Multiplayer Platform](https://www.partykit.io/)
- [Add PartyKit to a Next.js app — PartyKit Docs](https://docs.partykit.io/tutorials/add-partykit-to-a-nextjs-app/)
- [Pusher vs Ably vs PubNub Comparison 2026 — index.dev](https://www.index.dev/skill-vs-skill/pusher-vs-ably-vs-pubnub)
- [Ably vs Pusher 2026 — Ably](https://ably.com/compare/ably-vs-pusher)
- [Pusher pricing 2025 — Ably](https://ably.com/topic/pusher-pricing)
- [Soketi — Open-source WebSocket server — GitHub](https://github.com/soketi/soketi)
- [TanStack Query: Query Invalidation — Docs](https://tanstack.com/query/v5/docs/framework/react/guides/query-invalidation)
- [TanStack Query: Optimistic Updates — Docs](https://tanstack.com/query/v5/docs/react/guides/optimistic-updates)
- [Vercel AI SDK 6: Streaming Chat — DigitalApplied](https://www.digitalapplied.com/blog/vercel-ai-sdk-6-streaming-chat-nextjs-guide)
- [Real-time AI in Next.js: Streaming with Vercel AI SDK — LogRocket](https://blog.logrocket.com/nextjs-vercel-ai-sdk-streaming/)
- [AI SDK: Stream Text — Cookbook](https://ai-sdk.dev/cookbook/next/stream-text)
- [useOptimistic — React Docs](https://react.dev/reference/react/useOptimistic)
- [Implement Optimistic UI in Next.js — egghead.io](https://egghead.io/lessons/next-js-implement-optimistic-ui-with-the-react-useoptimistic-hook-in-next-js)
- [Modern Full Stack Architecture Using Next.js 15+ — SoftwareMill](https://softwaremill.com/modern-full-stack-application-architecture-using-next-js-15/)
- [React Stack Patterns 2026 — patterns.dev](https://www.patterns.dev/react/react-2026/)
- [Next.js State Management: Zustand vs Jotai — BetterLink Blog](https://eastondev.com/blog/en/posts/dev/20251219-nextjs-state-management/)
- [React State Management in 2025 — developerway.com](https://www.developerway.com/posts/react-state-management-2025)
- [State Management Trends in React 2025 — Makers Den](https://makersden.io/blog/react-state-management-in-2025)
- [OpenTelemetry Guide — Next.js Docs](https://nextjs.org/docs/app/guides/open-telemetry)
- [Next.js Performance Optimisation 2025 — Pagepro](https://pagepro.co/blog/nextjs-performance-optimization-in-9-steps/)
- [Sentry for Next.js — Monitoring](https://sentry.io/for/nextjs/)
- [Scaling Responsibly: Smarter API Requests with React Query — Medium](https://medium.com/@karamarkonikolina/scaling-responsibly-smarter-api-requests-with-react-query-apollo-client-part-2-4cef233454a3)
- [Server-Sent Events — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [EventSource Automatic Reconnection — javascript.info](https://javascript.info/server-sent-events)
- [Reconnecting EventSource — GitHub (fanout)](https://github.com/fanout/reconnecting-eventsource)
