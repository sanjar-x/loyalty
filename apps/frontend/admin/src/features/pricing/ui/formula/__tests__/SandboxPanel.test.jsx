/**
 * Regression tests for the pricing preview sandbox UI (FA-404).
 *
 * Surface: <SandboxPanel> at src/features/pricing/ui/formula/SandboxPanel.jsx.
 * The panel is the admin-side dry-run for the pricing engine: enter
 * Product/Category/Supplier IDs, watch the formula compute final price +
 * decomposition, with a 500ms debounce on input changes and a manual
 * "Пересчитать" button.
 *
 * Mock strategy:
 *   - vi.mock the PricingPageProvider module — usePricingPage returns only
 *     {contextId} for this consumer; mocking the provider isolates the panel
 *     from next/navigation infrastructure.
 *   - vi.spyOn(formulasApi, 'previewPrice') — same namespace-import pattern
 *     established in FA-401/407/402/402b.
 *   - Real timers throughout. RTL's `waitFor` polls via `setTimeout`, which
 *     `vi.useFakeTimers()` would freeze — leaving every result-rendering
 *     test stuck at the 5s default timeout. Real timers cost ~600ms per
 *     debounced test and let `waitFor` work out of the box. Net file
 *     runtime stays under 10s. fireEvent.change is used for inputs to
 *     avoid the userEvent setTimeout chain altogether.
 *
 * REC-014 (closed): the original FA-404 surface read err.data.error.message
 * first, with err.message as fallback. That deep-envelope branch was dead
 * code (apiClient always throws a flat ApiError). REC-014 simplified the
 * parse to err?.message || 'Ошибка расчёта' — the deep-envelope test that
 * fixated the safety-net contract was removed alongside the dead branch.
 *
 * Consciously NOT covered:
 *   - formatCurrency precision/format — covered by shared/lib/__tests__/utils.test.js.
 *   - PricingPageProvider's own behavior (next/navigation integration) —
 *     provider concern, mocked here.
 *   - Backend response contract validation — backend's own tests own that.
 *   - <SandboxField> sub-component independent rendering — exercised
 *     through panel tests.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/shared/api/clientFetch';

import * as formulasApi from '../../../api/formulas';
import { usePricingPage } from '../../../model/PricingPageProvider';
import { SandboxPanel } from '../SandboxPanel';

vi.mock('../../../model/PricingPageProvider', () => ({
  usePricingPage: vi.fn(),
}));

const SUCCESS_RESULT = {
  finalPrice: 1000,
  formulaVersionNumber: 5,
  formulaVersionId: 'abcdef1234567890',
  components: {
    cogs: 600,
    shipping: 100,
    margin: 300,
    final_price: 1000,
  },
};

// Use REAL timers throughout. Initial draft used vi.useFakeTimers() for the
// 500ms debounce, but RTL's `waitFor` polls via setTimeout, which fake timers
// freeze — that left every result-rendering test stuck at the 5s default
// timeout. Real timers cost ~600ms per debounced test and let waitFor work
// out of the box. Net file runtime stays under 10s.
beforeEach(() => {
  usePricingPage.mockReturnValue({ contextId: 'ctx-1' });
  vi.spyOn(formulasApi, 'previewPrice');
});

afterEach(() => {
  vi.restoreAllMocks();
});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const DEBOUNCE_MS = 500;
const FLUSH_TIMEOUT = 1500; // generous: 500ms debounce + render + RTL polling

const productInput = () => screen.getByPlaceholderText(/UUID продукта/);
const categoryInput = () => screen.getByPlaceholderText(/UUID категории/);
const supplierInput = () => screen.getByPlaceholderText(/UUID поставщика/);

function fillRequired() {
  fireEvent.change(productInput(), { target: { value: 'pid' } });
  fireEvent.change(categoryInput(), { target: { value: 'cid' } });
}

describe('canPreview gating', () => {
  it('shows the hint and does not fetch when inputs are empty', () => {
    render(<SandboxPanel />);
    expect(
      screen.getByText(/Заполните Product ID и Category ID/),
    ).toBeInTheDocument();
    expect(formulasApi.previewPrice).not.toHaveBeenCalled();
  });

  it('does not fetch when categoryId is missing', async () => {
    render(<SandboxPanel />);
    fireEvent.change(productInput(), { target: { value: 'pid' } });
    // Wait past the debounce window — must remain not-fetched.
    await sleep(DEBOUNCE_MS + 100);
    expect(formulasApi.previewPrice).not.toHaveBeenCalled();
    expect(
      screen.getByText(/Заполните Product ID и Category ID/),
    ).toBeInTheDocument();
  });

  it('does not fetch when contextId is missing from the provider', async () => {
    usePricingPage.mockReturnValue({ contextId: null });
    render(<SandboxPanel />);
    fillRequired();
    await sleep(DEBOUNCE_MS + 100);
    expect(formulasApi.previewPrice).not.toHaveBeenCalled();
  });
});

describe('debounce (500ms)', () => {
  it('fires the fetch 500ms after the last input change', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();

    expect(formulasApi.previewPrice).not.toHaveBeenCalled();
    await waitFor(
      () => expect(formulasApi.previewPrice).toHaveBeenCalledTimes(1),
      { timeout: FLUSH_TIMEOUT },
    );
  });

  it('coalesces rapid successive input changes into a single fetch', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce(SUCCESS_RESULT);
    render(<SandboxPanel />);

    fireEvent.change(productInput(), { target: { value: 'p1' } });
    fireEvent.change(productInput(), { target: { value: 'p2' } });
    fireEvent.change(productInput(), { target: { value: 'p3' } });
    fireEvent.change(categoryInput(), { target: { value: 'c1' } });

    // Advance only partway — no fire yet.
    await sleep(400);
    expect(formulasApi.previewPrice).not.toHaveBeenCalled();

    // Wait past the remaining debounce + buffer — exactly one fire from
    // the last scheduled timer (the prior three were cleared).
    await waitFor(
      () => expect(formulasApi.previewPrice).toHaveBeenCalledTimes(1),
      { timeout: FLUSH_TIMEOUT },
    );
  });

  it('debounces a subsequent input change after an initial fetch', async () => {
    formulasApi.previewPrice.mockResolvedValue(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();
    await waitFor(
      () => expect(formulasApi.previewPrice).toHaveBeenCalledTimes(1),
      { timeout: FLUSH_TIMEOUT },
    );

    fireEvent.change(supplierInput(), { target: { value: 'sup' } });
    await sleep(400);
    expect(formulasApi.previewPrice).toHaveBeenCalledTimes(1);

    await waitFor(
      () => expect(formulasApi.previewPrice).toHaveBeenCalledTimes(2),
      { timeout: FLUSH_TIMEOUT },
    );
  });
});

describe('successful render', () => {
  it('renders finalPrice via formatCurrency and the formula version stripe', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(
      () => expect(screen.getByText(/1\s+000\s+₽/)).toBeInTheDocument(),
      { timeout: FLUSH_TIMEOUT },
    );
    expect(screen.getByText('v5')).toBeInTheDocument();
    expect(screen.getByText(/abcdef12/)).toBeInTheDocument();
  });

  it('renders the decomposition with non-final_price components and their percent share', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(
      () => expect(screen.getByText('Декомпозиция')).toBeInTheDocument(),
      { timeout: FLUSH_TIMEOUT },
    );
    expect(screen.getByText(/Себестоимость/)).toBeInTheDocument();
    expect(screen.getByText('Доставка')).toBeInTheDocument();
    expect(screen.getByText('60.0%')).toBeInTheDocument(); // cogs/finalPrice
    expect(screen.getByText('10.0%')).toBeInTheDocument(); // shipping/finalPrice
    // final_price COMPONENT should be filtered out of the decomposition
    expect(screen.queryByText('Итоговая цена')).not.toBeInTheDocument();
  });

  it('shows the margin percent badge when components.margin is present', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();

    // margin=300, finalPrice=1000, d=700 → 300/700*100 = 42.9% (margin badge formula)
    await waitFor(() => expect(screen.getByText('42.9%')).toBeInTheDocument(), {
      timeout: FLUSH_TIMEOUT,
    });
  });

  it('shows "—" instead of the margin percent when finalPrice equals margin (zero divisor guard)', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce({
      finalPrice: 300,
      formulaVersionNumber: 5,
      formulaVersionId: 'abcdef1234567890',
      components: { margin: 300 },
    });
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(() => expect(screen.getByText('—')).toBeInTheDocument(), {
      timeout: FLUSH_TIMEOUT,
    });
  });

  it('displays the elapsed time in the header after a successful fetch', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(() => expect(screen.getByText(/мс$/)).toBeInTheDocument(), {
      timeout: FLUSH_TIMEOUT,
    });
  });
});

describe('error states', () => {
  it('renders ApiError.message when thrown by apiClient (canonical production path)', async () => {
    formulasApi.previewPrice.mockRejectedValueOnce(
      new ApiError({
        message: 'Не хватает данных по продукту',
        code: 'INSUFFICIENT_DATA',
        status: 400,
      }),
    );
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(
      () =>
        expect(
          screen.getByText('Не хватает данных по продукту'),
        ).toBeInTheDocument(),
      { timeout: FLUSH_TIMEOUT },
    );
  });

  it('falls back to "Ошибка расчёта" when err.message is missing or empty', async () => {
    formulasApi.previewPrice.mockRejectedValueOnce({});
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(
      () => expect(screen.getByText('Ошибка расчёта')).toBeInTheDocument(),
      { timeout: FLUSH_TIMEOUT },
    );
  });
});

describe('manual recalc + supplier optional', () => {
  it('manual "Пересчитать" click fires the fetch immediately, before the debounce timer elapses', async () => {
    formulasApi.previewPrice.mockResolvedValue(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();

    // Do NOT advance timers — click button immediately.
    const button = screen.getByRole('button', { name: 'Пересчитать' });
    fireEvent.click(button);

    await waitFor(() =>
      expect(formulasApi.previewPrice).toHaveBeenCalledTimes(1),
    );
  });

  it('omits supplierId from the previewPrice call when the supplier input is empty', async () => {
    formulasApi.previewPrice.mockResolvedValueOnce(SUCCESS_RESULT);
    render(<SandboxPanel />);
    fillRequired();
    // supplier left empty

    await waitFor(() => expect(formulasApi.previewPrice).toHaveBeenCalled(), {
      timeout: FLUSH_TIMEOUT,
    });
    expect(formulasApi.previewPrice).toHaveBeenCalledWith({
      productId: 'pid',
      categoryId: 'cid',
      contextId: 'ctx-1',
      supplierId: undefined,
    });
  });
});

describe('loading state', () => {
  it('shows the spinner during a pending fetch and disables the recalc button', async () => {
    let resolvePreview;
    formulasApi.previewPrice.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePreview = resolve;
        }),
    );
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(
      () => expect(screen.getByText(/Расчёт/)).toBeInTheDocument(),
      { timeout: FLUSH_TIMEOUT },
    );
    expect(screen.getByRole('button', { name: 'Пересчитать' })).toBeDisabled();

    // Cleanly resolve so React can finish unmounting between tests.
    resolvePreview(SUCCESS_RESULT);
  });
});

describe('ARIA accessibility (FA-406)', () => {
  it('binds each SandboxField label to its input via wrapping <label>', () => {
    render(<SandboxPanel />);
    expect(screen.getByLabelText('Product ID')).toBeInTheDocument();
    expect(screen.getByLabelText('Category ID')).toBeInTheDocument();
    expect(screen.getByLabelText('Supplier ID')).toBeInTheDocument();
  });

  it('marks the loading region as role="status" with aria-live="polite"', async () => {
    let resolvePreview;
    formulasApi.previewPrice.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePreview = resolve;
        }),
    );
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(
      () => expect(screen.getByRole('status')).toBeInTheDocument(),
      { timeout: FLUSH_TIMEOUT },
    );
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).toHaveTextContent('Расчёт');

    // Cleanly resolve so React can finish unmounting between tests.
    resolvePreview(SUCCESS_RESULT);
  });

  it('marks the error banner as role="alert"', async () => {
    formulasApi.previewPrice.mockRejectedValueOnce(
      new ApiError({ message: 'Boom', code: 'X', status: 500 }),
    );
    render(<SandboxPanel />);
    fillRequired();

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument(), {
      timeout: FLUSH_TIMEOUT,
    });
    expect(screen.getByRole('alert')).toHaveTextContent('Boom');
  });
});
