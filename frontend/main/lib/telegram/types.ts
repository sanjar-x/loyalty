// =============================================================================
// Telegram WebApp Type Definitions — Bot API 9.x
// Source of truth: https://core.telegram.org/bots/webapps
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Type Aliases
// -----------------------------------------------------------------------------

export type HapticImpactStyle = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft';

export type HapticNotificationType = 'error' | 'success' | 'warning';

export type InvoiceStatus = 'paid' | 'cancelled' | 'failed' | 'pending';

export type HomeScreenStatus = 'unsupported' | 'unknown' | 'added' | 'missed';

export type BiometricType = 'finger' | 'face' | 'unknown';

export type BottomButtonPosition = 'left' | 'right' | 'top' | 'bottom';

export type ChatType = 'sender' | 'private' | 'group' | 'supergroup' | 'channel';

export type WriteAccessStatus = 'allowed' | 'cancelled';

export type ContactRequestStatus = 'sent' | 'cancelled';

export type FullscreenError = 'UNSUPPORTED' | 'ALREADY_FULLSCREEN';

export type SensorError = 'UNSUPPORTED';

// -----------------------------------------------------------------------------
// 2. EventType — 43-member union
// -----------------------------------------------------------------------------

export type EventType =
  // Lifecycle
  | 'activated'
  | 'deactivated'
  // UI
  | 'themeChanged'
  | 'viewportChanged'
  | 'safeAreaChanged'
  | 'contentSafeAreaChanged'
  | 'mainButtonClicked'
  | 'secondaryButtonClicked'
  | 'backButtonClicked'
  | 'settingsButtonClicked'
  // Popups & Dialogs
  | 'invoiceClosed'
  | 'popupClosed'
  | 'qrTextReceived'
  | 'scanQrPopupClosed'
  | 'clipboardTextReceived'
  // Permissions
  | 'writeAccessRequested'
  | 'contactRequested'
  // Biometric
  | 'biometricManagerUpdated'
  | 'biometricAuthRequested'
  | 'biometricTokenUpdated'
  // Fullscreen
  | 'fullscreenChanged'
  | 'fullscreenFailed'
  // Home Screen
  | 'homeScreenAdded'
  | 'homeScreenChecked'
  // Sensors — Accelerometer
  | 'accelerometerStarted'
  | 'accelerometerStopped'
  | 'accelerometerChanged'
  | 'accelerometerFailed'
  // Sensors — Device Orientation
  | 'deviceOrientationStarted'
  | 'deviceOrientationStopped'
  | 'deviceOrientationChanged'
  | 'deviceOrientationFailed'
  // Sensors — Gyroscope
  | 'gyroscopeStarted'
  | 'gyroscopeStopped'
  | 'gyroscopeChanged'
  | 'gyroscopeFailed'
  // Location
  | 'locationManagerUpdated'
  | 'locationRequested'
  // Share
  | 'shareMessageSent'
  | 'shareMessageFailed'
  // Emoji Status
  | 'emojiStatusSet'
  | 'emojiStatusFailed'
  | 'emojiStatusAccessRequested';

// -----------------------------------------------------------------------------
// 3. Data Types
// -----------------------------------------------------------------------------

