# 01. CSS (Tailwind v4) и компонентная библиотека (shadcn/ui)

> Расширенное исследование секций 1-2 из `03-ui-design-system.md`
> Дата: апрель 2026 | Источники: официальная документация, веб-исследование

---

## 1. Tailwind CSS v4 — полный обзор возможностей

### 1.1 Oxide Engine (Rust)

Tailwind v4 полностью переписан на Rust (кодовое имя "Oxide"). Ключевые метрики производительности:

| Метрика                    | Tailwind v3 | Tailwind v4 | Ускорение |
| -------------------------- | ----------- | ----------- | --------- |
| Full build                 | ~378ms      | ~100ms      | 3.78x     |
| Incremental build          | ~35ms       | ~192μs      | 182x      |
| Большие проекты (600ms v3) | ~600ms      | ~120ms      | 5x        |

Инкрементальные сборки измеряются в **микросекундах** — практически мгновенный hot reload.

### 1.2 CSS-first конфигурация (@theme)

Главное архитектурное изменение — переход от `tailwind.config.js` к CSS-директиве `@theme`. Все дизайн-токены объявляются прямо в CSS и автоматически становятся CSS-переменными, доступными в runtime.

```css
/* globals.css */
@import 'tailwindcss';

@theme {
  /* Шрифты */
  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  /* Цвета — OKLCH */
  --color-brand-50: oklch(0.97 0.02 250);
  --color-brand-100: oklch(0.93 0.04 250);
  --color-brand-500: oklch(0.55 0.18 250);
  --color-brand-900: oklch(0.25 0.1 250);

  /* Семантические цвета */
  --color-background: oklch(1 0 0);
  --color-foreground: oklch(0.15 0.02 250);
  --color-primary: oklch(0.55 0.18 250);
  --color-primary-foreground: oklch(0.98 0.01 250);
  --color-destructive: oklch(0.55 0.2 25);
  --color-muted: oklch(0.92 0.01 250);
  --color-border: oklch(0.88 0.01 250);

  /* Spacing (4px система) */
  --spacing-0: 0px;
  --spacing-1: 4px;
  --spacing-2: 8px;
  --spacing-4: 16px;
  --spacing-8: 32px;
  --spacing-16: 64px;

  /* Скругления */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;

  /* Брейкпоинты */
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
  --breakpoint-2xl: 1536px;
  --breakpoint-3xl: 1920px;

  /* Анимации */
  --ease-snappy: cubic-bezier(0.2, 0, 0, 1);
  --ease-fluid: cubic-bezier(0.3, 0, 0, 1);
}
```

**Ключевой принцип:** каждый токен `--color-brand-500` автоматически порождает утилиту `bg-brand-500`, `text-brand-500`, `border-brand-500` и т.д. Одновременно доступен как `var(--color-brand-500)` в любом CSS.

### 1.3 Система цветов OKLCH

Tailwind v4 перевёл **всю** дефолтную палитру с `rgb` на `oklch`. Это не просто смена формата — это расширение цветового пространства.

#### Что такое OKLCH

OKLCH — цилиндрические координаты в цветовом пространстве Oklab:

| Параметр          | Диапазон        | Описание                   |
| ----------------- | --------------- | -------------------------- |
| **L** (Lightness) | 0% – 100% (0–1) | Воспринимаемая яркость     |
| **C** (Chroma)    | 0 – ~0.4        | Интенсивность/насыщенность |
| **H** (Hue)       | 0° – 360°       | Угол на цветовом круге     |

#### Преимущества OKLCH перед rgb/hsl

1. **Перцептивная однородность** — одинаковое изменение L даёт одинаковое визуальное изменение яркости (в отличие от HSL)
2. **P3 гамут** — доступны цвета за пределами sRGB, более насыщенные оттенки на современных дисплеях (MacBook, iPhone, большинство современных мониторов)
3. **Предсказуемость** — поддерживает единообразную яркость при изменении hue (нет "скачков яркости" как в HSL)
4. **Динамические темы** — легко программно генерировать палитры, изменяя только H (hue) при фиксированных L и C

