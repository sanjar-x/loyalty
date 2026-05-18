import { describe, it, expect, vi } from 'vitest';

import { decideCheckoutAction, CUSTOMS_FIELDS } from '../lib/payAction';

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
    recipient: { fullName: 'x' },
    customs: { passportSeries: 'x' },
    validate: () => ({ ok: true, errors: {} }),
    ...over,
  };
}

describe('decideCheckoutAction (CHK-005)', () => {
  it('BUSY — INITIATING status returns BUSY (silent)', () => {
    const r = decideCheckoutAction(makeInput({ status: INITIATING }));
    expect(r.type).toBe('BUSY');
  });

  it('BUSY — CONFIRMING status returns BUSY', () => {
    const r = decideCheckoutAction(makeInput({ status: CONFIRMING }));
    expect(r.type).toBe('BUSY');
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

  it('NEED_CUSTOMS — validate fails on a customs field', () => {
    const validate = vi.fn(() => ({
      ok: false,
      errors: { issueDate: 'required', passportSeries: 'required' },
    }));
    const r = decideCheckoutAction(makeInput({ validate }));
    expect(r.type).toBe('NEED_CUSTOMS');
    expect(r.field).toBe('issueDate'); // first key
    expect(r.message).toMatch(/паспортные/);
  });

  it('NEED_RECIPIENT — validate fails on a recipient field first', () => {
    const validate = () => ({
      ok: false,
      errors: { fullName: 'required', inn: 'required' },
    });
    const r = decideCheckoutAction(makeInput({ validate }));
    expect(r.type).toBe('NEED_RECIPIENT');
    expect(r.field).toBe('fullName');
    expect(r.message).toMatch(/получателя/);
  });

  it('READY — all guards green', () => {
    expect(decideCheckoutAction(makeInput()).type).toBe('READY');
  });

  it('READY — no validator provided still proceeds (validators optional in unit)', () => {
    const r = decideCheckoutAction(makeInput({ validate: undefined }));
    expect(r.type).toBe('READY');
  });

  it('priority order: BUSY > EMPTY_CART > PICKUP > QUOTE > FORM (CHK-005 TZ)', () => {
    // Busy beats everything
    expect(
      decideCheckoutAction(
        makeInput({
          status: INITIATING,
          selectedQuantity: 0,
          isPickupSelected: false,
        })
      ).type
    ).toBe('BUSY');

    // Empty cart beats no-pickup
    expect(
      decideCheckoutAction(makeInput({ selectedQuantity: 0, isPickupSelected: false })).type
    ).toBe('EMPTY_CART');

    // No pickup beats expired quote
    expect(
      decideCheckoutAction(makeInput({ isPickupSelected: false, isQuoteValid: false })).type
    ).toBe('NEED_PICKUP');

    // Expired quote beats form invalid
    expect(
      decideCheckoutAction(
        makeInput({
          isQuoteValid: false,
          validate: () => ({ ok: false, errors: { inn: 'required' } }),
        })
      ).type
    ).toBe('NEED_QUOTE_REFRESH');
  });

  it('CUSTOMS_FIELDS frozen list matches expected fields', () => {
    expect([...CUSTOMS_FIELDS]).toEqual([
      'passportSeries',
      'passportNumber',
      'issueDate',
      'birthDate',
      'inn',
    ]);
  });
});
