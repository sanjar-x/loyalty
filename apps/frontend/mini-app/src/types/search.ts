export interface SearchSuggestion {
  id: string;
  text: string;
  type: string;
  [key: string]: unknown;
}

export interface SearchHistoryItem {
  id: string;
  userId: string | null;
  query: string;
  parameters: Record<string, unknown>;
  searchedAt: string;
}

export interface CreateSearchHistoryPayload {
  query: string;
  parameters?: Record<string, unknown>;
}
