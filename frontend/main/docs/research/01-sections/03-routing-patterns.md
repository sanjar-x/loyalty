# 3. Паттерны маршрутизации Next.js App Router (углубленное исследование)

> Детальное руководство по всем паттернам маршрутизации Next.js 15+/16 для enterprise-проектов.
> Дата: апрель 2026.

---

## 3.1 Route Groups -- организация без влияния на URL

Route Groups (папки в круглых скобках) позволяют логически группировать маршруты,
назначать разные layout-ы и изолировать зоны ответственности в команде --
при этом скобки **не попадают в URL**.

### Типичная структура enterprise-приложения

```
src/app/
├── (marketing)/              # Публичные страницы
│   ├── layout.tsx            # Минимальный layout: header + footer
│   ├── page.tsx              # /
│   ├── about/page.tsx        # /about
│   └── pricing/page.tsx      # /pricing
│
├── (dashboard)/              # Защищенные страницы
│   ├── layout.tsx            # Layout с sidebar + topbar + auth guard
│   ├── dashboard/page.tsx    # /dashboard
│   ├── settings/page.tsx     # /settings
│   └── users/
│       ├── page.tsx          # /users
│       └── [id]/page.tsx     # /users/:id
│
├── (auth)/                   # Аутентификация
│   ├── layout.tsx            # Центрированный layout без навигации
│   ├── login/page.tsx        # /login
│   └── register/page.tsx     # /register
│
└── (api)/                    # API-маршруты (можно группировать отдельно)
    └── api/
        ├── webhooks/route.ts
        └── v1/
            └── users/route.ts
```

### Код layout для каждой группы

**`(marketing)/layout.tsx`** -- публичный layout:

```tsx
// src/app/(marketing)/layout.tsx
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header variant="marketing" />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
```

**`(dashboard)/layout.tsx`** -- защищенный layout с sidebar:

```tsx
// src/app/(dashboard)/layout.tsx
import { redirect } from 'next/navigation';
import { auth } from '@/lib/auth';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect('/login');

  return (
    <div className="flex h-screen">
      <Sidebar user={session.user} />
      <div className="flex flex-1 flex-col">
        <Topbar user={session.user} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
```

**`(auth)/layout.tsx`** -- минимальный layout для аутентификации:

```tsx
// src/app/(auth)/layout.tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
```

### Правила и ограничения Route Groups

- Две группы **не могут** генерировать одинаковый URL-сегмент (например, `(marketing)/about` и `(shop)/about` -- конфликт).
- Если нужна **главная страница** (`/`) в нескольких группах -- она должна быть только в одной.
- Route groups можно вкладывать: `(dashboard)/(analytics)/reports/page.tsx`.
- Рекомендация: **не более 3-4 групп** на корневом уровне, иначе навигация по проекту усложняется.

---

## 3.2 Parallel Routes -- независимые секции страницы

Parallel Routes используют конвенцию `@folder` для одновременного рендера нескольких
независимых секций на одной странице. Каждый слот автоматически передается как prop
в родительский `layout.tsx`.

### Файловая структура

```
src/app/(dashboard)/dashboard/
├── layout.tsx              # Собирает слоты: children, analytics, activity
├── page.tsx                # Основной контент (/dashboard)
├── @analytics/
│   ├── page.tsx            # Виджет аналитики
│   ├── loading.tsx         # Скелетон только для аналитики
│   ├── error.tsx           # Ошибка только для аналитики
│   └── default.tsx         # Fallback при навигации в другие суб-маршруты
└── @activity/
    ├── page.tsx            # Лента активности
    ├── loading.tsx         # Скелетон только для ленты
    └── default.tsx         # Fallback
```

### Код layout с параллельными слотами

```tsx
// src/app/(dashboard)/dashboard/layout.tsx
export default function DashboardLayout({
  children,
  analytics,
  activity,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  activity: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      {/* Основной контент (children = page.tsx) */}
      <section>{children}</section>

      {/* Параллельные секции в grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border bg-white p-4 shadow-sm">{analytics}</div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">{activity}</div>
      </div>
    </div>
  );
}
```

### Код слота `@analytics/page.tsx`

