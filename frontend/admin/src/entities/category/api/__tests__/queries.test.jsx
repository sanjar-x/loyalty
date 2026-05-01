import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWrapper } from '@/shared/query';
import * as categoriesApi from '../categories';
import * as attributesApi from '../form-attributes';
import { useCategoryFormAttributes, useCategoryTree } from '../queries';

describe('useCategoryTree', () => {
  beforeEach(() => {
    vi.spyOn(categoriesApi, 'fetchCategoryTree');
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns the tree array on success', async () => {
    categoriesApi.fetchCategoryTree.mockResolvedValueOnce([
      { id: 'root', children: [] },
    ]);

    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useCategoryTree(), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([{ id: 'root', children: [] }]);
  });
});

describe('useCategoryFormAttributes', () => {
  beforeEach(() => {
    vi.spyOn(attributesApi, 'fetchFormAttributes');
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('is disabled until categoryId is set', () => {
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useCategoryFormAttributes(null), {
      wrapper: Wrapper,
    });
    expect(result.current.fetchStatus).toBe('idle');
    expect(attributesApi.fetchFormAttributes).not.toHaveBeenCalled();
  });

  it('fires when categoryId is provided', async () => {
    attributesApi.fetchFormAttributes.mockResolvedValueOnce({ groups: [] });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useCategoryFormAttributes('cat-1'), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(attributesApi.fetchFormAttributes).toHaveBeenCalledWith('cat-1');
  });
});
