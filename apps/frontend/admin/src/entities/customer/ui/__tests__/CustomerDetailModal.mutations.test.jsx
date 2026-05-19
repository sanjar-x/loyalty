/**
 * Regression tests for the deactivate / reactivate flows in <CustomerDetailModal>
 * (FA-402b). Companion to CustomerDetailModal.test.jsx (FA-402), which covers
 * read/render flows. Same mock strategy: spyOn the customers API module +
 * createWrapper(); the modal exercises real hooks against a real QueryClient.
 *
 * Acceptance per FA-402b:
 *   - Active user surface: deactivate button only, confirm-then-reason flow,
 *     button disabled while reason is empty/whitespace, trimmed-reason submit
 *     calls deactivateCustomer and onUpdate, error codes mapped to Russian.
 *   - Inactive user surface: reactivate button only, single-click mutate,
 *     onUpdate on success, error codes mapped to Russian.
 *   - Reason validation boundary: maxLength attribute, identityId-change reset.
 *   - Cache invalidation: successful deactivate refetches the customer detail.
 *
 * Combined error-code coverage across FA-402 + FA-402b = 5/5 mapped codes
 * (IDENTITY_NOT_FOUND, INSUFFICIENT_PERMISSIONS — FA-402;
 * IDENTITY_ALREADY_DEACTIVATED, SELF_DEACTIVATION_FORBIDDEN, VALIDATION_ERROR
 * — FA-402b) plus 3 fallbacks (load / deactivate / reactivate).
 *
 * Consciously NOT covered here:
 *   - Reason counter UI text update on typing — cosmetic, low regression value.
 *   - Button label text during pending mutation ("Деактивация…",
 *     "Реактивация…") — derived from mutation.isPending, structurally implicit.
 *   - Cache namespace isolation — covered by useCustomers test in FA-402
 *     queries.test.jsx.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/shared/api/clientFetch';
import { createWrapper } from '@/shared/query';

import * as customersApi from '../../api/customers';
import { CustomerDetailModal } from '../CustomerDetailModal';

const ACTIVE_DETAIL = {
  id: 'c1',
  email: 'active@example.com',
  firstName: 'Анна',
  lastName: 'Иванова',
  isActive: true,
  roles: [],
  createdAt: '2026-01-15T10:30:00Z',
};

const INACTIVE_DETAIL = {
  id: 'c2',
  email: 'inactive@example.com',
  firstName: 'Иван',
  lastName: 'Петров',
  isActive: false,
  deactivatedAt: '2026-03-01T12:00:00Z',
  roles: [],
};

function renderModal({
  identityId = 'c1',
  open = true,
  onClose = vi.fn(),
  onUpdate = vi.fn(),
} = {}) {
  const { Wrapper, client } = createWrapper();
  const result = render(
    <CustomerDetailModal
      identityId={identityId}
      open={open}
      onClose={onClose}
      onUpdate={onUpdate}
    />,
    { wrapper: Wrapper },
  );
  return { ...result, Wrapper, client, onClose, onUpdate };
}

beforeEach(() => {
  vi.spyOn(customersApi, 'fetchCustomer');
  vi.spyOn(customersApi, 'deactivateCustomer');
  vi.spyOn(customersApi, 'reactivateCustomer');
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Active user — deactivate flow', () => {
  it('renders the deactivate button and not the reactivate button', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(ACTIVE_DETAIL);
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );
    expect(
      screen.getByRole('button', { name: 'Деактивировать' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Реактивировать' }),
    ).not.toBeInTheDocument();
  });

  it('first click reveals the reason textarea without firing the mutation', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(ACTIVE_DETAIL);
    const user = userEvent.setup();
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));

    expect(screen.getByPlaceholderText(/Например/)).toBeInTheDocument();
    expect(customersApi.deactivateCustomer).not.toHaveBeenCalled();
  });

  it('keeps the confirm button disabled while reason is empty', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(ACTIVE_DETAIL);
    const user = userEvent.setup();
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));

    const confirmBtn = screen.getByRole('button', {
      name: 'Подтвердить деактивацию',
    });
    expect(confirmBtn).toBeDisabled();
    await user.click(confirmBtn);
    expect(customersApi.deactivateCustomer).not.toHaveBeenCalled();
  });

  it('keeps the confirm button disabled when reason is whitespace-only', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(ACTIVE_DETAIL);
    const user = userEvent.setup();
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));
    await user.type(screen.getByPlaceholderText(/Например/), '   ');

    expect(
      screen.getByRole('button', { name: 'Подтвердить деактивацию' }),
    ).toBeDisabled();
  });

  it('submits with the trimmed reason and calls onUpdate on success', async () => {
    customersApi.fetchCustomer.mockResolvedValue(ACTIVE_DETAIL);
    customersApi.deactivateCustomer.mockResolvedValueOnce({});
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    renderModal({ onUpdate });
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));
    await user.type(
      screen.getByPlaceholderText(/Например/),
      '  Spam account  ',
    );
    await user.click(
      screen.getByRole('button', { name: 'Подтвердить деактивацию' }),
    );

    await waitFor(() =>
      expect(customersApi.deactivateCustomer).toHaveBeenCalledWith(
        'c1',
        'Spam account',
      ),
    );
    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
  });

  const deactivateMappedCodes = [
    {
      code: 'IDENTITY_ALREADY_DEACTIVATED',
      expected: 'Аккаунт уже деактивирован',
    },
    {
      code: 'SELF_DEACTIVATION_FORBIDDEN',
      expected: 'Нельзя деактивировать свой аккаунт',
    },
  ];

  it.each(deactivateMappedCodes)(
    'maps the deactivate error code "$code" to its Russian label',
    async ({ code, expected }) => {
      customersApi.fetchCustomer.mockResolvedValue(ACTIVE_DETAIL);
      customersApi.deactivateCustomer.mockRejectedValueOnce(
        new ApiError({ message: 'Server message', code, status: 400 }),
      );
      const user = userEvent.setup();
      renderModal();
      await waitFor(() =>
        expect(screen.getByText('Активен')).toBeInTheDocument(),
      );

      await user.click(screen.getByRole('button', { name: 'Деактивировать' }));
      await user.type(screen.getByPlaceholderText(/Например/), 'Reason');
      await user.click(
        screen.getByRole('button', { name: 'Подтвердить деактивацию' }),
      );

      await waitFor(() =>
        expect(screen.getByText(expected)).toBeInTheDocument(),
      );
    },
  );

  it('falls back to "Не удалось деактивировать" for an unknown error code with no message', async () => {
    customersApi.fetchCustomer.mockResolvedValue(ACTIVE_DETAIL);
    // describeError uses `??` (nullish coalescing): an empty-string message
    // would short-circuit the fallback. Plain object with code-only is the
    // canonical "unknown code, no message" shape.
    customersApi.deactivateCustomer.mockRejectedValueOnce({
      code: 'SOMETHING_UNKNOWN',
    });
    const user = userEvent.setup();
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));
    await user.type(screen.getByPlaceholderText(/Например/), 'Reason');
    await user.click(
      screen.getByRole('button', { name: 'Подтвердить деактивацию' }),
    );

    await waitFor(() =>
      expect(screen.getByText('Не удалось деактивировать')).toBeInTheDocument(),
    );
  });
});

describe('Inactive user — reactivate flow', () => {
  it('renders the reactivate button and not the deactivate button', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(INACTIVE_DETAIL);
    renderModal({ identityId: 'c2' });
    await waitFor(() =>
      expect(screen.getByText('Неактивен')).toBeInTheDocument(),
    );
    expect(
      screen.getByRole('button', { name: 'Реактивировать' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Деактивировать' }),
    ).not.toBeInTheDocument();
  });

  it('click invokes reactivateCustomer (no reason arg) and calls onUpdate on success', async () => {
    customersApi.fetchCustomer.mockResolvedValue(INACTIVE_DETAIL);
    customersApi.reactivateCustomer.mockResolvedValueOnce({});
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    renderModal({ identityId: 'c2', onUpdate });
    await waitFor(() =>
      expect(screen.getByText('Неактивен')).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Реактивировать' }));

    await waitFor(() =>
      expect(customersApi.reactivateCustomer).toHaveBeenCalledWith('c2'),
    );
    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
  });

  it('maps the reactivate error code "VALIDATION_ERROR" to its Russian label', async () => {
    customersApi.fetchCustomer.mockResolvedValue(INACTIVE_DETAIL);
    customersApi.reactivateCustomer.mockRejectedValueOnce(
      new ApiError({
        message: 'Validation failed',
        code: 'VALIDATION_ERROR',
        status: 400,
      }),
    );
    const user = userEvent.setup();
    renderModal({ identityId: 'c2' });
    await waitFor(() =>
      expect(screen.getByText('Неактивен')).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Реактивировать' }));

    await waitFor(() =>
      expect(
        screen.getByText('Проверьте введённые данные'),
      ).toBeInTheDocument(),
    );
  });

  it('falls back to "Не удалось реактивировать" for an unknown error code with no message', async () => {
    customersApi.fetchCustomer.mockResolvedValue(INACTIVE_DETAIL);
    customersApi.reactivateCustomer.mockRejectedValueOnce({
      code: 'SOMETHING_UNKNOWN',
    });
    const user = userEvent.setup();
    renderModal({ identityId: 'c2' });
    await waitFor(() =>
      expect(screen.getByText('Неактивен')).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Реактивировать' }));

    await waitFor(() =>
      expect(screen.getByText('Не удалось реактивировать')).toBeInTheDocument(),
    );
  });
});

describe('Reason validation boundary', () => {
  it('caps reason input at 200 characters via the maxLength attribute', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(ACTIVE_DETAIL);
    const user = userEvent.setup();
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));
    expect(screen.getByPlaceholderText(/Например/)).toHaveAttribute(
      'maxlength',
      '200',
    );
  });

  it('resets confirm and reason state when identityId changes', async () => {
    customersApi.fetchCustomer
      .mockResolvedValueOnce({ ...ACTIVE_DETAIL, email: 'first@example.com' })
      .mockResolvedValueOnce({
        ...ACTIVE_DETAIL,
        id: 'c2',
        email: 'second@example.com',
      });

    const { Wrapper } = createWrapper();
    const user = userEvent.setup();
    const { rerender } = render(
      <CustomerDetailModal
        identityId="c1"
        open={true}
        onClose={vi.fn()}
        onUpdate={vi.fn()}
      />,
      { wrapper: Wrapper },
    );
    await waitFor(() =>
      expect(screen.getByText('first@example.com')).toBeInTheDocument(),
    );

    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));
    expect(screen.getByPlaceholderText(/Например/)).toBeInTheDocument();

    rerender(
      <CustomerDetailModal
        identityId="c2"
        open={true}
        onClose={vi.fn()}
        onUpdate={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(screen.getByText('second@example.com')).toBeInTheDocument(),
    );

    expect(screen.queryByPlaceholderText(/Например/)).not.toBeInTheDocument();
  });
});

describe('Cache invalidation', () => {
  it('refetches the customer detail after a successful deactivate', async () => {
    customersApi.fetchCustomer
      .mockResolvedValueOnce(ACTIVE_DETAIL)
      .mockResolvedValueOnce({ ...ACTIVE_DETAIL, isActive: false });
    customersApi.deactivateCustomer.mockResolvedValueOnce({});
    const user = userEvent.setup();
    renderModal();

    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );
    expect(customersApi.fetchCustomer).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'Деактивировать' }));
    await user.type(screen.getByPlaceholderText(/Например/), 'Reason');
    await user.click(
      screen.getByRole('button', { name: 'Подтвердить деактивацию' }),
    );

    await waitFor(() =>
      expect(customersApi.deactivateCustomer).toHaveBeenCalledWith(
        'c1',
        'Reason',
      ),
    );

    // useCustomer query invalidated → refetch
    await waitFor(() =>
      expect(customersApi.fetchCustomer).toHaveBeenCalledTimes(2),
    );
  });
});
