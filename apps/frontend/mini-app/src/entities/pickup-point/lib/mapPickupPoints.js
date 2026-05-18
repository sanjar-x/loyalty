/**
 * Pickup-points (logistics PVZ) mapper.
 *
 * After REFACT-001, the backend (`POST /api/v1/storefront/logistics/pickup-points`)
 * returns `PickupPointsResponse` in camelCase. The UI shape is camelCase plus
 * additional computed fields (addressLine, providerLabel).
 *
 * Compound key: the backend `externalId` is unique **within a provider** only,
 * so on the frontend we build a globally unique id via
 * `${providerCode}:${externalId}`. URL params (?pvzId=cdek:PVZ_123) and the
 * marker registry use this key.
 *
 * Provider-internal identifiers (`cdek_pvz_code`, `platform_station_id`)
 * stay on the server side and are abstracted away behind `externalId`.
 */

import { pickupPointTypeLabel, providerLabel } from '@/entities/pickup-point/lib/providerLabels';

const COMPOUND_KEY_DELIM = ':';

export function buildPickupCompoundId(providerCode, externalId) {
  if (!providerCode || !externalId) return '';
  return `${providerCode}${COMPOUND_KEY_DELIM}${externalId}`;
}

export function parsePickupCompoundId(id) {
  if (typeof id !== 'string' || !id) return null;
  const idx = id.indexOf(COMPOUND_KEY_DELIM);
  if (idx <= 0 || idx === id.length - 1) return null;
  const providerCode = id.slice(0, idx);
  const externalId = id.slice(idx + 1);
  return { providerCode, externalId };
}

// A provider's raw_address sometimes repeats segments (CDEK: "Москва, Москва"
// — the postal index is returned together with the city name). This helper
// removes consecutive duplicates and repeats that contain another segment
// (case-insensitive), while preserving the original order.
function dedupeAddressSegments(line) {
  const segments = line
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  const out = [];
  const seen = new Set();
  for (const s of segments) {
    const key = s.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(s);
  }
  return out.join(', ');
}

function composeAddressLine(addr) {
  if (!addr || typeof addr !== 'object') return '';
  if (typeof addr.rawAddress === 'string' && addr.rawAddress.trim()) {
    return dedupeAddressSegments(addr.rawAddress.trim());
  }
  const parts = [];
  if (addr.city) parts.push(addr.city);
  if (addr.street) parts.push(addr.street);
  if (addr.house) parts.push(`д. ${addr.house}`);
  if (addr.apartment) parts.push(`кв. ${addr.apartment}`);
  return dedupeAddressSegments(parts.join(', '));
}

function mapAddress(addr) {
  if (!addr || typeof addr !== 'object') return null;
  return {
    countryCode: addr.countryCode ?? '',
    city: addr.city ?? '',
    region: addr.region ?? null,
    postalCode: addr.postalCode ?? null,
    street: addr.street ?? null,
    house: addr.house ?? null,
    apartment: addr.apartment ?? null,
    subdivisionCode: addr.subdivisionCode ?? null,
    raw: addr.rawAddress ?? null,
    line: composeAddressLine(addr),
  };
}

function mapDimensions(dim) {
  if (!dim || typeof dim !== 'object') return null;
  return {
    lengthCm: dim.lengthCm ?? null,
    widthCm: dim.widthCm ?? null,
    heightCm: dim.heightCm ?? null,
  };
}

export function mapPickupPoint(p) {
  if (!p || typeof p !== 'object') return null;
  const providerCode = p.providerCode;
  const externalId = p.externalId;
  if (!providerCode || !externalId) return null;
  if (!p.position || typeof p.position !== 'object') return null;
  const lat = Number(p.position.latitude);
  const lon = Number(p.position.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  const address = mapAddress(p.address);
  return {
    id: buildPickupCompoundId(providerCode, externalId),
    providerCode,
    externalId,
    providerLabel: providerLabel(providerCode),
    name: typeof p.name === 'string' ? p.name : '',
    pickupPointType: p.pickupPointType ?? null,
    pickupPointTypeLabel: pickupPointTypeLabel(p.pickupPointType),
    lat,
    lon,
    address,
    addressLine: address?.line ?? '',
    workSchedule:
      typeof p.workSchedule === 'string' && p.workSchedule.trim() ? p.workSchedule.trim() : null,
    phone: typeof p.phone === 'string' && p.phone.trim() ? p.phone.trim() : null,
    isCashAllowed: Boolean(p.isCashAllowed),
    isCardAllowed: Boolean(p.isCardAllowed),
    weightLimitGrams: typeof p.weightLimitGrams === 'number' ? p.weightLimitGrams : null,
    dimensionsLimit: mapDimensions(p.dimensionsLimit),
  };
}

export function mapPickupPointsResponse(response) {
  const points = Array.isArray(response?.points)
    ? response.points.map(mapPickupPoint).filter(Boolean)
    : [];
  const errors = response?.errors && typeof response.errors === 'object' ? response.errors : {};
  return { points, errors };
}

// Cleanup for the backend body — strips null/undefined fields
// (FastAPI accepts `anyOf [..., null]`, but a clean payload is preferable).
// REFACT-001: all fields are in the camelCase wire shape.
export function buildPickupPointsRequestBody({
  latitude,
  longitude,
  radiusKm,
  city,
  countryCode,
  postalCode,
  providerCode,
  deliveryType,
} = {}) {
  const body = {};
  const hasCenter =
    typeof latitude === 'number' &&
    typeof longitude === 'number' &&
    Number.isFinite(latitude) &&
    Number.isFinite(longitude);
  if (hasCenter) {
    body.latitude = latitude;
    body.longitude = longitude;
    const r = Number(radiusKm);
    // Cap at 40km: at zoom-out levels >40km the cluster icons collapse
    // anyway and a larger radius just inflates the carrier payload
    // (CDEK has no server-side radius — it returns the full city)
    // without adding visible markers.
    body.radiusKm = Number.isFinite(r) ? Math.min(100, Math.max(1, Math.floor(r))) : 10;
  } else if (typeof city === 'string' && city.trim()) {
    body.city = city.trim();
    if (typeof countryCode === 'string' && countryCode.trim()) {
      body.countryCode = countryCode.trim().toUpperCase();
    }
    if (typeof postalCode === 'string' && postalCode.trim()) {
      body.postalCode = postalCode.trim();
    }
  } else {
    return null; // backend requires either `latitude+longitude` or `city`
  }
  if (typeof providerCode === 'string' && providerCode) {
    body.providerCode = providerCode;
  }
  if (typeof deliveryType === 'string' && deliveryType) {
    body.deliveryType = deliveryType;
  }
  return body;
}
