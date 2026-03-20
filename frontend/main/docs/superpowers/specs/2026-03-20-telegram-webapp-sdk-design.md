# Telegram WebApp SDK Module — Design Spec

**Date:** 2026-03-20
**Goal:** Production-ready, enterprise-grade React module covering 100% of Telegram Web App API with full TypeScript types, a minimal Provider, and 28+ independent hooks.
**Location:** `lib/telegram/`
**Source of truth:** https://core.telegram.org/bots/webapps (Bot API 9.x)

---

## Context

- **Project:** Telegram Mini App loyalty-system (Next.js 16, React 19, TypeScript strict)
- **Current state:** Minimal `TelegramWebApp` type (~48 lines covering only MainButton, BackButton, basic methods). 4 ad-hoc components (TelegramInit, AuthBootstrap, NavButtons, WebViewErrorAlert). No hooks, no Provider, no feature detection.
- **Target:** Complete SDK module that any component can import and use. Must work outside Telegram (graceful fallback).

---

## Architecture: Layered Core + Independent Hooks

```
┌─────────────────────────────────────────────────┐
│                  React Components               │
│     useTelegram()  useMainButton()  useHaptic() │
├─────────────────────────────────────────────────┤
│            TelegramProvider (Context)           │
│ Reactive state: user, theme, viewport, platform │
├─────────────────────────────────────────────────┤
│               Core SDK (core.ts)                │
│getWebApp(), isVersionAtLeast(), supportsFeature()│
├─────────────────────────────────────────────────┤
│             window.Telegram.WebApp              │
└─────────────────────────────────────────────────┘
```

**Key principle:** Only reactive data (theme, viewport, user) goes through React Context. Imperative APIs (haptic, clipboard, links, storage) access `window.Telegram.WebApp` directly via core.ts — no unnecessary re-renders.

---

## File Structure

```
lib/telegram/
├── types.ts                     # Full WebApp API types
├── core.ts                      # SDK accessor, version check, feature detection
├── TelegramProvider.tsx         # Minimal React Context
├── hooks/
│   ├── useTelegram.ts           # Context consumer
│   ├── useTheme.ts              # Theme params + CSS vars
│   ├── useMainButton.ts         # MainButton control
│   ├── useSecondaryButton.ts    # SecondaryButton control
│   ├── useBackButton.ts         # BackButton with callback
│   ├── useSettingsButton.ts     # SettingsButton with callback
│   ├── useHaptic.ts             # Haptic feedback
│   ├── usePopup.ts              # Popups (Promise-based)
│   ├── useQrScanner.ts          # QR scanning
│   ├── useClipboard.ts          # Clipboard read
│   ├── useLocation.ts           # Geolocation
│   ├── useBiometric.ts          # Biometric auth
│   ├── useAccelerometer.ts      # Accelerometer sensor
│   ├── useGyroscope.ts          # Gyroscope sensor
│   ├── useDeviceOrientation.ts  # Device orientation sensor
│   ├── useCloudStorage.ts       # Cloud storage (synced)
│   ├── useDeviceStorage.ts      # Device-local storage
│   ├── useSecureStorage.ts      # Encrypted storage
│   ├── useFullscreen.ts         # Fullscreen + orientation lock
│   ├── useViewport.ts           # Viewport dimensions + safe areas
│   ├── useClosingConfirmation.ts # Close warning toggle
│   ├── useVerticalSwipes.ts     # Vertical swipes toggle
│   ├── useHomeScreen.ts         # Home screen install
│   ├── useEmojiStatus.ts        # Emoji status
│   ├── useInvoice.ts            # Invoice/payment
│   ├── useShare.ts              # Share message/story/file
│   ├── useLinks.ts              # Open links/TG links/inline query
│   ├── usePlatform.ts           # Platform detection + performance class
│   └── usePermissions.ts        # requestWriteAccess, requestContact
└── index.ts                     # Barrel export
```

**Total: 1 type file + 1 core + 1 provider + 28 hooks + 1 barrel = 32 files**

---

## 1. Types (`types.ts`)

Complete typing of `window.Telegram.WebApp` covering Telegram Bot API 9.x:

### Core Types

**`WebApp`** — full interface with ALL properties and methods:

