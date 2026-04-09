# 2. Архитектурные паттерны фронтенда: глубокое сравнение

> Расширенное исследование архитектурных подходов для Next.js 15+ (App Router).
> Дата: апрель 2026.

---

## 2.0 Введение: зачем нужна архитектура на фронтенде?

Архитектура фронтенда -- это не про папки. Это про **управление сложностью**: когда кодовая
база переваливает за 100 файлов, отсутствие чётких границ превращает разработку в лотерею --
любое изменение может сломать что угодно. Правильная архитектура обеспечивает:

- **Предсказуемость** -- разработчик знает, где искать код и куда класть новый.
- **Параллельную работу** -- команды не блокируют друг друга.
- **Тестируемость** -- бизнес-логика отделена от фреймворка.
- **Эволюционность** -- систему можно менять по частям, а не переписывать.

В этом разделе сравниваются **пять архитектурных подходов**, применимых к Next.js:

| #   | Подход                         | Ключевая идея                          |
| --- | ------------------------------ | -------------------------------------- |
| 1   | Layer-based (слоёная)          | Разделение по техническому типу        |
| 2   | Feature-based (фиче-модульная) | Разделение по бизнес-домену            |
| 3   | Feature-Sliced Design (FSD)    | Стандартизованные слои + слайсы        |
| 4   | Clean / Hexagonal Architecture | Порты, адаптеры, инверсия зависимостей |
| 5   | Vertical Slice Architecture    | Каждый запрос — самостоятельный срез   |

---

## 2.1 Подход 1: Layer-based (слоёная архитектура)

### Суть

Код группируется по **техническому типу** файла: компоненты, хуки, сервисы, типы --
каждая категория в своей папке.

### Структура

```
src/
├── components/          # Все компоненты приложения
│   ├── Button.tsx
│   ├── LoginForm.tsx
│   ├── UserCard.tsx
│   └── OrderTable.tsx
├── hooks/               # Все хуки
│   ├── useAuth.ts
│   ├── useOrders.ts
│   └── useUsers.ts
├── services/            # Все API-вызовы
│   ├── auth.service.ts
│   ├── orders.service.ts
│   └── users.service.ts
├── types/               # Все типы
│   ├── auth.types.ts
│   ├── order.types.ts
│   └── user.types.ts
├── utils/               # Все утилиты
└── app/                 # Next.js маршруты
```

### Диаграмма зависимостей

```
┌─────────────────────────────────────────────────┐
│                   app/ (routes)                  │
│  Импортирует всё: components, hooks, services    │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
  ┌───────────┐ ┌─────────┐ ┌──────────┐
  │components/│ │  hooks/  │ │services/ │
  └─────┬─────┘ └────┬────┘ └─────┬────┘
        │             │            │
        └──────┬──────┘            │
               ▼                   ▼
          ┌─────────┐        ┌──────────┐
          │  types/ │◄───────│  utils/  │
          └─────────┘        └──────────┘
```

**Проблема:** зависимости хаотичны. `LoginForm` импортирует `useAuth`, `auth.service`,
`auth.types` -- разработчик прыгает по 4+ папкам для одной фичи.

### Плюсы и минусы

| Плюс                            | Минус                                   |
| ------------------------------- | --------------------------------------- |
| Интуитивно для новичков         | Не масштабируется (50+ файлов = хаос)   |
| Быстрый старт                   | Работа над фичей = прыжки по 4-5 папкам |
| Привычен большинству            | Частые конфликты мержей в команде       |
| Не требует обучения архитектуре | Невозможно определить границы фичи      |
| Хорошо для прототипов           | Нет контроля над зависимостями          |

### Когда использовать

- Прототипы и MVP (< 20 файлов)
- Проекты на одного разработчика
- Внутренние инструменты с коротким жизненным циклом

---

## 2.2 Подход 2: Feature-based (фиче-модульная архитектура)

### Суть

Код группируется по **бизнес-домену**. Каждая фича -- самодостаточный модуль,
содержащий компоненты, хуки, сервисы, типы и тесты. Структура папок
**«кричит»** о назначении приложения (Screaming Architecture по Роберту Мартину),
а не о фреймворке.

### Структура

```
src/
├── features/
│   ├── auth/                    # Всё про аутентификацию
│   │   ├── components/
│   │   │   ├── login-form.tsx
│   │   │   └── user-menu.tsx
│   │   ├── hooks/
│   │   │   └── use-auth.ts
│   │   ├── services/
│   │   │   └── auth.service.ts
│   │   ├── types/
│   │   │   └── auth.types.ts
│   │   └── index.ts             # Public API фичи
│   │
│   ├── orders/                  # Всё про заказы
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── index.ts
│   │
│   └── users/                   # Всё про пользователей
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── types/
│       └── index.ts
│
├── components/                  # Общие UI-компоненты (Button, Input)
├── lib/                         # Общие утилиты
├── hooks/                       # Общие хуки (useDebounce, useMediaQuery)
└── app/                         # Next.js маршруты
```

### Диаграмма зависимостей

```
┌────────────────────────────────────────────────────────┐
│                    app/ (routes)                        │
│  Каждая страница импортирует из features/ и components/ │
└───────────┬──────────────┬──────────────┬──────────────┘
            │              │              │
            ▼              ▼              ▼
     ┌─────────────┐ ┌──────────┐ ┌─────────────┐
     │ features/   │ │features/ │ │  features/  │
     │    auth/    │ │  orders/ │ │   users/    │
     │ ┌─────────┐ │ │          │ │             │
     │ │  comps  │ │ │          │ │             │
     │ │  hooks  │ │ │          │ │             │
     │ │services │ │ │          │ │             │
     │ │  types  │ │ │          │ │             │
     │ └─────────┘ │ │          │ │             │
     └──────┬──────┘ └─────┬────┘ └──────┬──────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
              ┌────────────────────────┐
              │  components/ lib/      │
              │  hooks/ types/ config/ │
              │   (общие ресурсы)      │
              └────────────────────────┘
```

**Правило:** фичи могут импортировать из общих ресурсов, но **не друг из друга**
напрямую (либо через явный public API).

