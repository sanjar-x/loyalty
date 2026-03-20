"use client";

import Footer from "@/components/layout/Footer";
import { Check, Minus } from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/format/cn";
import Container from "@/components/layout/Layout";
import Header from "@/components/layout/Header";
import InviteLinkActions from "./InviteLinkActions";
import PromoCouponCard from "./PromoCouponCard";
import styles from "./page.module.css";

import { formatRuDateTime, formatUntilDate } from "@/lib/format/date";

function isExistingStatus(status: string | null | undefined): boolean {
  const s = String(status ?? "").toLowerCase();
  return (
    s.includes("уже") ||
    s.includes("польз") ||
    s.includes("зарегистр") ||
    s.includes("registered") ||
    s.includes("exists")
  );
}

export default function InviteFriends() {
  const linkData = {} as { link?: string }, isLinkLoading = false, isLinkFetching = false;
  const invitedData = {} as { items?: Record<string, unknown>[] }, isInvitedLoading = false, isInvitedFetching = false;
  const discountData = {} as { code?: string; percent?: number; expires_at?: string; max_amount?: number }, isDiscountLoading = false, isDiscountFetching = false;
  const statsData = {} as { clicked?: number; installed?: number; promo_issued_total?: number }, isStatsLoading = false, isStatsFetching = false;

  const inviteUrl = linkData?.link || "";
  const stats = {
    visited: statsData?.clicked ?? 0,
    started: statsData?.installed ?? 0,
    promocodes: statsData?.promo_issued_total ?? 0,
  };

  const isLinkPending = isLinkLoading || isLinkFetching;
  const isDiscountPending = isDiscountLoading || isDiscountFetching;
  const isStatsPending = isStatsLoading || isStatsFetching;
  const isInvitedPending = isInvitedLoading || isInvitedFetching;

  const invitedUsers = Array.isArray(invitedData?.items)
    ? invitedData.items
    : [];

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Зовите друзей и получайте скидку",
    description:
      "Пригласите друзей и получите скидку. Уникальная ссылка для приглашения в приложение.",
    mainEntity: {
      "@type": "Offer",
      name: "Скидка за приглашение друзей",
      description:
        "Пригласите 3 друзей в приложение и получите промокод на скидку 10%",
      eligibleQuantity: {
        "@type": "QuantitativeValue",
        value: 3,
        unitText: "друзья",
      },
      price: "0",
      priceCurrency: "RUB",
    },
    interactionStatistic: [
      {
        "@type": "InteractionCounter",
        interactionType: "https://schema.org/ClickAction",
        name: "Переходы по ссылке",
        userInteractionCount: stats.visited,
      },
      {
        "@type": "InteractionCounter",
        interactionType: "https://schema.org/ActivateAction",
        name: "Запуски приложения",
        userInteractionCount: stats.started,
      },
      {
        "@type": "InteractionCounter",
        interactionType: "https://schema.org/ReceiveAction",
        name: "Полученные промокоды",
        userInteractionCount: stats.promocodes,
      },
    ],
  };

  return (
    <main
      className={cn("tg-viewport", styles.page)}
      itemScope
      itemType="https://schema.org/WebPage"
    >
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <Container className={styles.container}>
        <Header title="Зовите друзей" />
        <section className={styles.hero} aria-label="Invite friends">
          <div className={styles.illustration} aria-hidden="true">
            <div className={styles.bubbles}>
              <Image
                src="/icons/invite-friends/1-avatar.svg"
                alt=""
                width={51}
                height={51}
                className={cn(styles.bubble, styles.b1)}
                priority
              />
              <Image
                src="/icons/invite-friends/2-avatar.svg"
                alt=""
                width={50}
                height={50}
                className={cn(styles.bubble, styles.b2)}
                priority
              />
              <Image
                src="/icons/invite-friends/3-avatar.svg"
                alt=""
                width={54}
                height={53}
                className={cn(styles.bubble, styles.b3)}
                priority
              />

              <Image
                src="/icons/invite-friends/4-avatar.svg"
                alt=""
                width={50}
                height={50}
                className={cn(styles.bubble, styles.b4)}
                priority
              />
              <Image
                src="/icons/invite-friends/5-avatar.svg"
                alt=""
                width={55}
                height={55}
                className={cn(styles.bubble, styles.b5)}
                priority
              />
              <Image
                src="/icons/invite-friends/6-avatar.svg"
                alt=""
                width={50}
                height={50}
                className={cn(styles.bubble, styles.b6)}
                priority
              />

              <div className={styles.centerBubble}>
                <Image
                  src="/icons/invite-friends/7-avatar.svg"
                  alt=""
                  width={100}
                  height={100}
                  className={styles.centerAvatar}
                  priority
                />
              </div>
            </div>
          </div>

          <h1 className={styles.title} itemProp="name">
            Зовите друзей и
            <br />
            получайте скидку
          </h1>

          <p className={styles.subtitle} itemProp="description">
            Пригласите в приложение 3 друзей по своей ссылке и мы подарим вам
            промокод на скидку 10%.
          </p>
        </section>

        {isDiscountPending ? (
          <section
            className={styles.promoCard}
            aria-label="Промокод"
            aria-busy="true"
          >
            <div className={styles.promoHeader} aria-hidden="true">
              <div className={styles.skeletonPromoPercent} />
              <div className={styles.skeletonPromoUntil} />
            </div>
            <div className={styles.skeletonPromoDesc} aria-hidden="true" />
            <div className={styles.skeletonPromoDescShort} aria-hidden="true" />
            <div className={styles.skeletonPromoButton} aria-hidden="true" />
          </section>
        ) : discountData?.code ? (
          <PromoCouponCard
            percent={discountData?.percent ?? 0}
            until={formatUntilDate(discountData?.expires_at)}
            description={`Скидка ${discountData?.percent ?? 0}% на любой заказ, но не более ${Number(discountData?.max_amount ?? 0).toLocaleString("ru-RU")} ₽`}
            copyValue={discountData.code}
          />
        ) : null}

        <section
          className={styles.section}
          aria-labelledby="invite-link"
          itemScope
          itemType="https://schema.org/Offer"
        >
          <h2 id="invite-link" className={styles.sectionTitle} itemProp="name">
            Ваша ссылка для приглашений
          </h2>

          <meta itemProp="price" content="0" />
          <meta itemProp="priceCurrency" content="RUB" />

          {isLinkPending ? (
            <div className={styles.actions} aria-busy="true">
              <div className={styles.skeletonInput} aria-hidden="true" />
              <div className={styles.skeletonShareButton} aria-hidden="true" />
              <div className={styles.hint} />
            </div>
          ) : (
            <InviteLinkActions url={inviteUrl} />
          )}
        </section>

        <section
          className={styles.statsCard}
          aria-label="Статистика"
          aria-busy={isStatsPending ? "true" : undefined}
        >
          <div className={styles.statRow}>
            <span className={styles.statLabel}>Перешло по ссылке</span>
            {isStatsPending ? (
              <span className={styles.skeletonStatValue} aria-hidden="true" />
            ) : (
              <strong className={styles.statValue}>{stats.visited}</strong>
            )}
          </div>
          <div className={styles.divider} />
          <div className={styles.statRow}>
            <span className={styles.statLabel}>Запустило приложение</span>
            {isStatsPending ? (
              <span className={styles.skeletonStatValue} aria-hidden="true" />
            ) : (
              <strong className={styles.statValue}>{stats.started}</strong>
            )}
          </div>
          <div className={styles.divider} />
          <div className={styles.statRow}>
            <span className={styles.statLabel}>Получено промокодов</span>
            {isStatsPending ? (
              <span className={styles.skeletonStatValue} aria-hidden="true" />
            ) : (
              <strong className={styles.statValue}>{stats.promocodes}</strong>
            )}
          </div>
        </section>

        <section className={styles.history} aria-labelledby="invite-history">
          <h2 id="invite-history" className={styles.historyTitle}>
            История приглашений
          </h2>

          <ul className={styles.historyList}>
            {isInvitedPending
              ? Array.from({ length: 3 }).map((_, idx) => (
                  <li
                    key={`sk-${idx}`}
                    className={styles.historyItem}
                    aria-hidden="true"
                  >
                    <div className={styles.skeletonAvatar} />
                    <div className={styles.skeletonHistoryBody}>
                      <div>
                        <div className={styles.skeletonHistoryName} />
                        <div className={styles.skeletonHistoryDate} />
                      </div>
                      <div className={styles.skeletonHistoryStatus} />
                    </div>
                  </li>
                ))
              : invitedUsers.map((user: Record<string, unknown>) => {
                  const status = String(user?.status ?? "");
                  const isExisting = isExistingStatus(status);
                  const name = String(
                    user?.invitee_username ||
                    user?.invitee_tg_id ||
                    (user?.invitee_id != null
                      ? String(user.invitee_id)
                      : "Пользователь"));
                  const date = formatRuDateTime(user?.created_at as string | undefined);

                  return (
                    <li
                      key={String(
                        user?.invite_id ??
                        user?.invitee_id ??
                        user?.invitee_tg_id ??
                        name
                      )}
                      className={styles.historyItem}
                    >
                      <Image
                        src="/icons/invite-friends/7-avatar.svg"
                        alt={`Аватар пользователя ${name}`}
                        width={44}
                        height={44}
                        className={styles.userAvatar}
                      />

                      <div className={styles.userBody}>
                        <div className={styles.userMain}>
                          <div className={styles.userName}>{name}</div>
                          <div className={styles.userDate}>{date}</div>
                        </div>

                        <div className={styles.userStatus}>
                          <span
                            className={styles.statusIcon}
                            aria-hidden="true"
                          >
                            {isExisting ? (
                              <Minus size={20} />
                            ) : (
                              <Check size={18} />
                            )}
                          </span>
                          <span className={styles.statusText}>{status}</span>
                        </div>
                      </div>
                    </li>
                  );
                })}
          </ul>
        </section>
      </Container>

      <Footer />
    </main>
  );
}
