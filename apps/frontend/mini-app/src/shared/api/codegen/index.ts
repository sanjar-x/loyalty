/**
 * Codegen barrel — hand-written modules should import from here.
 *
 *   import type { components } from "@/shared/api/codegen";
 *   import { generatedApi } from "@/shared/api/codegen";
 *
 * Hooks are NOT exposed here — the short names live in
 * src/app/providers/store/hooks.js (re-export over enhancedApi + customApi).
 */

export { generatedApi } from './api';
export type * from './schema';
