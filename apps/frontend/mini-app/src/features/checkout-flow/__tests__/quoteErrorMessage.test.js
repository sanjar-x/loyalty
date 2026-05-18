import { describe, it, expect } from 'vitest';

import {
  pickProviderErrorMessage,
  PROVIDER_ERROR_FALLBACK,
  PROVIDER_ERROR_MISSING_ORIGIN,
} from '../lib/quoteErrorMessage';

describe('pickProviderErrorMessage (CHK-017)', () => {
  it('default_origin substring → missing-origin RU message', () => {
    expect(
      pickProviderErrorMessage("Provider 'yandex_delivery' has no default_origin configured")
    ).toBe(PROVIDER_ERROR_MISSING_ORIGIN);
  });

  it('default_origin anywhere in message — still detected', () => {
    expect(pickProviderErrorMessage('Internal error: missing default_origin key')).toBe(
      PROVIDER_ERROR_MISSING_ORIGIN
    );
  });

  it('unrelated provider message → generic fallback', () => {
    expect(pickProviderErrorMessage('upstream timeout')).toBe(PROVIDER_ERROR_FALLBACK);
  });

  it('empty / null / non-string → fallback', () => {
    expect(pickProviderErrorMessage('')).toBe(PROVIDER_ERROR_FALLBACK);
    expect(pickProviderErrorMessage(null)).toBe(PROVIDER_ERROR_FALLBACK);
    expect(pickProviderErrorMessage(undefined)).toBe(PROVIDER_ERROR_FALLBACK);
    expect(pickProviderErrorMessage(42)).toBe(PROVIDER_ERROR_FALLBACK);
  });

  it('case-sensitive on `default_origin` — backend keeps lowercase', () => {
    // Documenting intent: we don't fuzzy-match; backend message format is
    // stable per BACK-LOG-001 ticket. Test guards accidental regex change.
    expect(pickProviderErrorMessage('Default_Origin not configured')).toBe(PROVIDER_ERROR_FALLBACK);
  });

  it('exported constants are non-empty Russian strings', () => {
    expect(PROVIDER_ERROR_FALLBACK).toMatch(/Сервис доставки/);
    expect(PROVIDER_ERROR_MISSING_ORIGIN).toMatch(/оператором/);
  });
});
