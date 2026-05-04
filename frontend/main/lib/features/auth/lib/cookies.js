export const ACCESS_COOKIE = "lm_access_token";
export const REFRESH_COOKIE = "lm_refresh_token";

/**
 * Client-side logout — calls BFF logout endpoint.
 * Always resolves (best-effort backend call).
 */
export async function logout() {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // best-effort — cookies are cleared server-side regardless
  }
}
