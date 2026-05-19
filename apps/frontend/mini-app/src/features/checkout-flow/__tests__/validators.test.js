import { describe, it, expect } from 'vitest';

import {
  PHONE_FORMATS,
  SUPPORTED_PHONE_COUNTRIES,
  normalizePhoneDigits,
  formatPhone,
} from '@/shared/lib/phone';
import { isValidLuhn } from '@/shared/lib/card';
import { validateRecipient } from '@/entities/recipient';
import { validateCardDraft, validateRecipientForOrder } from '../lib/validators';

describe('isValidLuhn', () => {
  it('rejects too-short numbers', () => {
    expect(isValidLuhn('123')).toBe(false);
  });
  it('accepts a known-valid card number', () => {
    expect(isValidLuhn('4242 4242 4242 4242')).toBe(true);
  });
  it('rejects an invalid checksum', () => {
    expect(isValidLuhn('4242 4242 4242 4241')).toBe(false);
  });
});

describe('normalizePhoneDigits (RU default, country-aware CHK-002)', () => {
  it('strips leading +7 (RU)', () => {
    expect(normalizePhoneDigits('+7 (988) 000-11-22')).toBe('9880001122');
  });
  it('strips leading 8 (RU trunk)', () => {
    expect(normalizePhoneDigits('89880001122')).toBe('9880001122');
  });
  it('caps at 10 digits (RU)', () => {
    expect(normalizePhoneDigits('9880001122999')).toBe('9880001122');
  });
  it('UZ — strips +998 and caps at 9', () => {
    expect(normalizePhoneDigits('+998 90 123 45 67', 'UZ')).toBe('901234567');
    expect(normalizePhoneDigits('998901234567', 'UZ')).toBe('901234567');
  });
  it('BY — strips +375 and caps at 9', () => {
    expect(normalizePhoneDigits('+375 29 123 45 67', 'BY')).toBe('291234567');
  });
  it('UA — strips +380 and caps at 9', () => {
    expect(normalizePhoneDigits('+380 67 123 45 67', 'UA')).toBe('671234567');
  });
  it('KZ — strips +7 and caps at 10', () => {
    expect(normalizePhoneDigits('+7 701 234 56 78', 'KZ')).toBe('7012345678');
  });
});

describe('formatPhone (country-aware)', () => {
  it('RU — +7 prefix and groups', () => {
    expect(formatPhone('9880001122', 'RU')).toBe('+7 988 000-11-22');
  });
  it('RU — short input progressive', () => {
    expect(formatPhone('988', 'RU')).toBe('+7 988');
    expect(formatPhone('988000', 'RU')).toBe('+7 988 000');
  });
  it('UZ — +998 with 2-3-2-2 grouping', () => {
    expect(formatPhone('901234567', 'UZ')).toBe('+998 90 123-45-67');
  });
  it('BY — +375 with 2-3-2-2 grouping', () => {
    expect(formatPhone('291234567', 'BY')).toBe('+375 29 123-45-67');
  });
  it('UA — +380 with 2-3-2-2 grouping', () => {
    expect(formatPhone('671234567', 'UA')).toBe('+380 67 123-45-67');
  });
  it('KZ — +7 with 3-3-2-2 grouping', () => {
    expect(formatPhone('7012345678', 'KZ')).toBe('+7 701 234-56-78');
  });
  it('empty input → empty string', () => {
    expect(formatPhone('', 'RU')).toBe('');
    expect(formatPhone('', 'UZ')).toBe('');
  });
  it('default country is RU', () => {
    expect(formatPhone('9880001122')).toBe('+7 988 000-11-22');
  });
});

describe('PHONE_FORMATS — completeness (CHK-002)', () => {
  it('covers RU/BY/KZ/UZ/UA', () => {
    expect([...SUPPORTED_PHONE_COUNTRIES].sort()).toEqual(['BY', 'KZ', 'RU', 'UA', 'UZ'].sort());
  });
  it('each format has prefix, lenAfter, placeholder', () => {
    for (const code of SUPPORTED_PHONE_COUNTRIES) {
      const fmt = PHONE_FORMATS[code];
      expect(fmt.prefix.startsWith('+')).toBe(true);
      expect(typeof fmt.lenAfter).toBe('number');
      expect(typeof fmt.placeholder).toBe('string');
    }
  });
});

