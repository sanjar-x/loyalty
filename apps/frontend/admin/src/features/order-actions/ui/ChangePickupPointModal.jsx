'use client';

import { useEffect, useState } from 'react';
import { Modal } from '@/shared/ui/Modal';
import { cn } from '@/shared/lib/utils';
import { apiClient } from '@/shared/api/clientFetch';
import { useChangePickupPoint } from '../model/useOrderActions';

const PROVIDERS = [
  { code: 'cdek', label: 'СДЭК' },
  { code: 'yandex_delivery', label: 'Яндекс.Доставка' },
];

async function searchPickupPoints({ city, providerCode }) {
  // PickupPointsRequest accepts either city or lat/lng. Admins typically
  // know the customer's city, so we keep the form to a single input.
  return apiClient.post('/api/admin/logistics/pickup-points', {
    city,
    countryCode: 'RU',
    providerCode,
    deliveryType: 'pickup_point',
  });
}

export function ChangePickupPointModal({ open, onClose, order, onSuccess }) {
  const [providerCode, setProviderCode] = useState(PROVIDERS[0].code);
  const [city, setCity] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [selected, setSelected] = useState(null);

  const mutation = useChangePickupPoint(order?.orderId);

  useEffect(() => {
    if (open) {
      setProviderCode(order?.pickupCarrier ?? PROVIDERS[0].code);
      setCity('');
      setResults([]);
      setSelected(null);
      setSearchError(null);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, order?.orderId]);

  if (!order) return null;

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!city.trim() || searching) return;
    setSearching(true);
    setSearchError(null);
    setSelected(null);
    try {
      const data = await searchPickupPoints({
        city: city.trim(),
        providerCode,
      });
      setResults(Array.isArray(data?.points) ? data.points : []);
    } catch (err) {
      setSearchError(err?.message ?? 'Не удалось найти пункты выдачи');
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selected || mutation.isPending) return;
    mutation.mutate(
      {
        carrier: selected.providerCode,
        pointId: selected.externalId,
      },
      {
        onSuccess: () => {
          onSuccess?.();
          onClose();
        },
      },
    );
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title="Изменить пункт выдачи"
    >
      <div className="mt-4 space-y-4">
        <div>
          <label className="text-app-text-dark mb-1 block text-sm font-medium">
            Перевозчик
          </label>
          <div className="flex flex-wrap gap-2">
            {PROVIDERS.map((p) => (
              <button
                key={p.code}
                type="button"
                onClick={() => {
                  setProviderCode(p.code);
                  setResults([]);
                  setSelected(null);
                }}
                className={cn(
                  'rounded-lg px-3 py-2 text-sm font-medium',
                  providerCode === p.code
                    ? 'bg-app-text-dark text-white'
                    : 'bg-app-card text-app-text-dark hover:bg-app-divider-strong',
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Город (например, Москва)"
            className="border-app-border focus:border-app-text-dark flex-1 rounded-lg border px-3 py-2 text-sm transition-colors outline-none"
            disabled={searching}
          />
          <button
            type="submit"
            disabled={!city.trim() || searching}
            className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {searching ? 'Ищем…' : 'Найти'}
          </button>
        </form>

        {searchError && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {searchError}
          </div>
        )}

        {results.length > 0 ? (
          <div className="border-app-border max-h-64 overflow-y-auto rounded-lg border">
            <ul className="divide-app-border divide-y">
              {results.map((p) => {
                const id = `${p.providerCode}-${p.externalId}`;
                const isSelected =
                  selected?.providerCode === p.providerCode &&
                  selected?.externalId === p.externalId;
                return (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => setSelected(p)}
                      className={cn(
                        'w-full px-3 py-2 text-left text-sm transition-colors',
                        isSelected
                          ? 'bg-app-text-dark/5 border-l-app-text-dark border-l-4'
                          : 'hover:bg-app-card',
                      )}
                    >
                      <p className="text-app-text-dark font-medium">{p.name}</p>
                      <p className="text-app-muted text-xs">
                        {p.address?.line ?? p.address?.street ?? '—'}
                      </p>
                      {p.workSchedule && (
                        <p className="text-app-muted text-xs">
                          {p.workSchedule}
                        </p>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : !searching && city.trim() && !searchError ? (
          <p className="text-app-muted bg-app-card rounded-lg p-3 text-sm">
            Введите город и нажмите «Найти», чтобы увидеть пункты.
          </p>
        ) : null}

        {mutation.error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {mutation.error.message}
          </div>
        )}

        <p className="text-app-muted text-xs">
          Текущий: {order.pickupCarrier} ·{' '}
          <code className="bg-app-card rounded px-1 font-mono">
            {order.pickupPointId}
          </code>
        </p>

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
            type="button"
            onClick={handleSubmit}
            disabled={!selected || mutation.isPending}
            className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? 'Сохраняем…' : 'Назначить пункт выдачи'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