/** Safe area inset values in pixels. @since Bot API 8.0 */
export interface SafeAreaInset {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

/** Content safe area inset values in pixels. @since Bot API 8.0 */
export interface ContentSafeAreaInset {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

/** Location data returned by LocationManager.getLocation(). @since Bot API 8.0 */
export interface LocationData {
  latitude: number;
  longitude: number;
  altitude: number | null;
  course: number | null;
  speed: number | null;
  horizontal_accuracy: number | null;
  vertical_accuracy: number | null;
  course_accuracy: number | null;
  speed_accuracy: number | null;
}

/** Theme parameters provided by the Telegram client. */
export interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
  header_bg_color?: string;
  bottom_bar_bg_color?: string;
  accent_text_color?: string;
  section_bg_color?: string;
  section_header_text_color?: string;
  section_separator_color?: string;
  subtitle_text_color?: string;
  destructive_text_color?: string;
}

/** A button displayed in a popup. @since Bot API 6.2 */
export interface PopupButton {
  id?: string;
  type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
  text?: string;
}

/** Parameters for showPopup(). @since Bot API 6.2 */
export interface PopupParams {
  title?: string;
  message: string;
  buttons?: PopupButton[];
}

/** Parameters for showScanQrPopup(). @since Bot API 6.4 */
export interface ScanQrPopupParams {
  text?: string;
}

/** Widget link displayed in a shared story. @since Bot API 7.8 */
export interface StoryWidgetLink {
  url: string;
  name?: string;
}

/** Parameters for shareToStory(). @since Bot API 7.8 */
export interface StoryShareParams {
  text?: string;
  widget_link?: StoryWidgetLink;
}

/** Parameters for downloadFile(). @since Bot API 8.0 */
export interface DownloadFileParams {
  url: string;
  file_name: string;
}

/** Parameters for setEmojiStatus(). @since Bot API 8.0 */
export interface EmojiStatusParams {
  duration?: number;
}

/** Parameters for BiometricManager.requestAccess(). @since Bot API 7.2 */
export interface BiometricRequestAccessParams {
  reason?: string;
}

/** Parameters for BiometricManager.authenticate(). @since Bot API 7.2 */
export interface BiometricAuthenticateParams {
  reason?: string;
}

// -----------------------------------------------------------------------------
// 4. Sub-object Interfaces
// -----------------------------------------------------------------------------

/** Back button displayed in the header. @since Bot API 6.1 */
export interface BackButton {
  /** Whether the button is visible. */
  isVisible: boolean;

  /** Show the back button. */
  show(): BackButton;

  /** Hide the back button. */
  hide(): BackButton;

  /** Register a click handler. */
  onClick(callback: () => void): BackButton;

  /** Remove a click handler. */
  offClick(callback: () => void): BackButton;
}

/** Settings button displayed in the header. @since Bot API 7.0 */
export interface SettingsButton {
  /** Whether the button is visible. */
  isVisible: boolean;

  /** Show the settings button. */
  show(): SettingsButton;

  /** Hide the settings button. */
  hide(): SettingsButton;

  /** Register a click handler. */
  onClick(callback: () => void): SettingsButton;

  /** Remove a click handler. */
  offClick(callback: () => void): SettingsButton;
}

/** Parameters for BottomButton.setParams(). @since Bot API 7.10 */
export interface BottomButtonParams {
  text?: string;
  color?: string;
  text_color?: string;
  is_visible?: boolean;
  is_active?: boolean;
  has_shine_effect?: boolean;
  position?: BottomButtonPosition;
  icon_custom_emoji_id?: string;
}

/**
 * A button displayed at the bottom of the WebApp.
 * Used for both MainButton and SecondaryButton.
 * @since Bot API 6.0 (MainButton), 7.10 (SecondaryButton)
 */
export interface BottomButton {
  /** The type of the button: 'main' or 'secondary'. */
  readonly type: 'main' | 'secondary';

  /** Current button text. */
  text: string;

  /** Current button color. */
  color: string;

  /** Current button text color. */
  textColor: string;

  /** Whether the button is visible. */
  isVisible: boolean;

  /** Whether the button is active (clickable). */
  isActive: boolean;

  /** Whether the button has a shine effect. @since Bot API 7.10 */
  hasShineEffect: boolean;

  /** Position of the button (SecondaryButton only). @since Bot API 7.10 */
  position: BottomButtonPosition;

  /** Whether the loading indicator is currently visible. */
  readonly isProgressVisible: boolean;

  /** Custom emoji ID used as the button icon. @since Bot API 9.5 */
  iconCustomEmojiId: string;

  /** Set the button text. */
  setText(text: string): BottomButton;

  /** Register a click handler. */
  onClick(callback: () => void): BottomButton;

  /** Remove a click handler. */
  offClick(callback: () => void): BottomButton;

  /** Show the button. */
  show(): BottomButton;

