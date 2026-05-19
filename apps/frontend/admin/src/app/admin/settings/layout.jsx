'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useMemo } from 'react';

import { cn } from '@/shared/lib/utils';

import styles from './layout.module.css';

// Sections group ~10 settings entries by domain so the operator can scan
// instead of reading a flat list end-to-end. Order: most-trafficked groups
// first; "Доступ" (staff/roles/permissions) lives below business config
// because admins touch it less often.
const NAV_SECTIONS = [
  {
    label: 'Каталог',
    items: [
      { href: '/admin/settings/brands', label: 'Бренды' },
      { href: '/admin/settings/categories', label: 'Категории' },
      { href: '/admin/settings/attributes', label: 'Атрибуты' },
      {
        href: '/admin/settings/attribute-templates',
        label: 'Шаблоны атрибутов',
      },
    ],
  },
  {
    label: 'Маркетинг',
    items: [
      { href: '/admin/settings/promocodes', label: 'Промокоды' },
      { href: '/admin/settings/referrals', label: 'Реферальные ссылки' },
    ],
  },
  {
    label: 'Логистика и цены',
    items: [
      { href: '/admin/settings/suppliers', label: 'Поставщики' },
      {
        href: '/admin/settings/logistics-providers',
        label: 'Провайдеры доставки',
      },
      { href: '/admin/settings/pricing-formulas', label: 'Формулы цен' },
    ],
  },
  {
    label: 'Доступ',
    items: [{ href: '/admin/settings/staff', label: 'Сотрудники' }],
  },
];

// Flat lookup for the breadcrumb. Computed once at module load — sections
// are static and the cost would otherwise repeat on every render.
const PATH_TO_LABEL = new Map(
  NAV_SECTIONS.flatMap((s) => s.items.map((i) => [i.href, i.label])),
);

export default function SettingsLayout({ children }) {
  const pathname = usePathname();
  // Strip trailing slash so /admin/settings/staff/ and /admin/settings/staff
  // both match.
  const normalized = pathname?.replace(/\/$/, '') ?? '';
  const activeLabel = useMemo(
    () => PATH_TO_LABEL.get(normalized) ?? null,
    [normalized],
  );

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>Настройки</h1>

      <div className={styles.grid}>
        <aside className={styles.sideCard}>
          <nav className={styles.sideNav} aria-label="Разделы настроек">
            {NAV_SECTIONS.map((section) => (
              <div key={section.label} className={styles.sideSection}>
                <p className={styles.sideSectionLabel}>{section.label}</p>
                <ul className={styles.sideSectionList}>
                  {section.items.map((item) => {
                    const active = normalized === item.href;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          aria-current={active ? 'page' : undefined}
                          className={cn(
                            styles.sideLink,
                            active && styles.sideLinkActive,
                          )}
                        >
                          {item.label}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </nav>
        </aside>

        <div className={styles.contentCard}>
          {activeLabel && (
            <nav aria-label="Хлебные крошки" className={styles.breadcrumb}>
              <span className={styles.breadcrumbItem}>Настройки</span>
              <span aria-hidden="true" className={styles.breadcrumbSep}>
                ›
              </span>
              <span
                className={`${styles.breadcrumbItem} ${styles.breadcrumbCurrent}`}
                aria-current="page"
              >
                {activeLabel}
              </span>
            </nav>
          )}
          {children}
        </div>
      </div>
    </section>
  );
}
