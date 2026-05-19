/**
 * Audit 2.4 — verify the helper covers every code currently emitted by
 * useSubmitProduct + useUpdateProduct. The mapping must stay in sync
 * with submit-error.js codes; if a new code is added without updating
 * this test, the default branch will swallow it silently.
 */
import { describe, expect, it } from 'vitest';
import { formatSubmitError } from '../formatSubmitError';

describe('formatSubmitError', () => {
  it('null/undefined → empty strings, not a cancellation', () => {
    expect(formatSubmitError(null)).toEqual({
      short: '',
      long: '',
      isCancellation: false,
    });
    expect(formatSubmitError(undefined)).toEqual({
      short: '',
      long: '',
      isCancellation: false,
    });
  });

  it('plain string error → identical short/long, not a cancellation', () => {
    const out = formatSubmitError('Что-то сломалось');
    expect(out.short).toBe('Что-то сломалось');
    expect(out.long).toBe('Что-то сломалось');
    expect(out.isCancellation).toBe(false);
  });

  it('MEDIA_PARTIAL_FAILURE long copy includes server message + reassurance', () => {
    const out = formatSubmitError({
      code: 'MEDIA_PARTIAL_FAILURE',
      message: '2 of 5 failed.',
    });
    expect(out.long).toContain('2 of 5 failed.');
    expect(out.long).toContain('отредактировать');
    expect(out.short).toContain('изображения');
    expect(out.isCancellation).toBe(false);
  });

  it('ABORTED_AFTER_CREATE → cancellation flag set', () => {
    const out = formatSubmitError({ code: 'ABORTED_AFTER_CREATE' });
    expect(out.isCancellation).toBe(true);
    expect(out.short).toMatch(/отменена/i);
  });

  it.each(['ZERO_SKUS', 'TIMEOUT', 'RATE_LIMITED'])(
    '%s → mapped to localized copy',
    (code) => {
      const out = formatSubmitError({ code });
      expect(out.short).not.toMatch(/^Ошибка/);
      expect(out.short.length).toBeGreaterThan(0);
      expect(out.isCancellation).toBe(false);
    },
  );

  it('unknown code → "Ошибка: <message>" fallback', () => {
    const out = formatSubmitError({ code: 'WHAT', message: 'boom' });
    expect(out.short).toBe('Ошибка: boom');
    expect(out.long).toBe('Ошибка: boom');
  });

  it('unknown code without message → bare "Ошибка"', () => {
    const out = formatSubmitError({ code: 'WHAT' });
    expect(out.short).toBe('Ошибка');
  });
});
