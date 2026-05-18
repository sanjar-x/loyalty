/**
 * Search history — client-side persistent store.
 *
 * The backend (Spec §6, §11) doesn't currently support search-history
 * endpoints, so the history is stored entirely on the client (`localStorage`).
 * This module is the single source of persistence for RTK Query's
 * `getSearchHistory` / `createSearchHistory` / `clearSearchHistory` /
 * `removeSearchHistoryItem`.
 *
 * Design decisions:
 *  - **Schema versioning**: each time `STORAGE_VERSION` is bumped, legacy
 *    payloads are silently dropped. Bump the version when new fields are added.
 *  - **Bounded size**: `MAX_ENTRIES` (50) — to save quota. The UI shows only
 *    12, the rest sit as an implicit "recently" pool.
 *  - **TTL**: `MAX_AGE_MS` (90 days). On read, stale entries are removed
 *    automatically (purge-on-read pattern — no background timer).
 *  - **Dedup**: by normalized key (`trim → lowercase → space-collapse`) —
 *    "iPhone " and "iphone" are one entry. Last-write-wins +
 *    `hits` counter is incremented (for analytics).
 *  - **Quota-safety**: `QuotaExceededError` is caught and a retry is attempted
 *    after removing the oldest entries.
 *  - **JSON corruption**: schema validation in `parse`. Corrupted payload →
 *    `clearHistory()` (silently) → empty array.
 *  - **Cross-tab**: subscribe to the `storage` event — if one tab clears,
 *    others update automatically (RTKQ `onCacheEntryAdded` uses this).
 *  - **SSR-safe**: all functions return empty when `window === undefined`
 *    (no-op on the Next.js server).
 *
 * @typedef {Object} SearchHistoryEntry
 * @property {string} query        Text as shown by the user (trimmed/space-collapsed)
 * @property {string} normalized   Lower-case dedup key (not used in UI)
 * @property {Object|null} parameters  Filters active at submit time (sort, category_id, brand_ids, ...) — opaque payload
 * @property {string} searchedAt   ISO-8601, last searched time
 * @property {number} hits         How many times searched (>= 1)
 *
 * @typedef {Object} SearchHistoryDocument
 * @property {number} version
 * @property {SearchHistoryEntry[]} entries
 */

const STORAGE_KEY = 'lm-search-history';
const STORAGE_VERSION = 2;

export const MAX_ENTRIES = 50;
export const MAX_QUERY_LENGTH = 200; // matches `Storefront Search` `q maxLength`
export const MAX_AGE_MS = 90 * 24 * 60 * 60 * 1000; // 90 days

/* ─────────────────────── helpers ─────────────────────── */

function safeLocalStorage() {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null; // privacy mode / disabled storage
  }
}

/**
 * Trimmed + single-space collapsed form for UI labels.
 * This form is sent to the backend `q` parameter.
 */
export function normalizeDisplay(value) {
  return String(value ?? '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Canonical key for dedup and lookup. Lowercase, minimal accent-stripping —
 * NFKD separates the diacritics (cafe ↔ café).
 */
export function normalizeKey(value) {
  const display = normalizeDisplay(value).toLowerCase();
  if (!display) return '';
  try {
    return display.normalize('NFKD').replace(/[̀-ͯ]/g, '');
  } catch {
    return display;
  }
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isValidEntry(value) {
  if (!isPlainObject(value)) return false;
  if (typeof value.query !== 'string' || !value.query.trim()) return false;
  if (typeof value.normalized !== 'string') return false;
  if (typeof value.searchedAt !== 'string') return false;
  // Validate ISO timestamp without throwing
  const ts = Date.parse(value.searchedAt);
  if (!Number.isFinite(ts)) return false;
  // `parameters` is optional but must be object|null
  if (value.parameters != null && !isPlainObject(value.parameters)) return false;
  // `hits` >= 1
  if (typeof value.hits !== 'number' || !Number.isFinite(value.hits) || value.hits < 1) {
    return false;
  }
  return true;
}

function parseDocument(raw) {
  if (typeof raw !== 'string' || !raw) return null;
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
    // Quota exceeded — retry after removing the oldest entries
    const isQuota =
      err &&
      typeof err === 'object' &&
      (err.name === 'QuotaExceededError' || err.code === 22 || err.code === 1014); /* Firefox */
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
    // If even 1 entry doesn't fit — clear entirely
    try {
      ls.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    return false;
  }
}

/**
 * Purges stale entries and trims anything over `MAX_ENTRIES`.
 * Order: searchedAt DESC (newest first).
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
 * Reads history entries. Side effect: silently cleans up stale/corrupted
 * records and re-stores the updated list.
 *
 * @returns {SearchHistoryEntry[]} sorted by searchedAt DESC
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
    // Corrupted or old version — silently clean up
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

  // If prune produced changes — persist them (next-read fast-path)
  if (pruned.length !== doc.entries.length) {
    writeDocument(ls, { version: STORAGE_VERSION, entries: pruned });
  }

  return pruned;
}

/**
 * Adds a new entry (or upserts an existing one: searchedAt + hits).
 *
 * @param {Object} input
 * @param {string} input.query                      User text
 * @param {Object|null} [input.parameters]          Filter snapshot at submit time
 * @returns {SearchHistoryEntry[]} updated list
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
          query: display, // store the most recently typed form (case-preserve)
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
 * Removes a single entry by normalized key.
 *
 * @param {string} query
 * @returns {SearchHistoryEntry[]} updated list
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
 * Removes the entire history.
 *
 * @returns {SearchHistoryEntry[]} empty array
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
 * Cross-tab synchronization. The `storage` event fires only when **another**
 * tab changes the value (the current tab's writes don't fire it).
 *
 * @param {() => void} listener
 * @returns {() => void} unsubscribe
 */
export function subscribe(listener) {
  if (typeof window === 'undefined') return () => {};
  if (typeof listener !== 'function') return () => {};

  const handler = (event) => {
    if (!event) return;
    // event.key === null — when `localStorage.clear()` is called
    if (event.key !== null && event.key !== STORAGE_KEY) return;
    try {
      listener();
    } catch {
      // don't let listener errors break the subscribe layer
    }
  };

  window.addEventListener('storage', handler);
  return () => window.removeEventListener('storage', handler);
}