  /** Hide the button. */
  hide(): BottomButton;

  /** Enable the button. */
  enable(): BottomButton;

  /** Disable the button. */
  disable(): BottomButton;

  /** Show a loading indicator on the button. */
  showProgress(leaveActive?: boolean): BottomButton;

  /** Hide the loading indicator. */
  hideProgress(): BottomButton;

  /** Set multiple button parameters at once. @since Bot API 7.10 */
  setParams(params: BottomButtonParams): BottomButton;
}

/** Haptic feedback interface. @since Bot API 6.1 */
export interface HapticFeedback {
  /** Trigger an impact haptic event. */
  impactOccurred(style: HapticImpactStyle): HapticFeedback;

  /** Trigger a notification haptic event. */
  notificationOccurred(type: HapticNotificationType): HapticFeedback;

  /** Trigger a selection change haptic event. */
  selectionChanged(): HapticFeedback;
}

/**
 * Cloud-based key-value storage.
 * Keys: 1-128 chars, Values: 0-4096 chars, Max 1024 items per bot per user.
 * @since Bot API 6.9
 */
export interface CloudStorage {
  /**
   * Store a value in cloud storage.
   * @param key - Key string, 1-128 characters.
   * @param value - Value string, 0-4096 characters.
   * @param callback - Optional callback with error and success flag.
   */
  setItem(
    key: string,
    value: string,
    callback?: (error: string | null, success: boolean) => void,
  ): CloudStorage;

  /**
   * Get a single value from cloud storage.
   * @param key - Key string, 1-128 characters.
   * @param callback - Callback with error and the stored value.
   */
  getItem(
    key: string,
    callback: (error: string | null, value: string) => void,
  ): CloudStorage;

  /**
   * Get multiple values from cloud storage.
   * @param keys - Array of key strings.
   * @param callback - Callback with error and a key-value record.
   */
  getItems(
    keys: string[],
    callback: (error: string | null, values: Record<string, string>) => void,
  ): CloudStorage;

  /**
   * Remove a value from cloud storage.
   * @param key - Key string.
   * @param callback - Optional callback with error and success flag.
   */
  removeItem(
    key: string,
    callback?: (error: string | null, success: boolean) => void,
  ): CloudStorage;

  /**
   * Remove multiple values from cloud storage.
   * @param keys - Array of key strings.
   * @param callback - Optional callback with error and success flag.
   */
  removeItems(
    keys: string[],
    callback?: (error: string | null, success: boolean) => void,
  ): CloudStorage;

  /**
   * Get all keys stored in cloud storage.
   * @param callback - Callback with error and array of keys.
   */
  getKeys(
    callback: (error: string | null, keys: string[]) => void,
  ): CloudStorage;
}

/**
 * Device-local key-value storage.
 * 5MB per bot per user.
 * @since Bot API 9.0
 */
export interface DeviceStorage {
  /**
   * Store a value in device storage.
   * @param key - Key string.
   * @param value - Value string.
   * @param callback - Optional callback with error and success flag.
   */
  setItem(
    key: string,
    value: string,
    callback?: (error: string | null, success: boolean) => void,
  ): DeviceStorage;

  /**
   * Get a value from device storage.
   * @param key - Key string.
   * @param callback - Callback with error and the stored value.
   */
  getItem(
    key: string,
    callback: (error: string | null, value: string) => void,
  ): DeviceStorage;

  /**
   * Remove a value from device storage.
   * @param key - Key string.
   * @param callback - Optional callback with error and success flag.
   */
  removeItem(
    key: string,
    callback?: (error: string | null, success: boolean) => void,
  ): DeviceStorage;

  /**
   * Clear all values from device storage.
   * @param callback - Optional callback with error and success flag.
   */
  clear(
    callback?: (error: string | null, success: boolean) => void,
  ): DeviceStorage;
}

/**
 * Encrypted secure storage.
 * Max 10 items.
 * @since Bot API 9.0
 */
export interface SecureStorage {
  /**
   * Store a value in secure storage.
   * @param key - Key string.
   * @param value - Value string.
   * @param callback - Optional callback with error and success flag.
   */
  setItem(
    key: string,
    value: string,
    callback?: (error: string | null, success: boolean) => void,
  ): SecureStorage;

