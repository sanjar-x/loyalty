'use client';

import { useEffect, useRef, useState } from 'react';

import { normalizeSearchText } from './utils';

/**
 * Bosh sahifa qidiruv holati — query/focus/typed/submitted + 220ms debounce.
 * Audit #1: `app/page.jsx` god-komponentidan ajratildi.
 *
 * `commitSearch` (filtr state'iga ham yozadi → cross-cutting glue) sahifada
 * qoladi — bu hook faqat qidiruvning o'z holatini va debounce'ini egallaydi.
 *
 * @returns {{
 *   inputRef: import('react').RefObject<HTMLInputElement|null>,
 *   blurCloseTimerRef: import('react').MutableRefObject<number|null>,
 *   query: string, setQuery: (v: string) => void,
 *   submittedQuery: string, setSubmittedQuery: (v: string) => void,
 *   isFocused: boolean, setIsFocused: (v: boolean) => void,
 *   hasTyped: boolean, setHasTyped: (v: boolean) => void,
 *   debouncedQuery: string,
 *   isSearchActivated: boolean, setSearchActivated: (v: boolean) => void,
 *   showSuggestions: boolean,
 * }}
 */
export function useHomeSearch() {
  const inputRef = useRef(null);
  const blurCloseTimerRef = useRef(null);

  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [hasTyped, setHasTyped] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [isSearchActivated, setSearchActivated] = useState(false);

  const showSuggestions = isFocused && hasTyped && normalizeSearchText(query).length > 0;

  // Suggest debounce — foydalanuvchi yozayotganda 220ms kutib turadi.
  useEffect(() => {
    if (!showSuggestions) {
      setDebouncedQuery('');
      return;
    }
    const next = String(query || '');
    const t = window.setTimeout(() => setDebouncedQuery(next), 220);
    return () => window.clearTimeout(t);
  }, [query, showSuggestions]);

  return {
    inputRef,
    blurCloseTimerRef,
    query,
    setQuery,
    submittedQuery,
    setSubmittedQuery,
    isFocused,
    setIsFocused,
    hasTyped,
    setHasTyped,
    debouncedQuery,
    isSearchActivated,
    setSearchActivated,
    showSuggestions,
  };
}
