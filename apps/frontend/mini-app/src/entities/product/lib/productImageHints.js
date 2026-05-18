/**
 * Product image hint store.
 *
 * Storefront PDP `/catalog/storefront/products/{slug}` currently sometimes
 * returns `media: []` for products whose images are correctly populated on
 * PLP / similar / also-viewed endpoints. Until backend fixes the PDP
 * serializer, we seed a client-side hint map (sessionStorage) every time any
 * storefront response passes through `mapStorefrontProduct` with non-empty
 * images, and read from it on PDP when `media` is empty.
 *
 * This is intentionally best-effort: on deep-link to PDP without prior PLP
 * visit there will be no hint, and the UI falls back to the placeholder.
 */

const STORAGE_KEY = 'pdp:image-hints:v1';
const MAX_ENTRIES = 200;

const memoryCache = new Map();

function isBrowser() {
  return typeof window !== 'undefined' && !!window.sessionStorage;
}

function readAll() {
  if (!isBrowser()) return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(map) {
  if (!isBrowser()) return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* quota or serialization error — ignore */
  }
}

function normalizeList(images) {
  if (!Array.isArray(images)) return [];
  const out = [];
  for (const u of images) {
    if (typeof u === 'string' && u.trim() && !out.includes(u)) out.push(u);
    if (out.length >= 12) break;
  }
  return out;
}

export function saveProductImageHint(slug, images) {
  const key = typeof slug === 'string' ? slug.trim() : '';
  if (!key) return;
  const list = normalizeList(images);
  if (!list.length) return;

  memoryCache.set(key, list);

  const all = readAll();
  if (!all) return;
  all[key] = list;

  const keys = Object.keys(all);
  if (keys.length > MAX_ENTRIES) {
    const drop = keys.length - MAX_ENTRIES;
    for (let i = 0; i < drop; i += 1) delete all[keys[i]];
  }
  writeAll(all);
}

export function loadProductImageHint(slug) {
  const key = typeof slug === 'string' ? slug.trim() : '';
  if (!key) return [];
  if (memoryCache.has(key)) return memoryCache.get(key);
  const all = readAll();
  const list = all && Array.isArray(all[key]) ? all[key] : [];
  if (list.length) memoryCache.set(key, list);
  return list;
}
