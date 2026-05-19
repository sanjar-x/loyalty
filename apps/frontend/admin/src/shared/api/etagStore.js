// Module-level ETag cache used by `apiClient` for opportunistic
// optimistic concurrency control (RFC 7232 If-Match semantics).
//
// Lifecycle:
//   - GET /api/foo/123 → backend sends `ETag: "v3"` → rememberEtag('/api/foo/123', '"v3"')
//   - PATCH /api/foo/123 → apiClient looks up the saved tag and adds
//     `If-Match: "v3"` to the outgoing headers
//   - On 412 Precondition Failed → invalidateEtag(url) so the next GET
//     repopulates the cache and the consumer can retry safely.
//
// Keyed by URL (path + query). The map is per-instance — there is no
// cross-tab synchronisation; a 412 in tab A doesn't preemptively
// invalidate tab B's cache. That's acceptable: the 412 will land on
// the next mutating request from tab B and we recover then.
//
// Not persisted across reloads. ETags are typically resource-version
// strings tied to in-memory query data; on reload TanStack Query
// re-fetches and we'll see the fresh tag.
//
// Backend coverage as of D0.3:
//   - Recipient (PATCH /api/v1/recipients/{id}) — covered.
// TODO(sprint-4): ETag/If-Match for Brand / Category / Variant / SKU
// once backend adds the `version` column (see backend/docs/sprint-3-deferred.md).
// The interceptor below is URL-keyed, so when those endpoints start
// emitting `ETag` headers no frontend change is needed — this comment
// is a search-anchor for the Sprint 4 audit.

const store = new Map();

/** Store the ETag header value (with quotes preserved) for a URL. */
export function rememberEtag(url, etag) {
  if (!url || !etag) return;
  store.set(url, etag);
}

/** Read the cached ETag for a URL, or null if none. */
export function getEtag(url) {
  return store.get(url) ?? null;
}

/** Drop the cached ETag for a URL — used after 412 + on mutations. */
export function invalidateEtag(url) {
  store.delete(url);
}

/** Test helper — wipe the entire cache between specs. */
export function clearAll() {
  store.clear();
}
