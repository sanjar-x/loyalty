'use client';

import { OrdersList } from '@/entities/order';
import { OrderStatusModal } from '@/entities/order';
import { StatusTabs } from '@/features/order-filter';
import { TopMetrics } from '@/entities/order';
import { OrderFilters } from '@/features/order-filter';
import { ReasonFilters } from '@/features/order-filter';
import { useOrderFilters } from '@/features/order-filter';
import { getOrders } from '@/entities/order';

export default function OrdersPage() {
  const {
    activeStatus,
    setActiveStatus,
    searchValue,
    setSearchValue,
    sortBy,
    setSortBy,
    reasonFilter,
    setReasonFilter,
    dateRange,
    setDateRange,
    loading,
    selectedOrder,
    isReasonMode,
    isTransitMode,
    dateFilteredOrders,
    statusCounts,
    activeStatusOrders,
    reasonCounts,
    filteredOrders,
    handleOpenStatusModal,
    handleCloseStatusModal,
    handleSaveStatusModal,
    resetFilters,
  } = useOrderFilters(getOrders());

  return (
    <section className="animate-fadeIn">
      <h1 className="text-app-text-dark mb-6 text-[40px] leading-[44px] font-bold tracking-[-1px]">
        Заказы
      </h1>

      <TopMetrics
        orders={dateFilteredOrders}
        range={dateRange}
        onRangeChange={setDateRange}
      />

      <div className="mt-6">
        <StatusTabs
          activeStatus={activeStatus}
          counts={statusCounts}
          onChange={setActiveStatus}
        />
      </div>

      {isReasonMode ? (
        <ReasonFilters
          reasonFilter={reasonFilter}
          reasonCounts={reasonCounts}
          onReasonChange={setReasonFilter}
        />
      ) : (
        <OrderFilters
          searchValue={searchValue}
          onSearchChange={setSearchValue}
          sortBy={sortBy}
          onSortChange={setSortBy}
          isTransitMode={isTransitMode}
          activeStatusCount={activeStatusOrders.length}
          onReset={resetFilters}
        />
      )}

      <OrdersList
        orders={filteredOrders}
        loading={loading}
        onOpenStatusModal={handleOpenStatusModal}
      />

      <OrderStatusModal
        open={Boolean(selectedOrder)}
        order={selectedOrder}
        onClose={handleCloseStatusModal}
        onSave={handleSaveStatusModal}
      />
    </section>
  );
}
