/**
 * Cache + rollback contract for useImageReorder.
 *
 * Mocks the entities/product barrel so we don't touch the real network
 * stack. Verifies:
 *   - optimistic onLocalReorder fires synchronously
 *   - server-known images (with `mediaId`) are sent in the body; new
 *     uploads (no mediaId) are skipped on the wire
 *   - rollback restores `prev` on backend failure and the consumer sees
 *     the error
 *   - create-mode (productId=null) skips the mutation entirely
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';

const reorderMediaMock = vi.fn();

vi.mock('@/entities/product', async () => {
  const actual = await vi.importActual('@/entities/product');
  return {
    ...actual,
    reorderMedia: (...args) => reorderMediaMock(...args),
  };
});

import { useImageReorder } from '../useImageReorder';

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, staleTime: 0 },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper, client };
}

afterEach(() => {
  reorderMediaMock.mockReset();
});

const PRODUCT_ID = '019cdbf4-e987-7000-8080-000000000001';

const SERVER_IMAGES = [
  { localId: 'a', mediaId: 'm-a' },
  { localId: 'b', mediaId: 'm-b' },
  { localId: 'c', mediaId: 'm-c' },
];

describe('useImageReorder', () => {
  it('optimistically applies and persists when productId is set', async () => {
    reorderMediaMock.mockResolvedValueOnce({});
    const onLocalReorder = vi.fn();
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => useImageReorder({ productId: PRODUCT_ID, onLocalReorder }),
      { wrapper: Wrapper },
    );
    const next = [SERVER_IMAGES[2], SERVER_IMAGES[0], SERVER_IMAGES[1]];
    act(() => {
      result.current.reorder(SERVER_IMAGES, next);
    });
    expect(onLocalReorder).toHaveBeenCalledWith(next);
    await waitFor(() => expect(reorderMediaMock).toHaveBeenCalledTimes(1));
    expect(reorderMediaMock).toHaveBeenCalledWith(PRODUCT_ID, {
      items: [
        { mediaId: 'm-c', sortOrder: 0 },
        { mediaId: 'm-a', sortOrder: 1 },
        { mediaId: 'm-b', sortOrder: 2 },
      ],
    });
  });

  it('rolls back to prev on backend failure', async () => {
    reorderMediaMock.mockRejectedValueOnce(new Error('500 boom'));
    const onLocalReorder = vi.fn();
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => useImageReorder({ productId: PRODUCT_ID, onLocalReorder }),
      { wrapper: Wrapper },
    );
    const next = [SERVER_IMAGES[1], SERVER_IMAGES[0], SERVER_IMAGES[2]];
    act(() => {
      result.current.reorder(SERVER_IMAGES, next);
    });
    expect(onLocalReorder).toHaveBeenNthCalledWith(1, next);
    await waitFor(() => {
      expect(onLocalReorder).toHaveBeenNthCalledWith(2, SERVER_IMAGES);
    });
    expect(result.current.error).toBeInstanceOf(Error);
  });

  it('skips the mutation entirely in create mode', () => {
    const onLocalReorder = vi.fn();
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => useImageReorder({ productId: null, onLocalReorder }),
      { wrapper: Wrapper },
    );
    const next = [{ localId: 'x' }, { localId: 'y' }];
    act(() => {
      result.current.reorder([{ localId: 'y' }, { localId: 'x' }], next);
    });
    expect(onLocalReorder).toHaveBeenCalledWith(next);
    expect(reorderMediaMock).not.toHaveBeenCalled();
  });

  it('skips images without mediaId on the wire even in edit mode', async () => {
    reorderMediaMock.mockResolvedValueOnce({});
    const onLocalReorder = vi.fn();
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => useImageReorder({ productId: PRODUCT_ID, onLocalReorder }),
      { wrapper: Wrapper },
    );
    const prev = [
      { localId: 'a', mediaId: 'm-a' },
      { localId: 'new', mediaId: undefined },
      { localId: 'b', mediaId: 'm-b' },
    ];
    const next = [
      { localId: 'b', mediaId: 'm-b' },
      { localId: 'new', mediaId: undefined },
      { localId: 'a', mediaId: 'm-a' },
    ];
    act(() => {
      result.current.reorder(prev, next);
    });
    await waitFor(() => expect(reorderMediaMock).toHaveBeenCalledTimes(1));
    expect(reorderMediaMock).toHaveBeenCalledWith(PRODUCT_ID, {
      items: [
        { mediaId: 'm-b', sortOrder: 0 },
        { mediaId: 'm-a', sortOrder: 2 },
      ],
    });
  });
});
