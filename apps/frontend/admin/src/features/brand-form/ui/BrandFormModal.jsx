'use client';

import { useEffect, useState } from 'react';
import { useBrand, useCreateBrand, useUpdateBrand } from '@/entities/brand';
import {
  confirmMedia,
  reserveMediaUpload,
  subscribeMediaStatus,
  uploadToS3,
} from '@/entities/product';
import { Modal } from '@/shared/ui/Modal';
import { cn } from '@/shared/lib/utils';

const SLUG_RE = /^[a-z0-9-]+$/;

function transliterate(value) {
  const map = {
    а: 'a',
    б: 'b',
    в: 'v',
    г: 'g',
    д: 'd',
    е: 'e',
    ё: 'yo',
    ж: 'zh',
    з: 'z',
    и: 'i',
    й: 'y',
    к: 'k',
    л: 'l',
    м: 'm',
    н: 'n',
    о: 'o',
    п: 'p',
    р: 'r',
    с: 's',
    т: 't',
    у: 'u',
    ф: 'f',
    х: 'kh',
    ц: 'ts',
    ч: 'ch',
    ш: 'sh',
    щ: 'shch',
    ъ: '',
    ы: 'y',
    ь: '',
    э: 'e',
    ю: 'yu',
    я: 'ya',
  };
  return value
    .toLowerCase()
    .split('')
    .map((c) => map[c] ?? c)
    .join('')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 255);
}

/**
 * Unified create / edit brand modal. The same form drives both flows;
 * the only branch is which mutation hook fires on submit. The logo
 * upload reuses the product-side 3-step media chain (reserve / S3 /
 * confirm / SSE) — brands ship a `logoStorageObjectId` field that the
 * backend resolves to the public URL on read.
 */
