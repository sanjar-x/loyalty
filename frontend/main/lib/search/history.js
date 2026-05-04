/**
 * Search history — client-side persistent store.
 *
 * Backend (Spec §6, §11) hozircha search-history endpoint'larini
 * qo'llab-quvvatlamaydi, shuning uchun tarix to'liq mijoz tarafda
 * (`localStorage`) saqlanadi. Bu modul RTK Query'dagi `getSearchHistory` /
 * `createSearchHistory` / `clearSearchHistory` / `removeSearchHistoryItem`
 * uchun yagona persistance manbai.
 *
 * Disayn qarorlari:
 *  - **Schema versioning**: `STORAGE_VERSION` bumb qilingan har safar legacy
 *    payload tashlanadi (silently). Yangi maydonlar qo'shilsa version'ni
 *    oshiring.
 *  - **Bounded size**: `MAX_ENTRIES` (50) — quota'ni tejash. UI faqat 12'tasini
 *    ko'rsatadi, qolgani implicit "yaqinda" pool sifatida turadi.
 *  - **TTL**: `MAX_AGE_MS` (90 kun). O'qish paytida eskirgan entry'lar
 *    avtomatik o'chiriladi (purge-on-read pattern — fon timer'siz).
 *  - **Dedup**: normallashtirilgan kalit (`trim → lowercase → space-collapse`)
 *    bo'yicha — "iPhone " va "iphone" bir entry. Last-write-wins +
 *    `hits` counter incrementlanadi (analytics uchun).
 *  - **Quota-safety**: `QuotaExceededError` ushlanadi va eng eskilarini olib
 *    tashlab qayta yozish urinishi qilinadi.
 *  - **JSON corruption**: schema validation `parse`'da. Buzilgan payload →
 *    `clearHistory()` (silently) → bo'sh massiv.
 *  - **Cross-tab**: `storage` event'iga subscribe — bitta tabda o'chirsa
 *    boshqasi avtomatik yangilanadi (RTKQ `onCacheEntryAdded` ishlatadi).
 *  - **SSR-safe**: barcha funksiyalar `window === undefined` bo'lsa empty
 *    qaytaradi (Next.js serverda no-op).
 *
 * @typedef {Object} SearchHistoryEntry
 * @property {string} query        Foydalanuvchi tomonidan ko'rsatilgan matn (ham trimmed/space-collapsed)
 * @property {string} normalized   Lower-case dedup kalit (UI'da ishlatilmaydi)
 * @property {Object|null} parameters  Submit paytida amal qilgan filtrlar (sort, category_id, brand_ids, ...) — opaque payload
 * @property {string} searchedAt   ISO-8601, oxirgi qidirilgan vaqt
 * @property {number} hits         Necha marta qidirilgan (>= 1)
 *
 * @typedef {Object} SearchHistoryDocument
 * @property {number} version
 * @property {SearchHistoryEntry[]} entries
 */

const STORAGE_KEY = "lm-search-history";
const STORAGE_VERSION = 2;

export const MAX_ENTRIES = 50;
export const MAX_QUERY_LENGTH = 200; // mos `Storefront Search` `q maxLength`
export const MAX_AGE_MS = 90 * 24 * 60 * 60 * 1000; // 90 days

/* ─────────────────────── helpers ─────────────────────── */

function safeLocalStorage() {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null; // privacy mode / disabled storage
  }
}

/**
 * UI label uchun trimmed + bitta probelga qisqartirilgan ko'rinish.
 * Backend `q` parametriga shu ko'rinish uzatiladi.
 */
