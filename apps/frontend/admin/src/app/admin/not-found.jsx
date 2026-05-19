import Link from 'next/link';

export default function AdminNotFound() {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-3">
      <h2 className="text-app-text text-xl font-bold">Страница не найдена</h2>
      <p className="text-app-muted">Проверьте URL или вернитесь к заказам.</p>
      <Link
        href="/admin/orders"
        className="bg-app-text-dark hover:bg-app-text-darker mt-2 rounded-xl px-6 py-2.5 text-white transition-colors"
      >
        К заказам
      </Link>
    </div>
  );
}