  /**
   * Get a value from secure storage.
   * @param key - Key string.
   * @param callback - Callback with error, stored value, and whether the item can be restored.
   */
  getItem(
    key: string,
    callback: (error: string | null, value: string, canRestore: boolean) => void,
  ): SecureStorage;

  /**
   * Restore a value in secure storage.
   * @param key - Key string.
   * @param callback - Optional callback with error and success flag.
   */
  restoreItem(
    key: string,
    callback?: (error: string | null, success: boolean) => void,
  ): SecureStorage;

  /**
   * Remove a value from secure storage.
   * @param key - Key string.
   * @param callback - Optional callback with error and success flag.
   */
  removeItem(
    key: string,
    callback?: (error: string | null, success: boolean) => void,
  ): SecureStorage;

  /**
   * Clear all values from secure storage.
   * @param callback - Optional callback with error and success flag.
   */
  clear(
    callback?: (error: string | null, success: boolean) => void,
  ): SecureStorage;
}

/**
 * Biometric authentication manager.
 * @since Bot API 7.2
 */
export interface BiometricManager {
  /** Whether the biometric manager has been initialized. */
  isInited: boolean;

  /** Whether biometric authentication is available on the device. */
  isBiometricAvailable: boolean;

  /** The type of biometric authentication available. */
  biometricType: BiometricType;

  /** Whether access to biometrics has been requested. */
  isAccessRequested: boolean;

  /** Whether access to biometrics has been granted. */
  isAccessGranted: boolean;

  /** Whether a biometric token has been saved. */
  isBiometricTokenSaved: boolean;

  /** Unique device identifier. */
  deviceId: string;

  /**
   * Initialize the biometric manager.
   * @param callback - Optional callback invoked when initialization is complete.
   */
  init(callback?: () => void): BiometricManager;

  /**
   * Request permission to use biometrics.
   * @param params - Parameters including an optional reason string.
   * @param callback - Optional callback with the granted status.
   */
  requestAccess(
    params: BiometricRequestAccessParams,
    callback?: (granted: boolean) => void,
  ): BiometricManager;

  /**
   * Authenticate using biometrics.
   * @param params - Parameters including an optional reason string.
   * @param callback - Optional callback with success status and token.
   */
  authenticate(
    params: BiometricAuthenticateParams,
    callback?: (success: boolean, token?: string) => void,
  ): BiometricManager;

  /**
   * Update the biometric token stored on the device.
   * @param token - The new token string.
   * @param callback - Optional callback with success status.
   */
  updateBiometricToken(
    token: string,
    callback?: (success: boolean) => void,
  ): BiometricManager;

  /** Open the device biometric settings. */
  openSettings(): BiometricManager;
}

/**
 * Accelerometer sensor.
 * @since Bot API 8.0
 */
export interface Accelerometer {
  /** Whether the accelerometer is currently active. */
  isStarted: boolean;

  /** Acceleration along the x-axis in m/s². */
  x: number;

  /** Acceleration along the y-axis in m/s². */
  y: number;

  /** Acceleration along the z-axis in m/s². */
  z: number;

  /**
   * Start listening to accelerometer data.
   * @param params - Configuration with optional refresh_rate in ms.
   * @param callback - Optional callback invoked when started.
   */
  start(
    params: { refresh_rate?: number },
    callback?: (started: boolean) => void,
  ): Accelerometer;

  /**
   * Stop listening to accelerometer data.
   * @param callback - Optional callback invoked when stopped.
   */
  stop(callback?: (stopped: boolean) => void): Accelerometer;
}

/**
 * Gyroscope sensor.
 * @since Bot API 8.0
 */
export interface Gyroscope {
  /** Whether the gyroscope is currently active. */
  isStarted: boolean;

  /** Angular velocity around the x-axis in rad/s. */
  x: number;

