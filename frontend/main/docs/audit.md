● Начну с глубокого аудита текущей реализации. Мне нужно изучить все связанные файлы.

● Explore(Deep audit Telegram SDK architecture)
  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)

● Запустил глубокий анализ архитектуры. Пока агент работает, давай параллельно посмотрю ключевые файлы.

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/core.ts)
  ⎿  Read 123 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/types.ts)
  ⎿  Read 1161 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/index.ts)
  ⎿  Read 104 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/provider.tsx)
  ⎿  Read 444 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/features/auth/index.ts)
  ⎿  Read 2 lines

● Search(pattern: "src/features/auth/**/*.{ts,tsx}")
  ⎿  Found 2 files
     src/features/auth/index.ts
     src/features/auth/components/telegram-auth-bootstrap.tsx

● Search(pattern: "src/features/telegram/hooks/*.ts")
  ⎿  Found 29 files
     src/features/telegram/hooks/useClipboard.ts
     src/features/telegram/hooks/useVerticalSwipes.ts
     src/features/telegram/hooks/useAccelerometer.ts
     src/features/telegram/hooks/useBackButton.ts
     src/features/telegram/hooks/useBiometric.ts
     src/features/telegram/hooks/useClosingConfirmation.ts
     src/features/telegram/hooks/useCloudStorage.ts
     src/features/telegram/hooks/useDeviceOrientation.ts
     src/features/telegram/hooks/useDeviceStorage.ts
     src/features/telegram/hooks/useEmojiStatus.ts
     src/features/telegram/hooks/useFullscreen.ts
     src/features/telegram/hooks/useGyroscope.ts
     src/features/telegram/hooks/useHaptic.ts
     src/features/telegram/hooks/useHomeScreen.ts
     src/features/telegram/hooks/useInvoice.ts
     src/features/telegram/hooks/useLinks.ts
     src/features/telegram/hooks/useLocation.ts
     src/features/telegram/hooks/useMainButton.ts
     src/features/telegram/hooks/usePermissions.ts
     src/features/telegram/hooks/usePlatform.ts
     src/features/telegram/hooks/usePopup.ts
     src/features/telegram/hooks/useQrScanner.ts
     src/features/telegram/hooks/useSecondaryButton.ts
     src/features/telegram/hooks/useSecureStorage.ts
     src/features/telegram/hooks/useSettingsButton.ts
     src/features/telegram/hooks/useShare.ts
     src/features/telegram/hooks/useTelegram.ts
     src/features/telegram/hooks/useTheme.ts
     src/features/telegram/hooks/useViewport.ts

● Search(pattern: "src/features/telegram/components/*.tsx")
  ⎿  Found 2 files
     src/features/telegram/components/telegram-back-button-controller.tsx
     src/features/telegram/components/telegram-environment-alert.tsx

● Search(pattern: "src/components/providers/*.tsx")
  ⎿  Found 4 files
     src/components/providers/toast-provider.tsx
     src/components/providers/theme-provider.tsx
     src/components/providers/query-provider.tsx
     src/components/providers/telegram-provider.tsx

● Read(/home/sanjar/Desktop/miniapp/new/src/features/auth/components/telegram-auth-bootstrap.tsx)
  ⎿  Read 111 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/components/telegram-back-button-controller.tsx)
  ⎿  Read 56 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/components/telegram-environment-alert.tsx)
  ⎿  Read 38 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/components/providers/theme-provider.tsx)
  ⎿  Read 12 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/components/providers/query-provider.tsx)
  ⎿  Read 18 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/components/providers/toast-provider.tsx)
  ⎿  Read 8 lines

● Search(pattern: "src/app/**/layout.tsx")
  ⎿  Found 1 file
     src/app/layout.tsx

● Search(pattern: "src/lib/auth/**/*.{ts,tsx}")
  ⎿  Found 4 files
     src/lib/auth/cookie-helpers.ts
     src/lib/auth/cookies.ts
     src/lib/auth/debug.ts
     src/lib/auth/events.ts

● Search(pattern: "src/stores/auth-store.{ts,tsx}")
  ⎿  Found 1 file
     src/stores/auth-store.ts

● Search(pattern: "src/types/auth.{ts,tsx}")
  ⎿  Found 1 file
     src/types/auth.ts

● Read(/home/sanjar/Desktop/miniapp/new/src/app/layout.tsx)
  ⎿  Read 71 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/stores/auth-store.ts)
  ⎿  Read 50 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/types/auth.ts)
  ⎿  Read 31 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/lib/auth/debug.ts)
  ⎿  Read 83 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/lib/auth/events.ts)
  ⎿  Read 20 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/lib/auth/cookies.ts)
  ⎿  Read 22 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/lib/auth/cookie-helpers.ts)
  ⎿  Read 118 lines