```tsx
// src/app/(dashboard)/dashboard/@analytics/page.tsx
import { getAnalyticsData } from '@/services/analytics.service';
import { AnalyticsChart } from '@/features/analytics/components/analytics-chart';

export default async function AnalyticsSlot() {
  const data = await getAnalyticsData();

  return (
    <div>
      <h3 className="mb-4 text-lg font-semibold">Аналитика</h3>
      <AnalyticsChart data={data} />
    </div>
  );
}
```

### Код `default.tsx` -- обязательный fallback

```tsx
// src/app/(dashboard)/dashboard/@analytics/default.tsx
export default function AnalyticsDefault() {
  // Возвращается при навигации в суб-маршруты, где у слота нет совпадения.
  // Можно вернуть null, скелетон или последнее состояние.
  return null;
}
```

**Важно:** без `default.tsx` Next.js вернет 404 при навигации в суб-маршруты,
если у параллельного слота нет соответствующего сегмента.

### Условный рендеринг через Parallel Routes

Parallel Routes позволяют рендерить разный контент в зависимости от роли пользователя:

```tsx
// src/app/(dashboard)/dashboard/layout.tsx
import { auth } from '@/lib/auth';

export default async function DashboardLayout({
  children,
  admin,
  user,
}: {
  children: React.ReactNode;
  admin: React.ReactNode;
  user: React.ReactNode;
}) {
  const session = await auth();
  const isAdmin = session?.user.role === 'admin';

  return (
    <div>
      {children}
      {isAdmin ? admin : user}
    </div>
  );
}
```

### Независимые loading/error states

Каждый слот стримится на клиент **независимо** -- если аналитика загружается 3 секунды,
а лента активности -- 200мс, пользователь увидит ленту сразу, а для аналитики
будет показан `@analytics/loading.tsx`. Это ключевое преимущество перед обычным
разделением на компоненты.

```tsx
// src/app/(dashboard)/dashboard/@analytics/loading.tsx
export default function AnalyticsLoading() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-4 w-1/3 rounded bg-gray-200" />
      <div className="h-48 rounded bg-gray-200" />
    </div>
  );
}
```

```tsx
// src/app/(dashboard)/dashboard/@analytics/error.tsx
'use client';

export default function AnalyticsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-lg bg-red-50 p-4 text-red-800">
      <p>Не удалось загрузить аналитику</p>
      <button onClick={reset} className="mt-2 text-sm underline">
        Попробовать снова
      </button>
    </div>
  );
}
```

---

## 3.3 Intercepting Routes -- модальные окна с URL

Intercepting Routes позволяют перехватывать навигацию и отображать маршрут в контексте
текущей страницы (обычно как модальное окно), сохраняя при этом реальный URL.
При прямом переходе по ссылке или обновлении страницы отображается полная страница.

### Конвенции перехвата

| Конвенция  | Описание                 | Пример                                                  |
| ---------- | ------------------------ | ------------------------------------------------------- |
| `(.)`      | Тот же уровень (sibling) | `(.)photo` перехватывает `photo` рядом                  |
| `(..)`     | На уровень выше (parent) | `(..)product` перехватывает `product` в родителе        |
| `(..)(..)` | На два уровня выше       | Редко используется                                      |
| `(...)`    | От корня приложения      | `(...)product` перехватывает `/product` из любого места |

**Важно:** конвенция основана на **сегментах маршрута**, а не на файловой системе.
Route groups `(group)` не считаются сегментами.

### Полная реализация модального окна товара

Структура файлов:

```
src/app/
├── layout.tsx                          # Root layout с @modal слотом
├── products/
│   ├── page.tsx                        # Список товаров (/products)
│   └── [id]/
│       └── page.tsx                    # Полная страница товара (/products/123)
├── @modal/
│   ├── default.tsx                     # Пустой fallback (модаль не открыта)
│   └── (.)products/[id]/
│       └── page.tsx                    # Перехваченный маршрут -> модальное окно
```

**`src/app/layout.tsx`** -- корневой layout, принимающий слот `@modal`:

```tsx
// src/app/layout.tsx
import type { Metadata } from 'next';
import '@/app/globals.css';

export const metadata: Metadata = {
  title: 'My Store',
};

export default function RootLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>
        {children}
        {modal}
      </body>
    </html>
  );
}
```

**`src/app/@modal/default.tsx`** -- пустой fallback:

```tsx
// src/app/@modal/default.tsx
export default function ModalDefault() {
  return null;
}
```

**`src/app/products/page.tsx`** -- список товаров:

```tsx
// src/app/products/page.tsx
import Link from 'next/link';
import { getProducts } from '@/services/products.service';

export default async function ProductsPage() {
  const products = await getProducts();

  return (
    <div className="grid grid-cols-3 gap-4 p-8">
      {products.map((product) => (
        <Link
          key={product.id}
          href={`/products/${product.id}`}
          className="rounded-lg border p-4 transition hover:shadow-md"
        >
          <img src={product.image} alt={product.name} className="h-48 w-full object-cover" />
          <h2 className="mt-2 font-semibold">{product.name}</h2>
          <p className="text-gray-600">${product.price}</p>
        </Link>
      ))}
    </div>
  );
}
```

**`src/app/@modal/(.)products/[id]/page.tsx`** -- перехваченный маршрут (модальное окно):

```tsx
// src/app/@modal/(.)products/[id]/page.tsx
import { getProduct } from '@/services/products.service';
import { Modal } from '@/components/ui/modal';

export default async function ProductModal({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);

  return (
    <Modal>
      <div className="flex gap-6">
        <img src={product.image} alt={product.name} className="h-64 w-64 rounded-lg object-cover" />
        <div>
          <h2 className="text-2xl font-bold">{product.name}</h2>
          <p className="mt-2 text-gray-600">{product.description}</p>
          <p className="mt-4 text-3xl font-bold">${product.price}</p>
          <button className="mt-4 rounded bg-blue-600 px-6 py-2 text-white">В корзину</button>
        </div>
      </div>
    </Modal>
  );
}
```

**`src/components/ui/modal.tsx`** -- переиспользуемый компонент модального окна:

```tsx
// src/components/ui/modal.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useCallback } from 'react';

export function Modal({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const handleClose = useCallback(() => {
    router.back();
  }, [router]);

  // Закрытие по Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={handleClose}
    >
      <div
        className="relative max-h-[90vh] w-full max-w-2xl overflow-auto rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          aria-label="Закрыть"
        >
          X
        </button>
        {children}
      </div>
    </div>
  );
}
```

**`src/app/products/[id]/page.tsx`** -- полная страница товара (при прямом переходе):

```tsx
// src/app/products/[id]/page.tsx
import { getProduct } from '@/services/products.service';
import { notFound } from 'next/navigation';

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);

  if (!product) notFound();

  return (
    <div className="mx-auto max-w-4xl p-8">
      <img src={product.image} alt={product.name} className="h-96 w-full rounded-xl object-cover" />
      <h1 className="mt-6 text-3xl font-bold">{product.name}</h1>
      <p className="mt-4 text-gray-600">{product.description}</p>
      <p className="mt-6 text-4xl font-bold">${product.price}</p>
    </div>
  );
}
```

### Как это работает

1. **Клик по ссылке** (client-side навигация) -> Next.js перехватывает маршрут -> показывает `@modal/(.)products/[id]/page.tsx` как модальное окно поверх текущей страницы. URL обновляется на `/products/123`.
2. **Прямой переход** (ввод URL / обновление страницы) -> рендерится полная страница `products/[id]/page.tsx`.
3. **Закрытие модали** -> `router.back()` возвращает на предыдущий URL, модаль демонтируется.

### Ограничения и подводные камни

- Intercepting Routes работают **только при client-side навигации** через `<Link>` или `router.push`.
- Используйте `router.back()` для закрытия модали, **не** `router.push("/products")` -- это создаст новую запись в истории.
- `default.tsx` в слоте `@modal` **обязателен**, иначе будет 404.
- Осторожно с вложенными route groups -- конвенция `(..)` считает сегменты маршрута, не файловой системы.

---

## 3.4 Динамические маршруты: `[slug]`, `[...slug]`, `[[...slug]]`

### Сравнительная таблица

| Тип                | Синтаксис     | Совпадает                       | НЕ совпадает            | `params`                                    |
| ------------------ | ------------- | ------------------------------- | ----------------------- | ------------------------------------------- |
| Динамический       | `[id]`        | `/products/123`                 | `/products/123/edit`    | `{ id: "123" }`                             |
| Catch-all          | `[...slug]`   | `/docs/a`, `/docs/a/b/c`        | `/docs` (без сегментов) | `{ slug: ["a","b","c"] }`                   |
| Optional catch-all | `[[...slug]]` | `/docs`, `/docs/a`, `/docs/a/b` | -- (совпадает со всем)  | `{ slug: undefined }` или `{ slug: ["a"] }` |

