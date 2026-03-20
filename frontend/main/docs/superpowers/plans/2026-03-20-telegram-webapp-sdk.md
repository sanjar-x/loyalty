# Telegram WebApp SDK Module — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready `lib/telegram/` module with complete TypeScript types, core SDK, React Provider, and 28 hooks covering 100% of Telegram WebApp API (Bot API 9.x).

**Architecture:** Three layers — Core SDK (pure TS, no React) → TelegramProvider (minimal Context for reactive state) → Independent hooks (each accesses WebApp directly via core for imperative APIs, or reads Context for reactive data). This prevents unnecessary re-renders.

**Tech Stack:** React 19, TypeScript 5 (strict mode), Next.js 16 App Router

**Spec:** `docs/superpowers/specs/2026-03-20-telegram-webapp-sdk-design.md`

---

## Phase 1: Foundation (types + core + provider)

### Task 1: Create Complete WebApp Type Definitions

**Files:**
- Create: `lib/telegram/types.ts`

This is the largest single file (~800 lines). It defines every type, interface, and union from the Telegram WebApp API (Bot API 9.x). All 41 event types, all sub-objects, all callback signatures.

- [ ] **Step 1: Create `lib/telegram/types.ts`**

Write the complete type file with these sections in order:

1. **Type aliases/enums** — `HapticImpactStyle`, `HapticNotificationType`, `InvoiceStatus`, `HomeScreenStatus`, `BiometricType`, `BottomButtonPosition`, `ChatType`, `WriteAccessStatus`, `ContactRequestStatus`, `FullscreenError`, `SensorError`, `EventType` (43-member union — count all events from spec list, not the heading which says 41)

2. **Data types** — `SafeAreaInset`, `ContentSafeAreaInset`, `LocationData` (9 fields), `ThemeParams` (15 color fields), `PopupButton`, `PopupParams`, `ScanQrPopupParams`, `StoryWidgetLink`, `StoryShareParams`, `DownloadFileParams`, `EmojiStatusParams`, `BiometricRequestAccessParams`, `BiometricAuthenticateParams`

3. **Sub-object interfaces** — `BackButton`, `SettingsButton`, `BottomButton` (with `setParams`, `iconCustomEmojiId`, `hasShineEffect`, `position`), `HapticFeedback`, `CloudStorage`, `DeviceStorage`, `SecureStorage`, `BiometricManager`, `Accelerometer`, `Gyroscope`, `DeviceOrientation`, `LocationManager`
   - ALL sub-object methods return `this` for chaining (e.g. `show(): this`, `impactOccurred(): this`). This includes HapticFeedback, not just buttons/storage.
   - CloudStorage callbacks: `(error: string | null, result?) => void`
   - SecureStorage.getItem callback: `(error: string | null, value: string, canRestore: boolean) => void`

4. **Init data types** — `WebAppUser`, `WebAppChat`, `WebAppInitData` (including `signature` field)

5. **Main WebApp interface** — all 30+ properties and 30+ methods with exact signatures from the spec. Every method with its minimum version annotated in JSDoc comments.

Key implementation details:
- `BottomButton.type` is `readonly`
- `BottomButton.isProgressVisible` is `readonly`
- Sensor `start` params include `refresh_rate` (20-1000, default 1000)
- `DeviceOrientation` start params also include `need_absolute`
- `lockOrientation()` has **no parameters** (locks to current mode)
- `openLink` has optional `options?: { try_instant_view?: boolean }`
- `sendData` accepts `string` (max 4096 bytes)
- `hideKeyboard()` is 9.1+

- [ ] **Step 2: Verify build**

Run: `npx next build 2>&1 | grep -E "(Compiled|Failed)"`
Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add lib/telegram/types.ts
git commit -m "feat(telegram-sdk): add complete WebApp type definitions (Bot API 9.x, 41 events)"
```

---

### Task 2: Create Core SDK

**Files:**
- Create: `lib/telegram/core.ts`

Pure TypeScript, zero React dependency. Provides safe access to `window.Telegram.WebApp`.

- [ ] **Step 1: Create `lib/telegram/core.ts`**

Implement:

```ts
import type { WebApp } from './types';

