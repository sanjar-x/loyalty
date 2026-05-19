import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Build a tiny base64url-encoded JWT payload. The header/signature are
// dummies — helpers only inspect the middle segment.
function makeJwt(payload) {
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `dummy.${body}.dummy`;
}

function makeCookieStore(initial) {
  const store = new Map(Object.entries(initial));
  return {
    get(name) {
      return store.has(name) ? { name, value: store.get(name) } : undefined;
    },
    set(name, value) {
      store.set(name, value);
    },
  };
}

const cookiesMock = vi.fn();
vi.mock('next/headers', () => ({
  cookies: () => cookiesMock(),
}));

describe('shared/auth/cookies — getAccessToken', () => {
  beforeEach(() => {
    vi.resetModules();
    cookiesMock.mockReset();
    // Catch any accidental refresh attempt — the helper is now read-only,
    // refresh lives exclusively in src/proxy.js.
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns the access token from cookies verbatim', async () => {
    const access = makeJwt({ sub: 'u-1', exp: 9999999999 });
    cookiesMock.mockResolvedValue(
      makeCookieStore({ access_token: access, refresh_token: 'r-1' }),
    );
    const { getAccessToken } = await import('../cookies');
    expect(await getAccessToken()).toBe(access);
  });

  it("never POSTs to the backend — refresh is the proxy's job", async () => {
    const expired = makeJwt({
      sub: 'u-1',
      exp: Math.floor(Date.now() / 1000) - 60,
    });
    cookiesMock.mockResolvedValue(
      makeCookieStore({ access_token: expired, refresh_token: 'r-1' }),
    );
    const { getAccessToken } = await import('../cookies');
    // Even when the token is clearly expired we just return what we
    // read — the proxy has already rotated it (or will, on the next
    // request) and downstream callers shouldn't fan-out their own
    // refresh storm.
    expect(await getAccessToken()).toBe(expired);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('returns null when no cookie is present', async () => {
    cookiesMock.mockResolvedValue(makeCookieStore({}));
    const { getAccessToken } = await import('../cookies');
    expect(await getAccessToken()).toBeNull();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});

describe('shared/auth/cookies — isTokenExpired', () => {
  it('treats payload without exp as expired', async () => {
    const { isTokenExpired } = await import('../cookies');
    expect(isTokenExpired({})).toBe(true);
    expect(isTokenExpired(null)).toBe(true);
  });

  it('compares exp directly to Date.now() (no skew — proxy owns the rotation timing)', async () => {
    const { isTokenExpired } = await import('../cookies');
    const now = Math.floor(Date.now() / 1000);
    expect(isTokenExpired({ exp: now - 60 })).toBe(true);
    expect(isTokenExpired({ exp: now + 60 })).toBe(false);
  });
});
