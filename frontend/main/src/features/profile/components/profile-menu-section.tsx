"use client";

import { cn } from "@/lib/utils";

import { ProfileMenuItem } from "./profile-menu-item";

interface MenuItemData {
  text: string;
  icon?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  fontWeight?: 400 | 500 | 600;
  badge?: number | string;
}

interface ProfileMenuSectionProps {
  items: MenuItemData[];
  className?: string;
}

export function ProfileMenuSection({ items, className }: ProfileMenuSectionProps) {
  return (
    <div className={cn("overflow-hidden rounded-xl", className)}>
      {items.map((item, index) => (
        <ProfileMenuItem
          key={item.href ?? item.text}
          {...item}
          isFirst={index === 0}
          isLast={index === items.length - 1}
        />
      ))}
    </div>
  );
}
