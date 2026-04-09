import type { WebApp } from './types';

// =============================================================================
// Error types
// =============================================================================

export class TelegramNotAvailableError extends Error {
  override name = 'TelegramNotAvailableError' as const;
}

export class TelegramFeatureNotSupportedError extends Error {
  override name = 'TelegramFeatureNotSupportedError' as const;
  constructor(public feature: string) {
    super(`Feature "${feature}" is not supported in this Telegram version`);
  }
}

export class TelegramTimeoutError extends Error {
  override name = 'TelegramTimeoutError' as const;
}

// =============================================================================
// Accessor
// =============================================================================

export function getWebApp(): WebApp | null {
  if (typeof window === 'undefined') return null;
  return window.Telegram?.WebApp ?? null;
}

export function getWebAppOrThrow(): WebApp {
  const wa = getWebApp();
  if (!wa) throw new TelegramNotAvailableError('Telegram WebApp is not available');
  return wa;
}

export function isTelegramEnvironment(): boolean {
  return getWebApp() !== null;
}

// =============================================================================
// Version
// =============================================================================

export function isVersionAtLeast(version: string): boolean {
  const wa = getWebApp();
  if (!wa) return false;
  return wa.isVersionAtLeast(version);
}

// =============================================================================
// Feature detection
// =============================================================================

const FEATURE_VERSIONS = {
  MainButton: '6.0',
  BackButton: '6.1',
  HapticFeedback: '6.1',
  openLink: '6.1',
  showPopup: '6.2',
  enableClosingConfirmation: '6.2',
  showScanQrPopup: '6.4',
  readTextFromClipboard: '6.4',
  switchInlineQuery: '6.7',
  CloudStorage: '6.9',
  requestWriteAccess: '6.9',
  requestContact: '6.9',
  SettingsButton: '7.0',
  BiometricManager: '7.2',
  enableVerticalSwipes: '7.7',
  shareToStory: '7.8',
  SecondaryButton: '7.10',
  setBottomBarColor: '7.10',
  requestFullscreen: '8.0',
  lockOrientation: '8.0',
  LocationManager: '8.0',
  Accelerometer: '8.0',
  Gyroscope: '8.0',
  DeviceOrientation: '8.0',
  shareMessage: '8.0',
  downloadFile: '8.0',
  setEmojiStatus: '8.0',
  addToHomeScreen: '8.0',
  DeviceStorage: '9.0',
  SecureStorage: '9.0',
  hideKeyboard: '9.1',
} as const;

export type FeatureName = keyof typeof FEATURE_VERSIONS;

export function supportsFeature(feature: FeatureName): boolean {
  return isVersionAtLeast(FEATURE_VERSIONS[feature]);
}

// =============================================================================
// Utilities
// =============================================================================

export function callbackToPromise<T>(
  register: (cb: (result: T) => void) => void,
  timeoutMs = 5000,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new TelegramTimeoutError(`Telegram callback timed out after ${timeoutMs}ms`)),
      timeoutMs,
    );
    register((result) => {
      clearTimeout(timer);
      resolve(result);
    });
  });
}

export function safeCall<T>(fn: () => T, fallback: T): T {
  try {
    return fn();
  } catch {
    return fallback;
  }
}
