// Sprint 3d: RTKQ hooks are split across entities/api/hooks.js and features/api/hooks.js.
// This barrel is kept for compatibility — it only exports the instance
// (api, enhancedApi, customApi) and makeStore.
//
// Import hooks from the specific slice:
//   from '@/entities/cart', '@/features/checkout-flow', '@/entities/user', etc.
// Cache-level operations (api.util.upsertQueryData):
//   from '@/app/providers/store/instance'
export * from './instance';
export * from './configure';
