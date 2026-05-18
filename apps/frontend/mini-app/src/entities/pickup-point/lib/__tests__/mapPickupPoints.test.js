import { describe, it, expect } from 'vitest';

import {
  mapPickupPoint,
  mapPickupPointsResponse,
  buildPickupPointsRequestBody,
  buildPickupCompoundId,
  parsePickupCompoundId,
} from '../mapPickupPoints';

const SAMPLE_POINT = {
  providerCode: 'cdek',
  externalId: 'MSK7',
  name: 'ПВЗ Тверская',
  pickupPointType: 'pvz',
  position: { latitude: 55.7558, longitude: 37.6173 },
  address: {
    countryCode: 'RU',
    city: 'Москва',
    region: 'Москва',
    postalCode: '125009',
    street: 'Тверская',
    house: '12',
    apartment: null,
    subdivisionCode: 'MOW',
    rawAddress: 'Россия, Москва, Тверская, д. 12',
  },
  workSchedule: 'Пн-Пт 10:00-21:00',
  phone: '+7 495 000-00-00',
  isCashAllowed: true,
  isCardAllowed: false,
  weightLimitGrams: 15000,
  dimensionsLimit: { lengthCm: 80, widthCm: 60, heightCm: 40 },
};

describe('mapPickupPoint (REFACT-001 camelCase wire)', () => {
  it('happy path — camelCase ответа маппится в UI shape', () => {
    const out = mapPickupPoint(SAMPLE_POINT);
    expect(out).not.toBeNull();
    expect(out.id).toBe('cdek:MSK7');
    expect(out.providerCode).toBe('cdek');
    expect(out.externalId).toBe('MSK7');
    expect(out.pickupPointType).toBe('pvz');
    expect(out.lat).toBe(55.7558);
    expect(out.lon).toBe(37.6173);
    expect(out.workSchedule).toBe('Пн-Пт 10:00-21:00');
    expect(out.isCashAllowed).toBe(true);
    expect(out.isCardAllowed).toBe(false);
    expect(out.weightLimitGrams).toBe(15000);
    expect(out.dimensionsLimit).toEqual({ lengthCm: 80, widthCm: 60, heightCm: 40 });
    expect(out.address.countryCode).toBe('RU');
    expect(out.address.postalCode).toBe('125009');
    expect(out.address.subdivisionCode).toBe('MOW');
    expect(out.address.raw).toBe('Россия, Москва, Тверская, д. 12');
    expect(out.addressLine).toContain('Москва');
  });

  it('snake_case вход (старый wire) → null (защита от регрессии)', () => {
    const snake = {
      provider_code: 'cdek',
      external_id: 'MSK7',
      position: { latitude: 55, longitude: 37 },
    };
    expect(mapPickupPoint(snake)).toBeNull();
  });

  it('missing providerCode/externalId → null', () => {
    expect(mapPickupPoint({ ...SAMPLE_POINT, providerCode: '' })).toBeNull();
    expect(mapPickupPoint({ ...SAMPLE_POINT, externalId: '' })).toBeNull();
  });

  it('missing position или non-finite координаты → null', () => {
    expect(mapPickupPoint({ ...SAMPLE_POINT, position: null })).toBeNull();
    expect(
      mapPickupPoint({ ...SAMPLE_POINT, position: { latitude: NaN, longitude: 37 } })
    ).toBeNull();
  });
});

describe('mapPickupPointsResponse', () => {
  it('массив points + errors → UI shape', () => {
    const out = mapPickupPointsResponse({
      points: [SAMPLE_POINT, { providerCode: 'broken' /* no externalId */ }],
      errors: { yandex_delivery: 'timeout' },
    });
    expect(out.points).toHaveLength(1);
    expect(out.points[0].id).toBe('cdek:MSK7');
    expect(out.errors).toEqual({ yandex_delivery: 'timeout' });
  });

  it('пустой/невалидный response → пустой points + пустые errors', () => {
    expect(mapPickupPointsResponse(null)).toEqual({ points: [], errors: {} });
    expect(mapPickupPointsResponse({})).toEqual({ points: [], errors: {} });
  });
});

describe('buildPickupPointsRequestBody (REFACT-001 camelCase body)', () => {
  it('latitude/longitude → camelCase radiusKm', () => {
    const body = buildPickupPointsRequestBody({
      latitude: 55,
      longitude: 37,
      radiusKm: 25,
    });
    expect(body).toEqual({ latitude: 55, longitude: 37, radiusKm: 25 });
  });

  it('radiusKm clamped to 1..100, default 10', () => {
    expect(
      buildPickupPointsRequestBody({ latitude: 1, longitude: 1, radiusKm: 999 })
    ).toMatchObject({ radiusKm: 100 });
    expect(buildPickupPointsRequestBody({ latitude: 1, longitude: 1, radiusKm: 0 })).toMatchObject({
      radiusKm: 1,
    });
    expect(buildPickupPointsRequestBody({ latitude: 1, longitude: 1 })).toMatchObject({
      radiusKm: 10,
    });
  });

  it('city fallback — countryCode upcase, postalCode passthrough', () => {
    const body = buildPickupPointsRequestBody({
      city: 'Москва',
      countryCode: 'ru',
      postalCode: '125009',
    });
    expect(body).toEqual({
      city: 'Москва',
      countryCode: 'RU',
      postalCode: '125009',
    });
  });

  it('ни coords, ни city → null', () => {
    expect(buildPickupPointsRequestBody({})).toBeNull();
    expect(buildPickupPointsRequestBody({ city: '   ' })).toBeNull();
  });

  it('providerCode/deliveryType добавляются camelCase', () => {
    const body = buildPickupPointsRequestBody({
      latitude: 55,
      longitude: 37,
      providerCode: 'cdek',
      deliveryType: 'pickup_point',
    });
    expect(body.providerCode).toBe('cdek');
    expect(body.deliveryType).toBe('pickup_point');
  });
});

describe('compound id helpers', () => {
  it('build → parse round-trip', () => {
    expect(buildPickupCompoundId('cdek', 'MSK7')).toBe('cdek:MSK7');
    expect(parsePickupCompoundId('cdek:MSK7')).toEqual({
      providerCode: 'cdek',
      externalId: 'MSK7',
    });
  });

  it('externalId с двоеточием — внутри (берём первый разделитель)', () => {
    const parsed = parsePickupCompoundId('cdek:weird:id:with:colons');
    expect(parsed).toEqual({ providerCode: 'cdek', externalId: 'weird:id:with:colons' });
  });

  it('некорректный вход → null', () => {
    expect(parsePickupCompoundId('')).toBeNull();
    expect(parsePickupCompoundId('no-colon')).toBeNull();
    expect(parsePickupCompoundId(':missing-provider')).toBeNull();
  });
});
