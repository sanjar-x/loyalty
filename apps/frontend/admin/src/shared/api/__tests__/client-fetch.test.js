import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiClient, request } from '../clientFetch';

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

  it('normalises FastAPI {detail: "..."} string envelope and infers code from status', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Permission denied' }), {
        status: 403,
      }),
    );
    await expect(apiClient.get('/api/x')).rejects.toMatchObject({
      message: 'Permission denied',
      code: 'FORBIDDEN',
      status: 403,
    });
  });

  it('normalises FastAPI {detail: {code, message, details}} object envelope', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: {
            code: 'VALIDATION_ERROR',
            message: 'Bad input',
            details: { field: 'slug' },
          },
        }),
        { status: 422 },
      ),
    );
    await expect(apiClient.get('/api/x')).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      message: 'Bad input',
      status: 422,
      details: { field: 'slug' },
    });
  });

  it('falls back to generic "Ошибка сервера (XXX)" + status-derived code when body is unparseable', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response('not-json', { status: 500 }),
    );
    await expect(apiClient.get('/api/x')).rejects.toMatchObject({
      message: 'Ошибка сервера (500)',
      code: 'UNKNOWN',
      status: 500,
    });
  });

  it('infers UNAUTHORIZED for 401 plain-string detail (preserves dictionary lookups)', async () => {
    global.fetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not authenticated' }), {
        status: 401,
      }),
    );
    await expect(apiClient.get('/api/x')).rejects.toMatchObject({
      code: 'UNAUTHORIZED',
      status: 401,
      // default translation kicks in for "Not authenticated"
      message: 'Сессия истекла. Войдите заново.',
    });
  });
});
