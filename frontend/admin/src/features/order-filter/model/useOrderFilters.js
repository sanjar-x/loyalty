'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import dayjs from '@/shared/lib/dayjs';
import { resolveOrderStatus } from '@/entities/order';

const initialRange = {
  from: null,
  to: null,
};

export function useOrderFilters(initialOrders) {
  const [activeStatus, setActiveStatus] = useState('placed');
  const [searchValue, setSearchValue] = useState('');
  const [sortBy, setSortBy] = useState('newest');
  const [reasonFilter, setReasonFilter] = useState('all');
  const [dateRange, setDateRange] = useState(initialRange);
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState(initialOrders);
  const [selectedOrder, setSelectedOrder] = useState(null);

  const isReasonMode =
    activeStatus === 'canceled' || activeStatus === 'received';
  const isTransitMode = activeStatus === 'in_transit';

  // ── derived data ──────────────────────────────────────────────

  const dateFilteredOrders = useMemo(() => {
    if (!dateRange.from && !dateRange.to) {
      return orders;
    }

    return orders.filter((order) => {
      const orderDate = dayjs(order.createdAt);

      if (dateRange.from && dateRange.to) {
        return (
          orderDate.isSameOrAfter(dateRange.from.startOf('day')) &&
          orderDate.isSameOrBefore(dateRange.to.endOf('day'))
        );
      }

      if (dateRange.from) {
        return orderDate.isSame(dateRange.from, 'day');
      }

      return true;
    });
  }, [dateRange.from, dateRange.to, orders]);

  const statusCounts = useMemo(
    () => ({
      placed: dateFilteredOrders.filter((order) => order.status === 'placed')
        .length,
      in_transit: dateFilteredOrders.filter(
        (order) => order.status === 'in_transit',
      ).length,
      pickup_point: dateFilteredOrders.filter(
        (order) => order.status === 'pickup_point',
      ).length,
      canceled: dateFilteredOrders.filter(
        (order) => order.status === 'canceled',
      ).length,
      received: dateFilteredOrders.filter(
        (order) => order.status === 'received',
      ).length,
    }),
    [dateFilteredOrders],
  );

  const activeStatusOrders = useMemo(
    () => dateFilteredOrders.filter((order) => order.status === activeStatus),
    [dateFilteredOrders, activeStatus],
  );

  const reasonCounts = useMemo(() => {
    const base = {
      not_for_sale: 0,
      release_refusal: 0,
      storage_expired: 0,
    };

    activeStatusOrders.forEach((order) => {
      if (order.reasonFilter) {
        base[order.reasonFilter] += 1;
      }
    });

    return base;
  }, [activeStatusOrders]);

  const filteredOrders = useMemo(() => {
    let next = [...activeStatusOrders];

    if (isReasonMode) {
      if (reasonFilter !== 'all') {
        next = next.filter((order) => order.reasonFilter === reasonFilter);
      }
    } else {
      next = next.filter((order) =>
        order.orderNumber
          .toLowerCase()
          .includes(searchValue.trim().toLowerCase()),
      );
    }

    return next.sort((a, b) => {
      const left = dayjs(a.createdAt).valueOf();
      const right = dayjs(b.createdAt).valueOf();

      if (isReasonMode) {
        return right - left;
      }

      return sortBy === 'newest' ? right - left : left - right;
    });
  }, [activeStatusOrders, isReasonMode, reasonFilter, searchValue, sortBy]);

  // ── effects ───────────────────────────────────────────────────

  useEffect(() => {
    setSearchValue('');
    setReasonFilter('all');
    setSortBy(isTransitMode ? 'oldest' : 'newest');
  }, [activeStatus, isTransitMode]);

  // Extract primitive timestamps so the dependency array stays statically analysable.
  const fromTs = dateRange.from?.valueOf() ?? null;
  const toTs = dateRange.to?.valueOf() ?? null;

  useEffect(() => {
    setLoading(true);
    const timeout = setTimeout(() => setLoading(false), 380);

    return () => clearTimeout(timeout);
  }, [activeStatus, reasonFilter, searchValue, sortBy, fromTs, toTs]);

  // ── actions ───────────────────────────────────────────────────

  const handleOpenStatusModal = useCallback((order) => {
    setSelectedOrder(order);
  }, []);

  const handleCloseStatusModal = useCallback(() => {
    setSelectedOrder(null);
  }, []);

  const handleSaveStatusModal = useCallback(({ orderId, itemStatuses }) => {
    const nextStatuses = Object.values(itemStatuses);
    setOrders((prev) =>
      prev.map((order) => {
        if (order.id !== orderId) {
          return order;
        }

        return {
          ...order,
          status: resolveOrderStatus(order.status, nextStatuses),
        };
      }),
    );
  }, []);

  const resetFilters = useCallback(() => {
    setSearchValue('');
    setSortBy(isTransitMode ? 'oldest' : 'newest');
  }, [isTransitMode]);

  return {
    // state
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

    // derived
    isReasonMode,
    isTransitMode,
    dateFilteredOrders,
    statusCounts,
    activeStatusOrders,
    reasonCounts,
    filteredOrders,

    // actions
    handleOpenStatusModal,
    handleCloseStatusModal,
    handleSaveStatusModal,
    resetFilters,
  };
}
