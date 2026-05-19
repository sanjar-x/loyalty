'use client';

import { useState } from 'react';

import { apiClient } from '@/shared/api/clientFetch';
import { cn } from '@/shared/lib/utils';

import { PICKUP_CARRIERS } from '../../lib/constants';
import { FormSection } from './FormSection';

// Pickup-point search lifted from `features/order-actions/ChangePickupPointModal`
// — same backend endpoint, same shape, just inlined into the walk-in form
// instead of opening a modal. A future refactor could lift the search hook
// into `entities/order` and have both surfaces consume it; for now the
// inline copy stays a one-feature concern.
async function searchPickupPoints({ city, providerCode }) {
  return apiClient.post('/api/admin/logistics/pickup-points', {
    city,
    countryCode: 'RU',
    providerCode,
    deliveryType: 'pickup_point',
  });
}

// AddressSchema is an object ({line?, street?, city, region, …}) — rendering
// it as a React child throws. Mirror the formatter used by ChangePickupPointModal.
function formatPickupAddress(address) {
  if (!address || typeof address !== 'object') return '—';
  return address.line ?? address.street ?? address.city ?? '—';
}

export function PickupPointSection({
  pickupCarrier,
  pickupPointId,
  pickupPointLabel,
  setPickup,
}) {
  const [providerCode, setProviderCode] = useState(
    pickupCarrier || PICKUP_CARRIERS[0].code,
  );
  const [city, setCity] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  async function handleSearch() {
    if (!city.trim() || searching) return;
    setSearching(true);
    setSearchError(null);
    try {
      const data = await searchPickupPoints({
        city: city.trim(),
        providerCode,
      });
      // Treat shape regression (non-array `points`) as a hard error rather
      // than silently rendering "no results" — wire-format drift should be
      // visible.
      if (!Array.isArray(data?.points)) {
        throw new Error('Сервис вернул некорректный ответ');
      }
      setResults(data.points);
    } catch (err) {
      setSearchError(err?.message ?? 'Не удалось найти пункты выдачи');
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  // The outer page-level <form onSubmit={createOrder}> in WalkInOrderForm
  // makes a nested <form> here invalid HTML, so the search trigger is
  // wired as a plain button + Enter handler on the city input.
  function handleCityKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  }

  return (
    <FormSection
      title="Доставка"
      description="Перевозчик и пункт выдачи. Доставка last-mile прикручивается отдельно после procure."
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-[200px_1fr_auto]">
        <label className="flex flex-col gap-1">
          <span className="text-app-muted text-xs font-medium">
            Перевозчик <span className="text-app-danger">*</span>
          </span>
          <select
            value={providerCode}
            onChange={(e) => {
              setProviderCode(e.target.value);
              setResults([]);
              setPickup('', '', '');
            }}
            className="border-app-border bg-app-panel rounded-lg border px-3 py-2 text-sm outline-none"
          >
            {PICKUP_CARRIERS.map((c) => (
              <option key={c.code} value={c.code}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-app-muted text-xs font-medium">Город</span>
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            onKeyDown={handleCityKeyDown}
            placeholder="Например, Москва"
            className="border-app-border bg-app-panel rounded-lg border px-3 py-2 text-sm outline-none"
          />
        </label>
        <button
          type="button"
          onClick={handleSearch}
          disabled={!city.trim() || searching}
          className={cn(
            'bg-app-text-dark self-end rounded-2xl px-4 py-2 text-sm font-medium text-white transition-colors',
            (!city.trim() || searching) && 'cursor-not-allowed opacity-60',
          )}
        >
          {searching ? 'Ищем…' : 'Найти ПВЗ'}
        </button>
      </div>

      {searchError && <p className="text-app-danger text-sm">{searchError}</p>}

      {results.length > 0 && (
        <ul className="border-app-border divide-app-border max-h-72 divide-y overflow-y-auto rounded-2xl border">
          {results.map((point) => {
            const isSelected =
              pickupPointId === point.externalId &&
              pickupCarrier === point.providerCode;
            const addressText = formatPickupAddress(point.address);
            return (
              <li key={`${point.providerCode}-${point.externalId}`}>
                <button
                  type="button"
                  onClick={() =>
                    setPickup(
                      point.providerCode,
                      point.externalId,
                      `${point.name ?? point.externalId} — ${addressText}`,
                    )
                  }
                  className={cn(
                    'hover:bg-app-card flex w-full flex-col items-start gap-1 px-4 py-3 text-left transition-colors',
                    isSelected && 'bg-app-card',
                  )}
                >
                  <span className="text-app-text text-sm font-medium">
                    {point.name ?? point.externalId}
                  </span>
                  <span className="text-app-muted text-xs">{addressText}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {pickupPointId && (
        <div className="bg-app-card text-app-text rounded-2xl px-4 py-3 text-sm">
          <div className="text-app-muted text-xs">Выбранный ПВЗ</div>
          <div className="mt-1 font-medium">
            {pickupPointLabel || pickupPointId}
          </div>
        </div>
      )}
    </FormSection>
  );
}