```css
/* Пример: генерация палитры бренда через один hue */
@theme {
  --color-brand-50: oklch(0.97 0.02 250); /* Очень светлый */
  --color-brand-100: oklch(0.93 0.04 250);
  --color-brand-200: oklch(0.87 0.08 250);
  --color-brand-300: oklch(0.78 0.12 250);
  --color-brand-400: oklch(0.68 0.15 250);
  --color-brand-500: oklch(0.55 0.18 250); /* Базовый */
  --color-brand-600: oklch(0.48 0.16 250);
  --color-brand-700: oklch(0.4 0.14 250);
  --color-brand-800: oklch(0.32 0.11 250);
  --color-brand-900: oklch(0.25 0.08 250);
  --color-brand-950: oklch(0.18 0.06 250); /* Очень тёмный */
}

/* Для смены бренда — достаточно изменить hue (250 -> 150 для зелёного) */
```

#### Встроенная палитра Tailwind v4

22 цветовых семейства, каждое с 11 оттенками (50–950):

| Группа      | Цвета                             |
| ----------- | --------------------------------- |
| Тёплые      | Red, Orange, Amber, Yellow        |
| Зелёные     | Lime, Green, Emerald, Teal        |
| Холодные    | Cyan, Sky, Blue, Indigo           |
| Фиолетовые  | Violet, Purple, Fuchsia           |
| Розовые     | Pink, Rose                        |
| Нейтральные | Slate, Gray, Zinc, Neutral, Stone |

Поддержка браузеров: Safari 16.4+, Chrome 111+, Firefox 128+ — полное покрытие OKLCH.

### 1.4 @custom-variant — пользовательские варианты

Tailwind v4 добавил возможность создавать собственные варианты через `@custom-variant`:

```css
/* Тёмная тема */
@custom-variant dark (&:where(.dark, .dark *));

/* Использование: dark:bg-gray-900 dark:text-white */
```

```css
/* Кастомные состояния для enterprise */
@custom-variant loading (&[data-loading="true"]);
@custom-variant error (&[data-state="error"]);
@custom-variant selected (&[aria-selected="true"]);
@custom-variant expanded (&[aria-expanded="true"]);

/* 
  Использование в JSX:
  <div className="loading:opacity-50 loading:pointer-events-none">
  <input className="error:border-destructive error:ring-destructive" />
  <li className="selected:bg-accent selected:text-accent-foreground">
  <button className="expanded:rotate-180">
*/
```

```css
/* Кастомный вариант для печати */
@custom-variant print (@media print);

/* Использование: print:hidden print:text-black */
```

```css
/* Вариант для reduced motion */
@custom-variant motion-safe (@media (prefers-reduced-motion: no-preference));
@custom-variant motion-reduce (@media (prefers-reduced-motion: reduce));
```

### 1.5 Container Queries — встроенная поддержка

В v3 container queries требовали плагин `@tailwindcss/container-queries`. В v4 это **встроенная** функциональность:

```html
<!-- Пометить элемент как контейнер -->
<div class="@container">
  <!-- Дочерний элемент реагирует на размер контейнера, НЕ viewport -->
  <div class="@sm:flex @lg:grid @lg:grid-cols-3">
    <div class="@sm:w-1/2 @lg:w-full">Card 1</div>
    <div class="@sm:w-1/2 @lg:w-full">Card 2</div>
    <div class="@sm:hidden @lg:block">Card 3</div>
  </div>
</div>
```

#### Именованные контейнеры

```html
<div class="@container/sidebar">
  <nav class="@sm/sidebar:flex @lg/sidebar:flex-col">
    <!-- Запрос размера конкретно sidebar-контейнера -->
  </nav>
</div>
```

#### Доступные breakpoints контейнера

| Вариант | Min-width | Вариант (max) | Max-width |
| ------- | --------- | ------------- | --------- |
| `@xs:`  | 320px     | `@max-xs:`    | 319px     |
| `@sm:`  | 384px     | `@max-sm:`    | 383px     |
| `@md:`  | 448px     | `@max-md:`    | 447px     |
| `@lg:`  | 512px     | `@max-lg:`    | 511px     |
| `@xl:`  | 576px     | `@max-xl:`    | 575px     |
| `@2xl:` | 672px     | `@max-2xl:`   | 671px     |
| `@3xl:` | 768px     | `@max-3xl:`   | 767px     |
| `@4xl:` | 896px     | `@max-4xl:`   | 895px     |
| `@5xl:` | 1024px    | `@max-5xl:`   | 1023px    |

