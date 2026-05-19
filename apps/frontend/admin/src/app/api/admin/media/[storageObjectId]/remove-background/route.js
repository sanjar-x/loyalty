import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// POST /api/admin/media/{storageObjectId}/remove-background
// → /api/v1/admin/media/{storage_object_id}/remove-background (IMG-007)
//
// Idempotent. Backend returns 202 + RemoveBackgroundResponse on every
// call: the first request kicks off the Bria RMBG-2.0 inference task on
// `image_ml`; subsequent calls return the existing derived storage object
// (`alreadyExisted: true`, `status: 'completed'`) instead of re-running
// the (paid) ML op. UI subscribes to the SSE status stream of
// `derivedStorageObjectId` for live progress.
//
// Feature flag is enforced server-side: when BG_REMOVAL_ENABLED=false the
// backend returns 503 with `error.code === 'BG_REMOVAL_DISABLED'`. We
// pass that envelope through unchanged so the UI can show the right toast.
export async function POST(request, { params }) {
  const csrfFail = assertSameOrigin(request);
  if (csrfFail) return csrfFail;

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

  const { storageObjectId } = await params;
  if (!UUID_RE.test(id)) {
    return bffError('INVALID_ID', 'Invalid storage object ID', {
      status: 400,
    });
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/media/${storageObjectId}/remove-background`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  if (!ok) {
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
  // Always relay the backend's 202 — the response body itself tells the
  // caller whether work was queued (alreadyExisted=false) or skipped
  // (alreadyExisted=true, status='completed').
  return NextResponse.json(data, { status: 202 });
}
