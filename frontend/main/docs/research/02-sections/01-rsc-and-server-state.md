# React Server Components и Управление серверным состоянием (TanStack Query v5)

> Глубокое исследование паттернов композиции RSC, Suspense-стриминга и enterprise-настройки TanStack Query v5 с Next.js App Router.

---

## Содержание

1. [Server Components vs Client Components: глубокий разбор](#1-server-components-vs-client-components)
2. [Паттерны композиции RSC](#2-паттерны-композиции-rsc)
3. [Streaming и Suspense: параллельная загрузка данных](#3-streaming-и-suspense)
4. [React.use() и серверные промисы](#4-reactuse-и-серверные-промисы)
5. [TanStack Query v5: полная настройка для Next.js App Router](#5-tanstack-query-v5-полная-настройка)
6. [Query Key Factory: управление ключами](#6-query-key-factory)
7. [Prefetch-паттерны: prefetchQuery vs ensureQueryData](#7-prefetch-паттерны)
8. [Optimistic Updates: enterprise-паттерны](#8-optimistic-updates)
9. [Infinite Scroll и курсорная пагинация](#9-infinite-scroll-и-курсорная-пагинация)
10. [Обработка ошибок с TanStack Query](#10-обработка-ошибок)
11. [TanStack Query vs SWR: сравнение и бенчмарки](#11-tanstack-query-vs-swr)

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
  const products = await db.products.findMany();

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
  // Прямой запрос к БД — возможен только в Server Component
  const product = await db.products.findUnique({
    where: { id: productId },
    include: { reviews: true, category: true },
  });

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

### Сравнительная таблица (2025-2026)

| Характеристика                  | TanStack Query v5                           | SWR v2                                  |
| ------------------------------- | ------------------------------------------- | --------------------------------------- |
| **Bundle size (gzip)**          | ~13.4 KB                                    | ~4.2 KB                                 |
| **Еженедельные загрузки (npm)** | ~12.3M                                      | ~7.7M                                   |
| **Рост за год**                 | +60%                                        | +15%                                    |
| **DevTools**                    | Встроенные (отличные)                       | Community plugin                        |
| **Mutations**                   | Полная поддержка + optimistic updates       | Базовая (`mutate()`)                    |
| **Infinite scroll**             | `useInfiniteQuery` (встроенный)             | `useSWRInfinite`                        |
| **Prefetching / SSR**           | `HydrationBoundary` + `prefetchQuery`       | `SWRConfig fallback`                    |
| **TypeScript**                  | Автовывод типов из queryFn                  | Требует ручных generics                 |
| **Retry**                       | Встроенный (3 попытки, exponential backoff) | Ручная настройка                        |
| **Query cancellation**          | AbortSignal автоматически                   | Ручная реализация                       |
| **Offline support**             | Встроенный                                  | Нет                                     |
| **Garbage collection**          | gcTime (настраиваемый)                      | Нет (ручная очистка)                    |
| **Parallel queries**            | `useQueries`                                | Нет эквивалента                         |
| **Suspense**                    | `useSuspenseQuery` (стабильный)             | `{ suspense: true }` (экспериментально) |
| **Streaming SSR**               | `@tanstack/react-query-next-experimental`   | Нет                                     |

### Бенчмарки памяти

| Метрика                 | TanStack Query v5 | SWR v2           |
| ----------------------- | ----------------- | ---------------- |
| **Idle**                | 3.2 MB            | 2.1 MB           |
| **100 запросов в кэше** | 6.1 MB (+2.9 MB)  | 3.8 MB (+1.7 MB) |
| **Overhead на запрос**  | ~29 KB            | ~17 KB           |

SWR расходует меньше памяти за счёт упрощённой архитектуры (нет mutation queue, нет offline persistence). Для приложений с менее чем 50 активными запросами разница несущественна.

### Когда выбрать SWR

- Простые приложения с read-only данными
- Максимальная оптимизация bundle size (4 KB vs 13 KB)
- Проект в экосистеме Vercel (SWR — их продукт)
- Не нужны мутации, optimistic updates, infinite queries

### Когда выбрать TanStack Query

- Enterprise-приложения с мутациями
- Нужны DevTools для отладки кэша
- Optimistic updates и сложные инвалидации
- Offline-first приложения
- SSR с streaming и Suspense
- Infinite scroll / курсорная пагинация
- Команда более 3 разработчиков (DevTools экономят часы)

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
