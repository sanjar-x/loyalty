# Аудит чистоты кода — frontend/main

**Дата:** 2026-04-05
**Компонент:** frontend-main (Next.js 16 + TypeScript + React 19 + Redux Toolkit)
**Аудитор:** Claude Opus 4.6

---

## Резюме

| Метрика                    | Значение     |
| -------------------------- | ------------ |
| Файлов .tsx                | 91           |
| Файлов .ts                 | 63           |
| Файлов .module.css         | 69           |
| Файлов .css (глобальных)   | 1            |
| **Критических проблем**    | **5**        |
| **Серьёзных проблем**      | **14**       |
| **Незначительных проблем** | **18**       |
| **Оценка**                 | **4.5 / 10** |

Проект находится в стадии прототипирования: множество страниц используют захардкоженные данные и стабы вместо API. Основные проблемы — массивные нарушения DRY, грубые баги в Telegram-хуках, повсеместная хаотичность CSS-классов, несоблюдение собственных конвенций по использованию `cn()`, и присутствие отладочного кода в production-коде.

---

## 1. Критические проблемы (Critical)

### 1.1. BUG: Неправильная проверка фичи в useGyroscope и useDeviceOrientation

**Файлы:**
- `lib/telegram/hooks/useGyroscope.ts:8`
- `lib/telegram/hooks/useDeviceOrientation.ts:11`

Оба хука проверяют `supportsFeature('Accelerometer')` вместо своей собственной фичи:

```ts
// useGyroscope.ts:8 — должен проверять 'Gyroscope'
if (!supportsFeature('Accelerometer')) return null;

// useDeviceOrientation.ts:11 — должен проверять 'DeviceOrientation'
if (!supportsFeature('Accelerometer')) return null;
```

**Последствия:** На устройствах, поддерживающих гироскоп/ориентацию, но не акселерометр, хуки молча вернут `null`. И наоборот — на устройствах без гироскопа будет попытка обращения к API, если акселерометр доступен.

---

### 1.2. BUG: `color: 13px` — невалидное значение CSS property

**Файлы (30+ вхождений):**
- `components/blocks/favorites/BrandCard.module.css:22,29`
- `components/blocks/favorites/brands/BrandCard.module.css:41,47`
- `components/blocks/favorites/brands/AllBrandsList.module.css:55,61`
- `components/blocks/favorites/BrandsSection.module.css:16,25`
- `components/blocks/favorites/brands/FavoriteBrandsSection.module.css:11`
- `components/blocks/favorites/brands/BrandsSearch.module.css:20`
- `app/trash/page.module.css` — 17 вхождений (строки 50, 92, 112, 118, 174, 227, 302, 434, 462, 468, 478, 491, 502, 512, 551, 567, 583, 589, 603, 658)

```css
/* Пример из BrandCard.module.css:22 */
.c5 {
  color: 13px;       /* <-- невалидное значение! Должно быть font-size: 13px */
  font-weight: 600;
  color: #000000;    /* Это свойство перезаписывает невалидное выше */
}
```

Пиксельное значение не является допустимым значением для `color`. Браузер его проигнорирует. Во многих случаях ниже идёт корректное объявление `color`, перезаписывающее ошибку, но само присутствие невалидных свойств — показатель механически сгенерированного/мигрированного CSS без проверки.

---

### 1.3. console.log в production-коде

**Файл:** `app/profile/reviews/[brand]/page.tsx`

```tsx
// строка 545:
onClick={() => console.log("buyNow", { brand })}

// строка 552:
onClick={() => console.log("addToCart", { brand, priceRub })}
```

Отладочные `console.log` остались в обработчиках кнопок «Купить сейчас» и «В корзину». В production-сборке логи будут видны в DevTools пользователя.

---

### 1.4. Опечатка в данных — «Аксессуры» вместо «Аксессуары»

**Файлы:**
- `app/catalog/page.tsx:47` — `normalize("Аксессуры")`
- `app/catalog/[category]/page.tsx:53` — `accessories: "Аксессуры"`

```ts
// catalog/page.tsx:47 — дублированная запись с опечаткой
[normalize("Аксессуры")]: {
  imageSrc: "/icons/catalog/catalog-icon-3.svg",
  altText: "Аксессуары",
},
[normalize("Аксессуары")]: {  // строка 51 — корректная запись перезаписывает
  imageSrc: "/icons/catalog/catalog-icon-3.svg",
  altText: "Аксессуары",
},
```