describe('validateCardDraft', () => {
  const valid = {
    numberDigits: '4242424242424242',
    exp: '12/30',
    cvc: '123',
    holder: 'IVAN PETROV',
  };

  it('passes for valid input', () => {
    expect(validateCardDraft(valid)).toEqual({});
  });
  it('rejects bad Luhn', () => {
    expect(validateCardDraft({ ...valid, numberDigits: '4242424242424241' }).numberDigits).toBe(
      'invalid'
    );
  });
  it('rejects month=13', () => {
    expect(validateCardDraft({ ...valid, exp: '13/30' }).exp).toBe('invalid');
  });
  it('rejects 2-digit cvc', () => {
    expect(validateCardDraft({ ...valid, cvc: '12' }).cvc).toBe('invalid');
  });
});

describe('validateRecipient — phone country matrix (CHK-002)', () => {
  const base = {
    fullName: 'Иван Петров',
    email: 'ivan@example.ru',
  };

  // RU
  it('RU valid (+7 9XX, 10 digits)', () => {
    const r = validateRecipient({ ...base, country: 'RU', phoneDigits: '9012345678' });
    expect(r.phoneDigits).toBeUndefined();
  });
  it('RU wrong firstDigit (8 instead of 9)', () => {
    const r = validateRecipient({ ...base, country: 'RU', phoneDigits: '8012345678' });
    expect(r.phoneDigits).toBe('invalid');
  });
  it('RU wrong length (9 digits)', () => {
    const r = validateRecipient({ ...base, country: 'RU', phoneDigits: '901234567' });
    expect(r.phoneDigits).toBe('invalid');
  });

  // UZ
  it('UZ valid (9 digits)', () => {
    const r = validateRecipient({ ...base, country: 'UZ', phoneDigits: '901234567' });
    expect(r.phoneDigits).toBeUndefined();
  });
  it('UZ wrong length (8 digits)', () => {
    const r = validateRecipient({ ...base, country: 'UZ', phoneDigits: '90123456' });
    expect(r.phoneDigits).toBe('invalid');
  });

  // KZ
  it('KZ valid (+7 7XX, 10 digits)', () => {
    const r = validateRecipient({ ...base, country: 'KZ', phoneDigits: '7012345678' });
    expect(r.phoneDigits).toBeUndefined();
  });
  it('KZ wrong firstDigit (9)', () => {
    const r = validateRecipient({ ...base, country: 'KZ', phoneDigits: '9012345678' });
    expect(r.phoneDigits).toBe('invalid');
  });

  // BY
  it('BY valid (9 digits)', () => {
    const r = validateRecipient({ ...base, country: 'BY', phoneDigits: '291234567' });
    expect(r.phoneDigits).toBeUndefined();
  });
  it('BY wrong length (10 digits)', () => {
    const r = validateRecipient({ ...base, country: 'BY', phoneDigits: '2912345678' });
    expect(r.phoneDigits).toBe('invalid');
  });

  // UA
  it('UA valid (9 digits)', () => {
    const r = validateRecipient({ ...base, country: 'UA', phoneDigits: '671234567' });
    expect(r.phoneDigits).toBeUndefined();
  });
  it('UA wrong length (8 digits)', () => {
    const r = validateRecipient({ ...base, country: 'UA', phoneDigits: '67123456' });
    expect(r.phoneDigits).toBe('invalid');
  });

  it('default country is RU when not provided', () => {
    const r = validateRecipient({ ...base, phoneDigits: '9012345678' });
    expect(r.phoneDigits).toBeUndefined();
  });
});

