'use client';

import { useEffect, useId } from 'react';

export function Modal({ open, onClose, title, titleId: titleIdProp, children }) {
  const generatedId = useId();
  const titleId = titleIdProp || `modal-title-${generatedId}`;
  useEffect(() => {
    if (!open) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-90 flex items-center justify-center p-4 bg-[rgba(17,17,17,0.38)]"
      role="presentation"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[460px] rounded-3xl bg-white p-6 shadow-[0_24px_60px_rgba(22,22,22,0.22)]"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        {title && (
          <p
            id={titleId}
            className="m-0 text-2xl font-bold leading-[30px] text-[#111111]"
          >
            {title}
          </p>
        )}
        {children}
      </div>
    </div>
  );
}