В файле `catalog/page.tsx` ошибка замаскирована дублированием, но в `[category]/page.tsx` привязка `accessories: "Аксессуры"` означает, что при навигации по legacy URL `/catalog/accessories` категория не будет найдена.

---

### 1.5. Опечатка на странице Poizon

**Файл:** `app/poizon/page.tsx:16`

```tsx
<p className={styles.subtitle}>
  Скоро здесь появится возомжность покупать оригинальные товары
</p>
```

Слово «возомжность» — опечатка, которую увидит каждый пользователь на видной странице.

---

## 2. Серьёзные проблемы (Major)

### 2.1. Нарушение конвенции: прямой импорт `clsx` вместо `cn()` (24 файла)

Проект определяет каноническую утилиту `cn()` в `lib/format/cn.ts` (обёртка над `clsx`). Документация CLAUDE.md предписывает: **всегда использовать `cn()` из `@/lib/format/cn`**.

**Файлы, нарушающие конвенцию (импортируют `clsx` напрямую):**

| Импорт                                                     | Файлы                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `import cx from "clsx"` (16 файлов)                        | `ProductCard.tsx`, `ProductImageGallery.tsx`, `ProductInfo.tsx`, `ProductReviews.tsx`, `ProductSizes.tsx`, `ProductAddToCart.tsx`, `ProductBrandsCarousel.tsx`, `FriendsSection.tsx`, `BrandCard.tsx` (x2), `BrandsSection.tsx`, `EmptyState.tsx`, `AllBrandsList.tsx`, `BrandsSearch.tsx`, `FavoriteBrandsSection.tsx`, `ProfileHeader.tsx`, `ProfileMenuItem.tsx`, `ProfileMenuSection.tsx` |
| `import cn from "clsx"` (3 файла)                          | `trash/page.tsx`, `checkout/page.tsx`, `checkout/pickup/page.tsx`                                                                                                                                                                                                                                                                                                                             |
| `import clsx from "clsx"` (1 файл)                         | `profile/reviews/page.tsx`                                                                                                                                                                                                                                                                                                                                                                    |
| `import cx from "clsx"` в `profile/page.tsx` (1 файл)      | `profile/page.tsx`                                                                                                                                                                                                                                                                                                                                                                            |
| `import cx from "clsx"` в `product/[id]/page.tsx` (1 файл) | `product/[id]/page.tsx`                                                                                                                                                                                                                                                                                                                                                                       |

**Правильный импорт (8 файлов):** `CategoryTabs.tsx`, `FriendsSection.tsx` (двойной — cx + cn), `invite-friends/page.tsx`, `invite-friends/loading.tsx`, `search/page.tsx`, `promo/page.tsx`

Три файла (`trash/page.tsx`, `checkout/page.tsx`, `checkout/pickup/page.tsx`) ещё и используют алиас `cn` для прямого `clsx`, что создаёт визуальную иллюзию использования конвенционального `cn` — самый запутывающий вариант.

---

### 2.2. Криптогенные имена CSS-классов (c1, c2, tw1, tw2...)

**435 классов** вида `.c1`–`.c84` и **200 классов** вида `.tw1`–`.tw40` обнаружены в **22 CSS-модулях**.

Наиболее пострадавшие файлы:
- `app/checkout/page.module.css` — 163 класса `.cN` + 67 классов `.twN`
- `app/checkout/pickup/page.module.css` — 89 `.cN` + 51 `.twN`
- `app/trash/page.module.css` — 84 `.cN` + 39 `.twN`

Семантические имена (`.root`, `.card`, `.title`, `.imageWrap`) используются в других частях проекта, показывая, что это не намеренная конвенция, а результат миграции/автоконвертации.

---

### 2.3. Массовое дублирование утилитарных функций

#### 2.3.1. `formatRub()` — 8 независимых реализаций

Одна и та же функция `formatRub(amount: number): string` переопределена локально в:
- `app/trash/page.tsx:20`
- `app/profile/orders/OrdersClient.tsx:53`
- `app/profile/orders/[id]/OrderDetailsClient.tsx:50`
- `app/profile/returns/page.tsx:56`
- `app/profile/returns/create/CreateReturnClient.tsx`
- `app/profile/returns/request/[id]/ReturnRequestClient.tsx`
- `app/checkout/page.tsx`
- `app/profile/reviews/[brand]/page.tsx`

