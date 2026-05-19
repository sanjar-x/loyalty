import { bffError } from '@/shared/api/bff';

// Refresh is owned exclusively by the Edge proxy (src/proxy.js). Two
// independent refresh paths would race on a one-time refresh_token,
// surface as REFRESH_TOKEN_REUSE on the backend, and revoke every
// session of the identity — see PR #39 (commit fa2d214) for the
// post-mortem.
//
// We keep this route as a loud 410 instead of deleting it, so any
// regressive client call (a stale fetch helper, a new dependency with
// its own interceptor, a copy-pasted snippet) fails fast at the BFF
// boundary with a self-documenting code, rather than silently re-
// introducing the race.
export async function POST() {
  return bffError(
    'REFRESH_HANDLED_BY_PROXY',
    'Refresh is handled by the Edge proxy; do not call this endpoint from the client.',
    { status: 410 },
  );
}
