import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWrapper } from '@/shared/query';
import * as suppliersApi from '../suppliers';
import { useSuppliers } from '../queries';

describe('useSuppliers', () => {
  beforeEach(() => {
    vi.spyOn(suppliersApi, 'fetchSuppliers');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns active supplier list', async () => {
    suppliersApi.fetchSuppliers.mockResolvedValueOnce({
      items: [{ id: 's1', name: 'Acme', isActive: true, type: 'local' }],
      total: 1,
    });

    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useSuppliers(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data.items).toHaveLength(1);
    expect(suppliersApi.fetchSuppliers).toHaveBeenCalledTimes(1);
  });
});