При этом в `lib/format/price.ts` уже есть `formatRubPrice()`.

#### 2.3.2. `pluralizeRu()` / `pluralizeItemsRu()` — 3 реализации

- `app/profile/orders/OrdersClient.tsx:61`
- `app/trash/page.tsx:29`
- `app/checkout/page.tsx`

#### 2.3.3. `copyText()` — 4 реализации (clipboard с fallback)

Идентичный код с textarea-fallback для clipboard API:
- `app/invite-friends/InviteLinkActions.tsx:19`
- `app/invite-friends/PromoCouponCard.tsx:25`
- `app/profile/promocodes/page.tsx:47`
- `app/product/[id]/page.tsx`

#### 2.3.4. `asNonEmptyTrimmedString()` + `asSafeImageSrc()` — 2 копии

- `app/profile/page.tsx:9,15`
- `app/profile/settings/page.tsx:11,17`

#### 2.3.5. `getLetter()` — 2 копии

- `components/blocks/favorites/brands/AllBrandsList.tsx:18`
- `components/blocks/catalog/BrandsList.tsx:17`

#### 2.3.6. `normalize()` — 3+ копии

Разные варианты функции нормализации строк в:
- `app/catalog/page.tsx:27`
- `app/catalog/[category]/page.tsx:25`
- `app/search/page.tsx:131`

#### 2.3.7. `ImgWithFallback` — 2 копии компонента

- `components/blocks/favorites/BrandCard.tsx:6`
- `components/blocks/favorites/brands/BrandCard.tsx:6`

Полностью идентичные реализации.

#### 2.3.8. `getProductPhotoCandidates()` — 2+ копии

Локальная версия в `app/trash/page.tsx:84` и `app/search/page.tsx:491` при наличии каноничной в `lib/format/product-image.ts`.

---

### 2.4. Дублирование утилит FiltersSheet.tsx и PriceSheet.tsx

**Файлы:**
- `components/blocks/search/FiltersSheet.tsx`
- `components/blocks/search/PriceSheet.tsx`

7+ идентичных вспомогательных функций (`toDigits`, `digitsToNumber`, `formatNumber`, и др.) скопированы между этими файлами.

---

### 2.5. Близнецы среди Telegram-хуков

Пары хуков с 80-90% идентичным кодом:

| Пара                                                                  | Общий код |
| --------------------------------------------------------------------- | --------- |
| `useMainButton.ts` / `useSecondaryButton.ts`                          | ~90%      |
| `useBackButton.ts` / `useSettingsButton.ts`                           | ~95%      |
| `useClosingConfirmation.ts` / `useVerticalSwipes.ts`                  | ~95%      |
| `useAccelerometer.ts` / `useGyroscope.ts` / `useDeviceOrientation.ts` | ~85%      |
| `useCloudStorage.ts` / `useDeviceStorage.ts` / `useSecureStorage.ts`  | ~80%      |

Каждая пара может быть заменена одной параметрической фабрикой.

---

### 2.6. Захардкоженные данные вместо API на всех страницах

Почти все страницы содержат пустые массивы или моковые данные:

- `app/page.tsx:13-16` — `recommendedProducts = []`, `specialOffers = []`, `NOOP`
- `app/favorites/page.tsx:69-71` — `brandsData: ApiBrand[] = []`
- `app/favorites/brands/page.tsx:29` — `brandsData: ApiBrand[] = []`
- `app/search/page.tsx:170-171` — `searchHistoryRaw: SearchHistoryItem[] = []`
- `app/catalog/page.tsx:35` — `categoriesData = []`
- `app/trash/page.tsx:174` — `forYouRaw = []`
- `app/profile/orders/OrdersClient.tsx:304` — `orders = useMemo<Order[]>(() => [], [])`
- `app/profile/viewed/page.tsx:9-63` — захардкоженный массив из 6 продуктов
- `app/profile/returns/page.tsx:258-308` — захардкоженные данные `returnOrders`
- `app/profile/reviews/page.tsx:200-260` — захардкоженные `pendingItems` и `reviewedItems`
- `components/blocks/cart/useCart.ts` — стаб, возвращающий пустые данные
- `lib/hooks/useItemFavorites.ts` — стаб с `TODO: connect to API`
- `components/blocks/catalog/BrandsList.tsx:51` — `TODO: подключить API`