Properties:
- `initData: string` — raw init data for server validation
- `initDataUnsafe: WebAppInitData` — parsed (untrusted) init data
- `version: string` — Bot API version supported
- `platform: string` — platform name (6.4+)
- `colorScheme: 'light' | 'dark'` — current color scheme
- `themeParams: ThemeParams` — current theme colors
- `isActive: boolean` — whether Mini App is active (8.0+)
- `isExpanded: boolean` — whether expanded to max height
- `viewportHeight: number` — current visible area height (px)
- `viewportStableHeight: number` — stable viewport height (px)
- `headerColor: string` — current header color #RRGGBB (6.1+)
- `backgroundColor: string` — current background color #RRGGBB (6.1+)
- `bottomBarColor: string` — current bottom bar color #RRGGBB (7.10+)
- `isClosingConfirmationEnabled: boolean` — close confirmation state (6.2+)
- `isVerticalSwipesEnabled: boolean` — vertical swipes state (7.7+)
- `isFullscreen: boolean` — fullscreen state (8.0+)
- `isOrientationLocked: boolean` — orientation lock state (8.0+)
- `safeAreaInset: SafeAreaInset` — device safe area (8.0+)
- `contentSafeAreaInset: ContentSafeAreaInset` — content safe area (8.0+)
- `BackButton: BackButton` — back button control
- `MainButton: BottomButton` — main button control
- `SecondaryButton: BottomButton` — secondary button (7.10+)
- `SettingsButton: SettingsButton` — settings menu item (7.0+)
- `HapticFeedback: HapticFeedback` — haptic feedback (6.1+)
- `CloudStorage: CloudStorage` — cloud storage (6.9+)
- `BiometricManager: BiometricManager` — biometric auth (7.2+)
- `Accelerometer: Accelerometer` — accelerometer (8.0+)
- `Gyroscope: Gyroscope` — gyroscope (8.0+)
- `DeviceOrientation: DeviceOrientation` — device orientation (8.0+)
- `LocationManager: LocationManager` — location (8.0+)
- `DeviceStorage: DeviceStorage` — local storage 5MB (9.0+)
- `SecureStorage: SecureStorage` — encrypted storage 10 items (9.0+)

Methods:
- `isVersionAtLeast(version: string): boolean`
- `setHeaderColor(color: string): void` (6.1+)
- `setBackgroundColor(color: string): void` (6.1+)
- `setBottomBarColor(color: string): void` (7.10+)
- `enableClosingConfirmation(): void` (6.2+)
- `disableClosingConfirmation(): void` (6.2+)
- `enableVerticalSwipes(): void` (7.7+)
- `disableVerticalSwipes(): void` (7.7+)
- `requestFullscreen(): void` (8.0+)
- `exitFullscreen(): void` (8.0+)
- `lockOrientation(): void` (8.0+) — locks to CURRENT mode (portrait or landscape), no parameter
- `unlockOrientation(): void` (8.0+)
- `addToHomeScreen(): void` (8.0+)
- `checkHomeScreenStatus(callback?: (status: HomeScreenStatus) => void): void` (8.0+)
- `onEvent(eventType: EventType, handler: Function): void`
- `offEvent(eventType: EventType, handler: Function): void`
- `sendData(data: string): void` — max 4096 bytes, keyboard button only
- `switchInlineQuery(query: string, chatTypes?: ChatType[]): void` (6.7+)
- `openLink(url: string, options?: { try_instant_view?: boolean }): void` (6.1+)
- `openTelegramLink(url: string): void` (6.1+)
- `openInvoice(url: string, callback?: (status: InvoiceStatus) => void): void` (6.1+)
- `shareToStory(mediaUrl: string, params?: StoryShareParams): void` (7.8+)
- `shareMessage(msgId: number, callback?: (success: boolean) => void): void` (8.0+)
- `setEmojiStatus(emojiId: string, params?: EmojiStatusParams, callback?: (success: boolean) => void): void` (8.0+)
- `requestEmojiStatusAccess(callback?: (granted: boolean) => void): void` (8.0+)
- `downloadFile(params: DownloadFileParams, callback?: (accepted: boolean) => void): void` (8.0+)
- `showPopup(params: PopupParams, callback?: (buttonId: string | null) => void): void` (6.2+)
- `showAlert(message: string, callback?: () => void): void` (6.2+)
- `showConfirm(message: string, callback?: (ok: boolean) => void): void` (6.2+)
- `showScanQrPopup(params: ScanQrPopupParams, callback?: (text: string) => void): void` (6.4+)
- `closeScanQrPopup(): void` (6.4+)
- `readTextFromClipboard(callback?: (text: string | null) => void): void` (6.4+)
- `requestWriteAccess(callback?: (status: 'allowed' | 'cancelled') => void): void` (6.9+)
- `requestContact(callback?: (status: 'sent' | 'cancelled') => void): void` (6.9+)
- `ready(): void`
- `expand(): void`
- `close(): void`
- `hideKeyboard(): void` (9.1+)

