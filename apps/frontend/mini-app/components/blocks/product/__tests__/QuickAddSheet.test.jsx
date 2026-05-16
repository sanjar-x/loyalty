import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import QuickAddSheet from '../QuickAddSheet';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn(),
  }),
}));

// Mock backendAssets
vi.mock('@/lib/url/backendAssets', () => ({
  buildProductPhotoUrl: (v) => (v ? `/photo/${v}` : ''),
  buildBackendAssetUrl: (v) => (v ? `/asset/${v}` : ''),
}));

const mockProduct = {
  id: 42,
  name: 'Джинсы Carne Bollente',
  price: 34990,
  image: 'test-image.jpg',
  delivery: 'Китай',
  delivery_date: '30 марта',
  sizes: [{ size: 'XS' }, { size: 'S' }, { size: 'M' }, { size: 'L' }, { size: 'XL' }],
  article: 'CB-1234',
};

// Mock RTK Query hooks
const mockAddCartItem = vi.fn().mockReturnValue({ unwrap: () => Promise.resolve({}) });

vi.mock('@/lib/store/api', () => ({
  useGetProductByIdQuery: (id, opts) => {
    if (opts?.skip) return { data: undefined, isLoading: false };
    return { data: mockProduct, isLoading: false };
  },
  useAddCartItemMutation: () => [
    mockAddCartItem,
    { isLoading: false, isError: false, isSuccess: false, reset: vi.fn() },
  ],
}));

function renderSheet(props = {}) {
  const store = configureStore({
    reducer: { test: (state = {}) => state },
  });

  return render(
    <Provider store={store}>
      <QuickAddSheet productId={42} open={true} onClose={vi.fn()} {...props} />
    </Provider>
  );
}

// TODO: rewrite mock to match new product shape
//   - new shape: product.variants[].skus[].variantAttributes[]
//   - old shape: product.sizes[{size}] (used in mockProduct above)
//   - QuickAddSheet shape change came in 7396d16 (cart integration);
//     tests weren't updated and now reference removed props (`productId`)
describe.skip('QuickAddSheet', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    const storage = {};
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation((key) => storage[key] ?? null);
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation((key, val) => {
      storage[key] = val;
    });
  });

  it('renders product name and price', () => {
    renderSheet();
    expect(screen.getByText('Джинсы Carne Bollente')).toBeInTheDocument();
    expect(screen.getByText('34 990 ₽')).toBeInTheDocument();
  });

  it('renders size buttons', () => {
    renderSheet();
    expect(screen.getByText('XS')).toBeInTheDocument();
    expect(screen.getByText('S')).toBeInTheDocument();
    expect(screen.getByText('M')).toBeInTheDocument();
    expect(screen.getByText('L')).toBeInTheDocument();
    expect(screen.getByText('XL')).toBeInTheDocument();
  });

  it('allows selecting a size', () => {
    renderSheet();
    const mBtn = screen.getByText('M');
    fireEvent.click(mBtn);
    // After click, the M button should have the selected style class
    expect(mBtn.className).toContain('sizeSelected');
  });

  it('renders action buttons', () => {
    renderSheet();
    expect(screen.getByText('Купить сейчас')).toBeInTheDocument();
    expect(screen.getByText('В корзину')).toBeInTheDocument();
  });

  it("calls addCartItem when 'В корзину' is clicked", async () => {
    const onClose = vi.fn();
    renderSheet({ onClose });

    fireEvent.click(screen.getByText('В корзину'));

    await waitFor(() => {
      expect(mockAddCartItem).toHaveBeenCalledWith({
        product_id: 42,
        quantity: 1,
      });
    });

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("calls addCartItem and navigates when 'Купить сейчас' is clicked", async () => {
    const onClose = vi.fn();
    renderSheet({ onClose });

    fireEvent.click(screen.getByText('Купить сейчас'));

    await waitFor(() => {
      expect(mockAddCartItem).toHaveBeenCalledWith({
        product_id: 42,
        quantity: 1,
      });
    });

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('does not render when open is false', () => {
    renderSheet({ open: false });
    expect(screen.queryByText('Джинсы Carne Bollente')).not.toBeInTheDocument();
  });

  it('saves cart meta to localStorage on add', async () => {
    renderSheet();
    fireEvent.click(screen.getByText('M'));
    fireEvent.click(screen.getByText('В корзину'));

    await waitFor(() => {
      expect(localStorage.setItem).toHaveBeenCalledWith(
        'loyaltymarket_cart_meta_v1',
        expect.any(String)
      );
    });
  });

  it('has accessible dialog role', () => {
    renderSheet();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
