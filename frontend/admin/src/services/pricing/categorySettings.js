export async function getCategorySettings(categoryId, contextId) {
  const res = await fetch(
    `/api/pricing/categories/${categoryId}/pricing?context_id=${contextId}`,
    { credentials: 'include' },
  );
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = new Error('Не удалось загрузить настройки категории');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function upsertCategorySettings(categoryId, contextId, payload) {
  const res = await fetch(
    `/api/pricing/categories/${categoryId}/pricing/${contextId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    },
  );
  if (!res.ok) {
    const err = new Error('Не удалось сохранить настройки категории');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function deleteCategorySettings(categoryId, contextId) {
  const res = await fetch(
    `/api/pricing/categories/${categoryId}/pricing/${contextId}`,
    { method: 'DELETE', credentials: 'include' },
  );
  if (!res.ok) {
    const err = new Error('Не удалось удалить настройки категории');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return true;
}
