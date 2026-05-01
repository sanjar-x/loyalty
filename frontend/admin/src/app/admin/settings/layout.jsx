'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/shared/lib/utils';
import styles from './layout.module.css';

const navItems = [
  { href: '/admin/settings/referrals', label: 'Реферальные ссылки' },
  { href: '/admin/settings/promocodes', label: 'Промокоды' },
  { href: '/admin/settings/brands', label: 'Бренды' },
  { href: '/admin/settings/categories', label: 'Категории' },
  { href: '/admin/settings/roles', label: 'Роли' },
  { href: '/admin/settings/suppliers', label: 'Поставщики' },
  { href: '/admin/settings/pricing-formulas', label: 'Формулы цен' },
  { href: '/admin/settings/staff', label: 'Сотрудники' },
];

export default function SettingsLayout({ children }) {
  const pathname = usePathname();

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>Настройки</h1>

      <div className={styles.grid}>
        <aside className={styles.sideCard}>
          <nav className={styles.sideNav}>
            {navItems.map((item) => {
              const active = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    styles.sideLink,
                    active && styles.sideLinkActive,
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        <div className={styles.contentCard}>{children}</div>
      </div>
    </section>
  );
}
