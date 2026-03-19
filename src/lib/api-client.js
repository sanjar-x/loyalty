const BACKEND_URL = process.env.BACKEND_URL;

export async function backendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });

  const data = await res.json().catch(() => null);

  return { ok: res.ok, status: res.status, data };
}
