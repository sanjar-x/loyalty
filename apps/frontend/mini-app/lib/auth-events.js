/**
 * Auth expiry event bus — EventTarget asosidagi sodda pub/sub.
 * RTK Query baseQuery 401 + refresh fail bo'lganda `emitAuthExpired()` chaqiradi.
 * TelegramAuthBootstrap `onAuthExpired` ga subscribe bo'lib auto re-login qiladi.
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
