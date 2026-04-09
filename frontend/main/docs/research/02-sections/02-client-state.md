# 3. Управление клиентским состоянием (углубленное исследование)

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

### Композиция атомов

```typescript
// atoms/filters.ts
import { atom } from 'jotai';
import { atomWithStorage } from 'jotai/utils';

// Базовые атомы
export const searchQueryAtom = atom('');
export const categoryAtom = atom<string | null>(null);
export const sortByAtom = atomWithStorage<'price' | 'name' | 'date'>('sort', 'date');
export const pageAtom = atom(1);

// Производный атом — автоматически пересчитывается
export const filtersAtom = atom((get) => ({
  search: get(searchQueryAtom),
  category: get(categoryAtom),
  sortBy: get(sortByAtom),
  page: get(pageAtom),
}));

// Async атом — fetch на основе фильтров
export const productsAtom = atom(async (get) => {
  const filters = get(filtersAtom);
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v != null) as [string, string][],
  );
  const res = await fetch(`/api/products?${params}`);
  return res.json();
});

// Write-only атом для сброса
export const resetFiltersAtom = atom(null, (_get, set) => {
  set(searchQueryAtom, '');
  set(categoryAtom, null);
  set(sortByAtom, 'date');
  set(pageAtom, 1);
});
```

---

## 3.4 Миграция с Redux на Zustand

### Пошаговый план

| Шаг | Действие                                                       |
| --- | -------------------------------------------------------------- |
| 1   | Создайте Zustand store рядом с Redux slice                     |
| 2   | Перенесите state shape и actions (1 slice = 1 store)           |
| 3   | Замените `useSelector` на `useStore(selector)`                 |
| 4   | Замените `dispatch(action())` на прямой вызов `store.action()` |
| 5   | Удалите Redux Provider, middleware, store config               |
| 6   | Удалите зависимости `@reduxjs/toolkit`, `react-redux`          |

### Сравнение кода

```typescript
// Redux Toolkit
const userSlice = createSlice({
  name: 'user',
  initialState: { user: null, loading: false },
  reducers: {
    setUser: (state, action) => {
      state.user = action.payload;
    },
    clearUser: (state) => {
      state.user = null;
    },
  },
});
// Компонент: const user = useSelector(s => s.user.user);
// Компонент: dispatch(setUser(data));

// Zustand — эквивалент
const useUserStore = create((set) => ({
  user: null,
  loading: false,
  setUser: (user) => set({ user }),
  clearUser: () => set({ user: null }),
}));
// Компонент: const user = useUserStore(s => s.user);
// Компонент: useUserStore.getState().setUser(data);
```

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
