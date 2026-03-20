import { useMemo } from 'react';
import { getWebApp, isTelegramEnvironment } from '../core';

type PerformanceClass = 'LOW' | 'AVERAGE' | 'HIGH';

// High-end Android device models (flagship SoCs)
const HIGH_PERF_PATTERNS = [
  /SM-S9\d{2}/i, // Samsung Galaxy S24+
  /SM-S91\d/i, // Samsung Galaxy S23+
  /SM-S90\d/i, // Samsung Galaxy S22+
  /SM-G99\d/i, // Samsung Galaxy S21+
  /SM-F9\d{2}/i, // Samsung Galaxy Z Fold/Flip
  /Pixel [7-9]/i, // Google Pixel 7+
  /2201123/i, // Xiaomi 12 Pro
  /2210132/i, // Xiaomi 13 Pro
  /IN20\d{2}/i, // OnePlus 11+
];

// Low-end Android device models
const LOW_PERF_PATTERNS = [
  /SM-A0[1-3]/i, // Samsung Galaxy A01-A03
  /SM-A1[0-3]/i, // Samsung Galaxy A10-A13
  /SM-M0[1-2]/i, // Samsung Galaxy M01-M02
  /Redmi [4-9]A/i, // Redmi A series (budget)
  /POCO C\d/i, // POCO C series (budget)
  /moto e/i, // Moto E series
  /Nokia [1-3]/i, // Nokia budget
];

function getPerformanceClass(): PerformanceClass | null {
  if (typeof navigator === 'undefined') return null;

  const ua = navigator.userAgent;

  // Only classify Android devices
  if (!/Android/i.test(ua)) return null;

  for (const pattern of HIGH_PERF_PATTERNS) {
    if (pattern.test(ua)) return 'HIGH';
  }

  for (const pattern of LOW_PERF_PATTERNS) {
    if (pattern.test(ua)) return 'LOW';
  }

  return 'AVERAGE';
}

export function usePlatform() {
  return useMemo(() => {
    const wa = getWebApp();
    const available = isTelegramEnvironment();

    return {
      platform: wa?.platform ?? '',
      version: wa?.version ?? '',
      isVersionAtLeast: (v: string): boolean => wa?.isVersionAtLeast(v) ?? false,
      performanceClass: getPerformanceClass(),
      isAvailable: available,
    };
  }, []);
}
