/**
 * Codegen barrel — qo'lda yozilgan modullar shu yerdan import qilishi tavsiya etiladi.
 *
 *   import type { components } from "@/lib/store/__generated__";
 *   import { generatedApi } from "@/lib/store/__generated__";
 *
 * `lib/store/__generated__/api.ts` va `schema.d.ts` qo'lda tahrirlanmaydi.
 * O'zgartirish uchun `npm run api:gen && npm run api:types` ishga tushiring.
 */

export { generatedApi } from './api';
export type * from './schema';
