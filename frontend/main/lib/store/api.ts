import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type {
  BaseQueryFn,
  FetchArgs,
  FetchBaseQueryError,
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

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  if (result.error && result.error.status === 401) {
    // Attempt silent refresh
    const refreshResult = await rawBaseQuery(
      { url: "/api/session/refresh", method: "POST" },
      api,
      extraOptions,
    );

    if (refreshResult.error) {
      // Refresh failed — session is dead
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
