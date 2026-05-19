import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Mock the entity so the hook stays unit-testable without spinning up a
// full Redux store + RTKQ middleware.
let mockTrigger;
let mockState;

vi.mock('@/entities/passport', () => ({
  useCreatePassportMutation: () => [mockTrigger, mockState],
}));

import { usePassportForm } from '../model/usePassportForm';

const VALID_DRAFT = Object.freeze({
  fullNameRu: 'Иванов Иван Иванович',
  fullNameLat: 'Ivanov Ivan Ivanovich',
  passportSerial: '1234',
  passportNumber: '567890',
  passportIssueDate: '20.06.2015',
  birthDate: '12.03.1990',
  inn: '500100732259',
});

function fillValid(result) {
  act(() => {
    result.current.setFullNameRu(VALID_DRAFT.fullNameRu);
    result.current.setFullNameLat(VALID_DRAFT.fullNameLat);
    result.current.setPassportSerial(VALID_DRAFT.passportSerial);
    result.current.setPassportNumber(VALID_DRAFT.passportNumber);
    result.current.setIssueDate(VALID_DRAFT.passportIssueDate);
    result.current.setBirthDate(VALID_DRAFT.birthDate);
    result.current.setInn(VALID_DRAFT.inn);
  });
}

beforeEach(() => {
  mockTrigger = vi.fn();
  mockState = { isLoading: false };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('usePassportForm', () => {
  it('submit() calls onSuccess with passportId on 201', async () => {
    mockTrigger.mockReturnValueOnce({
      unwrap: () => Promise.resolve({ passportId: 'p-1' }),
    });
    const onSuccess = vi.fn();
    const { result } = renderHook(() => usePassportForm({ onSuccess }));
    fillValid(result);

    let outcome;
    await act(async () => {
      outcome = await result.current.submit();
    });

    expect(outcome).toEqual({ ok: true, passportId: 'p-1' });
    expect(onSuccess).toHaveBeenCalledWith('p-1');
    expect(result.current.submitError).toBeNull();
  });

  it('submit() short-circuits with validation errors when draft is invalid', async () => {
    const onSuccess = vi.fn();
    const { result } = renderHook(() => usePassportForm({ onSuccess }));
    // Skip fillValid — keep the empty draft so validation fails.

    let outcome;
    await act(async () => {
      outcome = await result.current.submit();
    });

    expect(outcome.ok).toBe(false);
    expect(Object.keys(outcome.errors).length).toBeGreaterThan(0);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(mockTrigger).not.toHaveBeenCalled();
  });

  it('submit() surfaces the envelope code on backend failure (does NOT call onSuccess)', async () => {
    mockTrigger.mockReturnValueOnce({
      unwrap: () =>
        Promise.reject({
          status: 422,
          data: { error: { code: 'PASSPORT_DUPLICATE', message: 'Уже зарегистрирован' } },
        }),
    });
    const onSuccess = vi.fn();
    const { result } = renderHook(() => usePassportForm({ onSuccess }));
    fillValid(result);

    let outcome;
    await act(async () => {
      outcome = await result.current.submit();
    });

    expect(outcome.ok).toBe(false);
    expect(outcome.error?.code).toBe('PASSPORT_DUPLICATE');
    expect(onSuccess).not.toHaveBeenCalled();
    expect(result.current.submitError?.code).toBe('PASSPORT_DUPLICATE');
  });

  it('submit() handles a 201 with missing passportId as a soft failure', async () => {
    mockTrigger.mockReturnValueOnce({
      unwrap: () => Promise.resolve({}), // backend returned 201 but no id
    });
    const onSuccess = vi.fn();
    const { result } = renderHook(() => usePassportForm({ onSuccess }));
    fillValid(result);

    let outcome;
    await act(async () => {
      outcome = await result.current.submit();
    });

    expect(outcome.ok).toBe(false);
    expect(outcome.error?.code).toBe('PASSPORT_CREATE_FAILED');
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('reset() clears the draft and submitAttempted flag', () => {
    const { result } = renderHook(() => usePassportForm());
    fillValid(result);
    expect(result.current.draft.passportSerial).toBe('1234');

    act(() => {
      result.current.reset();
    });

    expect(result.current.draft.passportSerial).toBe('');
    expect(result.current.submitAttempted).toBe(false);
    expect(result.current.errors).toEqual({});
  });
});
