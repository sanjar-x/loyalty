# Git Hooks и стек тестирования для Next.js 15+ (Deep Research)

> Husky v9 + lint-staged + commitlint, Vitest, Playwright, MSW v2,
> паттерны тестирования RSC и Server Actions.
>
> Дата: 2026-04-05 | Контекст: enterprise Next.js 15 App Router

---

## 1. Git Hooks — Husky v9 + lint-staged + commitlint

### 1.1 Установка и инициализация

```bash
pnpm add -D husky lint-staged @commitlint/cli @commitlint/config-conventional
pnpm exec husky init  # создаёт .husky/ и prepare-скрипт
```

### 1.2 Конфигурация хуков

```bash
# .husky/pre-commit
pnpm exec lint-staged
```

```bash
# .husky/commit-msg
pnpm exec commitlint --edit "$1"
```

```bash
# .husky/pre-push
pnpm run typecheck
```

### 1.3 lint-staged — линтинг только staged-файлов

Критически важно для больших проектов: линтинг всего проекта — минуты, staged-файлов — секунды.

```jsonc
// package.json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix --max-warnings=0", "prettier --write"],
    "*.{json,md,yml,yaml}": ["prettier --write"],
    "*.css": ["prettier --write"],
  },
}
```

- `--max-warnings=0` — блокирует коммит с любыми warning'ами
- Порядок: сначала eslint (может менять код), потом prettier (финальное форматирование)
- **nano-staged** — альтернатива размером 47 КБ vs 6.7 МБ, идентичный API

### 1.4 commitlint — валидация коммит-сообщений

```javascript
// commitlint.config.js
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'ci', 'perf', 'style'],
    ],
    'subject-max-length': [2, 'always', 72],
    'subject-full-stop': [2, 'never', '.'],
    'type-case': [2, 'always', 'lower-case'],
    'body-leading-blank': [1, 'always'],
  },
};
```

---

## 2. Vitest — unit/integration тестирование

### 2.1 Vitest vs Jest — бенчмарки 2025-2026

| Метрика            | Vitest               | Jest              | Разница        |
| ------------------ | -------------------- | ----------------- | -------------- |
| Холодный запуск    | ~1.2 сек             | ~4.8 сек          | 4x быстрее     |
| Watch-режим (HMR)  | ~50 мс               | ~2-3 сек          | 40-60x быстрее |
| RAM (50K LOC)      | ~800 МБ              | ~1.2 ГБ           | на 30% меньше  |
| ESM                | Нативная             | Экспериментальная | стабильна      |
| TypeScript         | Из коробки (ESBuild) | ts-jest/babel     | zero-config    |
| npm downloads/нед. | ~3.8 млн             | ~35 млн           | Jest зрелее    |

**Вывод**: Vitest — стандарт для новых Next.js 15+ проектов. Jest — только legacy/React Native.

### 2.2 vitest.config.ts

```typescript
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['src/**/*.e2e.{test,spec}.{ts,tsx}', 'e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.d.ts', 'src/**/*.test.*', 'src/**/index.ts', 'src/**/*.stories.*'],
      thresholds: { branches: 80, functions: 80, lines: 80, statements: 80 },
    },
    reporters: ['verbose'],
    testTimeout: 10_000,
  },
});
```

### 2.3 vitest.setup.ts

```typescript
import '@testing-library/jest-dom/vitest';
import { server } from '@/mocks/server';

// Мок Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(), replace: vi.fn(), back: vi.fn(),
    prefetch: vi.fn(), refresh: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// Мок next/image
vi.mock('next/image', () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} />,
}));

// MSW lifecycle
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 2.4 Стратегия тестирования RSC

Vitest/RTL **не поддерживают async Server Components** — RSC рендерятся на сервере
и возвращают сериализованный payload, а не React-дерево.

```
Async Server Components → E2E тесты (Playwright)
Sync Server Components  → Unit тесты (Vitest + RTL)
Client Components       → Unit тесты (Vitest + RTL)
Server Actions          → Unit тесты (мок зависимостей)
```

### 2.5 Тестирование Server Actions

`'use server'` игнорируется Vitest — функция выполняется как обычная async-функция:

```typescript
// src/actions/create-user.test.ts
vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }));
vi.mock('@/lib/db', () => ({
  db: { user: { create: vi.fn().mockResolvedValue({ id: '1' }) } },
}));