### Плюсы и минусы

| Плюс                                | Минус                                          |
| ----------------------------------- | ---------------------------------------------- |
| Структура отражает бизнес-домен     | Требует дисциплины в определении границ        |
| Фича = зона ответственности команды | Дублирование кода между фичами                 |
| Минимум конфликтов мержей           | Непонятно, куда класть cross-feature логику    |
| Удаление фичи = удаление папки      | Нет стандарта: каждая команда делает по-своему |
| Высокая cohesion внутри фичи        | Требуется onboarding по архитектуре            |

### Пример кода: фича Auth

```typescript
// src/features/auth/types/auth.types.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

```typescript
// src/features/auth/services/auth.service.ts
import type { LoginCredentials, User } from '../types/auth.types';

export async function login(credentials: LoginCredentials): Promise<User> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  if (!response.ok) throw new Error('Login failed');
  return response.json();
}

export async function logout(): Promise<void> {
  await fetch('/api/auth/logout', { method: 'POST' });
}

export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch('/api/auth/me');
  if (!response.ok) return null;
  return response.json();
}
```

```typescript
// src/features/auth/hooks/use-auth.ts
'use client';

import { useState, useEffect } from 'react';
import * as authService from '../services/auth.service';
import type { AuthState, LoginCredentials } from '../types/auth.types';

export function useAuth(): AuthState & {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
} {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    authService.getCurrentUser().then((user) => {
      setState({ user, isAuthenticated: !!user, isLoading: false });
    });
  }, []);

  return {
    ...state,
    login: async (credentials) => {
      const user = await authService.login(credentials);
      setState({ user, isAuthenticated: true, isLoading: false });
    },
    logout: async () => {
      await authService.logout();
      setState({ user: null, isAuthenticated: false, isLoading: false });
    },
  };
}
```

```typescript
// src/features/auth/components/login-form.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '../hooks/use-auth';

export function LoginForm() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login({ email, password });
  };

  return (
    <form onSubmit={handleSubmit}>
      <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <Button type="submit">Sign In</Button>
    </form>
  );
}
```

```typescript
// src/features/auth/index.ts  -- Public API
export { LoginForm } from './components/login-form';
export { useAuth } from './hooks/use-auth';
export type { User, LoginCredentials, AuthState } from './types/auth.types';
```

### Когда использовать

- Средние и крупные проекты (30-200+ файлов)
- Команды из 3-10 разработчиков
- Продукты с чётко выделяемыми бизнес-доменами

---

## 2.3 Подход 3: Feature-Sliced Design (FSD)

### Суть

FSD -- это **стандартизованная методология** (не фреймворк), предлагающая фиксированный
набор слоёв с однонаправленными зависимостями. Каждый слой делится на **слайсы**
(по бизнес-домену), а слайсы -- на **сегменты** (по техническому назначению).

### Структура (адаптация для Next.js App Router)

Ключевой конфликт: Next.js использует `app/` для маршрутизации, а FSD использует `app/`
для инициализации. Решение -- разнести их:

```
project-root/
├── app/                         # Next.js App Router (маршруты)
│   ├── layout.tsx               # Оборачивает в FSD-провайдеры из src/app/
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx         # Тонкий: реэкспорт из src/pages/
│   └── (dashboard)/
│       └── dashboard/
│           └── page.tsx
│
├── pages/                       # Пустая папка (блокирует Pages Router)
│
└── src/                         # FSD-слои
    ├── app/                     # Слой: инициализация, провайдеры
    │   └── providers/
    │       ├── theme-provider.tsx
    │       └── query-provider.tsx
    │
    ├── pages/                   # Слой: композиция страниц
    │   ├── home/
    │   │   └── ui.tsx
    │   ├── login/
    │   │   └── ui.tsx
    │   └── dashboard/
    │       └── ui.tsx
    │
    ├── widgets/                 # Слой: составные блоки UI
    │   ├── header/
    │   │   ├── ui/
    │   │   │   └── header.tsx
    │   │   └── index.ts
    │   └── sidebar/
    │       ├── ui/
    │       │   └── sidebar.tsx
    │       └── index.ts
    │
    ├── features/                # Слой: пользовательские сценарии
    │   ├── auth/
    │   │   ├── login/
    │   │   │   ├── ui/
    │   │   │   │   └── login-form.tsx
    │   │   │   ├── model/
    │   │   │   │   └── use-login.ts
    │   │   │   ├── api/
    │   │   │   │   └── login.action.ts
    │   │   │   └── index.ts
    │   │   └── logout/
    │   │       ├── ui/
    │   │       │   └── logout-button.tsx
    │   │       └── index.ts
    │   └── cart/
    │       └── add-to-cart/
    │           ├── ui/
    │           ├── model/
    │           ├── api/
    │           └── index.ts
    │
    ├── entities/                # Слой: бизнес-сущности
    │   ├── user/
    │   │   ├── ui/
    │   │   │   └── user-card.tsx
    │   │   ├── model/
    │   │   │   └── user.types.ts
    │   │   ├── api/
    │   │   │   └── user.queries.ts
    │   │   └── index.ts
    │   └── order/
    │       ├── ui/
    │       ├── model/
    │       ├── api/
    │       └── index.ts
    │
    └── shared/                  # Слой: общие ресурсы
        ├── ui/
        │   ├── button.tsx
        │   ├── input.tsx
        │   └── dialog.tsx
        ├── lib/
        │   ├── cn.ts
        │   └── cache-tags.ts
        ├── api/
        │   └── base-client.ts
        └── config/
            └── env.ts