// --- Error types ---
export class TelegramNotAvailableError extends Error { name = 'TelegramNotAvailableError'; }
export class TelegramFeatureNotSupportedError extends Error { name = 'TelegramFeatureNotSupportedError'; }
export class TelegramTimeoutError extends Error { name = 'TelegramTimeoutError'; }

// --- Accessor ---
export function getWebApp(): WebApp | null {
  if (typeof window === 'undefined') return null;
  return (window as any).Telegram?.WebApp ?? null;
}

export function getWebAppOrThrow(): WebApp {
  const wa = getWebApp();
  if (!wa) throw new TelegramNotAvailableError('Telegram WebApp is not available');
  return wa;
}

export function isTelegramEnvironment(): boolean {
  return getWebApp() !== null;
}

// --- Version comparison ---
export function isVersionAtLeast(version: string): boolean {
  const wa = getWebApp();
  if (!wa) return false;
  return wa.isVersionAtLeast(version);
}

// --- Feature detection ---
type FeatureName = keyof typeof FEATURE_VERSIONS;

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
  shareMessage: '8.0',
  downloadFile: '8.0',
  setEmojiStatus: '8.0',
  addToHomeScreen: '8.0',
  DeviceStorage: '9.0',
  SecureStorage: '9.0',
  hideKeyboard: '9.1',
} as const;

export function supportsFeature(feature: FeatureName): boolean {
  return isVersionAtLeast(FEATURE_VERSIONS[feature]);
}

// --- Utility: wrap Telegram callback-based API in Promise ---
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

// --- Utility: safe call with fallback ---
export function safeCall<T>(fn: () => T, fallback: T): T {
  try { return fn(); } catch { return fallback; }
}
```

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/core.ts
git commit -m "feat(telegram-sdk): add core SDK with feature detection and utilities"
```

---

### Task 3: Create TelegramProvider

**Files:**
- Create: `lib/telegram/TelegramProvider.tsx`

Minimal React Context. Only holds reactive state that triggers re-renders: theme, viewport, user, active state.

- [ ] **Step 1: Create `lib/telegram/TelegramProvider.tsx`**

Implement the Provider with:

1. `TelegramContextValue` interface matching spec exactly (webApp, user, initData, initDataUnsafe, colorScheme, themeParams, viewportHeight, viewportStableHeight, isExpanded, isActive, safeAreaInset, contentSafeAreaInset, platform, version, isReady)

2. `createContext` with `null` default, `useTelegramContext()` hook that throws if used outside Provider

3. `TelegramProvider` component:
   - On mount: get WebApp from core, call `ready()`, call `expand()` on mobile only (`platform === 'ios' || platform === 'android'`)
   - Subscribe to `themeChanged` → update `colorScheme` + `themeParams` state
   - Subscribe to `viewportChanged` → update `viewportHeight`, `viewportStableHeight`, `isExpanded`
   - Subscribe to `safeAreaChanged` → update `safeAreaInset`
   - Subscribe to `contentSafeAreaChanged` → update `contentSafeAreaInset`
   - Subscribe to `activated` / `deactivated` → update `isActive`
   - Set CSS custom properties: all 15 `--tg-theme-*` variables from themeParams
   - Set viewport CSS vars: `--tg-viewport-height`, `--tg-viewport-stable-height`, `--tg-safe-area-*`, `--tg-content-safe-area-*`
   - Cleanup all subscriptions on unmount

