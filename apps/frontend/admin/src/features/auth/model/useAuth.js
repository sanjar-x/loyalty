'use client';

import { useContext } from 'react';

import { AuthContext } from './AuthProvider';

/**
 * Read the auth context. Always paired with `<AuthProvider>` higher in
 * the tree — the admin shell layout mounts the provider, so all admin
 * pages can read auth state without re-checking the session.
 */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