---

### 2.7. Дублирование типа Window.Telegram

**Файлы:**
- `lib/types/telegram-globals.d.ts` — объявляет `Window.Telegram`
- `lib/telegram/types.ts:1203-1209` — **также** объявляет `Window.Telegram`

Два независимых расширения интерфейса Window.

---

### 2.8. Конфликт имён типов: `ApiError`

- `lib/types/api.ts` — `export interface ApiError { detail: string; status: number; }`
- `lib/errors.ts` — `export class ApiError extends AppError { ... }`

Одно имя, но одно — интерфейс для серверного ответа, другое — класс ошибки. Легко перепутать при импорте.

---

### 2.9. `stroke-width` вместо `strokeWidth` в JSX

**Файлы:**
- `app/profile/settings/page.tsx:437,502`
- `app/checkout/pickup/page.tsx:647,656,672,681`

В JSX SVG-атрибуты должны быть в camelCase. React принимает `stroke-width`, но это расходится с рекомендациями и другими частями проекта, где используется `strokeWidth`.

---

### 2.10. Константы перед imports

**Файлы:**
- `app/product/[id]/page.tsx:1-3` — `const EMPTY_SET` и `const NOOP` перед `import`
- `app/search/page.tsx:2` — `const EMPTY_SET` перед `import`
- `app/favorites/brands/page.tsx:2` — `const EMPTY_SET` перед `import`
- `app/trash/page.tsx:2` — `const EMPTY_SET` перед `import`

```tsx
// product/[id]/page.tsx
"use client";
const EMPTY_SET: Set<number | string> = new Set();
const NOOP = (): void => {};
import { ... } from "react";
```

Нарушает стандартный порядок импортов. ESLint не ловит это, т.к. `"use client"` уже нарушает «imports first» для парсера.

---

### 2.11. Отсутствует `'use client'` в некоторых хуках

**Файл:** `lib/telegram/hooks/useHaptic.ts` — не имеет `'use client'` директивы, хотя использует `useCallback` и `useTelegramContext`. Большинство других хуков в той же директории имеют `'use client'`.

---

### 2.12. FriendsSection.tsx: двойной импорт cn и cx

**Файл:** `components/blocks/home/FriendsSection.tsx:6,8`

```tsx
import { cn } from "@/lib/format/cn";
import cx from "clsx";
```

Оба используются в компоненте, создавая противоречие: `cn` из конвенции и `cx` напрямую.

---

### 2.13. ProductCard.tsx: двойной импорт cn и cx

**Файл:** `components/blocks/product/ProductCard.tsx:2,8`

```tsx
import { cn } from "@/lib/format/cn";
import cx from "clsx";
```

---

### 2.14. Массовые inline-стили вместо CSS Modules

43 вхождения `style={{...}}` в 22 .tsx файлах. Наиболее заметные:
- `app/error.tsx` — 5 инлайн-стилей
- `app/not-found.tsx` — 5 инлайн-стилей
- `app/profile/reviews/[brand]/page.tsx` — 3 инлайн-стиля
- `app/checkout/page.tsx` — 3 инлайн-стиля

В проекте, использующем CSS Modules, инлайн-стили выглядят непоследовательно.

---

## 3. Незначительные проблемы (Minor)

### 3.1. `eslint-disable` подавления (4 файла)

| Файл                                                | Подавление                                                |
| --------------------------------------------------- | --------------------------------------------------------- |
| `leaflet.d.ts:1`                                    | `@typescript-eslint/no-explicit-any`                      |
| `app/checkout/page.tsx:516`                         | `react-hooks/set-state-in-effect`                         |
| `app/checkout/pickup/page.tsx:62`                   | `@typescript-eslint/no-explicit-any` (`LeafletAny = any`) |
| `components/blocks/product/ProductAddToCart.tsx:22` | `react-hooks/exhaustive-deps`                             |

---

### 3.2. `as any` приведения (11 вхождений, 3 файла)

- `lib/telegram/core.ts:28` — `(window as any).Telegram`
- `lib/telegram/TelegramProvider.tsx` — 7 вхождений `(window as any).__LM_*`
- `components/blocks/telegram/TelegramAuthBootstrap.tsx` — 2 вхождения

Существует тип `telegram-globals.d.ts`, но он не покрывает все window-глобалы, поэтому авторы вынуждены использовать `as any`.

