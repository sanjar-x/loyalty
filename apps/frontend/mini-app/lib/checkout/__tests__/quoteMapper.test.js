import { describe, it, expect } from 'vitest';

import { mapRateQuoteResponseToQuote } from '../quoteMapper';

describe('mapRateQuoteResponseToQuote (CHK-024)', () => {
  const SAMPLE = {
    quoteId: '6e7a9c3a-3a1e-4f51-8aaa-2ed7f6f7e3b1',
    providerCode: 'cdek',
    serviceCode: 'EC',
    serviceName: 'СДЭК — Посылка склад-склад',
    deliveryType: 'pickup_point',
    deliveryAmount: { amount: 32000, currency: 'RUB' },
    deliveryDaysMin: 3,
    deliveryDaysMax: 5,
    quotedAt: '2026-05-16T17:00:00Z',
    expiresAt: '2026-05-16T17:30:00Z',
    fallbackAlternatives: ['EC_EXPRESS', 'EC_OVERNIGHT'],
  };

  it('happy path — все поля camelCase, deliveryAmount распакован', () => {
    const out = mapRateQuoteResponseToQuote(SAMPLE);
    expect(out).toEqual({
      quoteId: '6e7a9c3a-3a1e-4f51-8aaa-2ed7f6f7e3b1',
      providerCode: 'cdek',
      serviceCode: 'EC',
      serviceName: 'СДЭК — Посылка склад-склад',
      deliveryType: 'pickup_point',
      deliveryAmount: 32000,
      currency: 'RUB',
      deliveryDaysMin: 3,
      deliveryDaysMax: 5,
      quotedAt: '2026-05-16T17:00:00Z',
      expiresAt: '2026-05-16T17:30:00Z',
      fallbackAlternatives: ['EC_EXPRESS', 'EC_OVERNIGHT'],
    });
  });

  it('null/undefined input → null', () => {
    expect(mapRateQuoteResponseToQuote(null)).toBeNull();
    expect(mapRateQuoteResponseToQuote(undefined)).toBeNull();
    expect(mapRateQuoteResponseToQuote('garbage')).toBeNull();
  });

  it('отсутствие deliveryAmount → 0 kopecks, RUB по умолчанию', () => {
    const out = mapRateQuoteResponseToQuote({ ...SAMPLE, deliveryAmount: undefined });
    expect(out.deliveryAmount).toBe(0);
    expect(out.currency).toBe('RUB');
  });

  it('float amount усекается до integer kopecks (totals.js требует int math)', () => {
    const out = mapRateQuoteResponseToQuote({
      ...SAMPLE,
      deliveryAmount: { amount: 32049.7, currency: 'RUB' },
    });
    expect(out.deliveryAmount).toBe(32049);
  });

  it('пустой fallbackAlternatives → [] (не undefined)', () => {
    const out = mapRateQuoteResponseToQuote({ ...SAMPLE, fallbackAlternatives: undefined });
    expect(out.fallbackAlternatives).toEqual([]);
  });

  it('фильтрует не-string записи в fallbackAlternatives', () => {
    const out = mapRateQuoteResponseToQuote({
      ...SAMPLE,
      fallbackAlternatives: ['EC_EXPRESS', null, 42, '', 'EC_OVERNIGHT'],
    });
    expect(out.fallbackAlternatives).toEqual(['EC_EXPRESS', 'EC_OVERNIGHT']);
  });

  it('null deliveryDaysMin/Max сохраняется как null', () => {
    const out = mapRateQuoteResponseToQuote({
      ...SAMPLE,
      deliveryDaysMin: null,
      deliveryDaysMax: null,
    });
    expect(out.deliveryDaysMin).toBeNull();
    expect(out.deliveryDaysMax).toBeNull();
  });

  it('non-RUB currency сохраняется (нет жёсткой привязки)', () => {
    const out = mapRateQuoteResponseToQuote({
      ...SAMPLE,
      deliveryAmount: { amount: 5000, currency: 'USD' },
    });
    expect(out.currency).toBe('USD');
    expect(out.deliveryAmount).toBe(5000);
  });
});
