"use client";
import { useState } from "react";
import InfoCard from "./InfoCard";
import Link from "next/link";

import { cn } from "@/lib/format/cn";
import styles from "./FriendsSection.module.css";
import cx from "clsx";

export default function FriendsSection() {
  const cards = [
    { title: "Наша\n команда", icon: "/img/FriendsSection1.webp" },
    { title: "Оплата\n и сплит", icon: "/img/brokenPrice.svg" },
    { title: "Доставка \nи отслеживание", icon: "/img/FriendsSection3.webp" },
    { title: "Условия\nвозврата", icon: "/img/FriendsSection4.webp" },
    { title: "Гарантии\n и безопасность", icon: "/img/FriendsSection5.webp" },
    {
      title: "POIZON –\n только\n оригинал",
      icon: "/img/FriendsSection6.webp",
    },
    { title: "Подарочные\nкарты", icon: "/img/FriendsSection7.svg" },
    { title: "Чат\nс поддержкой", icon: "/img/FriendsSection8.webp" },
  ];

  const friends = [
    { id: 1, avatar: "/img/Ava-1.webp", name: "Friend1" },
    { id: 2, avatar: "/img/Ava-2.webp", name: "Friend2" },
    { id: 3, avatar: "/img/Ava-3.webp", name: "Friend3" },
  ];

  const [imgErrorMap, setImgErrorMap] = useState({});
  return (
    <div className={styles.root}>
      <div className={styles.cardsOuter}>
        <div className={cn(styles.cardsRow, "scrollbar-hide")}>
          {cards.map((c, index) => (
            <div key={c.title} className={styles.cardItem}>
              <InfoCard title={c.title} iconSrc={c.icon} index={index} />
            </div>
          ))}
        </div>
      </div>

      <div className={styles.blocks}>
        <Link href="/invite-friends" className={styles.block}>
          <div className={styles.row}>
            <div>
              <span className={styles.title}>Зовите друзей</span>
              <span className={styles.subtitle}>Дарим скидку 10%</span>
            </div>
            <img
              className={styles.arrow}
              src="/icons/global/Wrap.svg"
              alt="arrow"
            />
          </div>
          <div className={styles.avatarsRow}>
            <div className={styles.avatars}>
              {friends.map((friend) => (
                <div key={friend.id} className={styles.avatar}>
                  {!imgErrorMap[friend.id] ? (
                    <img
                      src={friend.avatar}
                      alt={friend.name}
                      className={styles.avatarImg}
                      onError={() =>
                        setImgErrorMap((prev) => ({
                          ...prev,
                          [friend.id]: true,
                        }))
                      }
                    />
                  ) : (
                    <span className={cx(styles.c1, styles.tw1)}>👤</span>
                  )}
                </div>
              ))}
            </div>
            <button type="button" className={styles.addBtn}>
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
                  strokeWidth="1.63977"
                />
              </svg>
            </button>
          </div>
        </Link>

        <Link href="/promo" className={cn(styles.block, styles.blockSecondary)}>
          <div className={styles.row}>
            <div>
              <span className={cn(styles.title)} style={{ marginBottom: 3 }}>
                Баллы
              </span>
              <span className={styles.pointsSubtitle}>1 балл = 1 ₽</span>
            </div>
            <img
              className={styles.arrow}
              src="/icons/global/Wrap.svg"
              alt="arrow"
            />
          </div>
          <p className={styles.pointsValue}>—</p>
        </Link>
      </div>
    </div>
  );
}
