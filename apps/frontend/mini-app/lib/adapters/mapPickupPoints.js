/**
 * Pickup-points (logistics PVZ) mapper.
 *
 * Backend (`POST /api/v1/logistics/pickup-points`) snake_case'da
 * `PickupPointsResponse` qaytaradi. UI esa camelCase + qo'shimcha
 * computed maydonlarni (addressLine, providerLabel) kutadi.
 *
 * Compound key: backend `external_id` faqat **provider ichida** unique,
 * shuning uchun frontend'da `${provider_code}:${external_id}` orqali
 * global unique id yaratamiz. URL params (?pvzId=cdek:PVZ_123) va
 * marker registry shu kalit bilan ishlaydi.
 *
 * Provider-internal identifiers (`cdek_pvz_code`, `platform_station_id`)
 * server tomonida qoladi va `external_id` orqali abstract qilinadi.
 */

import { pickupPointTypeLabel, providerLabel } from '@/lib/format/providerLabels';

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

// Provider raw_address ba'zan segmentlarni takrorlaydi (CDEK: "Москва, Москва"
// — pochta indeksi shahar nomi bilan birga qaytariladi). Bu helper consecutive
// duplicate'larni va ichida boshqa segmentni qamrab oluvchi takrorlarni
// (case-insensitive) olib tashlaydi, asl tartibni saqlagan holda.
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
  if (typeof addr.raw_address === 'string' && addr.raw_address.trim()) {
    return dedupeAddressSegments(addr.raw_address.trim());
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
    countryCode: addr.country_code ?? '',
    city: addr.city ?? '',
    region: addr.region ?? null,
    postalCode: addr.postal_code ?? null,
    street: addr.street ?? null,
    house: addr.house ?? null,
    apartment: addr.apartment ?? null,
    subdivisionCode: addr.subdivision_code ?? null,
    raw: addr.raw_address ?? null,
    line: composeAddressLine(addr),
  };
}

function mapDimensions(dim) {
  if (!dim || typeof dim !== 'object') return null;
  return {
    lengthCm: dim.length_cm ?? null,
    widthCm: dim.width_cm ?? null,
    heightCm: dim.height_cm ?? null,
  };
}

export function mapPickupPoint(p) {
  if (!p || typeof p !== 'object') return null;
  const providerCode = p.provider_code;
  const externalId = p.external_id;
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
    pickupPointType: p.pickup_point_type ?? null,
    pickupPointTypeLabel: pickupPointTypeLabel(p.pickup_point_type),
    lat,
    lon,
    address,
    addressLine: address?.line ?? '',
    workSchedule:
      typeof p.work_schedule === 'string' && p.work_schedule.trim() ? p.work_schedule.trim() : null,
    phone: typeof p.phone === 'string' && p.phone.trim() ? p.phone.trim() : null,
    isCashAllowed: Boolean(p.is_cash_allowed),
    isCardAllowed: Boolean(p.is_card_allowed),
    weightLimitGrams: typeof p.weight_limit_grams === 'number' ? p.weight_limit_grams : null,
    dimensionsLimit: mapDimensions(p.dimensions_limit),
  };
}

export function mapPickupPointsResponse(response) {
  const points = Array.isArray(response?.points)
    ? response.points.map(mapPickupPoint).filter(Boolean)
    : [];
  const errors = response?.errors && typeof response.errors === 'object' ? response.errors : {};
  return { points, errors };
}

// Backend body uchun tozalash — null/undefined maydonlarni olib tashlaydi
// (FastAPI `anyOf [..., null]` qabul qiladi, lekin clean payload yaxshiroq).
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
    body.radius_km = Number.isFinite(r) ? Math.min(100, Math.max(1, Math.floor(r))) : 10;
  } else if (typeof city === 'string' && city.trim()) {
    body.city = city.trim();
    if (typeof countryCode === 'string' && countryCode.trim()) {
      body.country_code = countryCode.trim().toUpperCase();
    }
    if (typeof postalCode === 'string' && postalCode.trim()) {
      body.postal_code = postalCode.trim();
    }
  } else {
    return null; // backend `latitude+longitude` yoki `city` ni majburan kutadi
  }
  if (typeof providerCode === 'string' && providerCode) {
    body.provider_code = providerCode;
  }
  if (typeof deliveryType === 'string' && deliveryType) {
    body.delivery_type = deliveryType;
  }
  return body;
}
