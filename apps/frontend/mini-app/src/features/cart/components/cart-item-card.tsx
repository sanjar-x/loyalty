"use client";

import { Minus, Plus, Trash2 } from "lucide-react";

import { ImgWithFallback } from "@/components/ui/img-with-fallback";
import { formatRub } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CartItem } from "@/types";

interface CartItemCardProps {
  item: CartItem;
  selected: boolean;
  onSelect: (id: string) => void;
  onQuantityChange: (id: string, quantity: number) => void;
  onRemove: (id: string) => void;
}

export function CartItemCard({
  item,
  selected,
  onSelect,
  onQuantityChange,
  onRemove,
}: CartItemCardProps) {
  return (
    <div className="flex gap-3 rounded-xl bg-[#f4f3f1] p-3">
      {/* Checkbox */}
      <button
        onClick={() => onSelect(item.id)}
        className={cn(
          "mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-colors",
          selected
            ? "border-black bg-black text-white"
            : "border-gray-300 bg-white",
        )}
        aria-label={selected ? "Убрать из выбранных" : "Выбрать"}
      >
        {selected && (
          <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none">
            <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </button>

      {/* Image */}
      <div className="h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-white">
        <ImgWithFallback
          sources={item.image ? [item.image] : []}
          className="h-full w-full object-contain"
          alt={item.name ?? "Product"}
        />
      </div>

      {/* Details */}
      <div className="flex min-w-0 flex-1 flex-col justify-between">
        <div>
          {item.brand && (
            <p className="text-[10px] font-medium text-muted-foreground">{item.brand}</p>
          )}
          <p className="line-clamp-2 text-xs font-medium">{item.name}</p>
          {item.size && (
            <p className="mt-0.5 text-[10px] text-muted-foreground">Размер: {item.size}</p>
          )}
        </div>

        <div className="mt-2 flex items-center justify-between">
          <span className="text-sm font-bold">{formatRub(item.price * item.quantity)}</span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onRemove(item.id)}
              className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground hover:bg-white"
              aria-label="Удалить"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>

            <div className="flex items-center gap-1 rounded-full bg-white px-1">
              <button
                onClick={() => onQuantityChange(item.id, Math.max(1, item.quantity - 1))}
                disabled={item.quantity <= 1}
                className="flex h-6 w-6 items-center justify-center rounded-full disabled:opacity-30"
                aria-label="Уменьшить"
              >
                <Minus className="h-3 w-3" />
              </button>
              <span className="min-w-[20px] text-center text-xs font-medium">{item.quantity}</span>
              <button
                onClick={() => onQuantityChange(item.id, item.quantity + 1)}
                className="flex h-6 w-6 items-center justify-center rounded-full"
                aria-label="Увеличить"
              >
                <Plus className="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
