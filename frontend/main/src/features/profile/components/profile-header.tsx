"use client";

import Link from "next/link";

import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

interface ProfileHeaderProps {
  name: string;
  avatar?: string | null;
  className?: string;
}

export function ProfileHeader({ name, avatar, className }: ProfileHeaderProps) {
  return (
    <div className={cn("flex items-center gap-4 py-4", className)}>
      <div className="h-16 w-16 shrink-0 overflow-hidden rounded-full bg-gray-100">
        {avatar ? (
          <img src={avatar} alt={name} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gray-200 text-xl font-bold text-gray-500">
            {name.charAt(0).toUpperCase()}
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1">
        <h2 className="text-base font-semibold">{name}</h2>
        <Link
          href="/profile/settings"
          className="flex items-center gap-1 text-sm text-muted-foreground"
        >
          <span>Настройки</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