● Теперь посмотрю ключевые хуки и API route для auth.

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/hooks/useTelegram.ts)
  ⎿  Read 20 lines

● Search(pattern: "src/app/api/auth/**/*.{ts,tsx}")
  ⎿  Found 3 files
     src/app/api/auth/logout/route.ts
     src/app/api/auth/refresh/route.ts
     src/app/api/auth/telegram/route.ts

● Search(pattern: "src/components/providers/index.{ts,tsx}")
  ⎿  Found 0 files

● Read(/home/sanjar/Desktop/miniapp/new/src/app/api/auth/telegram/route.ts)
  ⎿  Read 155 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/app/api/auth/refresh/route.ts)
  ⎿  Read 74 lines

● Read(/home/sanjar/Desktop/miniapp/new/src/app/api/auth/logout/route.ts)
  ⎿  Read 38 lines

● Теперь у меня полная картина. Давайте посмотрю ещё на декларацию типов и middleware.

● Search(pattern: "__LM_HOME_BACK__")
  ⎿  Found 2 files
     src/features/telegram/components/telegram-back-button-controller.tsx
     src/features/telegram/globals.d.ts

● Search(pattern: "src/middleware.{ts,tsx}")
  ⎿  Found 0 files

● Search(pattern: "src/features/*/index.ts")
  ⎿  Found 3 files
     src/features/product/index.ts
     src/features/auth/index.ts
     src/features/telegram/index.ts

● Read(/home/sanjar/Desktop/miniapp/new/src/features/telegram/globals.d.ts)
  ⎿  Read 11 lines

● Search(pattern: "src/middleware.ts", path: "/home/sanjar/Desktop/miniapp/new")
  ⎿  Found 0 files

● Search(pattern: "middleware.ts", path: "/home/sanjar/Desktop/miniapp/new")
  ⎿  Found 0 files

● Теперь у меня полная картина всей архитектуры. Вот результаты Deep Audit:

  ---
  Deep Audit: Telegram SDK + Auth Architecture

  Обзор текущей структуры

  src/features/telegram/      — SDK, provider, 29 hooks, 2 компонента
  src/features/auth/           — только TelegramAuthBootstrap
  src/components/providers/    — TelegramProvider (оркестрация)
  src/lib/auth/                — debug, events, cookies, cookie-helpers
  src/stores/auth-store.ts     — Zustand store
  src/types/auth.ts            — типы
  src/app/api/auth/            — BFF routes (telegram, refresh, logout)

  ---
  КРИТИЧЕСКИЕ проблемы

  1. Дублирование Window.Telegram declaration
  - globals.d.ts:7 — Telegram?: { WebApp?: WebApp } (WebApp optional)
  - types.ts:1156 — Telegram?: { WebApp: WebApp } (WebApp required)
  - Конфликт типов, может ломать type inference

  2. TelegramBackButtonController обходит контекст провайдера
  - Вызывает getWebApp() напрямую вместо useTelegramContext()
  - Не ждёт isReady — может обратиться к SDK до инициализации
  - Нарушает контракт: SDK провайдер гарантирует lifecycle, а этот компонент его игнорирует

  3. TelegramAuthBootstrap — default export при named exports везде
  - Единственный default export во всём проекте, нарушает единообразие

  ---
  АРХИТЕКТУРНЫЕ проблемы

  4. features/auth/ — «размазанный» модуль
  - Компонент в features/auth/components/
  - Store в stores/auth-store.ts
  - Типы в types/auth.ts
  - Утилиты в lib/auth/ (4 файла)
  - Feature Sliced Design нарушен — auth раскидан по 4 директориям

  5. TelegramProvider — не провайдер, а Shell
  - Не создаёт никакого контекста, просто компонует TelegramSdkProvider + AuthBootstrap + BackButtonController + EnvironmentAlert
  - Название Provider вводит в заблуждение — это bootstrap/shell

  6. provider.tsx перегружен (~440 строк)
  - SDK инициализация + polling
  - CSS-переменные (theme, viewport, safe area, meta) — 4 разных домена
  - WebApp event subscriptions
  - Debug fallback
  - Применение цветов темы

  ---
  NAMING проблемы

  ┌───────────────────────────────────┬────────────────┬──────────────────────────────────────┐
  │              Текущее              │    Проблема    │             Рекомендация             │
  ├───────────────────────────────────┼────────────────┼──────────────────────────────────────┤
  │ TelegramProvider (components/)    │ Не провайдер   │ TelegramAppShell                     │
  ├───────────────────────────────────┼────────────────┼──────────────────────────────────────┤
  │ TelegramSdkProvider               │ ОК             │ ✅                                   │
  ├───────────────────────────────────┼────────────────┼──────────────────────────────────────┤
  │ useTelegram vs useTelegramContext │ Неясна разница │ useTelegram = фасад, документировать │
  ├───────────────────────────────────┼────────────────┼──────────────────────────────────────┤
  │ telegram-auth-bootstrap.tsx       │ default export │ Named export                         │
  └───────────────────────────────────┴────────────────┴──────────────────────────────────────┘

  ---
  Что работает ХОРОШО

  - Auth flow: initData → BFF → backend → httpOnly cookies — безопасно
  - Polling SDK с таймаутом + debug fallback — надёжно
  - CSS-переменные синхронизированы с Telegram темой
  - Auth store state machine (idle → loading → authenticated/error/expired)
  - BFF routes корректно обрабатывают ошибки и чистят cookies

  ---
  Хочешь, чтобы я перешёл к исправлениям? Основные направления:

  1. Fix types conflict — убрать дублирование Window.Telegram
  2. Fix BackButtonController — использовать контекст вместо прямого вызова
  3. Fix naming — TelegramProvider → TelegramAppShell, default → named export
  4. Консолидировать auth — собрать все auth-части в features/auth/
  5. Разгрузить provider.tsx — вынести CSS-логику в отдельные утилиты

  Или хочешь, чтобы я сфокусировался на определённых пунктах?

