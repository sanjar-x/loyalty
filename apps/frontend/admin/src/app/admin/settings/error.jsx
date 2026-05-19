'use client';

import Link from 'next/link';

// Per-section error boundary so that a thrown render error in any single
// settings page (brands, categories, attributes, …) doesn't bubble all
// the way up to admin/error.jsx — which would unmount the settings
// sidebar and force the operator to navigate back manually.
export default function SettingsError({ error, reset }) {
  const isDev = process.env.NODE_ENV === 'development';
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl bg-red-50 px-6 py-12 text-center">
      <h2 className="text-app-text-dark text-lg font-semibold">
        Не удалось открыть раздел настроек
      </h2>
      <p className="text-app-muted max-w-md text-sm">
        {isDev && error?.message
          ? error.message
          : 'Что-то пошло не так. Попробуйте ещё раз или выберите другой раздел в боковом меню.'}
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
          href="/admin/settings"
          className="border-app-border text-app-text-dark hover:bg-app-card rounded-lg border px-4 py-2 text-sm font-medium"
        >
          ← К настройкам
        </Link>
      </div>
    </div>
  );
}