```

### Диаграмма зависимостей (строго однонаправленные)

```
  ┌──────────────────────────────────────────────────────────────┐
  │  app/  (Next.js routes)                                      │
  │  Тонкие файлы: реэкспорт из src/pages/                      │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/app/   — провайдеры, инициализация                      │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/pages/ — композиция: импорт widgets + features           │
  └──────────┬──────────────────────────────────┬────────────────┘
             ▼                                  ▼
  ┌─────────────────────────┐    ┌──────────────────────────────┐
  │  src/widgets/            │    │  src/features/               │
  │  Импорт: features,       │    │  Импорт: entities, shared    │
  │  entities, shared        │    │  НЕ импортирует widgets!     │
  └──────────┬──────────────┘    └──────────────┬───────────────┘
             │                                  │
             └──────────────┬───────────────────┘
                            ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/entities/ — бизнес-сущности, их UI и API                │
  │  Импорт: ТОЛЬКО shared                                       │
  └──────────────────────────┬───────────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  src/shared/ — UI-kit, утилиты, конфиги                      │
  │  Импорт: НИЧЕГО из проекта (только npm-пакеты)               │
  └──────────────────────────────────────────────────────────────┘
```

### Правило зависимостей

> Каждый слой может импортировать **только из слоёв ниже себя**.
> Слайсы внутри одного слоя **не могут** импортировать друг друга.

Нарушение этого правила -- сигнал архитектурной ошибки. Проверяется линтером
`@feature-sliced/eslint-config` или `eslint-plugin-boundaries`.

### Плюсы и минусы

| Плюс                                          | Минус                                    |
| --------------------------------------------- | ---------------------------------------- |
| Стандартизованная структура                   | Конфликт с App Router (нужен workaround) |
| Строгий контроль зависимостей                 | Крутая кривая обучения                   |
| Масштабируется до больших команд              | Overhead для малых проектов              |
| Предсказуемость: знаешь слой = знаешь правила | Больше файлов и папок                    |
| Активное сообщество и тулинг                  | Избыточно для MVP                        |

### Пример: та же фича Auth в FSD

```typescript
// src/entities/user/model/user.types.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}
```

```typescript
// src/entities/user/api/user.queries.ts
import type { User } from '../model/user.types';

export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch('/api/auth/me');
  if (!response.ok) return null;
  return response.json();
}
```

```typescript
// src/entities/user/index.ts  -- Public API
export type { User } from './model/user.types';
export { getCurrentUser } from './api/user.queries';
export { UserCard } from './ui/user-card';
```

```typescript
// src/features/auth/login/api/login.action.ts
'use server';

import { revalidateTag } from 'next/cache';

interface LoginCredentials {
  email: string;
  password: string;
}

