// Default cache tuning for queries created via TanStack Query.
//
// Per-key staleTime overrides should be applied at the hook level, not here.
// This file is the single source of truth for the *default* policy and the
// well-known per-domain windows we re-use across slices.

const SECOND = 1_000;
const MINUTE = 60 * SECOND;

/** Default freshness window for an admin list/detail. */
export const DEFAULT_STALE_TIME_MS = 30 * SECOND;

/** Default cache retention after the last subscriber unsubscribes. */
export const DEFAULT_GC_TIME_MS = 5 * MINUTE;

/** Default network retry budget for transient (5xx, network) failures. */
export const DEFAULT_RETRY_COUNT = 2;

// ---- Per-domain staleTime windows (used by *.queries.js hooks) ----------

/** Slowly-changing reference data (brands, suppliers, countries, categories). */
export const REFERENCE_DATA_STALE_TIME_MS = 5 * MINUTE;

/** Effectively static during a session (subdivisions, permissions). */
export const SESSION_STATIC_STALE_TIME_MS = 30 * MINUTE;
