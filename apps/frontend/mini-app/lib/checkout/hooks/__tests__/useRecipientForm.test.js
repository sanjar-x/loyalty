import { describe, it, expect, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useRecipientForm } from '../useRecipientForm';

describe('useRecipientForm (CHK-020)', () => {
  const VALID = {
    fullName: 'Иван Петров',
    phoneDigits: '9990001122',
    email: 'ivan@example.ru',
    country: 'RU',
  };

  it('defaults to empty draft when no initialValue', () => {
    const { result } = renderHook(() => useRecipientForm({ initialValue: null, onSave: () => {} }));
    expect(result.current.draft).toEqual({
      fullName: '',
      phoneDigits: '',
      email: '',
      country: 'RU',
    });
    expect(result.current.submitAttempted).toBe(false);
    expect(result.current.errors).toEqual({});
  });

  it('hydrates from initialValue', () => {
    const { result } = renderHook(() =>
      useRecipientForm({ initialValue: VALID, onSave: () => {} })
    );
    expect(result.current.draft).toEqual(VALID);
  });

  it('setField updates draft', () => {
    const { result } = renderHook(() => useRecipientForm({ initialValue: null, onSave: () => {} }));
    act(() => result.current.setField('fullName', 'Анна Иванова'));
    expect(result.current.draft.fullName).toBe('Анна Иванова');
  });

  it('errors stays empty until submit attempted (CHK-020 quiet entry)', () => {
    const { result } = renderHook(() => useRecipientForm({ initialValue: null, onSave: () => {} }));
    act(() => result.current.setField('email', 'bad-email'));
    expect(result.current.errors).toEqual({});
  });

  it('handleSubmit returns false and exposes errors on invalid draft', () => {
    const onSave = vi.fn();
    const { result } = renderHook(() => useRecipientForm({ initialValue: null, onSave }));
    let ok;
    act(() => {
      ok = result.current.handleSubmit();
    });
    expect(ok).toBe(false);
    expect(onSave).not.toHaveBeenCalled();
    expect(Object.keys(result.current.errors).length).toBeGreaterThan(0);
  });

  it('handleSubmit succeeds and calls onSave with normalized payload', () => {
    const onSave = vi.fn();
    const { result } = renderHook(() => useRecipientForm({ initialValue: VALID, onSave }));
    let ok;
    act(() => {
      ok = result.current.handleSubmit();
    });
    expect(ok).toBe(true);
    expect(onSave).toHaveBeenCalledWith({
      fullName: 'Иван Петров',
      phoneDigits: '9990001122',
      email: 'ivan@example.ru',
      country: 'RU',
    });
  });

  it('reset clears draft and submitAttempted', () => {
    const { result } = renderHook(() =>
      useRecipientForm({ initialValue: VALID, onSave: () => {} })
    );
    act(() => result.current.handleSubmit());
    act(() => result.current.reset(null));
    expect(result.current.draft.fullName).toBe('');
    expect(result.current.submitAttempted).toBe(false);
  });

  it('country switch propagates to draft', () => {
    const { result } = renderHook(() =>
      useRecipientForm({ initialValue: VALID, onSave: () => {} })
    );
    act(() => result.current.setField('country', 'UZ'));
    expect(result.current.draft.country).toBe('UZ');
  });
});
