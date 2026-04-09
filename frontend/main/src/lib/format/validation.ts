/**
 * Return trimmed non-empty string or null.
 */
export function asNonEmptyTrimmedString(
  value: unknown,
): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * Return value as a safe image src string or empty string.
 */
export function asSafeImageSrc(value: unknown): string {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (/^(https?:\/\/|\/|data:image\/)/.test(trimmed)) return trimmed;
  return "";
}

/**
 * Validate a Russian phone number (10 digits, any starting digit).
 * Accepts formats: +7XXXXXXXXXX, 8XXXXXXXXXX, XXXXXXXXXX
 */
export function isValidPhone(phone: string): boolean {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 11 && (digits[0] === "7" || digits[0] === "8")) {
    return true;
  }
  return digits.length === 10;
}

/**
 * Validate email address. Accepts any valid TLD (not restricted to .ru/.com).
 */
export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim());
}

/**
 * Validate full name (at least two words).
 */
export function isValidFullName(name: string): boolean {
  const parts = name.trim().split(/\s+/);
  return parts.length >= 2 && parts.every((p) => p.length >= 2);
}
