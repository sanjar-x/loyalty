# 05. Утилиты, шрифты, изображения и документация компонентов

> Расширение секции 9 основного документа `03-ui-design-system.md`
> Исследование: апрель 2026 | Фокус: enterprise Next.js 15+ App Router

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

### Сравнение cva vs tailwind-variants

| Критерий                   | cva                  | tailwind-variants (tv) |
| -------------------------- | -------------------- | ---------------------- |
| **npm скачивания/нед.**    | ~4.5M                | ~1.2M                  |
| **Bundle size**            | ~1.5KB gzipped       | ~3.5KB gzipped         |
| **Compound variants**      | да                   | да                     |
| **Responsive variants**    | нет                  | да                     |
| **Slots**                  | нет                  | да                     |
| **Composability (extend)** | нет (вручную)        | встроенная (`extend`)  |
| **twMerge встроен**        | нет (нужен отдельно) | да (встроен)           |
| **TypeScript**             | полная               | полная                 |
| **Framework agnostic**     | да                   | да                     |

### tailwind-variants: responsive variants

```ts
import { tv } from "tailwind-variants";

const button = tv({
  base: "inline-flex items-center justify-center rounded-md font-medium transition-colors",
  variants: {
    size: {
      sm: "h-8 px-3 text-xs",
      md: "h-10 px-4 text-sm",
      lg: "h-12 px-6 text-base",
    },
    color: {
      primary: "bg-primary text-primary-foreground hover:bg-primary/90",
      secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/90",
    },
  },
  defaultVariants: { size: "md", color: "primary" },
});

// Responsive: sm на mobile, lg на desktop
<button className={button({ size: { initial: "sm", md: "lg" }, color: "primary" })} />
```

### tailwind-variants: Slots

Slots решают проблему стилизации вложенных элементов:

```ts
const card = tv({
  slots: {
    base: "rounded-lg border bg-card shadow-sm",
    header: "flex flex-col space-y-1.5 p-6",
    title: "text-2xl font-semibold leading-none tracking-tight",
    description: "text-sm text-muted-foreground",
    content: "p-6 pt-0",
    footer: "flex items-center p-6 pt-0",
  },
  variants: {
    variant: {
      elevated: {
        base: "shadow-lg",
        header: "border-b",
      },
      flat: {
        base: "shadow-none border-0 bg-muted/50",
      },
    },
  },
  defaultVariants: { variant: "elevated" },
});

// Использование
const { base, header, title, content } = card({ variant: "elevated" });

<div className={base()}>
  <div className={header()}>
    <h3 className={title()}>Card Title</h3>
  </div>
  <div className={content()}>Content</div>
</div>
```

### tailwind-variants: extend (наследование)

```ts
const baseButton = tv({
  base: 'inline-flex items-center justify-center rounded-md font-medium',
  variants: {
    size: {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
    },
  },
});

// IconButton наследует baseButton и расширяет
const iconButton = tv({
  extend: baseButton,
  base: 'gap-2', // добавляет к базовым классам
  variants: {
    size: {
      sm: 'px-2', // переопределяет padding
      md: 'px-3',
    },
  },
});
```

### Рекомендация

| Проект                         | Рекомендация                                             |
| ------------------------------ | -------------------------------------------------------- |
| shadcn/ui стандартный          | **cva** -- используется по умолчанию, минимальный bundle |
| Сложная дизайн-система с slots | **tailwind-variants** -- slots, responsive, extend       |
| Максимальная гибкость          | **tailwind-variants** -- больше возможностей при +2KB    |

Для нашего проекта: **cva** как основной (совместимость с shadcn/ui), но tv может быть добавлен для сложных составных компонентов, требующих slots.

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