**Ключевое преимущество:** компоненты становятся по-настоящему изолированными — карточка в sidebar и та же карточка в main content автоматически адаптируются к своему контейнеру, а не к viewport.

### 1.6 Новые встроенные утилиты (без плагинов)

В v4 множество утилит, которые в v3 требовали плагинов, стали встроенными:

| Категория             | Утилиты                                     | Описание                          |
| --------------------- | ------------------------------------------- | --------------------------------- |
| **Container Queries** | `@container`, `@sm:`, `@lg:`                | Стилизация по размеру контейнера  |
| **3D трансформации**  | `rotate-x-*`, `rotate-y-*`, `perspective-*` | Без плагинов                      |
| **Градиенты**         | `bg-conic-*`, `bg-radial-*`                 | Конические и радиальные градиенты |
| **not-\* вариант**    | `not-hover:`, `not-first:`, `not-disabled:` | Инверсия вариантов                |
| **nth-\* варианты**   | `nth-2:`, `nth-odd:`, `nth-last-3:`         | Стилизация n-го элемента          |
| **@starting-style**   | `starting:opacity-0`                        | Enter/exit анимации без JS        |
| **inert**             | `inert:opacity-50`                          | Стилизация `inert` элементов      |
| **field-sizing**      | `field-sizing-content`                      | Auto-resize для textarea          |
| **color-scheme**      | `scheme-dark`, `scheme-light`               | Нативная цветовая схема           |

#### Пример: @starting-style для enter-анимаций

```html
<!-- Элемент появляется с анимацией без JavaScript -->
<div
  class="translate-y-0 opacity-100 transition-all duration-300 starting:translate-y-4 starting:opacity-0"
>
  Animated content
</div>
```

#### Пример: расширенные градиенты

```html
<!-- Конический градиент -->
<div
  class="size-40 rounded-full bg-conic-[from_45deg,--color-brand-500,--color-brand-200,--color-brand-500]"
/>

<!-- Радиальный градиент -->
<div class="to-brand-500 size-40 rounded-full bg-radial-[at_25%_25%] from-white" />
```

### 1.7 Composable Variants — составные варианты

Tailwind v4 позволяет комбинировать варианты более гибко:

```html
<!-- Стилизация при hover на группу + конкретный child -->
<div class="group">
  <span class="group-hover:not-first:text-brand-500">
    Подсвечивается при hover на группу, кроме первого элемента
  </span>
</div>

<!-- not-* с любыми вариантами -->
<button class="not-disabled:hover:bg-brand-500">Hover только если не disabled</button>
```

---

## 2. Миграция с Tailwind v3 на v4

### 2.1 Автоматическая миграция

Tailwind предоставляет официальный codemod, который обрабатывает ~90% изменений:

```bash
# Автоматическая миграция (рекомендуемый способ)
npx @tailwindcss/upgrade@latest

# Что делает codemod:
# 1. Обновляет зависимости (tailwindcss, postcss, autoprefixer)
# 2. Конвертирует tailwind.config.js -> @theme в CSS
# 3. Заменяет переименованные классы в шаблонах
# 4. Обновляет @tailwind -> @import "tailwindcss"
# 5. Показывает diff всех изменений
```

### 2.2 Ключевые breaking changes

#### Импорт фреймворка

```css
/* v3 — директивы */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* v4 — стандартный CSS import */
@import 'tailwindcss';
```

#### Конфигурация → CSS

```js
// v3 — tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        brand: '#3b82f6',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [require('@tailwindcss/typography'), require('@tailwindcss/container-queries')],
};
```

```css
/* v4 — globals.css */
@import 'tailwindcss';
@plugin '@tailwindcss/typography';

@theme {
  --color-brand: #3b82f6;
  --font-sans: 'Inter', sans-serif;
}
/* Container queries теперь встроены, плагин не нужен */
```

