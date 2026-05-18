import { afterEach, describe, it, expect } from 'vitest';

import { usePvzAccumStore } from '../pvzAccumStore';

describe('usePvzAccumStore (CHK-016 Bug #3 — Sprint 3e перенос)', () => {
  afterEach(() => {
    usePvzAccumStore.setState({ entries: null });
  });

  it('initial state — null', () => {
    expect(usePvzAccumStore.getState().entries).toBeNull();
  });

  it('setEntries — stores entries array verbatim', () => {
    const entries = [
      ['pvz-1', { id: 'pvz-1', lat: 55.0, lon: 37.0 }],
      ['pvz-2', { id: 'pvz-2', lat: 56.0, lon: 38.0 }],
    ];
    usePvzAccumStore.getState().setEntries(entries);
    expect(usePvzAccumStore.getState().entries).toEqual(entries);
  });

  it('setEntries — non-array coerces to null', () => {
    usePvzAccumStore.getState().setEntries([['x', {}]]);
    usePvzAccumStore.getState().setEntries(null);
    expect(usePvzAccumStore.getState().entries).toBeNull();
  });

  it('setEntries — empty array preserved (legit clear)', () => {
    usePvzAccumStore.getState().setEntries([]);
    expect(usePvzAccumStore.getState().entries).toEqual([]);
  });

  it('clear — resets to null', () => {
    usePvzAccumStore.getState().setEntries([['a', {}]]);
    usePvzAccumStore.getState().clear();
    expect(usePvzAccumStore.getState().entries).toBeNull();
  });
});
