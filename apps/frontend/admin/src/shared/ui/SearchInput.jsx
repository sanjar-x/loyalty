'use client';

import SearchIcon from '@/assets/icons/search.svg';
import { cn } from '@/shared/lib/utils';

export function SearchInput({
  value,
  onChange,
  placeholder = 'Поиск',
  ariaLabel,
  className,
}) {
  return (
    <div
      className={cn(
        'bg-app-card flex h-[46px] items-center gap-[10px] rounded-[50px] px-[13px] py-3',
        className,
      )}
    >
      <SearchIcon className="h-5 w-5 shrink-0 text-[#1f1f1f]" />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel || placeholder}
        className="h-5 w-full bg-transparent p-0 text-base leading-5 font-medium tracking-normal text-[#000000] outline-none placeholder:text-[#000000]"
      />
    </div>
  );
}
