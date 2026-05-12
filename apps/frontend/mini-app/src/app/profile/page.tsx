"use client";

import { ProfileHeader } from "@/features/profile/components/profile-header";
import { ProfileMenuSection } from "@/features/profile/components/profile-menu-section";
import { useTelegram } from "@/features/telegram";
import { useMe } from "@/features/user/api/queries";
import { asNonEmptyTrimmedString, asSafeImageSrc } from "@/lib/format/validation";

function MenuIcon({ src, alt = "" }: { src: string; alt?: string }) {
  return <img src={src} alt={alt} className="h-6 w-6" />;
}

export default function ProfilePage() {
  const { data: me, isLoading, isFetching } = useMe();
  const { user: tgUser } = useTelegram();

  const firstName =
    asNonEmptyTrimmedString((me as Record<string, unknown> | undefined)?.first_name) ??
    asNonEmptyTrimmedString(tgUser?.first_name as unknown);
  const lastName =
    asNonEmptyTrimmedString((me as Record<string, unknown> | undefined)?.last_name) ??
    asNonEmptyTrimmedString(tgUser?.last_name as unknown);
  const fullName = [firstName, lastName].filter(Boolean).join(" ") || null;

  const username =
    asNonEmptyTrimmedString((me as Record<string, unknown> | undefined)?.username) ??
    asNonEmptyTrimmedString(tgUser?.username as unknown);

  const displayName =
    fullName ??
    username ??
    (isLoading || isFetching ? "Загрузка…" : "Пользователь");

  const avatar =
    asSafeImageSrc((me as Record<string, unknown> | undefined)?.photo_url) ||
    asSafeImageSrc(tgUser?.photo_url as unknown) ||
    "/img/profileLogo.png";

  return (
    <div className="space-y-4 pt-5">
      <ProfileHeader name={displayName} avatar={avatar} />

      {/* Add to home */}
      <div className="px-4">
        <ProfileMenuSection
          items={[
            {
              text: "Добавить на экран «Домой»",
              icon: <MenuIcon src="/icons/profile/home-icon.svg" />,
              href: "/profile/add-to-home",
            },
          ]}
        />
      </div>

      {/* Orders section */}
      <div className="px-4">
        <ProfileMenuSection
          items={[
            {
              text: "Заказы",
              icon: <MenuIcon src="/icons/profile/orders-icon.svg" />,
              href: "/profile/orders",
            },
            {
              text: "Купленные товары",
              icon: <MenuIcon src="/icons/profile/bag-icon.svg" />,
              href: "/profile/purchased",
            },
            {
              text: "Возвраты",
              icon: <MenuIcon src="/icons/profile/undo-icon.svg" />,
              href: "/profile/returns",
            },
          ]}
        />
      </div>

      {/* Points section */}
      <div className="px-4">
        <ProfileMenuSection
          items={[
            {
              text: "Баллы",
              icon: <MenuIcon src="/icons/profile/points-icon.svg" />,
              href: "/promo",
            },
            {
              text: "Пригласить друзей",
              icon: <MenuIcon src="/icons/profile/addFriends.svg" />,
              href: "/invite-friends",
            },
            {
              text: "Промокоды",
              icon: <MenuIcon src="/icons/profile/promo-icon.svg" />,
              href: "/profile/promocodes",
              badge: 5,
            },
          ]}
        />
      </div>

      {/* Reviews section */}
      <div className="px-4">
        <ProfileMenuSection
          items={[
            {
              text: "Отзывы",
              icon: <MenuIcon src="/icons/profile/stars-icon.svg" />,
              href: "/profile/reviews",
            },
            {
              text: "Избранное",
              icon: <MenuIcon src="/icons/profile/heart-icon.svg" />,
              href: "/favorites",
            },
            {
              text: "Просмотренное",
              icon: <MenuIcon src="/icons/profile/viewed-icon.svg" />,
              href: "/profile/viewed",
            },
          ]}
        />
      </div>

      {/* Settings section */}
      <div className="px-4">
        <ProfileMenuSection
          items={[
            {
              text: "Настройки",
              icon: <MenuIcon src="/icons/profile/settings-icon.svg" />,
              href: "/profile/settings",
            },
            {
              text: "О сервисе",
              icon: <MenuIcon src="/icons/profile/info-icon.svg" />,
              href: "/profile/about",
            },
            {
              text: "Чат с поддержкой",
              icon: <MenuIcon src="/icons/profile/chat-icon.svg" />,
              href: "/profile/support",
            },
          ]}
        />
      </div>
    </div>
  );
}
