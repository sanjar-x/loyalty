'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRef } from 'react';
import { cn, formatCurrency, formatDateTime } from '@/shared/lib/utils';
import { PRODUCT_STATUS_TRANSITIONS } from '@/entities/product';
import DotsIcon from '@/assets/icons/dots.svg';
import PencilIcon from '@/assets/icons/pencil.svg';
import { useOutsideClick } from '@/shared/hooks/useOutsideClick';
import styles from './products.module.css';

function RowActions({
  productId,
  status,
  open,
  onToggle,
  onStatusChange,
  onRequestArchive,
  onRequestDelete,
  onClose,
}) {
  const rootRef = useRef(null);
  useOutsideClick({ open, onClose, ref: rootRef });

  const transitions = PRODUCT_STATUS_TRANSITIONS[status] || [];

  return (
    <div className={styles.rowMenu} ref={rootRef}>
      <button
        type="button"
        className={styles.iconButton}
        aria-label="Меню"
        onClick={onToggle}
      >
        <DotsIcon className={styles.icon24} />
      </button>

      {open && (
        <div className={styles.rowMenuPanel}>
          <Link
            href={`/admin/products/${productId}/edit`}
            className={styles.rowMenuItem}
            onClick={onClose}
          >
            Редактировать
          </Link>
          {transitions.map((t) => (
            <button
              key={t.target}
              type="button"
              onClick={() => {
                if (t.target === 'archived') {
                  onRequestArchive();
                } else {
                  onStatusChange(t.target);
                }
                onClose();
              }}
              className={styles.rowMenuItem}
            >
              {t.label}
            </button>
          ))}
          {status !== 'published' && (
            <button
              type="button"
              onClick={() => {
                onRequestDelete();
                onClose();
              }}
              className={cn(styles.rowMenuItem, styles.rowMenuItemDanger)}
            >
              Удалить
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ProductImage({ src, alt }) {
  if (!src) {
    return (
      <div className={cn(styles.thumb, styles.thumbPlaceholder)}>
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <rect
            x="3"
            y="3"
            width="18"
            height="18"
            rx="3"
            stroke="#ccc"
            strokeWidth="1.5"
          />
          <circle cx="8.5" cy="8.5" r="1.5" fill="#ccc" />
          <path
            d="M3 16l5-5 4 4 3-3 6 6"
            stroke="#ccc"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    );
  }

  return (
    <div className={styles.thumb}>
      <Image
        src={src}
        alt={alt}
        width={120}
        height={120}
        className={styles.thumbImg}
      />
    </div>
  );
}

export function ProductRow({
  product: p,
  checked,
  openMenuId,
  onToggleSelection,
  onSetOpenMenuId,
  onStatusChange,
  onRequestArchive,
  onRequestDelete,
}) {
  const hasPrice = p.price != null;

  const toggleRowSelection = () => {
    onToggleSelection(p.id);
  };

  return (
    <div className={styles.row}>
      <div className={styles.productCell}>
        <div className={styles.thumbWrap}>
          <ProductImage src={p.image} alt={p.title} />

          <button
            type="button"
            onClick={toggleRowSelection}
            className={cn(
              styles.rowCheckBtn,
              checked ? styles.rowCheckBtnChecked : styles.rowCheckBtnIdle,
            )}
            aria-label="Выбрать"
          >
            <svg
              width="14"
              height="12"
              viewBox="0 0 14 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M0.707031 5.14014L5.20703 9.64014L12.707 0.640137"
                stroke="white"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        <div className={styles.productText}>
          <p className={styles.productTitle}>{p.title}</p>
          {p.brandName && <p className={styles.productBrand}>{p.brandName}</p>}
          {p.createdAt && (
            <p className={styles.productMeta}>{formatDateTime(p.createdAt)}</p>
          )}
          {p.variantAttrs?.length > 0 && (
            <div className={styles.variantAttrsWrap}>
              {p.variantAttrs.map((group) => (
                <div key={group.name} className={styles.variantAttrGroup}>
                  <span className={styles.variantAttrLabel}>{group.name}:</span>
                  {group.values.map((v) => (
                    <span key={v} className={styles.sizeBadge}>
                      {v}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className={styles.priceCell}>
        {hasPrice ? (
          <span className={styles.pricePill}>{formatCurrency(p.price)}</span>
        ) : (
          <span className={styles.priceMuted}>—</span>
        )}
      </div>

      <div className={styles.tagsCell}>
        <div className={styles.badges}>
          {p.supplierType === 'cross_border' && (
            <span className={cn(styles.badge, styles.badgeChina)}>
              {p.supplierCountry === 'CN'
                ? 'Из Китая'
                : `Импорт (${p.supplierCountry || '??'})`}
            </span>
          )}
          {p.supplierType === 'local' && (
            <span className={cn(styles.badge, styles.badgeStock)}>
              Из наличия
            </span>
          )}
          {p.supplierType === 'local' && (
            <span className={cn(styles.badge, styles.badgeDark)}>Оригинал</span>
          )}
        </div>
      </div>

      <div className={styles.actionsCell}>
        <div className={styles.actionsRow}>
          <Link
            href={`/admin/products/${p.id}/edit`}
            className={styles.iconButton}
            aria-label="Редактировать"
          >
            <PencilIcon className={styles.icon24} />
          </Link>
          <RowActions
            productId={p.id}
            status={p.status}
            open={openMenuId === p.id}
            onToggle={() =>
              onSetOpenMenuId((prev) => (prev === p.id ? null : p.id))
            }
            onClose={() => onSetOpenMenuId(null)}
            onStatusChange={(target) => onStatusChange(p.id, target)}
            onRequestArchive={() => onRequestArchive(p)}
            onRequestDelete={() => onRequestDelete(p)}
          />
        </div>
      </div>
    </div>
  );
}
