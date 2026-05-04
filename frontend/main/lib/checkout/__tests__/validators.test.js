import { describe, it, expect } from "vitest";

import {
  isValidLuhn,
  normalizePhoneDigits,
  formatPhone,
  validateRecipient,
  validateCardDraft,
} from "../validators";

describe("isValidLuhn", () => {
  it("rejects too-short numbers", () => {
    expect(isValidLuhn("123")).toBe(false);
  });
  it("accepts a known-valid card number", () => {
    expect(isValidLuhn("4242 4242 4242 4242")).toBe(true);
  });
  it("rejects an invalid checksum", () => {
    expect(isValidLuhn("4242 4242 4242 4241")).toBe(false);
  });
});

describe("normalizePhoneDigits", () => {
  it("strips leading +7", () => {
    expect(normalizePhoneDigits("+7 (988) 000-11-22")).toBe("9880001122");
  });
  it("strips leading 8", () => {
    expect(normalizePhoneDigits("89880001122")).toBe("9880001122");
  });
  it("caps at 10 digits", () => {
    expect(normalizePhoneDigits("9880001122999")).toBe("9880001122");
  });
});

describe("formatPhone", () => {
  it("renders +7 prefix and groups", () => {
    expect(formatPhone("9880001122")).toBe("+7 988 000-11-22");
  });
  it("handles short input progressively", () => {
    expect(formatPhone("988")).toBe("+7 988");
    expect(formatPhone("988000")).toBe("+7 988 000");
  });
  it("returns empty string for empty input", () => {
    expect(formatPhone("")).toBe("");
  });
});

describe("validateRecipient", () => {
  const valid = {
    fullName: "Иван Петров",
    phoneDigits: "9880001122",
    email: "ivan@example.ru",
  };

  it("passes for valid input", () => {
    expect(validateRecipient(valid)).toEqual({});
  });
  it("rejects latin in fullName", () => {
    expect(validateRecipient({ ...valid, fullName: "Ivan" }).fullName).toBe(
      "invalid",
    );
  });
  it("rejects single-word fullName", () => {
    expect(validateRecipient({ ...valid, fullName: "Иван" }).fullName).toBe(
      "invalid",
    );
  });
  it("rejects phone not starting with 9", () => {
    expect(
      validateRecipient({ ...valid, phoneDigits: "8800001122" }).phoneDigits,
    ).toBe("invalid");
  });
  it("rejects email with bad TLD", () => {
    expect(validateRecipient({ ...valid, email: "ivan@example.org" }).email).toBe(
      "invalid",
    );
  });
});

describe("validateCardDraft", () => {
  const valid = {
    numberDigits: "4242424242424242",
    exp: "12/30",
    cvc: "123",
    holder: "IVAN PETROV",
  };

  it("passes for valid input", () => {
    expect(validateCardDraft(valid)).toEqual({});
  });
  it("rejects bad Luhn", () => {
    expect(
      validateCardDraft({ ...valid, numberDigits: "4242424242424241" })
        .numberDigits,
    ).toBe("invalid");
  });
  it("rejects month=13", () => {
    expect(validateCardDraft({ ...valid, exp: "13/30" }).exp).toBe("invalid");
  });
  it("rejects 2-digit cvc", () => {
    expect(validateCardDraft({ ...valid, cvc: "12" }).cvc).toBe("invalid");
  });
});
