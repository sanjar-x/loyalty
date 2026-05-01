// Server-only entry-point. Do not import from client components —
// it pulls `next/headers`, which is unavailable on the client.
export { fetchCategoryTreeServer } from './api/categories.server';
export { categoryLabel } from './api/categories';