  /** Angular velocity around the y-axis in rad/s. */
  y: number;

  /** Angular velocity around the z-axis in rad/s. */
  z: number;

  /**
   * Start listening to gyroscope data.
   * @param params - Configuration with optional refresh_rate in ms.
   * @param callback - Optional callback invoked when started.
   */
  start(
    params: { refresh_rate?: number },
    callback?: (started: boolean) => void,
  ): Gyroscope;

  /**
   * Stop listening to gyroscope data.
   * @param callback - Optional callback invoked when stopped.
   */
  stop(callback?: (stopped: boolean) => void): Gyroscope;
}

/**
 * Device orientation sensor.
 * @since Bot API 8.0
 */
export interface DeviceOrientation {
  /** Whether the sensor is currently active. */
  isStarted: boolean;

  /** Whether the orientation data is absolute (relative to Earth). */
  absolute: boolean;

  /** Rotation around the z-axis (0-360). */
  alpha: number;

  /** Rotation around the x-axis (-180 to 180). */
  beta: number;

  /** Rotation around the y-axis (-90 to 90). */
  gamma: number;

  /**
   * Start listening to device orientation data.
   * @param params - Configuration with optional refresh_rate and need_absolute flag.
   * @param callback - Optional callback invoked when started.
   */
  start(
    params: { refresh_rate?: number; need_absolute?: boolean },
    callback?: (started: boolean) => void,
  ): DeviceOrientation;

  /**
   * Stop listening to device orientation data.
   * @param callback - Optional callback invoked when stopped.
   */
  stop(callback?: (stopped: boolean) => void): DeviceOrientation;
}

/**
 * Location manager for accessing device location.
 * @since Bot API 8.0
 */
export interface LocationManager {
  /** Whether the location manager has been initialized. */
  isInited: boolean;

  /** Whether location services are available on the device. */
  isLocationAvailable: boolean;

  /** Whether location access has been requested. */
  isAccessRequested: boolean;

  /** Whether location access has been granted. */
  isAccessGranted: boolean;

  /**
   * Initialize the location manager.
   * @param callback - Optional callback invoked when initialization is complete.
   */
  init(callback?: () => void): LocationManager;

  /**
   * Get the current device location.
   * @param callback - Callback with location data or null if unavailable.
   */
  getLocation(callback: (data: LocationData | null) => void): LocationManager;

  /** Open the device location settings. */
  openSettings(): LocationManager;
}

// -----------------------------------------------------------------------------
// 5. Init Data Types
// -----------------------------------------------------------------------------

/** A Telegram user as provided in WebApp init data. */
export interface WebAppUser {
  /** Unique user identifier. */
  id: number;

  /** True if the user is a bot. */
  is_bot?: boolean;

  /** User's first name. */
  first_name: string;

  /** User's last name. */
  last_name?: string;

  /** User's username. */
  username?: string;

  /** IETF language tag of the user's language. */
  language_code?: string;

  /** True if the user is a Telegram Premium user. */
  is_premium?: boolean;

  /** True if the user has been added to the attachment menu. */
  added_to_attachment_menu?: boolean;

  /** True if the user allows the bot to write to them. */
  allows_write_to_pm?: boolean;

  /** URL of the user's profile photo. */
  photo_url?: string;
}

/** A Telegram chat as provided in WebApp init data. */
export interface WebAppChat {
  /** Unique chat identifier. */
  id: number;

  /** Type of chat. */
  type: 'group' | 'supergroup' | 'channel';

  /** Title of the chat. */
  title: string;

  /** Username of the chat. */
  username?: string;

  /** URL of the chat's photo. */
  photo_url?: string;
}

/** Data passed to the WebApp during initialization. */
export interface WebAppInitData {
  /** A unique identifier for the WebApp session. */
  query_id?: string;

  /** The user that opened the WebApp. */
  user?: WebAppUser;

  /** The receiver (for inline queries). */
  receiver?: WebAppUser;

  /** The chat from which the WebApp was opened. */
  chat?: WebAppChat;

