'use client';

import { useState } from 'react';
import EyeIcon from '@/assets/icons/eye.svg';
import EyeOffIcon from '@/assets/icons/eye-off.svg';

const ERROR_MESSAGES = {
  INVALID_CREDENTIALS: 'Неверный логин или пароль',
  IDENTITY_DEACTIVATED: 'Аккаунт деактивирован',
  MAX_SESSIONS_EXCEEDED: 'Превышен лимит сессий (макс. 5)',
  REFRESH_TOKEN_REUSE: 'Сессия скомпрометирована. Войдите заново',
  IDENTITY_ALREADY_EXISTS: 'Этот аккаунт уже зарегистрирован',
  VALIDATION_ERROR: 'Проверьте введённые данные',
  SERVICE_UNAVAILABLE: 'Сервис временно недоступен',
};

export default function LoginPage() {
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);

  const passwordLength = password.length;
  const passwordValid = passwordLength >= 8;
  const passwordProgress = Math.min(passwordLength / 8, 1);

  async function handleSubmit(e) {
    e.preventDefault();
    if (loading) return;
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ login, password }),
      });

      if (res.ok) {
        window.location.href = '/admin/orders';
        return;
      }

      const data = await res.json().catch(() => null);
      const code = data?.error?.code;
      const backendMessage = data?.error?.message;
      setError(
        ERROR_MESSAGES[code] ??
          backendMessage ??
          'Ошибка входа. Попробуйте позже',
      );
    } catch {
      setError('Нет связи с сервером');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-app-bg flex min-h-screen items-center justify-center p-5">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm"
      >
        <h1 className="text-app-text mb-6 text-center text-xl font-semibold">
          Вход в панель
        </h1>

        {error && (
          <div
            role="alert"
            className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600"
          >
            {error}
          </div>
        )}

        <label className="mb-4 block">
          <span className="text-app-text mb-1 block text-sm font-medium">
            Логин
          </span>
          <input
            type="text"
            required
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            onFocus={() => setError('')}
            className="border-app-border focus:border-app-text w-full rounded-lg border px-3 py-2.5 text-sm transition-colors outline-none"
            placeholder="Email или имя пользователя"
            autoComplete="username"
          />
        </label>

        <div className="mb-6">
          <label className="block">
            <span className="text-app-text mb-1 block text-sm font-medium">
              Пароль
            </span>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={8}
                value={password}
                onFocus={() => {
                  setPasswordTouched(true);
                  setError('');
                }}
                onChange={(e) => setPassword(e.target.value)}
                className={`w-full rounded-lg border px-3 py-2.5 pr-10 text-sm transition-colors duration-300 outline-none ${
                  error
                    ? 'border-app-text'
                    : passwordTouched && passwordLength > 0 && !passwordValid
                      ? 'border-amber-400'
                      : passwordValid
                        ? 'border-emerald-400'
                        : 'border-app-border focus:border-app-text'
                }`}
                placeholder="Минимум 8 символов"
                autoComplete="current-password"
              />
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowPassword((v) => !v)}
                className="text-app-muted hover:text-app-text absolute top-1/2 right-2.5 -translate-y-1/2 rounded-md p-1 transition-colors"
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showPassword ? (
                  <EyeIcon
                    width={18}
                    height={18}
                    className="transition-transform duration-200"
                  />
                ) : (
                  <EyeOffIcon
                    width={18}
                    height={18}
                    className="transition-transform duration-200"
                  />
                )}
              </button>
            </div>
          </label>

          {/* Password length indicator */}
          {passwordTouched && passwordLength > 0 && !error && (
            <div className="animate-fadeIn mt-2">
              <div className="bg-app-bg h-1 w-full overflow-hidden rounded-full">
                <div
                  className={`h-full rounded-full transition-all duration-300 ease-out ${
                    passwordValid ? 'bg-emerald-500' : 'bg-amber-400'
                  }`}
                  style={{ width: `${passwordProgress * 100}%` }}
                />
              </div>
              {!passwordValid && (
                <div className="mt-1.5 flex items-center justify-between">
                  <span className="text-app-muted text-xs">
                    {passwordLength} / 8 символов
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="bg-app-text w-full rounded-lg px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Вход...' : 'Войти'}
        </button>
      </form>
    </div>
  );
}
