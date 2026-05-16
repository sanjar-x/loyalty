'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Desktop-friendly drag-to-scroll + wheel proxy hook.
 *
 * Mobil/touch muhitda gorizontal `overflow-x: auto` container'lari native
 * swipe orqali ishlaydi. Desktop'da esa default brauzer'da:
 *   • mouse wheel — vertical scroll'ni horizontal'ga konvertatsiya qilmaydi,
 *   • klik+drag — yo'q (text selection bo'ladi),
 *   • Mac trackpad — horizontal swipe ishlaydi, lekin Windows mouse'da yo'q.
 *
 * Ushbu hook bitta yondashuv bilan uchchala kamchilikni yopadi:
 *   1. Pointer Events API orqali mouse/pen klik+drag scrolling.
 *      Touch event'lar **butunlay tegmaydi** (`pointerType === "touch"` bo'lsa
 *      hook early-return qiladi) — native mobile swipe to'liq saqlanadi.
 *   2. Wheel listener vertical scroll'ni `scrollLeft += deltaY` ga aylantiradi
 *      (faqat container scrollable bo'lsa va deltaX deltaY'dan kichik bo'lsa).
 *      Mac trackpad horizontal swipe'i (deltaX > deltaY) o'zgartirilmaydi.
 *   3. Drag oxirida tasodifiy `click` event'i bola elementlarga (ProductCard
 *      kabi) tushmaydi — 4px+ siljish ro'y bersa, capture phase'da
 *      `stopPropagation + preventDefault`. Oddiy bosish hech narsani buzmaydi.
 *
 * **Interaktiv child elementlarni himoyalash**:
 *  • Pointer'ni `setPointerCapture` bilan **darhol parent'ga olmaymiz** —
 *    bu pointer event'larni heart button, link va boshqa interaktiv child
 *    elementlardan "yutib yuboradi" va child click handlerlar ishlamaydi.
 *  • Capture faqat haqiqatdan ham drag boshlanganda (4px+ siljish) ulanadi
 *    va `userSelect: none` shu paytda qo'yiladi.
 *  • PointerDown interaktiv element ustida bo'lsa (button, a, input,
 *    [role="button"]) — drag-detection umuman boshlanmaydi.
 *
 * Cursor:
 *   • idle  → `grab`
 *   • drag  → `grabbing`
 *   • touch → o'zgartirilmaydi
 *
 * @returns {(node: HTMLElement | null) => void} Container'ga ulash uchun
 *   callback-ref. Standart `useRef` o'rniga callback ref ishlatamiz —
 *   conditional rendering paytida element o'zgarsa, effect avtomatik qayta
 *   bog'lanadi.
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
      // Touch'da hookni o'chirib qo'yamiz — native swipe saqlanadi.
      if (e.pointerType === 'touch') return;
      // Faqat asosiy tugma (mouse left button = 0)
      if (e.button !== 0 && e.pointerType === 'mouse') return;
      // Interaktiv child element ustida bosildi — drag boshlamaymiz.
      // Aks holda click event button'ga yetib bormaydi.
      if (e.target?.closest?.(INTERACTIVE_SELECTOR)) return;

      isTracking = true;
      isDragging = false;
      movedFar = false;
      startX = e.clientX;
      startScrollLeft = el.scrollLeft;
      activePointerId = e.pointerId;
      // ❗ setPointerCapture bu yerda chaqirilmaydi — agar darhol ulasak,
      // child interaktiv elementlardagi click ishlamaydi. Faqat drag boshlanganda.
    };

    const onPointerMove = (e) => {
      if (!isTracking || e.pointerId !== activePointerId) return;
      const dx = e.clientX - startX;
      if (!movedFar && Math.abs(dx) > 4) {
        // Real drag boshlandi — endi capture qo'yamiz va text selection o'chiramiz.
        movedFar = true;
        isDragging = true;
        try {
          el.setPointerCapture?.(e.pointerId);
        } catch {
          // ignore — ba'zi brauzerlarda capture allaqachon boshqa element bilan
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
          // pointer allaqachon release qilingan — ignore
        }
        el.style.cursor = 'grab';
        el.style.userSelect = '';
      }
    };

    // Drag oxirida click'ni bloklash — 4px+ siljish ro'y bergan bo'lsa.
    // Capture phase = bola elementlarga (heart button, ProductCard) yetib
    // bormaydi. Oddiy bosish (movedFar=false) hech narsani buzmaydi.
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
      // Mac trackpad horizontal swipe (deltaX dominant) — o'zicha ishlaydi.
      // Faqat vertical wheel'ni proxy qilamiz.
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

    // Idle holatda grab kursori — foydalanuvchi container drag qilinadigan
    // ekanini ko'radi. Mobile'da CSS cursor ko'rinmaydi.
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
