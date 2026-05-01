function isoWithOffset(baseIso, daysForward) {
  const base = new Date(baseIso);
  const ms = base.getTime() + daysForward * 24 * 60 * 60_000;
  return new Date(ms).toISOString();
}

const baseIso = '2026-03-13T10:00:00.000Z';

export const promocodesSeed = [
  {
    id: 'promo-gnra56kh-3500',
    code: 'GNRA56KH',
    discount: { type: 'amount', value: 3500 },
    condition: 'на заказ от 20 000 ₽',
    expiresAt: isoWithOffset(baseIso, 19),
    uses: { value: 3, delta: 0 },
  },
  {
    id: 'promo-gnra56kh-5',
    code: 'GNRA56KH',
    discount: { type: 'percent', value: 5 },
    condition: 'на футболки',
    expiresAt: isoWithOffset(baseIso, 19),
    uses: { value: 9, delta: 2 },
  },
];
