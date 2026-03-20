import "server-only";

export interface HandoffPayload {
  user: Record<string, unknown>;
  createdAtMs: number;
  expiresAtMs: number;
}

function getGlobalStore(): Map<string, HandoffPayload> {
  const g = globalThis as typeof globalThis & {
    __tg_handoff_store?: Map<string, HandoffPayload>;
  };
  if (!g.__tg_handoff_store) g.__tg_handoff_store = new Map();
  return g.__tg_handoff_store;
}

function cleanupExpired(
  store: Map<string, HandoffPayload>,
  now: number,
): void {
  for (const [k, v] of store.entries()) {
    if (v.expiresAtMs <= now) store.delete(k);
  }
}

export const handoffStore = {
  set(code: string, payload: HandoffPayload): void {
    const store = getGlobalStore();
    cleanupExpired(store, Date.now());
    store.set(code, payload);
  },
  consume(code: string): HandoffPayload | null {
    const store = getGlobalStore();
    cleanupExpired(store, Date.now());
    const payload = store.get(code) ?? null;
    if (payload) store.delete(code);
    return payload;
  },
};