export async function loginAction(credentials: LoginCredentials) {
  const response = await fetch(`${process.env.API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    return { error: 'Invalid credentials' };
  }

  revalidateTag('current-user');
  return { success: true };
}
```

```typescript
// src/features/auth/login/ui/login-form.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { loginAction } from '../api/login.action';

export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await loginAction({ email, password });
    if (result.error) alert(result.error);
  };

  return (
    <form onSubmit={handleSubmit}>
      <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <Button type="submit">Sign In</Button>
    </form>
  );
}
```

```typescript
// src/features/auth/login/index.ts  -- Public API
export { LoginForm } from './ui/login-form';
```

```typescript
// src/pages/login/ui.tsx  -- Композиция страницы
import { LoginForm } from '@/features/auth/login';

export function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md p-6">
        <h1 className="mb-6 text-2xl font-bold">Login</h1>
        <LoginForm />
      </div>
    </main>
  );
}
```

```typescript
// app/(auth)/login/page.tsx  -- Тонкий маршрут
export { LoginPage as default } from '@/pages/login/ui';
```

### Когда использовать

- Крупные проекты (100+ файлов)
- Команды 5+ разработчиков
- Долгоживущие продукты с потребностью в стандартизации
- Команды, готовые инвестировать в onboarding

---

## 2.4 Подход 4: Clean / Hexagonal Architecture

### Суть

Вдохновлён идеями Роберта Мартина (Clean Architecture) и Алистера Кокбёрна
(Hexagonal / Ports & Adapters). Ключевой принцип: **бизнес-логика в центре,
детали реализации на периферии**. Зависимости направлены внутрь -- доменный
слой не знает ни о React, ни о Next.js, ни о базе данных.

### Структура

```
src/
├── domain/                      # Ядро: сущности и бизнес-правила
│   ├── user/
│   │   ├── user.entity.ts       # User class / interface
│   │   ├── user.repository.ts   # Port (интерфейс репозитория)
│   │   └── user.errors.ts       # Доменные ошибки
│   └── order/
│       ├── order.entity.ts
│       ├── order.repository.ts
│       └── order-total.vo.ts    # Value Object
│
├── application/                 # Use Cases (сценарии использования)
│   ├── auth/
│   │   ├── login.use-case.ts
│   │   ├── logout.use-case.ts
│   │   └── auth.port.ts         # Порт для auth-адаптера
│   └── orders/
│       ├── create-order.use-case.ts
│       └── get-orders.use-case.ts
│
├── infrastructure/              # Адаптеры (реализации портов)
│   ├── repositories/
│   │   ├── prisma-user.repository.ts
│   │   └── prisma-order.repository.ts
│   ├── auth/
│   │   └── next-auth.adapter.ts
│   └── api/
│       └── stripe.adapter.ts
│
├── presentation/                # UI (React/Next.js)
│   ├── components/
│   ├── hooks/
│   └── pages/
│
└── app/                         # Next.js маршруты
```

### Диаграмма зависимостей (инверсия зависимостей)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                         │   │
│   │   ┌─────────────────────────────────────────────────┐   │   │
│   │   │                                                 │   │   │
│   │   │   ┌─────────────────────────────────────────┐   │   │   │
│   │   │   │                                         │   │   │   │
│   │   │   │         DOMAIN (Entities)               │   │   │   │
│   │   │   │   User, Order, Value Objects            │   │   │   │
│   │   │   │   Repository Interfaces (Ports)         │   │   │   │
│   │   │   │                                         │   │   │   │
│   │   │   └─────────────────────────────────────────┘   │   │   │
│   │   │                                                 │   │   │
│   │   │         APPLICATION (Use Cases)                 │   │   │
│   │   │   LoginUseCase, CreateOrderUseCase              │   │   │
│   │   │   Зависит от: domain (только интерфейсы)        │   │   │
│   │   │                                                 │   │   │
│   │   └─────────────────────────────────────────────────┘   │   │
│   │                                                         │   │
│   │         INFRASTRUCTURE (Adapters)                       │   │
│   │   PrismaUserRepository, NextAuthAdapter                 │   │
│   │   Реализует порты domain, вызывается из application     │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│         PRESENTATION (UI) + FRAMEWORK (Next.js)                 │
│   React-компоненты, хуки, маршруты                              │
│   Вызывает application через use cases                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Все стрелки зависимостей направлены ВНУТРЬ → к domain
```

### Плюсы и минусы

| Плюс                                     | Минус                                         |
| ---------------------------------------- | --------------------------------------------- |
| Максимальная тестируемость               | Много boilerplate-кода (интерфейсы, адаптеры) |
| Бизнес-логика не зависит от фреймворка   | Избыточно для большинства фронтенд-проектов   |
| Легко менять инфраструктуру (БД, API)    | Крутая кривая обучения (паттерны GoF, SOLID)  |
| Идеально для сложной бизнес-логики       | Файловая структура раздута                    |
| Легко портировать на другой UI-фреймворк | Медленный старт разработки                    |

### Пример: та же фича Auth в Clean Architecture

```typescript
// src/domain/user/user.entity.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}
```

```typescript
// src/domain/user/user.repository.ts  -- Port (интерфейс)
import type { User } from './user.entity';

export interface UserRepository {
  findByEmail(email: string): Promise<User | null>;
  findById(id: string): Promise<User | null>;
}
```

```typescript
// src/application/auth/auth.port.ts  -- Port для auth-адаптера
export interface AuthPort {
  verifyCredentials(email: string, password: string): Promise<string | null>; // returns userId
  createSession(userId: string): Promise<string>; // returns session token
  destroySession(token: string): Promise<void>;
}
```

```typescript
// src/application/auth/login.use-case.ts
import type { UserRepository } from '@/domain/user/user.repository';
import type { AuthPort } from './auth.port';
import type { User } from '@/domain/user/user.entity';

export class LoginUseCase {
  constructor(
    private userRepository: UserRepository,
    private authAdapter: AuthPort,
  ) {}

  async execute(email: string, password: string): Promise<User> {
    const userId = await this.authAdapter.verifyCredentials(email, password);
    if (!userId) throw new Error('Invalid credentials');

    const user = await this.userRepository.findById(userId);
    if (!user) throw new Error('User not found');

    await this.authAdapter.createSession(userId);
    return user;
  }
}
```

```typescript
// src/infrastructure/repositories/prisma-user.repository.ts
import type { UserRepository } from '@/domain/user/user.repository';
import type { User } from '@/domain/user/user.entity';
import { db } from '@/lib/db';

export class PrismaUserRepository implements UserRepository {
  async findByEmail(email: string): Promise<User | null> {
    return db.user.findUnique({ where: { email } });
  }

  async findById(id: string): Promise<User | null> {
    return db.user.findUnique({ where: { id } });
  }
}
```

```typescript
// src/presentation/hooks/use-login.ts
'use client';

import { useState } from 'react';
import { LoginUseCase } from '@/application/auth/login.use-case';
import { PrismaUserRepository } from '@/infrastructure/repositories/prisma-user.repository';
import { NextAuthAdapter } from '@/infrastructure/auth/next-auth.adapter';

// В реальном проекте зависимости инжектятся через DI-контейнер
const loginUseCase = new LoginUseCase(new PrismaUserRepository(), new NextAuthAdapter());

export function useLogin() {
  const [isLoading, setIsLoading] = useState(false);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      return await loginUseCase.execute(email, password);
    } finally {
      setIsLoading(false);
    }
  };

  return { login, isLoading };
}
```

### Когда использовать

- Сложная бизнес-логика (финтех, медтех, ERP)
- Потребность менять инфраструктуру без переписывания логики
- Команда, знакомая с паттернами Enterprise Architecture
- Full-stack Next.js с тяжёлым серверным слоем

---

## 2.5 Подход 5: Vertical Slice Architecture

### Суть

Идея Джимми Богарда: вместо разделения по слоям код организуется вокруг
**конкретных пользовательских запросов**. Каждый «срез» -- это end-to-end
реализация одного действия, от UI до данных. Связность максимальна внутри
среза, минимальна между срезами.

Ключевое отличие от Feature-based: Feature-based группирует по **домену**
(User, Order), Vertical Slice -- по **действию** (CreateOrder, GetUserProfile).

### Структура

```
src/
├── slices/
│   ├── create-order/
│   │   ├── create-order.action.ts    # Server Action
│   │   ├── create-order.form.tsx     # UI компонент
│   │   ├── create-order.schema.ts    # Zod-валидация
│   │   ├── create-order.types.ts     # Типы этого среза
│   │   └── create-order.test.ts      # Тест
│   │
│   ├── get-orders/
│   │   ├── get-orders.query.ts       # Серверный запрос
│   │   ├── get-orders.table.tsx      # UI таблица
│   │   └── get-orders.types.ts
│   │
│   ├── login/
│   │   ├── login.action.ts
│   │   ├── login.form.tsx
│   │   ├── login.schema.ts
│   │   └── login.types.ts
│   │
│   └── get-current-user/
│       ├── get-current-user.query.ts
│       └── get-current-user.types.ts
│
├── shared/                          # Общие ресурсы
│   ├── ui/
│   ├── lib/
│   └── types/
│
└── app/                             # Next.js маршруты
```

### Диаграмма зависимостей

```
┌──────────────────────────────────────────────────────────────┐
│                     app/ (routes)                             │
│  page.tsx импортирует один или несколько slices               │
└──────┬────────────┬────────────┬────────────┬───────────────┘
       │            │            │            │
       ▼            ▼            ▼            ▼
  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
  │ create- │ │  get-    │ │  login  │ │  get-    │
  │ order   │ │  orders  │ │         │ │  current │
  │         │ │          │ │         │ │  -user   │
  │ action  │ │ query    │ │ action  │ │ query    │
  │ form    │ │ table    │ │ form    │ │          │
  │ schema  │ │ types    │ │ schema  │ │ types    │
  │ types   │ │          │ │ types   │ │          │
  └────┬────┘ └─────┬────┘ └────┬───┘ └────┬─────┘
       │            │            │           │
       └────────────┴────────────┴───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │      shared/         │
              │  ui, lib, types      │
              └──────────────────────┘

