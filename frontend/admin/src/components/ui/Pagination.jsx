'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';

export function Pagination({ page, pages, onPage, className }) {
  const list = useMemo(() => {
    const items = [];
    const max = Math.min(pages, 7);
    const start = Math.max(1, Math.min(page - 2, pages - max + 1));
    for (let p = start; p < start + max; p += 1) items.push(p);
    return items;
  }, [page, pages]);

  if (pages <= 1) return null;

  return (
    <div
      className={cn(
        'mt-6 flex items-center gap-2',
        className,
      )}
    >
      <button
        type="button"
        onClick={() => onPage(Math.max(1, page - 1))}
        className="flex h-9 w-9 items-center justify-center rounded-xl border-0 bg-[#f4f3f1] text-sm font-medium text-[#2d2d2d] hover:bg-[#ededed] cursor-pointer"
        aria-label="Назад"
      >
        <svg
          width="9"
          height="16"
          viewBox="0 0 9 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M8.72252 15.7243C9.09249 15.3568 9.09249 14.7609 8.72252 14.3933L2.28715 8L8.72252 1.60669C9.09249 1.23914 9.09249 0.643216 8.72252 0.275663C8.35255 -0.0918894 7.75271 -0.0918894 7.38274 0.275663L0.277478 7.33449C-0.0924925 7.70204 -0.0924925 8.29796 0.277478 8.66551L7.38274 15.7243C7.75271 16.0919 8.35255 16.0919 8.72252 15.7243Z"
            fill="#7E7E7E"
          />
        </svg>
      </button>
      {list.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onPage(p)}
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-xl border-0 text-sm font-medium cursor-pointer',
            p === page
              ? 'bg-[#2d2d2d] text-white'
              : 'bg-[#f4f3f1] text-[#2d2d2d] hover:bg-[#ededed]',
          )}
        >
          {p}
        </button>
      ))}
      <button
        type="button"
        onClick={() => onPage(Math.min(pages, page + 1))}
        className="flex h-9 w-9 items-center justify-center rounded-xl border-0 bg-[#f4f3f1] text-sm font-medium text-[#2d2d2d] hover:bg-[#ededed] cursor-pointer"
        aria-label="Вперёд"
      >
        <svg
          width="9"
          height="16"
          viewBox="0 0 9 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M0.277478 15.7243C-0.0924926 15.3568 -0.0924926 14.7609 0.277478 14.3933L6.71285 8L0.277478 1.60669C-0.0924926 1.23914 -0.0924926 0.643216 0.277478 0.275663C0.647448 -0.0918894 1.24729 -0.0918894 1.61726 0.275663L8.72252 7.33449C9.09249 7.70204 9.09249 8.29796 8.72252 8.66551L1.61726 15.7243C1.24729 16.0919 0.647448 16.0919 0.277478 15.7243Z"
            fill="#7E7E7E"
          />
        </svg>
      </button>
    </div>
  );
}
