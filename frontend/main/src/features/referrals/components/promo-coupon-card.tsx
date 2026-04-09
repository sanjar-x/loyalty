'use client';

import { useCallback, useState } from 'react';

import { copyText } from '@/lib/format';

interface PromoCouponCardProps {
  percent: number;
  until: string;
  description: string;
  copyValue: string;
}

export function PromoCouponCard({ percent, until, description, copyValue }: PromoCouponCardProps) {
  const [copied, setCopied] = useState(false);

  const doCopy = useCallback(async () => {
    const ok = await copyText(copyValue);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }
  }, [copyValue]);

  return (
    <section
      className="mx-4 mt-3.5 rounded-[18px] border border-black/[0.04] bg-[#f4f3f1] p-4"
      aria-label="Промокод"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-[44px] font-medium leading-none tracking-tight text-[#111]">
          {percent}%
        </div>
        <div className="pt-1 text-sm leading-tight text-[#111]/60">
          {until}
        </div>
      </div>

      <p className="mt-2.5 max-w-[250px] text-sm leading-[1.35] text-[#111]/80">
        {description}
      </p>

      <button
        type="button"
        onClick={doCopy}
        aria-label="Скопировать промокод"
        className="mt-3.5 h-12 w-full rounded-2xl bg-[#2d2d2d] text-[15px] font-semibold text-white transition-[transform,filter] duration-150 active:translate-y-px active:brightness-[0.98]"
      >
        {copied ? 'Скопировано' : 'Скопировать'}
      </button>
    </section>
  );
}