**`WebAppInitData`** — parsed init data:
- `query_id?: string` — session ID for answerWebAppQuery
- `user?: WebAppUser`
- `receiver?: WebAppUser` — chat partner (attachment menu only)
- `chat?: WebAppChat` — chat data (attachment menu only)
- `chat_type?: ChatType`
- `chat_instance?: string` — global chat identifier
- `start_param?: string` — startapp parameter
- `can_send_after?: number` — seconds before message can send
- `auth_date: number` — Unix timestamp
- `hash: string` — HMAC-SHA256 validation hash
- `signature?: string` — Ed25519 signature (8.0+, third-party validation)

**`WebAppUser`**:
- `id: number` — 64-bit safe
- `is_bot?: boolean`
- `first_name: string`
- `last_name?: string`
- `username?: string`
- `language_code?: string` — IETF language tag
- `is_premium?: boolean`
- `added_to_attachment_menu?: boolean`
- `allows_write_to_pm?: boolean`
- `photo_url?: string` — .jpeg or .svg

**`WebAppChat`**:
- `id: number` — 64-bit safe
- `type: 'group' | 'supergroup' | 'channel'`
- `title: string`
- `username?: string`
- `photo_url?: string` — attachment menu only

**`ThemeParams`** — all 15 color properties (optional, #RRGGBB format):
- `bg_color`, `text_color`, `hint_color`, `link_color`
- `button_color`, `button_text_color`
- `secondary_bg_color` (6.1+)
- `header_bg_color` (7.0+), `bottom_bar_bg_color` (7.10+)
- `accent_text_color` (7.0+)
- `section_bg_color` (7.0+), `section_header_text_color` (7.0+), `section_separator_color` (7.6+)
- `subtitle_text_color` (7.0+), `destructive_text_color` (7.0+)

### UI Controls

**`BottomButton`** (MainButton / SecondaryButton):
> **Chaining:** All methods on BottomButton, BackButton, SettingsButton, HapticFeedback, CloudStorage, BiometricManager, Accelerometer, Gyroscope, DeviceOrientation, LocationManager, and DeviceStorage return the parent object for method chaining. Types should return `this`.

- `type: 'main' | 'secondary'` (readonly, 7.10+)
- `text: string`
- `color: string`
- `textColor: string`
- `isVisible: boolean`
- `isActive: boolean`
- `hasShineEffect: boolean` (7.10+)
- `position: BottomButtonPosition` (SecondaryButton only, 7.10+)
- `isProgressVisible: boolean` (readonly)
- `iconCustomEmojiId: string` (9.5+)
- Methods: `setText`, `onClick`, `offClick`, `show`, `hide`, `enable`, `disable`, `showProgress(leaveActive?)`, `hideProgress`, `setParams(params)` (7.10+)

**`BackButton`**: `isVisible`, `show`, `hide`, `onClick`, `offClick` (6.1+)

**`SettingsButton`**: `isVisible`, `show`, `hide`, `onClick`, `offClick` (7.0+)

### Hardware & Sensors

**`HapticFeedback`** (6.1+):
- `impactOccurred(style: HapticImpactStyle): void`
- `notificationOccurred(type: HapticNotificationType): void`
- `selectionChanged(): void`

**`Accelerometer`** (8.0+): `x`, `y`, `z` (m/s²), `isStarted`, `start(params: { refresh_rate?: number }, cb?)`, `stop(cb?)`

**`Gyroscope`** (8.0+): `x`, `y`, `z` (rad/s), `isStarted`, `start(params: { refresh_rate?: number }, cb?)`, `stop(cb?)`

**`DeviceOrientation`** (8.0+): `alpha`, `beta`, `gamma` (radians), `absolute`, `isStarted`, `start(params: { refresh_rate?: number; need_absolute?: boolean }, cb?)`, `stop(cb?)`

Sensor `refresh_rate`: 20-1000ms, default 1000ms.

**`BiometricManager`** (7.2+):
- Properties: `isInited`, `isBiometricAvailable`, `biometricType: BiometricType`, `isAccessRequested`, `isAccessGranted`, `isBiometricTokenSaved`, `deviceId`
- Methods: `init(cb?)`, `requestAccess(params: { reason?: string }, cb?)`, `authenticate(params: { reason?: string }, cb?)`, `updateBiometricToken(token, cb?)`, `openSettings()`

### Location

**`LocationManager`** (8.0+):
- Properties: `isInited`, `isLocationAvailable`, `isAccessRequested`, `isAccessGranted`
- Methods: `init(cb?)`, `getLocation(cb)`, `openSettings()`

**`LocationData`**: `latitude`, `longitude`, `altitude?`, `course?`, `speed?`, `horizontal_accuracy?`, `vertical_accuracy?`, `course_accuracy?`, `speed_accuracy?` (all Float or null)

### Storage

**`CloudStorage`** (6.9+): key 1-128 chars, value 0-4096 chars, max 1024 items
- `setItem(key, value, cb?)`, `getItem(key, cb)`, `getItems(keys, cb)`, `removeItem(key, cb?)`, `removeItems(keys, cb?)`, `getKeys(cb)`
- Callbacks: `(error: string | null, result?) => void`

**`DeviceStorage`** (9.0+): local persistent, 5MB per bot per user
- `setItem(key, value, cb?)`, `getItem(key, cb)`, `removeItem(key, cb?)`, `clear(cb?)`

**`SecureStorage`** (9.0+): encrypted (Keychain iOS / Keystore Android), max 10 items
- `setItem(key, value, cb?)`, `getItem(key, cb)` → `(error, value, canRestore)`, `restoreItem(key, cb?)`, `removeItem(key, cb?)`, `clear(cb?)`

### Popups & Dialogs

- `PopupParams`: `title?: string` (0-64), `message: string` (1-256), `buttons?: PopupButton[]` (1-3, defaults to `[{type:'close'}]`)
- `PopupButton`: `id?: string` (0-64), `type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive'`, `text?: string` (0-64, required for default/destructive)
- `ScanQrPopupParams`: `text?: string` (0-64)

### Sharing & Files

- `StoryShareParams`: `text?: string` (0-200, 0-2048 for premium), `widget_link?: StoryWidgetLink` (premium only)
- `StoryWidgetLink`: `url: string`, `name?: string` (0-48)
- `DownloadFileParams`: `url: string` (HTTPS, requires Content-Disposition + CORS), `file_name: string`
- `EmojiStatusParams`: `duration?: number` (seconds)

### Layout

- `SafeAreaInset`: `top`, `bottom`, `left`, `right` (px) — device notches/nav bars
- `ContentSafeAreaInset`: `top`, `bottom`, `left`, `right` (px) — Telegram UI elements

### Events (complete list — 41 event types)

```ts
type EventType =
  // Lifecycle
  | 'activated' | 'deactivated'
  // UI
  | 'themeChanged' | 'viewportChanged'
  | 'safeAreaChanged' | 'contentSafeAreaChanged'
  | 'mainButtonClicked' | 'secondaryButtonClicked'
  | 'backButtonClicked' | 'settingsButtonClicked'
  // Popups & Dialogs
  | 'invoiceClosed' | 'popupClosed'
  | 'qrTextReceived' | 'scanQrPopupClosed'
  | 'clipboardTextReceived'
  // Permissions
  | 'writeAccessRequested' | 'contactRequested'
  // Biometric
  | 'biometricManagerUpdated' | 'biometricAuthRequested' | 'biometricTokenUpdated'
  // Fullscreen
  | 'fullscreenChanged' | 'fullscreenFailed'
  // Home Screen
  | 'homeScreenAdded' | 'homeScreenChecked'
  // Sensors
  | 'accelerometerStarted' | 'accelerometerStopped'
  | 'accelerometerChanged' | 'accelerometerFailed'
  | 'deviceOrientationStarted' | 'deviceOrientationStopped'
  | 'deviceOrientationChanged' | 'deviceOrientationFailed'
  | 'gyroscopeStarted' | 'gyroscopeStopped'
  | 'gyroscopeChanged' | 'gyroscopeFailed'
  // Location
  | 'locationManagerUpdated' | 'locationRequested'
  // Share
  | 'shareMessageSent' | 'shareMessageFailed'
  // Emoji Status
  | 'emojiStatusSet' | 'emojiStatusFailed' | 'emojiStatusAccessRequested';
```

### Type Aliases / Enums

- `HapticImpactStyle` = `'light' | 'medium' | 'heavy' | 'rigid' | 'soft'`
- `HapticNotificationType` = `'error' | 'success' | 'warning'`
- `InvoiceStatus` = `'paid' | 'cancelled' | 'failed' | 'pending'`
- `HomeScreenStatus` = `'unsupported' | 'unknown' | 'added' | 'missed'`
- `BiometricType` = `'finger' | 'face' | 'unknown'`
- `BottomButtonPosition` = `'left' | 'right' | 'top' | 'bottom'`
- `ChatType` = `'sender' | 'private' | 'group' | 'supergroup' | 'channel'`
- `PerformanceClass` = `'LOW' | 'AVERAGE' | 'HIGH'` (derived from User-Agent parsing, not official API)
- `WriteAccessStatus` = `'allowed' | 'cancelled'`
- `ContactRequestStatus` = `'sent' | 'cancelled'`
- `FullscreenError` = `'UNSUPPORTED' | 'ALREADY_FULLSCREEN'`
- `SensorError` = `'UNSUPPORTED'`

---

## 2. Core SDK (`core.ts`)

Singleton accessor with no React dependency:

```ts
export function getWebApp(): WebApp | null;
export function getWebAppOrThrow(): WebApp;
export function isTelegramEnvironment(): boolean;
export function isVersionAtLeast(version: string): boolean;
export function supportsFeature(feature: FeatureName): boolean;
```

### Feature Version Map (from official docs)

| Feature | Min Version |
|---------|-------------|
| MainButton | 6.0 |
| BackButton | 6.1 |
| HapticFeedback | 6.1 |
| openLink, openTelegramLink, openInvoice | 6.1 |
| setHeaderColor, setBackgroundColor | 6.1 |
| showPopup, showAlert, showConfirm | 6.2 |
| enableClosingConfirmation | 6.2 |
| showScanQrPopup, closeScanQrPopup | 6.4 |
| readTextFromClipboard | 6.4 |
| platform property | 6.4 |
| switchInlineQuery | 6.7 |
| CloudStorage | 6.9 |
| requestWriteAccess, requestContact | 6.9 |
| SettingsButton | 7.0 |
| enableVerticalSwipes | 7.7 |
| shareToStory | 7.8 |
| SecondaryButton | 7.10 |
| setBottomBarColor | 7.10 |
| BottomButton.setParams | 7.10 |
| BottomButton.hasShineEffect | 7.10 |
| BiometricManager | 7.2 |
| requestFullscreen, exitFullscreen | 8.0 |
| lockOrientation, unlockOrientation | 8.0 |
| isActive, isFullscreen, isOrientationLocked | 8.0 |
| safeAreaInset, contentSafeAreaInset | 8.0 |
| LocationManager | 8.0 |
| Accelerometer, Gyroscope, DeviceOrientation | 8.0 |
| shareMessage, downloadFile | 8.0 |
| setEmojiStatus, requestEmojiStatusAccess | 8.0 |
| addToHomeScreen, checkHomeScreenStatus | 8.0 |
| emojiStatusSet/Failed/AccessRequested events | 8.0 |
| DeviceStorage | 9.0 |
| SecureStorage | 9.0 |
| hideKeyboard | 9.1 |
| BottomButton.iconCustomEmojiId | 9.5 |

---

## 3. TelegramProvider (`TelegramProvider.tsx`)

### Context Value

```ts
interface TelegramContextValue {
  webApp: WebApp | null;
  user: WebAppUser | null;
  initData: string;
  initDataUnsafe: WebAppInitData | null;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  viewportHeight: number;
  viewportStableHeight: number;
  isExpanded: boolean;
  isActive: boolean;
  safeAreaInset: SafeAreaInset;
  contentSafeAreaInset: ContentSafeAreaInset;
  platform: string;
  version: string;
  isReady: boolean;
}
```

### Behavior on Mount

1. Call `getWebApp()` from core
2. If available: `webApp.ready()`, `webApp.expand()` (mobile only)
3. Subscribe to events: `themeChanged`, `viewportChanged`, `safeAreaChanged`, `contentSafeAreaChanged`, `activated`, `deactivated`
4. Set CSS custom properties from `themeParams` (all 15 colors as `--tg-theme-*`)
5. Set `isReady = true`
6. Cleanup all subscriptions on unmount

### Fallback (outside Telegram)

All values have safe defaults:
- `webApp: null`, `user: null`, `isReady: false`, `isActive: false`
- `colorScheme: 'light'`, `themeParams: {}` (empty)
- `viewportHeight: window.innerHeight`, `viewportStableHeight: window.innerHeight`
- `platform: 'unknown'`, `version: '0.0'`

---

## 4. Hooks

### Hook Categories

**A. Context Consumers** (read from TelegramProvider):
- `useTelegram()` — main accessor for webApp, user, initData, platform, isActive
- `useTheme()` — themeParams, colorScheme, isDark
- `useViewport()` — viewport dimensions, safe areas, expand()

**B. Button Controllers** (register callbacks, manage lifecycle):
- `useMainButton(config)` — text, onClick, show/hide, progress, shine, iconCustomEmojiId, setParams
- `useSecondaryButton(config)` — same + position
- `useBackButton(onBack)` — show/hide with callback
- `useSettingsButton(onSettings)` — show/hide with callback

**C. Imperative Wrappers** (stateless, no re-render):
- `useHaptic()` — returns `{ impactOccurred, notificationOccurred, selectionChanged }`
- `useClipboard()` — returns `{ readText }: Promise<string | null>`
- `useLinks()` — returns `{ openLink, openTelegramLink, switchInlineQuery }`

**D. Promise-based Dialogs** (wrap callback API in Promises):
- `usePopup()` — `{ showPopup, showAlert, showConfirm }`
- `useQrScanner()` — `{ show, close }`
- `useInvoice()` — `{ openInvoice }: Promise<InvoiceStatus>`

**E. Storage Hooks** (wrap callback API in Promises):
- `useCloudStorage()` — `{ setItem, getItem, getItems, removeItem, removeItems, getKeys }`
- `useDeviceStorage()` — `{ setItem, getItem, removeItem, clear }`
- `useSecureStorage()` — `{ setItem, getItem, restoreItem, removeItem, clear }`

**F. Sensor Hooks** (continuous data, cleanup on unmount):
- `useAccelerometer(refreshRate?)` — `{ x, y, z, isStarted, start, stop }`
- `useGyroscope(refreshRate?)` — `{ x, y, z, isStarted, start, stop }`
- `useDeviceOrientation(refreshRate?, needAbsolute?)` — `{ alpha, beta, gamma, absolute, isStarted, start, stop }`

**G. Feature Hooks** (complex lifecycle management):
- `useLocation()` — `{ init, getLocation, openSettings, isAvailable, isGranted, data }`
- `useBiometric()` — `{ init, requestAccess, authenticate, updateToken, openSettings, isAvailable, biometricType, deviceId, isTokenSaved }`
- `useFullscreen()` — `{ request, exit, isFullscreen, lockOrientation, unlockOrientation, isOrientationLocked }`

**H. Toggle Hooks** (simple on/off):
- `useClosingConfirmation(enabled)` — enables/disables close warning
- `useVerticalSwipes(enabled)` — enables/disables vertical swipes

**I. Action Hooks** (one-shot actions):
- `useHomeScreen()` — `{ addToHomeScreen, checkStatus }`
- `useEmojiStatus()` — `{ setEmojiStatus, requestAccess }`
- `useShare()` — `{ shareMessage, shareToStory, downloadFile }`
- `usePlatform()` — `{ platform, version, isVersionAtLeast, performanceClass }`
- `usePermissions()` — `{ requestWriteAccess, requestContact }` (since 6.9)

### Return Type Convention

Every hook returns `isAvailable: boolean` alongside its methods. When `isAvailable` is `false`, all methods are safe no-ops. Example:
```ts
const { isAvailable, impactOccurred } = useHaptic();
// isAvailable === false outside Telegram or on old versions
// impactOccurred() is a no-op in that case
```

### Button Hook Constraint

`useMainButton` and `useSecondaryButton` are **single-consumer** — only one component should use each at a time. If multiple components mount the same button hook simultaneously, the last one wins. This matches Telegram's API which has a single MainButton instance.

### React 19 Strict Mode

Sensor hooks (`useAccelerometer`, `useGyroscope`, `useDeviceOrientation`) handle React 19 Strict Mode double-mount by:
1. Using `useRef` to track the actual started state
2. Calling `stop()` in cleanup effect
3. Only calling `start()` if not already started
This prevents double-subscription and sensor resource leaks.

---

## 5. Error Handling Strategy

Every hook follows a 3-layer strategy:

### Layer 1: Feature Detection
```ts
const isAvailable = isTelegramEnvironment() && supportsFeature('HapticFeedback');
```
Returns `{ isAvailable: false, ...noopMethods }` when feature is not supported. No throws, no console spam.

### Layer 2: Safe Invocation
```ts
function safeCall<T>(fn: () => T, fallback: T): T {
  try { return fn(); } catch { return fallback; }
}
```
All WebApp method calls wrapped in try/catch. Telegram WebApp SDK can throw on malformed data or race conditions.

### Layer 3: Promise Timeouts
```ts
function callbackToPromise<T>(register: (cb: (result: T) => void) => void, timeoutMs = 5000): Promise<T>
```
All callback-based APIs (CloudStorage, Biometric, etc.) wrapped in Promises with configurable timeout. Rejects with `TelegramTimeoutError` on timeout.

### Custom Error Types
```ts
export class TelegramNotAvailableError extends Error {}
export class TelegramFeatureNotSupportedError extends Error {}
export class TelegramTimeoutError extends Error {}
```

---

## 6. Integration with Existing Codebase

### Files to Replace
| Current File | Replaced By | Reason |
|---|---|---|
| `lib/types/telegram.ts` (48 lines) | `lib/telegram/types.ts` (~800 lines) | Current types cover <10% of API |
| `lib/types/telegram-globals.d.ts` | Updated to import from `lib/telegram/types` | New type paths |
| `components/blocks/telegram/TelegramInit.tsx` | `lib/telegram/TelegramProvider.tsx` | Provider replaces manual init |
| `components/blocks/telegram/TelegramNavButtons.tsx` | `useBackButton` + `useMainButton` hooks | Hooks replace component |
| `app/TelegramViewportManager.tsx` | `useViewport` inside Provider | Viewport managed by Provider |

### Files to Update (not replace, just update imports)
| File | Change |
|---|---|
| `components/blocks/telegram/WebViewErrorAlert.tsx` | Replace `window.__LM_BROWSER_DEBUG_AUTH__` check with `useTelegram().isReady` |
| `app/invite-friends/InviteLinkActions.tsx` | Replace direct `window.Telegram.WebApp` access with `useTelegram()` hook |
| `app/invite-friends/PromoCouponCard.tsx` | Replace direct `window.Telegram.WebApp` access with `useTelegram()` hook |

### Files to Keep (unchanged)
| File | Reason |
|---|---|
| `components/blocks/telegram/TelegramAuthBootstrap.tsx` | Auth logic, not WebApp API |
| `lib/auth/telegram.ts` | Server-side auth validation, independent |
| `lib/auth/browserDebugAuth.ts` | Dev-only debug auth, independent |

### DebugUser Type
`DebugUser` type moves from `lib/types/telegram.ts` to `lib/auth/browserDebugAuth.ts` where it belongs — it is a debug/auth concept, not a Telegram WebApp API type. Update `lib/types/telegram-globals.d.ts` to import `DebugUser` from `@/lib/auth/browserDebugAuth`.

### Layout Change
`app/layout.tsx` currently renders:
```tsx
<TelegramInit />
<TelegramAuthBootstrap />
<TelegramNavButtons />
<TelegramViewportManager />
```

After migration:
```tsx
<TelegramProvider>
  <TelegramAuthBootstrap />
  {children}
</TelegramProvider>
```

`TelegramNavButtons` and `TelegramViewportManager` are removed — their functionality is consumed via hooks by individual pages.

---

## 7. Barrel Export (`index.ts`)

```ts
// Types
export type { WebApp, WebAppUser, WebAppInitData, WebAppChat, ThemeParams,
  BottomButton, BackButton, SettingsButton, HapticFeedback,
  CloudStorage, DeviceStorage, SecureStorage,
  BiometricManager, LocationManager, LocationData,
  Accelerometer, Gyroscope, DeviceOrientation,
  SafeAreaInset, ContentSafeAreaInset,
  PopupParams, PopupButton, ScanQrPopupParams,
  StoryShareParams, StoryWidgetLink, DownloadFileParams, EmojiStatusParams,
  EventType, HapticImpactStyle, HapticNotificationType,
  InvoiceStatus, HomeScreenStatus, BiometricType,
  BottomButtonPosition, ChatType } from './types';

// Core
export { getWebApp, getWebAppOrThrow, isTelegramEnvironment,
  isVersionAtLeast, supportsFeature } from './core';

// Errors
export { TelegramNotAvailableError, TelegramFeatureNotSupportedError,
  TelegramTimeoutError } from './core';

// Provider
export { TelegramProvider, useTelegramContext } from './TelegramProvider';

// All 28 hooks
export { useTelegram } from './hooks/useTelegram';
export { useTheme } from './hooks/useTheme';
export { useMainButton } from './hooks/useMainButton';
export { useSecondaryButton } from './hooks/useSecondaryButton';
export { useBackButton } from './hooks/useBackButton';
export { useSettingsButton } from './hooks/useSettingsButton';
export { useHaptic } from './hooks/useHaptic';
export { usePopup } from './hooks/usePopup';
export { useQrScanner } from './hooks/useQrScanner';
export { useClipboard } from './hooks/useClipboard';
export { useLocation } from './hooks/useLocation';
export { useBiometric } from './hooks/useBiometric';
export { useAccelerometer } from './hooks/useAccelerometer';
export { useGyroscope } from './hooks/useGyroscope';
export { useDeviceOrientation } from './hooks/useDeviceOrientation';
export { useCloudStorage } from './hooks/useCloudStorage';
export { useDeviceStorage } from './hooks/useDeviceStorage';
export { useSecureStorage } from './hooks/useSecureStorage';
export { useFullscreen } from './hooks/useFullscreen';
export { useViewport } from './hooks/useViewport';
export { useClosingConfirmation } from './hooks/useClosingConfirmation';
export { useVerticalSwipes } from './hooks/useVerticalSwipes';
export { useHomeScreen } from './hooks/useHomeScreen';
export { useEmojiStatus } from './hooks/useEmojiStatus';
export { useInvoice } from './hooks/useInvoice';
export { useShare } from './hooks/useShare';
export { useLinks } from './hooks/useLinks';
export { usePlatform } from './hooks/usePlatform';
export { usePermissions } from './hooks/usePermissions';
```

Usage:
```ts
import { useTelegram, useMainButton, useHaptic } from '@/lib/telegram';
```

---

## Success Criteria

1. `npx next build` passes with 0 errors
2. `npx tsc --noEmit` passes with 0 errors
3. All 28 hooks export correctly from barrel
4. Provider renders in layout.tsx without errors
5. Outside Telegram: all hooks return safe defaults, no throws
6. Inside Telegram: all features work on supported versions
7. Zero runtime errors on unsupported platform/version combinations
8. CSS custom properties set for all 15 theme colors
9. No duplicate Telegram-related code across codebase
10. All 41 event types typed in EventType union
