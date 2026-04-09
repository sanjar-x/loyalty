export const queryKeys = {
  user: {
    all: ["user"] as const,
    me: () => [...queryKeys.user.all, "me"] as const,
  },
  products: {
    all: ["products"] as const,
    lists: () => [...queryKeys.products.all, "list"] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.products.lists(), filters] as const,
    details: () => [...queryKeys.products.all, "detail"] as const,
    detail: (id: string) => [...queryKeys.products.details(), id] as const,
    latest: (limit: number) =>
      [...queryKeys.products.all, "latest", limit] as const,
    latestPurchased: (limit: number) =>
      [...queryKeys.products.all, "latest-purchased", limit] as const,
    byIds: (ids: string[]) =>
      [...queryKeys.products.all, "by-ids", ids] as const,
  },
  categories: {
    all: ["categories"] as const,
    list: () => [...queryKeys.categories.all, "list"] as const,
    withTypes: () => [...queryKeys.categories.all, "with-types"] as const,
  },
  brands: {
    all: ["brands"] as const,
    list: () => [...queryKeys.brands.all, "list"] as const,
    search: (query: string) =>
      [...queryKeys.brands.all, "search", query] as const,
    detail: (id: string) => [...queryKeys.brands.all, "detail", id] as const,
  },
  cart: {
    all: ["cart"] as const,
  },
  favorites: {
    all: ["favorites"] as const,
    list: (itemType: string) =>
      [...queryKeys.favorites.all, itemType] as const,
  },
  orders: {
    all: ["orders"] as const,
    list: (userId?: string) =>
      [...queryKeys.orders.all, "list", userId] as const,
    detail: (id: string) => [...queryKeys.orders.all, "detail", id] as const,
  },
  search: {
    all: ["search"] as const,
    suggestions: (query: string) =>
      [...queryKeys.search.all, "suggestions", query] as const,
    history: () => [...queryKeys.search.all, "history"] as const,
  },
  referrals: {
    all: ["referrals"] as const,
    link: () => [...queryKeys.referrals.all, "link"] as const,
    invited: () => [...queryKeys.referrals.all, "invited"] as const,
    discount: () => [...queryKeys.referrals.all, "discount"] as const,
    stats: () => [...queryKeys.referrals.all, "stats"] as const,
  },
} as const;
