/**
 * Generate a short, locally-unique id (not cryptographically secure).
 *
 * Use for client-side keys, optimistic-update placeholder ids, and other
 * non-persisted markers. For backend ids — let the backend generate them.
 */
let counter = 0;

export function genId(prefix = 'id') {
  counter += 1;
  return `${prefix}-${counter}-${Date.now().toString(36)}`;
}

const RANDOM_TOKEN_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

/**
 * Generate a cryptographically random alphanumeric token of the requested
 * length. Useful for invitation codes, promo codes, etc.
 */
export function randomAlphanumeric(length = 8) {
  if (length <= 0) return '';
  const buf = crypto.getRandomValues(new Uint32Array(length));
  let out = '';
  for (let i = 0; i < length; i += 1) {
    out += RANDOM_TOKEN_ALPHABET[buf[i] % RANDOM_TOKEN_ALPHABET.length];
  }
  return out;
}

/**
 * Generate a cryptographically random hex token. Returns a 16-char string by
 * default (8 random bytes), suitable for invite-link tokens.
 */
export function randomHexToken(byteLength = 8) {
  const bytes = crypto.getRandomValues(new Uint8Array(byteLength));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}
