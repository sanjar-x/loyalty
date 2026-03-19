'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import BagIcon from '@/assets/icons/bag.svg';
import dayjs from '@/lib/dayjs';
import { promocodesSeed } from '@/data/promocodes';
import styles from './page.module.css';

function formatDiscount(discount) {
  if (!discount) return '';
  if (discount.type === 'percent') {
    return `-${discount.value}%`;
  }
  return `-${Number(discount.value || 0).toLocaleString('ru-RU')}₽`;
}

// TODO: StatsIcon is duplicated in staff/page.jsx — extract to shared component (e.g. @/components/icons/StatsIcon)
function StatsIcon() {
  return (
    <svg
      className={styles.actionIcon}
      viewBox="0 0 26 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M16.25 24.6457H9.74996C3.86746 24.6457 1.35413 22.1323 1.35413 16.2498V9.74984C1.35413 3.86734 3.86746 1.354 9.74996 1.354H16.25C22.1325 1.354 24.6458 3.86734 24.6458 9.74984V16.2498C24.6458 22.1323 22.1325 24.6457 16.25 24.6457ZM9.74996 2.979C4.75579 2.979 2.97913 4.75567 2.97913 9.74984V16.2498C2.97913 21.244 4.75579 23.0207 9.74996 23.0207H16.25C21.2441 23.0207 23.0208 21.244 23.0208 16.2498V9.74984C23.0208 4.75567 21.2441 2.979 16.25 2.979H9.74996Z"
        fill="#292D32"
      />
      <path
        d="M7.94079 16.51C7.76746 16.51 7.59413 16.4558 7.44246 16.3367C7.08496 16.0658 7.01996 15.5567 7.29079 15.1992L9.86912 11.8517C10.1833 11.4508 10.6275 11.1908 11.1366 11.1258C11.635 11.0608 12.1441 11.2017 12.545 11.5158L14.5275 13.0758C14.6033 13.1408 14.6791 13.1408 14.7333 13.13C14.7766 13.13 14.8525 13.1083 14.9175 13.0217L17.42 9.79334C17.6908 9.43584 18.2108 9.37084 18.5575 9.65251C18.915 9.92334 18.98 10.4325 18.6983 10.79L16.1958 14.0183C15.8816 14.4192 15.4375 14.6792 14.9283 14.7333C14.4191 14.7983 13.9208 14.6575 13.52 14.3433L11.5375 12.7833C11.4616 12.7183 11.375 12.7183 11.3316 12.7292C11.2883 12.7292 11.2125 12.7508 11.1475 12.8375L8.56913 16.185C8.42829 16.4017 8.18996 16.51 7.94079 16.51Z"
        fill="#292D32"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      className={styles.actionIcon}
      width="18"
      height="18"
      viewBox="0 0 17 19"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M10.1798 7.4158V14.0269M6.42981 7.4158V14.0269M2.67981 3.63802V14.7825C2.67981 15.8403 2.67981 16.3689 2.88417 16.773C3.06393 17.1284 3.35057 17.4179 3.70337 17.599C4.10406 17.8047 4.62887 17.8047 5.67691 17.8047H10.9327C11.9808 17.8047 12.5048 17.8047 12.9055 17.599C13.2583 17.4179 13.5459 17.1284 13.7256 16.773C13.9298 16.3693 13.9298 15.8412 13.9298 14.7854V3.63802M2.67981 3.63802H4.55481M2.67981 3.63802H0.80481M4.55481 3.63802H12.0548M4.55481 3.63802C4.55481 2.75791 4.55481 2.31807 4.69754 1.97095C4.88784 1.50812 5.25261 1.14018 5.71204 0.948471C6.05661 0.804688 6.49367 0.804688 7.36731 0.804688H9.24231C10.1159 0.804688 10.5528 0.804688 10.8973 0.948471C11.3568 1.14018 11.7217 1.50812 11.912 1.97095C12.0547 2.31807 12.0548 2.75791 12.0548 3.63802M12.0548 3.63802H13.9298M13.9298 3.63802H15.8048"
        stroke="currentColor"
        strokeWidth="1.60973"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function PromocodesPage() {
  const [items, setItems] = useState(promocodesSeed);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const codeRef = useRef(null);

  const [openSelect, setOpenSelect] = useState(null);

  const [formCode, setFormCode] = useState('');
  const [discountUnit, setDiscountUnit] = useState('%');
  const [discountValue, setDiscountValue] = useState(null);
  const [conditions, setConditions] = useState([]);
  const [expiresPreset, setExpiresPreset] = useState('none');

  const discountPresets = useMemo(() => {
    return discountUnit === '%' ? [5, 10, 15] : [250, 500, 750, 1500];
  }, [discountUnit]);

  const conditionOptions = useMemo(() => {
    return [
      { id: 'order', label: 'на заказ' },
      { id: 'clothes', label: 'на одежду' },
      { id: 'shoes', label: 'на обувь' },
      { id: 'accessories', label: 'на аксессуары' },
    ];
  }, []);

  const expiresOptions = useMemo(() => {
    return [
      { id: 'none', label: 'без срока', days: null },
      { id: '7d', label: '7 дней', days: 7 },
      { id: '14d', label: '14 дней', days: 14 },
      { id: '30d', label: '30 дней', days: 30 },
    ];
  }, []);

  const discountText = useMemo(() => {
    if (!discountValue) return '';
    const value =
      discountUnit === '₽'
        ? Number(discountValue).toLocaleString('ru-RU')
        : String(discountValue);
    return `-${value}${discountUnit}`;
  }, [discountUnit, discountValue]);

  const conditionText = useMemo(() => {
    if (!conditions.length) return '';
    const byId = new Map(conditionOptions.map((o) => [o.id, o.label]));
    return conditions
      .map((id) => byId.get(id))
      .filter(Boolean)
      .join(', ');
  }, [conditions, conditionOptions]);

  const expiresText = useMemo(() => {
    const opt = expiresOptions.find((o) => o.id === expiresPreset);
    if (!opt) return '';
    return opt.label;
  }, [expiresOptions, expiresPreset]);

  const toggleSelect = (name) => {
    setOpenSelect((prev) => (prev === name ? null : name));
  };

  const generateCode = () => {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    const length = 8;
    const randomValues = crypto.getRandomValues(new Uint32Array(length));
    let next = '';
    for (let i = 0; i < length; i += 1) {
      next += alphabet[randomValues[i] % alphabet.length];
    }
    setFormCode(next);
    codeRef.current?.focus();
  };

  const toggleCondition = (id) => {
    setConditions((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      return [...prev, id];
    });
  };

  const closeCreate = useCallback(() => {
    setIsCreateOpen(false);
    setOpenSelect(null);
    setFormCode('');
    setDiscountUnit('%');
    setDiscountValue(null);
    setConditions([]);
    setExpiresPreset('none');
  }, []);

  useEffect(() => {
    if (!isCreateOpen) return undefined;

    codeRef.current?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event) => {
      if (event.key === 'Escape') closeCreate();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [isCreateOpen, closeCreate]);

  const canSubmit = useMemo(() => {
    return Boolean(formCode.trim()) && Boolean(discountValue);
  }, [formCode, discountValue]);

  const handleCreate = () => {
    const discount = {
      type: discountUnit === '%' ? 'percent' : 'amount',
      value: Number(discountValue || 0),
    };

    const expiresOption = expiresOptions.find((o) => o.id === expiresPreset);
    let expiresAt = null;
    if (expiresOption?.days) {
      const date = new Date();
      date.setDate(date.getDate() + expiresOption.days);
      date.setHours(23, 59, 59, 999);
      expiresAt = date.toISOString();
    }

    setItems((prev) => [
      {
        id: `promo-${Date.now()}`,
        code: formCode.trim().toUpperCase(),
        discount,
        condition: conditionText || '—',
        expiresAt,
        uses: { value: 0, delta: 0 },
      },
      ...prev,
    ]);

    closeCreate();
  };

  return (
    <section>
      <header className={styles.header}>
        <h2 className={styles.headerTitle}>Промокоды</h2>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => setIsCreateOpen(true)}
        >
          Создать промокод
        </button>
      </header>

      {isCreateOpen ? (
        <div
          className={styles.modalOverlay}
          role="presentation"
          onClick={closeCreate}
        >
          <div
            className={styles.modalCard}
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-promo-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <h3 id="create-promo-title" className={styles.modalTitle}>
                Создание промокода
              </h3>
              <button
                type="button"
                className={styles.modalClose}
                onClick={closeCreate}
                aria-label="Закрыть"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    d="M5 5L15 15"
                    stroke="#111111"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                  <path
                    d="M15 5L5 15"
                    stroke="#111111"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>

            <form
              className={styles.modalBody}
              onMouseDown={() => setOpenSelect(null)}
              onSubmit={(e) => {
                e.preventDefault();
                if (!canSubmit) return;
                handleCreate();
              }}
            >
              <div
                className={styles.row}
                onMouseDown={(e) => e.stopPropagation()}
              >
                <div
                  className={`${styles.textField} ${
                    formCode ? styles.fieldFilled : ''
                  }`}
                >
                  <span className={styles.textLabel}>Промокод</span>
                  <input
                    ref={codeRef}
                    className={styles.textInput}
                    value={formCode}
                    onChange={(e) => setFormCode(e.target.value)}
                    placeholder=""
                    autoComplete="off"
                    spellCheck={false}
                  />
                </div>
                <button
                  type="button"
                  className={styles.sideButton}
                  onClick={generateCode}
                  aria-label="Сгенерировать промокод"
                >
                  <svg
                    width="23"
                    height="23"
                    viewBox="0 0 23 23"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M15.9372 3.56282L13.2855 6.21447M9.75 1V4.75V1ZM3.56282 3.56282L6.21447 6.21447L3.56282 3.56282ZM1 9.75H4.75H1ZM3.56282 15.9372L6.21447 13.2855L3.56282 15.9372ZM9.75 18.5V14.75V18.5ZM15.9372 15.9372L13.2855 13.2855L15.9372 15.9372ZM18.5 9.75H14.75H18.5Z"
                      stroke="black"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M13.5 13.5L21.5 21.5"
                      stroke="black"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>

              <div
                className={styles.row}
                onMouseDown={(e) => e.stopPropagation()}
              >
                <div className={styles.selectRoot}>
                  <button
                    type="button"
                    className={`${styles.selectField} ${
                      discountText ? styles.fieldFilled : ''
                    }`}
                    onClick={() => toggleSelect('discount')}
                    aria-expanded={openSelect === 'discount'}
                  >
                    <span className={styles.fieldLabel}>Скидка</span>
                    <span className={styles.fieldValue}>{discountText}</span>
                    <svg
                      className={`${styles.chevron} ${
                        openSelect === 'discount' ? styles.chevronOpen : ''
                      }`}
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M5 7.5L10 12.5L15 7.5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>

                  {openSelect === 'discount' ? (
                    <div
                      className={styles.dropdown}
                      role="listbox"
                      onMouseDown={(e) => e.stopPropagation()}
                    >
                      {discountPresets.map((v) => {
                        const text =
                          discountUnit === '₽'
                            ? `-${Number(v).toLocaleString('ru-RU')}₽`
                            : `-${v}%`;
                        const selected = discountValue === v;

                        return (
                          <button
                            key={`${discountUnit}-${v}`}
                            type="button"
                            className={`${styles.dropdownItem} ${
                              selected ? styles.dropdownItemSelected : ''
                            }`}
                            onClick={() => {
                              setDiscountValue(v);
                              setOpenSelect(null);
                            }}
                            role="option"
                            aria-selected={selected}
                          >
                            {text}
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>

                <div className={styles.unitRoot}>
                  <button
                    type="button"
                    className={styles.sideButton}
                    onClick={() => toggleSelect('unit')}
                    aria-expanded={openSelect === 'unit'}
                    aria-label="Единица скидки"
                  >
                    <span className={styles.unitValue}>{discountUnit}</span>
                    <svg
                      className={`${styles.chevronSmall} ${
                        openSelect === 'unit' ? styles.chevronOpenSmall : ''
                      }`}
                      width="18"
                      height="18"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M5 7.5L10 12.5L15 7.5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>

                  {openSelect === 'unit' ? (
                    <div
                      className={styles.dropdownSmall}
                      role="listbox"
                      onMouseDown={(e) => e.stopPropagation()}
                    >
                      {['%', '₽'].map((u) => {
                        const selected = discountUnit === u;
                        return (
                          <button
                            key={u}
                            type="button"
                            className={`${styles.dropdownItemSmall} ${
                              selected ? styles.dropdownItemSelected : ''
                            }`}
                            onClick={() => {
                              setDiscountUnit(u);
                              setDiscountValue(null);
                              setOpenSelect(null);
                            }}
                            role="option"
                            aria-selected={selected}
                          >
                            <span className={styles.unitOptionLeft}>{u}</span>
                            {selected ? (
                              <svg
                                className={styles.checkIcon}
                                width="18"
                                height="18"
                                viewBox="0 0 20 20"
                                fill="none"
                                xmlns="http://www.w3.org/2000/svg"
                                aria-hidden="true"
                              >
                                <path
                                  d="M4.5 10.5L8.4 14.2L15.5 6.8"
                                  stroke="currentColor"
                                  strokeWidth="1.8"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                />
                              </svg>
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              </div>

              <div
                className={styles.fullRow}
                onMouseDown={(e) => e.stopPropagation()}
              >
                <div className={styles.selectRootFull}>
                  <button
                    type="button"
                    className={`${styles.selectField} ${
                      conditionText ? styles.fieldFilled : ''
                    }`}
                    onClick={() => toggleSelect('condition')}
                    aria-expanded={openSelect === 'condition'}
                  >
                    <span className={styles.fieldLabel}>Условие</span>
                    <span className={styles.fieldValue}>{conditionText}</span>
                    <svg
                      className={`${styles.chevron} ${
                        openSelect === 'condition' ? styles.chevronOpen : ''
                      }`}
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M5 7.5L10 12.5L15 7.5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>

                  {openSelect === 'condition' ? (
                    <div
                      className={styles.dropdown}
                      role="listbox"
                      onMouseDown={(e) => e.stopPropagation()}
                    >
                      {conditionOptions.map((opt) => {
                        const checked = conditions.includes(opt.id);
                        return (
                          <button
                            key={opt.id}
                            type="button"
                            className={styles.dropdownItemCheckbox}
                            onClick={() => {
                              toggleCondition(opt.id);
                              setOpenSelect(null);
                            }}
                            role="option"
                            aria-selected={checked}
                          >
                            <span
                              className={`${styles.checkbox} ${
                                checked ? styles.checkboxChecked : ''
                              }`}
                              aria-hidden="true"
                            />
                            <span className={styles.optionLabel}>
                              {opt.label}
                            </span>
                            <svg
                              className={styles.optionChevron}
                              width="18"
                              height="18"
                              viewBox="0 0 20 20"
                              fill="none"
                              xmlns="http://www.w3.org/2000/svg"
                              aria-hidden="true"
                            >
                              <path
                                d="M7.5 5L12.5 10L7.5 15"
                                stroke="currentColor"
                                strokeWidth="1.8"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              </div>

              <div
                className={styles.fullRow}
                onMouseDown={(e) => e.stopPropagation()}
              >
                <div className={styles.selectRootFull}>
                  <button
                    type="button"
                    className={`${styles.selectField} ${
                      expiresText ? styles.fieldFilled : ''
                    }`}
                    onClick={() => toggleSelect('expires')}
                    aria-expanded={openSelect === 'expires'}
                  >
                    <span className={styles.fieldLabel}>Срок действия</span>
                    <span className={styles.fieldValue}>{expiresText}</span>
                    <svg
                      className={`${styles.chevron} ${
                        openSelect === 'expires' ? styles.chevronOpen : ''
                      }`}
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M5 7.5L10 12.5L15 7.5"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>

                  {openSelect === 'expires' ? (
                    <div
                      className={styles.dropdown}
                      role="listbox"
                      onMouseDown={(e) => e.stopPropagation()}
                    >
                      {expiresOptions.map((opt) => {
                        const selected = expiresPreset === opt.id;
                        return (
                          <button
                            key={opt.id}
                            type="button"
                            className={`${styles.dropdownItem} ${
                              selected ? styles.dropdownItemSelected : ''
                            }`}
                            onClick={() => {
                              setExpiresPreset(opt.id);
                              setOpenSelect(null);
                            }}
                            role="option"
                            aria-selected={selected}
                          >
                            {opt.label}
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className={styles.modalFooter}>
                <button
                  type="submit"
                  className={styles.modalSubmit}
                  disabled={!canSubmit}
                >
                  Создать промокод
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {!items.length ? (
        <div className={styles.empty}>
          <p className={styles.emptyTitle}>Промокоды не найдены</p>
          <p className={styles.emptyText}>Создайте первый промокод.</p>
        </div>
      ) : (
        <div className={styles.list}>
          {items.map((promo) => {
            const expiresLabel = promo.expiresAt
              ? `до ${dayjs(promo.expiresAt).format('DD.MM.YYYY')}`
              : 'без срока';

            return (
              <article key={promo.id} className={styles.card}>
                <div className={styles.cardRow}>
                  <div className={styles.mainCell}>
                    <div className={styles.discountPill}>
                      {formatDiscount(promo.discount)}
                    </div>
                    <span className={styles.code}>Промокод {promo.code}</span>
                  </div>

                  <div className={styles.condition}>{promo.condition}</div>

                  <div className={styles.meta}>{expiresLabel}</div>

                  <div className={styles.usesCell}>
                    <BagIcon className={styles.usesIcon} />
                    <span className={styles.usesValue}>
                      {promo.uses?.value?.toLocaleString('ru-RU') ?? 0}
                      {promo.uses?.delta > 0 ? (
                        <span className={styles.delta}>
                          +{promo.uses.delta.toLocaleString('ru-RU')}
                        </span>
                      ) : null}
                    </span>
                  </div>

                  <div className={styles.actions}>
                    <button
                      type="button"
                      className={styles.iconButton}
                      aria-label="Статистика"
                    >
                      <StatsIcon />
                    </button>
                    <button
                      type="button"
                      className={styles.iconButton}
                      aria-label="Удалить"
                      onClick={() =>
                        setItems((prev) =>
                          prev.filter((p) => p.id !== promo.id),
                        )
                      }
                    >
                      <TrashIcon />
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
