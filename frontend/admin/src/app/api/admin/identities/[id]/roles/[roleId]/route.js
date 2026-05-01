import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { getAccessToken } from '@/shared/auth/cookies';

export async function DELETE(request, { params }) {
  const { id, roleId } = await params;
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      {
        error: {
          code: 'UNAUTHORIZED',
          message: 'Not authenticated',
          details: {},
        },
      },
      { status: 401 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/identities/${id}/roles/${roleId}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  if (status === 204 || ok) {
    return NextResponse.json({ success: true });
  }

  return NextResponse.json(
    data ?? {
      error: {
        code: 'SERVICE_UNAVAILABLE',
        message: 'Backend unavailable',
        details: {},
      },
    },
    { status: status || 502 },
  );
}
