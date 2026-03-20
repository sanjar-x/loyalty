export interface TelegramUser {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
  is_premium?: boolean;
}

export interface TelegramInitDataUnsafe {
  user?: TelegramUser;
  auth_date?: number;
  hash?: string;
  start_param?: string;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: TelegramInitDataUnsafe;
  version: string;
  platform: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  disableVerticalSwipes?: () => void;
  requestFullscreen?: () => void;
  requestFullScreen?: () => void;
  setBackgroundColor: (color: string) => void;
  setHeaderColor: (color: string) => void;
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
    isVisible: boolean;
  };
  showPopup?: (opts: { message: string }) => void;
  openTelegramLink?: (url: string) => void;
  MainButton: {
    show: () => void;
    hide: () => void;
    setText: (text: string) => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
    isVisible: boolean;
  };
}

export interface DebugUser {
  tg_id: string;
  username: string;
  id: number;
  registration_date?: string;
  points?: number;
  level?: string;
}
