import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiClient, request } from '../client-fetch';

describe('apiClient', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('GET returns parsed JSON for 2xx', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    const data = await apiClient.get('/api/test');
    expect(data).toEqual({ ok: true });
  });

  it('returns null for 204 No Content', async () => {
    global.fetch.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const data = await apiClient.del('/api/test/1');
    expect(data).toBeNull();
  });

  it('throws ApiError with translated message on 4xx/5xx', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { code: 'NOT_FOUND', message: 'Product not found' },
        }),
        { status: 404 },
      ),
    );
    await expect(
      apiClient.get('/api/p/1', {
        translations: { 'Product not found': 'Товар не найден' },
      }),
    ).rejects.toMatchObject({
      name: 'ApiError',
      code: 'NOT_FOUND',
      status: 404,
      message: 'Товар не найден',
    });
  });

  it('surfaces 429 Retry-After', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response('', { status: 429, headers: { 'Retry-After': '7' } }),
    );
    try {
      await apiClient.get('/api/p');
      throw new Error('expected throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.code).toBe('RATE_LIMITED');
      expect(err.retryAfter).toBe(7);
    }
  });

  it('serialises POST body to JSON', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: '1' }), { status: 201 }),
    );
    await apiClient.post('/api/p', { name: 'X' });
    const [, init] = global.fetch.mock.calls[0];
    expect(init.body).toBe('{"name":"X"}');
    expect(init.headers['Content-Type']).toBe('application/json');
  });

  it('always sends credentials: include', async () => {
    global.fetch.mockResolvedValueOnce(new Response('{}', { status: 200 }));
    await apiClient.get('/api/p');
    const [, init] = global.fetch.mock.calls[0];
    expect(init.credentials).toBe('include');
  });

  it('respects user-provided AbortSignal', async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    global.fetch.mockImplementationOnce((url, init) =>
      Promise.reject(
        Object.assign(new Error('aborted'), { name: 'AbortError' }),
      ),
    );
    await expect(
      request('/api/x', { signal: ctrl.signal }),
    ).rejects.toMatchObject({
      code: 'TIMEOUT',
    });
  });
});
