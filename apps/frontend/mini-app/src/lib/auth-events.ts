const AUTH_EXPIRED_EVENT = 'lm:auth:expired';

const authEventTarget = new EventTarget();

export function emitAuthExpired(): void {
  authEventTarget.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

export function onAuthExpired(listener: () => void): () => void {
  const handleExpired = () => {
    listener();
  };

  authEventTarget.addEventListener(AUTH_EXPIRED_EVENT, handleExpired);

  return () => {
    authEventTarget.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired);
  };
}
