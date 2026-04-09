import ky from "ky";

import { emitAuthExpired } from "@/lib/auth-events";

let refreshPromise: Promise<boolean> | null = null;

async function attemptRefresh(): Promise<boolean> {
  try {
    const res = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Client-side HTTP instance routed through the BFF proxy.
 * Automatically retries on 401 with a single token refresh attempt (mutex pattern).
 */
export const apiClient = ky.create({
  prefixUrl: "/api/backend",
  timeout: 30_000,
  credentials: "include",
  retry: {
    limit: 2,
    methods: ["get"],
    statusCodes: [408, 502, 503, 504],
  },
  hooks: {
    afterResponse: [
      async (request, _options, response) => {
        if (response.status !== 401) return;

        // Skip refresh for auth routes themselves
        if (new URL(request.url).pathname.startsWith("/api/auth/")) return;

        // Mutex: coalesce concurrent 401 refreshes into one request
        if (!refreshPromise) {
          refreshPromise = attemptRefresh().finally(() => {
            refreshPromise = null;
          });
        }

        const ok = await refreshPromise;
        if (!ok) {
          emitAuthExpired();
          return;
        }

        // Retry the original request with the new cookie
        return ky(request);
      },
    ],
  },
});

/**
 * Client-side instance for local Next.js API routes (auth, session).
 */
export const appClient = ky.create({
  prefixUrl: "",
  timeout: 15_000,
  credentials: "include",
});
