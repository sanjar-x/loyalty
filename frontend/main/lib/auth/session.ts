export const ACCESS_COOKIE_NAME = "lm_access_token";
export const REFRESH_COOKIE_NAME = "lm_refresh_token";

export function getAccessTokenCookieName(): string {
  return ACCESS_COOKIE_NAME;
}

export function getRefreshTokenCookieName(): string {
  return REFRESH_COOKIE_NAME;
}

/**
 * Calls the logout BFF route to clear cookies and revoke the backend session.
 * Returns true if the server acknowledged the logout, false on network/server error.
 *
 * Callers should also dispatch `logout()` from authSlice to reset Redux state.
 */
export async function logout(): Promise<boolean> {
  try {
    const res = await fetch("/api/session/logout", {
      method: "POST",
      credentials: "include",
    });
    return res.ok;
  } catch {
    return false;
  }
}
