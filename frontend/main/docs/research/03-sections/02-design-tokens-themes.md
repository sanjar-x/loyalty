# Дизайн-токены, темы и адаптивный дизайн

> Расширение секций 3-4 документа `03-ui-design-system.md`
> Исследование: апрель 2026 | Tailwind CSS v4 + Next.js 15+ App Router

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

### 2.1. Почему OKLCH, а не HSL/RGB

Tailwind v4 перевёл всю стандартную палитру на OKLCH. Причины:

| Проблема HSL/RGB                                                                                                | Решение OKLCH                                                                                    |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `hsl(60, 100%, 50%)` и `hsl(240, 100%, 50%)` имеют одинаковый L=50%, но визуально жёлтый намного светлее синего | OKLCH L (Lightness) перцептуально однородный -- одинаковый L = одинаковая воспринимаемая яркость |
| Нельзя программно генерировать шкалу оттенков -- нужна ручная коррекция каждого шага                            | Фиксируем Hue, меняем L линейно от 0.97 до 0.18 -- получаем визуально равномерную шкалу          |
| `saturate()` / `desaturate()` искажают оттенок при изменении насыщенности                                       | Chroma в OKLCH ортогонален к Lightness -- изменение C не сдвигает оттенок                        |
| P3 / wide-gamut цвета невозможны в sRGB hex                                                                     | OKLCH естественно покрывает P3 и Rec. 2020 гаммы                                                 |

### 2.2. Анатомия OKLCH

```
oklch(L  C  H)
      |  |  |
      |  |  +-- Hue (оттенок): 0-360 градусов
      |  +-- Chroma (насыщенность): 0 (серый) ... ~0.4 (максимальная)
      +-- Lightness (яркость): 0 (чёрный) ... 1 (белый)
```

**Ориентиры по Hue:**

- 0-30: красные
- 30-80: оранжевые / жёлтые
- 80-150: зелёные
- 150-250: голубые / синие
- 250-310: фиолетовые
- 310-360: розовые / пурпурные

### 2.3. Генерация палитры: формула для 11 оттенков

Алгоритм генерации шкалы из одного цвета (например, brand blue с Hue=250):

```typescript
// lib/palette.ts
type OklchColor = { l: number; c: number; h: number };

/**
 * Генерирует 11-ступенчатую палитру (50-950) по одному hue.
 * Lightness идёт от 0.97 (50) до 0.18 (950).
 * Chroma параболически нарастает к середине и спадает к краям.
 */
function generatePalette(hue: number, maxChroma: number = 0.18): Record<string, OklchColor> {
  const steps = [
    { name: '50', l: 0.97 },
    { name: '100', l: 0.93 },
    { name: '200', l: 0.86 },
    { name: '300', l: 0.77 },
    { name: '400', l: 0.66 },
    { name: '500', l: 0.55 },
    { name: '600', l: 0.47 },
    { name: '700', l: 0.39 },
    { name: '800', l: 0.31 },
    { name: '900', l: 0.25 },
    { name: '950', l: 0.18 },
  ];

  const palette: Record<string, OklchColor> = {};

  for (const step of steps) {
    // Chroma: параболическая кривая, пик при L=0.55 (500)
    const chromaFactor = 1 - Math.pow((step.l - 0.55) / 0.42, 2);
    const chroma = Math.max(0.01, maxChroma * Math.max(0, chromaFactor));

    palette[step.name] = { l: step.l, c: parseFloat(chroma.toFixed(3)), h: hue };
  }

  return palette;
}

// Использование:
// generatePalette(250)       -> синяя палитра
// generatePalette(25, 0.22)  -> красная палитра с высокой насыщенностью
// generatePalette(145, 0.17) -> зелёная палитра
```

### 2.4. Инструменты для OKLCH

- **oklch.com** (Evil Martians) -- интерактивный пикер с визуализацией гамута
- **Atmos Style** (atmos.style) -- генератор UI-палитр на основе OKLCH
- **Harmonizer** -- автоматическая генерация доступных палитр с проверкой APCA-контраста
- **Figma-плагин OKLCH Palette Generator** -- генерация палитр прямо в Figma

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
