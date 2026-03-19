'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import styles from '@/app/admin/settings/promocodes/page.module.css';

export default function CreatePromocodeModal({ open, onClose, onCreate }) {
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

  const canSubmit = useMemo(() => {
    return Boolean(formCode.trim()) && Boolean(discountValue);
  }, [formCode, discountValue]);

  const toggleSelect = (name) => {
    setOpenSelect((prev) => (prev === name ? null : name));
  };

  const generateCode = () => {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    const length = 8;
    const randomValues = crypto.getRandomValues(new Uint32Array(length));
    const next = Array.from(randomValues, (v) => alphabet[v % alphabet.length]).join('');
    setFormCode(next);
    codeRef.current?.focus();
  };

  const toggleCondition = (id) => {
    setConditions((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      return [...prev, id];
    });
  };

  const resetForm = () => {
    setOpenSelect(null);
    setFormCode('');
    setDiscountUnit('%');
    setDiscountValue(null);
    setConditions([]);
    setExpiresPreset('none');
  };

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return undefined;

    codeRef.current?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event) => {
      if (event.key === 'Escape') handleClose();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open, handleClose]);

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

    onCreate({
      id: `promo-${Date.now()}`,
      code: formCode.trim().toUpperCase(),
      discount,
      condition: conditionText || '—',
      expiresAt,
      uses: { value: 0, delta: 0 },
    });

    resetForm();
  };

  if (!open) return null;

  return (
    <div
      className={styles.modalOverlay}
      role="presentation"
      onClick={handleClose}
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
            onClick={handleClose}
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
  );
}
