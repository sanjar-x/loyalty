/**
 * Audit 1.3 / 4.3 — verify <ApiErrorState> discriminates the four
 * common failure modes (403/404/5xx/other) and surfaces requestId
 * when the error envelope carries one.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ApiErrorState } from '../ApiErrorState';

// Stub next/link so we can render outside a router.
vi.mock('next/link', () => ({
  default: ({ children, href, ...rest }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

describe('<ApiErrorState>', () => {
  it('403 → "Нет доступа", no retry, shows home link', () => {
    render(
      <ApiErrorState
        error={{ status: 403, message: 'Forbidden' }}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText('Нет доступа')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /попробовать/i })).toBeNull();
    expect(
      screen.getByRole('link', { name: /на главную/i }),
    ).toBeInTheDocument();
  });

  it('404 → "Не найдено", no retry, shows home link', () => {
    render(
      <ApiErrorState
        error={{ status: 404 }}
        homeHref="/admin/products"
        homeLabel="Назад к товарам"
      />,
    );
    expect(screen.getByText('Не найдено')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Назад к товарам' }),
    ).toHaveAttribute('href', '/admin/products');
  });

  it('5xx → "Сервер недоступен" + retry button calls onRetry', () => {
    const retry = vi.fn();
    render(
      <ApiErrorState
        error={{ status: 503, message: 'Service unavailable' }}
        onRetry={retry}
      />,
    );
    expect(screen.getByText('Сервер недоступен')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /попробовать/i }));
    expect(retry).toHaveBeenCalledTimes(1);
  });

  it('renders requestId when error.details.requestId is present', () => {
    render(
      <ApiErrorState
        error={{
          status: 500,
          message: 'Boom',
          details: { requestId: 'abc-123' },
        }}
      />,
    );
    expect(screen.getByText(/requestId: abc-123/)).toBeInTheDocument();
  });

  it('falls back to generic title + retry for unknown status', () => {
    const retry = vi.fn();
    render(
      <ApiErrorState
        error={{ status: 0, message: 'Network error' }}
        onRetry={retry}
      />,
    );
    expect(screen.getByText('Ошибка')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /попробовать/i }));
    expect(retry).toHaveBeenCalledTimes(1);
  });
});
