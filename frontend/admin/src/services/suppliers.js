/**
 * Fetch active suppliers from the API.
 * Returns { items: SupplierResponse[], total } or throws on failure.
 */
export async function fetchSuppliers() {
  const res = await fetch('/api/suppliers', { credentials: 'include' });
  if (!res.ok) {
    const error = new Error('Не удалось загрузить поставщиков');
    error.status = res.status;
    throw error;
  }
  const data = await res.json();
  // Filter to active suppliers only
  const items = (data.items ?? []).filter((s) => s.isActive);
  return { items, total: items.length };
}

/**
 * Create a new supplier.
 * @param {{ name: string, type: string, countryCode: string, subdivisionCode?: string | null }} payload
 * @returns {Promise<{ id: string }>}
 */
export async function createSupplier(payload) {
  const res = await fetch('/api/suppliers', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(
      data?.error?.message ??
        data?.detail?.message ??
        'Ошибка создания поставщика',
    );
  }
  return res.json();
}
