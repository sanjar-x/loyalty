import type {
  ContentSafeAreaInset,
  SafeAreaInset,
  ThemeParams,
  WebApp,
} from './types';

const THEME_KEY_TO_CSS: Record<string, string> = {
  bg_color: '--tg-theme-bg-color',
  text_color: '--tg-theme-text-color',
  hint_color: '--tg-theme-hint-color',
  link_color: '--tg-theme-link-color',
  button_color: '--tg-theme-button-color',
  button_text_color: '--tg-theme-button-text-color',
  secondary_bg_color: '--tg-theme-secondary-bg-color',
  header_bg_color: '--tg-theme-header-bg-color',
  bottom_bar_bg_color: '--tg-theme-bottom-bar-bg-color',
  accent_text_color: '--tg-theme-accent-text-color',
  section_bg_color: '--tg-theme-section-bg-color',
  section_header_text_color: '--tg-theme-section-header-text-color',
  section_separator_color: '--tg-theme-section-separator-color',
  subtitle_text_color: '--tg-theme-subtitle-text-color',
  destructive_text_color: '--tg-theme-destructive-text-color',
};

export function setThemeCSSVars(params: ThemeParams): void {
  const style = document.documentElement.style;

  for (const [key, cssVar] of Object.entries(THEME_KEY_TO_CSS)) {
    const value = (params as Record<string, string | undefined>)[key];
    if (value) {
      style.setProperty(cssVar, value);
    } else {
      style.removeProperty(cssVar);
    }
  }
}

export function setViewportCSSVars(height: number, stableHeight: number): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-viewport-height', `${height}px`);
  style.setProperty('--tg-viewport-stable-height', `${stableHeight}px`);
}

export function setSafeAreaCSSVars(inset: SafeAreaInset): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-safe-area-top', `${inset.top}px`);
  style.setProperty('--tg-safe-area-bottom', `${inset.bottom}px`);
  style.setProperty('--tg-safe-area-left', `${inset.left}px`);
  style.setProperty('--tg-safe-area-right', `${inset.right}px`);
}

export function setContentSafeAreaCSSVars(inset: ContentSafeAreaInset): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-content-safe-area-top', `${inset.top}px`);
  style.setProperty('--tg-content-safe-area-bottom', `${inset.bottom}px`);
  style.setProperty('--tg-content-safe-area-left', `${inset.left}px`);
  style.setProperty('--tg-content-safe-area-right', `${inset.right}px`);
}

export function setMetaCSSVars(isExpanded: boolean, isMobile: boolean): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-is-expanded', isExpanded ? '1' : '0');
  style.setProperty('--tg-is-mobile', isMobile ? '1' : '0');
}

export function clearAllCSSVars(): void {
  const style = document.documentElement.style;

  for (const cssVar of Object.values(THEME_KEY_TO_CSS)) {
    style.removeProperty(cssVar);
  }

  style.removeProperty('--tg-viewport-height');
  style.removeProperty('--tg-viewport-stable-height');
  style.removeProperty('--tg-safe-area-top');
  style.removeProperty('--tg-safe-area-bottom');
  style.removeProperty('--tg-safe-area-left');
  style.removeProperty('--tg-safe-area-right');
  style.removeProperty('--tg-content-safe-area-top');
  style.removeProperty('--tg-content-safe-area-bottom');
  style.removeProperty('--tg-content-safe-area-left');
  style.removeProperty('--tg-content-safe-area-right');
  style.removeProperty('--tg-is-expanded');
  style.removeProperty('--tg-is-mobile');
}

export function applyThemeColors(webApp: WebApp): void {
  if (typeof document === 'undefined') return;

  const appBg =
    getComputedStyle(document.documentElement)
      .getPropertyValue('--app-background')
      .trim() || '#f6f5f3';

  try {
    webApp.setBackgroundColor(appBg);
    webApp.setHeaderColor(appBg);
  } catch {
    // Older Telegram versions may not support these color APIs.
  }
}
