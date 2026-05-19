/**
 * F-5 ETag/If-Match interceptor — contract for the apiClient round-trip.
 *
 * The store is module-level state, so tests reach in via
 * `etag-store.clearAll()` to keep specs isolated.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient, ApiError } from '../clientFetch';
import { clearAll, getEtag, rememberEtag } from '../etagStore';

const URL = '/api/catalog/products/p1';

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

describe('etag-store', () => {
  it('round-trips a tag for a URL', () => {
    expect(getEtag(URL)).toBeNull();
    rememberEtag(URL, '"v3"');
    expect(getEtag(URL)).toBe('"v3"');
  });

  it('ignores empty url or empty tag', () => {
    rememberEtag('', '"v3"');
    rememberEtag(URL, '');
    expect(getEtag(URL)).toBeNull();
  });
});

describe('apiClient — ETag/If-Match interceptor', () => {
  it('captures ETag on a successful GET and replays it on the next PATCH', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve(
          jsonResponse({ id: 'p1' }, { headers: { ETag: '"v3"' } }),
        ),
      )
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({})));
    vi.stubGlobal('fetch', fetchMock);

    await apiClient.get(URL);
    expect(getEtag(URL)).toBe('"v3"');

    await apiClient.patch(URL, { titleI18N: { ru: 'X', en: 'X' } });
    const [, init] = fetchMock.mock.calls[1];
    expect(init.headers['If-Match']).toBe('"v3"');
    // Successful mutation drops the cached tag — next read will repopulate.
    expect(getEtag(URL)).toBeNull();
  });

  it('strips query string from the cache key (GET /...?cursor=x → PATCH /... uses same tag)', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve(jsonResponse({}, { headers: { ETag: '"v7"' } })),
      )
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({})));
    vi.stubGlobal('fetch', fetchMock);

    await apiClient.get(`${URL}?cursor=abc`);
    await apiClient.patch(URL, {});
    const [, init] = fetchMock.mock.calls[1];
    expect(init.headers['If-Match']).toBe('"v7"');
  });

  it('throws OPTIMISTIC_LOCK_FAILED on 412 and invalidates the cached tag', async () => {
    rememberEtag(URL, '"stale"');
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(null, {
            status: 412,
            headers: { 'Content-Type': 'application/json' },
          }),
        ),
      ),
    );

    await expect(
      apiClient.patch(URL, { titleI18N: { ru: 'X', en: 'X' } }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(getEtag(URL)).toBeNull();
  });

  it('lets caller-provided If-Match win over the cached tag', async () => {
    rememberEtag(URL, '"cached"');
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse({})));
    vi.stubGlobal('fetch', fetchMock);

    await apiClient.patch(URL, {}, { headers: { 'If-Match': '"caller"' } });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers['If-Match']).toBe('"caller"');
  });
});
