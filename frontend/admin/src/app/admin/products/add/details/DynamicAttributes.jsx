'use client';

import { useEffect, useRef, useState } from 'react';
import { i18n } from '@/lib/utils';
import { ChevronIcon } from './icons';
import styles from './page.module.css';

function TextButtonField({ attribute, selected, onToggle }) {
  const values = attribute.values ?? [];
  return (
    <div className={styles.attrField}>
      <label className={styles.attrLabel}>
        {i18n(attribute.nameI18N)}
        {attribute.requirementLevel === 'required' && (
          <span className={styles.attrRequired}>*</span>
        )}
      </label>
      <div className={styles.attrChips}>
        {values.map((val) => {
          const isActive = selected.includes(val.id);
          return (
            <button
              key={val.id}
              type="button"
              className={isActive ? styles.attrChipActive : styles.attrChip}
              onClick={() => onToggle(val.id)}
            >
              {i18n(val.valueI18N, val.code)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ColorSwatchField({ attribute, selected, onToggle }) {
  const values = attribute.values ?? [];
  return (
    <div className={styles.attrField}>
      <label className={styles.attrLabel}>
        {i18n(attribute.nameI18N)}
        {attribute.requirementLevel === 'required' && (
          <span className={styles.attrRequired}>*</span>
        )}
      </label>
      <div className={styles.attrSwatches}>
        {values.map((val) => {
          const isActive = selected.includes(val.id);
          const color = val.metaData?.hex ?? val.metaData?.color ?? '#ccc';
          const name = i18n(val.valueI18N, val.code);
          return (
            <div key={val.id} className={styles.attrSwatchItem}>
              <button
                type="button"
                className={isActive ? styles.attrSwatchActive : styles.attrSwatch}
                onClick={() => onToggle(val.id)}
                aria-label={name}
                title={name}
              >
                <span
                  className={styles.attrSwatchColor}
                  style={{ backgroundColor: color }}
                />
              </button>
              <span className={styles.attrSwatchName}>{name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DropdownField({ attribute, selected, onChange }) {
  const values = attribute.values ?? [];
  const value = selected[0] ?? '';
  const selectedVal = values.find((v) => v.id === value);
  const selectedLabel = selectedVal ? i18n(selectedVal.valueI18N, selectedVal.code) : '';

  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [search, setSearch] = useState('');
  const rootRef = useRef(null);
  const searchRef = useRef(null);

  const filtered = search.trim()
    ? values.filter((v) =>
        i18n(v.valueI18N, v.code).toLowerCase().includes(search.trim().toLowerCase()),
      )
    : values;

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e) {
      if (!rootRef.current?.contains(e.target)) setOpen(false);
    }
    function onEscape(e) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onEscape);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onEscape);
    };
  }, [open]);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (open) {
      setSearch('');
      setActiveIndex(-1);
      // small delay so the DOM paints first
      requestAnimationFrame(() => searchRef.current?.focus());
    }
  }, [open]);

  function handleKeyDown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      const item = filtered[activeIndex];
      if (item) {
        onChange(item.id === value ? [] : [item.id]);
        setOpen(false);
      }
    }
  }

  return (
    <div className={styles.attrField} ref={rootRef} style={{ position: 'relative' }}>
      <label className={styles.attrLabel}>
        {i18n(attribute.nameI18N)}
        {attribute.requirementLevel === 'required' && (
          <span className={styles.attrRequired}>*</span>
        )}
      </label>
      <button
        type="button"
        className={styles.attrDropdownTrigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={selectedLabel ? styles.attrDropdownValue : styles.attrDropdownPlaceholder}>
          {selectedLabel || 'Выберите'}
        </span>
        <span className={styles.attrDropdownChevron} style={open ? { transform: 'rotate(180deg)' } : undefined}>
          <ChevronIcon />
        </span>
      </button>

      {open && (
        <div className={styles.attrDropdownPanel}>
          {values.length > 6 && (
            <div className={styles.attrDropdownSearchWrap}>
              <input
                ref={searchRef}
                className={styles.attrDropdownSearchInput}
                placeholder="Поиск..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setActiveIndex(-1);
                }}
                onKeyDown={handleKeyDown}
              />
            </div>
          )}
          <div className={styles.attrDropdownList} role="listbox">
            {filtered.length === 0 ? (
              <div className={styles.attrDropdownEmpty}>Ничего не найдено</div>
            ) : (
              filtered.map((val, idx) => {
                const isSelected = val.id === value;
                const isActive = idx === activeIndex;
                return (
                  <button
                    key={val.id}
                    type="button"
                    className={styles.attrDropdownOption}
                    role="option"
                    aria-selected={isSelected}
                    style={isActive ? { background: '#f4f3f1' } : undefined}
                    onClick={() => {
                      onChange(isSelected ? [] : [val.id]);
                      setOpen(false);
                    }}
                  >
                    <span className={styles.attrDropdownOptionText}>
                      {i18n(val.valueI18N, val.code)}
                    </span>
                    <span className={styles.attrDropdownCheck}>
                      {isSelected && <span className={styles.attrDropdownCheckInner} />}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CheckboxField({ attribute, selected, onToggle }) {
  const values = attribute.values ?? [];
  return (
    <div className={styles.attrField}>
      <label className={styles.attrLabel}>
        {i18n(attribute.nameI18N)}
        {attribute.requirementLevel === 'required' && (
          <span className={styles.attrRequired}>*</span>
        )}
      </label>
      <div className={styles.attrCheckboxes}>
        {values.map((val) => {
          const isChecked = selected.includes(val.id);
          return (
            <label key={val.id} className={styles.attrCheckboxLabel}>
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => onToggle(val.id)}
                className={styles.attrCheckbox}
              />
              <span>{i18n(val.valueI18N, val.code)}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function RangeSliderField({ attribute, value, onChange }) {
  const rules = attribute.validationRules ?? {};
  const min = rules.min ?? 0;
  const max = rules.max ?? 100;
  return (
    <div className={styles.attrField}>
      <label className={styles.attrLabel}>
        {i18n(attribute.nameI18N)}
        {attribute.requirementLevel === 'required' && (
          <span className={styles.attrRequired}>*</span>
        )}
      </label>
      <input
        type="number"
        className={styles.attrInput}
        placeholder={`${min} — ${max}`}
        min={min}
        max={max}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function AttributeField({ attribute, values, onUpdate }) {
  const selected = values[attribute.attributeId] ?? [];
  const level = attribute.level ?? 'product';
  const isProductLevel = level === 'product';

  function handleToggle(valueId) {
    if (isProductLevel) {
      // Product-level: single select only (API allows one value per attribute).
      // Clicking the active value deselects it; clicking another replaces.
      const next = selected.includes(valueId) ? [] : [valueId];
      onUpdate(attribute.attributeId, next, level);
    } else {
      const next = selected.includes(valueId)
        ? selected.filter((id) => id !== valueId)
        : [...selected, valueId];
      onUpdate(attribute.attributeId, next, level);
    }
  }

  function handleSet(next) {
    onUpdate(attribute.attributeId, next, level);
  }

  // Product-level attrs with toggle-based uiTypes (text_button, color_swatch,
  // checkbox) must behave as single-select — fall through to dropdown instead.
  if (isProductLevel && (attribute.uiType === 'checkbox')) {
    return (
      <DropdownField
        attribute={attribute}
        selected={selected}
        onChange={handleSet}
      />
    );
  }

  switch (attribute.uiType) {
    case 'text_button':
      return (
        <TextButtonField
          attribute={attribute}
          selected={selected}
          onToggle={handleToggle}
        />
      );
    case 'color_swatch':
      return (
        <ColorSwatchField
          attribute={attribute}
          selected={selected}
          onToggle={handleToggle}
        />
      );
    case 'dropdown':
      return (
        <DropdownField
          attribute={attribute}
          selected={selected}
          onChange={handleSet}
        />
      );
    case 'checkbox':
      return (
        <CheckboxField
          attribute={attribute}
          selected={selected}
          onToggle={handleToggle}
        />
      );
    case 'range_slider':
      return (
        <RangeSliderField
          attribute={attribute}
          value={selected[0]}
          onChange={(val) => handleSet([val])}
        />
      );
    default:
      return (
        <DropdownField
          attribute={attribute}
          selected={selected}
          onChange={handleSet}
        />
      );
  }
}

export default function DynamicAttributes({
  formData,
  loading,
  values,
  onChange,
  excludeLevel,
}) {
  function handleUpdate(attributeId, selectedValues, level) {
    onChange?.(attributeId, selectedValues, level);
  }

  if (loading) {
    return (
      <section className={styles.card}>
        <div className={styles.skeletonGroup}>
          <div className={styles.skeletonRow}>
            <div className={styles.skeletonLabel} />
            <div className={styles.skeletonChips}>
              <div className={styles.skeletonChip} />
              <div className={styles.skeletonChip} />
              <div className={styles.skeletonChip} />
              <div className={styles.skeletonChip} />
            </div>
          </div>
          <div className={styles.skeletonRow}>
            <div className={styles.skeletonLabelShort} />
            <div className={styles.skeletonSelect} />
          </div>
          <div className={styles.skeletonRow}>
            <div className={styles.skeletonLabel} />
            <div className={styles.skeletonChips}>
              <div className={styles.skeletonChip} />
              <div className={styles.skeletonChip} />
              <div className={styles.skeletonChip} />
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (!formData?.groups?.length) return null;

  return formData.groups
    .map((group) => {
      // Filter out attributes at the excluded level
      const attrs = excludeLevel
        ? group.attributes.filter((a) => a.level !== excludeLevel)
        : group.attributes;

      if (attrs.length === 0) return null;

      return (
        <section key={group.groupId} className={styles.card}>
          <h2 className={styles.cardTitle}>
            {i18n(group.groupNameI18N, group.groupCode)}
          </h2>
          <div className={styles.fieldGroup}>
            {attrs.map((attr) => (
              <AttributeField
                key={attr.attributeId}
                attribute={attr}
                values={values}
                onUpdate={handleUpdate}
              />
            ))}
          </div>
        </section>
      );
    })
    .filter(Boolean);
}
