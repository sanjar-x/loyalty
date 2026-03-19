import "server-only";

function getGlobalStore() {
  const g = globalThis;
  if (!g.__tg_handoff_store) g.__tg_handoff_store = new Map();
  return g.__tg_handoff_store;
}

function cleanupExpired(store, now) {
  for (const [k, v] of store.entries()) {
    if (v.expiresAtMs <= now) store.delete(k);
  }
}

export const handoffStore = {
  set(code, payload) {
    const store = getGlobalStore();
    cleanupExpired(store, Date.now());
    store.set(code, payload);
  },
  consume(code) {
    const store = getGlobalStore();
    cleanupExpired(store, Date.now());
    const payload = store.get(code) ?? null;
    if (payload) store.delete(code);
    return payload;
  },
};
