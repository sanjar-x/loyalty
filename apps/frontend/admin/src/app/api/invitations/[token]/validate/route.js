import { proxyToBackend } from '@/shared/api/bff';

// GET /api/invitations/{token}/validate (public)
//
// Reachable without auth — the invitee landing on /invite/{token} has no
// session yet. The Edge proxy must bypass /api/invitations/* (see
// src/proxy.js AUTH_BYPASS_PATHS); proxyToBackend's `requireAuth: false`
// just ensures we don't 401 inside this handler. `csrf: false` because
// GETs are safe and the public page has no Origin to assert against.
export const GET = proxyToBackend({
  pathFn: ({ token }) => `/api/v1/invitations/${token}/validate`,
  requireAuth: false,
  csrf: false,
});
