'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/shared/lib/utils';
import { useAuth } from '@/features/auth';

import OrdersIcon from '@/assets/icons/orders.svg';
import ProductsIcon from '@/assets/icons/products.svg';
import ReturnsIcon from '@/assets/icons/returns.svg';
import ReviewsIcon from '@/assets/icons/reviews.svg';
import UsersIcon from '@/assets/icons/users.svg';
import SettingsIcon from '@/assets/icons/settings.svg';
import LogoutIcon from '@/assets/icons/logout.svg';

function PricingIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
    </svg>
  );
}

const navItems = [
  { href: '/admin/orders', label: 'Заказы', Icon: OrdersIcon },
  { href: '/admin/products', label: 'Товары', Icon: ProductsIcon },
  { href: '/admin/returns', label: 'Возвраты', Icon: ReturnsIcon },
  { href: '/admin/reviews', label: 'Отзывы', Icon: ReviewsIcon },
  { href: '/admin/users', label: 'Пользователи', Icon: UsersIcon },
  { href: '/admin/pricing', label: 'Цены', Icon: PricingIcon },
  { href: '/admin/settings', label: 'Настройки', Icon: SettingsIcon },
];

function normalizePath(path) {
  if (!path) return '';
  if (path === '/') return '/';
  return path.replace(/\/+$/, '');
}

function isNavActive(pathname, href) {
  const current = normalizePath(pathname);
  const target = normalizePath(href);

  if (!current || !target) return false;
  if (current === target) return true;
  return current.startsWith(`${target}/`);
}

export function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuth();
  const iconClassName =
    'shrink-0 overflow-visible text-current [&_path]:fill-current';

  return (
    <>
      <aside className="bg-app-text-dark sticky top-0 hidden h-screen w-54 px-4 py-5 text-white md:flex md:flex-col">
        <nav className="mt-1 flex flex-col gap-2">
          {navItems.map(({ href, label, Icon }) => {
            const isActive = isNavActive(pathname, href);

            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'group flex items-center gap-3 rounded-2xl px-4 py-3 text-base leading-5 font-medium tracking-normal text-[#d2d0ca] transition-colors',
                  'hover:bg-white/10 hover:text-white',
                  isActive && 'bg-[#555860] text-white',
                )}
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center">
                  <Icon className={cn('h-5 w-5.5', iconClassName)} />
                </span>
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <button
          onClick={logout}
          className="mt-auto flex items-center gap-3 rounded-2xl px-4 py-3 text-base leading-5 font-medium text-[#d2d0ca] transition-colors hover:bg-white/10 hover:text-white"
        >
          <span className="flex h-6 w-6 shrink-0 items-center justify-center">
            <LogoutIcon className={cn('h-5 w-5.5', iconClassName)} />
          </span>
          <span>Выйти</span>
        </button>
      </aside>

      <div className="bg-app-text-dark mb-5 rounded-2xl p-3 text-white md:hidden">
        <nav className="flex gap-1 overflow-auto pb-1">
          {navItems.map(({ href, label, Icon }) => {
            const isActive = isNavActive(pathname, href);

            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'flex min-w-fit items-center gap-2 rounded-xl px-3.5 py-2.5 text-base leading-5 font-medium text-[#d2d0ca]',
                  isActive && 'bg-[#555860] text-white',
                )}
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center">
                  <Icon className={cn('h-4 w-4.5', iconClassName)} />
                </span>
                <span>{label}</span>
              </Link>
            );
          })}
          <button
            onClick={logout}
            className="flex min-w-fit items-center gap-2 rounded-xl px-3.5 py-2.5 text-base leading-5 font-medium text-[#d2d0ca]"
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center">
              <LogoutIcon className={cn('h-4 w-4.5', iconClassName)} />
            </span>
            <span>Выйти</span>
          </button>
        </nav>
      </div>
    </>
  );
}
