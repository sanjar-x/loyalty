'use client';

import { useEffect } from 'react';

/**
 * Dev-only: fully overrides window.Telegram.WebApp.
 *
 * `<Script src="telegram-web-app.js" strategy="beforeInteractive">` (layout.tsx:93)
 * creates a stub WebApp object when the page loads (version='6.0', initData='').
 * Here we **override** it with a structure that mirrors real Telegram — so that
 * `useTelegramSdkRuntime` (lib/features/telegram/provider.jsx) finds real
 * initData on the next poll tick and the auth flow proceeds normally:
 *   bootstrap → POST /api/auth/telegram → BFF → backend parse → real JWT.
 *
 * Does nothing in production (early return).
 */
export default function InitTelegramMock() {
  useEffect(() => {
    if (process.env.NODE_ENV === 'production') return;
    if (typeof window === 'undefined') return;
    // If this is real Telegram (initData is already present) — do not touch it.
    if (window.Telegram?.WebApp?.initData) return;

    const MOCK_USER = {
      id: 99281932,
      first_name: 'Debug',
      last_name: 'User',
      username: 'debug_user',
      language_code: 'ru',
      is_premium: false,
      allows_write_to_pm: true,
      photo_url: '',
    };

    const authDate = Math.floor(Date.now() / 1000);
    const initData = {
      user: MOCK_USER,
      auth_date: authDate,
      hash: 'mock_hash_no_validation',
      chat_type: 'sender',
      chat_instance: '8428209589180549439',
      start_param: '',
    };

    const initDataRaw = new URLSearchParams({
      user: JSON.stringify(MOCK_USER),
      auth_date: String(authDate),
      hash: 'mock_hash_no_validation',
      chat_type: 'sender',
      chat_instance: '8428209589180549439',
    }).toString();

    const noop = () => {};
    const HapticFeedback = {
      impactOccurred: (style) => console.debug('[mock] Haptic.impact', style),
      notificationOccurred: (t) => console.debug('[mock] Haptic.notification', t),
      selectionChanged: () => console.debug('[mock] Haptic.selection'),
    };
    const BackButton = {
      isVisible: false,
      show() {
        this.isVisible = true;
        console.debug('[mock] BackButton.show');
      },
      hide() {
        this.isVisible = false;
        console.debug('[mock] BackButton.hide');
      },
      onClick: noop,
      offClick: noop,
    };
    const MainButton = {
      text: '',
      color: '#5288c1',
      textColor: '#ffffff',
      isVisible: false,
      isActive: false,
      isProgressVisible: false,
      setText(text) {
        this.text = text;
        return this;
      },
      onClick: noop,
      offClick: noop,
      show() {
        this.isVisible = true;
        return this;
      },
      hide() {
        this.isVisible = false;
        return this;
      },
      enable() {
        this.isActive = true;
        return this;
      },
      disable() {
        this.isActive = false;
        return this;
      },
      showProgress: noop,
      hideProgress: noop,
      setParams(p) {
        Object.assign(this, p);
        return this;
      },
    };

    if (!window.Telegram) window.Telegram = {};
    window.Telegram.WebApp = {
      initData: initDataRaw,
      initDataUnsafe: initData,
      version: '8.0',
      platform: 'web',
      colorScheme: 'light',
      themeParams: {
        bg_color: '#ffffff',
        text_color: '#000000',
        hint_color: '#999999',
        link_color: '#5288c1',
        button_color: '#5288c1',
        button_text_color: '#ffffff',
        secondary_bg_color: '#f5f5f5',
        header_bg_color: '#ffffff',
        accent_text_color: '#5288c1',
        section_bg_color: '#ffffff',
        section_header_text_color: '#5288c1',
        subtitle_text_color: '#999999',
        destructive_text_color: '#ec3942',
      },
      isExpanded: true,
      viewportHeight: window.innerHeight,
      viewportStableHeight: window.innerHeight,
      headerColor: '#ffffff',
      backgroundColor: '#ffffff',
      isClosingConfirmationEnabled: false,
      BackButton,
      MainButton,
      HapticFeedback,
      ready: () => console.debug('[mock] WebApp.ready'),
      expand: () => console.debug('[mock] WebApp.expand'),
      close: () => console.debug('[mock] WebApp.close'),
      onEvent: (eventType, handler) => console.debug('[mock] WebApp.onEvent', eventType),
      offEvent: noop,
      sendData: (data) => console.debug('[mock] WebApp.sendData', data),
      openLink: (url) => window.open(url, '_blank', 'noopener'),
      openTelegramLink: (url) => window.open(url, '_blank', 'noopener'),
      openInvoice: (url, cb) => {
        console.debug('[mock] WebApp.openInvoice', url);
        cb?.('cancelled');
      },
      requestContact: (cb) => {
        console.debug('[mock] WebApp.requestContact');
        cb?.(false);
      },
      switchInlineQuery: noop,
      shareToStory: noop,
      readTextFromClipboard: (cb) => cb?.(''),
      setHeaderColor: noop,
      setBackgroundColor: noop,
      enableClosingConfirmation: noop,
      disableClosingConfirmation: noop,
    };

    console.info('[dev] window.Telegram.WebApp overridden', {
      user: MOCK_USER.username,
      authDate,
      initDataLen: initDataRaw.length,
    });
  }, []);

  return null;
}
