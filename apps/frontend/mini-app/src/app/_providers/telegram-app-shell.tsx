'use client';

import type { ReactNode } from 'react';

import { TelegramAuthBootstrap } from '@/features/auth';
import {
  TelegramBackButtonController,
  TelegramEnvironmentAlert,
  TelegramSdkProvider,
} from '@/features/telegram';

interface TelegramAppShellProps {
  children: ReactNode;
}

/**
 * App-level Telegram composition that wires the SDK provider to auth and UI bootstrap.
 */
export function TelegramAppShell({ children }: TelegramAppShellProps) {
  return (
    <TelegramSdkProvider>
      <TelegramAuthBootstrap />
      <TelegramBackButtonController />
      {children}
      <TelegramEnvironmentAlert />
    </TelegramSdkProvider>
  );
}