#### Переименованные утилиты

| v3                  | v4                     | Описание               |
| ------------------- | ---------------------- | ---------------------- |
| `bg-gradient-to-r`  | `bg-linear-to-r`       | Линейные градиенты     |
| `bg-gradient-to-br` | `bg-linear-to-br`      | Диагональные градиенты |
| `flex-shrink-0`     | `shrink-0`             | Сокращение             |
| `flex-grow`         | `grow`                 | Сокращение             |
| `overflow-ellipsis` | `text-ellipsis`        | Текстовые утилиты      |
| `decoration-clone`  | `box-decoration-clone` | Box decoration         |
| `decoration-slice`  | `box-decoration-slice` | Box decoration         |

#### Поведение border

```html
<!-- v3: border добавлял border-gray-200 по умолчанию -->
<div class="border">Gray border</div>

<!-- v4: border использует currentColor по умолчанию -->
<div class="border border-gray-200">Нужно явно указать цвет</div>
```

#### Произвольные значения — пробелы

```html
<!-- v3: запятые заменялись на пробелы -->
<div class="grid-cols-[1fr,auto,1fr]">...</div>

<!-- v4: используйте подчёркивания для пробелов -->
<div class="grid-cols-[1fr_auto_1fr]">...</div>
```

### 2.3 Совместимость браузеров

| Браузер | Минимальная версия |
| ------- | ------------------ |
| Chrome  | 111+               |
| Firefox | 128+               |
| Safari  | 16.4+              |
| Edge    | 111+               |

**Важно:** если нужна поддержка IE или старых Safari — оставайтесь на v3.4.

### 2.4 Чек-лист миграции

```markdown
- [ ] Запустить `npx @tailwindcss/upgrade@latest`
- [ ] Проверить diff, сгенерированный codemod
- [ ] Убедиться в конвертации tailwind.config.js -> @theme
- [ ] Заменить @tailwind директивы на @import "tailwindcss"
- [ ] Обновить bg-gradient-to-_ -> bg-linear-to-_
- [ ] Добавить явный цвет к border (если использовался без цвета)
- [ ] Удалить плагин container-queries (встроен)
- [ ] Проверить произвольные значения (запятые -> подчёркивания)
- [ ] Обновить PostCSS конфиг (если используется)
- [ ] Проверить darkMode конфигурацию -> @custom-variant
- [ ] Запустить визуальное регрессионное тестирование
- [ ] Проверить поддержку целевых браузеров
```

---

## 3. shadcn/ui — полный обзор

### 3.1 Философия и архитектура

shadcn/ui — это **не библиотека** в традиционном смысле. Это коллекция переиспользуемых компонентов, которые **копируются в ваш проект**. Вы владеете кодом, нет `node_modules` зависимости для UI-компонентов.

**Стек под капотом:**

- **Примитивы:** Radix UI (по умолчанию) или Base UI (с января 2026)
- **Стилизация:** Tailwind CSS + `cva` (class-variance-authority)
- **Утилита слияния классов:** `cn()` = `clsx` + `tailwind-merge`
- **TypeScript:** полная типизация всех компонентов

### 3.2 CLI — команды и workflow

#### Инициализация проекта

```bash
# Инициализация (интерактивная)
pnpm dlx shadcn@latest init

# Вопросы CLI:
# - Which style? (Default / New York)
# - Which color? (Slate / Gray / Zinc / Neutral / Stone)
# - Which primitives? (Radix UI / Base UI)  ← новое с 2026
# - CSS variables for colors? (yes/no)
```

#### Добавление компонентов

```bash
# Один компонент
pnpm dlx shadcn@latest add button

# Несколько компонентов
pnpm dlx shadcn@latest add button card dialog table tabs

# Все компоненты
pnpm dlx shadcn@latest add --all

# Перезаписать существующий компонент
pnpm dlx shadcn@latest add button --overwrite
```

#### Создание проекта с нуля (октябрь 2025)

```bash
# Создание нового Next.js проекта с shadcn/ui
npx shadcn create my-app

# Создаёт:
# - Next.js 15 проект
# - Tailwind CSS v4
# - shadcn/ui (инициализированный)
# - TypeScript strict mode
# - Базовая структура папок
```

