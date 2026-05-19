'use client';

import Link from 'next/link';

// Per-route error boundary for /admin/orders/[orderId]. Without it the
// admin shell's generic boundary catches the throw, but the user loses
// the back-link to the orders list. Keep this minimal — message + retry
// + the navigation breadcrumb the parent layout would otherwise drop.
export default function OrderDetailError({ error, reset }) {
  const isDev = process.env.NODE_ENV === 'development';
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl bg-red-50 px-6 py-12 text-center">
      <h2 className="text-app-text-dark text-lg font-semibold">
        Не удалось открыть заказ
      </h2>
      <p className="text-app-muted max-w-md text-sm">
        {isDev && error?.message
          ? error.message
          : 'Что-то пошло не так. Попробуйте ещё раз или вернитесь к списку.'}
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
          href="/admin/orders"
          className="border-app-border text-app-text-dark hover:bg-app-card rounded-lg border px-4 py-2 text-sm font-medium"
        >
          ← К заказам
        </Link>
      </div>
    </div>
  );
}
