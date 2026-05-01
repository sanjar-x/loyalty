import { describe, expect, it } from 'vitest';
import { resolveOrderStatus } from '../orders';

describe('resolveOrderStatus', () => {
  it('returns canceled when every item is canceled', () => {
    expect(resolveOrderStatus('placed', ['Отменен', 'Отменен'])).toBe(
      'canceled',
    );
  });

  it('returns in_transit when at least one item is in transit', () => {
    expect(resolveOrderStatus('placed', ['В пути', 'Готов к выдаче'])).toBe(
      'in_transit',
    );
  });

  it('preserves pickup_point and received order-level status', () => {
    expect(resolveOrderStatus('pickup_point', ['Готов к выдаче'])).toBe(
      'pickup_point',
    );
    expect(resolveOrderStatus('received', ['Получен'])).toBe('received');
  });

  it('falls back to placed for any other combination', () => {
    expect(resolveOrderStatus('placed', ['Готов к выдаче'])).toBe('placed');
    expect(resolveOrderStatus('placed', [])).toBe('placed');
  });
});
