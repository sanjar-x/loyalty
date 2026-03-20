# Telegram WebApp SDK Module — Design Spec

**Date:** 2026-03-20
**Goal:** Production-ready, enterprise-grade React module covering 100% of Telegram Web App API with full TypeScript types, a minimal Provider, and 25+ independent hooks.
**Location:** `lib/telegram/`

---

## Context

- **Project:** Telegram Mini App loyalty-system (Next.js 16, React 19, TypeScript strict)
- **Current state:** Minimal `TelegramWebApp` type (~48 lines covering only MainButton, BackButton, basic methods). 4 ad-hoc components (TelegramInit, AuthBootstrap, NavButtons, WebViewErrorAlert). No hooks, no Provider, no feature detection.
- **Target:** Complete SDK module that any component can import and use. Must work outside Telegram (graceful fallback).

---

## Architecture: Layered Core + Independent Hooks

```
┌─────────────────────────────────────────────────┐
│                  React Components                │
│     useTelegram()  useMainButton()  useHaptic()  │
├─────────────────────────────────────────────────┤
│              TelegramProvider (Context)           │
│   Reactive state: user, theme, viewport, platform │
├─────────────────────────────────────────────────┤
│                   Core SDK (core.ts)              │
│   getWebApp(), isVersionAtLeast(), supportsFeature() │
├─────────────────────────────────────────────────┤
│             window.Telegram.WebApp               │
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

Complete typing of `window.Telegram.WebApp` covering Telegram Bot API 8.0+:

### Core Types
- `WebApp` — full interface with all properties and methods (including readable state: `headerColor`, `backgroundColor`, `bottomBarColor`, `isClosingConfirmationEnabled`, `isVerticalSwipesEnabled`, `isFullscreen`, `isOrientationLocked`, `isActive`, and method `setBottomBarColor`)
- `WebAppInitData` — parsed init data (query_id, user, receiver, chat, chat_type, chat_instance, start_param, can_send_after, auth_date, hash)
- `WebAppUser` — id, is_bot, first_name, last_name, username, language_code, is_premium, added_to_attachment_menu, allows_write_to_pm, photo_url
- `WebAppChat` — id, type, title, username, photo_url
- `ThemeParams` — all 15 color properties (bg_color, text_color, hint_color, link_color, button_color, button_text_color, secondary_bg_color, header_bg_color, bottom_bar_bg_color, accent_text_color, section_bg_color, section_header_text_color, section_separator_color, subtitle_text_color, destructive_text_color)

### UI Controls
- `BottomButton` — text, color, textColor, isVisible, isActive, hasShineEffect, position, isProgressVisible, show/hide/enable/disable/showProgress/hideProgress/setText/onClick/offClick/setParams
- `BackButton` — isVisible, show/hide/onClick/offClick
- `SettingsButton` — isVisible, show/hide/onClick/offClick

### Hardware & Sensors
- `HapticFeedback` — impactOccurred(style), notificationOccurred(type), selectionChanged()
- `Accelerometer` — x, y, z, isStarted, start(params, cb?), stop(cb?)
- `Gyroscope` — same shape
- `DeviceOrientation` — alpha, beta, gamma, absolute, isStarted, start(params, cb?), stop(cb?)
- `BiometricManager` — isInited, isBiometricAvailable, biometricType, isAccessRequested, isAccessGranted, isBiometricTokenSaved, deviceId, init/requestAccess/authenticate/updateBiometricToken/openSettings

### Location
- `LocationManager` — isInited, isLocationAvailable, isAccessRequested, isAccessGranted, init/getLocation/openSettings
- `LocationData` — latitude, longitude, altitude, course, speed, horizontal_accuracy, vertical_accuracy

### Storage
- `CloudStorage` — setItem/getItem/getItems/removeItem/removeItems/getKeys (callback-based)
- `DeviceStorage` — setItem/getItem/removeItem/clear (callback-based)
- `SecureStorage` — setItem/getItem/restoreItem/removeItem/clear (callback-based)

### Popups & Dialogs
- `PopupParams` — title?, message, buttons[]
- `PopupButton` — id?, type ('default'|'ok'|'close'|'cancel'|'destructive'), text?
- `ScanQrPopupParams` — text?

### Sharing & Files
- `StoryShareParams` — media_url, text?, widget_link?
- `StoryWidgetLink` — url, name?
- `DownloadFileParams` — url, file_name
- `EmojiStatusParams` — custom_emoji_id, duration?

### Layout
- `SafeAreaInset` — top, bottom, left, right
- `ContentSafeAreaInset` — top, bottom, left, right

### Events
- `EventType` — union type of all 40+ event names
- Event callback signatures for each event type

### Enums
- `HapticImpactStyle` = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'
- `HapticNotificationType` = 'error' | 'success' | 'warning'
- `InvoiceStatus` = 'paid' | 'cancelled' | 'failed' | 'pending'
- `HomeScreenStatus` = 'unsupported' | 'unknown' | 'added' | 'missed'
- `BiometricType` = 'finger' | 'face' | 'unknown'
- `BottomButtonPosition` = 'left' | 'right' | 'top' | 'bottom'
- `ChatType` = 'sender' | 'private' | 'group' | 'supergroup' | 'channel'
- `PerformanceClass` = 'LOW' | 'AVERAGE' | 'HIGH'

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

### Feature Version Map

| Feature | Min Version |
|---------|-------------|
| MainButton | 6.0 |
| BackButton | 6.1 |
| HapticFeedback | 6.1 |
| showPopup | 6.2 |
| showScanQrPopup | 6.4 |
| readTextFromClipboard | 6.4 |
| CloudStorage | 6.9 |
| requestWriteAccess | 6.9 |
| requestContact | 6.9 |
| SettingsButton | 7.0 |
| requestFullscreen | 7.0 |
| SecondaryButton | 7.10 |
| setBottomBarColor | 7.10 |
| BiometricManager | 7.2 |
| LocationManager | 8.0 |
| Accelerometer | 8.0 |
| Gyroscope | 8.0 |
| DeviceOrientation | 8.0 |
| DeviceStorage | 8.0 |
| SecureStorage | 8.0 |
| shareMessage | 8.0 |
| downloadFile | 8.0 |
| EmojiStatus | 8.0 |
| HomeScreen | 8.0 |

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
- `webApp: null`, `user: null`, `isReady: false`
- `colorScheme: 'light'`, `themeParams: {}` (empty)
- `viewportHeight: window.innerHeight`, `viewportStableHeight: window.innerHeight`
- `platform: 'unknown'`, `version: '0.0'`

---

## 4. Hooks

### Hook Categories

**A. Context Consumers** (read from TelegramProvider):
- `useTelegram()` — main accessor for webApp, user, initData, platform
- `useTheme()` — themeParams, colorScheme, isDark
- `useViewport()` — viewport dimensions, safe areas, expand()

**B. Button Controllers** (register callbacks, manage lifecycle):
- `useMainButton(config)` — text, onClick, show/hide, progress, shine, icon
- `useSecondaryButton(config)` — same + position
- `useBackButton(onBack)` — show/hide with callback
- `useSettingsButton(onSettings)` — show/hide with callback

**C. Imperative Wrappers** (stateless, no re-render):
- `useHaptic()` — returns `{ impactOccurred, notificationOccurred, selectionChanged }`
- `useClipboard()` — returns `{ readText }: Promise<string>`
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
| `lib/types/telegram.ts` (48 lines) | `lib/telegram/types.ts` (~600 lines) | Current types cover <10% of API |
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
export type { WebApp, WebAppUser, WebAppInitData, ThemeParams, ... } from './types';

// Core
export { getWebApp, isTelegramEnvironment, isVersionAtLeast, supportsFeature } from './core';

// Provider
export { TelegramProvider, useTelegramContext } from './TelegramProvider';

// Hooks
export { useTelegram } from './hooks/useTelegram';
export { useTheme } from './hooks/useTheme';
// ... all 27 hooks
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
