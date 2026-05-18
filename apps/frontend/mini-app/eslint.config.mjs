/**
 * FSD ESLint config — активирован Phase 10. Скопировано/адаптировано из
 * apps/frontend/admin/eslint.config.mjs:
 *  - Удалены `@tanstack/query` правила (mini-app использует RTK Query, не TanStack)
 *  - Списки FEATURES / ENTITIES — актуальные slices из src/features/ и src/entities/
 *  - `@next/next/no-img-element: off` — mini-app широко использует `<img>` для
 *    remote/blob (Telegram Mini App конструкция, `next/image` overhead не окупается)
 *  - `react-hooks/refs: warn` — есть god-component, бэклог фоллоу-ап (Phase 9 TODO)
 */

import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';

// ──────────────────────────────────────────────────────────────────────────
// Slice-реестр. Заполняется по мере добавления новых slice'ов.
// ──────────────────────────────────────────────────────────────────────────

const FEATURES = [
  'add-to-cart',
  'auth-telegram',
  'checkout-flow',
  'favorites',
  'home-feed',
  'pickup-selection',
  'recipient-form',
  'search',
  'telegram-api',
];

const ENTITIES = [
  'brand',
  'cart',
  'category',
  'favorite',
  'order',
  'pickup-point',
  'product',
  'promocode',
  'review',
];

// ──────────────────────────────────────────────────────────────────────────

const deepEntityImport = (slice) => ({
  group: [`@/entities/${slice}/*`],
  message: `Import \`@/entities/${slice}\` (its public index.js) instead of reaching into its internal files.`,
});

const deepFeatureImport = (slice) => ({
  group: [`@/features/${slice}/*`],
  message: `Import \`@/features/${slice}\` (its public index.js) instead of reaching into its internal files.`,
});

const featureBoundaryOverrides = FEATURES.map((self) => ({
  files: [`src/features/${self}/**/*.{js,jsx,ts,tsx}`],
  rules: {
    'no-restricted-imports': [
      'warn',
      {
        paths: [
          {
            name: `@/features/${self}`,
            message:
              "Don't import your own slice's barrel from inside it — use relative paths (creates an index.js cycle).",
          },
        ],
        patterns: [
          ...FEATURES.filter((other) => other !== self).map((other) => ({
            group: [`@/features/${other}`, `@/features/${other}/*`],
            message:
              'Cross-feature imports are forbidden. Lift shared code to src/entities/* or src/shared/*.',
          })),
          ...ENTITIES.map(deepEntityImport),
          // Sprint 7: features не должны зависеть от app/ (RTKQ hooks barrel
          // в app/providers/store — известная архитектурная дырка, отдельный
          // рефакторинг разнесёт хуки по entities/api).
          {
            group: ['@/app/*'],
            message:
              'features/* must not depend on app/*. RTKQ hooks must move to entities/*/api/hooks.js (Sprint 3d backlog).',
          },
        ],
      },
    ],
  },
}));

const entityBoundaryOverrides = ENTITIES.map((self) => ({
  files: [`src/entities/${self}/**/*.{js,jsx,ts,tsx}`],
  rules: {
    'no-restricted-imports': [
      'warn',
      {
        paths: [
          {
            name: `@/entities/${self}`,
            message: "Don't import your own slice's barrel from inside it — use relative paths.",
          },
        ],
        patterns: [
          ...FEATURES.map(deepFeatureImport),
          ...ENTITIES.filter((other) => other !== self).map(deepEntityImport),
          {
            group: ['@/features/*', '@/widgets/*', '@/app/*'],
            message: 'entities/* may import only from entities/* (via public API) and shared/*.',
          },
        ],
      },
    ],
  },
}));

const sharedBoundaryOverrides = [
  {
    files: ['src/shared/**/*.{js,jsx,ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'warn',
        {
          patterns: [
            {
              group: ['@/features/*', '@/entities/*', '@/widgets/*', '@/app/*'],
              message:
                'shared/* may import only from shared/*. Move upward dependencies to the consumer layer.',
            },
          ],
        },
      ],
    },
  },
];

const widgetBoundaryOverrides = [
  {
    files: ['src/widgets/**/*.{js,jsx,ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'warn',
        {
          patterns: [
            {
              group: ['@/app/*'],
              message: 'Widgets must not depend on app/*.',
            },
            ...FEATURES.map(deepFeatureImport),
            ...ENTITIES.map(deepEntityImport),
          ],
        },
      ],
    },
  },
];

const appBoundaryOverrides = [
  {
    files: ['src/app/**/*.{js,jsx,ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'warn',
        {
          patterns: [...FEATURES.map(deepFeatureImport), ...ENTITIES.map(deepEntityImport)],
        },
      ],
    },
  },
];

// ──────────────────────────────────────────────────────────────────────────

const eslintConfig = defineConfig([
  ...nextVitals,

  {
    files: ['**/*.{js,jsx,mjs,ts,tsx,mts,cts}'],
    rules: {
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/todo': 'off',
      'react-hooks/memo-dependencies': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/invariant': 'off',
      'react-hooks/immutability': 'off',
      'react-hooks/refs': 'warn',
      '@next/next/no-img-element': 'off',
    },
  },

  // Sprint 1.5 — запрет прямого `clsx`, требуем @/shared/lib/ui-utils#cn
  // (единый стиль; cn-wrapper позволяет добавить дополнительные правила
  // объединения классов в одном месте). Исключение — сам cn.js.
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    ignores: ['src/shared/lib/ui-utils/**'],
    rules: {
      'no-restricted-imports': [
        'warn',
        {
          paths: [
            {
              name: 'clsx',
              message: "Use `import { cn } from '@/shared/lib/ui-utils'` instead of clsx directly.",
            },
          ],
        },
      ],
    },
  },

  ...sharedBoundaryOverrides,
  ...entityBoundaryOverrides,
  ...featureBoundaryOverrides,
  ...widgetBoundaryOverrides,
  ...appBoundaryOverrides,

  // Sprint 3d: api/hooks.js — единственное допустимое место для импорта
  // enhancedApi/customApi/api из @/app/providers/store/instance. RTKQ
  // instance пока живёт в app/ (assembly endpoints), пока этого требует
  // FSD: shared не может ссылаться на entities (откуда endpoints). После
  // SDI seam с registerSheetSlot можно переместить instance в shared.
  {
    files: ['src/entities/*/api/hooks.js', 'src/features/*/api/hooks.js'],
    rules: {
      'no-restricted-imports': 'off',
    },
  },

  globalIgnores(['.next/**', 'out/**', 'build/**', 'eslint.config.legacy.mjs']),
]);

export default eslintConfig;
