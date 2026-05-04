import { NextResponse } from 'next/server';
import { getAccessToken } from '@/shared/auth/cookies';

// Hosts the proxy may PUT to. Configured via env so dev (MinIO) and prod
// (S3 / R2 / etc.) are explicit. Rejects arbitrary client-supplied targets.
const S3_ALLOWED_HOSTS = (process.env.S3_UPLOAD_ALLOWED_HOSTS ?? '')
  .split(',')
  .map((s) => s.trim().toLowerCase())
  .filter(Boolean);

const PRIVATE_HOST_RE = /^(0\.0\.0\.0|169\.254\.|::1|fc00:|fe80:)/i;

function isS3HostAllowed(hostname) {
  const host = hostname.toLowerCase();
  if (PRIVATE_HOST_RE.test(host)) return false;
  return S3_ALLOWED_HOSTS.includes(host);
}

// Per-request body cap. Image backend should already enforce this, but
// belt-and-suspenders prevents OOM on a single very large file uploaded
// directly to this BFF.
const MAX_BYTES = Number(process.env.S3_UPLOAD_MAX_BYTES ?? 50 * 1024 * 1024);

export async function POST(request) {
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

  const formData = await request.formData();
  const file = formData.get('file');
  const presignedUrl = formData.get('presignedUrl');

  if (!file || !presignedUrl) {
    return NextResponse.json(
      {
        error: {
          code: 'MISSING_FIELDS',
          message: 'file and presignedUrl are required',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  let target;
  try {
    target = new URL(String(presignedUrl));
  } catch {
    target = null;
  }
  if (
    !target ||
    !(target.protocol === 'https:' || target.protocol === 'http:') ||
    !isS3HostAllowed(target.hostname)
  ) {
    return NextResponse.json(
      {
        error: {
          code: 'BAD_REQUEST',
          message: 'presignedUrl host not permitted',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  if (typeof file.size === 'number' && file.size > MAX_BYTES) {
    return NextResponse.json(
      {
        error: {
          code: 'PAYLOAD_TOO_LARGE',
          message: `File exceeds ${MAX_BYTES} bytes`,
          details: { size: file.size, max: MAX_BYTES },
        },
      },
      { status: 413 },
    );
  }

  try {
    // Presigned URLs sign a fixed set of headers (X-Amz-SignedHeaders).
    // Sending anything outside that set — notably Content-Length — makes
    // S3-compatible providers (Tigris, R2, MinIO with strict mode) reject
    // the request with 403 SignatureDoesNotMatch. Buffer the body so we can
    // PUT without Transfer-Encoding: chunked and without extra headers.
    const body = Buffer.from(await file.arrayBuffer());
    const res = await fetch(target, {
      method: 'PUT',
      body,
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
      },
    });

    if (!res.ok) {
      const body = await res.text().catch(() => '');
      return NextResponse.json(
        {
          error: {
            code: 'S3_UPLOAD_FAILED',
            message: `S3 upload failed: ${res.status}`,
            details: { status: res.status, body: body.slice(0, 1024) },
          },
        },
        { status: 502 },
      );
    }

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: 'S3_UPLOAD_FAILED',
          message: 'S3 upload failed',
          details: {},
        },
      },
      { status: 502 },
    );
  }
}
