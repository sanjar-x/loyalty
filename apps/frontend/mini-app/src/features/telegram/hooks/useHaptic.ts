'use client';

import { useCallback } from 'react';

import { getWebApp } from '../core';

import type { HapticImpactStyle, HapticNotificationType } from '../types';

export function useHaptic() {
  const webApp = getWebApp();
  const haptic = webApp?.HapticFeedback ?? null;
  const isAvailable = haptic !== null;

  const impactOccurred = useCallback(
    (style: HapticImpactStyle) => {
      haptic?.impactOccurred(style);
    },
    [haptic],
  );

  const notificationOccurred = useCallback(
    (type: HapticNotificationType) => {
      haptic?.notificationOccurred(type);
    },
    [haptic],
  );

  const selectionChanged = useCallback(() => {
    haptic?.selectionChanged();
  }, [haptic]);

  return {
    impactOccurred,
    notificationOccurred,
    selectionChanged,
    isAvailable,
  };
}