Срезы НЕ зависят друг от друга.
Каждый срез -- самодостаточная единица.
```

### Плюсы и минусы

| Плюс                                                 | Минус                                    |
| ---------------------------------------------------- | ---------------------------------------- |
| Максимальная cohesion (всё в одном месте)            | Дублирование типов между срезами         |
| Добавление фичи = добавление папки (no side effects) | Не подходит для shared сущностей (User)  |
| Каждый срез можно тестировать изолированно           | Много мелких папок                       |
| Естественно сочетается с CQRS                        | Плохо масштабируется при сложных доменах |
| Разные паттерны в разных срезах                      | Непривычно для frontend-разработчиков    |

### Пример: та же фича Auth (login) как Vertical Slice

```typescript
// src/slices/login/login.schema.ts
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export type LoginInput = z.infer<typeof loginSchema>;
```

```typescript
// src/slices/login/login.action.ts
'use server';

import { revalidateTag } from 'next/cache';
import { loginSchema, type LoginInput } from './login.schema';

export async function loginAction(data: LoginInput) {
  const parsed = loginSchema.safeParse(data);
  if (!parsed.success) return { error: parsed.error.flatten() };

  const response = await fetch(`${process.env.API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(parsed.data),
  });

  if (!response.ok) return { error: 'Invalid credentials' };

  revalidateTag('current-user');
  return { success: true };
}
```

```typescript
// src/slices/login/login.form.tsx
'use client';

import { useActionState } from 'react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { loginAction } from './login.action';

export function LoginForm() {
  const [state, formAction, isPending] = useActionState(loginAction, null);

  return (
    <form action={formAction}>
      <Input name="email" placeholder="Email" />
      <Input name="password" type="password" placeholder="Password" />
      {state?.error && <p className="text-red-500">{String(state.error)}</p>}
      <Button type="submit" disabled={isPending}>
        {isPending ? 'Signing in...' : 'Sign In'}
      </Button>
    </form>
  );
}
```

### Когда использовать

- CRUD-тяжёлые приложения с множеством независимых операций
- Микрофронтенды
- Проекты с CQRS на бэкенде
- Прототипирование, когда нужно быстро добавлять/удалять фичи

---

## 2.6 Сравнительная таблица всех подходов

| Критерий                       | Layer-based |  Feature-based  |       FSD        |   Clean/Hex   | Vertical Slice  |
| ------------------------------ | :---------: | :-------------: | :--------------: | :-----------: | :-------------: |
| **Масштабируемость**           |   Низкая    |     Высокая     |  Очень высокая   |    Высокая    |     Средняя     |
| **Кривая обучения**            |   Нулевая   |     Низкая      |     Средняя      |    Высокая    |     Низкая      |
| **Boilerplate**                | Минимальный |    Умеренный    |  Выше среднего   |    Высокий    |   Минимальный   |
| **Тестируемость**              |   Низкая    |     Средняя     |     Высокая      | Максимальная  |     Высокая     |
| **Командная работа**           |    Плохо    |     Хорошо      |     Отлично      |    Хорошо     |     Хорошо      |
| **Контроль зависимостей**      |     Нет     |    Частичный    |     Строгий      | Строгий (DI)  |    По срезам    |
| **Совместимость с App Router** |   Полная    |     Полная      |   С workaround   |    Полная     |     Полная      |
| **Подходит для**               |     MVP     | Средние проекты | Крупные проекты  | Сложный домен | CRUD-приложения |
| **Размер команды**             |     1-2     |      3-10       |      5-20+       |     5-15      |      3-10       |
| **Стандартизация**             |     Нет     |       Нет       | Да (методология) | Паттерны GoF  |       Нет       |

---

## 2.7 Гибридный подход: рекомендация для enterprise

Для большинства enterprise-проектов на Next.js оптимален **гибридный подход**,
сочетающий лучшие элементы Feature-based и FSD:

```
src/
├── app/                    # Next.js маршруты (тонкие файлы)
├── features/               # Feature-based: бизнес-фичи
│   ├── auth/
│   ├── billing/
│   └── users/
├── entities/               # Из FSD: общие бизнес-сущности
│   ├── user/
│   └── order/
├── components/             # Общие UI-компоненты
│   ├── ui/                 # Атомарные (Button, Input)
│   ├── layout/             # Лейаут (Header, Sidebar)
│   └── shared/             # Составные (PageHeader, ErrorBoundary)
├── lib/                    # Утилиты, API-клиенты
├── hooks/                  # Общие хуки
├── types/                  # Глобальные типы
└── config/                 # Конфигурация
```

**Почему это работает:**

- `features/` даёт фиче-модульную организацию без overhead FSD
- `entities/` из FSD решает проблему shared бизнес-сущностей
- Общие ресурсы (`components/`, `lib/`, `hooks/`) -- из layer-based
- App Router используется нативно, без workaround

---

## 2.8 Матрица принятия решений: какой подход выбрать

```
                        Сложность бизнес-логики
                    Низкая ──────────────── Высокая
                    │                           │
Размер    Малый     │  Layer-based    Clean/Hex  │
команды             │  (до 20 файлов) (если DDD) │
  │                 │                           │
  │                 │  Feature-based  Feature-   │
  │       Средний   │  (3-10 чел.)   Sliced     │
  │                 │                Design     │
  │                 │                           │
  │       Крупный   │  Vertical      FSD +      │
  │                 │  Slice (CRUD)  Гибрид     │
                    │                           │
                    └───────────────────────────┘
```

### Алгоритм выбора (Decision Tree)

```
1. Проект < 20 файлов, 1-2 разработчика?
   → Layer-based. Не усложняйте.

2. CRUD-приложение, 50+ экранов, простая логика?
   → Vertical Slice Architecture.

3. 30-100 файлов, 3-5 разработчиков, чёткие домены?
   → Feature-based.

4. 100+ файлов, 5-20 разработчиков, нужна стандартизация?
   → Feature-Sliced Design (или гибрид с FSD-элементами).

5. Сложная бизнес-логика (финтех, медтех, ERP)?
   → Clean/Hexagonal Architecture.

6. Enterprise, 10+ разработчиков, разнородные требования?
   → Гибридный подход (Feature-based + elements FSD).
```

---

## 2.9 Межфичевое взаимодействие (Cross-Feature Communication)

Одна из главных проблем feature-based архитектур -- как фичи общаются друг с другом,
не нарушая границы изоляции. Пять основных паттернов:

### Паттерн 1: Shared Entities (рекомендуется)

Общие бизнес-сущности выносятся в слой `entities/` или `shared/types/`.

```typescript
// src/entities/user/index.ts  -- Общая сущность
export type { User } from './model/user.types';
export { getCurrentUser } from './api/user.queries';

// src/features/auth/ и src/features/billing/ оба импортируют User из entities/
```

```
  features/auth/  ──────►  entities/user/  ◄──────  features/billing/
                               │
                          Общая точка зависимости,
                          а не прямая связь между фичами
```

### Паттерн 2: Event Bus (для слабой связанности)

Фичи общаются через события, не зная друг о друге.

```typescript
// src/lib/event-bus.ts
type EventCallback<T = unknown> = (data: T) => void;

class EventBus {
  private listeners = new Map<string, Set<EventCallback>>();

  on<T>(event: string, callback: EventCallback<T>): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback as EventCallback);

    // Возвращает функцию отписки
    return () => this.listeners.get(event)?.delete(callback as EventCallback);
  }

  emit<T>(event: string, data: T): void {
    this.listeners.get(event)?.forEach((cb) => cb(data));
  }
}

export const eventBus = new EventBus();
```

```typescript
// src/features/auth/hooks/use-auth.ts  -- Отправляет событие
import { eventBus } from '@/lib/event-bus';

// После логина:
eventBus.emit('auth:login', { userId: user.id });
```

```typescript
// src/features/notifications/hooks/use-notifications.ts  -- Слушает событие
import { useEffect } from 'react';
import { eventBus } from '@/lib/event-bus';

export function useNotifications() {
  useEffect(() => {
    const unsubscribe = eventBus.on('auth:login', ({ userId }) => {
      // Загрузить уведомления для пользователя
    });
    return unsubscribe;
  }, []);
}
```

### Паттерн 3: Shared Context Provider (для глобального состояния)

Провайдер контекста в корневом layout обеспечивает доступ к общему состоянию.

```typescript
// src/app/providers/auth-provider.tsx  -- Общий провайдер
'use client';

import { createContext, useContext, useState } from 'react';
import type { User } from '@/entities/user';

interface AuthContextValue {
  user: User | null;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}
```

### Паттерн 4: Server-Side через Cache Tags (Next.js-специфичный)

Фичи инвалидируют кэш друг друга через теги, не импортируя код.

```typescript
// src/features/billing/actions/update-plan.action.ts
'use server';

import { revalidateTag } from 'next/cache';

export async function updatePlanAction(planId: string) {
  await fetch(`${process.env.API_URL}/billing/plan`, {
    method: 'PUT',
    body: JSON.stringify({ planId }),
  });

  revalidateTag('billing:plan');
  revalidateTag('user:permissions'); // ← Инвалидирует данные другой фичи
}
```

```typescript
// src/features/auth/api/get-permissions.query.ts
import { unstable_cache } from 'next/cache';

export const getPermissions = unstable_cache(
  async (userId: string) => {
    const res = await fetch(`${process.env.API_URL}/users/${userId}/permissions`);
    return res.json();
  },
  ['user-permissions'],
  { tags: ['user:permissions'] }, // ← Будет инвалидирован billing-фичей
);
```

### Паттерн 5: Composition в маршрутах (самый простой)

Страница (route) собирает фичи вместе, передавая данные через пропсы.

```typescript
// src/app/(dashboard)/dashboard/page.tsx
import { getCurrentUser } from '@/entities/user';
import { UserStats } from '@/features/users/components/user-stats';
import { RecentOrders } from '@/features/orders/components/recent-orders';
import { BillingAlert } from '@/features/billing/components/billing-alert';

export default async function DashboardPage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login');

  return (
    <div>
      <UserStats userId={user.id} />
      <RecentOrders userId={user.id} />
      <BillingAlert userId={user.id} />
    </div>
  );
}
```

### Сравнение паттернов межфичевого взаимодействия

| Паттерн           | Связанность |  Сложность  | Server/Client |        Рекомендация        |
| ----------------- | :---------: | :---------: | :-----------: | :------------------------: |
| Shared Entities   |   Низкая    |   Низкая    |      Оба      |      Основной подход       |
| Event Bus         | Минимальная |   Средняя   |    Client     | Для уведомлений, аналитики |
| Context Provider  |   Средняя   |   Низкая    |    Client     |  Для auth, theme, locale   |
| Cache Tags        | Минимальная |   Низкая    |    Server     |   Для инвалидации данных   |
| Route Composition |   Нулевая   | Минимальная |    Server     |  Для страниц-агрегаторов   |

---

## 2.10 Пошаговая миграция с Layer-based на Feature-based

### Обзор процесса

Миграция выполняется **инкрементально**, без big-bang переписывания.
Принцип «странгуляции» (Strangler Fig Pattern): новый код сразу пишется
по-новому, старый переносится при каждом касании.

### Шаг 0: Фиксация текущего состояния

```bash
# Визуализируйте текущие зависимости
npx dependency-cruiser --output-type dot src/ | dot -T svg > deps-before.svg

# Посчитайте файлы по папкам
find src/components -name "*.tsx" | wc -l
find src/hooks -name "*.ts" | wc -l
find src/services -name "*.ts" | wc -l
```

### Шаг 1: Создание структуры features/

```bash
mkdir -p src/features
mkdir -p src/entities    # Опционально, если нужны общие сущности
```

### Шаг 2: Определение доменов

Составьте карту бизнес-доменов, например:

```
Домен auth:      LoginForm, UserMenu, useAuth, auth.service, auth.types
Домен orders:    OrderTable, OrderCard, useOrders, orders.service, order.types
Домен users:     UserCard, UserList, useUsers, users.service, user.types
Общее:           Button, Input, Modal, useDebounce, formatDate
```

### Шаг 3: Перенос первой фичи (начните с изолированной)

```
# ДО:
src/components/LoginForm.tsx     → src/features/auth/components/login-form.tsx
src/hooks/useAuth.ts             → src/features/auth/hooks/use-auth.ts
src/services/auth.service.ts     → src/features/auth/services/auth.service.ts
src/types/auth.types.ts          → src/features/auth/types/auth.types.ts

# Создайте public API:
src/features/auth/index.ts
```

```typescript
// src/features/auth/index.ts
export { LoginForm } from './components/login-form';
export { useAuth } from './hooks/use-auth';
export type { User, AuthState } from './types/auth.types';
```

### Шаг 4: Обновление импортов

```typescript
// ДО:
import { LoginForm } from '@/components/LoginForm';
import { useAuth } from '@/hooks/useAuth';

// ПОСЛЕ:
import { LoginForm, useAuth } from '@/features/auth';
// Или прямые импорты (без barrel):
import { LoginForm } from '@/features/auth/components/login-form';
import { useAuth } from '@/features/auth/hooks/use-auth';
```

### Шаг 5: Настройка eslint-plugin-boundaries

```javascript
// eslint.config.mjs
import boundaries from 'eslint-plugin-boundaries';

export default [
  {
    plugins: { boundaries },
    settings: {
      'boundaries/elements': [
        { type: 'app', pattern: 'src/app/*' },
        { type: 'features', pattern: 'src/features/*' },
        { type: 'entities', pattern: 'src/entities/*' },
        { type: 'components', pattern: 'src/components/*' },
        { type: 'lib', pattern: 'src/lib/*' },
        { type: 'hooks', pattern: 'src/hooks/*' },
      ],
    },
    rules: {
      'boundaries/element-types': [
        2,
        {
          default: 'disallow',
          rules: [
            // features импортируют из entities, components, lib, hooks
            { from: 'features', allow: ['entities', 'components', 'lib', 'hooks'] },
            // features НЕ импортируют друг друга
            // entities импортируют только из lib
            { from: 'entities', allow: ['lib'] },
            // components НЕ импортируют из features
            { from: 'components', allow: ['lib', 'hooks'] },
            // app может всё
            { from: 'app', allow: ['features', 'entities', 'components', 'lib', 'hooks'] },
          ],
        },
      ],
    },
  },
];
```

### Шаг 6: Постепенный перенос остальных фичей

Правило: **при каждом тикете, затрагивающем «старый» код, переносите его в features/**.
Через 2-3 спринта основная часть кода будет перенесена.

### Шаг 7: Очистка пустых layer-папок

```bash
# Когда src/hooks/ и src/services/ опустеют -- удалите их
# Оставьте только общие ресурсы: src/components/ui/, src/lib/, src/hooks/ (общие)
```

### Шаг 8: Визуализация результата

```bash
# Проверьте зависимости после миграции
npx dependency-cruiser --output-type dot src/ | dot -T svg > deps-after.svg

# Убедитесь, что нет циклических зависимостей
npx dependency-cruiser --output-type err src/
```

### Типичный таймлайн

| Фаза          | Длительность | Действия                               |
| ------------- | :----------: | -------------------------------------- |
| Планирование  |   1-2 дня    | Карта доменов, выбор первой фичи       |
| Пилот         |   1 неделя   | Миграция 1 фичи, настройка линтера     |
| Развёртывание | 2-4 спринта  | Миграция при каждом тикете             |
| Очистка       |   1-2 дня    | Удаление пустых layer-папок            |
| Верификация   |    1 день    | Визуализация зависимостей, CI-проверки |

---

## 2.11 Архитектурные решения (ADR): фиксация выбора

Для enterprise-проектов критически важно фиксировать архитектурные решения
в формате **Architectural Decision Records (ADR)**. Это живой документ,
объясняющий **почему** был выбран конкретный подход.

### Шаблон ADR (формат MADR)

```markdown
# ADR-001: Выбор архитектурного подхода для frontend

## Статус

Принято (2026-04-05)

## Контекст

Проект — enterprise SaaS-приложение на Next.js 15+ (App Router).
Команда: 8 frontend-разработчиков, 3 из которых — junior.
Ожидаемый размер: 200+ файлов, 15+ бизнес-фичей.

## Рассмотренные варианты

1. Layer-based — отклонён: не масштабируется для команды 8 человек
2. Feature-Sliced Design — отклонён: конфликт с App Router, высокий порог входа
3. Clean Architecture — отклонён: избыточный boilerplate для frontend
4. **Feature-based (гибрид)** — выбран
5. Vertical Slice — отклонён: плохо подходит для сложного домена

## Решение

Гибридный Feature-based подход:

- `src/features/` для бизнес-фичей
- `src/entities/` для общих бизнес-сущностей (из FSD)
- `src/components/`, `src/lib/`, `src/hooks/` для общих ресурсов
- Контроль границ через `eslint-plugin-boundaries`

## Причины выбора

- Баланс между структурой и простотой
- Низкий порог входа для junior-разработчиков
- Полная совместимость с App Router
- Слой entities решает проблему shared бизнес-логики

## Последствия

- Необходимо документировать границы каждой фичи
- При росте до 20+ фичей рассмотреть переход на полный FSD
- Каждая фича должна иметь index.ts (public API)
```

### Где хранить ADR

```
docs/
└── adr/
    ├── 001-architecture-pattern.md
    ├── 002-state-management.md
    ├── 003-api-layer-design.md
    └── template.md
```

ADR хранятся в репозитории рядом с кодом и версионируются через Git.
Это обеспечивает трассируемость решений и контекст для новых членов команды.

---

## 2.12 Инструменты контроля архитектуры

### eslint-plugin-boundaries

Проверяет правила импортов между архитектурными элементами в реальном времени (в IDE).

```bash
pnpm add -D eslint-plugin-boundaries
```

### dependency-cruiser

Визуализирует зависимости, находит циклы, проверяет архитектурные правила в CI.

```bash
pnpm add -D dependency-cruiser

# Инициализация
npx depcruise --init

# Проверка
npx depcruise --validate .dependency-cruiser.cjs src/

# Визуализация
npx depcruise --output-type dot src/ | dot -T svg > dependency-graph.svg
```

Пример правила для dependency-cruiser:

```javascript
// .dependency-cruiser.cjs
module.exports = {
  forbidden: [
    {
      name: 'no-feature-to-feature',
      comment: 'Features must not depend on other features directly',
      severity: 'error',
      from: { path: '^src/features/([^/]+)/' },
      to: { path: '^src/features/([^/]+)/' },
      // Разрешаем импорт внутри своей фичи
      // но запрещаем из чужой фичи
    },
    {
      name: 'no-circular',
      severity: 'error',
      from: {},
      to: { circular: true },
    },
  ],
};
```

### @feature-sliced/eslint-config

Для проектов на FSD -- проверяет слои, слайсы, public API.

```bash
pnpm add -D @feature-sliced/eslint-config
```

---

## 2.13 Итоговые рекомендации

1. **Не начинайте с Clean Architecture** -- если у вас нет сложной доменной логики,
   overhead портов и адаптеров не оправдан.

2. **Layer-based -- только для прототипов**. При росте до 30+ файлов немедленно
   мигрируйте на Feature-based.

3. **FSD -- отличный выбор**, но требует workaround с App Router и инвестиций
   в обучение. Подходит для команд, готовых к стандартизации.

4. **Гибридный Feature-based -- золотая середина** для большинства enterprise-проектов.
   Берёт лучшее от FSD (entities, dependency rules) без его overhead.

5. **Vertical Slice -- недооценённый подход** для CRUD-тяжёлых приложений.
   Особенно хорош в сочетании с Server Actions Next.js.

6. **Фиксируйте решения в ADR** -- через 6 месяцев никто не вспомнит, почему
   выбран конкретный подход.

7. **Автоматизируйте контроль** через eslint-plugin-boundaries и dependency-cruiser.
   Архитектура без enforcement деградирует за 2-3 спринта.

---

## Источники

- [Feature-Sliced Design: Usage with Next.js](https://feature-sliced.design/docs/guides/tech/with-nextjs)
- [FSD: The Ultimate Next.js App Router Architecture](https://feature-sliced.design/blog/nextjs-app-router-guide)
- [Clean Architecture vs FSD in Next.js (Medium)](https://medium.com/@metastability/clean-architecture-vs-feature-sliced-design-in-next-js-applications-04df25e62690)
- [Clean Architecture in Next.js — The Guide You Need (Medium)](https://medium.com/@plozovikov/clean-architecture-the-guide-you-need-dd8c179b9f95)
- [Building a Clean Next.js App with Hexagonal Architecture (Medium)](https://medium.com/@martin_42533/building-a-clean-next-js-app-with-hexagonal-architecture-and-redux-7c898ac26e66)
- [Hexagonal Architecture in Front-End (Dimitri Dumont)](https://www.dimitri-dumont.fr/en/blog/hexagonal-architecture-front-end)
- [Domain-Driven Design with React (CSS-Tricks)](https://css-tricks.com/domain-driven-design-with-react/)
- [Clean Architecture Meets DDD in Frontend (Medium)](https://medium.com/@carolsancos/clean-architecture-meets-domain-driven-design-in-the-frontend-world-9c75e5f3e62e)
- [Does DDD Belong on the Frontend? (Khalil Stemmler)](https://khalilstemmler.com/articles/typescript-domain-driven-design/ddd-frontend/)
- [Vertical Slice Architecture (Jimmy Bogard)](https://www.jimmybogard.com/vertical-slice-architecture/)
- [You're Slicing Your Architecture Wrong (DEV Community)](https://dev.to/somedood/youre-slicing-your-architecture-wrong-4ob9)
- [Feature-Driven Architecture with Next.js (DEV Community)](https://dev.to/rufatalv/feature-driven-architecture-with-nextjs-a-better-way-to-structure-your-application-1lph)
- [Screaming Architecture in Front-End (Medium)](https://medium.com/@hrynkevych/screaming-architecture-in-front-end-de72d9ec961c)
- [Screaming Architecture: Evolution of React Folder Structure (DEV Community)](https://dev.to/profydev/screaming-architecture-evolution-of-a-react-folder-structure-4g25)
- [Modularizing React Applications with Established UI Patterns (Martin Fowler)](https://martinfowler.com/articles/modularizing-react-apps.html)
- [Migrating a Legacy React Project to FSD (Medium)](https://medium.com/@O5-25/migrating-a-legacy-react-project-to-feature-sliced-design-benefits-challenges-and-considerations-0aeecbc8b866)
- [EventBus Pattern in React (Medium)](https://medium.com/@ilham.abdillah.alhamdi/eventbus-pattern-in-react-a-lightweight-alternative-to-context-and-redux-cc6e8a1dc9ca)
- [Cross Micro Frontends Communication (DEV Community)](https://dev.to/luistak/cross-micro-frontends-communication-30m3)
- [MADR: Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [ADR GitHub Organization](https://adr.github.io/)
- [eslint-plugin-boundaries (npm)](https://www.npmjs.com/package/eslint-plugin-boundaries)
- [dependency-cruiser (GitHub)](https://github.com/sverweij/dependency-cruiser)
- [Taking Frontend Architecture Serious With Dependency-cruiser (Xebia)](https://xebia.com/blog/taking-frontend-architecture-serious-with-dependency-cruiser/)
- [The Battle-Tested NextJS Project Structure 2025 (Medium)](https://medium.com/@burpdeepak96/the-battle-tested-nextjs-project-structure-i-use-in-2025-f84c4eb5f426)
- [Scalable React Projects with Feature-Based Architecture (DEV Community)](https://dev.to/naserrasouli/scalable-react-projects-with-feature-based-architecture-117c)
- [Build Scalable React with Feature-Based Architecture (adjoe)](https://adjoe.io/company/engineer-blog/moving-to-feature-based-react-architecture/)