4. Fallback defaults (outside Telegram):
   - `webApp: null`, `user: null`, `isReady: false`, `isActive: false`
   - `colorScheme: 'light'`, `themeParams: {} as ThemeParams`
   - `viewportHeight/viewportStableHeight: typeof window !== 'undefined' ? window.innerHeight : 0`
   - `platform: 'unknown'`, `version: '0.0'`
   - Listen to `window.resize` for viewport fallback

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/TelegramProvider.tsx
git commit -m "feat(telegram-sdk): add TelegramProvider with reactive state management"
```

---

## Phase 2: Hooks (28 hooks in batches)

### Task 4: Context Consumer Hooks

**Files:**
- Create: `lib/telegram/hooks/useTelegram.ts`
- Create: `lib/telegram/hooks/useTheme.ts`
- Create: `lib/telegram/hooks/useViewport.ts`

- [ ] **Step 1: Create all 3 hooks**

**`useTelegram.ts`** — thin wrapper around `useTelegramContext()`:
```ts
// Returns: { webApp, user, initData, initDataUnsafe, platform, version, isReady, isActive, isAvailable: boolean }
// isAvailable = webApp !== null
```

**`useTheme.ts`** — reads theme from context:
```ts
// Returns: { themeParams, colorScheme, isDark: boolean, isAvailable }
// isDark = colorScheme === 'dark'
```

**`useViewport.ts`** — reads viewport from context + provides expand():
```ts
// Returns: { viewportHeight, viewportStableHeight, isExpanded, safeAreaInset,
//            contentSafeAreaInset, expand: () => void, isAvailable }
```

Every hook returns `isAvailable: boolean`.

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/hooks/
git commit -m "feat(telegram-sdk): add context consumer hooks (useTelegram, useTheme, useViewport)"
```

---

### Task 5: Button Controller Hooks

**Files:**
- Create: `lib/telegram/hooks/useMainButton.ts`
- Create: `lib/telegram/hooks/useSecondaryButton.ts`
- Create: `lib/telegram/hooks/useBackButton.ts`
- Create: `lib/telegram/hooks/useSettingsButton.ts`

- [ ] **Step 1: Create all 4 hooks**

**`useMainButton.ts`** — accepts config object, registers onClick, manages lifecycle:
```ts
interface MainButtonConfig {
  text?: string;
  color?: string;
  textColor?: string;
  isVisible?: boolean;
  isActive?: boolean;
  hasShineEffect?: boolean;
  iconCustomEmojiId?: string;
  onClick?: () => void;
}
// Returns: { show, hide, setText, enable, disable, showProgress, hideProgress, setParams, isAvailable, isProgressVisible }
```
- On mount: apply config via `setParams()` if available (7.10+), otherwise set individual properties
- Register `onClick` callback, cleanup with `offClick` on unmount
- React 19 Strict Mode safe: use ref for callback, cleanup in effect

**`useSecondaryButton.ts`** — same as MainButton + `position` config prop

**`useBackButton.ts`** — simple show/hide with callback:
```ts
// useBackButton(onBack?: () => void)
// Returns: { show, hide, isVisible, isAvailable }
```
- On mount: if `onBack` provided, `show()` + `onClick(onBack)`
- On unmount: `hide()` + `offClick(onBack)`

**`useSettingsButton.ts`** — same pattern as BackButton

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/hooks/useMainButton.ts lib/telegram/hooks/useSecondaryButton.ts lib/telegram/hooks/useBackButton.ts lib/telegram/hooks/useSettingsButton.ts
git commit -m "feat(telegram-sdk): add button controller hooks (main, secondary, back, settings)"
```

---

### Task 6: Imperative Wrapper Hooks

**Files:**
- Create: `lib/telegram/hooks/useHaptic.ts`
- Create: `lib/telegram/hooks/useClipboard.ts`
- Create: `lib/telegram/hooks/useLinks.ts`
- Create: `lib/telegram/hooks/usePopup.ts`
- Create: `lib/telegram/hooks/useQrScanner.ts`
- Create: `lib/telegram/hooks/useInvoice.ts`
- Create: `lib/telegram/hooks/usePermissions.ts`

- [ ] **Step 1: Create all 7 hooks**

Each hook:
1. Calls `getWebApp()` from core
2. Checks `supportsFeature()` for version requirement
3. Returns `{ isAvailable, ...methods }`
4. When `!isAvailable`, methods are safe no-ops

**`useHaptic.ts`**:
```ts
// Returns: { impactOccurred, notificationOccurred, selectionChanged, isAvailable }
// impactOccurred: (style: HapticImpactStyle) => void
```

**`useClipboard.ts`**:
```ts
// Returns: { readText: () => Promise<string | null>, isAvailable }
// Uses callbackToPromise from core
```

**`useLinks.ts`**:
```ts
// Returns: { openLink, openTelegramLink, switchInlineQuery, isAvailable }
// openLink: (url: string, options?: { try_instant_view?: boolean }) => void
```

**`usePopup.ts`**:
```ts
// Returns: { showPopup, showAlert, showConfirm, isAvailable }
// showPopup: (params: PopupParams) => Promise<string | null>
// showAlert: (message: string) => Promise<void>
// showConfirm: (message: string) => Promise<boolean>
```

**`useQrScanner.ts`**:
```ts
// Returns: { show, close, isAvailable }
// show: (params?: ScanQrPopupParams) => Promise<string>
```

**`useInvoice.ts`**:
```ts
// Returns: { openInvoice: (url: string) => Promise<InvoiceStatus>, isAvailable }
```

**`usePermissions.ts`**:
```ts
// Returns: { requestWriteAccess, requestContact, isAvailable }
// requestWriteAccess: () => Promise<WriteAccessStatus>
// requestContact: () => Promise<ContactRequestStatus>
```

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/hooks/
git commit -m "feat(telegram-sdk): add imperative hooks (haptic, clipboard, links, popup, qr, invoice, permissions)"
```

