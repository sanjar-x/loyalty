import { afterEach, beforeEach, describe, it, expect } from 'vitest';

import { useAuthStore } from '../authStore';
import { AuthStatus } from '../authStatus';

describe('useAuthStore (entities/user) — FSM transitions', () => {
  beforeEach(() => {
    // Reset state before each test
    useAuthStore.setState({
      status: AuthStatus.IDLE,
      isNewUser: false,
      error: null,
      user: null,
      isVerifying: false,
    });
  });

  afterEach(() => {
    useAuthStore.setState({
      status: AuthStatus.IDLE,
      isNewUser: false,
      error: null,
      user: null,
      isVerifying: false,
    });
  });

  it('начальный state — IDLE без user/error', () => {
    const s = useAuthStore.getState();
    expect(s.status).toBe(AuthStatus.IDLE);
    expect(s.user).toBeNull();
    expect(s.error).toBeNull();
    expect(s.isVerifying).toBe(false);
  });

  it('authStart → LOADING + сбрасывает error', () => {
    useAuthStore.setState({ error: 'prev error' });
    useAuthStore.getState().authStart();
    const s = useAuthStore.getState();
    expect(s.status).toBe(AuthStatus.LOADING);
    expect(s.error).toBeNull();
  });

  it('authSuccess → AUTHENTICATED + user + isVerifying=false', () => {
    useAuthStore.setState({ isVerifying: true });
    useAuthStore.getState().authSuccess({
      isNewUser: true,
      user: { firstName: 'Ivan', tgId: 123 },
    });
    const s = useAuthStore.getState();
    expect(s.status).toBe(AuthStatus.AUTHENTICATED);
    expect(s.user).toEqual({ firstName: 'Ivan', tgId: 123 });
    expect(s.isNewUser).toBe(true);
    expect(s.isVerifying).toBe(false);
    expect(s.error).toBeNull();
  });

  it('authSuccess без аргументов — default isNewUser=false, user=null', () => {
    useAuthStore.getState().authSuccess();
    const s = useAuthStore.getState();
    expect(s.status).toBe(AuthStatus.AUTHENTICATED);
    expect(s.user).toBeNull();
    expect(s.isNewUser).toBe(false);
  });

  it('authFailure → ERROR + сообщение, isVerifying=false', () => {
    useAuthStore.setState({ isVerifying: true });
    useAuthStore.getState().authFailure('Network timeout');
    const s = useAuthStore.getState();
    expect(s.status).toBe(AuthStatus.ERROR);
    expect(s.error).toBe('Network timeout');
    expect(s.isVerifying).toBe(false);
  });

  it('authFailure без сообщения — default "Unknown error"', () => {
    useAuthStore.getState().authFailure();
    const s = useAuthStore.getState();
    expect(s.error).toBe('Unknown error');
  });

  it('sessionExpired → EXPIRED + сброс error/isVerifying', () => {
    useAuthStore.setState({ error: 'foo', isVerifying: true });
    useAuthStore.getState().sessionExpired();
    const s = useAuthStore.getState();
    expect(s.status).toBe(AuthStatus.EXPIRED);
    expect(s.error).toBeNull();
    expect(s.isVerifying).toBe(false);
  });

  it('logout → LOGGED_OUT + полный сброс user/isNewUser', () => {
    useAuthStore.setState({
      status: AuthStatus.AUTHENTICATED,
      user: { firstName: 'X' },
      isNewUser: true,
    });
    useAuthStore.getState().logout();
    const s = useAuthStore.getState();
    expect(s.status).toBe(AuthStatus.LOGGED_OUT);
    expect(s.user).toBeNull();
    expect(s.isNewUser).toBe(false);
    expect(s.error).toBeNull();
  });

  it('setVerifying — coerce в boolean', () => {
    useAuthStore.getState().setVerifying(1);
    expect(useAuthStore.getState().isVerifying).toBe(true);

    useAuthStore.getState().setVerifying(0);
    expect(useAuthStore.getState().isVerifying).toBe(false);

    useAuthStore.getState().setVerifying(null);
    expect(useAuthStore.getState().isVerifying).toBe(false);
  });

  it('AuthStatus — frozen enum (нельзя мутировать)', () => {
    expect(Object.isFrozen(AuthStatus)).toBe(true);
    expect(AuthStatus.AUTHENTICATED).toBe('authenticated');
    expect(AuthStatus.LOGGED_OUT).toBe('logged_out');
  });
});
