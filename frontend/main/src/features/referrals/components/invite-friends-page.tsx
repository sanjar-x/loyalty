'use client';

import { Header } from '@/components/layout/header';
import { formatUntilDate, formatRub } from '@/lib/format';
import type { ActiveDiscount } from '@/types/referral';

// TODO: подключить реальные API-запросы когда бэкенд будет готов
// import {
//   useReferralLink,
//   useInvitedUsers,
//   useActiveDiscount,
//   useReferralStats,
// } from '../api/queries';

import { HeroIllustration } from './hero-illustration';
import { InviteLinkActions } from './invite-link-actions';
import { InvitationHistory } from './invitation-history';
import { PromoCouponCard } from './promo-coupon-card';
import { ReferralStatsCard } from './referral-stats-card';

export function InviteFriendsPage() {
  // TODO: заменить на реальные запросы
  // const { data: linkData } = useReferralLink();
  // const { data: invitedData } = useInvitedUsers();
  // const { data: discountData } = useActiveDiscount();
  // const { data: statsData } = useReferralStats();

  const inviteUrl = '';
  const invitedUsers: never[] = [];
  const discountData = null as ActiveDiscount | null;

  const stats = { visited: 0, started: 0, promocodes: 0 };

  return (
    <main className="mx-auto min-h-[var(--tg-viewport-stable-height,100vh)] max-w-[402px] pb-[calc(120px+var(--tg-safe-area-bottom,0px))]">
      <Header title="Зовите друзей" />

      {/* Spacer for fixed header */}
      <div className="h-14" />

      {/* Hero */}
      <section className="px-4 pt-5 pb-2" aria-label="Приглашение друзей">
        <HeroIllustration />

        <h1 className="text-[25px] font-extrabold leading-none tracking-tight text-[#111]">
          Зовите друзей и
          <br />
          получайте скидку
        </h1>

        <p className="mt-6 text-[15px] leading-[1.25] text-[#111]/70">
          Пригласите в приложение 3 друзей по своей ссылке и мы подарим вам
          промокод на скидку 10%.
        </p>
      </section>

      {/* Promo coupon */}
      {discountData?.code && (
        <PromoCouponCard
          percent={discountData.percent}
          until={formatUntilDate(discountData.expires_at)}
          description={`Скидка ${discountData.percent}% на любой заказ, но не более ${formatRub(discountData.max_amount)}`}
          copyValue={discountData.code}
        />
      )}

      {/* Invite link */}
      <section className="mx-4 mt-[18px]" aria-labelledby="invite-link">
        <h2
          id="invite-link"
          className="mb-[19px] pt-2.5 text-xl font-bold leading-[106%] tracking-tight text-[#111]"
        >
          Ваша ссылка для приглашений
        </h2>

        <InviteLinkActions url={inviteUrl} />
      </section>

      {/* Stats */}
      <ReferralStatsCard
        visited={stats.visited}
        started={stats.started}
        promocodes={stats.promocodes}
        isLoading={false}
      />

      {/* History */}
      <InvitationHistory
        users={invitedUsers}
        isLoading={false}
      />
    </main>
  );
}
