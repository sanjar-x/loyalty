'use client';

import { Skeleton } from '@/shared/ui/Skeleton';

/**
 * Audit 4.2 — full-page skeleton for the edit-product layout (back
 * button + title + form sections). Matches the live form's vertical
 * rhythm so the post-load swap doesn't push content around.
 */
export function ProductEditSkeleton() {
  return (
    <section
      role="status"
      aria-live="polite"
      aria-label="Загружаем форму редактирования"
      className="space-y-6 p-6"
    >
      <div className="flex items-center gap-3">
        <Skeleton.Circle size={32} />
        <Skeleton.Bar w={260} h={26} />
      </div>

      {Array.from({ length: 3 }).map((_, idx) => (
        <div
          key={idx}
          className="border-app-border space-y-3 rounded-2xl border p-5"
        >
          <Skeleton.Bar w={'40%'} h={18} />
          <Skeleton.Block h={48} />
          <Skeleton.Block h={48} />
        </div>
      ))}

      <div className="flex items-center justify-end gap-3">
        <Skeleton.Bar w={120} h={36} />
        <Skeleton.Bar w={160} h={36} />
      </div>
    </section>
  );
}
