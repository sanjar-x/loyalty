'use client';

import Link from 'next/link';

// Pricing has its own provider context and the heaviest data graph in
// the admin (formulas, variables, recompute jobs) — when any of that
// fails to render, a local boundary keeps the rest of the admin shell
// alive instead of unmounting the sidebar.
export default function PricingError({ error, reset }) {
  const isDev = process.env.NODE_ENV === 'development';
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl bg-red-50 px-6 py-12 text-center">
      <h2 className="text-app-text-dark text-lg font-semibold">
        Не удалось загрузить цены
      </h2>
      <p className="text-app-muted max-w-md text-sm">
        {isDev && error?.message
          ? error.message
          : 'Произошла ошибка при загрузке раздела цен. Попробуйте ещё раз.'}
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={reset}
          className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-medium text-white"
        >
          Попробовать снова
        </button>
        <Link
          href="/admin"
          className="border-app-border text-app-text-dark hover:bg-app-card rounded-lg border px-4 py-2 text-sm font-medium"
        >
          ← В админку
        </Link>
      </div>
    </div>
  );
}
