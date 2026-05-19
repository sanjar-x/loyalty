'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

import { useCloneAttributeTemplate } from '@/entities/attribute-template';

import { Modal } from '@/shared/ui/Modal';
import { buildI18nPayload, cn, i18n } from '@/shared/lib/utils';

const CODE_RE = /^[a-z0-9_-]+$/;

export function CloneTemplateModal({ open, source, onClose }) {
  const router = useRouter();
  const [code, setCode] = useState('');
  const [nameRu, setNameRu] = useState('');
  const [nameEn, setNameEn] = useState('');
  const [error, setError] = useState(null);
  const mutation = useCloneAttributeTemplate();

  useEffect(() => {
    if (open) {
      setCode(`${source?.code ?? ''}-copy`);
      setNameRu(`${i18n(source?.nameI18N, source?.code ?? '')} (копия)`);
      setNameEn('');
      setError(null);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, source?.id]);

  const codeError = !code
    ? 'Код обязателен'
    : !CODE_RE.test(code)
      ? 'Только нижний регистр, цифры, дефис, подчёркивание'
      : null;
  const nameError = nameRu.trim() ? null : 'Введите название';
  const isValid = useMemo(
    () => Boolean(source) && !codeError && !nameError,
    [source, codeError, nameError],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    if (!isValid || mutation.isPending) return;
    setError(null);
    try {
      const result = await mutation.mutateAsync({
        sourceTemplateId: source.id,
        newCode: code,
        newNameI18N: buildI18nPayload(nameRu, nameEn),
      });
      onClose?.();
      // Take the admin straight to the clone's detail page so they can
      // tweak the bindings (clones inherit them but admins typically
      // tweak requirement levels per template).
      if (result?.id) {
        router.push(`/admin/settings/attribute-templates/${result.id}`);
      }
    } catch (err) {
      setError(err?.message ?? 'Не удалось клонировать шаблон');
    }
  }

  if (!source) return null;

  return (
    <Modal open={open} onClose={onClose} size="md" title="Клонировать шаблон">
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <p className="text-app-muted text-sm">
          Создаётся копия «{i18n(source.nameI18N, source.code)}» со всеми
          привязками. Назначения категорий не переносятся.
        </p>
        <Field
          label="Новый код"
          value={code}
          onChange={setCode}
          error={codeError}
          mono
          required
        />
        <Field
          label="Название (ru)"
          value={nameRu}
          onChange={setNameRu}
          error={nameError}
          required
        />
        <Field label="Название (en)" value={nameEn} onChange={setNameEn} />

        {error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
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
            disabled={!isValid || mutation.isPending}
            className="bg-app-text rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? 'Клонируем…' : 'Клонировать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({ label, value, onChange, error, required, mono }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-app-text-dark text-xs font-medium">
        {label}
        {required && <span className="text-app-danger ml-1">*</span>}
      </span>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          'border-app-border focus:border-app-text-dark rounded-lg border px-3 py-2 text-sm transition-colors outline-none',
          mono && 'font-mono',
          error && 'border-app-danger',
        )}
      />
      {error && <span className="text-app-danger text-xs">{error}</span>}
    </label>
  );
}
