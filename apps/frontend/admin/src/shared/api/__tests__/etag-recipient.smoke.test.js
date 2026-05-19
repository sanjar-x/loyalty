/**
 * A6 smoke test — Recipient ETag/If-Match round-trip (post-D0.3).
 *
 * The interceptor itself is unit-tested in `etag.test.js`; this file
 * pins the contract end-to-end against the Recipient endpoint that
 * Backend ships first (Brand/Category/Variant/SKU follow in Sprint 4
 * — see `etag-store.js` comment).
 *
 *   1. GET /api/recipients/{id}  → response carries `ETag: "v3"`
 *   2. PATCH same URL            → apiClient automatically attaches `If-Match: "v3"`
 *   3. Backend rejects with 412  → apiClient throws ApiError(OPTIMISTIC_LOCK_FAILED)
 *   4. Cached tag is invalidated → next PATCH must NOT carry If-Match
 *      until the consumer re-GETs the resource.
 *
 * The test stays at the apiClient layer (no UI / TanStack Query) so
 * the contract is locked even if the BFF route or the React surface
 * changes later. The toast UX is exercised in modal-level tests.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient, ApiError } from '../clientFetch';
import { clearAll, getEtag } from '../etagStore';

const RECIPIENT_URL = '/api/recipients/019cdbf4-e987-7000-8080-000000000001';

beforeEach(() => {
  clearAll();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  clearAll();
});

function jsonResponse(body, init = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  });
}

describe('A6 — recipient ETag smoke', () => {
  it('GET caches the tag, PATCH replays it, 412 invalidates the cache', async () => {
    const fetchMock = vi
      .fn()
      // 1. GET — backend returns "v3"
      .mockImplementationOnce(() =>
        Promise.resolve(
          jsonResponse(
            { id: 'rec-1', fullNameRu: 'Иванов И.И.' },
            { headers: { ETag: '"v3"' } },
          ),
        ),
      )
      // 2. PATCH with stale "v3" — backend rejects with 412
      .mockImplementationOnce(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              error: {
                code: 'PRECONDITION_FAILED',
                message: 'Recipient version mismatch',
                details: {},
              },
            }),
            {
              status: 412,
              headers: { 'Content-Type': 'application/json' },
            },
          ),
        ),
      );
    vi.stubGlobal('fetch', fetchMock);

    // Step 1 — GET the resource, tag lands in the store.
    const recipient = await apiClient.get(RECIPIENT_URL);
    expect(recipient.id).toBe('rec-1');
    expect(getEtag(RECIPIENT_URL)).toBe('"v3"');

    // Step 2 — PATCH must carry If-Match: "v3", and 412 must surface
    // as ApiError(OPTIMISTIC_LOCK_FAILED) so the consumer can show
    // the "запись изменилась" toast + invalidate its query.
    let caught;
    try {
      await apiClient.patch(RECIPIENT_URL, {
        fullNameRu: 'Иванов И.И. (новая фамилия)',
      });
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.code).toBe('OPTIMISTIC_LOCK_FAILED');
    expect(caught.status).toBe(412);

    const [, patchInit] = fetchMock.mock.calls[1];
    expect(patchInit.headers['If-Match']).toBe('"v3"');

    // Step 3 — store invalidated; the next PATCH (without a fresh
    // GET) must NOT carry If-Match so the caller doesn't accidentally
    // resubmit the stale tag and trip another 412.
    expect(getEtag(RECIPIENT_URL)).toBeNull();
  });

  it('successful PATCH (200) drops the cache too — next read repopulates', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve(
          jsonResponse({ id: 'rec-1' }, { headers: { ETag: '"v3"' } }),
        ),
      )
      .mockImplementationOnce(() =>
        Promise.resolve(
          jsonResponse(
            { id: 'rec-1', updated: true },
            { status: 200, headers: { ETag: '"v4"' } },
          ),
        ),
      );
    vi.stubGlobal('fetch', fetchMock);

    await apiClient.get(RECIPIENT_URL);
    await apiClient.patch(RECIPIENT_URL, { fullNameRu: 'X' });

    // Mutating success → drop the cached tag (resource version moved
    // server-side; the next GET will pick up "v4"). The relayed ETag
    // header on the response is intentionally NOT auto-cached on
    // PATCH — only GETs populate the store.
    expect(getEtag(RECIPIENT_URL)).toBeNull();
  });
});
