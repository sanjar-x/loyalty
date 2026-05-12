'use client';

import { useCallback, useRef, useState } from 'react';

import { Check } from 'lucide-react';

import { copyText } from '@/lib/format';
import { cn } from '@/lib/utils';
import { useLinks } from '@/features/telegram';

interface InviteLinkActionsProps {
  url: string;
}

export function InviteLinkActions({ url }: InviteLinkActionsProps) {
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { openTelegramLink, isAvailable: isTgAvailable } = useLinks();

  const doCopy = useCallback(async () => {
    const ok = await copyText(url);

    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
      return;
    }

    inputRef.current?.focus();
    inputRef.current?.select();
  }, [url]);

  const onShare = useCallback(async () => {
    const shareText = `Присоединяйся к LOYALTY: ${url}`;

    if (navigator.share) {
      try {
        await navigator.share({ text: shareText, url });
        return;
      } catch {
        // User cancelled or API unavailable — fall through
      }
    }

    if (isTgAvailable) {
      const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(shareText)}`;
      openTelegramLink(shareUrl);
      return;
    }

    await doCopy();
  }, [url, isTgAvailable, openTelegramLink, doCopy]);

  return (
    <div className="grid gap-2.5">
      <div className="relative w-full">
        <input
          ref={inputRef}
          type="text"
          aria-label="Ссылка для приглашения"
          value={url}
          readOnly
          onClick={(e) => e.currentTarget.select()}
          className="h-[55px] w-full rounded-2xl bg-[#f4f3f1] pl-4 pr-[52px] text-[15px] leading-none text-[#111] outline-none focus-visible:ring-2 focus-visible:ring-[#111]/20"
        />

        <button
          type="button"
          onClick={doCopy}
          aria-label={copied ? 'Скопировано' : 'Скопировать ссылку'}
          className={cn(
            'absolute right-2.5 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-[10px] active:scale-[0.98]',
            copied ? 'bg-[#5c4bff]/10' : 'bg-transparent',
          )}
        >
          {copied ? (
            <Check className="h-[21px] w-[21px] text-[#5c4bff]" aria-hidden="true" />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src="/icons/invite-friends/copy.svg"
              alt=""
              className="h-[21px] w-[21px]"
            />
          )}
        </button>
      </div>

      <button
        type="button"
        onClick={onShare}
        aria-label="Поделиться ссылкой"
        className="h-[55px] w-full rounded-2xl bg-[#2d2d2d] text-[15px] font-semibold text-white transition-[transform,filter] duration-150 active:translate-y-px active:brightness-[0.98]"
      >
        Поделиться
      </button>
    </div>
  );
}