#### Diff — проверка обновлений

```bash
# Показать различия между вашим кодом и оригиналом
pnpm dlx shadcn@latest diff

# Diff конкретного компонента
pnpm dlx shadcn@latest diff button
```

### 3.3 Полный список компонентов по категориям

#### Формы и ввод

| Компонент        | Описание                                                         | Примитив                 |
| ---------------- | ---------------------------------------------------------------- | ------------------------ |
| **Button**       | Кнопка с вариантами (default, destructive, outline, ghost, link) | Нативный                 |
| **Button Group** | Группа связанных кнопок                                          | Нативный                 |
| **Input**        | Текстовое поле ввода                                             | Нативный                 |
| **Input Group**  | Поле с префиксом/суффиксом (иконки, текст)                       | Нативный                 |
| **Textarea**     | Многострочный ввод                                               | Нативный                 |
| **Checkbox**     | Чекбокс с состояниями                                            | Radix/Base UI            |
| **Radio Group**  | Группа радиокнопок                                               | Radix/Base UI            |
| **Switch**       | Переключатель (toggle)                                           | Radix/Base UI            |
| **Slider**       | Ползунок выбора значения                                         | Radix/Base UI            |
| **Select**       | Выпадающий список                                                | Radix/Base UI            |
| **Combobox**     | Autocomplete с поиском                                           | Radix/Base UI            |
| **Date Picker**  | Выбор даты (использует Calendar)                                 | Radix + react-day-picker |
| **Form**         | Обёртка для react-hook-form + zod                                | react-hook-form          |
| **Field**        | Контейнер для поля формы с label и ошибкой                       | Нативный                 |
| **Toggle**       | Кнопка-переключатель                                             | Radix/Base UI            |
| **Toggle Group** | Группа toggle-кнопок                                             | Radix/Base UI            |

#### Отображение данных

| Компонент      | Описание                             | Примитив            |
| -------------- | ------------------------------------ | ------------------- |
| **Table**      | HTML-таблица со стилизацией          | Нативный            |
| **Data Table** | Полноценная таблица (TanStack Table) | TanStack + Нативный |
| **Card**       | Контейнер-карточка                   | Нативный            |
| **Badge**      | Метка/тег статуса                    | Нативный            |
| **Avatar**     | Аватар пользователя                  | Radix/Base UI       |
| **Calendar**   | Календарь                            | react-day-picker    |
| **Chart**      | Графики (обёртка над Recharts)       | Recharts            |
| **Carousel**   | Карусель                             | Embla Carousel      |
| **Kbd**        | Клавиатурные сокращения              | Нативный            |
| **Empty**      | Пустое состояние с иконкой и текстом | Нативный            |
| **Spinner**    | Индикатор загрузки                   | Нативный            |

#### Навигация

| Компонент           | Описание                                        | Примитив      |
| ------------------- | ----------------------------------------------- | ------------- |
| **Sidebar**         | Боковая панель (collapsible, keyboard shortcut) | Нативный      |
| **Navigation Menu** | Горизонтальное навигационное меню               | Radix/Base UI |
| **Breadcrumb**      | Хлебные крошки                                  | Нативный      |
| **Tabs**            | Табы/вкладки                                    | Radix/Base UI |
| **Pagination**      | Пагинация                                       | Нативный      |
| **Command**         | Командная палитра (⌘K)                          | cmdk          |
| **Menubar**         | Меню-бар (File, Edit, View)                     | Radix/Base UI |

#### Оверлеи и обратная связь

