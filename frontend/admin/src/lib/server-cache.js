/**
 * Simple in-memory TTL cache for BFF server routes.
 *
 * Intended for shared, non-user-specific data (catalog brands, categories,
 * suppliers, attribute metadata) that changes rarely in an admin workflow.
 *
 * Module-level singleton — survives across requests on the same Node instance.
 * Not suitable for multi-instance deployments that require strong consistency
 * (TTL-only invalidation is accepted).
 */

const store = new Map();

/**
 * Get a cached value, or fetch it with the provided async `fetcher` and cache
 * the result for `ttlMs` milliseconds.
 *
 * Concurrent calls with the same key share a single in-flight promise to avoid
 * stampedes.
 *
 * @template T
 * @param {string} key
 * @param {number} ttlMs
 * @param {() => Promise<T>} fetcher
 * @returns {Promise<T>}
 */
export async function getOrFetch(key, ttlMs, fetcher) {
  const now = Date.now();
  const entry = store.get(key);

  if (entry && entry.expiresAt > now) {
    return entry.value;
  }

  if (entry && entry.pending) {
    return entry.pending;
  }

  const pending = (async () => {
    try {
      const value = await fetcher();
      store.set(key, { value, expiresAt: Date.now() + ttlMs });
      return value;
    } catch (err) {
      store.delete(key);
      throw err;
    }
  })();

  store.set(key, { pending, expiresAt: 0 });
  return pending;
}

export function invalidate(key) {
  store.delete(key);
}

export function clearAll() {
  store.clear();
}