### Примеры использования

**Динамический сегмент** -- для CRUD-страниц:

```tsx
// src/app/users/[id]/page.tsx
export default async function UserPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; // Next.js 15+: params -- это Promise
  // ...
}
```

**Catch-all** -- для документации с произвольной вложенностью:

```tsx
// src/app/docs/[...slug]/page.tsx
export default async function DocsPage({ params }: { params: Promise<{ slug: string[] }> }) {
  const { slug } = await params;
  // /docs/getting-started/installation -> slug = ["getting-started", "installation"]
  const doc = await getDocByPath(slug.join('/'));
  // ...
}
```

**Optional catch-all** -- для фильтров каталога:

```tsx
// src/app/shop/[[...filters]]/page.tsx
export default async function ShopPage({ params }: { params: Promise<{ filters?: string[] }> }) {
  const { filters } = await params;
  // /shop             -> filters = undefined (показать все)
  // /shop/electronics -> filters = ["electronics"]
  // /shop/electronics/phones -> filters = ["electronics", "phones"]
  const products = await getProducts(filters);
  // ...
}
```

**Важно (Next.js 15+):** `params` и `searchParams` теперь являются `Promise` и требуют `await`.
Это breaking change по сравнению с Next.js 14.

---

## 3.5 loading.tsx, error.tsx, not-found.tsx -- стратегия boundary-файлов

### Иерархия вложенности компонентов

Next.js автоматически оборачивает файлы маршрута в определенную иерархию:

```
<Layout>
  <Template>
    <ErrorBoundary fallback={<Error />}>
      <Suspense fallback={<Loading />}>
        <ErrorBoundary fallback={<NotFound />}>
          <Page />
        </ErrorBoundary>
      </Suspense>
    </ErrorBoundary>
  </Template>
</Layout>
```

**Ключевое правило:** `error.tsx` **не ловит** ошибки из `layout.tsx` того же сегмента --
для этого нужно поместить `error.tsx` в **родительский** сегмент.

### Стратегия размещения

```
src/app/
├── layout.tsx              # Root layout
├── global-error.tsx        # Ловит ошибки из root layout (единственный способ)
├── not-found.tsx           # Глобальная 404 (URL не совпал ни с одним маршрутом)
├── error.tsx               # Глобальный error boundary
├── loading.tsx             # Глобальный loading (осторожно -- может мигать)
│
├── (dashboard)/
│   ├── layout.tsx          # Dashboard layout
│   ├── error.tsx           # Ловит ошибки из dashboard/* но НЕ из этого layout
│   ├── loading.tsx         # Loading для dashboard-секции
│   │
│   ├── dashboard/
│   │   ├── page.tsx
│   │   └── loading.tsx     # Гранулярный loading для /dashboard
│   │
│   └── users/
│       ├── page.tsx        # /users
│       ├── loading.tsx     # Loading для /users
│       ├── error.tsx       # Error только для /users
│       ├── not-found.tsx   # 404 при вызове notFound()
│       └── [id]/
│           ├── page.tsx    # /users/:id
│           ├── loading.tsx # Loading для страницы пользователя
│           └── not-found.tsx # 404 для конкретного пользователя
```

### Код `global-error.tsx`

```tsx
// src/app/global-error.tsx
'use client'; // Обязательно client component

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    // global-error ДОЛЖЕН включать теги <html> и <body>,
    // так как он полностью заменяет root layout при ошибке
    <html>
      <body>
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Что-то пошло не так</h1>
            <p className="mt-2 text-gray-600">{error.digest && `Код ошибки: ${error.digest}`}</p>
            <button onClick={reset} className="mt-4 rounded bg-blue-600 px-4 py-2 text-white">
              Попробовать снова
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
```

### Код `not-found.tsx` с вызовом `notFound()`

```tsx
// src/app/users/[id]/page.tsx
import { notFound } from 'next/navigation';
import { getUserById } from '@/services/users.service';

export default async function UserPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await getUserById(id);

  if (!user) notFound(); // Триггерит ближайший not-found.tsx

  return <UserProfile user={user} />;
}
```

```tsx
// src/app/users/[id]/not-found.tsx
import Link from 'next/link';

export default function UserNotFound() {
  return (
    <div className="p-8 text-center">
      <h2 className="text-xl font-semibold">Пользователь не найден</h2>
      <p className="mt-2 text-gray-600">Проверьте правильность ссылки или вернитесь к списку.</p>
      <Link href="/users" className="mt-4 inline-block text-blue-600 underline">
        К списку пользователей
      </Link>
    </div>
  );
}
```

