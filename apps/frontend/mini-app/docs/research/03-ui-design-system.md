# UI и дизайн-система: Tailwind v4, shadcn/ui, анимации, layout и data display (2025-2026)

> **Контекст проекта:** Frontend-only Next.js приложение, часть большой системы с отдельными
> бэкенд-сервисами. Next.js выступает как BFF (Backend for Frontend) / proxy-слой.
>
> Полное исследование: Tailwind CSS v4 (Oxide), shadcn/ui + Radix/Base UI, дизайн-токены OKLCH,
> мультитемность, анимации (Motion, View Transitions), иконки (Lucide), layout-паттерны для
> enterprise-дашбордов, TanStack Table, графики (Recharts/Tremor), шрифты, изображения, Storybook.

---

## Содержание

### Часть 1 — CSS (Tailwind v4) и компонентная библиотека (shadcn/ui)

- [1. Tailwind CSS v4 — полный обзор](#1-tailwind-css-v4--полный-обзор-возможностей)
- [2. Миграция с Tailwind v3 на v4](#2-миграция-с-tailwind-v3-на-v4) _(не требуется)_
- [3. shadcn/ui — полный обзор](#3-shadcnui--полный-обзор)
- [4. Radix UI vs Base UI](#4-radix-ui-vs-base-ui--детальное-сравнение)
- [5. Практические паттерны](#5-практические-паттерны)

### Часть 2 — Дизайн-токены, темы и адаптивный дизайн

- [1. Архитектура дизайн-токенов](#1-архитектура-дизайн-токенов)
- [2. Цветовое пространство OKLCH](#2-цветовое-пространство-oklch) _(краткая справка)_
- [3. Мультитемность: Light / Dark / Brand](#3-мультитемность-light--dark--brand-themes)
- [4. Система типографики](#4-система-типографики)
- [5. Система отступов (4px Grid)](#5-система-отступов-4px-grid)
- [6. Система теней и elevation](#6-система-теней-и-elevation)
- [7. Адаптивный дизайн: Breakpoints + Container Queries](#7-адаптивный-дизайн-breakpoints--container-queries)

### Часть 3 — Анимации и иконки

- [5. Анимации](#5-анимации)
- [6. Иконки](#6-иконки)

### Часть 4 — Layout-паттерны и отображение данных

- [7.1 Архитектура dashboard-layout](#71-полная-архитектура-dashboard-layout)
- [7.2 Sidebar: shadcn/ui](#72-sidebar-shadcnui-sidebar-компонент)
- [7.3 Breadcrumbs](#73-breadcrumbs-с-динамическими-сегментами)
- [7.4 Responsive-брейкпоинты](#74-стратегия-responsive-брейкпоинтов)
- [8.1 TanStack Table](#81-tanstack-table-серверная-пагинация-сортировка-фильтрация)
- [8.2 Виртуальный скроллинг](#82-tanstack-table-виртуальный-скроллинг-для-больших-датасетов)
- [8.3 Графики: Recharts](#83-графики-recharts--настройка-и-типовые-графики)
- [8.4 Tremor vs Recharts](#84-tremor-vs-recharts-руководство-по-выбору)
- [8.5 KPI Card](#85-kpi-card--паттерн-компонента)
- [8.6 Empty State](#86-empty-state-паттерны)

### Часть 5 — Утилиты, шрифты, изображения и документация

- [9.1 cn() — глубокое погружение](#91-cn--глубокое-погружение)
- [9.2 cva — продвинутые паттерны](#92-cva--продвинутые-паттерны)
- [9.3 tailwind-variants (tv)](#93-альтернатива-tailwind-variants-tv) _(краткая справка)_
- [10. Шрифты: next/font](#10-шрифты-nextfont)
- [11. Изображения: next/image](#11-изображения-nextimage)
- [12. Storybook 8](#12-storybook-8-документация-компонентов)
- [13. Тестирование дизайн-системы](#13-тестирование-дизайн-системы)
- [14. Итоговая рекомендация: полный tech stack](#14-итоговая-рекомендация-полный-tech-stack)

---

# Часть 1 — CSS (Tailwind v4) и компонентная библиотека (shadcn/ui)

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

Проект создан на Tailwind v4 — миграция не требуется.

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

---

---

# Часть 2 — Дизайн-токены, темы и адаптивный дизайн

> Tailwind CSS v4 + Next.js 15+ App Router

---

## 1. Архитектура дизайн-токенов

### 1.1. Три уровня токенов

Enterprise дизайн-система строится на **трёхуровневой архитектуре** токенов. Это разделение позволяет менять визуал без затрагивания логики компонентов и поддерживать white-label / multi-tenant сценарии.

```
+-----------------------------------------------------------------+
|  УРОВЕНЬ 1: Примитивные (Primitive / Raw)                       |
|  Сырые значения без семантики                                   |
|  --blue-500: oklch(0.55 0.18 250)                               |
|  --gray-100: oklch(0.95 0.01 250)                               |
|  --space-4: 16px                                                |
+-----------------------------------------------------------------+
          |
          v
+-----------------------------------------------------------------+
|  УРОВЕНЬ 2: Семантические (Semantic / Alias)                    |
|  Назначение, не визуал                                          |
|  --color-primary: var(--blue-500)                               |
|  --color-background: var(--gray-100)                            |
|  --spacing-page-gutter: var(--space-4)                          |
+-----------------------------------------------------------------+
          |
          v
+-----------------------------------------------------------------+
|  УРОВЕНЬ 3: Компонентные (Component)                            |
|  Конкретные привязки к UI-элементам                             |
|  --button-bg: var(--color-primary)                              |
|  --card-padding: var(--spacing-page-gutter)                     |
|  --input-border: var(--color-border)                            |
+-----------------------------------------------------------------+
```

**Почему три уровня, а не один?**

- Примитивные токены -- единый источник правды для значений
- Семантические токены -- позволяют менять тему, переопределяя маппинг (dark: `--color-background` -> `var(--gray-900)`)
- Компонентные токены -- изолируют компонент от изменений в дизайн-системе

### 1.2. Реализация в Tailwind v4 с @theme

В Tailwind v4 `@theme` заменяет `tailwind.config.js`. Каждый токен внутри `@theme` автоматически становится:

1. **CSS-переменной** -- доступна через `var(--color-primary)` в любом CSS
2. **Tailwind-утилитой** -- `bg-primary`, `text-primary`, `border-primary`

```css
/* src/styles/tokens/primitives.css */
/* ===================================================
   УРОВЕНЬ 1: Примитивные токены
   Сырые значения. Никогда не используются в компонентах напрямую.
   =================================================== */

@theme {
  /* --- Цветовая палитра (oklch) --- */
  --color-blue-50: oklch(0.97 0.02 250);
  --color-blue-100: oklch(0.93 0.04 250);
  --color-blue-200: oklch(0.86 0.08 250);
  --color-blue-300: oklch(0.77 0.12 250);
  --color-blue-400: oklch(0.66 0.16 250);
  --color-blue-500: oklch(0.55 0.18 250);
  --color-blue-600: oklch(0.47 0.17 250);
  --color-blue-700: oklch(0.39 0.15 250);
  --color-blue-800: oklch(0.31 0.12 250);
  --color-blue-900: oklch(0.25 0.1 250);
  --color-blue-950: oklch(0.18 0.07 250);

  --color-gray-50: oklch(0.98 0.005 250);
  --color-gray-100: oklch(0.95 0.01 250);
  --color-gray-200: oklch(0.9 0.01 250);
  --color-gray-300: oklch(0.83 0.01 250);
  --color-gray-400: oklch(0.7 0.015 250);
  --color-gray-500: oklch(0.55 0.015 250);
  --color-gray-600: oklch(0.45 0.015 250);
  --color-gray-700: oklch(0.37 0.015 250);
  --color-gray-800: oklch(0.27 0.015 250);
  --color-gray-900: oklch(0.2 0.015 250);
  --color-gray-950: oklch(0.13 0.02 250);

  --color-red-500: oklch(0.55 0.22 25);
  --color-green-500: oklch(0.55 0.17 145);
  --color-amber-500: oklch(0.75 0.18 75);
  --color-orange-500: oklch(0.65 0.2 50);

  --color-white: oklch(1 0 0);
  --color-black: oklch(0 0 0);
}
```

```css
/* src/styles/tokens/semantic.css */
/* ===================================================
   УРОВЕНЬ 2: Семантические токены
   Смысл, а не цвет. Переопределяются для dark / brand тем.
   =================================================== */

@theme {
  /* --- Основные семантические цвета --- */
  --color-background: var(--color-white);
  --color-foreground: var(--color-gray-950);
  --color-card: var(--color-white);
  --color-card-foreground: var(--color-gray-950);
  --color-popover: var(--color-white);
  --color-popover-foreground: var(--color-gray-950);

  /* --- Акцентные --- */
  --color-primary: var(--color-blue-500);
  --color-primary-foreground: var(--color-white);
  --color-secondary: var(--color-gray-100);
  --color-secondary-foreground: var(--color-gray-900);
  --color-accent: var(--color-gray-100);
  --color-accent-foreground: var(--color-gray-900);
  --color-muted: var(--color-gray-100);
  --color-muted-foreground: var(--color-gray-500);

  /* --- Состояния --- */
  --color-destructive: var(--color-red-500);
  --color-destructive-foreground: var(--color-white);
  --color-success: var(--color-green-500);
  --color-success-foreground: var(--color-white);
  --color-warning: var(--color-amber-500);
  --color-warning-foreground: var(--color-gray-950);

  /* --- Элементы UI --- */
  --color-border: var(--color-gray-200);
  --color-input: var(--color-gray-200);
  --color-ring: var(--color-blue-400);

  /* --- Sidebar (shadcn) --- */
  --color-sidebar: var(--color-gray-50);
  --color-sidebar-foreground: var(--color-gray-700);
  --color-sidebar-accent: var(--color-gray-100);
  --color-sidebar-border: var(--color-gray-200);
  --color-sidebar-ring: var(--color-blue-400);
}
```

**Ключевой принцип:** Компоненты используют только семантические токены (`bg-background`, `text-foreground`, `border-border`). Переключение темы -- это смена маппинга семантических токенов на другие примитивные значения.

---

## 2. Цветовое пространство OKLCH

OKLCH — перцептуально однородное цветовое пространство, используемое Tailwind v4 по умолчанию. Детали и практическое применение — в Части 1, секция 1.3.

---

## 3. Мультитемность: Light / Dark / Brand themes

### 3.1. Архитектура мультитемности

```
Пользователь выбирает тему
        |
        v
next-themes устанавливает атрибут на <html>
        |
        +-- data-theme="light"   -> CSS-переменные light-темы
        +-- data-theme="dark"    -> CSS-переменные dark-темы
        +-- data-theme="brand-X" -> CSS-переменные бренда X (из БД)
```

### 3.2. Настройка next-themes с Tailwind v4

**Шаг 1: CSS-конфигурация dark mode**

В Tailwind v4 нет `darkMode: "class"` в конфиге. Вместо этого -- `@custom-variant` в CSS:

```css
/* src/styles/globals.css */
@import 'tailwindcss';
@import './tokens/primitives.css';
@import './tokens/semantic.css';

/* Tailwind v4: кастомный вариант для dark mode.
   Используем data-theme вместо class для совместимости с next-themes
   и предотвращения hydration-ошибок. */
@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

/* ===================================================
   DARK THEME: переопределение семантических токенов
   =================================================== */
[data-theme='dark'] {
  --color-background: var(--color-gray-950);
  --color-foreground: var(--color-gray-50);
  --color-card: var(--color-gray-900);
  --color-card-foreground: var(--color-gray-50);
  --color-popover: var(--color-gray-900);
  --color-popover-foreground: var(--color-gray-50);

  --color-primary: oklch(0.65 0.18 250); /* светлее на тёмном фоне */
  --color-primary-foreground: var(--color-white);
  --color-secondary: var(--color-gray-800);
  --color-secondary-foreground: var(--color-gray-100);
  --color-accent: var(--color-gray-800);
  --color-accent-foreground: var(--color-gray-100);
  --color-muted: var(--color-gray-800);
  --color-muted-foreground: var(--color-gray-400);

  --color-destructive: oklch(0.65 0.22 25);
  --color-destructive-foreground: var(--color-white);
  --color-success: oklch(0.65 0.17 145);
  --color-warning: oklch(0.8 0.18 75);

  --color-border: var(--color-gray-800);
  --color-input: var(--color-gray-800);
  --color-ring: oklch(0.6 0.18 250);

  --color-sidebar: var(--color-gray-900);
  --color-sidebar-foreground: var(--color-gray-300);
  --color-sidebar-accent: var(--color-gray-800);
  --color-sidebar-border: var(--color-gray-800);
}
```

**Шаг 2: ThemeProvider**

```tsx
// src/components/providers/theme-provider.tsx
'use client';

import { ThemeProvider as NextThemesProvider } from 'next-themes';
import type { ComponentProps } from 'react';

type ThemeProviderProps = ComponentProps<typeof NextThemesProvider>;

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

```tsx
// src/app/layout.tsx
import { ThemeProvider } from '@/components/providers/theme-provider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="data-theme" // data-атрибут вместо class
          defaultTheme="system" // авто-определение по OS
          enableSystem // поддержка prefers-color-scheme
          disableTransitionOnChange // без мерцания при переключении
          themes={['light', 'dark']} // доступные темы
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

**Почему `attribute="data-theme"` вместо `attribute="class"`?**

- Класс `.dark` может конфликтовать с другими классами при SSR
- `data-theme` не вызывает hydration mismatch -- классы стабильны, меняется только data-атрибут
- Проще поддерживать 3+ тем (light/dark/brand-custom) -- одно значение атрибута вместо комбинаций классов

**Шаг 3: Компонент переключения темы**

```tsx
// src/components/theme-toggle.tsx
'use client';

import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { Moon, Sun, Monitor } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Предотвращаем hydration mismatch -- рендер только на клиенте
  useEffect(() => setMounted(true), []);
  if (!mounted) return <Button variant="ghost" size="icon" disabled />;

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => {
        const next = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light';
        setTheme(next);
      }}
    >
      {theme === 'light' && <Sun className="size-4" />}
      {theme === 'dark' && <Moon className="size-4" />}
      {theme === 'system' && <Monitor className="size-4" />}
    </Button>
  );
}
```

### 3.3. Multi-tenant / White-label темы

Для SaaS-продуктов с кастомным брендингом на каждого клиента:

```
Запрос -> middleware определяет tenant по домену/поддомену
       -> загрузка конфига темы tenant из БД/edge config
       -> инъекция CSS-переменных в <html style="...">
       -> все компоненты автоматически используют цвета tenant
```

**Реализация:**

```typescript
// src/lib/tenant-theme.ts
export interface TenantTheme {
  id: string;
  name: string;
  colors: {
    primary: string; // oklch значение, например "oklch(0.55 0.20 150)"
    primaryForeground: string;
    background: string;
    foreground: string;
    accent: string;
    border: string;
    sidebar: string;
  };
  fonts?: {
    sans: string;
    mono: string;
  };
  radius?: string; // например "8px"
}

/**
 * Преобразует конфигурацию тенанта в inline CSS-переменные
 */
export function tenantThemeToCSS(theme: TenantTheme): string {
  const vars: string[] = [];

  vars.push(`--color-primary: ${theme.colors.primary}`);
  vars.push(`--color-primary-foreground: ${theme.colors.primaryForeground}`);
  vars.push(`--color-background: ${theme.colors.background}`);
  vars.push(`--color-foreground: ${theme.colors.foreground}`);
  vars.push(`--color-accent: ${theme.colors.accent}`);
  vars.push(`--color-border: ${theme.colors.border}`);
  vars.push(`--color-sidebar: ${theme.colors.sidebar}`);

  if (theme.fonts?.sans) vars.push(`--font-sans: ${theme.fonts.sans}`);
  if (theme.radius) vars.push(`--radius-md: ${theme.radius}`);

  return vars.join('; ');
}
```

```tsx
// src/app/layout.tsx (multi-tenant вариант)
import { getTenantByDomain, type TenantTheme } from '@/lib/tenant-theme';
import { tenantThemeToCSS } from '@/lib/tenant-theme';
import { headers } from 'next/headers';

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const headersList = await headers();
  const host = headersList.get('host') ?? 'default';
  const tenant = await getTenantByDomain(host);
  const tenantCSS = tenant ? tenantThemeToCSS(tenant) : '';

  return (
    <html lang="ru" suppressHydrationWarning style={{ cssText: tenantCSS } as any}>
      <body>
        <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

**Каскад приоритетов:** inline style на `<html>` переопределяет значения из `@theme`, но `[data-theme="dark"]` переопределяет inline (если использовать `!important` или специфичность). Для корректной работы dark mode + tenant одновременно рекомендуется:

```css
/* Tenant переменные инжектируются как light-значения.
   Dark-тема использует производные с модифицированным L (lightness). */
[data-theme='dark'] {
  /* Эти переменные могут быть сгенерированы на сервере
     из tenant-конфига с инвертированной яркостью */
}
```

---

## 4. Система типографики

### 4.1. Шкала размеров (Modular Scale)

Используем **Major Third** (ratio 1.25) масштаб, привязанный к base 16px:

```css
@theme {
  /* --- Типографика: размеры --- */
  --text-xs: 0.75rem; /* 12px -- подписи, метки */
  --text-sm: 0.875rem; /* 14px -- вспомогательный текст, таблицы */
  --text-base: 1rem; /* 16px -- основной текст */
  --text-lg: 1.125rem; /* 18px -- крупный текст */
  --text-xl: 1.25rem; /* 20px -- подзаголовки */
  --text-2xl: 1.5rem; /* 24px -- заголовки секций */
  --text-3xl: 1.875rem; /* 30px -- заголовки страниц */
  --text-4xl: 2.25rem; /* 36px -- hero заголовки */
  --text-5xl: 3rem; /* 48px -- landing крупный */

  /* --- Типографика: line-height --- */
  --leading-none: 1;
  --leading-tight: 1.25;
  --leading-snug: 1.375;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;

  /* --- Типографика: letter-spacing --- */
  --tracking-tighter: -0.05em;
  --tracking-tight: -0.025em;
  --tracking-normal: 0em;
  --tracking-wide: 0.025em;
  --tracking-wider: 0.05em;

  /* --- Типографика: font-weight --- */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* --- Шрифты --- */
  --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, 'Cascadia Code', monospace;
  --font-display: 'Inter', ui-sans-serif, system-ui, sans-serif;
}
```

### 4.2. Рекомендуемые комбинации для элементов

| Элемент         | Размер    | Weight         | Line-height  | Пример утилиты                        |
| --------------- | --------- | -------------- | ------------ | ------------------------------------- |
| Body text       | text-base | normal (400)   | normal (1.5) | `text-base leading-normal`            |
| Small / caption | text-sm   | normal (400)   | normal (1.5) | `text-sm text-muted-foreground`       |
| Table cell      | text-sm   | normal (400)   | tight (1.25) | `text-sm leading-tight`               |
| Button          | text-sm   | medium (500)   | none (1)     | `text-sm font-medium`                 |
| Card title      | text-lg   | semibold (600) | tight (1.25) | `text-lg font-semibold leading-tight` |
| Section heading | text-2xl  | bold (700)     | tight (1.25) | `text-2xl font-bold tracking-tight`   |
| Page heading    | text-3xl  | bold (700)     | none (1)     | `text-3xl font-bold tracking-tight`   |

---

## 5. Система отступов (4px Grid)

### 5.1. Шкала spacing

Все отступы кратны **4px**. Это обеспечивает визуальный ритм и пиксельную точность на экранах 1x/2x/3x.

```css
@theme {
  /* --- Spacing: 4px grid --- */
  --spacing-0: 0px; /* 0 */
  --spacing-px: 1px; /* pixel-perfect borders */
  --spacing-0.5: 2px; /* 0.5 * 4 */
  --spacing-1: 4px; /* 1 * 4 */
  --spacing-1.5: 6px; /* 1.5 * 4 */
  --spacing-2: 8px; /* 2 * 4 */
  --spacing-2.5: 10px; /* 2.5 * 4 */
  --spacing-3: 12px; /* 3 * 4 */
  --spacing-3.5: 14px; /* 3.5 * 4 */
  --spacing-4: 16px; /* 4 * 4 -- базовый модуль */
  --spacing-5: 20px; /* 5 * 4 */
  --spacing-6: 24px; /* 6 * 4 */
  --spacing-7: 28px; /* 7 * 4 */
  --spacing-8: 32px; /* 8 * 4 */
  --spacing-9: 36px; /* 9 * 4 */
  --spacing-10: 40px; /* 10 * 4 */
  --spacing-12: 48px; /* 12 * 4 */
  --spacing-14: 56px; /* 14 * 4 */
  --spacing-16: 64px; /* 16 * 4 */
  --spacing-20: 80px; /* 20 * 4 */
  --spacing-24: 96px; /* 24 * 4 */
  --spacing-32: 128px; /* 32 * 4 */
}
```

### 5.2. Правила применения

| Контекст                | Рекомендуемый spacing                | Утилита             |
| ----------------------- | ------------------------------------ | ------------------- |
| Между иконкой и текстом | 2 (8px)                              | `gap-2`             |
| Padding внутри кнопки   | 2.5-3 по вертикали, 4 по горизонтали | `px-4 py-2.5`       |
| Padding внутри карточки | 4-6 (16-24px)                        | `p-4` или `p-6`     |
| Между карточками в grid | 4-6 (16-24px)                        | `gap-4` или `gap-6` |
| Page gutter (десктоп)   | 8-12 (32-48px)                       | `px-8` или `px-12`  |
| Page gutter (мобильный) | 4 (16px)                             | `px-4`              |
| Между секциями страницы | 12-16 (48-64px)                      | `py-12` или `py-16` |
| Header height           | 14 (56px)                            | `h-14`              |
| Sidebar width           | 64 (256px)                           | `w-64`              |

---

## 6. Система теней и elevation

### 6.1. Уровни elevation

Тени создают визуальную иерархию. В enterprise-дашбордах используется **5-уровневая** система elevation:

```css
@theme {
  /* --- Shadows: 5 уровней elevation --- */
  --shadow-xs: 0 1px 2px 0 oklch(0 0 0 / 0.05);
  --shadow-sm: 0 1px 3px 0 oklch(0 0 0 / 0.1), 0 1px 2px -1px oklch(0 0 0 / 0.1);
  --shadow-md: 0 4px 6px -1px oklch(0 0 0 / 0.1), 0 2px 4px -2px oklch(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px oklch(0 0 0 / 0.1), 0 4px 6px -4px oklch(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px oklch(0 0 0 / 0.1), 0 8px 10px -6px oklch(0 0 0 / 0.1);
  --shadow-2xl: 0 25px 50px -12px oklch(0 0 0 / 0.25);
  --shadow-none: 0 0 0 0 transparent;

  /* --- Border radius --- */
  --radius-none: 0px;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-2xl: 24px;
  --radius-full: 9999px;
}
```

### 6.2. Маппинг elevation на UI-элементы

```
Elevation 0 (без тени):  фон страницы, inline-элементы
Elevation 1 (shadow-xs):  карточки в потоке, input borders
Elevation 2 (shadow-sm):  приподнятые карточки, sticky header
Elevation 3 (shadow-md):  dropdown menus, popovers
Elevation 4 (shadow-lg):  модальные окна, диалоги
Elevation 5 (shadow-xl):  floating action buttons, toast notifications
```

### 6.3. Тени для dark mode

В dark mode тени менее заметны (тёмный фон поглощает тень). Вместо shadow часто используются:

- **Светлые border** (`border-gray-800`) для разграничения
- **Более светлый фон** (`bg-gray-900` карточка на `bg-gray-950` фоне) для elevation

```css
[data-theme='dark'] {
  --shadow-xs: 0 1px 2px 0 oklch(0 0 0 / 0.2);
  --shadow-sm: 0 1px 3px 0 oklch(0 0 0 / 0.3), 0 1px 2px -1px oklch(0 0 0 / 0.2);
  --shadow-md: 0 4px 6px -1px oklch(0 0 0 / 0.3), 0 2px 4px -2px oklch(0 0 0 / 0.2);
  --shadow-lg: 0 10px 15px -3px oklch(0 0 0 / 0.4), 0 4px 6px -4px oklch(0 0 0 / 0.3);
  --shadow-xl: 0 20px 25px -5px oklch(0 0 0 / 0.5), 0 8px 10px -6px oklch(0 0 0 / 0.4);
}
```

---

## 7. Адаптивный дизайн: Breakpoints + Container Queries

### 7.1. Viewport breakpoints (media queries)

Tailwind v4 использует mobile-first подход. Утилиты без префикса -- для всех экранов, с префиксом -- от указанного breakpoint и выше.

```css
@theme {
  /* --- Breakpoints (viewport) --- */
  --breakpoint-sm: 640px; /* телефон (landscape) */
  --breakpoint-md: 768px; /* планшет */
  --breakpoint-lg: 1024px; /* ноутбук */
  --breakpoint-xl: 1280px; /* десктоп */
  --breakpoint-2xl: 1536px; /* wide desktop */
  --breakpoint-3xl: 1920px; /* ultra-wide (кастомный) */
}
```

**Примеры:**

```html
<!-- Стандартный responsive grid -->
<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
  <!-- cards -->
</div>

<!-- Range breakpoints (v4): только между md и lg -->
<div class="md:max-lg:grid-cols-2">...</div>
```

### 7.2. Container Queries -- компонентная адаптивность

Container queries -- главная инновация Tailwind v4 для адаптивности. Компоненты реагируют на **размер родителя**, а не viewport. Это критично для:

- Sidebar с разной шириной (collapsed/expanded)
- Карточки в grid'ах с разным числом колонок
- Переиспользуемые компоненты в разных layout-контекстах

**Container breakpoints по умолчанию:**

| Префикс | Ширина         | Аналог viewport |
| ------- | -------------- | --------------- |
| `@xs`   | 320px (20rem)  | --              |
| `@sm`   | 384px (24rem)  | --              |
| `@md`   | 448px (28rem)  | --              |
| `@lg`   | 512px (32rem)  | --              |
| `@xl`   | 576px (36rem)  | --              |
| `@2xl`  | 672px (42rem)  | sm (640px)      |
| `@3xl`  | 768px (48rem)  | md (768px)      |
| `@4xl`  | 896px (56rem)  | --              |
| `@5xl`  | 1024px (64rem) | lg (1024px)     |
| `@6xl`  | 1152px (72rem) | --              |
| `@7xl`  | 1280px (80rem) | xl (1280px)     |

**Пример: адаптивная карточка**

```tsx
// components/ui/metric-card.tsx
export function MetricCard({ title, value, change }: MetricCardProps) {
  return (
    // @container делает элемент контейнером
    <div className="@container">
      <div className="border-border bg-card rounded-lg border p-4">
        {/* Вертикальный layout по умолчанию, горизонтальный от @md (448px) */}
        <div className="flex flex-col @md:flex-row @md:items-center @md:justify-between">
          <div>
            <p className="text-muted-foreground text-sm">{title}</p>
            {/* Размер адаптируется под контейнер */}
            <p className="text-2xl font-bold @lg:text-3xl">{value}</p>
          </div>
          <span className="text-success mt-2 text-sm @md:mt-0 @md:text-base">{change}</span>
        </div>
      </div>
    </div>
  );
}
```

### 7.3. Стратегия: viewport для layout, container для компонентов

```
+-----------------------------------------------+
|  VIEWPORT queries (md:, lg:, xl:)             |
|  Используются для:                             |
|  - Количество колонок в grid                  |
|  - Sidebar visible / hidden                   |
|  - Header layout (мобильный / десктопный)     |
|  - Page-level padding                         |
+-----------------------------------------------+

+-----------------------------------------------+
|  CONTAINER queries (@md:, @lg:, @xl:)         |
|  Используются для:                             |
|  - Внутренний layout компонента               |
|  - Размер текста внутри карточки              |
|  - Переключение grid/list внутри блока        |
|  - Адаптация к sidebar collapsed / expanded   |
+-----------------------------------------------+
```

**Реальный сценарий** -- sidebar dashboard:

```tsx
// Sidebar expanded (256px): main content ~1024px -> карточки в 3 колонки
// Sidebar collapsed (64px):  main content ~1216px -> карточки в 4 колонки
// Без container queries пришлось бы вычислять вручную

<main className="@container flex-1 overflow-y-auto p-6">
  <div className="grid grid-cols-1 gap-4 @2xl:grid-cols-2 @5xl:grid-cols-3 @7xl:grid-cols-4">
    <MetricCard title="Revenue" value="$124,500" change="+12.5%" />
    <MetricCard title="Users" value="12,340" change="+8.2%" />
    <MetricCard title="Orders" value="1,280" change="+15.3%" />
    <MetricCard title="Conversion" value="3.2%" change="+0.4%" />
  </div>
</main>
```

### 7.4. Именованные контейнеры

Tailwind v4 поддерживает именованные контейнеры для вложенных сценариев:

```html
<!-- Именованный контейнер -->
<div class="@container/sidebar">
  <div class="@container/content">
    <!-- Реагирует на sidebar -->
    <div class="@md/sidebar:hidden">...</div>
    <!-- Реагирует на content -->
    <div class="@lg/content:grid-cols-2">...</div>
  </div>
</div>
```

---

## 8. Полная структура файлов дизайн-системы

```
src/
  styles/
    globals.css                 # @import'ы + @custom-variant dark
    tokens/
      primitives.css            # Уровень 1: сырые значения (цвета, шкалы)
      semantic.css              # Уровень 2: семантические маппинги
    themes/
      dark.css                  # [data-theme="dark"] переопределения
      brand-example.css         # Пример tenant-темы
  lib/
    utils.ts                    # cn() утилита
    palette.ts                  # Генератор OKLCH палитр
    tenant-theme.ts             # Multi-tenant CSS injection
  components/
    providers/
      theme-provider.tsx        # next-themes wrapper
    ui/                         # shadcn компоненты
    theme-toggle.tsx            # Переключатель dark/light/system
```

**globals.css -- точка входа:**

```css
/* src/styles/globals.css */
@import 'tailwindcss';
@import './tokens/primitives.css';
@import './tokens/semantic.css';
@import './themes/dark.css';

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));
```

---

## Источники

- [Tailwind CSS v4 Theme Variables](https://tailwindcss.com/docs/theme)
- [Tailwind CSS v4 Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [Tailwind CSS v4 Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [next-themes (GitHub)](https://github.com/pacocoursey/next-themes)
- [OKLCH in CSS -- Evil Martians](https://evilmartians.com/chronicles/oklch-in-css-why-quit-rgb-hsl)
- [Exploring the OKLCH Ecosystem -- Evil Martians](https://evilmartians.com/chronicles/exploring-the-oklch-ecosystem-and-its-tools)
- [Design Tokens That Scale in 2026 -- Mavik Labs](https://www.maviklabs.com/blog/design-tokens-tailwind-v4-2026)
- [Tailwind CSS 4 @theme: The Future of Design Tokens](https://medium.com/@sureshdotariya/tailwind-css-4-theme-the-future-of-design-tokens-at-2025-guide-48305a26af06)
- [Multi-Tenant Themes with NextJS App Router & Tailwind](https://medium.com/@aimanfaruk98/multi-tenant-theming-with-nextjs-app-router-tailwind-6a5a4195ed70)
- [Dark Mode with Tailwind v4 & next-themes](https://dev.to/abujakariacse/dark-mode-with-tailwind-v4-next-themes-1mag)
- [Tailwind CSS v4 Container Queries -- SitePoint](https://www.sitepoint.com/tailwind-css-v4-container-queries-modern-layouts/)
- [How to Add Dark Mode in Next.js 15 with Tailwind CSS V4](https://www.sujalvanjare.com/blog/dark-mode-nextjs15-tailwind-v4)
- [Atmos Style -- OKLCH Palette Generator](https://atmos.style/playground)

---

---

# Часть 3 — Анимации и иконки

> Enterprise Next.js 15+ App Router, production-паттерны

---

## 5. Анимации

### 5.1. Стек анимаций по уровням

| Уровень | Инструмент                 | Bundle          | Когда использовать                        |
| ------- | -------------------------- | --------------- | ----------------------------------------- |
| **L0**  | CSS transitions + Tailwind | 0 KB            | Hover, focus, простые переходы            |
| **L1**  | tailwindcss-motion plugin  | ~5 KB CSS       | Входные/выходные анимации, presets        |
| **L2**  | Motion (ex Framer Motion)  | ~85 KB          | AnimatePresence, layout, gestures, scroll |
| **L3**  | View Transitions API       | 0 KB (нативное) | Переходы между страницами                 |
| **L4**  | GSAP                       | ~78 KB          | Сложные таймлайны, SVG морфинг            |

**Принцип:** начинай с L0, поднимайся только когда предыдущего недостаточно.

---

### 5.2. Motion (бывший Framer Motion)

С 2025 года Framer Motion стал независимым проектом **Motion**. Пакет: `motion`, импорт: `motion/react`. API полностью совместим.

```bash
pnpm add motion
# Миграция: pnpm remove framer-motion && pnpm add motion
# Замена импортов: "framer-motion" -> "motion/react"
```

#### AnimatePresence -- анимация выхода

Три обязательных условия: (1) `AnimatePresence` оборачивает условие, не наоборот; (2) `motion`-компонент имеет уникальный `key`; (3) он -- прямой потомок `AnimatePresence`.

```tsx
import { motion, AnimatePresence } from 'motion/react';

export function NotificationStack({ notifications, onDismiss }) {
  return (
    <AnimatePresence mode="popLayout">
      {notifications.map((n) => (
        <motion.div
          key={n.id}
          layout
          initial={{ opacity: 0, x: 100, scale: 0.95 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 100, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        >
          {n.message}
        </motion.div>
      ))}
    </AnimatePresence>
  );
}
```

**Режимы:** `"sync"` (по умолчанию) -- exit и enter одновременно; `"wait"` -- сначала exit, потом enter; `"popLayout"` -- exit элемент снимается из layout-потока.

#### Layout-анимации и layoutId

Motion автоматически анимирует изменения layout через `transform` (GPU-ускорение). `layoutId` анимирует переход элемента между позициями в DOM:

```tsx
import { motion, LayoutGroup } from 'motion/react';

export function AnimatedTabs({ tabs, activeTab, setActiveTab }) {
  return (
    <LayoutGroup>
      <div className="bg-muted flex gap-1 rounded-lg p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="relative rounded-md px-3 py-1.5 text-sm font-medium"
          >
            {activeTab === tab.id && (
              <motion.div
                layoutId="active-tab"
                className="bg-background absolute inset-0 rounded-md shadow-sm"
                transition={{ type: 'spring', stiffness: 500, damping: 35 }}
              />
            )}
            <span className="relative z-10">{tab.label}</span>
          </button>
        ))}
      </div>
    </LayoutGroup>
  );
}
```

#### Scroll-triggered анимации

```tsx
import { motion, useScroll, useTransform } from 'motion/react';
import { useRef } from 'react';

export function ParallaxSection({ children }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] });
  const y = useTransform(scrollYProgress, [0, 1], [100, -100]);
  const opacity = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [0, 1, 1, 0]);

  return (
    <motion.div ref={ref} style={{ y, opacity }}>
      {children}
    </motion.div>
  );
}
```

#### Жесты

```tsx
<motion.div
  whileHover={{ scale: 1.02, boxShadow: '0 10px 30px rgba(0,0,0,0.12)' }}
  whileTap={{ scale: 0.98 }}
  drag="x"
  dragConstraints={{ left: -100, right: 100 }}
  dragElastic={0.1}
/>
```

Поддерживаемые: `whileHover`, `whileTap`, `whileDrag`, `whileFocus`, `whileInView`.

#### Staggered-анимации списков

```tsx
import { motion } from 'motion/react';

const container = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } },
};

export function StaggeredList({ items }) {
  return (
    <motion.ul variants={container} initial="hidden" animate="visible" className="space-y-3">
      {items.map((i) => (
        <motion.li key={i.id} variants={item} className="bg-card rounded-lg border p-4">
          <h3 className="font-medium">{i.title}</h3>
          <p className="text-muted-foreground text-sm">{i.description}</p>
        </motion.li>
      ))}
    </motion.ul>
  );
}
```

`staggerChildren` -- задержка между дочерними элементами. Variants наследуются: дети автоматически получают `initial`/`animate` от родителя.

---

### 5.3. View Transitions API в Next.js

**Статус (апрель 2026):** экспериментальный. Chrome, Edge, Firefox -- полная поддержка. Safari -- частичная. Без поддержки браузера приложение работает нормально, просто без переходов.

```ts
// next.config.ts
const nextConfig: NextConfig = {
  experimental: { viewTransition: true },
};
```

```tsx
// app/layout.tsx -- React <ViewTransition> (Canary)
import { ViewTransition } from 'react';

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>
        <ViewTransition name="page-content">{children}</ViewTransition>
      </body>
    </html>
  );
}
```

```css
/* CSS для кастомных переходов */
::view-transition-old(page-content) {
  animation: fade-out 200ms ease-out;
}
::view-transition-new(page-content) {
  animation: fade-in 200ms ease-in;
}

::view-transition-old(hero-image) {
  animation: slide-out 300ms cubic-bezier(0.2, 0, 0, 1);
}
::view-transition-new(hero-image) {
  animation: slide-in 300ms cubic-bezier(0.2, 0, 0, 1);
}

@keyframes fade-out {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}
@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
@keyframes slide-out {
  to {
    transform: translateX(-100%);
  }
}
@keyframes slide-in {
  from {
    transform: translateX(100%);
  }
}
```

При навигации через `<Link>` или `router.push()` Next.js автоматически запускает View Transition. Для enterprise -- пока с осторожностью (experimental API).

---

### 5.4. CSS-анимации с Tailwind CSS v4

```css
/* globals.css -- кастомные анимации через @theme */
@theme {
  --animate-fade-in: fade-in 0.3s var(--ease-snappy);
  --animate-slide-up: slide-up 0.3s var(--ease-fluid);
  --animate-scale-in: scale-in 0.2s var(--ease-snappy);
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes scale-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
```

Использование: `class="animate-fade-in"`, `class="animate-slide-up"`. Встроенные: `animate-spin`, `animate-ping`, `animate-pulse`, `animate-bounce`.

---

### 5.5. tailwindcss-motion -- CSS-only анимации

Плагин от RomboHQ: модульные утилит-классы без keyframes. Чистый CSS, нулевой JS.

```bash
pnpm add tailwindcss-motion
```

```css
/* globals.css */
@import 'tailwindcss';
@plugin 'tailwindcss-motion';
```

```html
<!-- Композиция анимаций -->
<div class="motion-translate-y-in-8 motion-opacity-in-0 motion-duration-300 motion-ease-out">
  Слайд снизу с fade
</div>

<!-- Scale-in для модальных -->
<div class="motion-scale-in-95 motion-opacity-in-0 motion-duration-200">Modal</div>

<!-- Пресеты -->
<div class="motion-preset-fade">Fade</div>
<div class="motion-preset-slide-up">Slide Up</div>
<div class="motion-preset-bounce">Bounce</div>

<!-- Spring -->
<div class="motion-translate-y-in-8 motion-opacity-in-0 motion-spring-smooth">Spring</div>

<!-- Stagger вручную через delay -->
<div class="motion-preset-fade motion-delay-0">1</div>
<div class="motion-preset-fade motion-delay-100">2</div>
<div class="motion-preset-fade motion-delay-200">3</div>
```

**Когда:** входные анимации без JS. Идеально для Server Components.

---

### 5.6. Loading Skeleton анимации

```tsx
// components/ui/skeleton.tsx
import { cn } from '@/lib/utils';

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('bg-muted animate-pulse rounded-md', className)} {...props} />;
}

export function CardSkeleton() {
  return (
    <div className="border-border bg-card space-y-4 rounded-xl border p-6">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-8 w-20 rounded-md" />
        <Skeleton className="h-8 w-20 rounded-md" />
      </div>
    </div>
  );
}
```

Shimmer-эффект (продвинутый скелетон):

```tsx
export function ShimmerSkeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'bg-muted relative overflow-hidden rounded-md',
        'before:absolute before:inset-0',
        'before:bg-linear-to-r before:from-transparent before:via-white/20 before:to-transparent',
        'before:animate-[shimmer_2s_infinite]',
        className,
      )}
      {...props}
    />
  );
}
```

```css
@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
@theme {
  --animate-shimmer: shimmer 2s infinite;
}
```

---

### 5.7. Производительность анимаций

#### GPU-ускоренные свойства

| Свойство              | GPU | Примечание               |
| --------------------- | --- | ------------------------ |
| `transform`           | Да  | translate, scale, rotate |
| `opacity`             | Да  | Всегда быстрая           |
| `filter`              | Да  | blur, brightness         |
| `width`/`height`      | Нет | reflow                   |
| `margin`/`top`/`left` | Нет | reflow                   |

#### Ключевые правила

```css
/* will-change -- подсказка браузеру (убирай после анимации!) */
.animated-element {
  will-change: transform, opacity;
}

/* contain -- изоляция рендеринга для сложных компонентов */
.sidebar {
  contain: layout style paint;
}
```

#### prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

```tsx
import { useReducedMotion } from 'motion/react';

export function AnimatedWidget({ children }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={{ opacity: 0, y: reduce ? 0 : 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.3 }}
    >
      {children}
    </motion.div>
  );
}
```

#### Чеклист

- Анимируй только `transform` и `opacity`
- `will-change` только на активно анимируемых элементах
- `box-shadow` -- через `::after` + `opacity`, не напрямую
- Списки >50 элементов -- анимируй только видимые (Intersection Observer)
- Всегда уважай `prefers-reduced-motion`

---

## 6. Иконки

### 6.1. Lucide React -- установка и оптимизация

Стандарт для shadcn/ui. ~29.4M скачиваний/неделю (2026), 1500+ иконок, ESM-first, tree-shakeable.

```bash
pnpm add lucide-react
```

```tsx
// ПРАВИЛЬНО -- именованные импорты
import { Search, Settings, ChevronRight } from 'lucide-react';

// ПРАВИЛЬНО -- прямой импорт (быстрее CI: 5.6s -> 0.784s, модули: 1637 -> 35)
import { Search } from 'lucide-react/icons/search';

// НЕПРАВИЛЬНО -- тянет ВСЕ иконки в бандл!
import * as Icons from 'lucide-react';
```

Tree-shaking работает благодаря: `"sideEffects": false` в package.json, каждая иконка -- ESM-экспорт, все бандлеры (Webpack, Vite, Turbopack) корректно обрабатывают.

---

### 6.2. Icon Wrapper компонент

```tsx
// components/ui/icon.tsx
import { type LucideIcon, type LucideProps } from 'lucide-react';
import { cn } from '@/lib/utils';

type IconSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

const sizeMap: Record<IconSize, string> = {
  xs: 'size-3',
  sm: 'size-4',
  md: 'size-5',
  lg: 'size-6',
  xl: 'size-8',
};

interface IconProps extends Omit<LucideProps, 'size'> {
  icon: LucideIcon;
  size?: IconSize;
}

export function Icon({ icon: Comp, size = 'md', className, ...props }: IconProps) {
  return (
    <Comp
      className={cn(sizeMap[size], 'shrink-0', className)}
      strokeWidth={size === 'xs' || size === 'sm' ? 2 : 1.75}
      aria-hidden="true"
      {...props}
    />
  );
}

// Использование:
// <Icon icon={Search} size="sm" className="text-muted-foreground" />
```

**Зачем:** единые размеры, `aria-hidden` по умолчанию, `shrink-0` для flex, адаптивный `strokeWidth`.

---

### 6.3. SVG Sprite система для кастомных иконок

Lucide покрывает ~90%, но брендовые/кастомные иконки требуют спрайт-системы.

```
src/assets/icons/
  raw/              # исходные SVG
  sprite.svg        # сгенерированный спрайт (в public/icons/)
```

```xml
<!-- public/icons/sprite.svg -->
<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">
  <symbol id="logo" viewBox="0 0 24 24">
    <path d="M12 2L2 7l10 5 10-5-10-5z" />
  </symbol>
  <symbol id="custom-chart" viewBox="0 0 24 24">
    <rect x="3" y="12" width="4" height="9" rx="1" />
    <rect x="10" y="6" width="4" height="15" rx="1" />
    <rect x="17" y="3" width="4" height="18" rx="1" />
  </symbol>
</svg>
```

```tsx
// components/ui/sprite-icon.tsx
import { cn } from '@/lib/utils';

type SpriteIconName = 'logo' | 'custom-chart' | 'notification-bell';

interface SpriteIconProps extends React.SVGAttributes<SVGSVGElement> {
  name: SpriteIconName;
  size?: number;
}

export function SpriteIcon({ name, size = 24, className, ...props }: SpriteIconProps) {
  return (
    <svg
      width={size}
      height={size}
      className={cn('shrink-0', className)}
      aria-hidden="true"
      {...props}
    >
      <use href={`/icons/sprite.svg#${name}`} />
    </svg>
  );
}
```

#### Автоматическая генерация

```bash
pnpm add -D svgo svg-sprite
```

```jsonc
// package.json
{
  "scripts": {
    "icons:optimize": "svgo -f src/assets/icons/raw -o src/assets/icons/optimized",
    "icons:sprite": "svg-sprite --symbol --symbol-dest=public/icons --symbol-sprite=sprite.svg src/assets/icons/optimized/*.svg",
    "icons:build": "pnpm icons:optimize && pnpm icons:sprite",
  },
}
```

#### Inline SVG (SVGR) vs SVG Sprite

| Критерий          | Inline SVG (SVGR) | SVG Sprite (`<use>`) |
| ----------------- | ----------------- | -------------------- |
| **Bundle impact** | Увеличивает JS    | Нулевой JS           |
| **Кеширование**   | Нет (часть JS)    | Да (HTTP-кеш)        |
| **Стилизация**    | Полная            | Через `currentColor` |
| **Рекомендация**  | <20 иконок        | Любое количество     |

---

### 6.4. Унифицированный Icon API (Lucide + Sprite)

```tsx
// components/ui/app-icon.tsx
import { type LucideIcon, type LucideProps } from 'lucide-react';
import { cn } from '@/lib/utils';

type IconSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
const sizes: Record<IconSize, { cls: string; px: number }> = {
  xs: { cls: 'size-3', px: 12 },
  sm: { cls: 'size-4', px: 16 },
  md: { cls: 'size-5', px: 20 },
  lg: { cls: 'size-6', px: 24 },
  xl: { cls: 'size-8', px: 32 },
};

interface LucideIconProps extends Omit<LucideProps, 'size'> {
  type: 'lucide';
  icon: LucideIcon;
  size?: IconSize;
}
interface SpriteIconProps extends React.SVGAttributes<SVGSVGElement> {
  type: 'sprite';
  name: string;
  size?: IconSize;
}

export function AppIcon(props: LucideIconProps | SpriteIconProps) {
  const { size = 'md', className } = props;
  if (props.type === 'lucide') {
    const { icon: Comp, type: _, ...rest } = props;
    return (
      <Comp className={cn(sizes[size].cls, 'shrink-0', className)} aria-hidden="true" {...rest} />
    );
  }
  const { name, type: _, ...rest } = props;
  return (
    <svg
      width={sizes[size].px}
      height={sizes[size].px}
      className={cn('shrink-0', className)}
      aria-hidden="true"
      {...rest}
    >
      <use href={`/icons/sprite.svg#${name}`} />
    </svg>
  );
}
```

---

### 6.5. Иконки и доступность (a11y)

```tsx
// Декоративная (большинство случаев) -- скрыта от скринридеров
<Search className="size-4" aria-hidden="true" />

// Семантическая (без текста) -- aria-label на кнопке
<button aria-label="Search">
  <Search className="size-5" aria-hidden="true" />
</button>

// С текстом -- иконка скрыта, текст достаточен
<button>
  <Search className="size-4" aria-hidden="true" />
  <span>Search</span>
</button>

// Статусная -- role="img"
<AlertCircle className="size-4 text-destructive" role="img" aria-label="Error" />
```

---

## Итоговые деревья решений

```
Анимации:
├── hover/focus/transition         -> CSS + Tailwind (L0)
├── входные/выходные без JS        -> tailwindcss-motion (L1)
├── exit, layout, gestures, scroll -> Motion (L2)
├── переходы между страницами      -> View Transitions API (L3, experimental)
└── сложные таймлайны              -> GSAP (L4)

Иконки:
├── стандартная UI                 -> Lucide React (именованный импорт)
├── кастомная/брендовая            -> SVG Sprite система
├── анимированная                  -> Lucide + Motion (motion.div wrapper)
└── одноразовая иллюстрация        -> Inline SVG / SVGR
```

### Ключевые пакеты

```bash
pnpm add motion                  # ~85KB, анимации
pnpm add tailwindcss-motion      # ~5KB CSS-only анимации
pnpm add lucide-react            # 1500+ иконок, tree-shakeable
pnpm add -D svgo svg-sprite      # генерация SVG-спрайтов
```

---

_Источники:_

- _[Motion -- official docs](https://motion.dev/docs/react)_
- _[Next.js -- View Transitions](https://nextjs.org/docs/app/guides/view-transitions)_
- _[tailwindcss-motion -- GitHub](https://github.com/romboHQ/tailwindcss-motion)_
- _[Lucide React -- deep dive](https://expertbeacon.com/lucide-react-technical-guide/)_
- _[SVG Sprites in React](https://benadam.me/thoughts/react-svg-sprites/)_
- _[Icon Libraries Bundle Size 2026](https://medium.com/codetodeploy/the-hidden-bundle-cost-of-react-icons-why-lucide-wins-in-2026-1ddb74c1a86c)_
- _[Rombo tailwindcss-motion](https://rombo.co/tailwind/)_
- _[next-view-transitions](https://github.com/shuding/next-view-transitions)_

---

---

# Часть 4 — Layout-паттерны и отображение данных

> Enterprise-дашборды | Апрель 2026

---

## 7.1. Полная архитектура dashboard-layout

### Принцип: CSS Grid для каркаса, Flexbox для содержимого

Enterprise-дашборд строится на трех уровнях:

1. **Shell** -- CSS Grid (header + sidebar + main)
2. **Page** -- Flexbox/Grid (breadcrumbs + toolbar + content area)
3. **Widgets** -- Grid (KPI-карточки, графики, таблицы)

### Реализация корневого layout

```tsx
// app/(dashboard)/layout.tsx
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/app-sidebar';
import { Separator } from '@/components/ui/separator';
import { DynamicBreadcrumbs } from '@/components/dynamic-breadcrumbs';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        {/* Header */}
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <DynamicBreadcrumbs />
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
```

### CSS Grid структура (детальная)

```css
/* Tailwind v4 -- определяется через утилиты, но для понимания: */
.dashboard-shell {
  display: grid;
  grid-template-areas:
    'sidebar header'
    'sidebar main';
  grid-template-columns: var(--sidebar-width, 256px) 1fr;
  grid-template-rows: 56px 1fr;
  min-height: 100dvh; /* dvh для мобильных браузеров */
}

/* Свернутый sidebar */
.dashboard-shell[data-collapsed='true'] {
  grid-template-columns: var(--sidebar-width-collapsed, 48px) 1fr;
}

/* Мобильная версия: sidebar как Sheet overlay */
@media (max-width: 768px) {
  .dashboard-shell {
    grid-template-areas: 'header' 'main';
    grid-template-columns: 1fr;
  }
}
```

---

## 7.2. Sidebar: shadcn/ui Sidebar компонент

### Ключевые возможности

| Возможность             | Реализация                                                                      |
| ----------------------- | ------------------------------------------------------------------------------- |
| **Сворачивание**        | `collapsible="icon"` -- иконки остаются, текст скрывается                       |
| **Клавиатура**          | `Cmd+B` (Mac) / `Ctrl+B` (Win), настраивается через `SIDEBAR_KEYBOARD_SHORTCUT` |
| **Мобильная версия**    | Автоматический переход на Sheet (drawer) на экранах < 768px                     |
| **Персистентность**     | Состояние (open/closed) сохраняется в cookies                                   |
| **Вложенная навигация** | Collapsible группы с `ChevronRight` индикаторами                                |

### Полная реализация sidebar с вложенной навигацией

```tsx
// components/app-sidebar.tsx
'use client';

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarHeader,
  SidebarFooter,
  SidebarRail,
} from '@/components/ui/sidebar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  LayoutDashboard,
  BarChart3,
  Users,
  Settings,
  ChevronRight,
  CreditCard,
  FileText,
  Bell,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navigation = [
  {
    title: 'Dashboard',
    icon: LayoutDashboard,
    href: '/dashboard',
  },
  {
    title: 'Analytics',
    icon: BarChart3,
    items: [
      { title: 'Overview', href: '/analytics' },
      { title: 'Reports', href: '/analytics/reports' },
      { title: 'Real-time', href: '/analytics/realtime' },
    ],
  },
  {
    title: 'Users',
    icon: Users,
    items: [
      { title: 'All Users', href: '/users' },
      { title: 'Roles', href: '/users/roles' },
    ],
  },
  {
    title: 'Billing',
    icon: CreditCard,
    items: [
      { title: 'Invoices', href: '/billing/invoices' },
      { title: 'Plans', href: '/billing/plans' },
    ],
  },
  {
    title: 'Settings',
    icon: Settings,
    href: '/settings',
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard">
                <div className="bg-primary text-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  A
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Acme Corp</span>
                  <span className="text-muted-foreground truncate text-xs">Enterprise</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Platform</SidebarGroupLabel>
          <SidebarMenu>
            {navigation.map((item) =>
              item.items ? (
                <Collapsible
                  key={item.title}
                  defaultOpen={item.items.some((sub) => pathname.startsWith(sub.href))}
                  className="group/collapsible"
                >
                  <SidebarMenuItem>
                    <CollapsibleTrigger asChild>
                      <SidebarMenuButton tooltip={item.title}>
                        <item.icon className="size-4" />
                        <span>{item.title}</span>
                        <ChevronRight className="ml-auto size-4 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                      </SidebarMenuButton>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <SidebarMenuSub>
                        {item.items.map((sub) => (
                          <SidebarMenuSubItem key={sub.href}>
                            <SidebarMenuSubButton asChild isActive={pathname === sub.href}>
                              <Link href={sub.href}>{sub.title}</Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </SidebarMenuItem>
                </Collapsible>
              ) : (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={pathname === item.href} tooltip={item.title}>
                    <Link href={item.href!}>
                      <item.icon className="size-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ),
            )}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>{/* User menu, notifications, etc. */}</SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
```

### Кастомизация клавиатурного шортката

```tsx
// По умолчанию: Cmd+B / Ctrl+B
// Изменение:
import { SIDEBAR_KEYBOARD_SHORTCUT } from '@/components/ui/sidebar';

// В sidebar.tsx компоненте можно переопределить:
const SIDEBAR_KEYBOARD_SHORTCUT = 's'; // теперь Cmd+S / Ctrl+S
```

---

## 7.3. Breadcrumbs с динамическими сегментами

```tsx
// components/dynamic-breadcrumbs.tsx
'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Fragment } from 'react';

// Маппинг slug -> человекочитаемое название
const segmentLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  analytics: 'Analytics',
  reports: 'Reports',
  users: 'Users',
  settings: 'Settings',
  billing: 'Billing',
  invoices: 'Invoices',
};

function formatSegment(segment: string): string {
  return segmentLabels[segment] ?? segment.charAt(0).toUpperCase() + segment.slice(1);
}

export function DynamicBreadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {segments.map((segment, index) => {
          const href = '/' + segments.slice(0, index + 1).join('/');
          const isLast = index === segments.length - 1;

          return (
            <Fragment key={href}>
              {index > 0 && <BreadcrumbSeparator />}
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{formatSegment(segment)}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link href={href}>{formatSegment(segment)}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
```

---

## 7.4. Стратегия responsive-брейкпоинтов

### Mobile-first подход Tailwind v4

Tailwind использует **mobile-first** систему: стили без префикса применяются ко всем экранам, префикс `md:` -- от 768px и выше. Это означает, что базовые стили пишутся для мобильных устройств.

### Стандартные брейкпоинты + кастомные

```css
/* globals.css */
@theme {
  /* Стандартные Tailwind v4 брейкпоинты: */
  /* sm: 640px, md: 768px, lg: 1024px, xl: 1280px, 2xl: 1536px */

  /* Кастомные для enterprise-дашбордов: */
  --breakpoint-3xl: 1920px; /* Full HD мониторы */
  --breakpoint-4xl: 2560px; /* 2K мониторы */
}
```

### Стратегия для dashboard-компонентов

| Брейкпоинт        | Ширина    | Layout | Sidebar             | Колонки KPI                |
| ----------------- | --------- | ------ | ------------------- | -------------------------- |
| **Base** (mobile) | < 640px   | Стек   | Sheet (overlay)     | 1 колонка                  |
| **sm**            | >= 640px  | Стек   | Sheet (overlay)     | 2 колонки                  |
| **md**            | >= 768px  | Grid   | Свернутый (icon)    | 2 колонки                  |
| **lg**            | >= 1024px | Grid   | Развернутый (256px) | 3 колонки                  |
| **xl**            | >= 1280px | Grid   | Развернутый         | 4 колонки                  |
| **2xl**           | >= 1536px | Grid   | Развернутый         | 4 колонки + боковая панель |

### Применение в компонентах

```tsx
// KPI-карточки: адаптивная сетка
<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
  <KPICard title="Revenue" value="$124,500" trend={+12.5} />
  <KPICard title="Users" value="12,340" trend={+5.2} />
  <KPICard title="Orders" value="1,234" trend={-2.1} />
  <KPICard title="Conversion" value="3.2%" trend={+0.8} />
</div>

// Графики: полная ширина на мобильном, 2 колонки на десктопе
<div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
  <AreaChartWidget />
  <BarChartWidget />
</div>

// Таблица: горизонтальный скролл на мобильном
<div className="overflow-x-auto">
  <DataTable columns={columns} data={data} />
</div>
```

### Container queries -- будущее responsive

```tsx
// Tailwind v4 поддерживает container queries нативно:
<div className="@container">
  <div className="grid grid-cols-1 @md:grid-cols-2 @lg:grid-cols-3">
    {/* Карточки адаптируются к размеру контейнера, а не viewport */}
  </div>
</div>
```

Container queries позволяют виджетам адаптироваться к размеру **родительского контейнера**, а не viewport. Это критично для дашбордов, где один и тот же виджет может быть размещен в разных зонах разного размера.

---

---

## 8. Отображение данных

## 8.1. TanStack Table: серверная пагинация, сортировка, фильтрация

### Архитектура: разделение client/server

Ключевой принцип -- `manualPagination`, `manualSorting`, `manualFiltering`. Когда эти опции включены, TanStack Table **не обрабатывает данные сам**, а ожидает уже обработанные данные с сервера.

### Типы и интерфейсы

```ts
// types/table.ts
export interface PaginationState {
  pageIndex: number;
  pageSize: number;
}

export interface SortingState {
  id: string;
  desc: boolean;
}

export interface ColumnFilter {
  id: string;
  value: unknown;
}

export interface ServerTableResponse<T> {
  data: T[];
  pageCount: number;
  totalRows: number;
}

// URL search params формат для серверной обработки
export interface TableSearchParams {
  page?: string;
  per_page?: string;
  sort?: string; // "name.asc" или "name.desc"
  filters?: string; // JSON-строка фильтров
}
```

### Server Action для получения данных (BFF proxy)

```ts
// app/(dashboard)/users/actions.ts
'use server';

import { apiServer } from '@/lib/api-server';
import { requireAuth } from '@/lib/dal';
import type { TableSearchParams, ServerTableResponse } from '@/types/table';

export async function getUsers(params: TableSearchParams): Promise<ServerTableResponse<User>> {
  const user = await requireAuth();

  // Proxy к бэкенд-сервису — сортировка, фильтрация, пагинация на стороне бэкенда
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', params.page);
  if (params.per_page) searchParams.set('per_page', params.per_page);
  if (params.sort) searchParams.set('sort', params.sort);
  if (params.filters) searchParams.set('filters', params.filters);

  return apiServer.get<ServerTableResponse<User>>(`/users?${searchParams.toString()}`, {
    headers: { Authorization: `Bearer ${user.token}` },
  });
}
```

> **Примечание BFF:** вся логика сортировки, фильтрации и пагинации выполняется на бэкенд-сервисе.
> Server Action только проверяет авторизацию и проксирует параметры.

### Клиентский компонент таблицы с URL-синхронизацией

```tsx
// components/data-table/data-table.tsx
'use client';

import { useCallback, useMemo } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
  type PaginationState,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { DataTablePagination } from './data-table-pagination';
import { DataTableToolbar } from './data-table-toolbar';

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  pageCount: number;
  totalRows: number;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  pageCount,
  totalRows,
}: DataTableProps<TData, TValue>) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Читаем состояние из URL
  const pagination: PaginationState = {
    pageIndex: Number(searchParams.get('page') ?? 1) - 1,
    pageSize: Number(searchParams.get('per_page') ?? 10),
  };

  const sorting: SortingState = useMemo(() => {
    const sort = searchParams.get('sort');
    if (!sort) return [];
    const [id, order] = sort.split('.');
    return [{ id, desc: order === 'desc' }];
  }, [searchParams]);

  // Обновляем URL при изменении состояния
  const updateSearchParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null) params.delete(key);
        else params.set(key, value);
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [router, pathname, searchParams],
  );

  const table = useReactTable({
    data,
    columns,
    pageCount,
    state: { pagination, sorting },
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    getCoreRowModel: getCoreRowModel(),
    onPaginationChange: (updater) => {
      const next = typeof updater === 'function' ? updater(pagination) : updater;
      updateSearchParams({
        page: String(next.pageIndex + 1),
        per_page: String(next.pageSize),
      });
    },
    onSortingChange: (updater) => {
      const next = typeof updater === 'function' ? updater(sorting) : updater;
      updateSearchParams({
        sort: next.length > 0 ? `${next[0].id}.${next[0].desc ? 'desc' : 'asc'}` : null,
        page: '1', // сброс на первую страницу при смене сортировки
      });
    },
  });

  return (
    <div className="space-y-4">
      <DataTableToolbar table={table} />
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <DataTablePagination table={table} totalRows={totalRows} />
    </div>
  );
}
```

### Column visibility (переключение колонок)

```tsx
// components/data-table/data-table-view-options.tsx
'use client';

import { type Table } from '@tanstack/react-table';
import { Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface DataTableViewOptionsProps<TData> {
  table: Table<TData>;
}

export function DataTableViewOptions<TData>({ table }: DataTableViewOptionsProps<TData>) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="ml-auto hidden h-8 lg:flex">
          <Settings2 className="mr-2 size-4" />
          Columns
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-37.5">
        <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {table
          .getAllColumns()
          .filter((col) => col.getCanHide())
          .map((col) => (
            <DropdownMenuCheckboxItem
              key={col.id}
              className="capitalize"
              checked={col.getIsVisible()}
              onCheckedChange={(value) => col.toggleVisibility(!!value)}
            >
              {col.id}
            </DropdownMenuCheckboxItem>
          ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---

## 8.2. TanStack Table: виртуальный скроллинг для больших датасетов

Когда датасет содержит тысячи строк и серверная пагинация нежелательна (например, оффлайн-режим), используется `@tanstack/react-virtual`.

```bash
pnpm add @tanstack/react-virtual
```

```tsx
// components/data-table/virtualized-table.tsx
'use client';

import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useReactTable, getCoreRowModel, flexRender, type ColumnDef } from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const ROW_HEIGHT = 48;

interface VirtualizedTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
}

export function VirtualizedTable<TData, TValue>({
  columns,
  data,
}: VirtualizedTableProps<TData, TValue>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { rows } = table.getRowModel();

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 20, // рендерим 20 строк за пределами viewport для плавного скролла
  });

  return (
    <div ref={parentRef} className="h-150 overflow-auto rounded-md border">
      <Table>
        <TableHeader className="bg-background sticky top-0 z-10">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {/* Верхний спейсер */}
          {virtualizer.getVirtualItems()[0]?.start > 0 && (
            <tr>
              <td style={{ height: virtualizer.getVirtualItems()[0].start }} />
            </tr>
          )}

          {virtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            return (
              <TableRow key={row.id} style={{ height: ROW_HEIGHT }}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}

          {/* Нижний спейсер */}
          <tr>
            <td
              style={{
                height:
                  virtualizer.getTotalSize() - (virtualizer.getVirtualItems().at(-1)?.end ?? 0),
              }}
            />
          </tr>
        </TableBody>
      </Table>
    </div>
  );
}
```

**Производительность:** виртуальный скроллинг рендерит только видимые строки + `overscan`. 10,000 строк ведут себя как 50 -- DOM содержит только ~50-70 элементов.

---

## 8.3. Графики: Recharts -- настройка и типовые графики

### Установка и настройка

```bash
pnpm add recharts
```

### Обертка для responsive-графиков

```tsx
// components/charts/chart-container.tsx
'use client';

import { ResponsiveContainer } from 'recharts';

interface ChartContainerProps {
  children: React.ReactElement;
  height?: number;
}

export function ChartContainer({ children, height = 350 }: ChartContainerProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      {children}
    </ResponsiveContainer>
  );
}
```

### Area Chart (основной для revenue/traffic)

```tsx
// components/charts/area-chart-widget.tsx
'use client';

import { Area, AreaChart, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import { ChartContainer } from './chart-container';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const data = [
  { month: 'Jan', revenue: 4000, expenses: 2400 },
  { month: 'Feb', revenue: 3000, expenses: 1398 },
  { month: 'Mar', revenue: 9800, expenses: 2000 },
  { month: 'Apr', revenue: 3908, expenses: 2780 },
  { month: 'May', revenue: 4800, expenses: 1890 },
  { month: 'Jun', revenue: 3800, expenses: 2390 },
];

export function AreaChartWidget() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Revenue vs Expenses</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer>
          <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="month" className="fill-muted-foreground text-xs" />
            <YAxis className="fill-muted-foreground text-xs" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--popover))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
              }}
            />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="hsl(var(--chart-1))"
              fill="url(#colorRevenue)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="expenses"
              stroke="hsl(var(--chart-2))"
              fill="none"
              strokeWidth={2}
              strokeDasharray="5 5"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
```

### Bar Chart, Pie Chart, Line Chart -- краткие примеры

```tsx
// Bar Chart
import { Bar, BarChart, XAxis, YAxis, Tooltip } from 'recharts';

<BarChart data={data}>
  <XAxis dataKey="name" />
  <YAxis />
  <Tooltip />
  <Bar dataKey="value" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
</BarChart>;

// Pie Chart
import { Pie, PieChart, Cell, Tooltip } from 'recharts';

const COLORS = ['hsl(var(--chart-1))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))'];

<PieChart>
  <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
    {data.map((_, index) => (
      <Cell key={index} fill={COLORS[index % COLORS.length]} />
    ))}
  </Pie>
  <Tooltip />
</PieChart>;

// Line Chart
import { Line, LineChart, XAxis, YAxis, Tooltip, Legend } from 'recharts';

<LineChart data={data}>
  <XAxis dataKey="date" />
  <YAxis />
  <Tooltip />
  <Legend />
  <Line type="monotone" dataKey="users" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={false} />
  <Line
    type="monotone"
    dataKey="sessions"
    stroke="hsl(var(--chart-2))"
    strokeWidth={2}
    dot={false}
  />
</LineChart>;
```

---

## 8.4. Tremor vs Recharts: руководство по выбору

### Архитектурное отличие

Tremor -- это **высокоуровневая обертка над Recharts** с нативной интеграцией Tailwind CSS. Tremor генерирует Recharts-компоненты внутри, но предоставляет упрощенный декларативный API.

### Когда что использовать

| Критерий                     | Recharts               | Tremor                           |
| ---------------------------- | ---------------------- | -------------------------------- |
| **Уровень контроля**         | Полный (SVG-примитивы) | Ограничен API                    |
| **Кастомные tooltip/legend** | Полная свобода         | Через props                      |
| **Скорость разработки**      | Средняя (больше кода)  | Высокая (1 компонент = 1 график) |
| **Bundle size**              | ~180 KB                | ~240 KB (Recharts + обертка)     |
| **Tailwind интеграция**      | Ручная (CSS vars)      | Нативная                         |
| **Кол-во типов графиков**    | 10+                    | 6 основных                       |
| **KPI-карточки**             | Нет (делать самим)     | Есть из коробки                  |
| **Темная тема**              | Ручная настройка       | Автоматическая                   |

### Рекомендация

- **Recharts**: когда нужны кастомные визуализации, нестандартные tooltip, анимации, комбинированные графики, интерактивные элементы (brush, zoom)
- **Tremor**: когда нужен быстрый MVP дашборда с KPI-карточками и стандартными графиками
- **Nivo**: избегать для enterprise -- плохая документация, сложная кастомизация

### Гибридный подход (рекомендуемый)

Начать с Tremor для быстрого прототипирования. Заменять отдельные графики на Recharts по мере роста требований к кастомизации. Поскольку Tremor использует Recharts внутри, миграция безболезненна.

---

## 8.5. KPI Card -- паттерн компонента

```tsx
// components/kpi-card.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUpRight, ArrowDownRight, Minus, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KPICardProps {
  title: string;
  value: string;
  trend?: number; // процент изменения, например +12.5 или -3.2
  trendLabel?: string; // "vs last month"
  icon?: LucideIcon;
  description?: string;
}

export function KPICard({
  title,
  value,
  trend,
  trendLabel,
  icon: Icon,
  description,
}: KPICardProps) {
  const TrendIcon =
    trend === undefined || trend === 0 ? Minus : trend > 0 ? ArrowUpRight : ArrowDownRight;

  const trendColor =
    trend === undefined || trend === 0
      ? 'text-muted-foreground'
      : trend > 0
        ? 'text-emerald-600 dark:text-emerald-400'
        : 'text-red-600 dark:text-red-400';

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-muted-foreground text-sm font-medium">{title}</CardTitle>
        {Icon && <Icon className="text-muted-foreground size-4" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend !== undefined && (
          <div className="mt-1 flex items-center gap-1">
            <TrendIcon className={cn('size-4', trendColor)} />
            <span className={cn('text-xs font-medium', trendColor)}>
              {trend > 0 ? '+' : ''}
              {trend}%
            </span>
            {trendLabel && <span className="text-muted-foreground text-xs">{trendLabel}</span>}
          </div>
        )}
        {description && <p className="text-muted-foreground mt-1 text-xs">{description}</p>}
      </CardContent>
    </Card>
  );
}
```

### Использование

```tsx
<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
  <KPICard
    title="Total Revenue"
    value="$45,231.89"
    trend={20.1}
    trendLabel="vs last month"
    icon={DollarSign}
  />
  <KPICard
    title="Subscriptions"
    value="+2,350"
    trend={180.1}
    trendLabel="vs last month"
    icon={Users}
  />
  <KPICard title="Sales" value="+12,234" trend={19} trendLabel="vs last month" icon={CreditCard} />
  <KPICard title="Active Now" value="573" trend={-2.5} trendLabel="vs last hour" icon={Activity} />
</div>
```

---

## 8.6. Empty State паттерны

Empty state -- критически важный UX-элемент. Три типа:

### Универсальный компонент

```tsx
// components/empty-state.tsx
import { type LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-100 flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
      <div className="bg-muted flex size-12 items-center justify-center rounded-full">
        <Icon className="text-muted-foreground size-6" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="text-muted-foreground mt-2 max-w-sm text-sm">{description}</p>
      {action && (
        <Button onClick={action.onClick} className="mt-6">
          {action.label}
        </Button>
      )}
    </div>
  );
}
```

### Три типа empty state

```tsx
// 1. Первый запуск (onboarding)
<EmptyState
  icon={Inbox}
  title="No projects yet"
  description="Get started by creating your first project. It only takes a minute."
  action={{ label: "Create Project", onClick: () => setOpen(true) }}
/>

// 2. Пустой результат поиска/фильтрации
<EmptyState
  icon={SearchX}
  title="No results found"
  description="Try adjusting your search or filter criteria to find what you're looking for."
  action={{ label: "Clear Filters", onClick: clearFilters }}
/>

// 3. Ошибка загрузки
<EmptyState
  icon={AlertCircle}
  title="Something went wrong"
  description="We couldn't load the data. Please try again or contact support if the issue persists."
  action={{ label: "Try Again", onClick: refetch }}
/>
```

---

## Итоговая карта компонентов

```
Dashboard Layout
+-- SidebarProvider
|   +-- AppSidebar (collapsible, nested nav, mobile sheet, Cmd+B)
|   +-- SidebarInset
|       +-- Header (SidebarTrigger + Breadcrumbs + Actions)
|       +-- Main Content
|           +-- KPI Cards (grid, responsive cols)
|           +-- Charts (Recharts/Tremor, ResponsiveContainer)
|           +-- DataTable (TanStack Table, server-side ops)
|           +-- EmptyState (onboarding / no results / error)

Данные:
  Server Action -> URL search params -> DataTable (manual pagination/sorting)
  Large datasets -> VirtualizedTable (@tanstack/react-virtual)

Графики:
  Стандартные -> Tremor (быстро, Tailwind-нативно)
  Кастомные -> Recharts (полный контроль)
  Не рекомендуется -> Nivo (плохая документация)
```

---

_Источники:_

- _[shadcn/ui Sidebar](https://ui.shadcn.com/docs/components/radix/sidebar)_
- _[TanStack Table Pagination Guide](https://tanstack.com/table/v8/docs/guide/pagination)_
- _[TanStack Table Sorting Guide](https://tanstack.com/table/v8/docs/guide/sorting)_
- _[Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design)_
- _[Tremor](https://www.tremor.so/)_
- _[Recharts](https://recharts.org/)_
- _[Advanced Shadcn Table](https://next.jqueryscript.net/shadcn-ui/advanced-shadcn-table/)_
- _[AdminLTE: Build Admin Dashboard with shadcn/ui](https://adminlte.io/blog/build-admin-dashboard-shadcn-nextjs/)_
- _[Responsive Design Breakpoints 2025](https://dev.to/gerryleonugroho/responsive-design-breakpoints-2025-playbook-53ih)_
- _[Nivo vs Recharts](https://www.speakeasy.com/blog/nivo-vs-recharts)_

---

---

# Часть 5 — Утилиты, шрифты, изображения и документация

> Enterprise Next.js 15+ App Router

---

## 9.1. cn() -- глубокое погружение

### Как работает cn()

```ts
// lib/utils.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Два этапа:**

1. `clsx` -- разрешает условные классы: объекты `{ "bg-red-500": isError }`, массивы, undefined/null/false
2. `twMerge` -- разрешает конфликты Tailwind-классов: `"p-4 p-2"` -> `"p-2"` (последний побеждает)

### Edge cases и подводные камни

**Кастомные классы не распознаются twMerge:**

```ts
// ПРОБЛЕМА: twMerge не знает, что "card-padding" -- это padding
cn('card-padding', 'p-4'); // "card-padding p-4" -- оба остаются!
```

**Решение -- extendTailwindMerge:**

```ts
import { extendTailwindMerge } from 'tailwind-merge';

const customTwMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      // Добавляем кастомную группу для padding
      padding: ['card-padding'],
      // Кастомные font-size
      'font-size': ['text-heading', 'text-body', 'text-caption'],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return customTwMerge(clsx(inputs));
}
```

**Tailwind v4 CSS-переменные и twMerge:**

С Tailwind v4 все токены `@theme` становятся CSS-переменными. twMerge v2.x+ поддерживает Tailwind v4.0-v4.2. Если вы добавили кастомные значения через `@theme`, twMerge автоматически распознает их как валидные arbitrary-значения.

```ts
// Tailwind v4 @theme: --color-brand-500: oklch(...)
cn('bg-brand-500', 'bg-primary'); // -> "bg-primary" (конфликт разрешен)
```

### Производительность cn()

```
clsx:     ~340,000 ops/sec (микроскопический overhead)
twMerge:  ~95,000 ops/sec (парсинг + кеш LRU на 500 записей)
cn():     ~90,000 ops/sec (bottleneck -- twMerge)
```

**Рекомендации:**

- `extendTailwindMerge` вычисляет тяжелую структуру данных -- вызывайте **один раз** на верхнем уровне модуля
- twMerge использует LRU-кеш (по умолчанию 500 записей). Для enterprise с сотнями компонентов можно увеличить:

```ts
const customTwMerge = extendTailwindMerge({
  cacheSize: 1000, // увеличен кеш
  extend: {
    /* ... */
  },
});
```

- Если вам **не нужно** разрешение конфликтов (например, в статическом контексте), используйте просто `clsx` -- в 3.5x быстрее

---

## 9.2. cva -- продвинутые паттерны

### Compound variants (составные варианты)

Compound variants позволяют применять классы при **комбинации** нескольких вариантов:

```ts
import { cva } from 'class-variance-authority';

const alertVariants = cva('rounded-lg border p-4', {
  variants: {
    intent: {
      info: 'border-blue-200 bg-blue-50 text-blue-800',
      warning: 'border-yellow-200 bg-yellow-50 text-yellow-800',
      error: 'border-red-200 bg-red-50 text-red-800',
    },
    size: {
      sm: 'p-2 text-sm',
      md: 'p-4 text-base',
      lg: 'p-6 text-lg',
    },
    hasIcon: {
      true: 'pl-10',
      false: '',
    },
  },
  compoundVariants: [
    // Когда error + lg -- усиленный стиль
    {
      intent: 'error',
      size: 'lg',
      className: 'border-2 font-semibold shadow-lg',
    },
    // Множественные значения: info ИЛИ warning + hasIcon
    {
      intent: ['info', 'warning'],
      hasIcon: true,
      className: 'pl-12',
    },
  ],
  defaultVariants: {
    intent: 'info',
    size: 'md',
    hasIcon: false,
  },
});
```

### Композиция вариантов (composing)

cva не имеет встроенной композиции, но паттерн реализуется через функции:

```ts
// Базовые варианты текста
const textVariants = cva("", {
  variants: {
    weight: {
      normal: "font-normal",
      medium: "font-medium",
      bold: "font-bold",
    },
    align: {
      left: "text-left",
      center: "text-center",
      right: "text-right",
    },
  },
  defaultVariants: { weight: "normal", align: "left" },
});

// Компонент Badge использует textVariants + свои варианты
const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        outline: "border border-border text-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

// Композиция в компоненте
function Badge({ variant, weight, align, className, ...props }) {
  return (
    <span
      className={cn(
        textVariants({ weight, align }),
        badgeVariants({ variant }),
        className
      )}
      {...props}
    />
  );
}
```

### Типобезопасность: VariantProps

```ts
import { type VariantProps } from 'class-variance-authority';

type AlertProps = React.HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof alertVariants> & {
    icon?: React.ReactNode;
  };

// VariantProps автоматически извлекает:
// { intent?: "info" | "warning" | "error" | null;
//   size?: "sm" | "md" | "lg" | null;
//   hasIcon?: boolean | null; }
```

### cva -- ограничения

- **Нет responsive variants** -- нельзя сделать `size: { sm: "md", lg: "lg" }` (варианты по breakpoint)
- **Нет slots** -- один вызов cva = одна строка классов (нельзя стилизовать вложенные элементы)
- **Нет composability API** -- композиция только вручную через cn()

---

## 9.3. Альтернатива: tailwind-variants (tv)

tailwind-variants (tv) — альтернатива cva с поддержкой slots, responsive variants и extend.
Может быть добавлен позже для сложных составных компонентов.
Основной выбор проекта — cva.

---

## 10. Шрифты: next/font

### Почему next/font

- **Автоматический self-hosting** -- шрифты загружаются с вашего домена, нет запросов к Google Fonts
- **Нулевой layout shift (CLS = 0)** -- CSS `size-adjust` применяется автоматически
- **Оптимальная загрузка** -- `font-display: swap` по умолчанию, preload через `<link rel="preload">`
- **Variable fonts** -- один файл вместо множества weight-файлов

### Настройка: Geist Sans + Geist Mono

Geist -- шрифт Vercel, используется по умолчанию в Next.js 15+:

```tsx
// app/layout.tsx
import { Geist, Geist_Mono } from 'next/font/google';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
  display: 'swap',
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
  display: 'swap',
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
```

### Настройка: Inter (альтернатива)

Inter -- наиболее популярный шрифт для enterprise UI (цифры, таблицы, дашборды):

```tsx
import { Inter } from 'next/font/google';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin', 'cyrillic'], // важно для русского языка!
  display: 'swap',
  axes: ['opsz'], // optical size -- адаптивный рендеринг по размеру текста
});
```

### Интеграция с Tailwind v4

```css
/* globals.css */
@import 'tailwindcss';

@theme {
  --font-sans: var(--font-geist-sans), ui-sans-serif, system-ui, sans-serif;
  --font-mono: var(--font-geist-mono), ui-monospace, monospace;
}
```

Теперь `font-sans` и `font-mono` в Tailwind используют next/font шрифты.

### Локальные шрифты (self-hosted)

Если нужен шрифт, отсутствующий в Google Fonts:

```tsx
import localFont from 'next/font/local';

const customFont = localFont({
  src: [
    { path: '../fonts/CustomFont-Regular.woff2', weight: '400', style: 'normal' },
    { path: '../fonts/CustomFont-Medium.woff2', weight: '500', style: 'normal' },
    { path: '../fonts/CustomFont-Bold.woff2', weight: '700', style: 'normal' },
  ],
  variable: '--font-custom',
  display: 'swap',
});
```

### Рекомендация по шрифтам

| Сценарий                       | Шрифт                                 | Почему                                    |
| ------------------------------ | ------------------------------------- | ----------------------------------------- |
| Enterprise дашборд             | **Inter**                             | Отличные цифры, кириллица, optical sizing |
| Next.js default / Vercel стиль | **Geist Sans + Mono**                 | Дефолт Next.js 15+, современный вид       |
| Документация / контент         | **Inter** или **Source Sans 3**       | Читаемость длинных текстов                |
| Код / терминал                 | **Geist Mono** или **JetBrains Mono** | Лигатуры, различимые символы              |

**Важно:** Максимум 2 font-family на проект. Каждый дополнительный шрифт -- это ресурс, который клиент загружает.

---

## 11. Изображения: next/image

### Базовое использование

```tsx
import Image from 'next/image';

<Image
  src="/hero-banner.jpg"
  alt="Dashboard overview"
  width={1200}
  height={630}
  priority // LCP-изображение -- preload
  quality={85} // 85% достаточно для фото (default: 75)
/>;
```

### Responsive images

```tsx
// fill -- изображение заполняет родительский контейнер
<div className="relative aspect-video w-full">
  <Image
    src="/chart-preview.png"
    alt="Revenue chart"
    fill
    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
    className="rounded-lg object-cover"
  />
</div>
```

**`sizes` -- критически важен** для responsive images. Без него Next.js генерирует srcset с deviceSizes (640, 750, 828, 1080, 1200, 1920, 2048, 3840px), но браузер не знает, какой выбрать.

### Blur placeholder (плавная загрузка)

**Статические импорты -- автоматический blur:**

```tsx
import heroImage from '@/public/hero.jpg';

<Image
  src={heroImage} // статический импорт
  alt="Hero"
  placeholder="blur" // blurDataURL автоматически из файла
  priority
/>;
```

**Динамические изображения -- ручной blurDataURL:**

```tsx
// Генерация blur placeholder на сервере
async function getBlurDataURL(src: string): Promise<string> {
  const response = await fetch(src);
  const buffer = await response.arrayBuffer();
  const base64 = Buffer.from(buffer).toString('base64');

  // Для production используйте sharp или plaiceholder
  return `data:image/jpeg;base64,${base64}`;
}

// Или с библиотекой plaiceholder
import { getPlaiceholder } from 'plaiceholder';

const { base64 } = await getPlaiceholder('/public/photo.jpg');

<Image
  src="/api/images/photo.jpg"
  alt="Photo"
  width={800}
  height={600}
  placeholder="blur"
  blurDataURL={base64}
/>;
```

### Priority и loading стратегия

| Prop              | Когда использовать                                                           |
| ----------------- | ---------------------------------------------------------------------------- |
| `priority`        | LCP-элемент (hero, первый баннер). Отключает lazy loading, добавляет preload |
| `loading="lazy"`  | По умолчанию. Загрузка при приближении к viewport                            |
| `loading="eager"` | Изображение above the fold, но не LCP                                        |

**Правило:** только **одно** изображение на странице должно иметь `priority` -- то, которое является Largest Contentful Paint.

### Art direction (разные изображения для разных экранов)

next/image не поддерживает `<picture>` нативно. Паттерн:

```tsx
// Используем CSS для art direction
<div className="relative w-full">
  {/* Mobile */}
  <Image
    src="/hero-mobile.jpg"
    alt="Hero"
    width={640}
    height={480}
    className="block md:hidden"
    sizes="100vw"
  />
  {/* Desktop */}
  <Image
    src="/hero-desktop.jpg"
    alt="Hero"
    width={1920}
    height={800}
    className="hidden md:block"
    sizes="100vw"
    priority
  />
</div>
```

### Оптимизация: Sharp

Next.js использует Sharp для обработки изображений на сервере. Результаты:

- **Сжатие:** 40-70% уменьшение размера файла
- **Формат:** автоматическая конвертация в WebP (или AVIF при настройке)
- **Суммарно:** 60-80% экономия трафика по сравнению с оригиналом

```ts
// next.config.ts
const config: NextConfig = {
  images: {
    formats: ['image/avif', 'image/webp'], // AVIF приоритетнее (меньше размер)
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    remotePatterns: [{ protocol: 'https', hostname: 'cdn.example.com' }],
  },
};
```

---

## 12. Storybook 8: документация компонентов

### Установка с Next.js + Tailwind

```bash
# Инициализация Storybook (автодетект Next.js)
pnpm dlx storybook@latest init

# Результат: .storybook/ + stories/
```

### Критическая настройка: Tailwind в Storybook

По умолчанию Storybook **не подхватывает** Tailwind-стили. Необходимо:

```ts
// .storybook/preview.ts
import type { Preview } from '@storybook/react';
import '../src/app/globals.css'; // <-- импорт Tailwind стилей!

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
  },
};

export default preview;
```

### Темная тема в Storybook

```bash
pnpm add -D @storybook/addon-themes
```

```ts
// .storybook/preview.ts
import { withThemeByClassName } from '@storybook/addon-themes';

const preview: Preview = {
  decorators: [
    withThemeByClassName({
      themes: {
        light: '',
        dark: 'dark',
      },
      defaultTheme: 'light',
    }),
  ],
};
```

### Пример Story для shadcn Button

```tsx
// components/ui/button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './button';

const meta: Meta<typeof Button> = {
  title: 'UI/Button',
  component: Button,
  tags: ['autodocs'], // автодокументация из props
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'destructive', 'outline', 'ghost'],
    },
    size: {
      control: 'select',
      options: ['sm', 'md', 'lg', 'icon'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Default: Story = {
  args: {
    children: 'Click me',
    variant: 'default',
    size: 'md',
  },
};

export const Destructive: Story = {
  args: {
    children: 'Delete',
    variant: 'destructive',
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-4">
      <Button variant="default">Default</Button>
      <Button variant="destructive">Destructive</Button>
      <Button variant="outline">Outline</Button>
      <Button variant="ghost">Ghost</Button>
    </div>
  ),
};
```

### Стратегия документации компонентов

```
src/
  components/
    ui/
      button.tsx              # Компонент
      button.stories.tsx      # Stories (визуальная документация)
      button.test.tsx         # Unit/a11y тесты
```

**Правила:**

1. Каждый UI-компонент должен иметь `.stories.tsx`
2. Используйте `tags: ["autodocs"]` -- Storybook автоматически генерирует документацию из TypeScript props
3. Создавайте story для каждого варианта + story "All Variants" для обзора
4. Добавляйте interaction tests в stories для сложных компонентов

---

## 13. Тестирование дизайн-системы

### Visual regression testing

**Chromatic** (от команды Storybook):

```bash
pnpm add -D chromatic

# Запуск visual testing
pnpm dlx chromatic --project-token=<TOKEN>
```

- Делает скриншот каждой story
- Сравнивает с предыдущей версией (pixel-by-pixel)
- CI интеграция: блокирует PR при визуальных изменениях без approve
- Бесплатно: 5000 снимков/месяц

**Альтернатива -- Lost Pixel:**

```bash
pnpm add -D lost-pixel
```

- Open-source, self-hosted
- Интеграция со Storybook, Next.js pages, Ladle
- Хранение baseline в репозитории (нет облачных зависимостей)

| Критерий                 | Chromatic            | Lost Pixel           | Percy            |
| ------------------------ | -------------------- | -------------------- | ---------------- |
| **Цена**                 | Free tier (5K)       | Open-source          | From $399/mo     |
| **Storybook интеграция** | нативная             | да                   | да               |
| **Self-hosted**          | нет                  | да                   | нет              |
| **CI/CD**                | GitHub Actions, etc. | GitHub Actions       | любой CI         |
| **Рекомендация**         | **Enterprise выбор** | Budget / self-hosted | Крупные компании |

### Accessibility testing

**jest-axe -- unit-тесты a11y:**

```bash
pnpm add -D jest-axe @types/jest-axe
```

```tsx
// components/ui/button.test.tsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { Button } from './button';

expect.extend(toHaveNoViolations);

describe('Button accessibility', () => {
  it('should have no a11y violations', async () => {
    const { container } = render(<Button>Click me</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no a11y violations (disabled state)', async () => {
    const { container } = render(<Button disabled>Disabled</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

**@storybook/addon-a11y -- a11y аудит в Storybook:**

```bash
pnpm add -D @storybook/addon-a11y
```

```ts
// .storybook/main.ts
const config: StorybookConfig = {
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-a11y', // <-- панель a11y в каждой story
    '@storybook/addon-themes',
  ],
};
```

Панель a11y показывает violations, passes и incomplete checks по WCAG 2.1 AA/AAA для каждой story.

**Playwright + axe -- e2e a11y:**

```ts
// e2e/a11y.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('dashboard page should have no a11y violations', async ({ page }) => {
  await page.goto('/dashboard');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();

  expect(results.violations).toEqual([]);
});
```

### Стратегия тестирования дизайн-системы

```
+-----------------------------------------------------------------+
| Уровень            | Инструмент           | Что тестируем        |
| ------------------ |
| Unit (a11y)        | jest-axe             | WCAG violations      |
| Visual (snapshot)  | Chromatic            | Pixel-perfect рендер |
| Interaction        | Storybook play()     | Клики, фокус, hover  |
| Integration (a11y) | @axe-core/playwright | Полные страницы      |
| Manual review      | Storybook addon-a11y | Ручная проверка      |
+-----------------------------------------------------------------+
```

---

## 14. Итоговая рекомендация: полный tech stack

```
+-------------------------------------------------------------------+
|                 ПОЛНЫЙ РЕКОМЕНДУЕМЫЙ СТЕК                          |
+-------------------------------------------------------------------+
| СТИЛИЗАЦИЯ    |
| ------------- |
| CSS framework | Tailwind CSS v4 (Oxide engine, @theme)   |
| Компоненты    | shadcn/ui (Radix UI примитивы)           |
| Иконки        | Lucide React                             |
| Темная тема   | next-themes + CSS variables              |
| Анимации      | Motion (Framer Motion) + CSS transitions |
+-------------------------------------------------------------------+
| УТИЛИТЫ       |
| ------------- |
| Class merging | cn() = clsx + tailwind-merge              |
| Варианты      | cva (простые) + tv (сложные со slots)     |
| IDE support   | tailwindCSS.classFunctions: ["cva", "cn"] |
+-------------------------------------------------------------------+
| ШРИФТЫ И МЕДИА   |
| ---------------- |
| Шрифты           | next/font: Inter (UI) + Geist Mono (code) |
| Изображения      | next/image + Sharp (AVIF/WebP)            |
| Blur placeholder | plaiceholder (dynamic) / auto (static)    |
+-------------------------------------------------------------------+
| ДАННЫЕ И LAYOUT |
| --------------- |
| Таблицы         | TanStack Table v8 + shadcn DataTable   |
| Графики         | Tremor (дашборды) / Recharts (custom)  |
| Layout          | CSS Grid (каркас) + Flexbox (элементы) |
| Токены          | @theme CSS variables (Tailwind v4)     |
+-------------------------------------------------------------------+
| ДОКУМЕНТАЦИЯ И ТЕСТИРОВАНИЕ |
| --------------------------- |
| Component docs              | Storybook 8 + autodocs                    |
| Visual regression           | Chromatic (CI) / Lost Pixel (self-hosted) |
| A11y testing                | jest-axe (unit) + addon-a11y (Storybook)  |
| A11y e2e                    | @axe-core/playwright                      |
| Theme testing               | Storybook addon-themes (light/dark)       |
+-------------------------------------------------------------------+
```

### Почему этот стек

1. **Нулевой runtime-оверхед** -- Tailwind v4, shadcn/ui, cva генерируют только CSS
2. **RSC-совместимость** -- все компоненты работают с React Server Components
3. **Полное владение кодом** -- shadcn копирует код в проект, нет vendor lock-in
4. **AAA Accessibility** -- Radix UI + jest-axe + Chromatic visual testing
5. **Шрифты без CLS** -- next/font self-hosting, zero layout shift
6. **Изображения на 60-80% легче** -- next/image + Sharp + AVIF
7. **Документация из кода** -- Storybook autodocs из TypeScript props
8. **Визуальная регрессия** -- каждый PR проверяется Chromatic
9. **Масштабируемость** -- design tokens, мультитемность, slots (tv)
10. **DX** -- один `cn()` для всех классов, cva/tv для вариантов, IDE autocomplete

---

_Источники:_

- _[CVA Documentation](https://cva.style/docs/getting-started/variants)_
- _[tailwind-merge GitHub](https://github.com/dcastil/tailwind-merge)_
- _[tailwind-variants](https://www.tailwind-variants.org/docs/config)_
- _[Next.js Font Optimization](https://nextjs.org/docs/app/getting-started/fonts)_
- _[Next.js Image Component](https://nextjs.org/docs/app/api-reference/components/image)_
- _[Geist Font](https://vercel.com/font)_
- _[Storybook Tailwind Recipe](https://storybook.js.org/recipes/tailwindcss)_
- _[Chromatic Visual Testing](https://www.chromatic.com/)_
- _[axe-core](https://github.com/dequelabs/axe-core)_
- _[Lost Pixel](https://www.lost-pixel.com/)_
