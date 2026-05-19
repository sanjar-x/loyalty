import { describe, it, expect, vi } from 'vitest';

import { decideCheckoutAction } from '../lib/payAction';

const INITIATING = 'initiating';
const CONFIRMING = 'confirming';
const READY_STATUS = 'ready';

function makeInput(over = {}) {
  return {
    status: READY_STATUS,
    initiatingStatus: INITIATING,
    confirmingStatus: CONFIRMING,
    selectedQuantity: 1,
    isPickupSelected: true,
    isQuoteValid: true,
    recipient: { fullName: 'Иванов Иван' },
    hasCrossBorderItems: false,
    passportId: null,
    validate: () => ({ ok: true, errors: {} }),
    ...over,
  };
}

describe('decideCheckoutAction (CHK-005)', () => {
  it('BUSY — INITIATING status returns BUSY (silent)', () => {
    expect(decideCheckoutAction(makeInput({ status: INITIATING })).type).toBe('BUSY');
  });

  it('BUSY — CONFIRMING status returns BUSY', () => {
    expect(decideCheckoutAction(makeInput({ status: CONFIRMING })).type).toBe('BUSY');
  });

  it('EMPTY_CART — selectedQuantity 0', () => {
    const r = decideCheckoutAction(makeInput({ selectedQuantity: 0 }));
    expect(r).toEqual({ type: 'EMPTY_CART', message: 'Корзина пуста' });
  });

  it('EMPTY_CART — selectedQuantity is NaN/negative', () => {
    expect(decideCheckoutAction(makeInput({ selectedQuantity: -3 })).type).toBe('EMPTY_CART');
    expect(decideCheckoutAction(makeInput({ selectedQuantity: NaN })).type).toBe('EMPTY_CART');
  });

  it('NEED_PICKUP — pickup not selected (after EMPTY_CART check)', () => {
    const r = decideCheckoutAction(makeInput({ isPickupSelected: false }));
    expect(r.type).toBe('NEED_PICKUP');
    expect(r.message).toMatch(/Выберите пункт/);
  });

  it('NEED_QUOTE_REFRESH — quote expired', () => {
    const r = decideCheckoutAction(makeInput({ isQuoteValid: false }));
    expect(r.type).toBe('NEED_QUOTE_REFRESH');
    expect(r.message).toMatch(/Обновляем/);
  });

  it('NEED_RECIPIENT — validate fails on a recipient field', () => {
    const validate = vi.fn(() => ({
      ok: false,
      errors: { fullName: 'required' },
    }));
    const r = decideCheckoutAction(makeInput({ validate }));
    expect(r.type).toBe('NEED_RECIPIENT');
    expect(r.field).toBe('fullName');
    expect(r.message).toMatch(/получателя/);
  });

  it('NEED_PASSPORT — cross-border cart without resolved passportId', () => {
    const r = decideCheckoutAction(makeInput({ hasCrossBorderItems: true, passportId: null }));
    expect(r.type).toBe('NEED_PASSPORT');
    expect(r.message).toMatch(/паспорт/i);
  });

  it('READY — cross-border cart WITH resolved passportId', () => {
    expect(
      decideCheckoutAction(makeInput({ hasCrossBorderItems: true, passportId: 'pp-1' })).type
    ).toBe('READY');
  });

  it('READY — local cart, no passport required', () => {
    expect(decideCheckoutAction(makeInput()).type).toBe('READY');
  });

  it('READY — no validator provided still proceeds (validators optional in unit)', () => {
    const r = decideCheckoutAction(makeInput({ validate: undefined }));
    expect(r.type).toBe('READY');
  });

  it('priority order: BUSY > EMPTY_CART > PICKUP > QUOTE > RECIPIENT > PASSPORT', () => {
    // Busy beats everything.
    expect(
      decideCheckoutAction(
        makeInput({
          status: INITIATING,
          selectedQuantity: 0,
          isPickupSelected: false,
          hasCrossBorderItems: true,
          passportId: null,
        })
      ).type
    ).toBe('BUSY');

    // Empty cart beats no-pickup.
    expect(
      decideCheckoutAction(makeInput({ selectedQuantity: 0, isPickupSelected: false })).type
    ).toBe('EMPTY_CART');

    // No pickup beats expired quote.
    expect(
      decideCheckoutAction(makeInput({ isPickupSelected: false, isQuoteValid: false })).type
    ).toBe('NEED_PICKUP');

    // Expired quote beats form invalid.
    expect(
      decideCheckoutAction(
        makeInput({
          isQuoteValid: false,
          validate: () => ({ ok: false, errors: { fullName: 'required' } }),
        })
      ).type
    ).toBe('NEED_QUOTE_REFRESH');

    // Form invalid beats need_passport.
    expect(
      decideCheckoutAction(
        makeInput({
          validate: () => ({ ok: false, errors: { fullName: 'required' } }),
          hasCrossBorderItems: true,
          passportId: null,
        })
      ).type
    ).toBe('NEED_RECIPIENT');
  });
});
