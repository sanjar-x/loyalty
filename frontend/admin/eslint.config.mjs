import nextPlugin from '@next/eslint-plugin-next';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import tanstackQueryPlugin from '@tanstack/eslint-plugin-query';

// Feature-Sliced Design layers (top → bottom). A higher layer may import
// only from layers below; siblings inside the same layer are forbidden
// (cross-feature, cross-entity).
//
//   app → widgets, features, entities, shared
//   widgets → features, entities, shared
//   features → entities, shared
//   entities → shared
//   shared → shared
//
// Inside a slice the structure is:
//   <slice>/{ui,model,api,lib,config}/...
//   <slice>/index.js  ← public API (barrel)
//
// Other slices import only the slice's index.js — never reach inside.

const FEATURES = [
  'auth',
  'order-filter',
  'pricing',
  'product-archive',
  'product-filter',
  'product-form',
  'product-status-change',
];

const ENTITIES = [
  'brand',
  'category',
  'order',
  'product',
  'promocode',
  'referral',
  'review',
  'role',
  'staff',
  'supplier',
  'user',
];

// Public-API rule for a slice: outside code may import the slice
// only through its index.js, not via deep paths into ui/, model/, etc.
const deepEntityImport = (slice) => ({
  group: [`@/entities/${slice}/*`],
  message: `Import \`@/entities/${slice}\` (its public index.js) instead of reaching into its internal files.`,
});

const deepFeatureImport = (slice) => ({
  group: [`@/features/${slice}/*`],
  message: `Import \`@/features/${slice}\` (its public index.js) instead of reaching into its internal files.`,
});

// Feature: may import shared, entities (via public API), widgets, and its own internals.
// Forbidden: cross-feature imports, deep imports into other entities.
const featureBoundaryOverrides = FEATURES.map((self) => ({
  files: [`src/features/${self}/**/*.{js,jsx}`],
  rules: {
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          // No cross-feature imports at all.
          ...FEATURES.filter((other) => other !== self).map((other) => ({
            group: [`@/features/${other}`, `@/features/${other}/*`],
            message:
              'Cross-feature imports are forbidden. Lift shared code to src/entities/* or src/shared/*.',
          })),
          // Other entities — only via public API, never deep paths.
          ...ENTITIES.map(deepEntityImport),
        ],
      },
    ],
  },
}));

// Entity: may import shared and other entities (via public API).
// Forbidden: features, widgets, app, deep paths into sibling entities.
const entityBoundaryOverrides = ENTITIES.map((self) => ({
  files: [`src/entities/${self}/**/*.{js,jsx}`],
  rules: {
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          {
            group: ['@/features/*', '@/widgets/*', '@/app/*'],
            message:
              'Entities cannot depend on features, widgets, or app. Use only shared/* and other entities/* (via public API).',
          },
          ...ENTITIES.filter((other) => other !== self).map(deepEntityImport),
        ],
      },
    ],
  },
}));

// Shared: bottom layer. May import only from shared.
const sharedBoundaryOverrides = [
  {
    files: ['src/shared/**/*.{js,jsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
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

// Widget: may import features, entities, shared (all via public API).
// Forbidden: app, deep imports into features or entities.
const widgetBoundaryOverrides = [
  {
    files: ['src/widgets/**/*.{js,jsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
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

// App: top layer. May import everything via public APIs only.
// Allow deep paths inside the same route folder (e.g. ./page.module.css),
// but ban deep paths into features/entities slices.
const appBoundaryOverrides = [
  {
    files: ['src/app/**/*.{js,jsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            ...FEATURES.map(deepFeatureImport),
            ...ENTITIES.filter((s) => s !== 'category').map(deepEntityImport),
            // category has a separate server.js entry, so the deep ban needs
            // to allow `@/entities/category/server`.
            {
              group: ['@/entities/category/api/*', '@/entities/category/ui/*'],
              message:
                'Import `@/entities/category` (or `@/entities/category/server` for server-only code) instead of deep paths.',
            },
          ],
        },
      ],
    },
  },
];

export default [
  {
    ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts'],
  },
  {
    files: ['**/*.{js,jsx,mjs,cjs}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
  },
  nextPlugin.configs['core-web-vitals'],
  {
    plugins: {
      'react-hooks': reactHooksPlugin,
      '@tanstack/query': tanstackQueryPlugin,
    },
    rules: {
      ...Object.fromEntries(
        Object.keys(reactHooksPlugin.rules).map((rule) => [
          `react-hooks/${rule}`,
          'warn',
        ]),
      ),
      // TanStack Query — enforce hygiene for queryKeys / queryFn / mutations.
      '@tanstack/query/exhaustive-deps': 'error',
      '@tanstack/query/no-rest-destructuring': 'warn',
      '@tanstack/query/stable-query-client': 'error',
      '@tanstack/query/no-unstable-deps': 'error',
      '@tanstack/query/infinite-query-property-order': 'error',
      '@tanstack/query/no-void-query-fn': 'error',
      // Async data-loading via `useEffect(() => { fetch().then(setState) }, [])`
      // is the canonical React pattern. The React-19 strict rule flags it as a
      // performance smell, but in our admin panel the trade-off is acceptable.
      // Reviewers should still call out *derivable* state being set in effects.
      'react-hooks/set-state-in-effect': 'off',
      // `react-hooks/todo` is a meta-rule fired whenever the React Compiler
      // skips optimizing a component. We're not yet running the compiler, so
      // these hints are noise. Re-enable when adopting React Compiler.
      'react-hooks/todo': 'off',
      // Compiler-only diagnostics — no runtime impact, only optimisation hints.
      'react-hooks/memo-dependencies': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/invariant': 'off',
      'react-hooks/immutability': 'off',
      '@next/next/no-img-element': 'warn',
    },
  },
  {
    // The product-form previews render `blob:`-URLs (newly picked / cropped
    // files) and short-lived presigned URLs from ImageBackend. `next/image`
    // requires `remotePatterns` + explicit width/height and does not handle
    // blob URLs at all, so we keep plain <img> here.
    files: ['src/features/product-form/ui/**/*.{js,jsx}'],
    rules: {
      '@next/next/no-img-element': 'off',
    },
  },
  ...sharedBoundaryOverrides,
  ...entityBoundaryOverrides,
  ...featureBoundaryOverrides,
  ...widgetBoundaryOverrides,
  ...appBoundaryOverrides,
];