  /** Type of the chat from which the WebApp was opened. */
  chat_type?: ChatType;

  /** Chat instance identifier. */
  chat_instance?: string;

  /** The start parameter passed via the deep link. */
  start_param?: string;

  /** Unix timestamp after which sendData can be called. */
  can_send_after?: number;

  /** Unix timestamp when the form was opened. */
  auth_date: number;

  /** A hash of all passed parameters for validation. */
  hash: string;

  /** A signature of the init data for third-party verification. */
  signature?: string;
}

// -----------------------------------------------------------------------------
// 6. Main WebApp Interface
// -----------------------------------------------------------------------------

/**
 * The main Telegram WebApp interface.
 * Provides access to all WebApp functionality.
 * @see https://core.telegram.org/bots/webapps
 */
export interface WebApp {
  // ---------------------------------------------------------------------------
  // Properties
  // ---------------------------------------------------------------------------

  /** Raw init data string received from Telegram. */
  readonly initData: string;

  /** Parsed init data object. */
  readonly initDataUnsafe: WebAppInitData;

  /** The version of the Bot API available in the user's Telegram app. */
  readonly version: string;

  /** The name of the platform of the user's Telegram app. */
  readonly platform: string;

  /** The current color scheme: 'light' or 'dark'. */
  readonly colorScheme: 'light' | 'dark';

  /** Current theme parameters. */
  readonly themeParams: ThemeParams;

  /** Whether the WebApp is currently active (in foreground). @since Bot API 8.0 */
  readonly isActive: boolean;

  /** Whether the WebApp is expanded to full height. */
  readonly isExpanded: boolean;

  /** Current viewport height in pixels. */
  readonly viewportHeight: number;

  /** Stable viewport height (does not change with keyboard). */
  readonly viewportStableHeight: number;

  /** Current header color. @since Bot API 6.1 */
  headerColor: string;

  /** Current background color. @since Bot API 6.1 */
  backgroundColor: string;

  /** Current bottom bar color. @since Bot API 7.10 */
  bottomBarColor: string;

  /** Whether the closing confirmation dialog is enabled. @since Bot API 6.2 */
  isClosingConfirmationEnabled: boolean;

  /** Whether vertical swipes are enabled. @since Bot API 7.7 */
  isVerticalSwipesEnabled: boolean;

  /** Whether the WebApp is in fullscreen mode. @since Bot API 8.0 */
  readonly isFullscreen: boolean;

  /** Whether the screen orientation is locked. @since Bot API 8.0 */
  readonly isOrientationLocked: boolean;

  /** Safe area inset values. @since Bot API 8.0 */
  readonly safeAreaInset: SafeAreaInset;

  /** Content safe area inset values. @since Bot API 8.0 */
  readonly contentSafeAreaInset: ContentSafeAreaInset;

  /** The back button in the header. @since Bot API 6.1 */
  readonly BackButton: BackButton;

  /** The main button at the bottom. */
  readonly MainButton: BottomButton;

  /** The secondary button at the bottom. @since Bot API 7.10 */
  readonly SecondaryButton: BottomButton;

  /** The settings button in the header. @since Bot API 7.0 */
  readonly SettingsButton: SettingsButton;

  /** Haptic feedback interface. @since Bot API 6.1 */
  readonly HapticFeedback: HapticFeedback;

  /** Cloud-based key-value storage. @since Bot API 6.9 */
  readonly CloudStorage: CloudStorage;

  /** Biometric authentication manager. @since Bot API 7.2 */
  readonly BiometricManager: BiometricManager;

  /** Accelerometer sensor. @since Bot API 8.0 */
  readonly Accelerometer: Accelerometer;

  /** Gyroscope sensor. @since Bot API 8.0 */
  readonly Gyroscope: Gyroscope;

  /** Device orientation sensor. @since Bot API 8.0 */
  readonly DeviceOrientation: DeviceOrientation;

  /** Location manager. @since Bot API 8.0 */
  readonly LocationManager: LocationManager;