### Рекомендации по boundary-стратегии

| Уровень             | loading.tsx                          | error.tsx                      | not-found.tsx                 |
| ------------------- | ------------------------------------ | ------------------------------ | ----------------------------- |
| Root (`app/`)       | Осторожно (мигает на каждый переход) | Да                             | Да (глобальная 404)           |
| Route Group         | Да (если все страницы группы похожи) | Да                             | Нет (обычно не нужен)         |
| Конкретная страница | Да (кастомный скелетон)              | Если нужна кастомная обработка | Если есть `notFound()` в page |
| Parallel Route слот | Да (независимый loading)             | Да (изолированная ошибка)      | Редко                         |

---

## 3.6 template.tsx vs layout.tsx -- когда использовать template

### Ключевое различие

| Характеристика         | `layout.tsx`                                | `template.tsx`                            |
| ---------------------- | ------------------------------------------- | ----------------------------------------- |
| **Перемонтирование**   | НЕ перемонтируется при навигации            | Перемонтируется при КАЖДОЙ навигации      |
| **Состояние**          | Сохраняется между страницами                | Сбрасывается на каждой странице           |
| **useEffect**          | Вызывается один раз при первом монтировании | Вызывается при каждой навигации           |
| **DOM**                | Переиспользуется                            | Пересоздается                             |
| **Производительность** | Лучше (нет повторных рендеров)              | Хуже (полный remount)                     |
| **Позиция в иерархии** | Внешний wrapper                             | Внутри layout, снаружи error/loading/page |

### Иерархия: layout оборачивает template

```
<Layout>           ← Не перемонтируется
  <Template>       ← Перемонтируется при навигации
    <ErrorBoundary>
      <Suspense>
        <Page />
      </Suspense>
    </ErrorBoundary>
  </Template>
</Layout>
```

Можно использовать и layout, и template одновременно -- layout будет внешней оболочкой,
а template -- внутренней, перемонтируемой при смене страниц.

### Когда использовать template.tsx

**1. Трекинг просмотров страниц:**

```tsx
// src/app/(dashboard)/template.tsx
'use client';

import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { trackPageView } from '@/lib/analytics';

export default function DashboardTemplate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    trackPageView(pathname);
  }, [pathname]);

  return <>{children}</>;
}
```

**2. Анимации входа/выхода страницы:**

```tsx
// src/app/template.tsx
'use client';

import { useEffect, useRef } from 'react';

export default function AnimatedTemplate({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Анимация появления при каждой навигации
    ref.current?.animate(
      [
        { opacity: 0, transform: 'translateY(10px)' },
        { opacity: 1, transform: 'translateY(0)' },
      ],
      { duration: 300, easing: 'ease-out', fill: 'forwards' },
    );
  }, []);

  return <div ref={ref}>{children}</div>;
}
```

**3. Сброс форм при навигации:**

```tsx
// src/app/(auth)/template.tsx
'use client';

export default function AuthTemplate({ children }: { children: React.ReactNode }) {
  // Форма внутри будет сброшена при каждой навигации
  // между /login и /register, так как template перемонтируется
  return <div className="animate-fadeIn">{children}</div>;
}
```

### Когда НЕ использовать template.tsx

- Если нужно сохранить состояние (открытый sidebar, scroll position) -- используйте `layout.tsx`.
- Если нет специфичной логики на `useEffect`/`useState` -- `layout.tsx` производительнее.
- Если template нужен только для обертки CSS -- используйте `layout.tsx` с CSS-классами.

---

## 3.7 Middleware -- паттерны для enterprise

`middleware.ts` выполняется на Edge Runtime **до** каждого запроса. Это единственная точка
перехвата для auth guards, i18n, редиректов и A/B-тестирования.

### Базовая структура middleware

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Логика middleware
  return NextResponse.next();
}

