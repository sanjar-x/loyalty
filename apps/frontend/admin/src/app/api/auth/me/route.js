import { NextResponse } from 'next/server';
import { getAccessToken, decodeJwtPayload } from '@/shared/auth/cookies';

// /api/auth/me — minimal identity surface for the admin shell.
//
// We decode the JWT payload locally to read identity id + session id. We do
// NOT verify the signature here for two reasons:
//   1) Cookie shape is httpOnly + sameSite=lax + secure-in-prod, so client
//      JS cannot set a forged cookie cross-site, and existing XSS would
//      already be a complete compromise.
//   2) Every actual data request goes through `getAccessToken()` and is
//      Bearer-authenticated against the backend, which DOES verify the
//      signature — a forged JWT will fail the first real call and the user
//      will be bounced to /login by the regular 401 path.
// An earlier iteration probed `/api/v1/admin/identities/{sub}` to force a
// signature check, but that endpoint requires `identities:manage`, which
// only super_admins hold — managers were getting locked out of the panel
// despite a valid token. Falling back to local decode is the right
// trade-off here.
export async function GET() {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated' } },
      { status: 401 },
    );
  }

  const payload = decodeJwtPayload(token);
  if (!payload?.sub) {
    return NextResponse.json(
      { error: { code: 'INVALID_TOKEN', message: 'Invalid token payload' } },
      { status: 401 },
    );
  }

  return NextResponse.json(
    {
      identityId: payload.sub,
      sessionId: payload.sid ?? null,
    },
    { headers: { 'Cache-Control': 'private, max-age=60' } },
  );
}
