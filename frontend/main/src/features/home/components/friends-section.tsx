'use client';

import Image from 'next/image';
import Link from 'next/link';

import { cn } from '@/lib/utils';

// ── Static info cards data ──────────────────────────────────────────

interface InfoCardData {
  title: string;
  icon: string;
  href?: string;
}

const INFO_CARDS: InfoCardData[] = [
  {
    title: 'Наша\nкоманда',
    icon: '/img/FriendsSection1.webp',
    href: 'https://teletype.in/@loyaltymarket/our-team',
  },
  {
    title: 'Оплата\nи сплит',
    icon: '/img/brokenPrice.webp',
    href: 'https://teletype.in/@loyaltymarket/payment-and-split',
  },
  {
    title: 'Доставка\nи отслеживание',
    icon: '/img/FriendsSection3.webp',
    href: 'https://teletype.in/@loyaltymarket/delivery-and-tracking',
  },
  {
    title: 'Условия\nвозврата',
    icon: '/img/FriendsSection4.webp',
    href: 'https://teletype.in/@loyaltymarket/terms-of-return',
  },
  {
    title: 'Гарантии\nи безопасность',
    icon: '/img/FriendsSection5.webp',
    href: 'https://teletype.in/@loyaltymarket/guarantees-and-security',
  },
  {
    title: 'POIZON –\nтолько\nоригинал',
    icon: '/img/FriendsSection6.webp',
    href: 'https://teletype.in/@loyaltymarket/poizon-only-original',
  },
  {
    title: 'Подарочные\nкарты',
    icon: '/img/FriendsSection7.webp',
    href: 'https://teletype.in/@loyaltymarket/gift-cards',
  },
  {
    title: 'Чат\nс поддержкой',
    icon: '/img/FriendsSection8.webp',
  },
];

// ── Info card component ─────────────────────────────────────────────

function InfoCard({ title, icon }: { title: string; icon: string }) {
  return (
    <div className="relative flex h-28 w-28 shrink-0 flex-col justify-between overflow-hidden rounded-2xl bg-gray-100 pt-3 pl-3">
      <p className="text-xs leading-tight font-medium whitespace-pre-line text-black">
        {title}
      </p>
      <div className="flex justify-end">
        <Image
          src={icon}
          alt=""
          width={79}
          height={79}
          className="absolute right-0 bottom-0 object-contain"
        />
      </div>
    </div>
  );
}

// ── Open link helper (Telegram-aware) ───────────────────────────────

function openExternalLink(href: string) {
  const tg =
    typeof window !== 'undefined'
      ? (window as unknown as Record<string, unknown>).Telegram
      : undefined;
  const webApp = (tg as Record<string, unknown> | undefined)?.WebApp as
    | { openLink?: (url: string, options?: { try_instant_view: boolean }) => void }
    | undefined;

  if (webApp?.openLink) {
    webApp.openLink(href, { try_instant_view: true });
  } else {
    window.open(href, '_blank', 'noopener');
  }
}

// ── Marquee (auto-scrolling row) ────────────────────────────────────

function Marquee({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden">
      <div className="flex w-max animate-[marquee_30s_linear_infinite] gap-2">
        {children}
        {/* Duplicate for seamless loop */}
        {children}
      </div>
    </div>
  );
}

// ── Friends section (invite block + points) ─────────────────────────

const FRIENDS = [
  { id: 1, avatar: '/img/Ava-1.webp' },
  { id: 2, avatar: '/img/Ava-2.webp' },
  { id: 3, avatar: '/img/Ava-3.webp' },
];

interface FriendsSectionProps {
  className?: string;
}

export function FriendsSection({ className }: FriendsSectionProps) {
  return (
    <section className={cn('space-y-2', className)}>
      {/* Info cards marquee */}
      <Marquee>
        {INFO_CARDS.map((card) =>
          card.href ? (
            <div
              key={card.title}
              role="button"
              tabIndex={0}
              onClick={() => openExternalLink(card.href!)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') openExternalLink(card.href!);
              }}
              className="cursor-pointer [-webkit-tap-highlight-color:transparent]"
            >
              <InfoCard title={card.title} icon={card.icon} />
            </div>
          ) : (
            <div key={card.title}>
              <InfoCard title={card.title} icon={card.icon} />
            </div>
          ),
        )}
      </Marquee>

      {/* Invite friends + Points blocks */}
      <div className="flex gap-2 px-4">
        {/* Invite friends */}
        <Link
          href="/invite-friends"
          className="flex flex-1 flex-col rounded-2xl bg-gray-100 p-4 no-underline [-webkit-tap-highlight-color:transparent]"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="block text-[15px] font-bold text-black">
                Зовите друзей
              </span>
              <span className="block text-xs text-black">
                Дарим скидку 10%
              </span>
            </div>
            <img
              src="/icons/global/Wrap.svg"
              alt=""
              className="shrink-0"
              aria-hidden
            />
          </div>

          <div className="mt-3 flex items-center justify-between gap-3">
            <div className="-ml-0.5 flex">
              {FRIENDS.map((friend) => (
                <div
                  key={friend.id}
                  className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-gray-200 [&:not(:first-child)]:-ml-2.5"
                >
                  <img
                    src={friend.avatar}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                </div>
              ))}
            </div>

            <button
              type="button"
              className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full bg-white"
              aria-label="Добавить друга"
            >
              <svg
                width="34"
                height="34"
                viewBox="0 0 34 34"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect width="34" height="34" rx="17" fill="white" />
                <path
                  d="M17.2826 10.5V17M17.2826 23.5V17M17.2826 17H10.5M17.2826 17H23.5"
                  stroke="#2D2D2D"
                  strokeWidth="1.64"
                />
              </svg>
            </button>
          </div>
        </Link>

        {/* Points */}
        <Link
          href="/promo"
          className="flex flex-1 flex-col rounded-2xl bg-gray-100 p-4 no-underline [-webkit-tap-highlight-color:transparent]"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="mb-0.5 block text-[15px] font-bold text-black">
                Баллы
              </span>
              <span className="block text-xs text-[#111]">1 балл = 1 ₽</span>
            </div>
            <img
              src="/icons/global/Wrap.svg"
              alt=""
              className="shrink-0"
              aria-hidden
            />
          </div>

          <p className="mt-4 text-[23px] leading-tight font-medium text-black">
            11
          </p>
        </Link>
      </div>
    </section>
  );
}
