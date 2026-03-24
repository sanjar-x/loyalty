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

  async function handleSubmit(e) {
    e.preventDefault();
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
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
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
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b]"
            placeholder="Email или имя пользователя"
            autoComplete="username"
          />
        </label>

        <label className="mb-6 block">
          <span className="mb-1 block text-sm font-medium text-[#22252b]">
            Пароль
          </span>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-[#dfdfe2] px-3 py-2.5 text-sm transition-colors outline-none focus:border-[#22252b]"
            placeholder="Минимум 8 символов"
            autoComplete="current-password"
          />
        </label>

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
