import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type AuthStatus = "idle" | "loading" | "authenticated" | "expired" | "error";

interface AuthState {
  status: AuthStatus;
  isNewUser: boolean;
  error: string | null;
}

const initialState: AuthState = {
  status: "idle",
  isNewUser: false,
  error: null,
};

export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    authStart(state) {
      state.status = "loading";
      state.error = null;
    },
    authSuccess(state, action: PayloadAction<{ isNewUser: boolean }>) {
      state.status = "authenticated";
      state.isNewUser = action.payload.isNewUser;
      state.error = null;
    },
    authFailure(state, action: PayloadAction<string>) {
      state.status = "error";
      state.error = action.payload;
    },
    sessionExpired(state) {
      state.status = "expired";
    },
    logout(state) {
      state.status = "idle";
      state.isNewUser = false;
      state.error = null;
    },
  },
});

export const { authStart, authSuccess, authFailure, sessionExpired, logout } =
  authSlice.actions;

export const selectAuthStatus = (state: { auth: AuthState }) => state.auth.status;
export const selectIsAuthenticated = (state: { auth: AuthState }) =>
  state.auth.status === "authenticated";
export const selectIsNewUser = (state: { auth: AuthState }) => state.auth.isNewUser;
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error;
