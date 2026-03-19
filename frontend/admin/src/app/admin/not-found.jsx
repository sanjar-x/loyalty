import Link from 'next/link';

export default function AdminNotFound() {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-3">
      <h2 className="text-xl font-bold text-[#22252b]">Страница не найдена</h2>
      <p className="text-[#878b93]">Проверьте URL или вернитесь к заказам.</p>
      <Link
        href="/admin/orders"
        className="mt-2 rounded-xl bg-[#2d2d2d] px-6 py-2.5 text-white transition-colors hover:bg-[#3d3d3d]"
      >
        К заказам
      </Link>
    </div>
  );
}
