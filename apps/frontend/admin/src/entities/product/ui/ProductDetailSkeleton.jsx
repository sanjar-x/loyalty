'use client';

import { Skeleton } from '@/shared/ui/Skeleton';

/**
 * Audit 1.1 — full-page skeleton that matches the live product-detail
 * layout (back link → title row → status badge / version tag / edit
 * button → transition bar → main card + completeness sidebar → SKU
 * pricing table) so the post-load swap doesn't shift layout.
 */
export function ProductDetailSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Загружаем товар"
      className="space-y-6 p-6"
    >
      <div className="space-y-3">
        <Skeleton.Bar w={140} h={14} />
        <div className="flex items-center gap-3">
          <Skeleton.Bar w={280} h={28} />
          <Skeleton.Bar w={120} h={24} />
          <Skeleton.Bar w={70} h={20} />
          <Skeleton.Bar w={140} h={32} />
        </div>
        <Skeleton.Bar w={200} h={12} />
      </div>

      <Skeleton.Block h={64} />

      <div className="grid gap-6 md:grid-cols-[2fr_1fr]">
        <div className="border-app-border space-y-3 rounded-2xl border p-5">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="flex items-center justify-between gap-4">
              <Skeleton.Bar w={120} h={14} />
              <Skeleton.Bar w={'45%'} h={14} />
            </div>
          ))}
        </div>
        <div className="border-app-border space-y-3 rounded-2xl border p-5">
          <Skeleton.Bar w={'70%'} h={18} />
          <Skeleton.Block h={140} />
        </div>
      </div>

      <div className="border-app-border space-y-3 rounded-2xl border p-5">
        <div className="flex items-center justify-between">
          <Skeleton.Bar w={140} h={20} />
          <Skeleton.Bar w={220} h={32} />
        </div>
        <Skeleton.Block h={180} />
      </div>
    </div>
  );
}
