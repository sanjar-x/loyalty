'use client';

import { useMemo, useState } from 'react';
import { BrandRow, groupBrandsByLetter, useBrands } from '@/entities/brand';
import { BrandFormModal, DeleteBrandConfirmModal } from '@/features/brand-form';
import { SearchInput } from '@/shared/ui/SearchInput';

export default function BrandsAdminPage() {
  const { data, isPending, error, refetch } = useBrands();
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const filtered = useMemo(() => {
    const list = data?.items ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (b) =>
        b.name.toLowerCase().includes(q) || b.slug.toLowerCase().includes(q),
    );
  }, [data, search]);

  const grouped = useMemo(() => groupBrandsByLetter(filtered), [filtered]);

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-app-text text-xl font-semibold">Бренды</h2>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Создать бренд
        </button>
      </div>

      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Поиск по названию или slug"
        className="mb-4 max-w-md"
      />

      {error ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl bg-red-50 px-6 py-12 text-center">
          <p className="text-sm text-red-700">
            {error?.message ?? 'Не удалось загрузить бренды'}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-medium text-white"
          >
            Повторить
          </button>
        </div>
      ) : isPending ? (
        <div className="border-app-border rounded-xl border p-6">
          <div className="bg-app-card h-6 w-1/3 animate-pulse rounded" />
          <div className="mt-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="bg-app-card h-12 w-full animate-pulse rounded"
              />
            ))}
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-app-muted text-sm">
            {search ? 'Бренды не найдены' : 'Бренды не добавлены'}
          </p>
          {!search && (
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="text-app-text text-sm font-medium underline hover:no-underline"
            >
              Добавить первый
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {grouped.map((group) => (
            <section key={group.key}>
              <h3 className="text-app-muted mb-2 text-xs font-semibold tracking-wide uppercase">
                {group.key}
              </h3>
              <div className="border-app-border overflow-hidden rounded-xl border">
                <table className="w-full text-left text-sm">
                  <tbody>
                    {group.brands.map((brand) => (
                      <BrandRow
                        key={brand.id}
                        brand={brand}
                        onEdit={setEditTarget}
                        onDelete={setDeleteTarget}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>
      )}

      <BrandFormModal
        open={createOpen}
        mode="create"
        onClose={() => setCreateOpen(false)}
      />
      <BrandFormModal
        open={Boolean(editTarget)}
        mode="edit"
        brandId={editTarget?.id}
        onClose={() => setEditTarget(null)}
      />
      <DeleteBrandConfirmModal
        open={Boolean(deleteTarget)}
        brand={deleteTarget}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  );
}
