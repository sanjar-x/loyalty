"use client";

import { memo, useEffect, useRef } from "react";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import {
  IconCart,
  IconCatalog,
  IconFavorites,
  IconHome,
  IconPoizon,
  IconProfile,
  type TabIconProps,
} from "@/components/ui/icons";
import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/utils";
import type { Cart } from "@/types";

// ---------------------------------------------------------------------------
// Tab configuration
// ---------------------------------------------------------------------------

interface TabRoute {
  key: string;
  href: string;
  icon: React.ComponentType<TabIconProps>;
  label: string;
  hasBadge?: boolean;
}

const TAB_ROUTES: TabRoute[] = [
  { key: "home", href: "/", icon: IconHome, label: "Главная" },
  { key: "poizon", href: "/poizon", icon: IconPoizon, label: "Poizon" },
  { key: "catalog", href: "/catalog", icon: IconCatalog, label: "Каталог" },
  { key: "favorites", href: "/favorites", icon: IconFavorites, label: "Избранное" },
  { key: "cart", href: "/cart", icon: IconCart, label: "Корзина", hasBadge: true },
  { key: "profile", href: "/profile", icon: IconProfile, label: "Профиль" },
];

// ---------------------------------------------------------------------------
// Route → active tab resolution
// ---------------------------------------------------------------------------

function resolveActiveTab(pathname: string): string | null {
  if (pathname === "/" || pathname.startsWith("/search")) return "home";

  for (const tab of TAB_ROUTES) {
    if (tab.href !== "/" && pathname.startsWith(tab.href)) {
      return tab.key;
    }
  }

  return null;
}

// ---------------------------------------------------------------------------
// Footer height CSS variable sync
// ---------------------------------------------------------------------------

function useFooterHeight(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const sync = () => {
      document.documentElement.style.setProperty(
        "--lm-footer-height",
        `${el.offsetHeight}px`,
      );
    };

    sync();

    const ro = new ResizeObserver(sync);
    ro.observe(el);

    return () => {
      ro.disconnect();
      document.documentElement.style.removeProperty("--lm-footer-height");
    };
  }, [ref]);
}

// ---------------------------------------------------------------------------
// Footer component
// ---------------------------------------------------------------------------

export const Footer = memo(function Footer() {
  const pathname = usePathname();
  const navRef = useRef<HTMLElement>(null);

  useFooterHeight(navRef);

  const { data: cart } = useQuery({
    queryKey: queryKeys.cart.all,
    queryFn: () => apiClient.get("api/v1/cart").json<Cart>(),
  });

  const cartCount = cart?.totalItems ?? 0;
  const activeTab = resolveActiveTab(pathname);

  return (
    <nav
      ref={navRef}
      className={cn(
        "fixed bottom-0 left-0 right-0 z-40 mx-auto w-full max-w-[448px]",
        "border-t-[2.5px] border-[#dbd7d7] bg-white",
        "pb-[var(--tg-safe-area-bottom,0px)]",
      )}
      aria-label="Bottom navigation"
    >
      <div className="flex items-center justify-between px-[23px] py-[15px]">
        {TAB_ROUTES.map((tab) => {
          const isActive = tab.key === activeTab;
          const Icon = tab.icon;

          return (
            <Link
              key={tab.key}
              href={tab.href}
              className="inline-flex items-center justify-center [-webkit-tap-highlight-color:transparent]"
              aria-current={isActive ? "page" : undefined}
              aria-label={tab.label}
            >
              <span className="relative inline-flex">
                <Icon filled={isActive} />

                {tab.hasBadge && cartCount > 0 && (
                  <Badge
                    variant="orange"
                    className="absolute -right-3 -top-2 h-[18px] min-w-[18px] px-1 text-[11px] font-semibold leading-[18px]"
                  >
                    {cartCount > 99 ? "99+" : cartCount}
                  </Badge>
                )}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
});
