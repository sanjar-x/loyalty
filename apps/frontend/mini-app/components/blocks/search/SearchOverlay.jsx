'use client';
import { useMemo } from 'react';
import { Search, Trash2, X } from 'lucide-react';

import {
  useGetSearchHistoryQuery,
  useGetSearchSuggestionsQuery,
  useClearSearchHistoryMutation,
  useRemoveSearchHistoryItemMutation,
} from '@/lib/store/api';

import styles from './SearchOverlay.module.css';

function normalize(value) {
  return String(value || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();
}

function SuggestSkeleton() {
  const widths = [78, 64, 86, 58, 72, 90];
  return (
    <div className={styles.skelSuggestList} aria-hidden="true">
      {widths.map((w, idx) => (
        <div key={idx} className={styles.skelSuggestItem}>
          <span className={styles.skelSuggestIcon} />
          <span className={styles.skelSuggestLine} style={{ width: `${w}%` }} />
        </div>
      ))}
    </div>
  );
}

function RecentSkeleton() {
  const widths = [92, 70, 84, 60, 78, 66];
  return (
    <div className={styles.skelChips} aria-hidden="true">
      {widths.map((w, idx) => (
        <span key={idx} className={styles.skelChip} style={{ width: `${w}px` }} />
      ))}
    </div>
  );
}

function renderSuggestionLabel(label, query) {
  const q = normalize(query);
  const hay = label;
  const hayLower = hay.toLowerCase();
  const idx = q ? hayLower.indexOf(q) : -1;
  if (idx < 0 || !q) return <span className={styles.suggestText}>{label}</span>;

  const before = hay.slice(0, idx);
  const match = hay.slice(idx, idx + q.length);
  const after = hay.slice(idx + q.length);

  return (
    <span className={styles.suggestText}>
      {before}
      <span className={styles.suggestStrong}>{match}</span>
      <span className={styles.suggestRest}>{after}</span>
    </span>
  );
}

export default function SearchOverlay({
  query,
  debouncedQuery,
  showSuggestions,
  onSelectSuggestion,
  onBackdropClick,
}) {
  const {
    data: searchHistoryRaw,
    isLoading: isHistoryLoading,
    isFetching: isHistoryFetching,
  } = useGetSearchHistoryQuery(undefined, {
    skip: normalize(query).length > 0,
    refetchOnFocus: false,
    refetchOnReconnect: false,
  });

  const [clearSearchHistory] = useClearSearchHistoryMutation();
  const [removeSearchHistoryItem] = useRemoveSearchHistoryItemMutation();

  // Backend `q minLength: 2` (Spec §6) — 1 belgili so'rov 422 beradi.
  // RTKQ darajasida ham, bu yerda ham guard.
  const trimmedQ = normalize(debouncedQuery);
  const {
    data: suggestRaw,
    isLoading: isSuggestLoading,
    isFetching: isSuggestFetching,
  } = useGetSearchSuggestionsQuery(debouncedQuery, {
    skip: !showSuggestions || trimmedQ.length < 2,
    refetchOnFocus: false,
    refetchOnReconnect: false,
  });

  // History entry'lari `lib/search/history.js`'da searchedAt DESC bo'yicha
  // qaytariladi va dedup-prune qilingan. UI faqat 12 tasini ko'rsatadi.
  const recent = useMemo(() => {
    const rows = Array.isArray(searchHistoryRaw) ? searchHistoryRaw : [];
    const out = [];
    for (const it of rows) {
      const label = String(it?.query ?? '').trim();
      if (!label) continue;
      out.push(label);
      if (out.length >= 12) break;
    }
    return out;
  }, [searchHistoryRaw]);

  const suggestions = useMemo(() => {
    if (!Array.isArray(suggestRaw)) return [];
    return suggestRaw
      .map((x) => String(x || '').trim())
      .filter(Boolean)
      .slice(0, 12);
  }, [suggestRaw]);

  const showSuggestSkeleton =
    showSuggestions && (isSuggestLoading || isSuggestFetching) && suggestions.length === 0;

  // Skeleton — faqat birinchi mount paytida ko'rinadi (localStorage o'qishi
  // sinxron, lekin RTKQ initial fetch tsikli bir tick olib boradi).
  const showRecentSkeleton =
    !query && (isHistoryLoading || isHistoryFetching) && recent.length === 0;

  let content = null;

  if (showSuggestions) {
    content = (
      <div
        className={styles.suggestList}
        role="listbox"
        aria-label="Подсказки"
        aria-busy={showSuggestSkeleton ? 'true' : 'false'}
      >
        {showSuggestSkeleton ? (
          <SuggestSkeleton />
        ) : (
          suggestions.map((label) => (
            <button
              key={label}
              type="button"
              className={styles.suggestItem}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onSelectSuggestion?.(label)}
              role="option"
              aria-selected="false"
            >
              <span className={styles.suggestIconWrap}>
                <Search size={18} className={styles.suggestItemIcon} aria-hidden="true" />
              </span>
              {renderSuggestionLabel(label, query)}
            </button>
          ))
        )}
      </div>
    );
  } else if (!query && (showRecentSkeleton || recent.length > 0)) {
    content = (
      <section className={styles.recent} aria-label="Вы искали">
        <div className={styles.recentHeader}>
          <div className={styles.recentTitle}>Вы искали</div>
          <button
            type="button"
            className={styles.trashBtn}
            aria-label="Очистить историю"
            onClick={() => clearSearchHistory()}
          >
            <Trash2 size={18} aria-hidden="true" />
          </button>
        </div>
        <div className={styles.chips}>
          {showRecentSkeleton ? (
            <RecentSkeleton />
          ) : (
            recent.map((label, idx) => (
              <span key={`${label}-${idx}`} className={styles.chipWrap}>
                <button
                  type="button"
                  className={styles.chip}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => onSelectSuggestion?.(label)}
                >
                  {label}
                </button>
                <button
                  type="button"
                  className={styles.chipRemoveBtn}
                  aria-label={`Удалить «${label}» из истории`}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={(e) => {
                    e.stopPropagation();
                    removeSearchHistoryItem(label);
                  }}
                >
                  <X size={12} aria-hidden="true" />
                </button>
              </span>
            ))
          )}
        </div>
      </section>
    );
  }

  if (!content) return null;

  return (
    <>
      <div className={styles.backdrop} onMouseDown={() => onBackdropClick?.()} />
      <div className={styles.content}>{content}</div>
    </>
  );
}
