'use client';

import { OrdersList } from '@/components/admin/OrdersList';
import { OrderStatusModal } from '@/components/admin/OrderStatusModal';
import { StatusTabs } from '@/components/admin/StatusTabs';
import { TopMetrics } from '@/components/admin/TopMetrics';
import { OrderFilters } from '@/components/admin/orders/OrderFilters';
import { ReasonFilters } from '@/components/admin/orders/ReasonFilters';
import { useOrderFilters } from '@/hooks/useOrderFilters';
import { getOrders } from '@/services/orders';

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
      <h1 className="mb-6 text-[40px] leading-[44px] font-bold tracking-[-1px] text-[#2d2d2d]">
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