| Компонент         | Описание                                         | Примитив               |
| ----------------- | ------------------------------------------------ | ---------------------- |
| **Dialog**        | Модальное окно                                   | Radix/Base UI          |
| **Alert Dialog**  | Модальное подтверждение (деструктивные действия) | Radix/Base UI          |
| **Sheet**         | Выдвижная панель (сбоку)                         | Radix/Base UI          |
| **Drawer**        | Мобильная выдвижная панель (снизу)               | Vaul                   |
| **Popover**       | Всплывающий контейнер                            | Radix/Base UI          |
| **Tooltip**       | Подсказка при наведении                          | Radix/Base UI          |
| **Dropdown Menu** | Выпадающее меню                                  | Radix/Base UI          |
| **Context Menu**  | Контекстное меню (правый клик)                   | Radix/Base UI          |
| **Hover Card**    | Карточка при наведении                           | Radix/Base UI          |
| **Toast**         | Уведомления-тосты                                | Radix/Base UI (Sonner) |
| **Alert**         | Статичное уведомление                            | Нативный               |
| **Progress**      | Полоса прогресса                                 | Radix/Base UI          |
| **Skeleton**      | Скелетон загрузки                                | Нативный               |

#### Макет и прочее

| Компонент        | Описание                                      | Примитив               |
| ---------------- | --------------------------------------------- | ---------------------- |
| **Accordion**    | Аккордеон (раскрывающиеся секции)             | Radix/Base UI          |
| **Collapsible**  | Сворачиваемый контейнер                       | Radix/Base UI          |
| **Aspect Ratio** | Контейнер с фиксированным соотношением сторон | Radix                  |
| **Scroll Area**  | Кастомный скроллбар                           | Radix/Base UI          |
| **Separator**    | Разделитель (горизонтальный/вертикальный)     | Radix/Base UI          |
| **Resizable**    | Изменяемые по размеру панели                  | react-resizable-panels |
| **Sonner**       | Альтернативный toast с анимациями             | Sonner                 |
| **Item**         | Универсальный элемент списка                  | Нативный               |

**Итого:** 50+ компонентов, покрывающих большинство потребностей enterprise-дашборда.

### 3.4 Новые компоненты (2025-2026)

| Компонент              | Дата         | Описание                                                            |
| ---------------------- | ------------ | ------------------------------------------------------------------- |
| **Sidebar**            | Август 2024  | Production-ready sidebar с collapsible, ⌘B shortcut, mobile sheet   |
| **Chart**              | 2024         | Обёртка над Recharts для Area, Bar, Line, Pie, Radar, Radial charts |
| **Spinner**            | Октябрь 2025 | Индикатор загрузки (заменяет кастомные SVG-лоадеры)                 |
| **Kbd**                | Октябрь 2025 | Отображение клавиатурных сокращений                                 |
| **Button Group**       | Октябрь 2025 | Группировка связанных кнопок                                        |
| **Input Group**        | Октябрь 2025 | Поле ввода с дополнительными элементами                             |
| **Field**              | Октябрь 2025 | Контейнер для form field                                            |
| **Item**               | Октябрь 2025 | Универсальный list item                                             |
| **Empty**              | Октябрь 2025 | Пустое состояние (empty state)                                      |
| **Base UI support**    | Январь 2026  | Альтернативные примитивы вместо Radix                               |
| **Blocks for Base UI** | Февраль 2026 | Готовые блоки на Base UI                                            |

### 3.5 Структура файлов после init

```
src/
├── components/
│   └── ui/              # shadcn компоненты (ВАШ код)
│       ├── button.tsx
│       ├── card.tsx
│       ├── dialog.tsx
│       ├── sidebar.tsx
│       ├── data-table.tsx
│       └── ...
├── lib/
│   └── utils.ts         # cn() утилита
├── hooks/
│   └── use-mobile.tsx   # хук определения мобильных устройств
├── app/
│   └── globals.css      # @import "tailwindcss" + @theme
└── components.json      # конфигурация shadcn
```

---

## 4. Radix UI vs Base UI — детальное сравнение

С января 2026 shadcn/ui поддерживает два провайдера примитивов. Выбор делается при `shadcn init`.

### 4.1 Сравнительная таблица

