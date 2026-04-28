export async function getSupplierSettings(supplierId) {
  const res = await fetch(`/api/pricing/suppliers/${supplierId}/pricing`, {
    credentials: 'include',
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = new Error('Не удалось загрузить настройки поставщика');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function upsertSupplierSettings(supplierId, payload) {
  const res = await fetch(`/api/pricing/suppliers/${supplierId}/pricing`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = new Error('Не удалось сохранить настройки поставщика');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}
