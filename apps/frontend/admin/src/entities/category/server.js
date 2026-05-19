// Server-only entry-point. Do not import from client components —
// it pulls `next/headers`, which is unavailable on the client.
export { fetchCategoryTreeServer } from './api/categoriesServer';
export { categoryLabel } from './api/categories';
