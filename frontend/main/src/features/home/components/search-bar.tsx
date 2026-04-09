'use client';

import { useRouter } from 'next/navigation';

import { Search } from 'lucide-react';

import { cn } from '@/lib/utils';

interface SearchBarProps {
  className?: string;
}

export function SearchBar({ className }: SearchBarProps) {
  const router = useRouter();

  const handleFocus = () => {
    router.push('/search');
  };

  return (
    <div className={cn('px-4', className)}>
      <div
        role="button"
        tabIndex={0}
        onClick={handleFocus}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') handleFocus();
        }}
        className={cn(
          'flex items-center gap-2.5 rounded-xl bg-gray-100 px-3.5 py-2.5',
          'cursor-pointer transition-colors active:bg-gray-200',
        )}
      >
        <Search size={18} className="shrink-0 text-gray-400" aria-hidden />
        <span className="text-sm text-gray-400 select-none">Поиск</span>
      </div>
    </div>
  );
}