export function normalizeDisplay(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

/**
 * Dedup va lookup uchun kanonik kalit. Kichik harf, accent-stripping
 * minimal — JS NFKD bilan diakritikalar ajraladi (cafe ↔ café).
 */
export function normalizeKey(value) {
  const display = normalizeDisplay(value).toLowerCase();
  if (!display) return "";
  try {
    return display.normalize("NFKD").replace(/[̀-ͯ]/g, "");
  } catch {
    return display;
  }
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isValidEntry(value) {
  if (!isPlainObject(value)) return false;
  if (typeof value.query !== "string" || !value.query.trim()) return false;
  if (typeof value.normalized !== "string") return false;
  if (typeof value.searchedAt !== "string") return false;
  // Validate ISO timestamp without throwing
  const ts = Date.parse(value.searchedAt);
  if (!Number.isFinite(ts)) return false;
  // `parameters` opsional, lekin object|null bo'lishi kerak
  if (value.parameters != null && !isPlainObject(value.parameters)) return false;
  // `hits` >= 1
  if (typeof value.hits !== "number" || !Number.isFinite(value.hits) || value.hits < 1) {
    return false;
  }
  return true;
}

function parseDocument(raw) {
  if (typeof raw !== "string" || !raw) return null;
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isPlainObject(parsed)) return null;
  if (parsed.version !== STORAGE_VERSION) return null;
  if (!Array.isArray(parsed.entries)) return null;
  return parsed;
}

function writeDocument(ls, doc) {
  const serialized = JSON.stringify(doc);
  try {
    ls.setItem(STORAGE_KEY, serialized);
    return true;
  } catch (err) {
    // Quota exceeded — eng eskilarini olib tashlab qayta urinish
    const isQuota =
      err &&
      typeof err === "object" &&
      (err.name === "QuotaExceededError" ||
        err.code === 22 ||
        err.code === 1014 /* Firefox */);
    if (!isQuota) return false;

    let entries = Array.isArray(doc.entries) ? doc.entries : [];
    while (entries.length > 1) {
      entries = entries.slice(0, Math.floor(entries.length / 2));
      try {
        ls.setItem(STORAGE_KEY, JSON.stringify({ ...doc, entries }));
        return true;
      } catch {
        // try again with smaller slice
      }
    }
    // Hatto 1 ta entry ham sig'masa — to'liq tozalaymiz
    try {
      ls.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    return false;
  }
}

/**
 * Eskirganlarni purge va `MAX_ENTRIES`'dan ortiqlarini trim qiladi.
 * Tartib: searchedAt DESC (yangi-eski).
 */
function pruneEntries(entries) {
  const now = Date.now();
  const seen = new Set();
  const valid = [];
  for (const entry of entries) {
    if (!isValidEntry(entry)) continue;
    const ts = Date.parse(entry.searchedAt);
    if (now - ts > MAX_AGE_MS) continue;
    if (seen.has(entry.normalized)) continue; // sanity dedup
    seen.add(entry.normalized);
    valid.push(entry);
  }
  valid.sort((a, b) => Date.parse(b.searchedAt) - Date.parse(a.searchedAt));
  if (valid.length > MAX_ENTRIES) valid.length = MAX_ENTRIES;
  return valid;
}

/* ─────────────────────── public API ─────────────────────── */

/**
 * Tarix entry'larini o'qiydi. Yon ta'sir: eskirgan/buzilgan yozuvlarni
 * jim ravishda tozalaydi va yangilangan ro'yxatni qayta saqlaydi.
 *
 * @returns {SearchHistoryEntry[]} searchedAt DESC bo'yicha tartiblangan
 */
export function readHistory() {
  const ls = safeLocalStorage();
  if (!ls) return [];

  let raw;
  try {
    raw = ls.getItem(STORAGE_KEY);
  } catch {
    return [];
  }

  const doc = parseDocument(raw);
  if (!doc) {
    // Buzilgan yoki eski versiya — tinch tozalaymiz
    if (raw != null) {
      try {
        ls.removeItem(STORAGE_KEY);
      } catch {
        // ignore
      }
    }
    return [];
  }

  const pruned = pruneEntries(doc.entries);

  // Agar prune'da o'zgarish bo'lgan bo'lsa — saqlab qo'yamiz (next-read fast-path)
  if (pruned.length !== doc.entries.length) {
    writeDocument(ls, { version: STORAGE_VERSION, entries: pruned });
  }

  return pruned;
}

/**
 * Yangi entry qo'shadi (yoki mavjudini upsert qiladi: searchedAt + hits).
 *
 * @param {Object} input
 * @param {string} input.query                      Foydalanuvchi matni
 * @param {Object|null} [input.parameters]          Submit paytidagi filter snapshot'i
 * @returns {SearchHistoryEntry[]} yangilangan ro'yxat
 */
export function addEntry({ query, parameters = null } = {}) {
  const display = normalizeDisplay(query);
  if (!display) return readHistory();
  if (display.length > MAX_QUERY_LENGTH) return readHistory();

  const ls = safeLocalStorage();
  if (!ls) return [];

  const key = normalizeKey(display);
  if (!key) return readHistory();

  const existing = readHistory();
  const now = new Date().toISOString();

  const existingIdx = existing.findIndex((e) => e.normalized === key);
  /** @type {SearchHistoryEntry} */
  const upserted =
    existingIdx >= 0
      ? {
          ...existing[existingIdx],
          query: display, // oxirgi yozilgan ko'rinishni saqlaymiz (case-preserve)
          parameters: isPlainObject(parameters) ? parameters : null,
          searchedAt: now,
          hits: existing[existingIdx].hits + 1,
        }
      : {
          query: display,
          normalized: key,
          parameters: isPlainObject(parameters) ? parameters : null,
          searchedAt: now,
          hits: 1,
        };

  const next =
    existingIdx >= 0
      ? [upserted, ...existing.slice(0, existingIdx), ...existing.slice(existingIdx + 1)]
      : [upserted, ...existing];

  if (next.length > MAX_ENTRIES) next.length = MAX_ENTRIES;

  writeDocument(ls, { version: STORAGE_VERSION, entries: next });
  return next;
}

/**
 * Bitta entry'ni normallashtirilgan kalit bo'yicha o'chiradi.
 *
 * @param {string} query
 * @returns {SearchHistoryEntry[]} yangilangan ro'yxat
 */
export function removeEntry(query) {
  const ls = safeLocalStorage();
  if (!ls) return [];
  const key = normalizeKey(query);
  if (!key) return readHistory();

  const current = readHistory();
  const next = current.filter((e) => e.normalized !== key);
  if (next.length === current.length) return current;

  writeDocument(ls, { version: STORAGE_VERSION, entries: next });
  return next;
}

/**
 * Barcha tarixni o'chiradi.
 *
 * @returns {SearchHistoryEntry[]} bo'sh massiv
 */
export function clearHistory() {
  const ls = safeLocalStorage();
  if (!ls) return [];
  try {
    ls.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
  return [];
}

/**
 * Cross-tab sinxronizatsiya. `storage` event'i faqat **boshqa** tabda
 * o'zgarish bo'lganda chaqiriladi (joriy tab o'zgartirsa — yo'q).
 *
 * @param {() => void} listener
 * @returns {() => void} unsubscribe
 */
export function subscribe(listener) {
  if (typeof window === "undefined") return () => {};
  if (typeof listener !== "function") return () => {};

  const handler = (event) => {
    if (!event) return;
    // event.key === null — `localStorage.clear()` chaqirilganda
    if (event.key !== null && event.key !== STORAGE_KEY) return;
    try {
      listener();
    } catch {
      // listener xatolari subscribe layer'ni buzmasin
    }
  };

  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}
