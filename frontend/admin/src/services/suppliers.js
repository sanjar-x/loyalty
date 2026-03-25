/**
 * Fetch active suppliers from the API.
 * Returns { items: SupplierResponse[], total } or empty on failure.
 */
export async function fetchSuppliers() {
  try {
    const res = await fetch('/api/suppliers', { credentials: 'include' });
    if (!res.ok) return { items: [], total: 0 };
    const data = await res.json();
    // Filter to active suppliers only
    const items = (data.items ?? []).filter((s) => s.isActive);
    return { items, total: items.length };
  } catch {
    return { items: [], total: 0 };
  }
}
