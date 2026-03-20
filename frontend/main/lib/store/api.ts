import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type {
  BaseQueryFn,
  FetchArgs,
  FetchBaseQueryError,
  FetchBaseQueryMeta,
} from "@reduxjs/toolkit/query";
import { sessionExpired } from "./authSlice";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/backend";

const backendBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: "include",
});

const appBaseQuery = fetchBaseQuery({
  baseUrl: "",
  credentials: "include",
});

const rawBaseQuery: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  const url = typeof args === "string" ? args : args?.url;

  if (typeof url === "string" && url.startsWith("/api/session/")) {
    return appBaseQuery(args, api, extraOptions);
  }

  return backendBaseQuery(args, api, extraOptions);
};

// Mutex: ensures only one refresh request flies at a time.
// Prevents token stampede when multiple concurrent requests get 401.
type RefreshResult = { data?: unknown; error?: FetchBaseQueryError };
let refreshPromise: Promise<RefreshResult> | null = null;

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  const reqUrl = typeof args === "string" ? args : args?.url;
  const isSessionRoute = typeof reqUrl === "string" && reqUrl.startsWith("/api/session/");

  if (result.error && result.error.status === 401 && !isSessionRoute) {
    // Coalesce concurrent refresh calls into a single request
    if (!refreshPromise) {
      refreshPromise = Promise.resolve(
        rawBaseQuery(
          { url: "/api/session/refresh", method: "POST" },
          api,
          extraOptions,
        ),
      ).finally(() => {
        refreshPromise = null;
      });
    }

    const refreshResult = await refreshPromise;

    if (refreshResult?.error) {
      api.dispatch(sessionExpired());
      return result;
    }

    // Retry the original request with fresh cookies
    result = await rawBaseQuery(args, api, extraOptions);
  }

  return result;
};

export const api = createApi({
  reducerPath: "api",
  baseQuery: baseQueryWithReauth,
  tagTypes: ["User", "Products", "Product", "Categories", "Brands"],
  endpoints: () => ({}),
});
