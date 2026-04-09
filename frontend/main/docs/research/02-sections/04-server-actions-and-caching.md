# 6-7. Server Actions и стратегии кэширования (углубленное исследование)

> Расширенный анализ Server Actions, Data Access Layer, React 19 хуков и многоуровневого кэширования в Next.js 15+.

---

## 6.1 Server Actions: архитектура безопасности

### Data Access Layer (DAL)

Рекомендованный Vercel паттерн — авторизация на уровне доступа к данным, а не на уровне маршрутов:

```typescript
// lib/dal.ts (Data Access Layer)
import 'server-only';
import { cache } from 'react';
import { getSession } from '@/lib/auth';

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
// lib/data/products.ts
import 'server-only';
import { requireAuth, requireRole } from '@/lib/dal';

export async function getProducts() {
  await requireAuth(); // Проверка auth на уровне данных
  return db.product.findMany();
}

export async function deleteProduct(id: string) {
  await requireRole('admin'); // Только admin
  return db.product.delete({ where: { id } });
}
```

```typescript
// app/actions/products.ts
'use server';

import { z } from 'zod';
import { revalidateTag } from 'next/cache';
import { deleteProduct } from '@/lib/data/products';

const deleteSchema = z.object({ id: z.string().uuid() });

export async function deleteProductAction(input: unknown) {
  const { id } = deleteSchema.parse(input);
  await deleteProduct(id); // DAL проверяет auth + role
  revalidateTag('products');
  return { success: true };
}
```

**Почему DAL, а не middleware?**

- Middleware можно обойти (CVE-2025-29927 — обход через заголовок `x-middleware-subrequest`)
- DAL проверяет авторизацию максимально близко к данным
- `cache()` из React дедуплицирует вызовы в одном request

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

  await db.post.create({
    data: { ...parsed.data, authorId: user.id },
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

// unstable_cache — для non-fetch данных (DB queries, computations)
const getCachedProducts = unstable_cache(
  async (categoryId: string) => {
    return db.product.findMany({
      where: { categoryId },
      include: { category: true },
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

| Критерий           | `fetch` cache        | `unstable_cache`       | TanStack Query                |
| ------------------ | -------------------- | ---------------------- | ----------------------------- |
| Среда              | Server               | Server                 | Client (+ SSR prefetch)       |
| Источник           | HTTP endpoints       | Любые async функции    | HTTP endpoints                |
| Tag invalidation   | Да                   | Да                     | Через `invalidateQueries`     |
| Persistence        | Data Cache (disk)    | Data Cache (disk)      | In-memory (browser)           |
| DevTools           | Нет                  | Нет                    | Да (отличные)                 |
| Optimistic updates | Нет                  | Нет                    | Да                            |
| **Когда**          | Fetch от внешних API | DB queries, вычисления | Клиентские данные, интерактив |

---

## 7.4 Многоуровневый кэш: полная картина

```
Запрос пользователя
        │
        ▼
┌─ CDN / Edge Cache ──────────────────┐
│  Cache-Control: s-maxage=300        │
│  stale-while-revalidate=600         │
│  HIT → мгновенный ответ            │
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
│  HIT → рендер с кэшированными      │
│        данными                      │
└──────────┬──────────────────────────┘
           │ MISS
           ▼
┌─ Origin (API / Database) ───────────┐
│  Реальный запрос к источнику        │
│  Результат кэшируется на всех       │
│  уровнях выше                       │
└─────────────────────────────────────┘

        На клиенте:
┌─ TanStack Query Cache ─────────────┐
│  In-memory, staleTime: 60_000      │
│  Background refetch при фокусе     │
│  Optimistic updates при мутациях   │
└─────────────────────────────────────┘
```

---

## 7.5 Стратегия для enterprise

| Сценарий            | Серверный кэш          | Клиентский кэш                              | Инвалидация                      |
| ------------------- | ---------------------- | ------------------------------------------- | -------------------------------- |
| **Маркетинг/блог**  | ISR `revalidate: 3600` | Нет (SSG)                                   | Webhook `revalidateTag`          |
| **Каталог товаров** | ISR `revalidate: 300`  | TQ `staleTime: 60s`                         | Server Action + `revalidateTag`  |
| **Dashboard**       | No cache               | TQ `staleTime: 30s`, `refetchInterval: 30s` | `invalidateQueries` при мутации  |
| **Профиль**         | `unstable_cache` tags  | TQ `staleTime: 5min`                        | Server Action + tag + invalidate |
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