import { createUser } from './create-user';

describe('createUser', () => {
  it('creates user with valid data', async () => {
    const formData = new FormData();
    formData.set('name', 'John Doe');
    formData.set('email', 'john@test.com');
    const result = await createUser(formData);
    expect(result).toEqual({ success: true });
  });

  it('returns validation errors for invalid data', async () => {
    const formData = new FormData();
    formData.set('name', '');
    formData.set('email', 'not-an-email');
    const result = await createUser(formData);
    expect(result).toHaveProperty('error');
  });
});
```

---

## 3. Playwright — E2E тестирование

### 3.1 playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ...(process.env.CI ? [['github' as const]] : []),
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
  // Production build (НЕ dev — нестабилен для E2E)
  webServer: {
    command: 'pnpm build && pnpm start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
```

### 3.2 Auth Setup — переиспользование аутентификации

Аутентификация выполняется один раз, state переиспользуется всеми браузерами:

```typescript
// e2e/auth.setup.ts
import { expect, test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL('/dashboard');
  await page.context().storageState({ path: 'e2e/.auth/user.json' });
});
```

### 3.3 Page Object Model (POM)

```typescript
// e2e/pages/dashboard.page.ts
import type { Locator, Page } from '@playwright/test';

export class DashboardPage {
  readonly heading: Locator;
  readonly searchInput: Locator;

  constructor(private page: Page) {
    this.heading = page.getByRole('heading', { name: 'Dashboard' });
    this.searchInput = page.getByPlaceholder('Search...');
  }

  async goto() {
    await this.page.goto('/dashboard');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    await this.searchInput.press('Enter');
  }
}
```

### 3.4 Тестирование async RSC через Playwright

```typescript
// e2e/users.spec.ts
test('renders server-fetched user list', async ({ page }) => {
  await page.goto('/users');
  // RSC отрендерил данные на сервере — Playwright видит готовый HTML
  await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible();
  await expect(page.getByTestId('user-card')).toHaveCount(10);
});
```

---

## 4. MSW v2 — мокирование API

### 4.1 Архитектура в Next.js App Router

MSW перехватывает запросы на сетевом уровне. Два контекста:

- **Server** (Node.js): `setupServer` из `msw/node` — для Vitest и SSR
- **Browser**: `setupWorker` из `msw/browser` — для development через Service Worker

В Next.js 15 MSW корректно перехватывает серверные запросы (в RSC/Route Handlers).
В Next.js 14 это не работало.

### 4.2 Структура и handlers

```
src/mocks/
├── handlers/
│   ├── users.ts      # Handlers для /api/users
│   ├── auth.ts       # Handlers для /api/auth
│   └── index.ts      # Re-export всех handlers
├── browser.ts        # setupWorker
├── server.ts         # setupServer
└── index.ts          # Условная инициализация
```

```typescript
// src/mocks/handlers/users.ts
import { http, HttpResponse } from 'msw';

export const usersHandlers = [
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: '1', name: 'Alice', email: 'alice@example.com' },
      { id: '2', name: 'Bob', email: 'bob@example.com' },
    ]);
  }),
  http.post('/api/users', async ({ request }) => {
    const body = (await request.json()) as { name: string; email: string };
    return HttpResponse.json({ id: '3', ...body }, { status: 201 });
  }),
];
```

```typescript
// src/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';
export const server = setupServer(...handlers);
```

```typescript
// src/mocks/browser.ts
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';
export const worker = setupWorker(...handlers);
```

### 4.3 Условная инициализация в layout

```typescript
// src/mocks/index.ts
export async function initMocks() {
  if (typeof window === 'undefined') {
    const { server } = await import('./server');
    server.listen({ onUnhandledRequest: 'bypass' });
  } else {
    const { worker } = await import('./browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }
}
```

```typescript
// src/app/layout.tsx — вызов на верхнем уровне
async function enableMocking() {
  if (process.env.NEXT_PUBLIC_API_MOCKING !== 'enabled') return;
  const { initMocks } = await import('@/mocks');
  await initMocks();
}
enableMocking();
```

