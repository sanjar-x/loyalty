export async function recomputeSku(skuId) {
  const res = await fetch(`/api/pricing/recompute/skus/${skuId}`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось запустить пересчёт SKU');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function recomputeContext(contextId) {
  const res = await fetch(`/api/pricing/recompute/contexts/${contextId}`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось запустить пересчёт контекста');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function recomputeCategory(categoryId) {
  const res = await fetch(`/api/pricing/recompute/categories/${categoryId}`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось запустить пересчёт категории');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function recomputeSupplier(supplierId) {
  const res = await fetch(`/api/pricing/recompute/suppliers/${supplierId}`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    const err = new Error('Не удалось запустить пересчёт поставщика');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}
