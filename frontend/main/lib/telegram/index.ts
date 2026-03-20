// =============================================================================
// Barrel export — lib/telegram
// =============================================================================

// Types
export type {
  WebApp, WebAppUser, WebAppInitData, WebAppChat, ThemeParams,
  BottomButton, BottomButtonParams, BackButton, SettingsButton,
  HapticFeedback as HapticFeedbackType,
  CloudStorage as CloudStorageType, DeviceStorage as DeviceStorageType, SecureStorage as SecureStorageType,
  BiometricManager as BiometricManagerType, LocationManager as LocationManagerType, LocationData,
  Accelerometer as AccelerometerType, Gyroscope as GyroscopeType, DeviceOrientation as DeviceOrientationType,
  SafeAreaInset, ContentSafeAreaInset,
  PopupParams, PopupButton, ScanQrPopupParams,
  StoryShareParams, StoryWidgetLink, DownloadFileParams, EmojiStatusParams,
  BiometricRequestAccessParams, BiometricAuthenticateParams,
  EventType, HapticImpactStyle, HapticNotificationType,
  InvoiceStatus, HomeScreenStatus, BiometricType,
  BottomButtonPosition, ChatType, WriteAccessStatus, ContactRequestStatus,
  FullscreenError, SensorError,
} from './types';

// Core
export {
  getWebApp, getWebAppOrThrow, isTelegramEnvironment,
  isVersionAtLeast, supportsFeature,
  TelegramNotAvailableError, TelegramFeatureNotSupportedError, TelegramTimeoutError,
  callbackToPromise, safeCall,
} from './core';
export type { FeatureName } from './core';

// Provider
export { TelegramProvider, useTelegramContext } from './TelegramProvider';

// Hooks
export { useTelegram } from './hooks/useTelegram';
export { useTheme } from './hooks/useTheme';
export { useViewport } from './hooks/useViewport';
export { useMainButton } from './hooks/useMainButton';
export { useSecondaryButton } from './hooks/useSecondaryButton';
export { useBackButton } from './hooks/useBackButton';
export { useSettingsButton } from './hooks/useSettingsButton';
export { useHaptic } from './hooks/useHaptic';
export { useClipboard } from './hooks/useClipboard';
export { useLinks } from './hooks/useLinks';
export { usePopup } from './hooks/usePopup';
export { useQrScanner } from './hooks/useQrScanner';
export { useInvoice } from './hooks/useInvoice';
export { usePermissions } from './hooks/usePermissions';
export { useCloudStorage } from './hooks/useCloudStorage';
export { useDeviceStorage } from './hooks/useDeviceStorage';
export { useSecureStorage } from './hooks/useSecureStorage';
export { useAccelerometer } from './hooks/useAccelerometer';
export { useGyroscope } from './hooks/useGyroscope';
export { useDeviceOrientation } from './hooks/useDeviceOrientation';
export { useLocation } from './hooks/useLocation';
export { useBiometric } from './hooks/useBiometric';
export { useFullscreen } from './hooks/useFullscreen';
export { useClosingConfirmation } from './hooks/useClosingConfirmation';
export { useVerticalSwipes } from './hooks/useVerticalSwipes';
export { useHomeScreen } from './hooks/useHomeScreen';
export { useEmojiStatus } from './hooks/useEmojiStatus';
export { useShare } from './hooks/useShare';
export { usePlatform } from './hooks/usePlatform';
