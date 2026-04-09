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
