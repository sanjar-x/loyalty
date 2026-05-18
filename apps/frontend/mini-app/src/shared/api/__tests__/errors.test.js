import { describe, it, expect } from 'vitest';

import { normalizeApiError, isTokenExpiredError } from '../errors';

function envelope(code, message = '', status = 422) {
  return {
    status,
    data: { error: { code, message, details: null, request_id: 'req-1' } },
  };
}

describe('normalizeApiError', () => {
  it('возвращает каноническую форму для backend envelope', () => {
    const n = normalizeApiError(envelope('SOMETHING', 'msg'));
    expect(n).toEqual({
      status: 422,
      code: 'SOMETHING',
      message: 'msg',
      details: null,
      requestId: 'req-1',
    });
  });

  it('FETCH_ERROR (string status) — code сохраняется', () => {
    const n = normalizeApiError({ status: 'FETCH_ERROR', error: 'Failed' });
    expect(n.code).toBe('FETCH_ERROR');
    expect(n.message).toBe('Failed');
  });
});

describe('isTokenExpiredError (sanity)', () => {
  it('401 без кода — true', () => {
    expect(isTokenExpiredError(envelope('', '', 401))).toBe(true);
  });

  it('TOKEN_EXPIRED код', () => {
    expect(isTokenExpiredError(envelope('TOKEN_EXPIRED'))).toBe(true);
  });
});
