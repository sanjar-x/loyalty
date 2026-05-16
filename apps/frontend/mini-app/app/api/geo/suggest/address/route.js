import { NextResponse } from 'next/server';

import { getBackendBaseUrl } from '@/lib/api/server/backendBaseUrl';

/**
 * Address suggest BFF — endi backend'imizning custom geo katalog'iga proxy.
 *
 * Eski xatti-harakat: `dadata.ru` Suggestions API'ga so'rov.
 * Yangi xatti-harakat: `GET /api/v1/geo/countries/RU/subdivisions?search=...&lang=ru`
 * — backend tomonidan tarjima qilingan tuman/region nomi bo'yicha qidiradi
 * va lat/lng bilan birga qaytaradi.
 *
 * Response shape DaData'ga mos tarzda saqlangan, shuning uchun
 * `app/checkout/pickup/page.jsx` mijozi o'zgartirishsiz ishlaydi:
 *
 *   {
 *     suggestions: [
 *       { value: <name>, data: { geo_lat, geo_lon, city_with_type, region_with_type, country } },
 *       ...
 *     ]
 *   }
 *
 * Cheklov: backend'da bitta chaqiruv bilan butun mamlakat bo'yicha district
 * darajasidagi qidiruv yo'q (faqat per-subdivision). Hozirgi UX (yirik
 * shaharlar/regionlar) subdivision darajasi yetadi (Moskva, Sankt-Peterburg,
 * Tatarstan va h.k. — RF subyektlari). Granular district qidiruvi kerak
 * bo'lsa, kelajakda subdivision tanlanganidan keyin districts'ga drill-in
 * qilish mumkin.
 */

function pickPreferredTranslation(translations, lang) {
  if (!Array.isArray(translations) || translations.length === 0) return null;
  const target = String(lang || 'ru').toLowerCase();
  const exact = translations.find((t) => String(t?.lang_code || '').toLowerCase() === target);
  return exact || translations[0];
}

export async function POST(req) {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Server config error' },
      { status: 500 }
    );
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const query = body?.query;
  if (typeof query !== 'string') {
    return NextResponse.json({ error: 'query must be a string' }, { status: 400 });
  }

  const q = query.trim();
  if (!q) {
    return NextResponse.json({ suggestions: [] });
  }

  const countRaw = body?.count;
  const count =
    typeof countRaw === 'number' && Number.isFinite(countRaw)
      ? Math.min(20, Math.max(1, Math.floor(countRaw)))
      : 10;

  const lang = typeof body?.lang === 'string' && body.lang.trim() ? body.lang.trim() : 'ru';
  const countryCode =
    typeof body?.countryCode === 'string' && body.countryCode.trim()
      ? body.countryCode.trim().toUpperCase()
      : 'RU';

  const sp = new URLSearchParams();
  sp.set('search', q);
  sp.set('lang', lang);
  sp.set('limit', String(count));

  const upstreamUrl = `${backendBase}/api/v1/geo/countries/${encodeURIComponent(
    countryCode
  )}/subdivisions?${sp.toString()}`;

  let upstream;
  try {
    upstream = await fetch(upstreamUrl, {
      method: 'GET',
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(10_000),
    });
  } catch (e) {
    return NextResponse.json(
      {
        error: 'Backend unreachable',
        hint: e?.name === 'TimeoutError' ? 'Timeout' : e?.message,
      },
      { status: 502 }
    );
  }

  if (!upstream.ok) {
    let details = null;
    try {
      details = await upstream.json();
    } catch {
      // ignore
    }
    return NextResponse.json(
      {
        error: 'Geo lookup failed',
        status: upstream.status,
        details,
      },
      { status: upstream.status === 404 ? 404 : 502 }
    );
  }

  let payload;
  try {
    payload = await upstream.json();
  } catch {
    return NextResponse.json({ suggestions: [] });
  }

  const items = Array.isArray(payload?.items) ? payload.items : [];
  const suggestions = items
    .map((it) => {
      if (!it || typeof it !== 'object') return null;
      const tr = pickPreferredTranslation(it.translations, lang);
      const name = tr?.name?.trim() || it.code || '';
      if (!name) return null;
      const lat = typeof it.latitude === 'number' ? it.latitude : null;
      const lon = typeof it.longitude === 'number' ? it.longitude : null;
      return {
        value: name,
        data: {
          geo_lat: lat,
          geo_lon: lon,
          city_with_type: name,
          region_with_type: tr?.official_name || name,
          settlement_with_type: null,
          area_with_type: null,
          country: countryCode === 'RU' ? 'Россия' : countryCode,
          subdivision_code: it.code || null,
        },
      };
    })
    .filter(Boolean);

  return NextResponse.json({ suggestions });
}
