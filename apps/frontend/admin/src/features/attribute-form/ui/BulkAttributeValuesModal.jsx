'use client';

import { useEffect, useMemo, useState } from 'react';

import { useBulkAddAttributeValues } from '@/entities/attribute-value';

import { Modal } from '@/shared/ui/Modal';

const CODE_RE = /^[a-z0-9_]+$/;

/**
 * Parses one CSV-ish line into a `BulkAttributeValueItem`. Format:
 *
 *     code,slug,ru name,en name?[,group?[,#hex?]]
 *
 * Empty lines are skipped; lines without enough mandatory columns
 * surface as `errors` so the admin can fix them inline before submit.
 */
function parseLine(line, index) {
  const cells = line.split(',').map((c) => c.trim());
  const [code, slug, ru, en, group, hex] = cells;
  const errors = [];
  if (!code) errors.push('код');
  else if (!CODE_RE.test(code)) errors.push('некорректный код');
  if (!slug) errors.push('slug');
  if (!ru) errors.push('ru');
  return {
    index,
    raw: line,
    item: errors.length
      ? null
      : {
          code,
          slug,
          valueI18N: { ru, en: en || ru },
          searchAliases: [],
          metaData: hex ? { hex } : {},
          valueGroup: group || null,
          sortOrder: index,
        },
    errors,
  };
}

export function BulkAttributeValuesModal({ open, attributeId, onClose }) {
  const [text, setText] = useState('');
  const [error, setError] = useState(null);
  const mutation = useBulkAddAttributeValues(attributeId);

  useEffect(() => {
    if (open) {
      setText('');
      setError(null);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const parsed = useMemo(
    () =>
      text
        .split('\n')
        .map((line, idx) => ({ line: line.trim(), idx }))
        .filter(({ line }) => line.length > 0)
        .map(({ line, idx }) => parseLine(line, idx)),
    [text],
  );

  const validItems = parsed.filter((p) => !p.errors.length).map((p) => p.item);
  const errorRows = parsed.filter((p) => p.errors.length);
  const isValid = validItems.length > 0 && errorRows.length === 0;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!isValid || mutation.isPending) return;
    setError(null);
    try {
      await mutation.mutateAsync(validItems);
      onClose?.();
    } catch (err) {
      setError(err?.message ?? 'Не удалось импортировать значения');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title="Массовый ввод значений"
    >
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <p className="text-app-muted text-xs">
          Формат CSV:{' '}
          <code className="bg-app-card rounded px-1 font-mono">
            code,slug,ru name,en name?[,group?[,#hex?]]
          </code>
          . Максимум 100 строк.
        </p>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={10}
          placeholder={`red,red,Красный,Red,Warm tones,#FF0000\nblue,blue,Синий,Blue,Cool tones,#0000FF`}
          className="border-app-border focus:border-app-text-dark w-full rounded-lg border px-3 py-2 font-mono text-sm transition-colors outline-none"
        />
        {errorRows.length > 0 && (
          <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <p className="mb-1 font-medium">
              Строки с ошибками ({errorRows.length}):
            </p>
            <ul className="list-disc pl-4">
              {errorRows.slice(0, 5).map((row) => (
                <li key={row.index}>
                  Строка {row.index + 1}: пропущено {row.errors.join(', ')}
                </li>
              ))}
              {errorRows.length > 5 && <li>…и ещё {errorRows.length - 5}</li>}
            </ul>
          </div>
        )}

        <p className="text-app-muted text-xs">
          Готово к отправке: {validItems.length} строк
        </p>

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
            {mutation.isPending ? 'Импортируем…' : 'Импортировать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
