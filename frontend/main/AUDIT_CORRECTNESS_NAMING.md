# Аудит корректности и именования

**Проект:** Frontend Main (Telegram Mini App)  
**Стек:** Next.js 16, TypeScript (strict), React 19, Redux Toolkit + RTK Query  
**Дата:** 2026-04-05  
**Проверено файлов:** ~100+ (все `.ts`, `.tsx`, `.css` модули, конфиги)

---

## Содержание

1. [Критические баги (Critical)](#1-критические-баги-critical)
2. [Серьезные проблемы (Major)](#2-серьезные-проблемы-major)
3. [Незначительные замечания (Minor)](#3-незначительные-замечания-minor)
4. [Гонки состояний и утечки памяти](#4-гонки-состояний-и-утечки-памяти)
5. [Аудит именования](#5-аудит-именования)
6. [Дублирование кода](#6-дублирование-кода)
7. [Незавершенные реализации (TODO/Stub)](#7-незавершённые-реализации-todostub)
8. [Рекомендации](#8-рекомендации)
9. [Итоговые оценки](#9-итоговые-оценки)

---

## 1. Критические баги (Critical)

### 1.1. Copy-paste баг в `useGyroscope` -- проверка фичи Accelerometer вместо Gyroscope

**Файл:** `lib/telegram/hooks/useGyroscope.ts:8`

```typescript
const isAvailable = supportsFeature('Accelerometer'); // BUG: должно быть Gyroscope
```

**Проблема:** Хук гироскопа проверяет доступность акселерометра. Но `Gyroscope` отсутствует в карте `FEATURE_VERSIONS` в `core.ts`, поэтому замена на `supportsFeature('Gyroscope')` вызовет ошибку типизации. Необходимо либо добавить `Gyroscope` в карту версий, либо использовать прямую проверку `isVersionAtLeast('8.0')`.

**Влияние:** Хук может показать `isAvailable = false` на устройствах, поддерживающих гироскоп, но не акселерометр (теоретически), или наоборот -- разрешить использование, когда гироскоп недоступен.

### 1.2. Аналогичный copy-paste баг в `useDeviceOrientation`

**Файл:** `lib/telegram/hooks/useDeviceOrientation.ts:11`

```typescript
const isAvailable = supportsFeature('Accelerometer'); // BUG: должно быть DeviceOrientation
```

**Проблема:** Идентична 1.1 -- хук ориентации устройства проверяет доступность акселерометра. `DeviceOrientation` также отсутствует в `FEATURE_VERSIONS`.

### 1.3. Некорректный CSS в `BottomSheet` -- синтаксическая ошибка в inline-стиле

**Файл:** `components/ui/BottomSheet.tsx:124`

```typescript
height: `${isReview ? "auto" : "min(85vh)"}, calc(var(--tg-viewport-stable-height, 100vh) - ${maxHeightOffset}px))`
```

**Проблемы (три в одной строке):**
1. Запятая внутри значения `height` -- CSS не поддерживает множественные значения для `height` через запятую (это не `background`).
2. Лишняя закрывающая скобка `)` в конце.
3. `min(85vh)` с одним аргументом бессмысленно -- `min()` требует минимум два значения.

**Влияние:** Браузер отбросит всё значение `height` как невалидное. Стиль не применяется.

### 1.4. CSRF-защита пропускает запросы без заголовка Origin

**Файл:** `middleware.ts:27`

```typescript
if (origin) {  // проверка только если Origin СУЩЕСТВУЕТ
```

**Проблема:** Если злоумышленник отправляет POST-запрос без заголовка `Origin` (что возможно через HTML-формы в некоторых браузерах, а также через curl/Postman), CSRF-проверка полностью пропускается.

**Смягчающий фактор:** SameSite=Lax куки обеспечивают первый уровень защиты. Это лишь defence-in-depth, но дыра существует.

**Рекомендация:** Блокировать POST-запросы к auth-маршрутам при отсутствии заголовка Origin.

---

## 2. Серьезные проблемы (Major)

### 2.1. `InputFocusFix` -- `touchAction` устанавливается, но никогда не сбрасывается

**Файл:** `components/ios/InputFocusFix.tsx:12`

```typescript
document.body.style.touchAction = "manipulation";
```

**Проблема:** При фокусе на `<input>` или `<textarea>` устанавливается `touchAction = "manipulation"` на `document.body`, но нет обработчика `focusout`/`blur`, который бы сбрасывал значение. После первого фокуса стиль остается навсегда.

**Влияние:** Может нарушить стандартное поведение жестов (pinch-to-zoom) на всей странице после первого взаимодействия с полем ввода.

### 2.2. `useHaptic` -- отсутствует директива `'use client'`

**Файл:** `lib/telegram/hooks/useHaptic.ts`

**Проблема:** Хук использует `useCallback` из React, но файл не содержит директиву `'use client'`. В Next.js App Router это означает, что при импорте в серверный компонент произойдет ошибка рантайма.

**Смягчающий фактор:** В текущем коде хук всегда импортируется через barrel export, который используется только в клиентских компонентах. Но это мина замедленного действия.

### 2.3. `useClipboard` -- аналогично отсутствует `'use client'`

**Файл:** `lib/telegram/hooks/useClipboard.ts`

**Проблема:** Идентична 2.2.

### 2.4. `ProductAddToCart` -- побочный эффект при монтировании

**Файл:** `components/blocks/product/ProductAddToCart.tsx:20-23`

```typescript
React.useEffect(() => {
  onQuantityChange?.(quantity);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, []);
```

**Проблема:** При монтировании компонент вызывает `onQuantityChange` с текущим значением quantity (по умолчанию 1). Это может спровоцировать неожиданный re-render у родителя и потенциально бесконечный цикл, если родитель обновляет props в ответ. ESLint-подавление предупреждает, что это осознанное решение, но паттерн хрупкий.

### 2.5. `ProductReviews` -- параметр `size` в `renderStars` не используется

**Файл:** `components/blocks/product/ProductReviews.tsx:64`

```typescript
const renderStars = (rating: number, size: number = 12, showEmpty: boolean = true) => {
```

**Проблема:** Параметр `size` принимается, имеет дефолт, передается при вызовах (`size: 10`, `size: 12`), но нигде не используется для управления размером. Все звезды рендерятся одинаковым размером `<img>`.

### 2.6. Hardcoded цены в лейблах фильтров

**Файл:** `components/blocks/search/FiltersSheet.tsx:566-567`

```typescript
{minLabel} 2190 &#8381;
...
{maxLabel} 20000 &#8381;
```

**Файл:** `components/blocks/search/PriceSheet.tsx:294, 322`

```typescript
<div className={styles.fieldLabel}>{minLabel} 2190 ₽</div>
...
<div className={...}>{maxLabel} 20000 &#8381;</div>
```

**Проблема:** Захардкоженные цены "2190 ₽" и "20000 ₽" дублируются рядом с динамическими лейблами (`minLabel`/`maxLabel`), которые уже содержат форматированные значения из `priceBounds`. В итоге пользователь может видеть "От 1 000 ₽ 2190 ₽".

### 2.7. `PriceSheet` -- поле max disabled, но кнопка очистки работает

**Файл:** `components/blocks/search/PriceSheet.tsx:333-347`

```typescript
<input ... disabled />
...
{maxDigits ? (
  <button ... onClick={() => setMaxDigits("")}>...</button>
) : null}
```

**Проблема:** Input для максимальной цены заблокирован (`disabled`), но кнопка очистки рядом с ним работает и сбрасывает `maxDigits`. Пользователь не может ввести значение, но может его удалить -- несогласованное поведение.

### 2.8. Неполная карта `FEATURE_VERSIONS` в Telegram SDK

**Файл:** `lib/telegram/core.ts:55-85`

**Проблема:** Карта не содержит записей для `Gyroscope` и `DeviceOrientation`, хотя в Telegram Bot API 8.0 эти фичи доступны. Без этих записей `supportsFeature()` не может корректно проверять доступность этих сенсоров.

---

## 3. Незначительные замечания (Minor)

### 3.1. `ProductCard` импортирует и `cn`, и `cx` одновременно

**Файл:** `components/blocks/product/ProductCard.tsx:2,8`

```typescript
import { cn } from "@/lib/format/cn";
import cx from "clsx";
```

**Проблема:** Конвенция проекта (CLAUDE.md) -- использовать только `cn()`. В одном файле два разных утилита для классов. При этом `cx` используется лишь в одном месте (строка 168).

### 3.2. Множественные файлы используют `cx` вместо `cn`

**Файлы:**
- `components/blocks/product/ProductImageGallery.tsx:5` -- `import cx from "clsx"`
- `components/blocks/product/ProductAddToCart.tsx:4` -- `import cx from "clsx"`
- `components/blocks/product/ProductReviews.tsx:6` -- `import cx from "clsx"`

**Проблема:** Нарушение конвенции проекта. Три файла в product-блоке используют `clsx` напрямую.

### 3.3. Плюрализация отзывов -- неполная логика

**Файл:** `components/blocks/product/ProductReviews.tsx:157-161`

```typescript
{totalReviews === 1 ? "отзыв" : totalReviews < 5 ? "отзыва" : "отзывов"}
```

**Проблема:** Русская плюрализация требует учета чисел 21, 31, 101 ("отзыв"), 22-24, 32-34 ("отзыва") и т.д. Текущая логика выдаст "21 отзывов" вместо "21 отзыв".

### 3.4. Закомментированный код в `SearchBar`

**Файл:** `components/blocks/search/SearchBar.tsx:100-115`

Закомментированный блок с `Button` компонентом. Мертвый код.

### 3.5. Переменная `canAction` не используется

**Файл:** `components/blocks/search/SearchBar.tsx:59`

```typescript
const canAction = rawText.trim().length > 0;
```

Переменная вычисляется, но нигде не используется (ссылка на неё в закомментированном коде).

### 3.6. Двойное пустое пространство в лейбле

**Файл:** `components/blocks/search/FiltersSheet.tsx:354`

```typescript
`От ${formatNumber(priceBounds.min)}  ₽`  // два пробела перед ₽
```

---

## 4. Гонки состояний и утечки памяти

### 4.1. Утечка стиля `touchAction` (см. 2.1)

**Файл:** `components/ios/InputFocusFix.tsx`

`document.body.style.touchAction` устанавливается навсегда после первого фокуса на input.

### 4.2. Потенциальная гонка в `TelegramAuthBootstrap`

**Файл:** `components/blocks/telegram/TelegramAuthBootstrap.tsx`

Компонент читает `window.Telegram.WebApp.initData` напрямую (не из контекста), что является осознанным решением для избежания проблем с порядком эффектов. Гонка возможна, если Telegram SDK загрузится позже, чем выполнится эффект, но `<Script strategy="beforeInteractive">` минимизирует этот риск.

**Оценка:** Низкий риск, хорошая архитектура.

### 4.3. Mutex для refresh-токена -- корректная реализация

**Файл:** `lib/store/api.ts:39-63`

Паттерн с `refreshPromise` реализован правильно -- `finally` обнуляет промис, все параллельные 401-запросы ждут один и тот же refresh. Гонки нет.

### 4.4. `BottomSheet` -- корректная очистка анимаций

**Файл:** `components/ui/BottomSheet.tsx:70-74`

`cancelAnimationFrame` и `clearTimeout` в cleanup функции. Утечки нет.

### 4.5. `Footer` -- ResizeObserver корректно очищается

**Файл:** `components/layout/Footer.tsx`

`ResizeObserver.disconnect()` вызывается в cleanup. Утечки нет.

---

## 5. Аудит именования

### 5.1. Именование файлов

| Паттерн | Файлы | Конвенция |
|---------|-------|-----------|
| PascalCase | ~95% компонентов | `ProductCard.tsx`, `SearchBar.tsx`, `BottomSheet.tsx` |
| **kebab-case** | 1 файл | `promo-points.tsx` |
| camelCase | хуки | `useCart.ts`, `useHaptic.ts` |

**Нарушение:** `components/blocks/promo/promo-points.tsx` -- единственный файл компонента в kebab-case. Все остальные компоненты в PascalCase. CSS-модуль тоже kebab-case: `promo-points.module.css`.

**Рекомендация:** Переименовать в `PromoPoints.tsx` / `PromoPoints.module.css`.

### 5.2. Именование компонентов (экспортов)

| Файл | Экспорт | Несоответствие |
|------|---------|---------------|
| `components/layout/Layout.tsx` | `Container` | Файл `Layout.tsx`, но экспортирует `Container` |
| `components/blocks/promo/promo-points.tsx` | `PointsHistory` | Файл `promo-points`, компонент `PointsHistory` |

### 5.3. Именование пропсов -- нарушение семантики boolean

**Файл:** `components/blocks/search/SearchBar.tsx:10`

```typescript
isSearchClear?: () => void;
```

**Проблема:** Префикс `is` обозначает boolean. Но `isSearchClear` -- это callback-функция. Должно быть `onSearchClear` (по конвенции React-обработчиков).

### 5.4. Криптические имена CSS-классов

Множество компонентов используют бессмысленные имена типа `c1`, `c2`, ..., `tw1`, `tw2`:

| Файл | Примеры классов |
|------|----------------|
| `ProductImageGallery.tsx` | `c1`-`c11`, `tw1`-`tw5` |
| `ProductCard.tsx:168` | `c1`, `tw1` |
| `ProductAddToCart.tsx:36` | `c1`, `tw1` |

**Проблема:** Имена абсолютно ни о чем не говорят. Вероятно, это артефакт автоматической конвертации из Tailwind в CSS Modules (где `tw*` = бывшие Tailwind-классы, `c*` = layout-контейнеры).

**Рекомендация:** Переименовать в семантические имена: `c1` -> `root`/`container`/`wrapper`, `tw1` -> `rounded`/`shadow` и т.д.

### 5.5. Именование хуков -- корректное

Все хуки следуют конвенции `useX`:
- `useTelegram`, `useTheme`, `useMainButton`, `useBackButton`, `useHaptic`, `useClipboard`, `usePopup`, `useQrScanner`, `useInvoice`, `usePermissions`, `useCloudStorage`, `useDeviceStorage`, `useSecureStorage`, `useAccelerometer`, `useGyroscope`, `useDeviceOrientation`, `useLocation`, `useBiometric`, `useFullscreen`, `useClosingConfirmation`, `useVerticalSwipes`, `useHomeScreen`, `useEmojiStatus`, `useShare`, `usePlatform`, `useCart`, `useItemFavorites`, `useViewport`.

### 5.6. Именование типов и интерфейсов

Типы без префиксов `I`/`T` -- соответствует конвенции TypeScript (не C#-стиль):
- `WebApp`, `WebAppUser`, `ProductCardData`, `PriceRange`, `FilterValue`, `CartItem`.

**Коллизия имён:**
- `lib/types/api.ts` экспортирует **интерфейс** `ApiError` (`{ detail: string; status: number }`)
- `lib/errors.ts` экспортирует **класс** `ApiError` (extends `AppError`)

Оба имеют одинаковое имя, но принципиально разную структуру. В файлах, где нужны оба, придется использовать алиасы при импорте. Рекомендация: переименовать интерфейс в `ApiErrorResponse`.

### 5.7. Именование Redux-артефактов -- корректное

- Slice: `authSlice` (файл `authSlice.ts`)
- Actions: `authStart`, `authSuccess`, `authFailure`, `sessionExpired`, `logout` -- camelCase, глаголы
- Reducer path: `"api"` -- просто и ясно
- Tag types: `"User"`, `"Products"`, `"Product"`, `"Categories"`, `"Brands"` -- PascalCase

### 5.8. Именование констант

- `AUTH_ROUTE_PREFIX` (middleware.ts) -- UPPER_SNAKE_CASE
- `ANIMATION_MS`, `UNMOUNT_DELAY_MS` (BottomSheet.tsx) -- UPPER_SNAKE_CASE
- `MAX_DIGITS` (PriceSheet.tsx, FiltersSheet.tsx) -- UPPER_SNAKE_CASE
- `EMPTY_SET`, `EMPTY_MAP`, `EMPTY_ARRAY` (useItemFavorites.ts) -- UPPER_SNAKE_CASE

**Все константы следуют UPPER_SNAKE_CASE -- корректно.**

### 5.9. Именование boolean-переменных

| Файл | Переменная | Оценка |
|------|-----------|--------|
| `BottomSheet.tsx` | `isTypeModule`, `isFilter`, `isReview`, `isPromocodePage` | Корректный `is` префикс |
| `ProductCard.tsx` | `isPurchased`, `isViewed`, `isCompact`, `isActive` | Корректно |
| `SearchBar.tsx` | `isSearchActivated` | Корректно (boolean prop) |
| `SearchBar.tsx` | `isSearchClear` | **Некорректно** -- это callback, не boolean |
| `ProductImageGallery.tsx` | `isDragging`, `isFavorite` | Корректно |

### 5.10. Именование API-маршрутов

- `/api/auth/telegram` -- POST, начальная авторизация
- `/api/auth/refresh` -- POST, обновление токена
- `/api/auth/logout` -- POST, выход
- `/api/backend/[...path]` -- catch-all прокси
- `/api/dadata/suggest/address` -- предложение адреса
- `/api/dadata/clean/address` -- стандартизация адреса

**Все маршруты RESTful, семантически корректные, соответствуют принятым конвенциям.**

---

## 6. Дублирование кода

### 6.1. Утилиты форматирования цен

Следующие функции **идентично дублированы** между `PriceSheet.tsx` и `FiltersSheet.tsx`:
- `toDigits()`
- `digitsToNumber()`
- `formatNumber()`
- `formatNumberFromDigits()`
- `buildCurrencyValue()`
- `countDigitsBeforeCaret()`
- `findCaretPosByDigitIndex()`

**Рекомендация:** Вынести в `lib/format/price-input.ts`.

### 6.2. Обработчики `handleMinChange` / `handleMaxChange`

Тело этих функций практически идентично в обоих файлах.

---

## 7. Незавершённые реализации (TODO/Stub)

### 7.1. `useItemFavorites` -- заглушка

**Файл:** `lib/hooks/useItemFavorites.ts`

```typescript
// TODO: connect to API
```

Возвращает пустые данные. Не подключен к RTK Query.

### 7.2. `useCart` -- заглушка

**Файл:** `components/blocks/cart/useCart.ts`

Все методы (`toggleFavorite`, `removeItem`, `setQuantity`, `removeMany`, `clear`) -- no-op. Корзина не функциональна.

---

## 8. Рекомендации

### Приоритет: Высокий (исправить немедленно)

1. **Исправить copy-paste баг** в `useGyroscope.ts` и `useDeviceOrientation.ts` -- добавить `Gyroscope: '8.0'` и `DeviceOrientation: '8.0'` в `FEATURE_VERSIONS` и исправить вызовы `supportsFeature()`.

2. **Исправить CSS в BottomSheet** (строка 124) -- заменить невалидное значение `height` корректным выражением, например:
   ```typescript
   height: isReview ? "auto" : `min(85vh, calc(var(--tg-viewport-stable-height, 100vh) - ${maxHeightOffset}px))`
   ```

3. **Добавить `'use client'`** в `useHaptic.ts` и `useClipboard.ts`.

4. **Убрать захардкоженные цены** "2190" и "20000" из `FiltersSheet.tsx` и `PriceSheet.tsx`.

### Приоритет: Средний

5. **Усилить CSRF-защиту** в `middleware.ts` -- блокировать POST к auth-маршрутам при отсутствии `Origin`.

6. **Добавить `focusout` обработчик** в `InputFocusFix.tsx` для сброса `touchAction`.

7. **Переименовать `isSearchClear`** в `onSearchClear` в `SearchBar.tsx`.

8. **Вынести утилиты** `toDigits`, `formatNumber`, `buildCurrencyValue` и пр. в общий модуль.

9. **Переименовать `Layout.tsx`** -> `Container.tsx` (или экспорт `Container` -> `Layout`).

10. **Переименовать `promo-points.tsx`** -> `PromoPoints.tsx` для согласованности.

11. **Устранить коллизию `ApiError`** -- переименовать интерфейс в `lib/types/api.ts` в `ApiErrorResponse`.

### Приоритет: Низкий

12. **Заменить `cx`/`clsx` на `cn`** во всех файлах, где используется напрямую (`ProductImageGallery`, `ProductAddToCart`, `ProductReviews`, `ProductCard`).

13. **Переименовать криптические CSS-классы** `c1`-`c11`, `tw1`-`tw5` в семантические имена.

14. **Исправить плюрализацию** "отзыв/отзыва/отзывов" в `ProductReviews.tsx` -- добавить корректную русскую плюрализацию через утилиту.

15. **Удалить неиспользуемый параметр `size`** из `renderStars` в `ProductReviews.tsx` или реализовать поддержку размера.

16. **Удалить закомментированный код** и неиспользуемую переменную `canAction` из `SearchBar.tsx`.

17. **Удалить `eslint-disable`** в `ProductAddToCart.tsx` -- либо добавить зависимости в массив, либо пересмотреть необходимость эффекта.

---

## 9. Итоговые оценки

### Корректность: 6.5 / 10

**Обоснование:**
- Три критических бага (copy-paste в сенсорных хуках, невалидный CSS в BottomSheet, дыра в CSRF)
- Несколько серьезных проблем (утечка стиля, отсутствие `'use client'`, захардкоженные данные)
- Основной каркас (auth flow, RTK Query, mutex, BFF proxy, Telegram provider) реализован грамотно
- Redux-слой, API-маршруты, middleware (за исключением Origin-проверки) корректны
- Очистка ресурсов (event listeners, ResizeObserver, animation frames) выполняется правильно в большинстве компонентов

### Именование: 7.0 / 10

**Обоснование:**
- Общая конвенция именования файлов, хуков, типов, констант, Redux-артефактов -- стабильная и последовательная
- Криптические CSS-классы (`c1`, `tw1`) -- серьезная проблема читаемости, но ограничена ~3-4 файлами
- Единственное нарушение файловой конвенции (`promo-points.tsx`)
- Одно несоответствие имени файла экспорту (`Layout.tsx` -> `Container`)
- Семантическое нарушение в `isSearchClear` (callback с boolean-префиксом)
- Коллизия имен `ApiError` между интерфейсом и классом
- Все остальное (хуки, Redux, constants, boolean vars, API routes) -- чисто и предсказуемо
