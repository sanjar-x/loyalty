// Backend FSM forces DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED. Hide
// that ladder from the UI: one click on "Опубликовать" runs the full chain
// from whatever the current status is. Mirrors the backend transition graph
// exposed via PRODUCT_STATUS_TRANSITIONS so any future state insertion is
// caught by the unit tests.
const PUBLISH_PATH = ['enriching', 'ready_for_review', 'published'];

/**
 * Compute the slice of PUBLISH_PATH still to traverse from `currentStatus`.
 * Pure helper — no React, no API, no state. Lives in `lib/` so consumers
 * can call it from validation/preview code without dragging the publish
 * mutation hook along.
 */
export function pathToPublished(currentStatus) {
  if (currentStatus === 'published') return [];
  if (currentStatus === 'draft') return PUBLISH_PATH;
  const idx = PUBLISH_PATH.indexOf(currentStatus);
  if (idx === -1) {
    // Not in the publish ladder (archived, unknown) — caller decides what
    // to do; we throw so the mutation surfaces it.
    throw Object.assign(
      new Error(`Из статуса «${currentStatus}» нельзя опубликовать напрямую`),
      { code: 'INVALID_TRANSITION' },
    );
  }
  return PUBLISH_PATH.slice(idx + 1);
}