| Критерий                  | Radix UI                                  | Base UI                                          |
| ------------------------- | ----------------------------------------- | ------------------------------------------------ |
| **Разработчик**           | WorkOS (ранее независимый)                | MUI (команда Material UI)                        |
| **Версия**                | ~1.1                                      | 1.0 (декабрь 2025)                               |
| **Подход**                | Primitives — готовые составные части      | Behavioral building blocks — поведенческие блоки |
| **Композиция**            | `asChild` prop                            | Render props, `render` prop                      |
| **Пакеты**                | Множество (`@radix-ui/react-dialog`, ...) | Один пакет `@base-ui-components/react`           |
| **Accessibility**         | WCAG AAA                                  | WCAG AAA                                         |
| **Bundle size**           | ~2-5KB/компонент                          | ~1-3KB/компонент                                 |
| **TypeScript**            | Полная типизация                          | Полная типизация                                 |
| **SSR/RSC**               | Поддерживается                            | Поддерживается                                   |
| **Документация**          | Зрелая, обширная                          | Новая, растущая                                  |
| **Уникальные компоненты** | —                                         | Multi-select, Combobox, Autocomplete             |
| **Стабильность API**      | Устоявшийся                               | Новый, может меняться                            |
| **Экосистема**            | 16K+ stars, огромная                      | Растущая (MUI backing)                           |
| **Maintenance**           | Замедлился после WorkOS                   | Активная разработка (MUI)                        |

### 4.2 Ключевые различия в коде

#### Композиция компонентов

```tsx
// Radix UI — asChild pattern
import * as Dialog from '@radix-ui/react-dialog';

<Dialog.Root>
  <Dialog.Trigger asChild>
    <button>Open</button>
  </Dialog.Trigger>
  <Dialog.Portal>
    <Dialog.Overlay />
    <Dialog.Content>
      <Dialog.Title>Title</Dialog.Title>
      <Dialog.Description>Description</Dialog.Description>
      <Dialog.Close asChild>
        <button>Close</button>
      </Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>;
```

```tsx
// Base UI — render prop pattern
import { Dialog } from '@base-ui-components/react/dialog';

<Dialog.Root>
  <Dialog.Trigger render={<button>Open</button>} />
  <Dialog.Portal>
    <Dialog.Backdrop />
    <Dialog.Popup>
      <Dialog.Title>Title</Dialog.Title>
      <Dialog.Description>Description</Dialog.Description>
      <Dialog.Close render={<button>Close</button>} />
    </Dialog.Popup>
  </Dialog.Portal>
</Dialog.Root>;
```

#### Управление зависимостями

```bash
# Radix — отдельные пакеты для каждого примитива
pnpm add @radix-ui/react-dialog
pnpm add @radix-ui/react-dropdown-menu
pnpm add @radix-ui/react-tooltip
pnpm add @radix-ui/react-popover
# ... 10+ отдельных пакетов

# Base UI — один пакет
pnpm add @base-ui-components/react
# Всё включено, tree-shakeable
```

### 4.3 Рекомендация по выбору

| Сценарий                         | Рекомендация      | Причина                                          |
| -------------------------------- | ----------------- | ------------------------------------------------ |
| **Новый проект**                 | Base UI           | Один пакет, современный API, активная разработка |
| **Существующий проект на Radix** | Остаться на Radix | Работает, нет срочности мигрировать              |
| **Нужен multi-select/combobox**  | Base UI           | Встроенные компоненты, у Radix нет               |
| **Нужна стабильность API**       | Radix             | Устоявшийся API, меньше breaking changes         |
| **Минимальный bundle**           | Base UI           | Один пакет, эффективнее tree-shaking             |
| **Максимальная экосистема**      | Radix             | Больше примеров, статей, решений                 |

**Для нового enterprise-проекта в 2026:** рекомендуется Base UI — один пакет, активная поддержка MUI, встроенные сложные компоненты (multi-select, combobox). При этом shadcn/ui абстрагирует разницу, так что переключение примитивов минимально затрагивает прикладной код.

---

## 5. Практические паттерны

### 5.1 @theme + dark mode + @custom-variant — полный пример

