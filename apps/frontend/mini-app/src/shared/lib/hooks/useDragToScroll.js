'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Desktop-friendly drag-to-scroll + wheel proxy hook.
 *
 * In a mobile/touch environment, horizontal `overflow-x: auto` containers work
 * via native swipe. On desktop, the browser default is:
 *   • mouse wheel — does not convert vertical scroll into horizontal,
 *   • click+drag — none (it produces text selection),
 *   • Mac trackpad — horizontal swipe works, but a Windows mouse cannot.
 *
 * This hook closes all three gaps with a single approach:
 *   1. Mouse/pen click+drag scrolling via the Pointer Events API.
 *      Touch events are **left completely alone** (if `pointerType === "touch"`
 *      the hook early-returns) — native mobile swipe is fully preserved.
 *   2. A wheel listener converts vertical scroll into `scrollLeft += deltaY`
 *      (only if the container is scrollable and deltaX is smaller than deltaY).
 *      The Mac trackpad horizontal swipe (deltaX > deltaY) is left as-is.
 *   3. The accidental `click` event at the end of a drag does not reach child
 *      elements (such as ProductCard) — if a 4px+ shift happened, we apply
 *      `stopPropagation + preventDefault` in the capture phase. A plain click
 *      does not break anything.
 *
 * **Protecting interactive child elements**:
 *  • We do **not** call `setPointerCapture` on the parent **immediately** —
 *    that would "swallow" pointer events from heart buttons, links and other
 *    interactive child elements, and their click handlers would stop working.
 *  • Capture is attached only when a real drag actually starts (4px+ shift),
 *    and `userSelect: none` is set at the same moment.
 *  • If pointerdown lands on an interactive element (button, a, input,
 *    [role="button"]) — drag detection does not even start.
 *
 * Cursor:
 *   • idle  → `grab`
 *   • drag  → `grabbing`
 *   • touch → not modified
 *
 * @returns {(node: HTMLElement | null) => void} Callback ref to attach to the
 *   container. We use a callback ref instead of the standard `useRef` —
 *   when the element changes during conditional rendering, the effect
 *   re-binds automatically.
 */

const INTERACTIVE_SELECTOR =
  'button, a, input, select, textarea, label, [role="button"], [role="link"], [role="checkbox"], [role="tab"]';

export function useDragToScroll() {
  const [el, setEl] = useState(null);
  const setRef = useCallback((node) => {
    setEl(node ?? null);
  }, []);

  useEffect(() => {
    if (!el) return undefined;

    let isTracking = false;
    let isDragging = false;
    let startX = 0;
    let startScrollLeft = 0;
    let activePointerId = -1;
    let movedFar = false;

    const onPointerDown = (e) => {
      // On touch we disable the hook — native swipe is preserved.
      if (e.pointerType === 'touch') return;
      // Only the primary button (mouse left button = 0)
      if (e.button !== 0 && e.pointerType === 'mouse') return;
      // The press landed on an interactive child element — do not start drag.
      // Otherwise the click event would not reach the button.
      if (e.target?.closest?.(INTERACTIVE_SELECTOR)) return;

      isTracking = true;
      isDragging = false;
      movedFar = false;
      startX = e.clientX;
      startScrollLeft = el.scrollLeft;
      activePointerId = e.pointerId;
      // ❗ setPointerCapture is not called here — attaching it immediately would
      // break clicks on child interactive elements. We only attach it once a drag starts.
    };

    const onPointerMove = (e) => {
      if (!isTracking || e.pointerId !== activePointerId) return;
      const dx = e.clientX - startX;
      if (!movedFar && Math.abs(dx) > 4) {
        // A real drag has started — now attach capture and disable text selection.
        movedFar = true;
        isDragging = true;
        try {
          el.setPointerCapture?.(e.pointerId);
        } catch {
          // ignore — in some browsers capture is already held by another element
        }
        el.style.cursor = 'grabbing';
        el.style.userSelect = 'none';
      }
      if (isDragging) {
        el.scrollLeft = startScrollLeft - dx;
      }
    };

    const endDrag = (e) => {
      if (!isTracking) return;
      if (e && e.pointerId !== activePointerId) return;
      isTracking = false;
      const wasDragging = isDragging;
      isDragging = false;
      activePointerId = -1;
      if (wasDragging) {
        try {
          el.releasePointerCapture?.(e.pointerId);
        } catch {
          // pointer already released — ignore
        }
        el.style.cursor = 'grab';
        el.style.userSelect = '';
      }
    };

    // Block the click at the end of a drag — if a 4px+ shift occurred.
    // Capture phase = does not reach child elements (heart button, ProductCard).
    // A plain click (movedFar=false) does not break anything.
    const onClickCapture = (e) => {
      if (movedFar) {
        e.stopPropagation();
        e.preventDefault();
        movedFar = false;
      }
    };

    const onWheel = (e) => {
      const canScrollH = el.scrollWidth > el.clientWidth + 1;
      if (!canScrollH) return;
      // Mac trackpad horizontal swipe (deltaX dominant) — works on its own.
      // We only proxy the vertical wheel.
      if (Math.abs(e.deltaX) >= Math.abs(e.deltaY)) return;
      if (e.deltaY === 0) return;
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    };

    el.addEventListener('pointerdown', onPointerDown);
    el.addEventListener('pointermove', onPointerMove);
    el.addEventListener('pointerup', endDrag);
    el.addEventListener('pointercancel', endDrag);
    el.addEventListener('pointerleave', endDrag);
    el.addEventListener('click', onClickCapture, true);
    el.addEventListener('wheel', onWheel, { passive: false });

    // Grab cursor in idle — the user sees that the container is draggable.
    // The CSS cursor is invisible on mobile.
    el.style.cursor = 'grab';

    return () => {
      el.removeEventListener('pointerdown', onPointerDown);
      el.removeEventListener('pointermove', onPointerMove);
      el.removeEventListener('pointerup', endDrag);
      el.removeEventListener('pointercancel', endDrag);
      el.removeEventListener('pointerleave', endDrag);
      el.removeEventListener('click', onClickCapture, true);
      el.removeEventListener('wheel', onWheel);
      el.style.cursor = '';
      el.style.userSelect = '';
    };
  }, [el]);

  return setRef;
}
