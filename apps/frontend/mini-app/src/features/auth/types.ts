export type AuthProvider = 'telegram' | 'email';

export type AuthStatus = 'idle' | 'loading' | 'authenticated' | 'expired' | 'error' | 'logged_out';

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
}

export interface Identity {
  identityId: string;
  email: string;
  authType: string;
  isActive: boolean;
  createdAt: string;
}

export interface Session {
  id: string;
  ipAddress: string;
  userAgent: string;
  createdAt: string;
  isCurrent: boolean;
}

export interface TelegramAuthResponse {
  ok: boolean;
  isNewUser: boolean;
}
