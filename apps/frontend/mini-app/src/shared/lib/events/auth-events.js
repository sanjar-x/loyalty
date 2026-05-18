/**
 * Auth-expiry event bus — a simple EventTarget-based pub/sub.
 * RTK Query baseQuery calls `emitAuthExpired()` on 401 + refresh failure.
 * TelegramAuthBootstrap subscribes to `onAuthExpired` and performs auto re-login.
 */

const authTarget = typeof EventTarget !== 'undefined' ? new EventTarget() : null;

const AUTH_EXPIRED_EVENT = 'auth:expired';

export function emitAuthExpired() {
  authTarget?.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

export function onAuthExpired(listener) {
  if (!authTarget) return () => {};
  authTarget.addEventListener(AUTH_EXPIRED_EVENT, listener);
  return () => authTarget.removeEventListener(AUTH_EXPIRED_EVENT, listener);
}
