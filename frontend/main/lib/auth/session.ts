export function getAccessTokenCookieName(): string {
  return "lm_access_token";
}

export async function isAuthenticated(): Promise<boolean> {
  return false;
}

export async function logout(): Promise<void> {
  await fetch("/api/session/logout", { method: "POST", credentials: "include" });
}
