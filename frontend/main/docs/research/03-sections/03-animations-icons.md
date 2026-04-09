# 5. Анимации и 6. Иконки -- Расширенное исследование

> Расширение секций 5-6 из `03-ui-design-system.md` | Апрель 2026
> Фокус: enterprise Next.js 15+ App Router, production-паттерны

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