---

### Task 7: Storage Hooks

**Files:**
- Create: `lib/telegram/hooks/useCloudStorage.ts`
- Create: `lib/telegram/hooks/useDeviceStorage.ts`
- Create: `lib/telegram/hooks/useSecureStorage.ts`

- [ ] **Step 1: Create all 3 hooks**

Each wraps callback-based Storage API in Promises using `callbackToPromise` from core.

**`useCloudStorage.ts`** (6.9+):
```ts
// Returns: { setItem, getItem, getItems, removeItem, removeItems, getKeys, isAvailable }
// setItem: (key: string, value: string) => Promise<boolean>
// getItem: (key: string) => Promise<string>
// getItems: (keys: string[]) => Promise<Record<string, string>>
// removeItem: (key: string) => Promise<boolean>
// removeItems: (keys: string[]) => Promise<boolean>
// getKeys: () => Promise<string[]>
```

**`useDeviceStorage.ts`** (9.0+):
```ts
// Returns: { setItem, getItem, removeItem, clear, isAvailable }
```

**`useSecureStorage.ts`** (9.0+):
```ts
// Returns: { setItem, getItem, restoreItem, removeItem, clear, isAvailable }
// getItem returns: Promise<{ value: string; canRestore: boolean }>
```

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/hooks/
git commit -m "feat(telegram-sdk): add storage hooks (cloud, device, secure)"
```

---

### Task 8: Sensor Hooks

**Files:**
- Create: `lib/telegram/hooks/useAccelerometer.ts`
- Create: `lib/telegram/hooks/useGyroscope.ts`
- Create: `lib/telegram/hooks/useDeviceOrientation.ts`

- [ ] **Step 1: Create all 3 hooks**

Each sensor hook:
1. Manages `isStarted` state via `useState`
2. Reads sensor values via `useState` updated on `*Changed` events
3. Uses `useRef` to track actual started state (React 19 Strict Mode)
4. Cleanup: `stop()` in effect cleanup, `offEvent` for change listener

**`useAccelerometer.ts`** (8.0+):
```ts
// useAccelerometer(refreshRate?: number)
// Returns: { x, y, z, isStarted, start, stop, isAvailable }
// Subscribes to accelerometerChanged event to update x/y/z state
// refreshRate: 20-1000ms, defaults to 1000
```

**`useGyroscope.ts`** (8.0+):
```ts
// Same shape as accelerometer, rad/s units
```

**`useDeviceOrientation.ts`** (8.0+):
```ts
// useDeviceOrientation(refreshRate?: number, needAbsolute?: boolean)
// Returns: { alpha, beta, gamma, absolute, isStarted, start, stop, isAvailable }
```

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/hooks/
git commit -m "feat(telegram-sdk): add sensor hooks (accelerometer, gyroscope, device orientation)"
```

---

### Task 9: Feature Hooks

**Files:**
- Create: `lib/telegram/hooks/useLocation.ts`
- Create: `lib/telegram/hooks/useBiometric.ts`
- Create: `lib/telegram/hooks/useFullscreen.ts`

