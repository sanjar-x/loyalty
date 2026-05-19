/**
 * Audit 6.1 / 6.2 — verify slug validation surfaces via aria-invalid +
 * role="alert", and the logo-upload status text lives inside an
 * aria-live region so screen readers announce transitions.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrandFormModal } from '../BrandFormModal';

vi.mock('@/entities/brand', () => ({
  useBrand: () => ({ data: null }),
  useCreateBrand: () => ({ mutate: vi.fn(), reset: vi.fn(), isPending: false }),
  useUpdateBrand: () => ({ mutate: vi.fn(), reset: vi.fn(), isPending: false }),
}));

vi.mock('@/entities/product', () => ({
  reserveMediaUpload: vi.fn(),
  uploadToS3: vi.fn(),
  confirmMedia: vi.fn(),
  subscribeMediaStatus: vi.fn(),
}));

function wrap(node) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{node}</QueryClientProvider>;
}

describe('<BrandFormModal> a11y', () => {
  it('slug input is aria-invalid + an alert appears when invalid', () => {
    render(wrap(<BrandFormModal open onClose={vi.fn()} />));

    const slug = screen.getByLabelText('Slug');
    // Initially empty — should not be flagged invalid.
    expect(slug.getAttribute('aria-invalid')).toBeNull();

    fireEvent.change(slug, { target: { value: 'НеЛатиница' } });

    // Whatever the input transforms it to, the value must contain
    // characters outside [a-z0-9-]; the form should flag it.
    fireEvent.change(slug, { target: { value: 'BAD!' } });
    expect(slug).toHaveAttribute('aria-invalid', 'true');
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(/не соответствует шаблону/i);
    expect(slug.getAttribute('aria-describedby')).toContain('brand-slug-error');
  });

  it('slug describedby always includes the static help id', () => {
    render(wrap(<BrandFormModal open onClose={vi.fn()} />));
    const slug = screen.getByLabelText('Slug');
    expect(slug.getAttribute('aria-describedby')).toContain('brand-slug-help');
  });

  it('logo upload status lives inside aria-live="polite"', () => {
    const { container } = render(
      wrap(<BrandFormModal open onClose={vi.fn()} />),
    );
    const live = container.querySelector('[aria-live="polite"]');
    expect(live).not.toBeNull();
    expect(live).toHaveTextContent(/JPG.*PNG.*SVG/i);
    expect(live.getAttribute('aria-atomic')).toBe('true');
  });
});
