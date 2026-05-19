import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWrapper } from '@/shared/query';
import * as geoApi from '../geo';
import { useCountries, useSubdivisions } from '../queries';

describe('useCountries', () => {
  beforeEach(() => {
    vi.spyOn(geoApi, 'fetchCountries');
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('forwards lang/limit and surfaces items', async () => {
    geoApi.fetchCountries.mockResolvedValueOnce({
      items: [{ code: 'RU', name: 'Россия' }],
      total: 1,
    });

    const { Wrapper } = createWrapper();
    const { result } = renderHook(
      () => useCountries({ lang: 'ru', limit: 5 }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(geoApi.fetchCountries).toHaveBeenCalledWith({
      lang: 'ru',
      limit: 5,
    });
    expect(result.current.data.items[0].code).toBe('RU');
  });
});

describe('useSubdivisions', () => {
  beforeEach(() => {
    vi.spyOn(geoApi, 'fetchSubdivisions');
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('is disabled when countryCode is empty', () => {
    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useSubdivisions(''), {
      wrapper: Wrapper,
    });
    expect(result.current.fetchStatus).toBe('idle');
    expect(geoApi.fetchSubdivisions).not.toHaveBeenCalled();
  });

  it('fetches when countryCode is provided', async () => {
    geoApi.fetchSubdivisions.mockResolvedValueOnce({
      items: [{ code: 'RU-MOW', name: 'Москва' }],
      total: 1,
    });

    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useSubdivisions('RU'), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(geoApi.fetchSubdivisions).toHaveBeenCalledWith('RU', { lang: 'ru' });
  });
});
