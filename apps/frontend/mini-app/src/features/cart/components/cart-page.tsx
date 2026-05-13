"use client";

import { useCallback } from "react";

import Link from "next/link";

import { ShoppingCart } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { useCartStore } from "@/stores/cart-store";

import { useCart } from "../hooks/use-cart";

import { CartItemCard } from "./cart-item-card";

export function CartPage() {
  const {
    items,
    totalQuantity,
    formattedSubtotal,
    isLoading,
    updateQuantity,
    removeItem,
  } = useCart();

  const { selectedItemIds, toggleItemSelection, selectAll, deselectAll } = useCartStore();

  const allSelected = items.length > 0 && items.every((i) => selectedItemIds.has(i.id));

  const handleToggleAll = useCallback(() => {
    if (allSelected) {
      deselectAll();
    } else {
      selectAll(items.map((i) => i.id));
    }
  }, [allSelected, items, selectAll, deselectAll]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-32" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
        <ShoppingCart className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-lg font-semibold">Корзина пуста</h2>
        <p className="text-sm text-muted-foreground">
          Добавьте товары из каталога
        </p>
        <Link
          href="/catalog"
          className="rounded-full bg-black px-6 py-2.5 text-sm font-medium text-white"
        >
          Перейти в каталог
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Корзина ({totalQuantity})</h1>
        <button
          onClick={handleToggleAll}
          className="text-sm text-muted-foreground"
        >
          {allSelected ? "Снять всё" : "Выбрать всё"}
        </button>
      </div>

      {/* Items */}
      <div className="space-y-2">
        {items.map((item) => (
          <CartItemCard
            key={item.id}
            item={item}
            selected={selectedItemIds.has(item.id)}
            onSelect={toggleItemSelection}
            onQuantityChange={updateQuantity}
            onRemove={removeItem}
          />
        ))}
      </div>

      {/* Sticky bottom bar */}
      <div className="fixed bottom-16 left-0 right-0 z-30 mx-auto w-full max-w-[440px] border-t border-border bg-white px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">Итого</p>
            <p className="text-lg font-bold">{formattedSubtotal}</p>
          </div>
          <Link
            href="/checkout"
            className="rounded-full bg-black px-8 py-3 text-sm font-semibold text-white"
          >
            К оформлению
          </Link>
        </div>
      </div>
    </div>
  );
}
