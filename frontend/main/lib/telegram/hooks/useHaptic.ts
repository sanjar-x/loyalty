import { useCallback } from 'react';
import type { HapticImpactStyle, HapticNotificationType } from '../types';
import { getWebApp } from '../core';

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
