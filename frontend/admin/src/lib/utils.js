import { clsx } from 'clsx';
import dayjs from '@/lib/dayjs';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value) {
  return new Intl.NumberFormat('ru-RU').format(Number(value) || 0) + ' ₽';
}

export function formatDateTime(value) {
  return dayjs(value).format('D MMMM HH:mm');
}

export function pluralizeRu(count, one, few, many) {
  const abs = Math.abs(count);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod100 >= 11 && mod100 <= 14) return many;
  if (mod10 === 1) return one;
  if (mod10 >= 2 && mod10 <= 4) return few;
  return many;
}

export function buildFacetOptions(list, valueSelector) {
  const counts = new Map();
  list.forEach((item) => {
    const key = valueSelector(item);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });

  const values = Array.from(counts.keys()).sort((a, b) =>
    String(a).localeCompare(String(b), 'ru-RU'),
  );

  return {
    options: ['all', ...values].map((value) => ({
      value,
      label: value === 'all' ? 'Все' : value,
      count: value === 'all' ? list.length : (counts.get(value) ?? 0),
    })),
    counts,
  };
}

export function i18n(obj, fallback = '') {
  if (!obj || typeof obj !== 'object') return fallback;
  return obj.ru ?? obj.en ?? Object.values(obj)[0] ?? fallback;
}

/**
 * Build an i18n payload with both ru and en locales.
 * When en is empty/falsy, copies the ru value as fallback.
 */
export function buildI18nPayload(ru, en) {
  return { ru, en: en || ru };
}

export async function copyToClipboard(text) {
  const value = String(text ?? '').trim();
  if (!value) return;

  try {
    await navigator.clipboard.writeText(value);
    return;
  } catch {
    // ignore and fallback below
  }

  try {
    const el = document.createElement('textarea');
    el.value = value;
    el.setAttribute('readonly', '');
    el.style.position = 'fixed';
    el.style.top = '0';
    el.style.left = '0';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.focus();
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
  } catch {
    // ignore
  }
}

