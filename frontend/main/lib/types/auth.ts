export type AuthProvider = "telegram" | "email";

export interface LoginRequest {
  email: string;
  password: string;
}

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
