'use client';

import Link from 'next/link';

// Public invite flow has no admin shell to fall back to — without this
// boundary an unexpected error during validate/accept renders the
// default Next.js error page, which mentions internals an invitee
// shouldn't see. Keep the copy reassuring, and link to /login so an
// already-accepted invitee can sign in instead of starting over.
export default function InviteError({ error, reset }) {
  const isDev = process.env.NODE_ENV === 'development';
  return (
    <div className="w-full max-w-md rounded-3xl bg-white p-8 text-center shadow-sm">
      <h1 className="text-app-text text-xl font-semibold">
        Что-то пошло не так
      </h1>
      <p className="text-app-muted mt-3 text-sm">
        {isDev && error?.message
          ? error.message
          : 'Не удалось открыть приглашение. Попробуйте ещё раз — если ошибка повторится, свяжитесь с администратором.'}
      </p>
      <div className="mt-6 flex items-center justify-center gap-2">
        <button
          type="button"
          onClick={reset}
          className="bg-app-text-dark rounded-2xl px-5 py-2.5 text-sm font-medium text-white"
        >
          Попробовать снова
        </button>
        <Link
          href="/login"
          className="border-app-border text-app-text-dark hover:bg-app-card rounded-2xl border px-5 py-2.5 text-sm font-medium"
        >
          Войти
        </Link>
      </div>
    </div>
  );
}