  /** Device-local storage. @since Bot API 9.0 */
  readonly DeviceStorage: DeviceStorage;

  /** Encrypted secure storage. @since Bot API 9.0 */
  readonly SecureStorage: SecureStorage;

  // ---------------------------------------------------------------------------
  // Methods
  // ---------------------------------------------------------------------------

  /**
   * Check if the current version is at least the specified version.
   * @param version - Version string to compare against, e.g. "6.1".
   * @returns True if the current version is >= the specified version.
   */
  isVersionAtLeast(version: string): boolean;

  /**
   * Set the header color.
   * @param color - A hex color string or one of 'bg_color', 'secondary_bg_color'.
   * @since Bot API 6.1
   */
  setHeaderColor(color: string): void;

  /**
   * Set the background color.
   * @param color - A hex color string or one of 'bg_color', 'secondary_bg_color'.
   * @since Bot API 6.1
   */
  setBackgroundColor(color: string): void;

  /**
   * Set the bottom bar color.
   * @param color - A hex color string or one of 'bg_color', 'secondary_bg_color', 'bottom_bar_bg_color'.
   * @since Bot API 7.10
   */
  setBottomBarColor(color: string): void;

  /**
   * Enable the closing confirmation dialog.
   * @since Bot API 6.2
   */
  enableClosingConfirmation(): void;

  /**
   * Disable the closing confirmation dialog.
   * @since Bot API 6.2
   */
  disableClosingConfirmation(): void;

  /**
   * Enable vertical swipes to minimize the WebApp.
   * @since Bot API 7.7
   */
  enableVerticalSwipes(): void;

  /**
   * Disable vertical swipes.
   * @since Bot API 7.7
   */
  disableVerticalSwipes(): void;

  /**
   * Request fullscreen mode.
   * @since Bot API 8.0
   */
  requestFullscreen(): void;

  /**
   * Exit fullscreen mode.
   * @since Bot API 8.0
   */
  exitFullscreen(): void;

  /**
   * Lock the screen orientation.
   * @since Bot API 8.0
   */
  lockOrientation(): void;

  /**
   * Unlock the screen orientation.
   * @since Bot API 8.0
   */
  unlockOrientation(): void;

  /**
   * Add the WebApp to the home screen.
   * @since Bot API 8.0
   */
  addToHomeScreen(): void;

  /**
   * Check the home screen status.
   * @param callback - Optional callback with the home screen status.
   * @since Bot API 8.0
   */
  checkHomeScreenStatus(
    callback?: (status: HomeScreenStatus) => void,
  ): void;

  /**
   * Subscribe to a WebApp event.
   * @param eventType - The event type to listen for.
   * @param callback - The callback function.
   */
  onEvent(eventType: EventType, callback: (...args: unknown[]) => void): void;

  /**
   * Unsubscribe from a WebApp event.
   * @param eventType - The event type to stop listening for.
   * @param callback - The callback function to remove.
   */
  offEvent(eventType: EventType, callback: (...args: unknown[]) => void): void;

  /**
   * Send data to the bot. Max 4096 bytes.
   * @param data - String data to send.
   */
  sendData(data: string): void;

  /**
   * Switch to inline mode with a query.
   * @param query - The inline query string.
   * @param chooseChatTypes - Optional array of chat types to filter.
   * @since Bot API 6.7
   */
  switchInlineQuery(query: string, chooseChatTypes?: ChatType[]): void;

  /**
   * Open a link in the browser.
   * @param url - The URL to open.
   * @param options - Optional settings, e.g. try_instant_view.
   * @since Bot API 6.1
   */
  openLink(url: string, options?: { try_instant_view?: boolean }): void;

  /**
   * Open a Telegram link inside the Telegram app.
   * @param url - A t.me link.
   * @since Bot API 6.1
   */
  openTelegramLink(url: string): void;

  /**
   * Open an invoice by its URL.
   * @param url - The invoice URL.
   * @param callback - Optional callback with the invoice status.
   * @since Bot API 6.1
   */
  openInvoice(
    url: string,
    callback?: (status: InvoiceStatus) => void,
  ): void;

