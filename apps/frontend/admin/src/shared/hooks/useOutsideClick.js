'use client';

import { useEffect, useRef } from 'react';

export function useOutsideClick({ open, onClose, ref }) {
  const onCloseRef = useRef(onClose);

  // Sync the latest onClose into the ref *after* render — never during render.
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return undefined;

    function handleMouseDown(event) {
      const target = event.target;
      if (!ref.current) return;
      if (
        typeof Node !== 'undefined' &&
        target instanceof Node &&
        ref.current.contains(target)
      ) {
        return;
      }
      onCloseRef.current?.();
    }

    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, [open, ref]);
}
