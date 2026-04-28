export async function listMappings() {
  const res = await fetch('/api/pricing/supplier-type-mapping', {
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось загрузить маппинги');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function getMapping(supplierType) {
  const res = await fetch(`/api/pricing/supplier-type-mapping/${supplierType}`, {
    credentials: 'include',
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = new Error('Не удалось загрузить маппинг');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function upsertMapping(supplierType, { contextId }) {
  const res = await fetch(`/api/pricing/supplier-type-mapping/${supplierType}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ context_id: contextId }),
  });
  if (!res.ok) {
    const err = new Error('Не удалось сохранить маппинг');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function deleteMapping(supplierType) {
  const res = await fetch(`/api/pricing/supplier-type-mapping/${supplierType}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось удалить маппинг');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return true;
}