// Matcher: middleware вызывается ТОЛЬКО для указанных путей
export const config = {
  matcher: [
    // Исключаем статику, изображения, favicon и API-маршруты
    '/((?!_next/static|_next/image|favicon.ico|api/webhooks).*)',
  ],
};
```

### Паттерн 1: Auth Guard с JWT-верификацией

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

const PUBLIC_PATHS = ['/', '/about', '/pricing', '/login', '/register'];
const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET!);

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Публичные страницы -- пропускаем
  if (PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith('/api/public'))) {
    return NextResponse.next();
  }

  const token = request.cookies.get('session-token')?.value;

  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  try {
    const { payload } = await jwtVerify(token, JWT_SECRET);

    // Передаем данные пользователя в headers для использования в Server Components
    const response = NextResponse.next();
    response.headers.set('x-user-id', String(payload.sub));
    response.headers.set('x-user-role', String(payload.role || 'user'));
    return response;
  } catch {
    // Невалидный/просроченный токен
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('error', 'session-expired');
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### Паттерн 2: i18n-маршрутизация

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const SUPPORTED_LOCALES = ['en', 'ru', 'uz'];
const DEFAULT_LOCALE = 'ru';

function getLocaleFromHeaders(request: NextRequest): string {
  const acceptLang = request.headers.get('accept-language') || '';
  const preferred = acceptLang.split(',')[0]?.split('-')[0]?.toLowerCase();
  return SUPPORTED_LOCALES.includes(preferred || '') ? preferred! : DEFAULT_LOCALE;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Проверяем, есть ли уже локаль в URL
  const hasLocale = SUPPORTED_LOCALES.some(
    (locale) => pathname.startsWith(`/${locale}/`) || pathname === `/${locale}`,
  );

  if (hasLocale) return NextResponse.next();

  // Определяем локаль из cookie или headers
  const locale = request.cookies.get('NEXT_LOCALE')?.value || getLocaleFromHeaders(request);

  // Перенаправляем на URL с локалью
  const url = request.nextUrl.clone();
  url.pathname = `/${locale}${pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
};
```

### Паттерн 3: Комбинированный middleware (цепочка)

В реальных проектах middleware обычно совмещает несколько задач.
Рекомендуется разбивать логику на функции и вызывать их последовательно:

```ts
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Отдельные middleware-функции
import { withAuth } from '@/lib/middleware/auth';
import { withI18n } from '@/lib/middleware/i18n';
import { withRateLimit } from '@/lib/middleware/rate-limit';

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Rate limiting для API
  if (pathname.startsWith('/api')) {
    const rateLimitResponse = await withRateLimit(request);
    if (rateLimitResponse) return rateLimitResponse; // 429 если превышен лимит
  }

  // 2. i18n для всех страниц (кроме API)
  if (!pathname.startsWith('/api')) {
    const i18nResponse = withI18n(request);
    if (i18nResponse) return i18nResponse; // redirect на URL с локалью
  }

  // 3. Auth для защищенных маршрутов
  if (pathname.startsWith('/dashboard') || pathname.startsWith('/settings')) {
    const authResponse = await withAuth(request);
    if (authResponse) return authResponse; // redirect на /login
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### Ограничения middleware

- Выполняется на **Edge Runtime**: нет доступа к Node.js API (fs, crypto.createHash и т.д.).
- **Один файл** `middleware.ts` на проект (в корне или `src/`).
- Нельзя напрямую обращаться к базе данных -- только через fetch к API.
- Для JWT-верификации используйте `jose` (совместима с Edge Runtime), не `jsonwebtoken`.

---

## 3.8 Route Handlers vs Server Actions -- что когда использовать

### Сравнительная таблица

| Критерий                    | Server Actions                         | Route Handlers                          |
| --------------------------- | -------------------------------------- | --------------------------------------- |
| **Вызов**                   | Из React-компонентов как функции       | Любой HTTP-клиент                       |
| **HTTP-методы**             | Только POST (автоматически)            | GET, POST, PUT, DELETE, PATCH           |
| **Type safety**             | Автоматическая (вызов функции)         | Ручной парсинг Request                  |
| **Кеширование**             | Нет                                    | GET-запросы кешируемы                   |
| **Progressive enhancement** | Да (формы работают без JS)             | Нет                                     |
| **Файл**                    | `actions.ts` или inline `"use server"` | `route.ts`                              |
| **Лучше для**               | Мутации из UI                          | Вебхуки, внешние API, мобильные клиенты |

### Дерево решений

```
Кто вызывает?
├── Внешний клиент (вебхук, мобильное приложение, 3rd party)
│   └── -> Route Handler
├── React-компонент
│   ├── Мутация (создание, обновление, удаление)?
│   │   └── -> Server Action
│   ├── Чтение данных?
│   │   ├── Server Component -> Fetch напрямую в компоненте
│   │   └── Client Component -> Route Handler с кешированием
│   └── Загрузка файлов?
│       └── -> Server Action (FormData) или Route Handler
└── Нужен полный контроль HTTP (headers, status codes, streaming)?
    └── -> Route Handler
```

### Пример Server Action

```ts
// src/features/users/actions/update-user.ts
'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { updateUser } from '@/services/users.service';

const UpdateUserSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
});

export async function updateUserAction(formData: FormData) {
  const parsed = UpdateUserSchema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
  });

  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors };
  }

  await updateUser(parsed.data);
  revalidatePath('/settings');
  return { success: true };
}
```

### Пример Route Handler

```ts
// src/app/api/webhooks/stripe/route.ts
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(request: Request) {
  const body = await request.text();
  const headersList = await headers();
  const signature = headersList.get('stripe-signature')!;

  try {
    const event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!,
    );

    switch (event.type) {
      case 'checkout.session.completed':
        // Обработка успешной оплаты
        break;
      case 'customer.subscription.deleted':
        // Обработка отмены подписки
        break;
    }

    return NextResponse.json({ received: true });
  } catch (err) {
    return NextResponse.json({ error: 'Webhook signature verification failed' }, { status: 400 });
  }
}
```

### Правило 90/10

В типичном enterprise-проекте ~90% серверного кода -- это Server Actions (мутации из UI),
и ~10% -- Route Handlers (вебхуки, публичные API, интеграции).

---

## 3.9 Partial Prerendering (PPR) -- маршрутизация и производительность

PPR (Partial Prerendering) -- стратегия рендеринга, позволяющая комбинировать
статический и динамический контент **в одном маршруте**.

### Как включить (Next.js 15)

```ts
// next.config.ts
import type { NextConfig } from 'next';

const config: NextConfig = {
  experimental: {
    ppr: 'incremental', // Включаем PPR по-маршрутно
  },
};

export default config;
```

```tsx
// src/app/products/page.tsx
export const experimental_ppr = true; // Opt-in для этого маршрута

export default async function ProductsPage() {
  return (
    <div>
      {/* Статическая оболочка -- отправляется мгновенно */}
      <h1>Каталог товаров</h1>
      <FilterBar />

      {/* Динамический контент -- стримится после */}
      <Suspense fallback={<ProductsSkeleton />}>
        <ProductList />
      </Suspense>
    </div>
  );
}
```

### Эволюция в Next.js 16

В Next.js 16 (октябрь 2025) PPR стал стабильным и был переименован:

- Вместо `experimental.ppr` используется `cacheComponents: true`
- Вместо `experimental_ppr` в маршруте -- Cache Components API

---

## 3.10 Блок-схема: выбор паттерна маршрутизации

```
Вопрос                                          Паттерн
───────────────────────────────────────────────────────────────

Нужны разные layout-ы для групп страниц?
  └── Да ────────────────────────────────────> Route Groups

Нужно несколько независимых секций на одной
странице с отдельными loading/error?
  └── Да ────────────────────────────────────> Parallel Routes

Нужно модальное окно с сохранением URL,
которое при прямом переходе -- полная страница?
  └── Да ────────────────────────────────────> Intercepting Routes
                                               + Parallel Routes

Разный контент в зависимости от роли
пользователя (admin/user)?
  └── Да ────────────────────────────────────> Parallel Routes
                                               (условный рендеринг)

Нужен auth guard / i18n / редирект
до рендера страницы?
  └── Да ────────────────────────────────────> Middleware

Маршрут с произвольной глубиной вложенности
(/docs/a/b/c)?
  └── Да ────────────────────────────────────> Catch-all [...slug]

Маршрут может иметь или не иметь сегменты
(/shop или /shop/electronics)?
  └── Да ────────────────────────────────────> Optional catch-all
                                               [[...slug]]

Нужно выполнять useEffect / сбрасывать
состояние при каждой навигации?
  └── Да ────────────────────────────────────> template.tsx

Нужен статический shell + динамический
контент в одном маршруте?
  └── Да ────────────────────────────────────> PPR + Suspense

Для всего остального                          Обычные вложенные
                                               layout + page
```

---

## 3.11 Рекомендации по производительности вложенных layout-ов

### Проблема глубокой вложенности

Каждый layout -- это React-компонент, оборачивающий дочерние. При глубине 5+ уровней:

```
RootLayout > (dashboard)/layout > users/layout > [id]/layout > settings/layout > page
```

Проблемы:

1. **Водопад запросов:** если каждый layout делает async-запрос, они выполняются последовательно (layout рендерится сверху вниз).
2. **Сложность отладки:** ошибку в 5-м уровне сложно отследить.
3. **Негибкость:** layout нельзя отменить/переопределить для одной страницы.

### Решения

**Ограничивайте вложенность -- максимум 3-4 уровня:**

```
RootLayout              # Уровень 1: HTML, providers, глобальные стили
  └── (group)/layout    # Уровень 2: Sidebar, auth guard
      └── section/layout # Уровень 3: Секционный header
          └── page       # Страница
```

**Параллельный data fetching вместо водопада:**

```tsx
// ПЛОХО: водопад -- layout ждет данные перед рендером children
export default async function DashboardLayout({ children }) {
  const user = await getUser(); // 200ms
  const notifications = await getNotifications(); // 300ms
  // Total: 500ms sequential

  return <div>{children}</div>;
}

// ХОРОШО: параллельные запросы
export default async function DashboardLayout({ children }) {
  const [user, notifications] = await Promise.all([getUser(), getNotifications()]);
  // Total: 300ms (parallel)

  return <div>{children}</div>;
}
```

**Выносите динамические данные в Client Components с Suspense:**

```tsx
// ХОРОШО: layout статичный, данные загружаются в Suspense-границах
export default function DashboardLayout({ children }) {
  return (
    <div className="flex">
      <Sidebar />
      <main>
        <Suspense fallback={<TopbarSkeleton />}>
          <Topbar /> {/* Server Component с async data */}
        </Suspense>
        {children}
      </main>
    </div>
  );
}
```

**Делайте layout максимально "тонким":**

Layout должен содержать только структуру (grid, flex) и общие компоненты (sidebar, header).
Бизнес-логика, data fetching и тяжелые вычисления -- в `page.tsx` или отдельных компонентах
с собственными Suspense-границами.

---

## Источники

- [Next.js: Route Groups](https://nextjs.org/docs/app/api-reference/file-conventions/route-groups)
- [Next.js: Parallel Routes](https://nextjs.org/docs/app/api-reference/file-conventions/parallel-routes)
- [Next.js: Intercepting Routes](https://nextjs.org/docs/app/api-reference/file-conventions/intercepting-routes)
- [Next.js: Dynamic Segments](https://nextjs.org/docs/app/api-reference/file-conventions/dynamic-routes)
- [Next.js: template.js](https://nextjs.org/docs/app/api-reference/file-conventions/template)
- [Next.js: Error Handling](https://nextjs.org/docs/app/getting-started/error-handling)
- [Next.js: Partial Prerendering](https://nextjs.org/docs/15/app/getting-started/partial-prerendering)
- [Next.js: Middleware](https://nextjs.org/docs/pages/building-your-application/routing/middleware)
- [Mastering NextJS Parallel Routes (AndiSmith)](https://www.andismith.com/blogs/2025/02/mastering-nextjs-parallel-routes)
- [Server Actions vs Route Handlers (MakerKit)](https://makerkit.dev/blog/tutorials/server-actions-vs-route-handlers)
- [8 Middleware Patterns That Scale (Medium)](https://medium.com/@ThinkingLoop/8-next-js-middleware-patterns-that-scale-across-regions-568dab5f6c38)
- [Next.js Intercepting Routes Guide (Medium)](https://itsankitbhusal.medium.com/next-js-intercepting-routes-a-complete-implementation-guide-2025-what-is-the-intercepting-route-a9571888ac2e)
- [BetterLink Blog: Advanced Routing](https://eastondev.com/blog/en/posts/dev/20251218-nextjs-advanced-routing/)
- [Next.js App Router Patterns 2026 (DEV Community)](https://dev.to/teguh_coding/nextjs-app-router-the-patterns-that-actually-matter-in-2026-146)
- [Next.js 15/16 Features Migration Guide (Jishu Labs)](https://jishulabs.com/blog/nextjs-15-16-features-migration-guide-2026)
- [Next.js Layouts vs Templates (Builder.io)](https://www.builder.io/blog/nextjs-14-layouts-templates)
