import { NextResponse } from 'next/server';
import { getAccessToken, decodeJwtPayload } from '@/lib/auth';

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

  return NextResponse.json({
    identityId: payload.sub,
    sessionId: payload.sid ?? null,
  });
}