describe('validateRecipient — email global TLD (CHK-002)', () => {
  const base = {
    fullName: 'Иван Петров',
    phoneDigits: '9012345678',
    country: 'RU',
  };
  it('user@example.io — valid', () => {
    expect(validateRecipient({ ...base, email: 'user@example.io' }).email).toBeUndefined();
  });
  it('john.doe+filter@sub.example.uk — valid', () => {
    expect(
      validateRecipient({ ...base, email: 'john.doe+filter@sub.example.uk' }).email
    ).toBeUndefined();
  });
  it('user@example.uz — valid', () => {
    expect(validateRecipient({ ...base, email: 'user@example.uz' }).email).toBeUndefined();
  });
  it('user@example.app — valid', () => {
    expect(validateRecipient({ ...base, email: 'user@example.app' }).email).toBeUndefined();
  });
  it('noTld@example — invalid', () => {
    expect(validateRecipient({ ...base, email: 'noTld@example' }).email).toBe('invalid');
  });
  it('missing @ — invalid', () => {
    expect(validateRecipient({ ...base, email: 'noatsign.com' }).email).toBe('invalid');
  });
  it('empty — required', () => {
    expect(validateRecipient({ ...base, email: '' }).email).toBe('required');
  });
  it('trailing space trimmed', () => {
    expect(validateRecipient({ ...base, email: '  user@example.io  ' }).email).toBeUndefined();
  });
});

describe('validateRecipient — ФИО (CHK-002, latin/cyrillic/punct)', () => {
  const base = { phoneDigits: '9012345678', email: 'u@e.io', country: 'RU' };
  it("Анна О'Брайен — valid (apostrof)", () => {
    expect(validateRecipient({ ...base, fullName: "Анна О'Брайен" }).fullName).toBeUndefined();
  });
  it('Жан-Поль Иванов — valid (hyphen inside word)', () => {
    expect(validateRecipient({ ...base, fullName: 'Жан-Поль Иванов' }).fullName).toBeUndefined();
  });
  it('Mary Jane Watson-Parker — valid (latin, hyphen)', () => {
    expect(
      validateRecipient({ ...base, fullName: 'Mary Jane Watson-Parker' }).fullName
    ).toBeUndefined();
  });
  it('Иван (1 word) — invalid', () => {
    expect(validateRecipient({ ...base, fullName: 'Иван' }).fullName).toBe('invalid');
  });
  it('six words — invalid (max 5)', () => {
    expect(validateRecipient({ ...base, fullName: 'A B C D E F' }).fullName).toBe('invalid');
  });
  it('digits — invalid', () => {
    expect(validateRecipient({ ...base, fullName: 'Иван 123' }).fullName).toBe('invalid');
  });
  it('empty — required', () => {
    expect(validateRecipient({ ...base, fullName: '' }).fullName).toBe('required');
  });
});

describe('validateRecipientForOrder — shipping-only payload check (ADR-011)', () => {
  const validRecipient = {
    fullName: 'Иван Иванов',
    phoneDigits: '9990001122',
    email: 'ivan@example.ru',
    country: 'RU',
  };

  it('happy path → ok:true', () => {
    expect(validateRecipientForOrder({ recipient: validRecipient }).ok).toBe(true);
  });

  it('UZ recipient happy path', () => {
    expect(
      validateRecipientForOrder({
        recipient: { ...validRecipient, country: 'UZ', phoneDigits: '901234567' },
      }).ok
    ).toBe(true);
  });

  it('missing fullName → required', () => {
    expect(
      validateRecipientForOrder({ recipient: { ...validRecipient, fullName: '' } }).errors.fullName
    ).toBe('required');
  });

  it('RU phone not 10 digits → invalid', () => {
    expect(
      validateRecipientForOrder({
        recipient: { ...validRecipient, phoneDigits: '999000' },
      }).errors.phoneDigits
    ).toBe('invalid');
  });

  it('missing email → required', () => {
    expect(
      validateRecipientForOrder({ recipient: { ...validRecipient, email: '' } }).errors.email
    ).toBe('required');
  });

  it('passport / customs fields are NOT validated here anymore (ADR-011)', () => {
    // Customs migrated to features/passport-form/lib/validators — see
    // features/passport-form/__tests__/validators.test.js for coverage.
    const r = validateRecipientForOrder({ recipient: validRecipient });
    expect(r.errors.passportSeries).toBeUndefined();
    expect(r.errors.passportNumber).toBeUndefined();
    expect(r.errors.inn).toBeUndefined();
    expect(r.errors.birthDate).toBeUndefined();
    expect(r.errors.issueDate).toBeUndefined();
  });
});
