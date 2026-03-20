import type { AuthProvider } from "@/lib/types/auth";

export interface AuthState {
  provider: AuthProvider | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
