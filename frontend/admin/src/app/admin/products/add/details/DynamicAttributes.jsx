'use client';

import { useEffect, useState } from 'react';
import { i18n } from '@/lib/utils';
import { fetchFormAttributes } from '@/services/attributes';
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
          return (
            <button
              key={val.id}
              type="button"
              className={isActive ? styles.attrSwatchActive : styles.attrSwatch}
              onClick={() => onToggle(val.id)}
              aria-label={i18n(val.valueI18N, val.code)}
              title={i18n(val.valueI18N, val.code)}
            >
              <span
                className={styles.attrSwatchColor}
                style={{ backgroundColor: color }}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DropdownField({ attribute, selected, onChange }) {
  const values = attribute.values ?? [];
  const value = selected[0] ?? '';
  return (
    <div className={styles.attrField}>
      <label className={styles.attrLabel}>
        {i18n(attribute.nameI18N)}
        {attribute.requirementLevel === 'required' && (
          <span className={styles.attrRequired}>*</span>
        )}
      </label>
      <select
        className={styles.attrSelect}
        value={value}
        onChange={(e) => onChange(e.target.value ? [e.target.value] : [])}
      >
        <option value="">Выберите</option>
        {values.map((val) => (
          <option key={val.id} value={val.id}>
            {i18n(val.valueI18N, val.code)}
          </option>
        ))}
      </select>
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

  function handleToggle(valueId) {
    const current = selected;
    const next = current.includes(valueId)
      ? current.filter((id) => id !== valueId)
      : [...current, valueId];
    onUpdate(attribute.attributeId, next);
  }

  function handleSet(next) {
    onUpdate(attribute.attributeId, next);
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

export default function DynamicAttributes({ categoryId, values, onChange }) {
  const [formData, setFormData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!categoryId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    fetchFormAttributes(categoryId)
      .then((data) => setFormData(data))
      .finally(() => setLoading(false));
  }, [categoryId]);

  function handleUpdate(attributeId, selectedValues) {
    onChange?.({ ...values, [attributeId]: selectedValues });
  }

  if (loading) {
    return (
      <section className={styles.card}>
        <div className="space-y-4">
          <div className="h-5 w-40 rounded bg-app-card animate-pulse" />
          <div className="h-10 rounded-lg bg-app-card animate-pulse" />
          <div className="h-10 rounded-lg bg-app-card animate-pulse" />
        </div>
      </section>
    );
  }

  if (!formData?.groups?.length) return null;

  return formData.groups.map((group) => (
    <section key={group.groupId} className={styles.card}>
      <h2 className={styles.cardTitle}>
        {i18n(group.groupNameI18N, group.groupCode)}
      </h2>
      <div className={styles.fieldGroup}>
        {group.attributes.map((attr) => (
          <AttributeField
            key={attr.attributeId}
            attribute={attr}
            values={values}
            onUpdate={handleUpdate}
          />
        ))}
      </div>
    </section>
  ));
}
