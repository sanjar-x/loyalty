# Аудит масштабируемости: Frontend Main

**Проект:** Loyalty Marketplace — Telegram Mini App  
**Технологии:** Next.js 16, TypeScript, React 19, Redux Toolkit + RTK Query  
**Дата аудита:** 2026-04-05  
**Аудитор:** Claude Opus 4.6  

---

## Содержание

1. [Общая оценка](#1-общая-оценка)
2. [Рост фичей и модульность](#2-рост-фичей-и-модульность)
3. [Переиспользуемость кода](#3-переиспользуемость-кода)
4. [RTK Query и слой данных](#4-rtk-query-и-слой-данных)
5. [Размер бандла](#5-размер-бандла)
6. [Композиция компонентов](#6-композиция-компонентов)
7. [Управление состоянием](#7-управление-состоянием)
8. [Стили](#8-стили)
9. [Паттерны производительности](#9-паттерны-производительности)
10. [Оптимизация изображений](#10-оптимизация-изображений)
11. [Code Splitting](#11-code-splitting)
12. [API-слой](#12-api-слой)
13. [Система типов](#13-система-типов)
14. [Производительность сборки](#14-производительность-сборки)
15. [Сводка проблем](#15-сводка-проблем)
16. [Рекомендации](#16-рекомендации)
17. [Прогнозы роста и лимиты](#17-прогнозы-роста-и-лимиты)
18. [Итоговая оценка](#18-итоговая-оценка)

---

## 1. Общая оценка

Проект находится на **ранней стадии разработки**: UI-компоненты созданы и стилизованы, но **слой данных фактически не подключен** — RTK Query не содержит ни одного эндпоинта, страницы работают на захардкоженных данных или пустых массивах. Архитектурный фундамент (BFF-прокси, auth-flow, Telegram SDK) заложен грамотно, но **инфраструктура для масштабирования** (code splitting, bundle analysis, мемоизация, injectEndpoints) — отсутствует.

**Текущий статус:** прототип/MVP с хорошей архитектурой, но без готовности к production-нагрузкам.

---

## 2. Рост фичей и модульность

### Структура проекта

```
app/              — 34 страницы (App Router)
components/
  blocks/         — 10 доменных директорий (product, home, catalog, favorites, search, ...)
  ios/            — 1 компонент
  layout/         — 3 компонента
  providers/      — 1 компонент (StoreProvider)
  ui/             — 2 компонента (Button, BottomSheet)
lib/
  auth/           — 4 файла
  format/         — 5 утилит
  hooks/          — 1 хук (заглушка)
  store/          — 4 файла
  telegram/       — 25+ хуков, провайдер, типы
  types/          — 6 файлов
  errors.ts
```

### Положительное

- **Доменная организация `blocks/`** — компоненты сгруппированы по фичам (product, home, catalog, favorites, search, reviews, profile, promo, cart, telegram). Добавление новой фичи = новая директория.
- **App Router** правильно используется — вложенные layout-ы, loading-состояния, API routes.
- **Чёткое разделение**: UI-примитивы (`components/ui/`), блоки фичей (`components/blocks/`), утилиты (`lib/`).

### Проблемы

| Проблема                                                                                                           | Влияние                                                                                          |
| ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Всего **2 UI-примитива** (Button, BottomSheet) — при 43 компонентах в `blocks/`                                    | Каждый block-компонент вынужден дублировать базовые элементы (инпуты, списки, скелетоны, иконки) |
| Нет shared-компонентов для форм, модальных окон, списков                                                           | Невозможно масштабировать без дублирования                                                       |
| `components/blocks/favorites/` содержит **дублирующую вложенную директорию** `brands/` с аналогичными компонентами | `BrandCard.tsx` существует в двух местах с разной реализацией                                    |

**Файлы-дубликаты:**
- `components/blocks/favorites/BrandCard.tsx` vs `components/blocks/favorites/brands/BrandCard.tsx`
- `components/blocks/favorites/BrandsSection.tsx` vs `components/blocks/favorites/brands/FavoriteBrandsSection.tsx`

---

## 3. Переиспользуемость кода

### Положительное

- `ProductSection` — хорошо спроектированный переиспользуемый компонент (grid/horizontal layout, skeleton, tabs).
- `Button` — 5 вариантов, 3 размера, loading-состояние, слоты для иконок.
- Утилиты форматирования (`formatRubPrice`, `formatRuDateTime`, `cn`) — переиспользуемы и хорошо типизированы.
- Fallback-chain для изображений (`buildProductPhotoUrl`, `buildBrandLogoUrl`) — продуманный подход.

### Проблемы

| Серьёзность | Проблема                                                                                                     | Файл                            |
| ----------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------- |
| **MAJOR**   | 6 SVG-иконок определены inline в Footer (~260 строк SVG из 449)                                              | `components/layout/Footer.tsx`  |
| **MAJOR**   | BottomSheet используется 6+ раз, но каждый раз с разной конфигурацией через boolean-пропсы вместо композиции | `components/ui/BottomSheet.tsx` |
| **MAJOR**   | Нет общего компонента для пустого состояния — каждая страница реализует свой                                 | Множество файлов                |
| **MINOR**   | `HomeDeliveryStatusCard` используется 2 раза подряд на главной странице — явно-заглушечный код               | `app/page.tsx`                  |
| **MINOR**   | `useItemFavorites` — полностью заглушка, возвращает пустые данные                                            | `lib/hooks/useItemFavorites.ts` |

### Анализ переиспользования clsx/cn

24 файла импортируют `clsx` напрямую (как `cx`, `cn`, или `clsx`), и лишь 14 файлов используют `cn` из `@/lib/format/cn`. **Три разных имени для одной функции:**

```
cx from "clsx"      — 14 файлов (components/blocks/*)
cn from "clsx"      — 3 файла (app/trash, app/checkout/pickup, app/checkout)
clsx from "clsx"    — 1 файл (app/profile/reviews)
cn from "@/lib/format/cn" — 14 файлов
```

Это создаёт путаницу и затрудняет рефакторинг.

---

## 4. RTK Query и слой данных

### CRITICAL: RTK Query не содержит ни одного эндпоинта

```typescript
// lib/store/api.ts, строка 83
endpoints: () => ({})
```

Это **блокирующая проблема масштабируемости**: весь data-fetching framework настроен (baseQuery, reauth, tagTypes), но **ни один API-запрос не реализован через RTK Query**.

### Отсутствующая инфраструктура

| Что отсутствует            | Почему это критично                               |
| -------------------------- | ------------------------------------------------- |
| `injectEndpoints`          | Невозможно добавлять эндпоинты из фичевых модулей |
| Сплит API на фичевые файлы | Единый `api.ts` станет монолитом при росте        |
| Кеш-инвалидация            | 5 tagTypes объявлены, но нигде не используются    |
| Optimistic updates         | Нет паттерна для оптимистичных обновлений         |
| Бесконечная прокрутка      | Нет механизма для пагинации каталога              |

### Текущее состояние данных на страницах

| Страница                              | Источник данных                                      |
| ------------------------------------- | ---------------------------------------------------- |
| Home (`app/page.tsx`)                 | `const recentProducts: never[] = []` — пустой массив |
| Catalog (`app/catalog/page.tsx`)      | Захардкоженные данные в компоненте                   |
| Product (`app/product/[id]/page.tsx`) | Захардкоженный объект товара                         |
| Profile (`app/profile/page.tsx`)      | Заглушка                                             |
| Favorites (`app/favorites/page.tsx`)  | Заглушка                                             |
| Search (`app/search/page.tsx`)        | Локальное состояние                                  |
| Checkout (`app/checkout/page.tsx`)    | localStorage                                         |

**Все 37 страниц с `"use client"` работают без серверных данных.**

### Рекомендуемая архитектура API (на будущее)

```
lib/store/
  api.ts                    — базовый createApi (как сейчас)
  api/
    catalogApi.ts           — api.injectEndpoints для каталога
    userApi.ts              — api.injectEndpoints для пользователя
    cartApi.ts              — api.injectEndpoints для корзины
    ordersApi.ts            — api.injectEndpoints для заказов
    reviewsApi.ts           — api.injectEndpoints для отзывов
```

---

## 5. Размер бандла

### Зависимости (7 runtime)

| Пакет                   | Примерный размер (gzip) | Комментарий                    |
| ----------------------- | ----------------------- | ------------------------------ |
| `next`                  | ~90KB                   | Фреймворк, неизбежно           |
| `react` + `react-dom`   | ~44KB                   | Ядро, неизбежно                |
| `@reduxjs/toolkit`      | ~12KB                   | Включает RTK Query             |
| `react-redux`           | ~5KB                    |                                |
| `leaflet`               | **~40KB**               | Загружается синхронно          |
| `leaflet.markercluster` | **~10KB**               | Загружается синхронно          |
| `lucide-react`          | tree-shakeable          | Зависит от количества импортов |
| `clsx`                  | <1KB                    |                                |

### Проблемы

| Серьёзность  | Проблема                                                                                       | Влияние                                                                                             |
| ------------ | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **CRITICAL** | Нет `@next/bundle-analyzer` — невозможно отслеживать рост бандла                               | Рост размера останется незамеченным до критического момента                                         |
| **MAJOR**    | `leaflet` (~40KB) + `leaflet.markercluster` (~10KB) грузятся синхронно как обычные зависимости | **+50KB** к начальному бандлу для всех пользователей, хотя карта нужна только на `/checkout/pickup` |
| **MAJOR**    | Нет `dynamic()` импортов нигде в проекте (0 вхождений)                                         | Весь код грузится в один бандл                                                                      |
| **MINOR**    | `next.config.ts` — минимальная конфигурация, нет оптимизации webpack                           | Отсутствует `modularizeImports`, нет сжатия SVG                                                     |

### Рекомендуемые изменения для `next.config.ts`

```typescript
const nextConfig: NextConfig = {
  images: {
    remotePatterns: [...],
  },
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
};
```

---

## 6. Композиция компонентов

### BottomSheet — антипаттерн boolean-пропсов

```typescript
// components/ui/BottomSheet.tsx
interface BottomSheetProps {
  isTypeModule?: boolean;    // Влияет на высоту
  isFilter?: boolean;        // Влияет на стили
  isReview?: boolean;        // Влияет на высоту/скролл
  isPromocodePage?: boolean; // Влияет на стили body
  // ... + ещё 8 пропсов
}
```

**Проблема:** каждая новая страница, использующая BottomSheet, потребует нового boolean-пропса. Уже сейчас 4 boolean-а создают 16 возможных комбинаций стилей.

**Решение:** заменить на `variant: 'default' | 'module' | 'filter' | 'review' | 'promocode'` или, лучше, использовать compound component pattern:

```tsx
<BottomSheet open={open} onClose={onClose}>
  <BottomSheet.Header title="Фильтры" />
  <BottomSheet.Body scrollable maxHeight={446}>
    {children}
  </BottomSheet.Body>
  <BottomSheet.Footer>{footer}</BottomSheet.Footer>
</BottomSheet>
```

### ProductCard — монолитный компонент

`components/blocks/product/ProductCard.tsx` — единственный компонент для всех контекстов (каталог, избранное, поиск, главная). При росте контекстов станет неуправляемым.

### Footer — монолит со встроенными SVG

`components/layout/Footer.tsx` — **449 строк**, из которых ~260 — inline SVG-иконки (6 штук, каждая в двух вариантах: filled и outline). Иконки должны быть в отдельных файлах.

---

## 7. Управление состоянием

### Архитектура Redux Store

```typescript
// lib/store/store.ts
configureStore({
  reducer: {
    [api.reducerPath]: api.reducer,  // RTK Query (пустой)
    auth: authReducer,                // Состояние авторизации
  },
});
```

### Положительное

- Фабрика `makeStore()` — правильный паттерн для Next.js (отдельный store на каждый запрос).
- `StoreProvider` с `useRef` — предотвращает пересоздание store при ре-рендерах.
- `authSlice` — чёткий конечный автомат: `idle → loading → authenticated | expired | error`.
- Типизированные хуки `useAppDispatch` / `useAppSelector`.
- Mutex-паттерн для рефреша токенов — предотвращает token stampede.

### Проблемы

| Серьёзность | Проблема                                                                                                                            | Файл                                                                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **MAJOR**   | Корзина хранится в `localStorage` вместо Redux                                                                                      | `components/layout/Footer.tsx`, `components/blocks/cart/useCart.ts` |
| **MAJOR**   | Синхронизация корзины через `window.addEventListener('storage')` и кастомное событие `loyaltymarket_cart_updated` — хрупкий паттерн | `components/layout/Footer.tsx`                                      |
| **MAJOR**   | Нет слайсов для фичей (favorites, search filters, UI state) — всё в локальном состоянии компонентов                                 |                                                                     |
| **MINOR**   | При подключении API потребуется массовый рефакторинг всех страниц, т.к. данные сейчас захардкожены                                  | Все `app/**/page.tsx`                                               |

### Корзина: текущий паттерн vs рекомендуемый

**Сейчас:**
```
localStorage → custom event → window.addEventListener → useState
```

**Рекомендуется:**
```
Redux slice → RTK Query mutation → optimistic update → UI подписка через useSelector
```

---

## 8. Стили

### Подход

- **CSS Modules** (`.module.css`) — основной метод стилизации.
- **Глобальные CSS-переменные** в `globals.css` для тем Telegram.
- **Нет Tailwind** (в отличие от admin-панели).

### Положительное

- CSS Modules обеспечивают изоляцию стилей по умолчанию.
- Telegram-тема интегрирована через CSS custom properties (`--tg-theme-*`).
- Safe area управляется через `--tg-safe-area-*` переменные.
- Шрифты self-hosted (Inter, BebasNeue) — нет зависимости от Google Fonts.

### Проблемы

| Серьёзность | Проблема                                                                                     | Файл                              |
| ----------- | -------------------------------------------------------------------------------------------- | --------------------------------- |
| **MINOR**   | Нет дизайн-системы или токенов (цвета, отступы, размеры захардкожены в каждом `.module.css`) | `globals.css` + все `.module.css` |
| **MINOR**   | Dark mode закомментирован в `globals.css`                                                    | `app/globals.css`                 |
| **MINOR**   | Leaflet-стили загружаются глобально                                                          | `app/globals.css`                 |
| **MINOR**   | Нет утилитарных CSS-классов — каждый компонент определяет свои `padding`, `margin`, `gap`    | Все `.module.css`                 |

### Масштабирование стилей

При текущем подходе (каждый компонент со своим `.module.css`) добавление 50+ компонентов создаст 50+ CSS-файлов без общих токенов. Рефакторинг тёмной темы потребует правки каждого файла вручную.

**Рекомендация:** определить design tokens в `globals.css`:

```css
:root {
  --lm-spacing-xs: 4px;
  --lm-spacing-sm: 8px;
  --lm-spacing-md: 16px;
  --lm-spacing-lg: 24px;
  --lm-color-text-primary: #2D2D2D;
  --lm-color-text-secondary: #B6B6B6;
  --lm-radius-sm: 8px;
  --lm-radius-md: 12px;
}
```

---

## 9. Паттерны производительности

### Мемоизация

| Метрика            | Значение                                                     |
| ------------------ | ------------------------------------------------------------ |
| `React.memo`       | **0 использований** во всём проекте                          |
| `useCallback`      | 22 использования в 11 файлах (в основном в `blocks/search/`) |
| `useMemo`          | 19 использований в 11 файлах                                 |
| `dynamic()` import | **0 использований**                                          |

### CRITICAL: Отсутствие `React.memo` на элементах списков

`ProductCard` рендерится в списках (каталог, поиск, главная, избранное). При прокрутке каталога с 100+ товарами **каждый ProductCard будет ре-рендериться при любом изменении родительского состояния**.

```typescript
// components/blocks/product/ProductCard.tsx — НЕТ мемоизации
export default function ProductCard({ product, onToggleFavorite, layout }: ProductCardProps) {
  // ...расчёт цен, форматирование, router.push...
}
```

### Проблемные паттерны

| Серьёзность | Проблема                                                                                                      | Файл                                                |
| ----------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| **MAJOR**   | `ProductCard` без `React.memo` — ре-рендер при каждом обновлении списка                                       | `components/blocks/product/ProductCard.tsx`         |
| **MAJOR**   | `Footer` подписывается на `storage`, `visibilitychange`, и кастомное событие — 3 слушателя на каждой странице | `components/layout/Footer.tsx`                      |
| **MAJOR**   | `ProductImageGallery` — touch/mouse swipe обработчики без throttle/debounce                                   | `components/blocks/product/ProductImageGallery.tsx` |
| **MINOR**   | `ResizeObserver` в Footer для расчёта `--lm-footer-height` — вызывается при каждом ресайзе без debounce       | `components/layout/Footer.tsx`                      |
| **MINOR**   | Создание функций внутри рендера (inline arrow functions в map)                                                | Множество компонентов                               |

### Loading-состояния

Из 34 страниц только **3 имеют `loading.tsx`**:
- `app/catalog/loading.tsx`
- `app/catalog/[category]/loading.tsx`
- `app/invite-friends/loading.tsx`

Остальные 31 страница не имеют Suspense-границ. При подключении реального API это приведёт к жёсткому UX без скелетонов.

---

## 10. Оптимизация изображений

### Смешанное использование `<img>` и `next/image`

| Подход                        | Файлы                                                                                                                                                                           |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `next/image` (оптимизировано) | 8 компонентов: ProductPrice, ProductReviews, ProductShippingOptions, ProductSizes, SplitPaymentSheet, ProductImageGallery, ProductInfo, BrandsList                              |
| `<img>` (не оптимизировано)   | 10 компонентов: BottomSheet, PriceSheet, SearchBar, SelectSheet, PromoInfoModal, FiltersSheet, ProductReviews (частично), SplitPaymentSheet (частично), ProfileHeader, InfoCard |

### Проблемы

| Серьёзность | Проблема                                                                                                                                                      | Файл                                                                      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **MAJOR**   | `ProductCard` использует `<img>` вместо `next/image` — это **самый рендерящийся компонент с изображениями** в каталоге                                        | `components/blocks/product/ProductCard.tsx`                               |
| **MAJOR**   | `next.config.ts` разрешает `remotePatterns` только для `i.pravatar.cc` — при подключении реального CDN с изображениями товаров `next/image` не будет работать | `next.config.ts`                                                          |
| **MINOR**   | Иконки в BottomSheet, SearchBar загружаются как `<img src="/icons/...">` вместо SVG-компонентов                                                               | `components/ui/BottomSheet.tsx`, `components/blocks/search/SearchBar.tsx` |
| **MINOR**   | Нет `sizes` пропса в некоторых использованиях `next/image`                                                                                                    | Некоторые компоненты                                                      |

### Fallback-цепочка изображений

Грамотно реализована система fallback для изображений товаров:

```typescript
// lib/format/product-image.ts
export function getProductPhotoCandidates(photos, productId): string[] {
  // Возвращает массив URL-кандидатов: CDN → backend → fallback
}
```

Но `ProductCard` реализует свой собственный fallback через `onError` на `<img>` — это не масштабируется и не использует `next/image` blur placeholder.

---

## 11. Code Splitting

### CRITICAL: Полное отсутствие code splitting

```bash
# Количество dynamic() импортов в проекте
$ grep -r "dynamic(" -- 0 результатов
```

**Ни один компонент не загружается лениво.** Это означает:

1. **Leaflet** (~50KB) грузится для всех пользователей, хотя нужен только на `/checkout/pickup`.
2. **BottomSheet** (с Portal-логикой) грузится даже если никогда не открывается.
3. **Все 43 block-компонента** входят в начальный бандл.
4. Все 25+ Telegram-хуков грузятся целиком через barrel export.

### Рекомендуемые `dynamic()` импорты

```typescript
// app/checkout/pickup/page.tsx
const MapPicker = dynamic(() => import('@/components/blocks/checkout/MapPicker'), {
  ssr: false,
  loading: () => <MapSkeleton />,
});

// Любая страница с BottomSheet
const FiltersSheet = dynamic(() => import('@/components/blocks/search/FiltersSheet'));
```

### Route-level splitting

Next.js App Router автоматически делает code splitting на уровне маршрутов. Однако, т.к. **37 из 37 страниц** помечены `"use client"`, весь код этих страниц входит в клиентский бандл. Серверные компоненты не используются **нигде** (кроме layout).

---

## 12. API-слой

### BFF-прокси

Хорошо реализованный catch-all прокси:

```
Browser → /api/backend/[...path] → BACKEND_API_BASE_URL
```

**Файл:** `app/api/backend/[...path]/route.ts`

### Положительное

- 25-секундный таймаут через `AbortController`.
- Фильтрация заголовков (только safe headers: `accept`, `content-type`, `accept-language`).
- Нормализация URL-encoding.
- Поддержка всех методов: GET, POST, PUT, PATCH, DELETE.
- Правильная обработка ошибок с `NextResponse.json`.

### Auth-флоу

```
Telegram initData → POST /api/auth/telegram → Backend validates HMAC
                   → Set httpOnly cookies (loyalty_access, loyalty_refresh)
                   → RTK Query baseQueryWithReauth (mutex refresh on 401)
```

**Положительное:**
- Mutex-паттерн предотвращает token stampede при множественных 401.
- Разделение baseQuery для auth-роутов (appBaseQuery) и API-роутов (backendBaseQuery).
- Debug-режим для разработки без Telegram.

### Проблемы

| Серьёзность  | Проблема                                                                                                            | Файл                                      |
| ------------ | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| **CRITICAL** | RTK Query `endpoints: () => ({})` — весь механизм не используется                                                   | `lib/store/api.ts`                        |
| **MAJOR**    | Нет `injectEndpoints` — при добавлении эндпоинтов всё будет в одном файле                                           | `lib/store/api.ts`                        |
| **MAJOR**    | Нет error boundary для API-ошибок — `AppError`/`ApiError`/`NetworkError` классы определены но не интегрированы с UI | `lib/errors.ts`                           |
| **MINOR**    | DaData API routes (`app/api/dadata/`) не имеют rate limiting                                                        | `app/api/dadata/suggest/address/route.ts` |

---

## 13. Система типов

### Положительное

- `strict: true` в `tsconfig.json`.
- Доменные типы хорошо структурированы: `Product`, `SKU`, `Brand`, `Category`, `Attribute`, `AttributeValue`, `Money`.
- Generics используются: `PaginatedResponse<T>`.
- Telegram SDK полностью типизирован (~1200 строк типов).
- Typed hooks для Redux: `useAppDispatch`, `useAppSelector`.

### Проблемы

| Серьёзность | Проблема                                                                                                                                             | Файл                                        |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **MAJOR**   | `ProductCardData` дублирует `Product` с другими типами полей (`price: string` vs `Money`) — это **два несовместимых контракта** для одной сущности   | `lib/types/ui.ts` vs `lib/types/catalog.ts` |
| **MAJOR**   | `lib/types/index.ts` **не экспортирует** `ui.ts` — `ProductCardData` невидим через barrel                                                            | `lib/types/index.ts`                        |
| **MAJOR**   | `ApiError` определён **дважды**: как интерфейс в `lib/types/api.ts` и как класс в `lib/errors.ts` — разные структуры                                 | `lib/types/api.ts`, `lib/errors.ts`         |
| **MINOR**   | `never[]` используется как тип для пустых массивов продуктов на главной — заглушка но опасная (не позволит присвоить реальные данные без приведения) | `app/page.tsx`                              |
| **MINOR**   | Нет generic-типов для API-ответов (envelope: `{error: {...}}`)                                                                                       |                                             |

### Рекомендация: унификация типов продукта

```typescript
// Вместо двух типов:
// catalog.ts: Product { id: string, titleI18n: Record<string,string>, ... }
// ui.ts: ProductCardData { id: number|string, name: string, price: string, ... }

// Создать адаптер:
function toProductCardData(product: Product, sku: SKU): ProductCardData {
  return {
    id: product.id,
    name: product.titleI18n.ru,
    price: formatRubPrice(sku.price.amount),
    image: buildProductPhotoUrl(product.id),
    // ...
  };
}
```

---

## 14. Производительность сборки

### Текущая конфигурация

- **Turbopack** — используется по умолчанию в Next.js 16 для `dev` (нет `--webpack` флага, в отличие от admin).
- **Минимальная `next.config.ts`** — нет webpack-кастомизации, нет `experimental` опций.
- **7 зависимостей** — минимальный `node_modules`, быстрая установка.
- **TypeScript incremental** — включён в `tsconfig.json`.

### Положительное

- Малый набор зависимостей = быстрая установка и сборка.
- Turbopack для dev = быстрый HMR.
- Нет тяжёлых трансформаций (нет SVGR, нет PostCSS плагинов).

### Проблемы

| Серьёзность | Проблема                                                                     | Влияние                               |
| ----------- | ---------------------------------------------------------------------------- | ------------------------------------- |
| **MINOR**   | Нет CI-пайплайна для проверки размера бандла                                 | Рост бандла незаметен                 |
| **MINOR**   | `moduleResolution: "node"` вместо `"bundler"` — не оптимально для Next.js 16 | Потенциальные проблемы с ESM-пакетами |
| **MINOR**   | Нет `@next/bundle-analyzer` в devDependencies                                |                                       |

---

## 15. Сводка проблем

### CRITICAL (блокируют масштабирование)

| #   | Проблема                                                       | Файл(ы)               | Влияние                       |
| --- | -------------------------------------------------------------- | --------------------- | ----------------------------- |
| C1  | RTK Query не содержит эндпоинтов — data layer не функционирует | `lib/store/api.ts:83` | Невозможно подключить backend |
| C2  | Все страницы работают на захардкоженных/пустых данных          | Все `app/**/page.tsx` | Нет реального data flow       |
| C3  | 0 dynamic() импортов — нет code splitting                      | Весь проект           | Раздутый начальный бандл      |
| C4  | Нет bundle analyzer — невозможно отслеживать размер            | `package.json`        | Слепой рост бандла            |

### MAJOR (значительно затрудняют масштабирование)

| #   | Проблема                                                             | Файл(ы)                                     |
| --- | -------------------------------------------------------------------- | ------------------------------------------- |
| M1  | Leaflet (~50KB) грузится синхронно на всех страницах                 | `package.json`                              |
| M2  | Footer.tsx — 449 строк с inline SVG                                  | `components/layout/Footer.tsx`              |
| M3  | BottomSheet — boolean-пропсы вместо композиции                       | `components/ui/BottomSheet.tsx`             |
| M4  | ProductCard без React.memo в списках                                 | `components/blocks/product/ProductCard.tsx` |
| M5  | Непоследовательное использование cn/cx/clsx (24 файла vs 14 файлов)  | Множество файлов                            |
| M6  | Смешанное использование `<img>` и `next/image` (10 vs 8 файлов)      | Множество компонентов                       |
| M7  | ProductCardData дублирует Product с несовместимыми типами            | `lib/types/ui.ts`, `lib/types/catalog.ts`   |
| M8  | Корзина в localStorage с кастомными событиями вместо Redux           | `components/layout/Footer.tsx`              |
| M9  | Нет injectEndpoints — API будет монолитным                           | `lib/store/api.ts`                          |
| M10 | 37/37 страниц — `"use client"`, серверные компоненты не используются | Все `app/**/page.tsx`                       |
| M11 | ApiError дублируется (интерфейс + класс с разными структурами)       | `lib/types/api.ts`, `lib/errors.ts`         |
| M12 | Только 2 UI-примитива на 43 block-компонента                         | `components/ui/`                            |
| M13 | Дублирование компонентов favorites (BrandCard x2, BrandsSection x2)  | `components/blocks/favorites/`              |

### MINOR (мешают, но не блокируют)

| #   | Проблема                                  | Файл(ы)                                   |
| --- | ----------------------------------------- | ----------------------------------------- |
| m1  | Захардкоженные категории в CategoryTabs   | `components/blocks/home/CategoryTabs.tsx` |
| m2  | lib/types/index.ts не экспортирует ui.ts  | `lib/types/index.ts`                      |
| m3  | Нет дизайн-токенов (CSS variables)        | `app/globals.css`                         |
| m4  | Dark mode закомментирован                 | `app/globals.css`                         |
| m5  | 31 из 34 страниц без loading.tsx          | `app/**/`                                 |
| m6  | never[] тип для пустых массивов           | `app/page.tsx`                            |
| m7  | Нет i18n-инфраструктуры                   | Весь проект                               |
| m8  | useItemFavorites — полная заглушка        | `lib/hooks/useItemFavorites.ts`           |
| m9  | moduleResolution: "node" вместо "bundler" | `tsconfig.json`                           |
| m10 | Leaflet CSS грузится глобально            | `app/globals.css`                         |

---

## 16. Рекомендации

### Приоритет 1 — CRITICAL (немедленно)

#### 1.1. Реализовать RTK Query endpoints через `injectEndpoints`

**Файл:** `lib/store/api.ts` + новая директория `lib/store/api/`

```typescript
// lib/store/api/catalogApi.ts
import { api } from '../api';
import type { Product, PaginatedResponse } from '@/lib/types';

export const catalogApi = api.injectEndpoints({
  endpoints: (builder) => ({
    getProducts: builder.query<PaginatedResponse<Product>, { page: number; limit: number }>({
      query: ({ page, limit }) => `/catalog/products?page=${page}&limit=${limit}`,
      providesTags: ['Products'],
    }),
    getProduct: builder.query<Product, string>({
      query: (id) => `/catalog/products/${id}`,
      providesTags: (result, error, id) => [{ type: 'Product', id }],
    }),
  }),
});

export const { useGetProductsQuery, useGetProductQuery } = catalogApi;
```

**Трудозатраты:** 2-3 дня  
**Влияние:** разблокирует весь data flow

#### 1.2. Добавить bundle analyzer

```bash
npm install --save-dev @next/bundle-analyzer
```

**Трудозатраты:** 30 минут  

#### 1.3. Добавить dynamic() для тяжёлых компонентов

**Минимум:**
```typescript
// app/checkout/pickup/page.tsx
import dynamic from 'next/dynamic';
const MapView = dynamic(() => import('@/components/blocks/checkout/MapView'), { ssr: false });
```

**Трудозатраты:** 1 день

### Приоритет 2 — MAJOR (в ближайшие спринты)

#### 2.1. Мемоизировать ProductCard

```typescript
export default React.memo(function ProductCard(...) { ... });
```

**Трудозатраты:** 15 минут  

#### 2.2. Вынести SVG-иконки из Footer

Создать `components/icons/` или использовать `lucide-react` (уже в зависимостях).

**Трудозатраты:** 1 час

#### 2.3. Унифицировать cn/cx/clsx

Заменить все 24 прямых импорта `clsx` на `import { cn } from '@/lib/format/cn'`.

**Трудозатраты:** 30 минут  

#### 2.4. Рефакторинг BottomSheet — compound component

**Трудозатраты:** 4 часа  

#### 2.5. Перевести ProductCard на next/image

**Трудозатраты:** 1 час  

#### 2.6. Перенести корзину в Redux

**Трудозатраты:** 1 день

#### 2.7. Удалить дублирующиеся компоненты favorites

Объединить `components/blocks/favorites/BrandCard.tsx` и `components/blocks/favorites/brands/BrandCard.tsx`.

**Трудозатраты:** 2 часа

#### 2.8. Унифицировать типы Product / ProductCardData

**Трудозатраты:** 2 часа

### Приоритет 3 — MINOR (при возможности)

| #   | Рекомендация                                                            | Трудозатраты |
| --- | ----------------------------------------------------------------------- | ------------ |
| 3.1 | Определить дизайн-токены в `globals.css`                                | 2 часа       |
| 3.2 | Добавить `loading.tsx` для всех маршрутов                               | 3 часа       |
| 3.3 | Переключить `moduleResolution` на `"bundler"`                           | 15 минут     |
| 3.4 | Загружать Leaflet CSS только на странице карты                          | 30 минут     |
| 3.5 | Добавить `optimizePackageImports` для `lucide-react`                    | 5 минут      |
| 3.6 | Экспортировать `ui.ts` из `lib/types/index.ts`                          | 1 минута     |
| 3.7 | Расширить библиотеку UI-примитивов (Input, List, Skeleton, Icon, Badge) | 1 неделя     |

---

## 17. Прогнозы роста и лимиты

### Текущие метрики

| Метрика                     | Значение                            |
| --------------------------- | ----------------------------------- |
| Страницы (routes)           | 34                                  |
| Компоненты                  | 43 block + 2 UI + 3 layout = **48** |
| Хуки (custom)               | 1 (заглушка) + 25 Telegram = **26** |
| RTK Query endpoints         | **0**                               |
| CSS Module файлы            | ~40                                 |
| Общий размер исходного кода | ~150 файлов                         |
| Runtime зависимости         | 7                                   |

### Лимиты без рефакторинга

| При достижении...          | Что сломается                       | Причина                         |
| -------------------------- | ----------------------------------- | ------------------------------- |
| **10+ API эндпоинтов**     | Монолитный `api.ts`                 | Нет `injectEndpoints`           |
| **50+ товаров в каталоге** | Тормоза при скролле                 | Нет `React.memo` на ProductCard |
| **100+ товаров**           | Необходим виртуализированный список | Нет react-window/virtuoso       |
| **20+ страниц с данными**  | Невозможность поддержки             | Все данные захардкожены         |
| **10+ модалок/листов**     | Неуправляемый BottomSheet           | Boolean-пропсы                  |
| **5+ тем/скинов**          | Массовый рефакторинг CSS            | Нет дизайн-токенов              |
| **3+ языков**              | Полная переработка                  | Нет i18n                        |

### При выполнении рекомендаций (Приоритет 1-2)

| Метрика               | Предел                                    |
| --------------------- | ----------------------------------------- |
| Страницы              | 100+ без проблем                          |
| Товары в каталоге     | 10,000+ (с виртуализацией)                |
| API эндпоинты         | 50+ (через `injectEndpoints`)             |
| Размер бандла         | Контролируемый (с analyzer + splitting)   |
| Команда разработчиков | 3-5 человек (при наличии типов и модулей) |

---

## 18. Итоговая оценка

### Оценка по измерениям

| Измерение                 | Оценка | Комментарий                                      |
| ------------------------- | ------ | ------------------------------------------------ |
| Рост фичей                | 6/10   | Хорошая структура, но мало UI-примитивов         |
| Переиспользуемость        | 4/10   | Дублирование, inline SVG, несогласованность      |
| RTK Query                 | 1/10   | Настроен, но пуст                                |
| Размер бандла             | 3/10   | Нет analyzer, splitting, Leaflet грузится всегда |
| Композиция компонентов    | 5/10   | Хорошие блоки, плохой BottomSheet                |
| Управление состоянием     | 5/10   | Хороший auth, плохая корзина, нет data-слоя      |
| Стили                     | 6/10   | CSS Modules работают, но нет токенов             |
| Производительность        | 3/10   | Нет memo, нет splitting, нет виртуализации       |
| Оптимизация изображений   | 4/10   | Смешанный подход img/Image                       |
| Code Splitting            | 1/10   | Полное отсутствие                                |
| API-слой                  | 6/10   | BFF-прокси отличный, но RTK Query пуст           |
| Система типов             | 6/10   | Strict mode, но дублирование типов               |
| Производительность сборки | 7/10   | Быстро благодаря малому количеству зависимостей  |

### Общая оценка масштабируемости

## 4.2 / 10

**Обоснование:** Проект имеет **хороший архитектурный фундамент** (BFF-прокси, auth-flow с mutex, Telegram SDK, App Router, TypeScript strict), но **критически не готов к масштабированию** из-за: полного отсутствия data layer (RTK Query пуст), нулевого code splitting, отсутствия мемоизации, и тотального использования захардкоженных данных. При выполнении рекомендаций Приоритета 1 оценка может вырасти до **6.5/10**, а при выполнении Приоритета 2 — до **8/10**.

---

*Аудит проведён на основании анализа ~150 исходных файлов проекта.*
