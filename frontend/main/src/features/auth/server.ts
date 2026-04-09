export {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  getBackendBaseUrl,
  isProduction,
  shouldSecureCookie,
  getCookieDomain,
  serializeCookie,
  clearCookieHeader,
  setTokenCookies,
  clearTokenCookies,
} from './lib/cookie-helpers';

export {
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from './lib/debug';
