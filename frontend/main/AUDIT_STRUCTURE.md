# Аудит структуры проекта — Frontend Main

**Дата:** 2026-04-05
**Компонент:** frontend-main (Telegram Mini App)
**Стек:** Next.js 16, TypeScript, React 19, Redux Toolkit
**Аудитор:** Claude Opus 4.6

---

## Содержание

1. [Общее резюме](#общее-резюме)
2. [Карта текущей структуры](#карта-текущей-структуры)
3. [Критические проблемы](#критические-проблемы)
4. [Серьёзные проблемы](#серьёзные-проблемы)
5. [Мелкие проблемы](#мелкие-проблемы)
6. [Анализ по категориям](#анализ-по-категориям)
7. [Рекомендации с приоритетами](#рекомендации-с-приоритетами)
8. [Итоговая оценка](#итоговая-оценка)

---

## Общее резюме

Проект имеет **узнаваемую и логичную базовую структуру** для Next.js App Router: корневые каталоги `app/`, `components/`, `lib/` правильно разделяют маршрутизацию, UI и бизнес-логику. Telegram SDK обёрнут профессионально. Типизация строгая (`strict: true`).

Однако проект находится на **ранней стадии разработки с серьёзным техническим долгом**: страницы содержат по 750–1160 строк монолитного кода с дублированием утилит, RTK Query не имеет ни одного эндпоинта, хуки `useCart` и `useItemFavorites` полностью заглушены, а barrel-экспорты отсутствуют для большинства каталогов.

**Ключевые цифры:**

| Метрика | Значение |
|---------|----------|
| Общее количество исходных файлов (TS/TSX/CSS) | ~75 |
| Максимальный размер файла | `app/search/page.tsx` — ~1160 строк |
| Файлов > 400 строк | 7 (search, product, trash, Footer, TelegramProvider, lib/telegram/types, globals.css) |
| Дублированных утилит в страницах | 5+ функций, повторённых 2–3 раза |
| RTK Query эндпоинтов | 0 (пустой `endpoints: () => ({})`) |
| Заглушенных хуков | 2 (useCart, useItemFavorites) |
| Barrel-файлов (index.ts) | 2 из ~15 каталогов |

---

## Карта текущей структуры

```
frontend/main/
├── app/                          # App Router — страницы и API-маршруты
│   ├── layout.tsx                # Корневой layout (Provider tree)
│   ├── page.tsx                  # Главная страница
│   ├── globals.css               # Глобальные стили (~280 строк)
│   ├── api/
│   │   ├── auth/
│   │   │   ├── telegram/route.ts # Авторизация через Telegram initData
│   │   │   ├── refresh/route.ts  # Обновление JWT токенов
│   │   │   └── logout/route.ts   # Выход
│   │   ├── backend/
│   │   │   └── [...path]/route.ts # Catch-all BFF прокси к бэкенду
│   │   └── dadata/
│   │       ├── suggest/address/route.ts
│   │       └── clean/address/route.ts
│   ├── catalog/page.tsx
│   ├── checkout/page.tsx
│   ├── favorites/page.tsx
│   ├── invite-friends/page.tsx
│   ├── poizon/page.tsx
│   ├── product/[id]/page.tsx     # ~790 строк, монолитный
│   ├── profile/
│   │   ├── page.tsx
│   │   ├── _shared/
│   │   │   ├── ComingSoon.tsx
│   │   │   └── comingSoon.module.css  # ⚠ Несовпадение регистра
│   │   ├── delivery-addresses/page.tsx
│   │   ├── loyalty/page.tsx
│   │   ├── orders/page.tsx
│   │   ├── personal-info/page.tsx
│   │   └── support/page.tsx
│   ├── promo/page.tsx
│   ├── search/page.tsx           # ~1160 строк, крупнейший файл
│   └── trash/page.tsx            # ~753 строки
│
├── components/
│   ├── blocks/                   # Доменные компоненты
│   │   ├── cart/
│   │   │   └── useCart.ts        # ⚠ Полная заглушка
│   │   ├── catalog/
│   │   │   └── CategoryTabs.tsx
│   │   ├── favorites/
│   │   │   └── FavoritesList.tsx
│   │   ├── home/
│   │   │   ├── FriendsSection.tsx      # ⚠ Двойной импорт cn + cx
│   │   │   ├── HomeDeliveryStatusCard.tsx
│   │   │   └── ProductSection.tsx
│   │   ├── product/
│   │   │   ├── ProductCard.tsx         # ⚠ Двойной импорт cn + cx
│   │   │   └── ProductImageGallery.tsx
│   │   ├── promo/
│   │   │   └── promo-points.tsx        # ⚠ kebab-case (должен быть PascalCase)
│   │   ├── reviews/
│   │   │   └── ReviewItem.tsx
│   │   ├── search/
│   │   │   └── SearchBar.tsx
│   │   └── telegram/
│   │       ├── TelegramAuthBootstrap.tsx
│   │       └── WebViewErrorAlert.tsx   # ⚠ Текст на узбекском языке
│   ├── ios/
│   │   └── InputFocusFix.tsx
│   ├── layout/
│   │   ├── Footer.tsx            # ~449 строк (инлайн SVG)
│   │   └── Layout.tsx
│   ├── providers/
│   │   └── StoreProvider.tsx
│   └── ui/
│       ├── BottomSheet.tsx       # ⚠ Feature-specific boolean props
│       ├── BottomSheet.module.css
│       ├── Button.tsx
│       └── Button.module.css
│
├── lib/
│   ├── auth/
│   │   ├── cookie-helpers.ts     # Серверные утилиты для cookie
│   │   ├── cookies.ts            # Константы имён cookie + клиентский logout()
│   │   └── debug.ts              # Debug-авторизация для разработки
│   ├── errors.ts                 # AppError → ApiError, NetworkError
│   ├── format/
│   │   ├── brand-image.ts
│   │   ├── cn.ts                 # clsx-обёртка
│   │   ├── date.ts
│   │   ├── price.ts
│   │   └── product-image.ts
│   ├── hooks/
│   │   └── useItemFavorites.ts   # ⚠ Полная заглушка
│   ├── store/
│   │   ├── api.ts                # RTK Query — 0 эндпоинтов
│   │   ├── authSlice.ts
│   │   ├── hooks.ts
│   │   └── store.ts
│   ├── telegram/
│   │   ├── index.ts              # Barrel-экспорт (хороший пример)
│   │   ├── types.ts              # ~1210 строк типов Telegram Bot API
│   │   ├── core.ts
│   │   ├── TelegramProvider.tsx
│   │   └── hooks/                # 25+ хуков для Telegram SDK
│   │       ├── useBackButton.ts
│   │       ├── useBiometric.ts
│   │       ├── useCloudStorage.ts
│   │       ├── useFullscreen.ts
│   │       ├── useHaptic.ts
│   │       ├── useMainButton.ts
│   │       ├── usePopup.ts
│   │       ├── useQrScanner.ts
│   │       ├── useSettingsButton.ts
│   │       ├── useTelegram.ts
│   │       ├── useTheme.ts
│   │       └── useViewport.ts
│   └── types/
│       ├── index.ts              # Barrel (⚠ не экспортирует ui.ts)
│       ├── api.ts
│       ├── auth.ts
│       ├── catalog.ts
│       ├── user.ts
│       ├── ui.ts                 # ⚠ Не экспортируется из barrel
│       └── telegram-globals.d.ts # ⚠ Дублирует Window из telegram/types.ts
│
├── public/
│   ├── fonts/                    # Inter (4 начертания), BebasNeue
│   │   ├── Inter-Regular.woff2
│   │   ├── Inter-Medium.woff2
│   │   ├── Inter-SemiBold.woff2
│   │   ├── Inter-Bold.woff2
│   │   └── BebasNeue-Bold.woff2
│   ├── icons/
│   │   ├── catalog/              # Иконки категорий
│   │   ├── global/               # Общие иконки
│   │   ├── invite-friends/
│   │   ├── product/
│   │   ├── profile/
│   │   └── promo/
│   └── img/
│       ├── fauriteHeadrtImg.png  # ⚠ Опечатка: faurite → favorite, Headrt → Heart
│       ├── returnIocn.svg        # ⚠ Опечатка: Iocn → Icon
│       ├── Frame 37083.svg       # ⚠ Пробелы в имени файла
│       └── ...
│
├── scripts/
│   ├── audit-unused-public-assets.mjs
│   └── audit-unused-source-files.mjs
│
├── docs/                         # ⚠ Артефакты тулинга, не документация
│
├── leaflet.d.ts                  # ⚠ Должен быть в lib/types/
├── middleware.ts                  # Edge middleware (CSRF + Security headers)
├── next.config.ts
├── tsconfig.json
├── postcss.config.mjs            # ⚠ Пустой — нет плагинов
├── eslint.config.mjs
├── package.json
└── README.md                     # ⚠ Дефолтный boilerplate + "telegramsotre"
```

---

## Критические проблемы

### C1. Монолитные страницы с массивным дублированием кода

**Серьёзность:** КРИТИЧЕСКАЯ
**Влияние:** Поддерживаемость, тестируемость, ошибки при рассинхронизации копий

Три страницы содержат от 750 до 1160 строк кода с **локальными переопределениями утилит**, которые уже существуют в `lib/format/`:

| Файл | Строк | Дублированные функции |
|------|-------|----------------------|
| `app/search/page.tsx` | ~1160 | `localGetProductPhotoCandidates` (дубль `lib/format/product-image.ts`), `formatPrice` (дубль `lib/format/price.ts`), локальные интерфейсы дублируют `lib/types/catalog.ts` |
| `app/trash/page.tsx` | ~753 | `formatRub`, `pluralizeItemsRu`, `formatRubPrice` (дубль `lib/format/price.ts`), `getProductPhotoCandidates` (дубль `lib/format/product-image.ts`), `mapApiProductToCard` |
| `app/product/[id]/page.tsx` | ~790 | Локальные интерфейсы `ApiProduct`, `ProductCard`, `Review`, `InfoCardItem`, `BrandCarouselItem`, `CategoryWithTypes`, `BrandItem`; инлайн `copyText`; `extractProductsList`, `mapApiProductToCard`, `buildDeliveryTextFromProduct` |

**Конкретные дублирования:**

```
lib/format/price.ts::formatRubPrice     ←→  app/trash/page.tsx::formatRub
lib/format/price.ts::formatRubPrice     ←→  app/search/page.tsx::formatPrice
lib/format/product-image.ts::getProductPhotoCandidates  ←→  app/trash/page.tsx::getProductPhotoCandidates
lib/format/product-image.ts::getProductPhotoCandidates  ←→  app/search/page.tsx::localGetProductPhotoCandidates
lib/types/catalog.ts::Product           ←→  app/product/[id]/page.tsx::ApiProduct
lib/types/catalog.ts::ProductCardData?  ←→  app/product/[id]/page.tsx::ProductCard
```

Кроме того, `app/trash/page.tsx` импортирует `cn` напрямую из `"clsx"` вместо `@/lib/format/cn`.

### C2. RTK Query без единого эндпоинта

**Серьёзность:** КРИТИЧЕСКАЯ
**Файл:** `lib/store/api.ts`

```typescript
endpoints: () => ({}),
```

RTK Query настроен полностью (createApi, baseQueryWithReauth, mutex-based token refresh, tag types), но **ни один endpoint не определён**. Все страницы используют статические/захардкоженные данные вместо API-вызовов. Определены tag types (`User`, `Products`, `Product`, `Categories`, `Brands`), но инвалидировать нечего.

Это означает, что вся инфраструктура RTK Query — мёртвый код до момента добавления эндпоинтов.

### C3. Полностью заглушенные хуки без реализации

**Серьёзность:** КРИТИЧЕСКАЯ

| Файл | Проблема |
|------|----------|
| `components/blocks/cart/useCart.ts` | Все операции (add, remove, update, clear) — no-op. Состояние — пустой массив. Комментарий: "TODO: подключить к API". |
| `lib/hooks/useItemFavorites.ts` | Возвращает пустые Set/Array и no-op коллбэки. Комментарий: "TODO: connect to API". |

Страницы, использующие эти хуки, выглядят функциональными для пользователя, но **ничего не делают**.

---

## Серьёзные проблемы

### M1. Непоследовательное использование `cn` / `clsx`

**Серьёзность:** СЕРЬЁЗНАЯ
**Влияние:** Непоследовательность, нарушение конвенции из CLAUDE.md

В проекте есть каноническая утилита `lib/format/cn.ts`, которая оборачивает `clsx`. Однако:

| Файл | Импортирует |
|------|------------|
| `components/blocks/home/FriendsSection.tsx` | `cn` из `@/lib/format/cn` **И** `cx` из `"clsx"` (оба!) |
| `components/blocks/product/ProductCard.tsx` | `cn` из `@/lib/format/cn` **И** `cx` из `"clsx"` (оба!) |
| `app/trash/page.tsx` | `cn` из `"clsx"` напрямую (минуя lib) |

Должен использоваться **только** `cn` из `@/lib/format/cn`.

### M2. Дублирование глобальных типов Window

**Серьёзность:** СЕРЬЁЗНАЯ
**Файлы:**
- `lib/telegram/types.ts` (строки ~1140–1210) — `declare global { interface Window { Telegram: { WebApp: WebApp } } }`
- `lib/types/telegram-globals.d.ts` — Расширяет `Window` с `__LM_TG_INIT_DATA__`, `__LM_TG_INIT_DATA_UNSAFE__`, `__LM_BROWSER_DEBUG_AUTH__`, `__LM_BROWSER_DEBUG_USER__`, а также **повторно** объявляет `Telegram.WebApp`

Два файла расширяют `Window` с перекрывающимися полями. Это может вызвать конфликты типов и путаницу при обслуживании.

### M3. `lib/types/ui.ts` не экспортируется из barrel

**Серьёзность:** СЕРЬЁЗНАЯ
**Файлы:**
- `lib/types/index.ts` — экспортирует `api`, `auth`, `catalog`, `user`
- `lib/types/ui.ts` — содержит `ProductCardData`, но **не включён** в barrel

Интерфейс `ProductCardData` определён, но не доступен через `@/lib/types`. Любой, кто импортирует через barrel, не увидит этот тип.

### M4. BottomSheet с feature-specific пропсами

**Серьёзность:** СЕРЬЁЗНАЯ
**Файл:** `components/ui/BottomSheet.tsx`

Общий UI-компонент имеет булевые пропсы, привязанные к конкретным фичам:

```typescript
isTypeModule?: boolean;
isFilter?: boolean;
isReview?: boolean;
isPromocodePage?: boolean;
```

Это нарушает принцип разделения ответственности. Универсальный компонент не должен знать о бизнес-контексте (промокоды, отзывы, фильтры).

### M5. Отсутствие barrel-экспортов для компонентных каталогов

**Серьёзность:** СЕРЬЁЗНАЯ
**Влияние:** Длинные пути импорта, сложность рефакторинга

Barrel-экспорты (`index.ts`) существуют только в:
- `lib/telegram/index.ts` — отличный пример
- `lib/types/index.ts` — неполный (см. M3)

**Отсутствуют** в:
- `components/ui/` — нет index.ts
- `components/layout/` — нет index.ts
- `components/blocks/` и все поддиректории — нет index.ts
- `lib/format/` — нет index.ts
- `lib/auth/` — нет index.ts
- `lib/store/` — нет index.ts
- `lib/hooks/` — нет index.ts

Следствие — импорты выглядят так:
```typescript
import { Button } from "@/components/ui/Button";
import { Footer } from "@/components/layout/Footer";
import { formatRubPrice } from "@/lib/format/price";
```
вместо:
```typescript
import { Button } from "@/components/ui";
import { Footer } from "@/components/layout";
import { formatRubPrice } from "@/lib/format";
```

### M6. WebViewErrorAlert — текст на узбекском языке

**Серьёзность:** СЕРЬЁЗНАЯ
**Файл:** `components/blocks/telegram/WebViewErrorAlert.tsx`

Компонент показывает alert:
> "Telegram WebApp topilmadi. Ilovani Telegram ichida oching."

Это **узбекский язык**, а не русский. Приложение целиком на русском (`<html lang="ru">`). Текст должен быть:
> "Telegram WebApp не найден. Откройте приложение внутри Telegram."

### M7. Захардкоженные данные дублированы между страницами

**Серьёзность:** СЕРЬЁЗНАЯ
**Файлы:** `app/page.tsx`, `app/product/[id]/page.tsx`

Массив `infoCards` (иконка + заголовок + описание, 4 элемента) **идентично дублирован** на главной странице и на странице продукта. Также дублированы моковые отзывы. При изменении одной копии вторая рассинхронизируется.

### M8. Footer содержит ~300 строк инлайн SVG

**Серьёзность:** СЕРЬЁЗНАЯ
**Файл:** `components/layout/Footer.tsx` (~449 строк)

6 SVG-иконок (IconHome, IconPoizon, IconCatalog, IconFavorites, IconTrash, IconProfile), каждая с filled/unfilled вариантами, определены как инлайн компоненты внутри Footer. Это раздувает файл и затрудняет переиспользование иконок.

Иконки должны быть вынесены в `components/ui/icons/` или использоваться через `lucide-react` (уже в зависимостях).

---

## Мелкие проблемы

### m1. Непоследовательное именование файлов

| Файл | Проблема |
|------|----------|
| `components/blocks/promo/promo-points.tsx` | kebab-case вместо PascalCase (`PromoPoints.tsx`) |
| `app/profile/_shared/comingSoon.module.css` | camelCase, тогда как компонент — `ComingSoon.tsx` (PascalCase) |

### m2. `leaflet.d.ts` в корне проекта

**Файл:** `/leaflet.d.ts`

Файл объявлений типов для Leaflet размещён в корне проекта вместо `lib/types/leaflet.d.ts`. Все остальные типы живут в `lib/types/`.

### m3. Пустой `postcss.config.mjs`

**Файл:** `postcss.config.mjs`

```javascript
const config = { plugins: {} };
```

Конфигурация PostCSS без единого плагина. Next.js включает autoprefixer по умолчанию, поэтому файл можно удалить или добавить нужные плагины.

### m4. README.md — дефолтный boilerplate

**Файл:** `README.md`

Содержит стандартный текст `create-next-app` с добавленной строкой:
```
# telegramsotre
```

Опечатка: "sotre" → "store". README не описывает проект.

### m5. Опечатки в именах public-ассетов

| Файл | Опечатка |
|------|----------|
| `public/img/fauriteHeadrtImg.png` | "faurite" → "favorite", "Headrt" → "Heart" |
| `public/img/returnIocn.svg` | "Iocn" → "Icon" |
| `public/img/Frame 37083.svg` | Пробелы в имени файла — может ломать URL |

### m6. `next.config.ts` — только тестовый remote pattern

**Файл:** `next.config.ts`

Единственный remote pattern — `i.pravatar.cc` (тестовые аватары). Для продакшена потребуются реальные домены.

### m7. `docs/` — артефакты тулинга

Каталог `docs/` содержит файлы от Superpowers/планирования Claude, а не проектную документацию. Следует очистить или добавить в `.gitignore`.

### m8. Компонент `app/page.tsx` использует статические пустые массивы

**Файл:** `app/page.tsx`

```typescript
const products: never[] = [];
```

Главная страница объявляет пустые массивы для продуктов с комментарием, что API ещё не подключено. При этом `ProductSection` с пустым массивом рендерит пустую секцию.

---

## Анализ по категориям

### 1. Организация директорий и размещение файлов

**Оценка: 6/10**

Базовая структура (`app/`, `components/`, `lib/`) соответствует стандартам Next.js App Router. Разделение на `blocks/`, `ui/`, `layout/`, `providers/` в `components/` — хорошая практика. Telegram SDK выделен в отдельный подмодуль `lib/telegram/` с barrel-экспортом.

Проблемы:
- `leaflet.d.ts` в корне вместо `lib/types/`
- `docs/` — мусор
- Отсутствует каталог для shared mock data/constants
- Хук `useCart` расположен в `components/blocks/cart/`, хотя это бизнес-логика (лучше в `lib/hooks/` или `features/`)

### 2. Границы модулей и разделение ответственности

**Оценка: 3/10**

Основная проблема — **страницы совмещают роли контроллера, модели и представления**:
- `app/search/page.tsx`: 20+ useState, фильтрация, сортировка, маппинг данных, рендеринг — всё в одном файле
- `app/product/[id]/page.tsx`: 7 локальных интерфейсов, 3 helper-функции, API-маппинг, инлайн clipboard, рендеринг
- `app/trash/page.tsx`: повторяет утилиты из lib, содержит бизнес-логику корзины

Должно быть:
- Страница → только композиция компонентов и data fetching
- Бизнес-логика → хуки в `lib/hooks/` или `features/`
- UI-маппинг → утилиты в `lib/format/`

### 3. Соглашения об именовании

**Оценка: 7/10**

В целом **PascalCase** для компонентов, **camelCase** для утилит и хуков. Исключения:
- `promo-points.tsx` — единственный kebab-case компонент
- `comingSoon.module.css` — camelCase вместо PascalCase для пары к `ComingSoon.tsx`
- Типы в `lib/types/` — все lowercase (api.ts, catalog.ts) — это нормально для типов

### 4. Barrel-экспорты и index-файлы

**Оценка: 3/10**

Только `lib/telegram/index.ts` является полноценным barrel-экспортом. `lib/types/index.ts` — неполный (пропущен `ui.ts`). Все остальные каталоги не имеют index-файлов, что приводит к длинным путям импорта и делает рефакторинг болезненным.

### 5. Ко-локация (co-location)

**Оценка: 6/10**

Положительные примеры:
- `components/ui/Button.tsx` + `Button.module.css` — рядом
- `components/ui/BottomSheet.tsx` + `BottomSheet.module.css` — рядом
- `app/profile/_shared/` — общие компоненты для подстраниц профиля

Проблемы:
- CSS модули для страниц живут отдельно (нет ко-локации стилей со страницами)
- Хук `useCart` находится в `components/blocks/cart/`, но больше подходит для `lib/hooks/`
- Mock данные разбросаны по страницам вместо одного места

### 6. Мёртвый код и неиспользуемые файлы

**Оценка: 5/10**

| Категория | Примеры |
|-----------|---------|
| Заглушенные хуки | `useCart.ts`, `useItemFavorites.ts` — 100% мёртвый код |
| Неиспользуемый тип | `lib/types/ui.ts::ProductCardData` — не экспортируется из barrel |
| Пустая инфраструктура | RTK Query endpoints — пустой объект |
| Пустая конфигурация | `postcss.config.mjs` — нет плагинов |
| Дубли вместо реюза | 5+ функций, дублированных в страницах |

### 7. Конфигурационные файлы

**Оценка: 7/10**

| Файл | Статус |
|------|--------|
| `tsconfig.json` | Хорошо настроен: strict, baseUrl, paths |
| `next.config.ts` | Минимален, но адекватен для текущей стадии |
| `eslint.config.mjs` | Стандартный core-web-vitals |
| `postcss.config.mjs` | Пустой — можно удалить |
| `package.json` | Чист, зависимости обоснованы |
| `middleware.ts` | Хорошо реализован (CSRF + headers) |

### 8. Организация public-ассетов

**Оценка: 6/10**

Структура `public/fonts/`, `public/icons/`, `public/img/` — логичная. Иконки разделены по доменам (catalog, profile, promo). Шрифты самохостятся с корректными woff2 файлами.

Проблемы: опечатки в именах, пробелы в имени файла (`Frame 37083.svg`), тестовые ассеты без пометки.

### 9. Поддержание flat-структуры (без src/)

**Оценка: 7/10**

Решение не использовать `src/` — стандартное для Next.js App Router. Корень проекта не перегружен: `app/`, `components/`, `lib/` чётко разделены. Конфигурационные файлы в корне — неизбежны.

Потенциальная проблема: при росте проекта корень может стать перегруженным. Стоит следить за количеством корневых каталогов и вовремя рассмотреть введение `features/` или `modules/`.

---

## Рекомендации с приоритетами

### Приоритет 1 — Критические (исправить немедленно)

| # | Рекомендация | Обоснование |
|---|-------------|-------------|
| R1 | **Декомпозиция страниц search, product, trash** — вынести бизнес-логику в хуки, UI-маппинг в утилиты, подкомпоненты в отдельные файлы | Страницы по 750–1160 строк нечитаемы и нетестируемы |
| R2 | **Устранить дублирование утилит** — удалить локальные `formatRub`, `getProductPhotoCandidates`, `mapApiProductToCard` из страниц, использовать `@/lib/format/*` | 5+ функций продублированы 2–3 раза, рассинхронизация неизбежна |
| R3 | **Реализовать RTK Query endpoints** или удалить инфраструктуру RTK Query, если не планируется использовать | Пустой `endpoints: () => ({})` — мёртвый код |

### Приоритет 2 — Серьёзные (исправить в ближайшем спринте)

| # | Рекомендация | Обоснование |
|---|-------------|-------------|
| R4 | **Унифицировать использование `cn`** — удалить все прямые импорты `clsx`/`cx`, использовать только `@/lib/format/cn` | Непоследовательность в 3+ файлах |
| R5 | **Добавить barrel-экспорты** для `components/ui/`, `components/layout/`, `lib/format/`, `lib/auth/`, `lib/store/` | Упрощает импорты и рефакторинг |
| R6 | **Объединить типы Window** — удалить дублирование между `lib/telegram/types.ts` и `lib/types/telegram-globals.d.ts` | Два файла расширяют один и тот же интерфейс |
| R7 | **Рефакторинг BottomSheet** — заменить feature-specific boolean props на `variant` enum или composition pattern | Нарушение SRP в UI-компоненте |
| R8 | **Вынести SVG-иконки из Footer** — в `components/ui/icons/` или использовать `lucide-react` | 300 строк инлайн SVG в одном файле |
| R9 | **Исправить язык WebViewErrorAlert** — на русский | Ошибка локализации |
| R10 | **Вынести mock-данные** в `lib/mocks/` или `__mocks__/` — единый источник для infoCards, reviews, placeholder products | Дублированы между страницами |

### Приоритет 3 — Мелкие (исправить по возможности)

| # | Рекомендация | Обоснование |
|---|-------------|-------------|
| R11 | Переименовать `promo-points.tsx` → `PromoPoints.tsx` | Консистентность |
| R12 | Переименовать `comingSoon.module.css` → `ComingSoon.module.css` | Консистентность |
| R13 | Переместить `leaflet.d.ts` → `lib/types/leaflet.d.ts` | Все типы в одном месте |
| R14 | Удалить `postcss.config.mjs` или добавить нужные плагины | Пустой конфиг |
| R15 | Обновить `README.md` с описанием проекта | Дефолтный boilerplate бесполезен |
| R16 | Исправить опечатки в именах public-ассетов | `fauriteHeadrtImg`, `returnIocn`, `Frame 37083` |
| R17 | Добавить `ui.ts` в `lib/types/index.ts` barrel | Недоступный тип |
| R18 | Очистить `docs/` от артефактов тулинга | Мусор в репозитории |
| R19 | Реализовать или удалить заглушенные хуки `useCart` и `useItemFavorites` | Мёртвый код |

---

## Итоговая оценка

### Оценка: 4.5 / 10

| Категория | Оценка | Вес | Взвешенная |
|-----------|--------|-----|------------|
| Организация директорий | 6/10 | 15% | 0.90 |
| Границы модулей / SoC | 3/10 | 20% | 0.60 |
| Именование | 7/10 | 10% | 0.70 |
| Barrel-экспорты | 3/10 | 10% | 0.30 |
| Ко-локация | 6/10 | 10% | 0.60 |
| Мёртвый код | 5/10 | 15% | 0.75 |
| Конфигурация | 7/10 | 10% | 0.70 |
| Public-ассеты | 6/10 | 5% | 0.30 |
| Flat-структура | 7/10 | 5% | 0.35 |
| **Итого** | | **100%** | **5.20** |

> **Корректировка:** −0.7 за критическое дублирование кода и пустую RTK Query инфраструктуру.
>
> **Финальная оценка: 4.5 / 10**

### Резюме

Проект имеет **хороший архитектурный фундамент** (правильная структура каталогов, TypeScript strict, RTK Query setup, профессиональная обёртка Telegram SDK), но **страдает от ранней стадии разработки** с монолитными страницами, дублированием кода и незавершённой интеграцией с API. Основные усилия по рефакторингу должны быть направлены на декомпозицию трёх крупнейших страниц и устранение дублирования утилит.
