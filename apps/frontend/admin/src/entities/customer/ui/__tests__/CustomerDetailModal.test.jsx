/**
 * Regression tests for <CustomerDetailModal> — the customer detail page surface
 * (FA-402).
 *
 * The modal is the only customer-detail UI today (the /admin/customers page
 * opens it on row click). Tests exercise the full hook → query → render path:
 * spyOn the customers API module, wrap in a real QueryClient via
 * createWrapper, render the modal, observe DOM.
 *
 * Acceptance per FA-402:
 *   - render gates: open=false / identityId=null → no fetch, nothing rendered
 *   - loading state: skeleton placeholders during pending fetch
 *   - successful render: response shape regression guard at the UI layer
 *   - error states: known code mapped to Russian, unknown code falls back
 *     to err.message, missing both falls back to fixed string
 *
 * Consciously NOT covered here:
 *   - Deactivate/reactivate UI flow (button states, reason validation,
 *     mutation success/error). Out of FA-402 scope per the briefing —
 *     possible follow-up FA-402b "customer status change UI".
 *   - Hook-level cache and shape normalization — see queries.test.jsx.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/shared/api/clientFetch';
import { createWrapper } from '@/shared/query';

import * as customersApi from '../../api/customers';
import { CustomerDetailModal } from '../CustomerDetailModal';

const FULL_DETAIL = {
  id: 'c1',
  email: 'anna.ivanova@example.com',
  username: 'anna_iv',
  firstName: 'Анна',
  lastName: 'Иванова',
  phone: '+7 999 123-45-67',
  authType: 'LOCAL',
  authMethods: ['email_password', 'telegram'],
  isActive: true,
  createdAt: '2026-01-15T10:30:00Z',
  roles: [
    { id: 'r1', name: 'customer' },
    { id: 'r2', name: 'vip' },
  ],
};

const MINIMAL_DETAIL = {
  id: 'c2',
  email: 'minimal@example.com',
  isActive: true,
  roles: [],
};

const INACTIVE_DETAIL = {
  ...MINIMAL_DETAIL,
  id: 'c3',
  isActive: false,
  deactivatedAt: '2026-03-01T12:00:00Z',
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
  return { ...result, client, onClose, onUpdate };
}

beforeEach(() => {
  vi.spyOn(customersApi, 'fetchCustomer');
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('render gates', () => {
  it('renders nothing when open is false', () => {
    customersApi.fetchCustomer.mockResolvedValue(FULL_DETAIL);
    const { container } = renderModal({ open: false });
    expect(container).toBeEmptyDOMElement();
  });

  it('does not fetch when open is false even with a valid identityId', () => {
    customersApi.fetchCustomer.mockResolvedValue(FULL_DETAIL);
    renderModal({ open: false });
    expect(customersApi.fetchCustomer).not.toHaveBeenCalled();
  });

  it('does not fetch when identityId is null', () => {
    customersApi.fetchCustomer.mockResolvedValue(FULL_DETAIL);
    renderModal({ identityId: null });
    expect(customersApi.fetchCustomer).not.toHaveBeenCalled();
  });
});

describe('loading state', () => {
  it('shows skeleton placeholders while the detail is pending', async () => {
    // Promise that never resolves keeps the query in pending state.
    customersApi.fetchCustomer.mockImplementation(() => new Promise(() => {}));
    const { container } = renderModal();
    expect(customersApi.fetchCustomer).toHaveBeenCalledWith('c1');
    // The skeletonRow class is the unique loading indicator shape.
    await waitFor(() => {
      expect(container.querySelectorAll('[class*="skeletonRow"]').length).toBe(
        3,
      );
    });
  });
});

describe('successful detail render (response shape regression guard)', () => {
  it('renders core fields: email, full name, status, registration date', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(FULL_DETAIL);
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('anna.ivanova@example.com')).toBeInTheDocument(),
    );
    expect(screen.getByText('Анна Иванова')).toBeInTheDocument();
    expect(screen.getByText('Активен')).toBeInTheDocument();
    expect(screen.getByText('Дата регистрации')).toBeInTheDocument();
  });

  it('renders all optional fields when present', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(FULL_DETAIL);
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('@anna_iv')).toBeInTheDocument(),
    );
    expect(screen.getByText('+7 999 123-45-67')).toBeInTheDocument();
    expect(screen.getByText('Email + пароль')).toBeInTheDocument();
    expect(screen.getByText('Email + пароль, Telegram')).toBeInTheDocument();
  });

  it('omits all optional fields when the response is minimal', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(MINIMAL_DETAIL);
    renderModal({ identityId: 'c2' });
    await waitFor(() =>
      expect(screen.getByText('minimal@example.com')).toBeInTheDocument(),
    );
    expect(screen.queryByText('Username')).not.toBeInTheDocument();
    expect(screen.queryByText('Телефон')).not.toBeInTheDocument();
    expect(screen.queryByText('Тип аккаунта')).not.toBeInTheDocument();
    expect(screen.queryByText('Способы входа')).not.toBeInTheDocument();
    expect(screen.queryByText('Роли')).not.toBeInTheDocument();
  });

  it('renders the roles section only when roles is non-empty', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(FULL_DETAIL);
    renderModal();
    await waitFor(() => expect(screen.getByText('Роли')).toBeInTheDocument());
    expect(screen.getByText('customer')).toBeInTheDocument();
    expect(screen.getByText('vip')).toBeInTheDocument();
  });

  it('renders deactivatedAt only when the user is inactive', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce(INACTIVE_DETAIL);
    renderModal({ identityId: 'c3' });
    await waitFor(() =>
      expect(screen.getByText('Неактивен')).toBeInTheDocument(),
    );
    expect(screen.getByText('Деактивирован')).toBeInTheDocument();
  });

  it('hides deactivatedAt when the user is active even if the field is present', async () => {
    customersApi.fetchCustomer.mockResolvedValueOnce({
      ...FULL_DETAIL,
      deactivatedAt: '2025-12-01T00:00:00Z',
    });
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Активен')).toBeInTheDocument(),
    );
    expect(screen.queryByText('Деактивирован')).not.toBeInTheDocument();
  });
});

describe('error states', () => {
  it('maps the known IDENTITY_NOT_FOUND code to its Russian label', async () => {
    customersApi.fetchCustomer.mockRejectedValueOnce(
      new ApiError({
        message: 'Identity not found',
        code: 'IDENTITY_NOT_FOUND',
        status: 404,
      }),
    );
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Пользователь не найден')).toBeInTheDocument(),
    );
  });

  it('maps the known INSUFFICIENT_PERMISSIONS code (used for 401/403) to its Russian label', async () => {
    customersApi.fetchCustomer.mockRejectedValueOnce(
      new ApiError({
        message: 'Forbidden',
        code: 'INSUFFICIENT_PERMISSIONS',
        status: 401,
      }),
    );
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Недостаточно прав')).toBeInTheDocument(),
    );
  });

  it('falls back to err.message when the code is unknown (e.g. 500)', async () => {
    customersApi.fetchCustomer.mockRejectedValueOnce(
      new ApiError({
        message: 'Сервер недоступен',
        code: 'SOMETHING_WEIRD',
        status: 500,
      }),
    );
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Сервер недоступен')).toBeInTheDocument(),
    );
  });

  it('falls back to the fixed string when both code and message are missing', async () => {
    customersApi.fetchCustomer.mockRejectedValueOnce({});
    renderModal();
    await waitFor(() =>
      expect(screen.getByText('Не удалось загрузить')).toBeInTheDocument(),
    );
  });
});
