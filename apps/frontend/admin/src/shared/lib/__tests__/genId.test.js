import { describe, expect, it } from 'vitest';
import { genId, randomAlphanumeric, randomHexToken } from '../genId';

describe('genId', () => {
  it('produces unique ids on subsequent calls', () => {
    const a = genId('test');
    const b = genId('test');
    expect(a).not.toEqual(b);
    expect(a.startsWith('test-')).toBe(true);
  });

  it('uses default prefix when none is given', () => {
    expect(genId()).toMatch(/^id-/);
  });
});

describe('randomAlphanumeric', () => {
  it('returns a string of the requested length', () => {
    expect(randomAlphanumeric(8)).toHaveLength(8);
    expect(randomAlphanumeric(16)).toHaveLength(16);
  });

  it('returns only alphanumeric uppercase characters', () => {
    expect(randomAlphanumeric(64)).toMatch(/^[A-Z0-9]+$/);
  });
});

describe('randomHexToken', () => {
  it('returns a hex string of length 2 * byteLength', () => {
    expect(randomHexToken(8)).toHaveLength(16);
    expect(randomHexToken(16)).toHaveLength(32);
  });

  it('contains only hex characters', () => {
    expect(randomHexToken(32)).toMatch(/^[0-9a-f]+$/);
  });
});
