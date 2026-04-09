'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRef } from 'react';
import { cn, formatCurrency, pluralizeRu } from '@/lib/utils';
import { CopyMark } from '@/components/ui/CopyMark';
import EyeIcon from '@/assets/icons/eye.svg';
import BagIcon from '@/assets/icons/bag.svg';
import DotsIcon from '@/assets/icons/dots.svg';
import PencilIcon from '@/assets/icons/pencil.svg';
import VariantsIcon from '@/assets/icons/variants.svg';
import { useOutsideClick } from '@/hooks/useOutsideClick';
import styles from './products.module.css';

/* CopyMark imported from @/components/ui/CopyMark */

function RowActions({ open, onToggle, onArchive, onClose }) {
  const rootRef = useRef(null);
  useOutsideClick({ open, onClose, ref: rootRef });

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
          <button
            type="button"
            onClick={() => {
              onArchive();
              onClose();
            }}
            className={styles.rowMenuItem}
          >
            В архив
          </button>
        </div>
      )}
    </div>
  );
}

export function ProductRow({
  product: p,
  checked,
  selectMode,
  openMenuId,
  onToggleSelection,
  onSetOpenMenuId,
  onRequestArchive,
}) {
  const tagLabel = p.source === 'china' ? 'Из Китая' : 'Из наличия';
  const showOriginal = p.isOriginal;
  const viewDeltaSign = p.viewsDelta > 0 ? '+' : '';
  const orderDeltaSign = p.ordersDelta > 0 ? '+' : '';

  const toggleRowSelection = () => {
    onToggleSelection(p.id);
  };

  return (
    <div className={styles.row}>
      <div className={styles.productCell}>
        <div className={styles.thumbWrap}>
          <div className={styles.thumb}>
            <Image
              src={p.image}
              alt={p.title}
              width={120}
              height={120}
              className={styles.thumbImg}
            />
            {(p.imagesCount ?? 1) > 1 && (
              <div className={styles.thumbDots}>
                {Array.from({ length: Math.min(p.imagesCount ?? 1, 4) }, (_, i) => (
                  <span
                    key={i}
                    className={cn(styles.thumbDot, i === 0 && styles.thumbDotActive)}
                  />
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={toggleRowSelection}
            className={cn(
              styles.rowCheckBtn,
              checked && styles.rowCheckBtnChecked,
              !selectMode && styles.rowCheckBtnIdle,
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
          <p className={styles.productMeta}>
            Размеры: {p.sizes.join(', ')}
          </p>
          {(p.variantsCount ?? 1) > 1 && (
            <button type="button" className={styles.variantsLink}>
              <VariantsIcon className={styles.variantsIcon} />
              {p.variantsCount}{' '}
              {pluralizeRu(p.variantsCount, 'вариант', 'варианта', 'вариантов')}
            </button>
          )}
        </div>
      </div>

      <div className={styles.priceCell}>
        <span className={styles.pricePill}>
          {formatCurrency(p.price)}
        </span>
      </div>

      <div className={styles.skuCell}>
        <p className={styles.skuLine}>
          <span>{p.sku}</span>
          <CopyMark text={p.sku} />
        </p>
      </div>

      <div className={styles.tagsCell}>
        <div className={styles.badges}>
          <span
            className={cn(
              styles.badge,
              p.source === 'china'
                ? styles.badgeChina
                : styles.badgeStock,
            )}
          >
            {tagLabel}
          </span>
          {showOriginal && (
            <span className={cn(styles.badge, styles.badgeDark)}>
              Оригинал
            </span>
          )}
          {p.status === 'draft' && (
            <span className={styles.badge}>Черновик</span>
          )}
          {p.status === 'archived' && (
            <span className={cn(styles.badge, styles.badgeMuted)}>
              Архив
            </span>
          )}
        </div>
      </div>

      <div className={styles.statsCell}>
        <div className={styles.stats}>
          <span className={styles.stat}>
            <EyeIcon className={styles.statIcon} />

            <span>{p.views.toLocaleString('ru-RU')}</span>
            <span className={styles.statDelta}>
              {viewDeltaSign}
              {p.viewsDelta.toLocaleString('ru-RU')}
            </span>
          </span>
          <span className={styles.stat}>
            <BagIcon
              className={cn(styles.statIcon, styles.statIconBag)}
            />

            <span>{p.orders}</span>
            <span className={styles.statDelta}>
              {orderDeltaSign}
              {p.ordersDelta}
            </span>
          </span>
        </div>
      </div>

      <div className={styles.actionsCell}>
        <div className={styles.actionsRow}>
          <Link
            href={`/admin/products/${p.id}`}
            className={styles.iconButton}
            aria-label="Редактировать"
          >
            <PencilIcon className={styles.icon24} />
          </Link>
          <RowActions
            open={openMenuId === p.id}
            onToggle={() =>
              onSetOpenMenuId((prev) => (prev === p.id ? null : p.id))
            }
            onClose={() => onSetOpenMenuId(null)}
            onArchive={() => onRequestArchive(p)}
          />
        </div>
      </div>
    </div>
  );
}
