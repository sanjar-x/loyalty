import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/backend";

const backendBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: "include",
});

const appBaseQuery = fetchBaseQuery({
  baseUrl: "",
  credentials: "include",
});

const baseQuery = async (args, api, extraOptions) => {
  const url = typeof args === "string" ? args : args?.url;

  if (typeof url === "string" && url.startsWith("/api/session/")) {
    return appBaseQuery(args, api, extraOptions);
  }

  return backendBaseQuery(args, api, extraOptions);
};

export const api = createApi({
  reducerPath: "api",
  baseQuery,
  tagTypes: [
    "User",
    "Products",
    "Product",
    "Categories",
    "Types",
    "Brands",
    "Favorites",
    "Cart",
    "Orders",
    "Payments",
    "Shipments",
    "Referrals",
    "PVZ",
    "SearchHistory",
  ],
  endpoints: () => ({}),
});
