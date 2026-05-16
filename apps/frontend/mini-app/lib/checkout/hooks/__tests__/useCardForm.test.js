import { describe, it, expect, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useCardForm } from '../useCardForm';

const VALID = {
  numberDigits: '4242424242424242',
  exp: '12/30',
  cvc: '123',
  holder: 'IVAN PETROV',
};

describe('useCardForm (CHK-020)', () => {
  it('empty defaults; PCI — no initialValue (card never persists)', () => {
    const { result } = renderHook(() => useCardForm({ onSave: () => {} }));
    expect(result.current.draft).toEqual({
      numberDigits: '',
      exp: '',
      cvc: '',
      holder: '',
    });
  });

  it('setNumber normalizes (strips non-digits, caps 19)', () => {
    const { result } = renderHook(() => useCardForm({ onSave: () => {} }));
    act(() => result.current.setNumber('4242 4242 4242 4242'));
    expect(result.current.draft.numberDigits).toBe('4242424242424242');
  });

  it('numberFormatted groups by 4', () => {
    const { result } = renderHook(() => useCardForm({ onSave: () => {} }));
    act(() => result.current.setNumber('4242424242424242'));
    expect(result.current.numberFormatted).toBe('4242 4242 4242 4242');
  });

  it('setExp normalizes MM/YY', () => {
    const { result } = renderHook(() => useCardForm({ onSave: () => {} }));
    act(() => result.current.setExp('1230'));
    expect(result.current.draft.exp).toBe('12/30');
  });

  it('setCvc strips non-digits and caps 4', () => {
    const { result } = renderHook(() => useCardForm({ onSave: () => {} }));
    act(() => result.current.setCvc('12abc345'));
    expect(result.current.draft.cvc).toBe('1234');
  });

  it('errors empty until submit attempted', () => {
    const { result } = renderHook(() => useCardForm({ onSave: () => {} }));
    act(() => result.current.setNumber('0000'));
    expect(result.current.errors).toEqual({});
  });

  it('handleSubmit fails on invalid (Luhn)', () => {
    const onSave = vi.fn();
    const { result } = renderHook(() => useCardForm({ onSave }));
    act(() => result.current.setNumber('4242424242424241'));
    act(() => result.current.setExp('12/30'));
    act(() => result.current.setCvc('123'));
    act(() => result.current.setHolder('IVAN'));
    let ok;
    act(() => {
      ok = result.current.handleSubmit();
    });
    expect(ok).toBe(false);
    expect(onSave).not.toHaveBeenCalled();
    expect(result.current.errors.numberDigits).toBe('invalid');
  });

  it('handleSubmit succeeds and calls onSave with the draft', () => {
    const onSave = vi.fn();
    const { result } = renderHook(() => useCardForm({ onSave }));
    act(() => result.current.setNumber(VALID.numberDigits));
    act(() => result.current.setExp(VALID.exp));
    act(() => result.current.setCvc(VALID.cvc));
    act(() => result.current.setHolder(VALID.holder));
    let ok;
    act(() => {
      ok = result.current.handleSubmit();
    });
    expect(ok).toBe(true);
    expect(onSave).toHaveBeenCalledWith(VALID);
  });

  it('reset clears draft', () => {
    const { result } = renderHook(() => useCardForm({ onSave: () => {} }));
    act(() => result.current.setNumber(VALID.numberDigits));
    act(() => result.current.reset());
    expect(result.current.draft.numberDigits).toBe('');
    expect(result.current.submitAttempted).toBe(false);
  });
});
