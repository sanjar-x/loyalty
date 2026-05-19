import { describe, expect, it } from 'vitest';

import { validatePassport } from '../lib/validators';

const VALID = Object.freeze({
  fullNameRu: 'Иванов Иван Иванович',
  fullNameLat: 'Ivanov Ivan Ivanovich',
  passportSerial: '1234',
  passportNumber: '567890',
  passportIssueDateIso: '2015-06-20',
  birthDateIso: '1990-03-12',
  inn: '500100732259',
});

describe('validatePassport', () => {
  it('returns no errors for a valid draft', () => {
    expect(validatePassport(VALID)).toEqual({});
  });

  it('flags required fields with code "required"', () => {
    const errors = validatePassport({
      fullNameRu: '',
      fullNameLat: '',
      passportSerial: '',
      passportNumber: '',
      passportIssueDateIso: '',
      birthDateIso: '',
      inn: '',
    });
    expect(errors).toMatchObject({
      fullNameRu: 'required',
      fullNameLat: 'required',
      passportSerial: 'required',
      passportNumber: 'required',
      passportIssueDate: 'required',
      birthDate: 'required',
      inn: 'required',
    });
  });

  it('rejects 3-digit serial / 5-digit number with "invalid"', () => {
    expect(
      validatePassport({ ...VALID, passportSerial: '123', passportNumber: '12345' })
    ).toMatchObject({ passportSerial: 'invalid', passportNumber: 'invalid' });
  });

  it('rejects future issue date / future birth date / pre-1991 issue date', () => {
    const tomorrow = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 10);
    expect(validatePassport({ ...VALID, passportIssueDateIso: tomorrow })).toMatchObject({
      passportIssueDate: 'future',
    });
    expect(validatePassport({ ...VALID, birthDateIso: tomorrow })).toMatchObject({
      birthDate: 'future',
    });
    expect(validatePassport({ ...VALID, passportIssueDateIso: '1989-12-31' })).toMatchObject({
      passportIssueDate: 'before_passport_era',
    });
  });

  it('rejects bearer younger than 14 with "too_young"', () => {
    const tooYoung = new Date(Date.now() - 12 * 365.25 * 24 * 3600 * 1000)
      .toISOString()
      .slice(0, 10);
    expect(validatePassport({ ...VALID, birthDateIso: tooYoung })).toMatchObject({
      birthDate: 'too_young',
    });
  });

  it('rejects issue date before bearer turns 14 with "before_owner_age"', () => {
    expect(
      validatePassport({
        ...VALID,
        birthDateIso: '2010-01-01',
        passportIssueDateIso: '2020-01-01', // 10 years old at issue
      })
    ).toMatchObject({ passportIssueDate: 'before_owner_age' });
  });

  it('rejects ИНН with a bad checksum', () => {
    expect(validatePassport({ ...VALID, inn: '500100732250' })).toMatchObject({ inn: 'checksum' });
  });

  it('rejects ФИО with only one word', () => {
    expect(
      validatePassport({ ...VALID, fullNameRu: 'Иванов', fullNameLat: 'Ivanov' })
    ).toMatchObject({ fullNameRu: 'invalid', fullNameLat: 'invalid' });
  });

  it('rejects ФИО (Latin) with Cyrillic characters', () => {
    expect(validatePassport({ ...VALID, fullNameLat: 'Иванов Иван' })).toMatchObject({
      fullNameLat: 'invalid',
    });
  });
});