- [ ] **Step 1: Create all 3 hooks**

**`useLocation.ts`** (8.0+):
```ts
// Returns: { init, getLocation, openSettings, isInited, isAvailable, isGranted, isAvailable }
// init: () => Promise<void>
// getLocation: () => Promise<LocationData | null>
// Subscribes to locationManagerUpdated to update state
```

**`useBiometric.ts`** (7.2+):
```ts
// Returns: { init, requestAccess, authenticate, updateToken, openSettings,
//            isInited, isAvailable, biometricType, deviceId, isAccessGranted, isTokenSaved, isAvailable }
// authenticate: (reason?: string) => Promise<{ success: boolean; token?: string }>
// Subscribes to biometricManagerUpdated
```

**`useFullscreen.ts`** (8.0+):
```ts
// Returns: { request, exit, isFullscreen, lockOrientation, unlockOrientation, isOrientationLocked, isAvailable }
// Subscribes to fullscreenChanged, fullscreenFailed
```

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/hooks/
git commit -m "feat(telegram-sdk): add feature hooks (location, biometric, fullscreen)"
```

---

### Task 10: Toggle + Action Hooks

**Files:**
- Create: `lib/telegram/hooks/useClosingConfirmation.ts`
- Create: `lib/telegram/hooks/useVerticalSwipes.ts`
- Create: `lib/telegram/hooks/useHomeScreen.ts`
- Create: `lib/telegram/hooks/useEmojiStatus.ts`
- Create: `lib/telegram/hooks/useShare.ts`
- Create: `lib/telegram/hooks/usePlatform.ts`

- [ ] **Step 1: Create all 6 hooks**

**`useClosingConfirmation.ts`** (6.2+):
```ts
// useClosingConfirmation(enabled: boolean)
// On enabled change: call enableClosingConfirmation() / disableClosingConfirmation()
// Cleanup: disableClosingConfirmation() on unmount if was enabled
```

**`useVerticalSwipes.ts`** (7.7+):
```ts
// useVerticalSwipes(enabled: boolean)
// Same pattern as closingConfirmation
```

**`useHomeScreen.ts`** (8.0+):
```ts
// Returns: { addToHomeScreen, checkStatus, isAvailable }
// checkStatus: () => Promise<HomeScreenStatus>
// Subscribes to homeScreenChecked, homeScreenAdded events
```

**`useEmojiStatus.ts`** (8.0+):
```ts
// Returns: { setEmojiStatus, requestAccess, isAvailable }
// setEmojiStatus: (emojiId: string, params?: EmojiStatusParams) => Promise<boolean>
// requestAccess: () => Promise<boolean>
// Subscribes to emojiStatusSet, emojiStatusFailed, emojiStatusAccessRequested
```

**`useShare.ts`** (7.8+ / 8.0+):
```ts
// Returns: { shareToStory, shareMessage, downloadFile, isAvailable }
// shareMessage: (msgId: number) => Promise<boolean>
// Subscribes to shareMessageSent, shareMessageFailed
```

**`usePlatform.ts`**:
```ts
// Returns: { platform, version, isVersionAtLeast, performanceClass, isAvailable }
// performanceClass: derived from User-Agent parsing for Android devices
// Returns 'HIGH' | 'AVERAGE' | 'LOW' or null for non-Android
```

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/hooks/
git commit -m "feat(telegram-sdk): add toggle and action hooks (closing, swipes, home, emoji, share, platform)"
```

---

## Phase 3: Integration

### Task 11: Create Barrel Export

**Files:**
- Create: `lib/telegram/index.ts`

- [ ] **Step 1: Create barrel**

