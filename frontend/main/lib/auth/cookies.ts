/**
 * Cookie name constants — single source of truth.
 * Imported by both client code and server-side BFF routes (cookie-helpers.ts).
 */
export const ACCESS_COOKIE = "lm_access_token";
export const REFRESH_COOKIE = "lm_refresh_token";

/**
 * Calls the logout BFF route to clear cookies and revoke the backend session.
 * Returns true if the server acknowledged the logout, false on network/server error.
 *
 * Callers should also dispatch `logout()` from authSlice to reset Redux state.
 */
export async function logout(): Promise<boolean> {
  try {
    const res = await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });
    return res.ok;
  } catch {
    return false;
  }
}
