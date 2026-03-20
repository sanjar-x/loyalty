export const ACCESS_COOKIE_NAME = "lm_access_token";
export const REFRESH_COOKIE_NAME = "lm_refresh_token";

export function getAccessTokenCookieName(): string {
  return ACCESS_COOKIE_NAME;
}

export function getRefreshTokenCookieName(): string {
  return REFRESH_COOKIE_NAME;
}

export async function logout(): Promise<void> {
  await fetch("/api/session/logout", { method: "POST", credentials: "include" });
}
