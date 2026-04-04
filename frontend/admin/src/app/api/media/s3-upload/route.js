import { NextResponse } from 'next/server';
import { getAccessToken } from '@/lib/auth';

export async function POST(request) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const formData = await request.formData();
  const file = formData.get('file');
  const presignedUrl = formData.get('presignedUrl');

  if (!file || !presignedUrl) {
    return NextResponse.json(
      { error: { code: 'MISSING_FIELDS', message: 'file and presignedUrl are required', details: {} } },
      { status: 400 },
    );
  }

  try {
    const buffer = Buffer.from(await file.arrayBuffer());
    const res = await fetch(presignedUrl, {
      method: 'PUT',
      body: buffer,
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: { code: 'S3_UPLOAD_FAILED', message: `S3 upload failed: ${res.status}`, details: {} } },
        { status: 502 },
      );
    }

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch {
    return NextResponse.json(
      { error: { code: 'S3_UPLOAD_FAILED', message: 'S3 upload failed', details: {} } },
      { status: 502 },
    );
  }
}