export function BrandFormModal({ open, onClose, mode = 'create', brandId }) {
  const isEdit = mode === 'edit';
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [logoStorageObjectId, setLogoStorageObjectId] = useState(null);
  const [logoUrl, setLogoUrl] = useState(null);
  const [logoUploadStatus, setLogoUploadStatus] = useState('idle');
  const [logoError, setLogoError] = useState(null);

  const { data: existing } = useBrand(isEdit ? brandId : null);
  const createMutation = useCreateBrand();
  const updateMutation = useUpdateBrand(brandId);
  const mutation = isEdit ? updateMutation : createMutation;

  // Reset form on (re)open + seed from server snapshot in edit mode.
  useEffect(() => {
    if (!open) return;
    setSlugTouched(false);
    setLogoUploadStatus('idle');
    setLogoError(null);
    if (isEdit && existing) {
      setName(existing.name ?? '');
      setSlug(existing.slug ?? '');
      setLogoStorageObjectId(null);
      setLogoUrl(existing.logoUrl ?? null);
    } else {
      setName('');
      setSlug('');
      setLogoStorageObjectId(null);
      setLogoUrl(null);
    }
    mutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, isEdit, existing?.id]);

  const slugValid = slug.length > 0 && SLUG_RE.test(slug);
  const canSubmit = name.trim().length > 0 && slugValid && !mutation.isPending;

  function handleNameChange(value) {
    setName(value);
    if (!slugTouched) setSlug(transliterate(value));
  }

  async function handleLogoChange(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setLogoUploadStatus('uploading');
    setLogoError(null);
    try {
      const slot = await reserveMediaUpload({
        contentType: file.type || 'image/jpeg',
        filename: file.name,
      });
      await uploadToS3(slot.presignedUrl, file);
      await confirmMedia(slot.storageObjectId);
      setLogoUploadStatus('processing');
      const metadata = await subscribeMediaStatus(slot.storageObjectId);
      setLogoStorageObjectId(slot.storageObjectId);
      setLogoUrl(metadata?.url ?? null);
      setLogoUploadStatus('completed');
    } catch (err) {
      setLogoUploadStatus('failed');
      setLogoError(err?.message ?? 'Не удалось загрузить логотип');
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    const payload = { name: name.trim(), slug };
    if (logoStorageObjectId) payload.logoStorageObjectId = logoStorageObjectId;
    mutation.mutate(payload, { onSuccess: onClose });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={isEdit ? 'Редактировать бренд' : 'Создать бренд'}
    >
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label
            htmlFor="brand-name"
            className="text-app-text-dark mb-1 block text-sm font-medium"
          >
            Название
          </label>
          <input
            id="brand-name"
            type="text"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            className="border-app-border focus:border-app-text-dark w-full rounded-lg border px-3 py-2 text-sm transition-colors outline-none"
            disabled={mutation.isPending}
            autoFocus
          />
        </div>

        <div>
          <label
            htmlFor="brand-slug"
            className="text-app-text-dark mb-1 block text-sm font-medium"
          >
            Slug
          </label>
          <input
            id="brand-slug"
            type="text"
            value={slug}
            onChange={(e) => {
              setSlug(e.target.value.toLowerCase());
              setSlugTouched(true);
            }}
            className={cn(
              'border-app-border focus:border-app-text-dark w-full rounded-lg border px-3 py-2 font-mono text-sm transition-colors outline-none',
              slug.length > 0 && !slugValid && 'border-app-danger',
            )}
            disabled={mutation.isPending}
            // Audit 6.1 — describedby pulls both the static format hint
            // and the conditionally-rendered error so SR users get the
            // grammar rule first, then the validation verdict.
            aria-invalid={(slug.length > 0 && !slugValid) || undefined}
            aria-describedby="brand-slug-help brand-slug-error"
          />
          <p id="brand-slug-help" className="text-app-muted mt-1 text-xs">
            Латинские буквы, цифры и дефис. Шаблон:{' '}
            <code className="font-mono">{SLUG_RE.source}</code>.
          </p>
          {slug.length > 0 && !slugValid && (
            // Audit 6.1 — role="alert" announces the error the moment
            // the validation switches from valid → invalid. Pre-fix the
            // inline red text was visual-only; SR users had to discover
            // the rule from the hint alone.
            <p
              id="brand-slug-error"
              role="alert"
              className="text-app-danger mt-1 text-xs"
            >
              Slug не соответствует шаблону.
            </p>
          )}
        </div>

        <div>
          <label className="text-app-text-dark mb-1 block text-sm font-medium">
            Логотип
          </label>
          <div className="border-app-border flex items-center gap-3 rounded-lg border p-3">
            <div className="bg-app-card flex h-16 w-16 items-center justify-center overflow-hidden rounded-md">
              {logoUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={logoUrl}
                  alt="Логотип бренда"
                  className="h-full w-full object-contain"
                />
              ) : (
                <span className="text-app-muted text-xs">—</span>
              )}
            </div>
            <div className="flex-1">
              <input
                id="brand-logo"
                type="file"
                accept="image/*"
                onChange={handleLogoChange}
                disabled={
                  mutation.isPending ||
                  logoUploadStatus === 'uploading' ||
                  logoUploadStatus === 'processing'
                }
                className="text-sm"
              />
              {/* Audit 6.2 — aria-live so SR users hear the upload state
                  transitions (Загрузка → Обработка → Готово / ошибка) instead
                  of only sighted users seeing the text flip. `polite` queues
                  behind any current speech instead of interrupting it. */}
              <p
                className="text-app-muted mt-1 text-xs"
                aria-live="polite"
                aria-atomic="true"
              >
                {logoUploadStatus === 'uploading' && 'Загрузка...'}
                {logoUploadStatus === 'processing' && 'Обработка...'}
                {logoUploadStatus === 'completed' &&
                  'Готово — нажмите "Сохранить" чтобы применить.'}
                {logoUploadStatus === 'failed' && logoError}
                {logoUploadStatus === 'idle' && <>JPG / PNG / SVG, до 5 МБ</>}
              </p>
            </div>
          </div>
        </div>

        {mutation.error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {mutation.error.message}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={mutation.isPending}
            className="text-app-muted hover:text-app-text-dark px-3 py-2 text-sm font-medium"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={!canSubmit}
            className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending
              ? 'Сохраняем…'
              : isEdit
                ? 'Сохранить'
                : 'Создать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
