export async function listVariables({ scope, isSystem, isFxRate } = {}) {
  const params = new URLSearchParams();
  if (scope) params.set('scope', scope);
  if (isSystem !== undefined) params.set('is_system', String(isSystem));
  if (isFxRate !== undefined) params.set('is_fx_rate', String(isFxRate));
  const qs = params.toString();

  const res = await fetch(`/api/pricing/variables${qs ? `?${qs}` : ''}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось загрузить переменные');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function getVariable(id) {
  const res = await fetch(`/api/pricing/variables/${id}`, { credentials: 'include' });
  if (!res.ok) {
    const err = new Error('Не удалось загрузить переменную');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function createVariable(payload) {
  const res = await fetch('/api/pricing/variables', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = new Error('Не удалось создать переменную');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function updateVariable(id, patch) {
  const res = await fetch(`/api/pricing/variables/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const err = new Error('Не удалось обновить переменную');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function deleteVariable(id) {
  const res = await fetch(`/api/pricing/variables/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось удалить переменную');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return true;
}
