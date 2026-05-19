const BACKEND_URL = process.env.BACKEND_URL;

// Headers we relay verbatim from backend to the BFF caller. ETag is the
// only one currently consumed (apiClient stores it for If-Match round-
// trips); the list is here so future cases (Cache-Control,
// X-Request-Id) only need a single edit.
const RELAYED_RESPONSE_HEADERS = ['etag'];

function pickRelayedHeaders(res) {
  const out = {};
  for (const name of RELAYED_RESPONSE_HEADERS) {
    const value = res.headers.get(name);
    if (value != null) out[name] = value;
  }
  return out;
}

export async function backendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
    });

    const data = await res.json().catch(() => null);

    return {
      ok: res.ok,
      status: res.status,
      data,
      // Subset of response headers worth relaying to the BFF caller. Kept
      // narrow on purpose — leaking everything (Set-Cookie, internal
      // tracing) would be a security regression.
      headers: pickRelayedHeaders(res),
    };
  } catch {
    return {
      ok: false,
      status: 502,
      data: {
        error: {
          code: 'BACKEND_UNAVAILABLE',
          message: 'Сервер недоступен',
          details: {},
        },
      },
      headers: {},
    };
  }
}
