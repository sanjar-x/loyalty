export async function listVersions(contextId, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  const qs = params.toString();

  const res = await fetch(
    `/api/pricing/contexts/${contextId}/formula/versions${qs ? `?${qs}` : ''}`,
    { credentials: 'include' },
  );
  if (!res.ok) {
    const err = new Error('Не удалось загрузить версии формулы');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function getVersion(contextId, versionId) {
  const res = await fetch(
    `/api/pricing/contexts/${contextId}/formula/versions/${versionId}`,
    { credentials: 'include' },
  );
  if (!res.ok) {
    const err = new Error('Не удалось загрузить версию формулы');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function getDraft(contextId) {
  const res = await fetch(
    `/api/pricing/contexts/${contextId}/formula/draft`,
    { credentials: 'include' },
  );
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = new Error('Не удалось загрузить черновик');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function saveDraft(contextId, { ast, expectedVersionLock }) {
  const body = { ast };
  if (expectedVersionLock != null) body.expected_version_lock = expectedVersionLock;

  const res = await fetch(
    `/api/pricing/contexts/${contextId}/formula/draft`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) {
    const err = new Error('Не удалось сохранить черновик');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function deleteDraft(contextId) {
  const res = await fetch(
    `/api/pricing/contexts/${contextId}/formula/draft`,
    { method: 'DELETE', credentials: 'include' },
  );
  if (!res.ok) {
    const err = new Error('Не удалось удалить черновик');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function publishDraft(contextId) {
  const res = await fetch(
    `/api/pricing/contexts/${contextId}/formula/draft/publish`,
    { method: 'POST', credentials: 'include' },
  );
  if (!res.ok) {
    const err = new Error('Не удалось опубликовать формулу');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function rollbackVersion(contextId, versionId) {
  const res = await fetch(
    `/api/pricing/contexts/${contextId}/formula/versions/${versionId}/rollback`,
    { method: 'POST', credentials: 'include' },
  );
  if (!res.ok) {
    const err = new Error('Не удалось откатить версию');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}

export async function previewPrice({ productId, categoryId, contextId, supplierId }) {
  const body = {
    product_id: productId,
    category_id: categoryId,
    context_id: contextId,
  };
  if (supplierId) body.supplier_id = supplierId;

  const res = await fetch('/api/pricing/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = new Error('Не удалось рассчитать цену');
    err.status = res.status;
    try { err.data = await res.json(); } catch {}
    throw err;
  }
  return res.json();
}
