export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface ApiError {
  detail: string;
  status: number;
}

export type SortOrder = "asc" | "desc";
