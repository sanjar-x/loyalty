import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWrapper } from '@/shared/query';
import * as brandsApi from '../brands';
import { brandKeys } from '../keys';
import { useBrands } from '../queries';

describe('useBrands', () => {
  beforeEach(() => {
    vi.spyOn(brandsApi, 'fetchBrands');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns brand items on success and exposes them under the canonical key', async () => {
    brandsApi.fetchBrands.mockResolvedValueOnce({
      items: [{ id: '1', name: 'Nike' }],
      total: 1,
    });

    const { Wrapper, client } = createWrapper();
    const { result } = renderHook(() => useBrands(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toEqual([{ id: '1', name: 'Nike' }]);
    expect(client.getQueryData(brandKeys.lists())).toEqual({
      items: [{ id: '1', name: 'Nike' }],
      total: 1,
    });
    expect(brandsApi.fetchBrands).toHaveBeenCalledTimes(1);
  });
});