---

### 3.3. TODO-комментарии без трекинга (11 штук)

| Файл                                                     | TODO                      |
| -------------------------------------------------------- | ------------------------- |
| `lib/hooks/useItemFavorites.ts:9`                        | `TODO: connect to API`    |
| `components/blocks/catalog/BrandsList.tsx:51`            | `TODO: подключить API`    |
| `app/profile/settings/page.tsx:424`                      | `TODO: edit pickup point` |
| `app/profile/settings/page.tsx:451`                      | `TODO: add pickup point`  |
| `app/profile/about/page.tsx:25,43,61,79`                 | 4x `TODO: open ...`       |
| `app/profile/purchased/review/[id]/ReviewClient.tsx:344` | `TODO: send to API`       |
| `app/product/[id]/page.tsx:386,390`                      | 2x `TODO: подключить API` |

Ни один TODO не привязан к issue или тикету.

---

### 3.4. Неиспользуемый параметр `size` в `renderStars`

**Файл:** `components/blocks/product/ProductReviews.tsx:64`

```tsx
const renderStars = (count: number, size = 14) => { ... }
```

Параметр `size` объявлен со значением по умолчанию, но нигде не используется в теле функции.

---

### 3.5. Пустое тело обработчика

**Файл:** `components/blocks/product/ProductImageGallery.tsx:116-118`

```tsx
const onMouseMoveHandler = (e: React.MouseEvent<HTMLDivElement>) => {
  // empty
};
```

---

### 3.6. `isSearchClear` — вводящее в заблуждение имя пропа

**Файл:** `components/blocks/search/SearchBar.tsx`

Проп `isSearchClear` выглядит как boolean, но на самом деле имеет тип `() => void` — это callback.

---

### 3.7. Комментарии на узбекском языке

**Файл:** `components/blocks/search/PriceSheet.tsx:43-44,55-56,227`
**Файл:** `app/trash/page.tsx:688`

```tsx
{/* К оформлению tugmasi - z-40 bilan */}
```

Микс русского и узбекского текста в комментариях.

---

### 3.8. Magic numbers в cookie-helpers

**Файл:** `lib/auth/cookie-helpers.ts`

`maxAge: 900` (15 минут) и `maxAge: 604800` (7 дней) без именованных констант.

---

### 3.9. Инлайн SVG-компоненты в Footer (449 строк)

**Файл:** `components/layout/Footer.tsx`

6 SVG-иконок определены как инлайн-компоненты внутри Footer. Файл раздут до ~449 строк. SVG-иконки должны быть выделены в отдельные файлы.

---

### 3.10. Большие монолитные компоненты

| Файл                                   | Строк  |
| -------------------------------------- | ------ |
| `app/search/page.tsx`                  | ~1160  |
| `app/trash/page.tsx`                   | ~754   |
| `app/checkout/page.tsx`                | ~1400+ |
| `app/checkout/pickup/page.tsx`         | ~700+  |
| `app/profile/settings/page.tsx`        | ~600   |
| `app/profile/reviews/[brand]/page.tsx` | ~600+  |
| `app/profile/returns/page.tsx`         | ~421   |
| `components/layout/Footer.tsx`         | ~449   |
| `app/favorites/page.tsx`               | ~257   |

Компоненты свыше 300 строк затрудняют обзор и рефакторинг.

---

### 3.11. `EMPTY_SET` повторяется в 5 файлах

Паттерн `const EMPTY_SET = new Set<...>()` — дублируется в:
- `app/product/[id]/page.tsx`
- `app/search/page.tsx`
- `app/trash/page.tsx`
- `app/favorites/page.tsx`
- `app/favorites/brands/page.tsx`

---

### 3.12. Hardcoded delivery dates

**Файл:** `components/blocks/home/HomeDeliveryStatusCard.tsx:18`

```tsx
<div className={styles.subtitle}>Примерный срок доставки 6 мая</div>
```

---

### 3.13. `StarsClone` — дублированный компонент звёзд

**Файл:** `app/profile/reviews/page.tsx:52-70`

Компонент `StarsClone` делает то же, что `Stars` (строка 26), но с inline SVG и `style` вместо CSS-модулей.

---

### 3.14. Дублирование интерфейса `Brand` в favorites