✻ Cooked for 4m 27s · 1 local agent still running

● Agent "Deep audit Telegram SDK architecture" completed

● Фоновый агент завершил полный анализ и подтвердил все найденные проблемы. Он также обнаружил дополнительный контекст:

  - src/proxy.ts — edge middleware с CSRF-защитой (Origin validation) и security headers
  - src/lib/api-client.ts — клиент с mutex-pattern для 401 refresh (предотвращает thundering herd)
  - BFF proxy src/app/api/backend/[...path]/route.ts — прозрачно прокидывает Bearer токены из httpOnly cookies

  Эти части реализованы корректно. Основные проблемы — те, что я описал выше. Жду твоего решения по направлениям исправлений.


• Findings

  1. High. src/lib/api-client.ts:3 imports emitAuthExpired from src/features/auth/lib/events.ts, which breaks your own layer contract in eslint.config.mjs:153. pnpm lint already fails on
     this. lib/ is infrastructure; if auth/session expiry is cross-cutting, that event bus belongs in src/lib/ or in an app/auth orchestration layer, not inside a feature.
  2. High. The codebase currently violates the stated FSD rule “features do NOT import from other features” from docs/SPEC.md:162, and the lint config does not actually enforce slice
     isolation. Concrete examples: src/features/telegram/provider-runtime.ts:3, src/features/telegram/components/telegram-environment-alert.tsx:5, src/features/home/components/product-
     grid.tsx:8, and src/features/home/components/category-tabs.tsx:5. The current rule set in eslint.config.mjs:83 only separates top-level layers, so “feature modules” are not real
     isolation boundaries yet.
  3. Medium. The architecture enforcement itself is already on a deprecated API. eslint.config.mjs:99 still uses boundaries/element-types with legacy selectors, and pnpm lint warns about
     both on every run. That means the one mechanism meant to preserve your architecture is already drifting under the tooling.
  4. Medium. The implementation no longer matches the documented “No barrel files” decision in docs/SPEC.md:87. Internal barrels are active in src/features/telegram/index.ts:1, src/features/
     auth/index.ts:1, and src/types/index.ts:1, and they are consumed from src/app/_providers/telegram-app-shell.tsx:5 and src/app/profile/page.tsx:5. Either barrels are now an accepted
     public-API pattern and the SPEC is wrong, or the code is drifting away from the chosen architecture.
  5. Medium. There is effectively no automated regression safety net for the architecture-critical runtime you just consolidated. The only real project test is the scaffold at e2e/
     example.spec.ts:1; there are no project tests covering src/features/telegram/provider-runtime.ts:34, src/features/auth/components/telegram-auth-bootstrap.tsx:38, src/lib/api-
     client.ts:23, or src/app/api/backend/[...path]/route.ts:31. For a Next.js BFF with auth refresh and Telegram bootstrap, that leaves refactors largely unguarded.

  Open Questions

  - I assumed docs/SPEC.md is the architectural contract for review, not an aspirational document. If it is only aspirational, findings 2 and 4 downgrade from violations to unresolved
    direction.
  - You need to choose one model: strict FSD slice isolation, or pragmatic layered modules with cross-feature imports and public barrels. Right now the repo mixes both.
  - The app-level composition convention is mid-migration: src/app/_providers, src/components/providers, and an empty src/app/providers all coexist.

  Verification
  pnpm typecheck passed. pnpm lint failed; the architecture-relevant failure is the lib -> features import above, and there are also unrelated existing lint issues in img-with-fallback and
  use-cart. No code changes were made in this review pass.