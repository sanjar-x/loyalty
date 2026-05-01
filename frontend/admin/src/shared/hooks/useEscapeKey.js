'use client';

import { useEffect, useRef } from 'react';

/**
 * Calls `onEscape` whenever the Escape key is pressed while `active` is true.
 * The handler is read from a ref so callers can pass an inline function
 * without forcing the listener to re-attach on every render.
 */
export function useEscapeKey(onEscape, active = true) {
  const handlerRef = useRef(onEscape);

  useEffect(() => {
    handlerRef.current = onEscape;
  }, [onEscape]);

  useEffect(() => {
    if (!active) return undefined;

    function onKeyDown(event) {
      if (event.key === 'Escape') handlerRef.current?.(event);
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [active]);
}
