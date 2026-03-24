'use client';

import { useState } from 'react';

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
        ERROR_MESSAGES[code] ?? backendMessage ?? 'Ошибка входа. Попробуйте позже',
      );
    } catch {
      setError('Нет связи с сервером');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#efeff0] p-5">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm"
      >
        <h1 className="mb-6 text-center text-xl font-semibold text-[#22252b]">
          Вход в панель
        </h1>

        {error && (
          <div role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium text-[#22252b]">
            Логин
          </span>
          <input
            type="text"
            required
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            onFocus={() => setError('')}
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b]"
            placeholder="Email или имя пользователя"
            autoComplete="username"
          />
        </label>

        <div className="mb-6">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-[#22252b]">
              Пароль
            </span>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={8}
                value={password}
                onFocus={() => { setPasswordTouched(true); setError(''); }}
                onChange={(e) => setPassword(e.target.value)}
                className={`w-full rounded-lg border px-3 py-2.5 pr-10 text-sm transition-colors duration-300 outline-none ${
                  error
                    ? 'border-[#22252b]'
                    : passwordTouched && passwordLength > 0 && !passwordValid
                      ? 'border-amber-400'
                      : passwordValid
                        ? 'border-emerald-400'
                        : 'border-[#dfdfe2] focus:border-[#22252b]'
                }`}
                placeholder="Минимум 8 символов"
                autoComplete="current-password"
              />
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowPassword((v) => !v)}
                className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded-md p-1 text-[#878b93] transition-colors hover:text-[#22252b]"
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="transition-transform duration-200"
                >
                  {showPassword ? (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" />
                      <circle cx="12" cy="12" r="3" />
                    </>
                  ) : (
                    <>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </>
                  )}
                </svg>
              </button>
            </div>
          </label>

          {/* Password length indicator */}
          {passwordTouched && passwordLength > 0 && !error && (
            <div className="mt-2 animate-fadeIn">
              <div className="h-1 w-full overflow-hidden rounded-full bg-[#efeff0]">
                <div
                  className={`h-full rounded-full transition-all duration-300 ease-out ${
                    passwordValid ? 'bg-emerald-500' : 'bg-amber-400'
                  }`}
                  style={{ width: `${passwordProgress * 100}%` }}
                />
              </div>
              {!passwordValid && (
                <div className="mt-1.5 flex items-center justify-between">
                  <span className="text-xs text-[#878b93]">
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
          className="w-full rounded-lg bg-[#22252b] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Вход...' : 'Войти'}
        </button>
      </form>
    </div>
  );
}
