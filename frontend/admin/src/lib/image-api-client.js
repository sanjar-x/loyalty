const IMAGE_BACKEND_URL = process.env.IMAGE_BACKEND_URL;
const IMAGE_BACKEND_API_KEY = process.env.IMAGE_BACKEND_API_KEY;

if (!IMAGE_BACKEND_URL) console.warn('[image-api-client] IMAGE_BACKEND_URL is not set');
if (!IMAGE_BACKEND_API_KEY) console.warn('[image-api-client] IMAGE_BACKEND_API_KEY is not set');

export async function imageBackendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

  try {
    const res = await fetch(`${IMAGE_BACKEND_URL}${path}`, {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': IMAGE_BACKEND_API_KEY,
        ...headers,
      },
    });

    const data = await res.json().catch(() => null);

    return { ok: res.ok, status: res.status, data };
  } catch {
    return {
      ok: false,
      status: 502,
      data: {
        error: {
          code: 'IMAGE_BACKEND_UNAVAILABLE',
          message: 'Image service unreachable',
          details: {},
        },
      },
    };
  }
}
