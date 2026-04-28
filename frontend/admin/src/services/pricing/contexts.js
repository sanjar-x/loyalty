export async function listContexts() {
  const res = await fetch('/api/pricing/contexts', { credentials: 'include' });
  if (!res.ok) {
    const err = new Error('Не удалось загрузить контексты');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function getContext(id) {
  const res = await fetch(`/api/pricing/contexts/${id}`, { credentials: 'include' });
  if (!res.ok) {
    const err = new Error('Не удалось загрузить контекст');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function createContext(payload) {
  const res = await fetch('/api/pricing/contexts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = new Error('Не удалось создать контекст');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function updateContext(id, patch) {
  const res = await fetch(`/api/pricing/contexts/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const err = new Error('Не удалось обновить контекст');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function deactivateContext(id) {
  const res = await fetch(`/api/pricing/contexts/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось деактивировать контекст');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function freezeContext(id, { reason }) {
  const res = await fetch(`/api/pricing/contexts/${id}/freeze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = new Error('Не удалось заморозить контекст');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function unfreezeContext(id) {
  const res = await fetch(`/api/pricing/contexts/${id}/unfreeze`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось разморозить контекст');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function getGlobalValues(contextId) {
  const res = await fetch(`/api/pricing/contexts/${contextId}/variables/values`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось загрузить значения переменных');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function setGlobalValue(contextId, variableCode, { value, versionLock }) {
  const res = await fetch(`/api/pricing/contexts/${contextId}/variables/values/${variableCode}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ value, version_lock: versionLock }),
  });
  if (!res.ok) {
    const err = new Error('Не удалось сохранить значение');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}
