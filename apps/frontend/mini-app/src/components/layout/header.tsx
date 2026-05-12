"use client";

import { useRouter } from "next/navigation";

import { ArrowLeft, MoreHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";

interface HeaderProps {
  title?: string;
  subtitle?: string;
  showBack?: boolean;
  showMenu?: boolean;
  onBack?: () => void;
  onMenu?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export function Header({
  title,
  subtitle,
  showBack = true,
  showMenu = false,
  onBack,
  onMenu,
  className,
  children,
}: HeaderProps) {
  const router = useRouter();

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      router.back();
    }
  };

  return (
    <header
      className={cn(
        "fixed top-0 z-40 mx-auto flex w-full max-w-[440px] items-center justify-between px-4 py-3",
        "bg-white/80 backdrop-blur-sm",
        "safe-area-top",
        className,
      )}
    >
      <div className="flex w-10 items-center">
        {showBack && (
          <button
            onClick={handleBack}
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-100"
            aria-label="Назад"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
        )}
      </div>

      <div className="flex-1 text-center">
        {title && (
          <h1 className="text-sm font-semibold leading-tight">{title}</h1>
        )}
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
        {children}
      </div>

      <div className="flex w-10 items-center justify-end">
        {showMenu && (
          <button
            onClick={onMenu}
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-100"
            aria-label="Меню"
          >
            <MoreHorizontal className="h-5 w-5" />
          </button>
        )}
      </div>
    </header>
  );
}
