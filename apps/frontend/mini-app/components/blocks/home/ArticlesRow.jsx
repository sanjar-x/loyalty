'use client';

import InfoCard from './InfoCard';
import { cn } from '@/lib/format/cn';
import { useDragToScroll } from '@/lib/hooks/useDragToScroll';
import styles from './ArticlesRow.module.css';

const cards = [
  {
    title: 'Наша\n команда',
    icon: '/img/FriendsSection1.webp',
    href: 'https://teletype.in/@loyaltymarket/our-team',
  },
  {
    title: 'Оплата\n и сплит',
    icon: '/img/brokenPrice.webp',
    href: 'https://teletype.in/@loyaltymarket/payment-and-split',
  },
  {
    title: 'Доставка \nи отслеживание',
    icon: '/img/FriendsSection3.webp',
    href: 'https://teletype.in/@loyaltymarket/delivery-and-tracking',
  },
  {
    title: 'Условия\nвозврата',
    icon: '/img/FriendsSection4.webp',
    href: 'https://teletype.in/@loyaltymarket/terms-of-return',
  },
  {
    title: 'Гарантии\n и безопасность',
    icon: '/img/FriendsSection5.webp',
    href: 'https://teletype.in/@loyaltymarket/guarantees-and-security',
  },
  {
    title: 'POIZON –\n только\n оригинал',
    icon: '/img/FriendsSection6.webp',
    href: 'https://teletype.in/@loyaltymarket/poizon-only-original',
  },
  {
    title: 'Подарочные\nкарты',
    icon: '/img/FriendsSection7.webp',
    href: 'https://teletype.in/@loyaltymarket/gift-cards',
  },
  { title: 'Чат\nс поддержкой', icon: '/img/FriendsSection8.webp' },
];

export default function ArticlesRow() {
  // Desktop swipe — touch'da hook avtomatik o'chiriladi.
  const rowRef = useDragToScroll();
  return (
    <div className={styles.outer}>
      <div ref={rowRef} className={cn(styles.row, 'scrollbar-hide')}>
        {cards.map((c, index) => (
          <div key={c.title} className={styles.item}>
            {c.href ? (
              <div
                role="button"
                tabIndex={0}
                style={{
                  textDecoration: 'none',
                  color: 'inherit',
                  cursor: 'pointer',
                  WebkitTapHighlightColor: 'transparent',
                }}
                onClick={() => {
                  const tg = typeof window !== 'undefined' && window.Telegram?.WebApp;
                  if (tg?.openLink) {
                    tg.openLink(c.href, { try_instant_view: true });
                  } else {
                    window.open(c.href, '_blank', 'noopener');
                  }
                }}
              >
                <InfoCard title={c.title} iconSrc={c.icon} index={index} />
              </div>
            ) : (
              <InfoCard title={c.title} iconSrc={c.icon} index={index} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
