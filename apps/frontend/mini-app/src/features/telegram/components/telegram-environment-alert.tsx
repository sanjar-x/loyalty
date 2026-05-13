'use client';

import { useEffect, useState } from 'react';

import { isBrowserDebugAuthEnabled } from '@/features/auth';

import { useTelegram } from '../hooks/useTelegram';

export function TelegramEnvironmentAlert() {
  const { isReady, isAvailable } = useTelegram();
  const [delayElapsed, setDelayElapsed] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const timerId = window.setTimeout(() => {
      setDelayElapsed(true);
    }, 150);

    return () => {
      window.clearTimeout(timerId);
    };
  }, []);

  const shouldShow = delayElapsed && isReady && !isAvailable && !isBrowserDebugAuthEnabled();

  if (!shouldShow) return null;

  return (
    <div
      role="alert"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-black/10 bg-white/95 px-4 py-3 text-sm text-gray-900 backdrop-blur-sm"
    >
      Telegram WebApp не найден. Откройте приложение в Telegram.
    </div>
  );
}
