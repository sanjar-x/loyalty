/**
 * Contract test for `removeBackground` (F-2.1 / IMG-007).
 *
 * Stubs `global.fetch` so we can assert URL, method and the
 * code-translation behaviour for the BG_REMOVAL_DISABLED 503 envelope.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { removeBackground } from '../products';

const STORAGE_ID = '019cdbf4-e987-7000-8080-000000000abc';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function jsonResponse(body, init = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  });
}

describe('removeBackground', () => {
  it('POSTs to the BFF route and returns the derivation payload', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        jsonResponse(
          {
            derivedStorageObjectId: 'derived-1',
            status: 'processing',
            url: null,
            alreadyExisted: false,
          },
          { status: 202 },
        ),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const data = await removeBackground(STORAGE_ID);
    expect(data).toMatchObject({
      derivedStorageObjectId: 'derived-1',
      status: 'processing',
      alreadyExisted: false,
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/admin/media/${STORAGE_ID}/remove-background`);
    expect(init.method).toBe('POST');
  });

  it('returns the existing derivation on idempotent re-call', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            {
              derivedStorageObjectId: 'derived-1',
              status: 'completed',
              url: 'https://cdn/no-bg.webp',
              alreadyExisted: true,
            },
            { status: 202 },
          ),
        ),
      ),
    );
    const data = await removeBackground(STORAGE_ID);
    expect(data.alreadyExisted).toBe(true);
    expect(data.url).toBe('https://cdn/no-bg.webp');
  });

  it('translates BG_REMOVAL_DISABLED into the Russian disabled message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            {
              error: {
                code: 'BG_REMOVAL_DISABLED',
                message: 'Background removal feature is currently disabled.',
                details: { feature_flag: 'BG_REMOVAL_ENABLED' },
              },
            },
            { status: 503 },
          ),
        ),
      ),
    );
    await expect(removeBackground(STORAGE_ID)).rejects.toMatchObject({
      code: 'BG_REMOVAL_DISABLED',
      status: 503,
      message: expect.stringContaining('временно отключено'),
    });
  });
});