Интерфейс `Brand` (с полями `id`, `name`, `image`, `isFavorite`) определён заново в:
- `components/blocks/favorites/BrandsSection.tsx:8`
- `components/blocks/favorites/brands/AllBrandsList.tsx:7`
- `components/blocks/favorites/brands/FavoriteBrandsSection.tsx:7`

---

### 3.15. Использование `key={index}` без уникального идентификатора

**Файл:** `components/blocks/profile/ProfileMenuSection.tsx:25`

```tsx
<MenuItem key={index} {...item} />
```

При `key={index}` React не сможет корректно отслеживать перестановки/удаления.

---

### 3.16. `let` вместо `const` для неизменяемой переменной

**Файл:** `app/trash/page.tsx:318`

```tsx
let showEmpty = cartReady && items.length === 0;
```

Переменная `showEmpty` никогда не переприсваивается.

---

### 3.17. `document.title` устанавливается вручную

**Файлы:**
- `app/profile/orders/OrdersClient.tsx:301`
- `app/profile/purchased/page.tsx:99`
- `app/profile/returns/page.tsx:252`
- `app/profile/purchased/review/[id]/ReviewClient.tsx:50`

В Next.js App Router для установки title следует использовать `metadata` export в серверных компонентах, а не `document.title` в useEffect.

---

### 3.18. `typeof window !== "undefined"` в `"use client"` компонентах

**Файл:** `app/profile/page.tsx:43`

В клиентских компонентах проверка `typeof window !== "undefined"` не нужна для обычного рендера, но может быть необходима для SSR. В данном случае переменная `tgUnsafeUser` используется синхронно при первом рендере, что может привести к hydration mismatch.

---

## 4. Статистика

### Импорты clsx/cn

| Тип импорта                                         | Количество файлов |
| --------------------------------------------------- | ----------------- |
| `import { cn } from "@/lib/format/cn"` (правильно)  | 8                 |
| `import cx from "clsx"` (нарушение)                 | 19                |
| `import cn from "clsx"` (замаскированное нарушение) | 3                 |
| `import clsx from "clsx"` (нарушение)               | 1                 |
| Двойной импорт (cn + cx)                            | 2                 |
| **Итого нарушений**                                 | **24**            |

### CSS-классы по типу

| Тип именования                             | Примерное количество |
| ------------------------------------------ | -------------------- |
| Семантические (`.root`, `.card`, `.title`) | ~60%                 |
| Криптогенные `.cN`                         | ~435 определений     |
| Криптогенные `.twN`                        | ~200 определений     |
| Невалидные свойства (`color: Npx`)         | ~30 вхождений        |

### Дублированные утилиты

| Функция                                      | Количество копий       |
| -------------------------------------------- | ---------------------- |
| `formatRub`                                  | 8                      |
| `copyText` (clipboard)                       | 4                      |
| `pluralizeRu`                                | 3                      |
| `normalize`                                  | 3                      |
| `asNonEmptyTrimmedString` / `asSafeImageSrc` | 2                      |
| `getLetter`                                  | 2                      |
| `ImgWithFallback`                            | 2                      |
| `getProductPhotoCandidates`                  | 2 (+ каноничная в lib) |
| **PriceSheet/FiltersSheet общие функции**    | 7+                     |

---

## 5. Что сделано хорошо

1. **Telegram SDK wrapper** (`lib/telegram/`) — впечатляющий по полноте набор из 25+ типизированных хуков с документацией. Типы (`types.ts`, ~1210 строк) тщательно описаны.

2. **BFF-паттерн** — все API-вызовы проходят через серверные Next.js routes. Браузер не обращается к бэкенду напрямую. Токены хранятся в httpOnly cookie.

3. **Auth flow** — грамотная реализация: mutex-based token refresh в RTK Query, CSRF-защита в middleware, debug-режим для локальной разработки.

4. **Error hierarchy** — `lib/errors.ts` реализует чистую иерархию ошибок (`AppError` -> `ApiError`, `NetworkError`).

5. **Format utilities** — `lib/format/price.ts`, `date.ts`, `brand-image.ts`, `product-image.ts` реализованы аккуратно и централизованно (проблема в том, что не все части кодовой базы ими пользуются).

6. **Accessibility** — `aria-label`, `role`, `aria-busy`, `aria-selected`, `aria-pressed` используются повсеместно. Семантические HTML-элементы (`section`, `header`, `main`) применяются.

7. **Type safety** — TypeScript используется строго, интерфейсы определены для большинства пропсов. Явных `any` в пользовательском коде минимум (кроме Telegram window globals).