```css
/* globals.css */
@import 'tailwindcss';

/* Кастомный dark mode variant */
@custom-variant dark (&:where(.dark, .dark *));

/* Кастомные enterprise-варианты */
@custom-variant loading (&[data-loading="true"]);
@custom-variant compact (&:where(.compact, .compact *));

@theme {
  /* Light theme tokens */
  --color-background: oklch(1 0 0);
  --color-foreground: oklch(0.15 0.02 250);
  --color-card: oklch(1 0 0);
  --color-card-foreground: oklch(0.15 0.02 250);
  --color-primary: oklch(0.55 0.18 250);
  --color-primary-foreground: oklch(0.98 0.01 250);
  --color-secondary: oklch(0.92 0.01 250);
  --color-secondary-foreground: oklch(0.15 0.02 250);
  --color-muted: oklch(0.92 0.01 250);
  --color-muted-foreground: oklch(0.55 0.02 250);
  --color-accent: oklch(0.92 0.03 250);
  --color-accent-foreground: oklch(0.15 0.02 250);
  --color-destructive: oklch(0.55 0.2 25);
  --color-border: oklch(0.88 0.01 250);
  --color-ring: oklch(0.55 0.18 250);

  /* Typography */
  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

/* Dark theme overrides */
.dark {
  --color-background: oklch(0.13 0.02 250);
  --color-foreground: oklch(0.95 0.01 250);
  --color-card: oklch(0.17 0.02 250);
  --color-card-foreground: oklch(0.95 0.01 250);
  --color-primary: oklch(0.65 0.18 250);
  --color-primary-foreground: oklch(0.1 0.02 250);
  --color-secondary: oklch(0.22 0.02 250);
  --color-secondary-foreground: oklch(0.95 0.01 250);
  --color-muted: oklch(0.22 0.02 250);
  --color-muted-foreground: oklch(0.65 0.02 250);
  --color-accent: oklch(0.22 0.03 250);
  --color-accent-foreground: oklch(0.95 0.01 250);
  --color-destructive: oklch(0.55 0.22 25);
  --color-border: oklch(0.3 0.02 250);
  --color-ring: oklch(0.65 0.18 250);
}
```

### 5.2 Типичный workflow с shadcn/ui

```bash
# 1. Создание проекта
npx shadcn create my-dashboard
cd my-dashboard

# 2. Добавление нужных компонентов
pnpm dlx shadcn@latest add sidebar button card dialog \
  data-table tabs badge avatar dropdown-menu \
  sheet tooltip command input select \
  form toast chart separator breadcrumb \
  spinner empty field

# 3. Настройка @theme токенов в globals.css
# 4. Кастомизация компонентов в src/components/ui/
# 5. Создание составных блоков из UI-компонентов
# 6. Проверка обновлений
pnpm dlx shadcn@latest diff
```

---

## Источники

- [Tailwind CSS v4.0 — официальный блог](https://tailwindcss.com/blog/tailwindcss-v4)
- [Tailwind CSS — Upgrade Guide](https://tailwindcss.com/docs/upgrade-guide)
- [Tailwind CSS — Responsive Design (Container Queries)](https://tailwindcss.com/docs/responsive-design)
- [Tailwind CSS — Colors](https://tailwindcss.com/docs/customizing-colors)
- [shadcn/ui — Changelog](https://ui.shadcn.com/docs/changelog)
- [shadcn/ui — Components](https://ui.shadcn.com/docs/components)
- [shadcn/ui — October 2025 New Components](https://ui.shadcn.com/docs/changelog/2025-10-new-components)
- [shadcn/ui — January 2026 Base UI Documentation](https://ui.shadcn.com/docs/changelog/2026-01-base-ui)
- [Radix UI vs Base UI — Detailed Guide](https://shadcnspace.com/blog/radix-ui-vs-base-ui)
- [Base UI vs Radix UI Features](https://shadcnstudio.com/blog/base-ui-vs-radix-ui)
- [Tailwind CSS v4 Color System — OKLCH Guide](https://tailwindcolor.tools/blog/tailwind-css-v4-color-system-complete-guide)
- [Better Dynamic Themes with OKLCH — Evil Martians](https://evilmartians.com/chronicles/better-dynamic-themes-in-tailwind-with-oklch-color-magic)
- [Tailwind CSS v4 Container Queries — SitePoint](https://www.sitepoint.com/tailwind-css-v4-container-queries-modern-layouts/)
- [Tailwind 4 Migration — Design Revision](https://designrevision.com/blog/tailwind-4-migration)
