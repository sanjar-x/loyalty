import { describe, it, expect, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useCustomsForm } from '../useCustomsForm';

const VALID = {
  passportSeries: '1234',
  passportNumber: '567890',
  issueDate: '01.06.2015',
  birthDate: '15.01.1990',
  inn: '123456789012',
};

describe('useCustomsForm (CHK-020)', () => {
  it('empty defaults', () => {
    const { result } = renderHook(() => useCustomsForm({ initialValue: null, onSave: () => {} }));
    expect(result.current.draft.passportSeries).toBe('');
    expect(result.current.draft.inn).toBe('');
    expect(result.current.errors).toEqual({});
  });

  it('hydrates from initialValue', () => {
    const { result } = renderHook(() => useCustomsForm({ initialValue: VALID, onSave: () => {} }));
    expect(result.current.draft).toEqual(VALID);
  });

  it('setDigitsField caps at maxLen', () => {
    const { result } = renderHook(() => useCustomsForm({ initialValue: null, onSave: () => {} }));
    act(() => result.current.setDigitsField('inn', '1234567890123456', 12));
    expect(result.current.draft.inn).toBe('123456789012');
  });

  it('setPassportSeriesField normalizes (uppercase, strips punctuation)', () => {
    const { result } = renderHook(() => useCustomsForm({ initialValue: null, onSave: () => {} }));
    act(() => result.current.setPassportSeriesField('12-34 abc'));
    expect(result.current.draft.passportSeries).toBe('1234ABC');
  });

  it('setDateField applies RU mask', () => {
    const { result } = renderHook(() => useCustomsForm({ initialValue: null, onSave: () => {} }));
    act(() => result.current.setDateField('issueDate', '15031990'));
    expect(result.current.draft.issueDate).toBe('15.03.1990');
  });

  it('errors stay empty until submit attempted', () => {
    const { result } = renderHook(() => useCustomsForm({ initialValue: null, onSave: () => {} }));
    expect(result.current.errors).toEqual({});
  });

  it('handleSubmit returns ok:false on invalid', () => {
    const onSave = vi.fn();
    const { result } = renderHook(() => useCustomsForm({ initialValue: null, onSave }));
    let res;
    act(() => {
      res = result.current.handleSubmit();
    });
    expect(res.ok).toBe(false);
    expect(onSave).not.toHaveBeenCalled();
    expect(result.current.errors.passportSeries).toBe('required');
  });

  it('handleSubmit calls onSave with trimmed payload when valid', () => {
    const onSave = vi.fn();
    const { result } = renderHook(() => useCustomsForm({ initialValue: VALID, onSave }));
    let res;
    act(() => {
      res = result.current.handleSubmit();
    });
    expect(res.ok).toBe(true);
    expect(onSave).toHaveBeenCalledWith(VALID);
  });

  it('reset clears draft and submitAttempted', () => {
    const { result } = renderHook(() => useCustomsForm({ initialValue: VALID, onSave: () => {} }));
    act(() => result.current.handleSubmit());
    act(() => result.current.reset(null));
    expect(result.current.draft.inn).toBe('');
    expect(result.current.submitAttempted).toBe(false);
  });
});
