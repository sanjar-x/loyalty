/**
 * Auth status DI seam — baseApi needs to know auth status to skip
 * refresh-on-401 when user is not authenticated. Sprint 3a: instead of a
 * direct `require('@/features/auth-telegram')` (FSD shared→features
 * violation), this is a module-level singleton getter; features/auth-telegram
 * installs it at init (`TelegramSdkProvider` / `useAuthStore` setup).
 *
 * shared does not know where the status comes from; the feature registers
 * its own getter — no cyclic dependency and no lazy require.
 */

let getter = () => null;

export function setAuthStatusGetter(fn) {
  getter = typeof fn === 'function' ? fn : () => null;
}

export function readAuthStatus() {
  try {
    return getter();
  } catch {
    return null;
  }
}
