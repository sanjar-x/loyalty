'use client';

import { useEffect, useRef } from 'react';

export function useOutsideClick({ open, onClose, ref }) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;

    function onDown(event) {
      const target = event.target;
      if (!ref.current) return;
      if (
        typeof Node !== 'undefined' &&
        target instanceof Node &&
        ref.current.contains(target)
      )
        return;
      onCloseRef.current();
    }

    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open, ref]);
}
