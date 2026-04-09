"use client";

import Link from "next/link";

import { ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ProfileMenuItemProps {
  text: string;
  icon?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  fontWeight?: 400 | 500 | 600;
  badge?: number | string;
  isFirst?: boolean;
  isLast?: boolean;
}

export function ProfileMenuItem({
  text,
  icon,
  href,
  onClick,
  fontWeight = 500,
  badge,
  isFirst = false,
  isLast = false,
}: ProfileMenuItemProps) {
  const fontClass =
    fontWeight === 400
      ? "font-normal"
      : fontWeight === 600
        ? "font-semibold"
        : "font-medium";

  const radiusClass = cn(
    isFirst && isLast && "rounded-xl",
    isFirst && !isLast && "rounded-t-xl",
    isLast && !isFirst && "rounded-b-xl",
    !isFirst && !isLast && "rounded-none",
  );

  const content = (
    <div
      className={cn(
        "flex items-center gap-3 bg-[#f4f3f1] px-4 py-3.5",
        radiusClass,
        !isLast && "border-b border-white/50",
      )}
    >
      {icon && <div className="flex h-5 w-5 shrink-0 items-center justify-center">{icon}</div>}
      <span className={cn("flex-1 text-sm", fontClass)}>{text}</span>
      {badge !== undefined && (
        <Badge variant="orange" size="sm">
          {badge}
        </Badge>
      )}
      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {content}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button onClick={onClick} className="block w-full text-left">
        {content}
      </button>
    );
  }

  return content;
}