8. **Skeleton loading states** — почти каждая страница имеет грамотный скелетон для loading state.

---

## 6. Рекомендации (по приоритету)

### P0 — Исправить немедленно

1. **Исправить баги в useGyroscope.ts и useDeviceOrientation.ts** — заменить `'Accelerometer'` на `'Gyroscope'` и `'DeviceOrientation'` соответственно.

2. **Удалить console.log** из `app/profile/reviews/[brand]/page.tsx:545,552`.

3. **Исправить `color: Npx`** в CSS — заменить на `font-size: Npx` во всех 30+ вхождениях. Проверить визуальный результат, т.к. возможно font-size уже установлен отдельно.

4. **Исправить опечатку «Аксессуры»** в `catalog/page.tsx:47` и `catalog/[category]/page.tsx:53`.

5. **Исправить опечатку «возомжность»** в `poizon/page.tsx:16`.

### P1 — Решить в ближайшем спринте

6. **Унифицировать импорт `cn`** — заменить все 24 прямых импорта `clsx` на `import { cn } from "@/lib/format/cn"`. Можно добавить ESLint-правило `no-restricted-imports` для `clsx`.

7. **Вынести дублированные утилиты** в `lib/format/`:
   - `formatRub` -> `lib/format/price.ts` (уже есть `formatRubPrice`)
   - `pluralizeRu` -> `lib/format/pluralize.ts` (новый)
   - `copyText` -> `lib/clipboard.ts` (новый)
   - `asNonEmptyTrimmedString`, `asSafeImageSrc` -> `lib/format/string.ts` (новый)
   - `normalize` -> `lib/format/normalize.ts` (новый)

8. **Создать фабрику для Telegram-хуков**:
   - `createButtonHook(type)` для useMainButton/useSecondaryButton
   - `createToggleHook(getter, setter)` для useClosingConfirmation/useVerticalSwipes
   - `createSensorHook(sensorKey)` для useAccelerometer/useGyroscope/useDeviceOrientation

### P2 — Техдолг

9. **Переименовать CSS-классы** `.c1`-`.c84` и `.tw1`-`.tw40` в семантические имена. Начать с самых крупных файлов: `trash`, `checkout`, `checkout/pickup`.

10. **Убрать дублирование** `ImgWithFallback`, `getLetter`, `getProductPhotoCandidates` — вынести в `lib/` или `components/ui/`.

11. **Убрать дублирование** между `FiltersSheet.tsx` и `PriceSheet.tsx` — вынести общие утилиты.

12. **Разбить крупные компоненты** — `search/page.tsx` (1160 строк), `checkout/page.tsx` (1400+ строк) на подкомпоненты.

13. **Удалить дублирование Window.Telegram** — оставить одно объявление в `telegram-globals.d.ts`.

14. **Добавить `'use client'`** в `useHaptic.ts` и проверить остальные хуки.

15. **Заменить `document.title =`** на Next.js `metadata` export.

---

## 7. Оценка: 4.5 / 10

| Критерий               | Оценка | Комментарий                                                            |
| ---------------------- | ------ | ---------------------------------------------------------------------- |
| Code style consistency | 3/10   | Хаос в именовании CSS, три стиля импорта clsx, constants перед imports |
| DRY                    | 3/10   | 8 копий formatRub, 4 copyText, массив дубликатов                       |
| Dead code              | 5/10   | Стабы с TODO допустимы для прототипа, но слишком много                 |
| Code smells            | 4/10   | Монолитные компоненты, инлайн SVG, magic numbers                       |
| Error handling         | 7/10   | Грамотная иерархия ошибок, try-catch обёрнуты                          |
| TypeScript quality     | 6/10   | Строгие типы, но `as any` для window globals                           |
| React best practices   | 5/10   | Хорошая мемоизация, но монолитные компоненты                           |
| Import organization    | 4/10   | Нарушена конвенция cn, constants перед imports                         |
| CSS quality            | 2/10   | 30+ `color: Npx`, 635 криптогенных классов                             |
| Debug/console code     | 6/10   | Только 2 console.log в production                                      |
| TODO/FIXME             | 6/10   | 11 TODO — допустимо для прототипа                                      |
| Documentation          | 7/10   | Хорошие JSDoc в Telegram SDK, CLAUDE.md детален                        |