Export everything listed in spec section 7:
- All types (as `export type`)
- Core functions + error classes
- Provider + `useTelegramContext`
- All 28 hooks

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/telegram/index.ts
git commit -m "feat(telegram-sdk): add barrel export"
```

---

### Task 12: Update Window Globals + Move DebugUser Type

**Files:**
- Modify: `lib/types/telegram-globals.d.ts` — update imports to use `lib/telegram/types`
- Modify: `lib/auth/browserDebugAuth.ts` — move `DebugUser` type here (it already has a local type)
- Delete: `lib/types/telegram.ts` — replaced by `lib/telegram/types.ts`

- [ ] **Step 1: Update `lib/types/telegram-globals.d.ts`**

Change imports from `./telegram` to `@/lib/telegram/types`. The `DebugUser` type should import from `@/lib/auth/browserDebugAuth`.

Read `lib/auth/browserDebugAuth.ts` — check if it already exports a `DebugUser`-like type. If yes, use that. If not, add the `DebugUser` interface there and export it.

**Note:** Do NOT delete `lib/types/telegram.ts` here — `TelegramInit.tsx` still imports from it and is deleted in Task 13. The deletion happens there.

- [ ] **Step 2: Verify build, commit**

```bash
git add lib/types/telegram-globals.d.ts lib/auth/browserDebugAuth.ts
git commit -m "refactor(telegram-sdk): update globals, map DebugUser to BrowserDebugUser"
```

**Note on DebugUser:** The existing `lib/auth/browserDebugAuth.ts` already defines `BrowserDebugUser` (with required fields + `[key: string]: unknown`). Use `BrowserDebugUser` for the `window.__LM_BROWSER_DEBUG_USER__` global type. Do not create a separate `DebugUser` — map directly to `BrowserDebugUser | null`.

---

### Task 13: Update Layout + Replace Old Components

**Files:**
- Modify: `app/layout.tsx` — replace old TG components with `TelegramProvider`
- Delete: `components/blocks/telegram/TelegramInit.tsx` — replaced by Provider
- Delete: `components/blocks/telegram/TelegramNavButtons.tsx` — replaced by hooks
- Delete: `app/TelegramViewportManager.tsx` — replaced by Provider viewport management
- Modify: `components/blocks/telegram/WebViewErrorAlert.tsx` — use `useTelegram()` instead of `window.__LM_BROWSER_DEBUG_AUTH__`

- [ ] **Step 1: Update `app/layout.tsx`**

Current:
```tsx
<StoreProvider>
  <TelegramInit />
  <TelegramAuthBootstrap />
  <TelegramNavButtons />
  <TelegramViewportManager />
  <InputFocusFix />
  {children}
  <WebViewErrorAlert />
</StoreProvider>
```

New:
```tsx
<StoreProvider>
  <TelegramProvider>
    <TelegramAuthBootstrap />
    <InputFocusFix />
    {children}
    <WebViewErrorAlert />
  </TelegramProvider>
</StoreProvider>
```

- Remove imports: `TelegramInit`, `TelegramNavButtons`, `TelegramViewportManager`
- Add import: `TelegramProvider` from `@/lib/telegram`
- Keep: `Script` tag for `telegram-web-app.js`, `StoreProvider`, `TelegramAuthBootstrap`, `InputFocusFix`, `WebViewErrorAlert`

- [ ] **Step 2: Update `WebViewErrorAlert.tsx`**

Change from:
```ts
!window.Telegram?.WebApp && !window.__LM_BROWSER_DEBUG_AUTH__
```
To using the `useTelegram()` hook:
```ts
const { isReady } = useTelegram();
// Show alert only if not ready after timeout
```

- [ ] **Step 3: Migrate TelegramInit behavior into Provider**

The current `TelegramInit.tsx` does more than `ready()` + `expand()`. The Provider must also:

1. **Set window globals** — `window.__LM_TG_INIT_DATA__`, `window.__LM_TG_INIT_DATA_UNSAFE__`, `window.__LM_BROWSER_DEBUG_AUTH__`, `window.__LM_BROWSER_DEBUG_USER__`. These are read by `TelegramAuthBootstrap.tsx`.
2. **Dispatch `lm:telegram:initdata` custom event** — `TelegramAuthBootstrap` listens for it.
3. **Call `requestFullscreen()` on mobile** — current TelegramInit does this.
4. **Call `disableVerticalSwipes()` on mobile** — current TelegramInit does this.
5. **Apply theme colors via `setBackgroundColor` / `setHeaderColor`** from `--app-background` CSS variable.

Read `TelegramAuthBootstrap.tsx` fully. If it reads `window.__LM_TG_INIT_DATA__` or listens to `lm:telegram:initdata`, the Provider MUST replicate this. If not, skip.

Add this logic to the Provider's mount effect, after `ready()` and `expand()`:
```ts
// Publish init data for auth bootstrap
window.__LM_TG_INIT_DATA__ = wa.initData;
window.__LM_TG_INIT_DATA_UNSAFE__ = wa.initDataUnsafe;
window.dispatchEvent(new CustomEvent('lm:telegram:initdata', { detail: { initData: wa.initData } }));