  /**
   * Share a media to a Telegram Story.
   * @param mediaUrl - URL of the media to share.
   * @param params - Optional story sharing parameters.
   * @since Bot API 7.8
   */
  shareToStory(mediaUrl: string, params?: StoryShareParams): void;

  /**
   * Share a message to another chat.
   * @param msgId - The prepared message ID.
   * @param callback - Optional callback with success status.
   * @since Bot API 8.0
   */
  shareMessage(
    msgId: string,
    callback?: (success: boolean) => void,
  ): void;

  /**
   * Set the user's custom emoji status.
   * @param customEmojiId - The custom emoji ID.
   * @param params - Optional parameters including duration.
   * @param callback - Optional callback with success status.
   * @since Bot API 8.0
   */
  setEmojiStatus(
    customEmojiId: string,
    params?: EmojiStatusParams,
    callback?: (success: boolean) => void,
  ): void;

  /**
   * Request access to set the user's emoji status.
   * @param callback - Optional callback with the access granted status.
   * @since Bot API 8.0
   */
  requestEmojiStatusAccess(
    callback?: (granted: boolean) => void,
  ): void;

  /**
   * Download a file.
   * @param params - Download parameters with url and file_name.
   * @param callback - Optional callback with success status.
   * @since Bot API 8.0
   */
  downloadFile(
    params: DownloadFileParams,
    callback?: (success: boolean) => void,
  ): void;

  /**
   * Show a popup with custom buttons.
   * @param params - Popup parameters.
   * @param callback - Optional callback with the pressed button ID.
   * @since Bot API 6.2
   */
  showPopup(
    params: PopupParams,
    callback?: (buttonId: string) => void,
  ): void;

  /**
   * Show an alert popup with a single OK button.
   * @param message - The message to display.
   * @param callback - Optional callback when the popup is closed.
   * @since Bot API 6.2
   */
  showAlert(message: string, callback?: () => void): void;

  /**
   * Show a confirmation popup with OK and Cancel buttons.
   * @param message - The message to display.
   * @param callback - Optional callback with true if OK was pressed.
   * @since Bot API 6.2
   */
  showConfirm(
    message: string,
    callback?: (confirmed: boolean) => void,
  ): void;

  /**
   * Show a QR code scanner popup.
   * @param params - Scanner parameters with optional text.
   * @param callback - Optional callback with the scanned text. Return true to close the popup.
   * @since Bot API 6.4
   */
  showScanQrPopup(
    params: ScanQrPopupParams,
    callback?: (text: string) => boolean | void,
  ): void;

  /**
   * Close the QR code scanner popup.
   * @since Bot API 6.4
   */
  closeScanQrPopup(): void;

  /**
   * Read text from the clipboard.
   * @param callback - Callback with the clipboard text or null.
   * @since Bot API 6.4
   */
  readTextFromClipboard(
    callback?: (text: string | null) => void,
  ): void;

  /**
   * Request write access to send messages to the user.
   * @param callback - Optional callback with the access status.
   * @since Bot API 6.9
   */
  requestWriteAccess(
    callback?: (status: WriteAccessStatus) => void,
  ): void;

  /**
   * Request the user's contact information.
   * @param callback - Optional callback with the request status.
   * @since Bot API 6.9
   */
  requestContact(
    callback?: (status: ContactRequestStatus) => void,
  ): void;

  /** Inform the Telegram app that the WebApp is ready to be displayed. */
  ready(): void;

  /** Expand the WebApp to full height. */
  expand(): void;

  /** Close the WebApp. */
  close(): void;

  /**
   * Hide the native keyboard.
   * @since Bot API 9.1
   */
  hideKeyboard(): void;
}

// -----------------------------------------------------------------------------
// 7. Global Augmentation
// -----------------------------------------------------------------------------

/**
 * Extends the global Window interface to include the Telegram WebApp object.
 */
declare global {
  interface Window {
    Telegram?: {
      WebApp: WebApp;
    };
  }
}
