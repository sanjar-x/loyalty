import { NextResponse } from 'next/server';
import { getAccessToken } from '@/shared/auth/cookies';

// Hostnames whose origin this proxy may forward to. SSRF mitigation —
// anything outside the allow-list is rejected. Comma-separated env var,
// subdomains require explicit listing.
const PROXY_ALLOWED_HOSTS = (process.env.MEDIA_PROXY_ALLOWED_HOSTS ?? '')
  .split(',')
  .map((s) => s.trim().toLowerCase())
  .filter(Boolean);

// Defense-in-depth: refuse private/loopback/link-local hostnames even if
// they slip through the allow-list. Covers cloud metadata (169.254.169.254)
// and internal CIDR leaks. DNS-rebinding still possible — stronger fix is a
// real resolve + post-resolve recheck.
const PRIVATE_HOST_RE =
  /^(localhost|0\.0\.0\.0|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|::1|fc00:|fe80:)/i;

function isHostAllowed(hostname) {
  const host = hostname.toLowerCase();
  if (PRIVATE_HOST_RE.test(host)) return false;
  return PROXY_ALLOWED_HOSTS.includes(host);
}

export async function GET(request) {
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

  const raw = new URL(request.url).searchParams.get('url');
  let target;
  try {
    target = raw ? new URL(raw) : null;
  } catch {
    target = null;
  }
  if (
    !target ||
    target.protocol !== 'https:' ||
    !isHostAllowed(target.hostname)
  ) {
    return NextResponse.json(
      {
        error: {
          code: 'BAD_REQUEST',
          message: 'URL not permitted',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  try {
    const res = await fetch(target, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; LoyalityAdmin/1.0)',
        Accept: 'image/*,*/*',
      },
      // Don't auto-follow redirects to a different host — would bypass allow-list.
      redirect: 'manual',
    });
    if (!res.ok) {
      return new Response(null, { status: res.status });
    }

    return new Response(res.body, {
      headers: {
        'Content-Type': res.headers.get('Content-Type') || 'image/jpeg',
        'Cache-Control': 'private, max-age=3600',
      },
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: 'FETCH_FAILED',
          message: 'Failed to fetch image',
          details: {},
        },
      },
      { status: 502 },
    );
  }
}
