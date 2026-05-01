'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
} from 'react';

/**
 * Toast notification system.
 *
 * Wrap your layout with <ToastProvider> and use useToast() anywhere:
 *   const toast = useToast();
 *   toast.success('Продукт создан');
 *   toast.error('Не удалось загрузить');
 *   toast.warning('Частичная ошибка');
 *   toast.info('Загрузка...');
 */

const MAX_TOASTS = 5;

let _nextId = 0;

const DURATIONS = {
  success: 4000,
  error: 8000,
  warning: 6000,
  info: 4000,
};

const ToastContext = createContext(null);

function reducer(state, action) {
  switch (action.type) {
    case 'ADD': {
      const next = [...state, action.toast];
      // Keep only the latest MAX_TOASTS
      return next.length > MAX_TOASTS ? next.slice(-MAX_TOASTS) : next;
    }
    case 'DISMISS':
      return state.map((t) =>
        t.id === action.id ? { ...t, exiting: true } : t,
      );
    case 'REMOVE':
      return state.filter((t) => t.id !== action.id);
    default:
      return state;
  }
}

export function ToastProvider({ children }) {
  const [toasts, dispatch] = useReducer(reducer, []);

  const addToast = useCallback((type, message, options = {}) => {
    const id = ++_nextId;
    const duration = options.duration ?? DURATIONS[type] ?? 4000;

    dispatch({
      type: 'ADD',
      toast: { id, type, message, exiting: false },
    });

    if (duration > 0) {
      setTimeout(() => dispatch({ type: 'DISMISS', id }), duration);
      setTimeout(
        () => dispatch({ type: 'REMOVE', id }),
        duration + 300, // 300ms for exit animation
      );
    }

    return id;
  }, []);

  const dismiss = useCallback((id) => {
    dispatch({ type: 'DISMISS', id });
    setTimeout(() => dispatch({ type: 'REMOVE', id }), 300);
  }, []);

  const api = useMemo(
    () => ({
      success: (msg, opts) => addToast('success', msg, opts),
      error: (msg, opts) => addToast('error', msg, opts),
      warning: (msg, opts) => addToast('warning', msg, opts),
      info: (msg, opts) => addToast('info', msg, opts),
      dismiss,
    }),
    [addToast, dismiss],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>');
  return ctx;
}

// ── Toast UI ──

const ICONS = {
  success: (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="10" cy="10" r="10" fill="#16a34a" />
      <path
        d="M6 10.5L8.5 13L14 7"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  error: (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="10" cy="10" r="10" fill="#dc2626" />
      <path
        d="M7 7L13 13M13 7L7 13"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
  warning: (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="10" cy="10" r="10" fill="#ea580c" />
      <path d="M10 6V11" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
      <circle cx="10" cy="14" r="1" fill="#fff" />
    </svg>
  ),
  info: (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="10" cy="10" r="10" fill="#2563eb" />
      <circle cx="10" cy="6.5" r="1" fill="#fff" />
      <path
        d="M10 9.5V14.5"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
};

function ToastContainer({ toasts, onDismiss }) {
  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column-reverse',
        gap: 8,
        pointerEvents: 'none',
        maxWidth: 420,
        width: '100%',
      }}
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }) {
  const isError = toast.type === 'error' || toast.type === 'warning';

  return (
    <div
      role={isError ? 'alert' : 'status'}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        padding: '12px 16px',
        borderRadius: 12,
        background: '#fff',
        boxShadow: '0 4px 24px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08)',
        border: '1px solid #e5e1dc',
        pointerEvents: 'auto',
        animation: toast.exiting
          ? 'toastOut 0.3s ease forwards'
          : 'toastIn 0.3s ease',
        fontSize: 14,
        lineHeight: '20px',
        color: '#1a1a1a',
        maxWidth: 420,
      }}
    >
      <span style={{ flexShrink: 0, marginTop: 1 }}>{ICONS[toast.type]}</span>
      <span style={{ flex: 1, wordBreak: 'break-word' }}>{toast.message}</span>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Закрыть"
        style={{
          flexShrink: 0,
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 2,
          color: '#8c8c8c',
          fontSize: 18,
          lineHeight: 1,
        }}
      >
        ×
      </button>
      <style>{`
        @keyframes toastIn {
          from { opacity: 0; transform: translateX(40px) scale(0.95); }
          to   { opacity: 1; transform: translateX(0) scale(1); }
        }
        @keyframes toastOut {
          from { opacity: 1; transform: translateX(0) scale(1); }
          to   { opacity: 0; transform: translateX(40px) scale(0.95); }
        }
      `}</style>
    </div>
  );
}