### 4.4 Переопределение handlers в тестах

```typescript
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';

it('shows error state on API failure', async () => {
  server.use(
    http.get('/api/users', () => HttpResponse.json({ error: 'Server Error' }, { status: 500 })),
  );
  render(<UserList />);
  await waitFor(() => expect(screen.getByText(/error/i)).toBeInTheDocument());
});
```

---

## 5. Стратегия тестирования — пирамида

### 5.1 Что чем тестировать

| Слой              | Инструмент            | Примеры                                       |
| ----------------- | --------------------- | --------------------------------------------- |
| Утилиты, helpers  | Vitest                | `formatDate()`, `cn()`, `parseSearchParams()` |
| Zod-схемы         | Vitest                | Валидация форм, env-переменных                |
| Server Actions    | Vitest + мок DB       | `createUser()`, `updateProfile()`             |
| Custom hooks      | Vitest + `renderHook` | `useDebounce()`, `useMediaQuery()`            |
| Client Components | Vitest + RTL          | Формы, кнопки, модалки                        |
| Sync RSC          | Vitest + RTL          | Presentational-компоненты без async           |
| Async RSC         | Playwright            | Страницы с серверным fetch                    |
| User flows        | Playwright            | Регистрация, оплата, CRUD                     |

### 5.2 Установка всего стека

```bash
# Git hooks
pnpm add -D husky lint-staged @commitlint/cli @commitlint/config-conventional

# Unit/Integration
pnpm add -D vitest @vitejs/plugin-react vite-tsconfig-paths \
  @testing-library/react @testing-library/dom @testing-library/jest-dom \
  @testing-library/user-event jsdom msw

# E2E
pnpm add -D @playwright/test

# Init
pnpm exec husky init && pnpm exec playwright install
```

### 5.3 Чеклист готовности

- [ ] `vitest.config.ts` с coverage thresholds 80%
- [ ] `vitest.setup.ts` подключает jest-dom + MSW server
- [ ] `playwright.config.ts` с auth setup и webServer
- [ ] `.husky/pre-commit` запускает lint-staged
- [ ] `.husky/commit-msg` запускает commitlint
- [ ] MSW handlers покрывают API-эндпоинты
- [ ] `.gitignore` содержит `e2e/.auth/`, `test-results/`, `playwright-report/`

---

## Источники

- [Next.js Official: Testing with Vitest](https://nextjs.org/docs/app/guides/testing/vitest)
- [Setting up Vitest for Next.js 15](https://www.wisp.blog/blog/setting-up-vitest-for-nextjs-15)
- [Testing RSC with RTL and Vitest](https://aurorascharff.no/posts/running-tests-with-rtl-and-vitest-on-internationalized-react-server-components-in-nextjs-app-router/)
- [Next.js Playwright E2E Guide](https://eastondev.com/blog/en/posts/dev/20260107-nextjs-playwright-e2e/)
- [Playwright + Next.js Best Practices](https://jsmastery.com/blogs/test-next-js-apps-with-playwright-5-best-practices)
- [Setting up MSW in Next.js App Router](https://gimbap.dev/blog/setting-msw-in-next)
- [MSW + Next.js 15 Setup](https://blog.stackademic.com/setting-up-msw-and-urql-with-next-js-15-cbfd374e916a)
- [Next.js 16 x MSW Integration](https://github.com/laststance/next-msw-integration)
- [Husky + lint-staged Setup 2025](https://dev.to/_d7eb1c1703182e3ce1782/git-hooks-with-husky-and-lint-staged-the-complete-setup-guide-for-2025-53ji)
- [Commitlint Local Setup](https://commitlint.js.org/guides/local-setup.html)
- [Jest vs Vitest 2025](https://medium.com/@ruverd/jest-vs-vitest-which-test-runner-should-you-use-in-2025-5c85e4f2bda9)
- [Vitest vs Jest Benchmarks](https://dev.to/thejaredwilcurt/vitest-vs-jest-benchmarks-on-a-5-year-old-real-work-spa-4mf1)
