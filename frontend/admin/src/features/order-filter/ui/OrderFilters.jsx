import SearchIcon from '@/assets/icons/search.svg';
import { SortSelect } from '@/features/order-filter';

export function OrderFilters({
  searchValue,
  onSearchChange,
  sortBy,
  onSortChange,
  isTransitMode,
  activeStatusCount,
  onReset,
}) {
  const searchPlaceholder = isTransitMode ? '№' : 'Поиск по номеру заказа';

  return (
    <div className="my-4 flex flex-wrap items-center gap-3">
      <div className="bg-app-card flex h-[46px] w-full items-center gap-[10px] rounded-[50px] px-[13px] py-3 sm:w-[306px]">
        <SearchIcon className="h-5 w-5 shrink-0 text-[#1f1f1f]" />
        <input
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={searchPlaceholder}
          className="h-5 w-full bg-transparent p-0 text-base leading-5 font-medium tracking-normal text-[#000000] outline-none placeholder:text-[#000000]"
        />
      </div>

      {isTransitMode && (
        <button
          type="button"
          className="bg-app-text-dark inline-flex h-[46px] items-center gap-[10px] rounded-[50px] px-[13px] py-3 text-base leading-5 font-medium text-[#9e9e9e]"
        >
          <span className="text-[#f2f2f2]">
            <svg
              width="18"
              height="18"
              viewBox="0 0 18 18"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M9.01763 4.48623L0.805054 12.6987V16.8049L4.91134 16.8049L13.1239 8.59245M9.01763 4.48623L11.9625 1.54139L11.9643 1.53964C12.3696 1.13427 12.5727 0.931225 12.8067 0.855175C13.0129 0.788184 13.235 0.788184 13.4412 0.855175C13.6751 0.931171 13.8779 1.13398 14.2827 1.53878L16.0688 3.32478C16.4753 3.73132 16.6787 3.93468 16.7548 4.16907C16.8218 4.37525 16.8218 4.59734 16.7548 4.80352C16.6787 5.03774 16.4756 5.2408 16.0697 5.64675L16.0688 5.64762L13.1239 8.59245M9.01763 4.48623L13.1239 8.59245"
                stroke="#7E7E7E"
                strokeWidth="1.61"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span>{activeStatusCount}</span>
        </button>
      )}

      <SortSelect
        value={sortBy}
        onChange={onSortChange}
        variant={isTransitMode ? 'dark' : 'light'}
      />

      <button
        type="button"
        onClick={onReset}
        className="text-app-text-dark inline-flex h-[46px] items-center justify-center px-2 text-[36px] leading-none"
        aria-label="Сбросить фильтры"
      >
        <svg
          width="15"
          height="15"
          viewBox="0 0 15 15"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M1 1L7.5 7.5M14 14L7.5 7.5M7.5 7.5L13.5357 1M7.5 7.5L1 14"
            stroke="#2D2D2D"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  );
}