// Mobile-only behaviors
if (isMobile) {
  safeCall(() => wa.requestFullscreen?.(), undefined);
  safeCall(() => wa.disableVerticalSwipes?.(), undefined);
}
```

- [ ] **Step 4: Delete replaced files + old types**

```bash
git rm components/blocks/telegram/TelegramInit.tsx
git rm components/blocks/telegram/TelegramNavButtons.tsx
git rm app/TelegramViewportManager.tsx
git rm lib/types/telegram.ts
```

- [ ] **Step 5: Verify build**

Run: `npx next build 2>&1 | grep -E "(Compiled|Failed)"`
Expected: `✓ Compiled successfully`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(telegram-sdk): integrate provider into layout, remove old TG components"
```

---

### Task 14: Update Remaining Direct WebApp References

**Files:**
- Modify: `app/invite-friends/InviteLinkActions.tsx`
- Modify: `app/invite-friends/PromoCouponCard.tsx`

- [ ] **Step 1: Update `InviteLinkActions.tsx`**

Read the file. Find `window.Telegram.WebApp` references. Replace with `useTelegram()` hook. This file likely uses `openTelegramLink` or `shareToStory` — replace with `useLinks()` or `useShare()`.

- [ ] **Step 2: Update `PromoCouponCard.tsx`**

Same — read, find direct WebApp access, replace with appropriate hook.

- [ ] **Step 3: Verify build, commit**

```bash
git add app/invite-friends/
git commit -m "refactor(telegram-sdk): replace direct WebApp access with hooks in invite-friends"
```

---

### Task 15: Final Cleanup + Verification

**Files:**
- Verify: no remaining `window.Telegram` references outside `lib/telegram/`
- Verify: no remaining imports from `@/lib/types/telegram`

- [ ] **Step 1: Audit for stale references**

```bash
# No direct window.Telegram outside lib/telegram/
grep -r "window\.Telegram" app/ components/ --include="*.ts" --include="*.tsx" | grep -v node_modules

# No imports from old telegram types
grep -r "@/lib/types/telegram" app/ components/ lib/ --include="*.ts" --include="*.tsx"

# No remaining TelegramInit/TelegramNavButtons/TelegramViewportManager imports
grep -r "TelegramInit\|TelegramNavButtons\|TelegramViewportManager" app/ components/ --include="*.ts" --include="*.tsx"
```

Expected: 0 matches for all.

- [ ] **Step 2: Full build verification**

```bash
npx next build 2>&1 | grep -E "(Compiled|Failed|Type error)"
```
Expected: `✓ Compiled successfully`, no type errors.

- [ ] **Step 3: Verify all exports work**

Create a temporary test: import everything from `@/lib/telegram` in a scratch file to verify barrel exports resolve.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore(telegram-sdk): final cleanup and verification"
```

---

## Verification Checklist

After all tasks complete, verify:

- [ ] `npx next build` passes with 0 errors
- [ ] `npx tsc --noEmit` passes with 0 errors
- [ ] All 28 hooks export from `@/lib/telegram`
- [ ] `TelegramProvider` renders in `layout.tsx`
- [ ] No `window.Telegram` access outside `lib/telegram/`
- [ ] No imports from `@/lib/types/telegram` (old path)
- [ ] No remaining `TelegramInit`, `TelegramNavButtons`, `TelegramViewportManager` references
- [ ] CSS variables set for all 15 theme colors + viewport + safe areas
- [ ] `types.ts` includes all 41 event types in `EventType` union
- [ ] Outside Telegram: all hooks return `{ isAvailable: false, ...noopMethods }`
