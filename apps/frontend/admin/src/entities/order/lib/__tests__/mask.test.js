import { describe, expect, it } from 'vitest';
import { formatInn, maskEmail, maskPassport, maskPhone } from '../mask';

describe('maskPassport', () => {
  const cases = [
    {
      title: 'standard 4+6 RU passport → last-2 / last-4',
      input: ['4520', '123456'],
      expected: '**20 **3456',
    },
    {
      title: 'serial shorter than 2 chars → placeholder',
      input: ['1', '123456'],
      expected: '**** ****',
    },
    {
      title: 'number shorter than 4 chars → placeholder',
      input: ['4520', '12'],
      expected: '**** ****',
    },
    {
      title: 'non-string inputs → placeholder',
      input: [null, undefined],
      expected: '**** ****',
    },
    {
      title: 'extra-long inputs still take the trailing safe slice',
      input: ['ABCDE', '0123456789'],
      expected: '**DE **6789',
    },
  ];

  it.each(cases)('$title', ({ input, expected }) => {
    expect(maskPassport(input[0], input[1])).toBe(expected);
  });
});

describe('maskPhone', () => {
  const cases = [
    {
      title: 'plain E.164 mobile',
      input: '+79161234567',
      expected: '+7 (***) ***-45-67',
    },
    {
      title: 'pre-formatted with parens / dashes',
      input: '+7 (916) 123-45-67',
      expected: '+7 (***) ***-45-67',
    },
    {
      title: 'leading 8 substituted local format',
      input: '89161234567',
      expected: '+7 (***) ***-45-67',
    },
    {
      title: 'exactly 4 digits — splits last 4 across the two pairs',
      input: '+7916',
      expected: '+7 (***) ***-79-16',
    },
    {
      title: 'fewer than 4 digits → placeholder',
      input: '+79',
      expected: '+7 (***) ***-**-**',
    },
    {
      title: 'empty input → placeholder',
      input: '',
      expected: '+7 (***) ***-**-**',
    },
    {
      title: 'non-string input → placeholder',
      input: undefined,
      expected: '+7 (***) ***-**-**',
    },
  ];

  it.each(cases)('$title', ({ input, expected }) => {
    expect(maskPhone(input)).toBe(expected);
  });
});

describe('maskEmail', () => {
  const cases = [
    {
      title: 'standard email — first + last of local, full domain',
      input: 'john.doe@example.com',
      expected: 'j***e@example.com',
    },
    {
      title: 'single-char local → masks local entirely',
      input: 'a@example.com',
      expected: '***@example.com',
    },
    {
      title: 'plus-tagged local works on first/last chars',
      input: 'sanjar+test@gmail.com',
      expected: 's***t@gmail.com',
    },
    {
      title: 'missing @ → placeholder',
      input: 'no-at-symbol',
      expected: '***@***',
    },
    {
      title: 'leading @ (empty local) → placeholder',
      input: '@example.com',
      expected: '***@***',
    },
    {
      title: 'trailing @ (empty domain) → placeholder',
      input: 'john@',
      expected: '***@***',
    },
    {
      title: 'non-string input → placeholder',
      input: null,
      expected: '***@***',
    },
  ];

  it.each(cases)('$title', ({ input, expected }) => {
    expect(maskEmail(input)).toBe(expected);
  });
});

describe('formatInn', () => {
  it('returns INN as-is — admin needs full precision for customs', () => {
    expect(formatInn('123456789012')).toBe('123456789012');
  });

  it('falls back to empty string for non-string inputs', () => {
    expect(formatInn(null)).toBe('');
    expect(formatInn(undefined)).toBe('');
    expect(formatInn(12345)).toBe('');
  });
});
