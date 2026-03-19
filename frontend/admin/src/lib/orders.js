/**
 * Resolves the aggregate order status based on individual item statuses.
 *
 * @param {string}   currentStatus – current order-level status
 * @param {string[]} statuses      – per-item status labels (UI strings)
 * @returns {string} resolved status key
 */
export function resolveOrderStatus(currentStatus, statuses) {
  const allCanceled =
    statuses.length > 0 && statuses.every((status) => status === 'Отменен');
  if (allCanceled) {
    return 'canceled';
  }

  if (statuses.some((status) => status === 'В пути')) {
    return 'in_transit';
  }

  if (currentStatus === 'pickup_point' || currentStatus === 'received') {
    return currentStatus;
  }

  return 'placed';
}
