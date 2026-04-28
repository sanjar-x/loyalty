Checkout & Pickup — Backend Texnik Topshiriq (TZ)

▎ Hujjat maqsadi: app/checkout, app/checkout/pickup va ularga aloqador komponentlarning biznes-mantiqi va texnik tuzilishini batafsil tushuntirish. Backend tomonida qanday endpointlar, modellar,
▎ validatsiyalar va biznes qoidalari kerakligini ko'rsatish.
▎
▎ Frontend stack: Next.js 15 (App Router), React 18, RTK Query, Leaflet + leaflet.markercluster, DaData Suggestions API.

---

1. Biznes flow (yuqori darajada)

User savatga mahsulot qo'shadi → /trash sahifasida kerakli pozitsiyalarni selectedIds bilan tanlaydi va promokod kiritadi → «Перейти к оформлению» tugmasi selectedIds + appliedPromo'ni localStorage'ga yozib
/checkout'ga o'tkazadi.

/checkout sahifasida user quyidagi 4 blokni to'ldiradi:

1. Пункт выдачи (PVZ) — /checkout/pickup sahifasiga o'tib (search → map → list) tanlanadi va URL query (pickupPvzId, pickupAddress, pickupProvider) bilan /checkout'ga qaytadi.
2. Получатель (recipient) — FIO, telefon (+7 9XX), email — bottom-sheet modal, localStorage'da saqlanadi.
3. Данные для таможни (customs) — passport seriya/raqam, beriliş sanasi, tug'ilgan sana, INN — modal, localStorage'da saqlanadi.
4. To'lov usuli — СБП yoki bank kartasi (+ ixtiyoriy «сплит» 4×880₽).

Tepada balans (поинты) toggle, promokod chegirmasi, dostavka summasi va итого ko'rsatiladi. Tugma «Оформить сплит» / «Оплатить через СБП» / «Оплатить картой» — hozircha frontend faqat split bottom-sheet'ni
ochadi, backend chaqiruvi yo'q.

▎ Diqqat: hozir checkout submit'i (initiate / confirm) ulanмаgan. RTK Query'da useInitiateCheckoutMutation, useConfirmCheckoutMutation, useCancelCheckoutMutation mavjud (/api/v1/cart/checkout,
▎ /cart/checkout/confirm, /cart/checkout/cancel), lekin UI ularni hali chaqirmaydi. Quyidagi TZ — backend qanday tayyor turishi kerakligi haqida.

---
1. PVZ (Пункт выдачи) flow

3.1 Hozirgi vaziyat — frontend mock

app/checkout/pickup/page.jsx'da 500 ta test PVZ nuqtasi generateTestPvzPoints(500) bilan client'da generatsiya qilinadi (28 shahar × 4 provayder: «Яндекс Доставка», «CDEK», «Boxberry», «Почта России»). Hech
qanday backend chaqiruv yo'q.

Backend integratsiyasidan keyin bu mock olib tashlanadi va useListPickupPointsMutation'ga ulanadi (RTK Query'da allaqachon e'lon qilingan, lekin chaqirilmaydi):

Provayder enum: yandex | cdek | boxberry | russianpost (frontendda hozir display label sifatida ishlatiladi: "Яндекс Доставка", "CDEK", "Boxberry", "Почта России" — backend providerLabel bersa, frontend
mapping olib tashlanadi).

B. GET /api/v1/logistics/pickup-points/{id} — bitta PVZ haqida to'liq ma'lumot (PVZ modal ochilganda fallback / refresh).

Response: yuqoridagi PickupPoint schema bilan bir xil + tarif/доставка хисоблаш SKU кесими:

{
"...": "...",
"tariffsBySku": [
{ "skuId": "uuid", "deliveryDays": {"min":1,"max":3},
"price": {"amount":19900,"currency":"RUB"} }
]
}

C. (Optional) POST /api/v1/logistics/pickup-points/search — matnli qidiruv (provider + address ichida LIKE):
{ "query": "Тверская 7", "city": "Москва", "limit": 50 }

3.3 Map UX texnik tafsilotlari

- Tile provider: hozirda CartoCDN (https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png) — backend tomonida o'zgartirish kerak emas, lekin balki MAP_TILE_URL env qilinadi.
- Clustering: leaflet.markercluster, maxClusterRadius: 52, chunkedLoading: true. 500+ marker'da CPU yetadi — backend bbox bo'yicha pagination qaytarsa, ularni sanab qaytaradigan total ham qo'shilsin ({ items,
  total, hasMore }).
- Geolocation: navigator.geolocation.watchPosition (high accuracy), backend bilan aloqasi yo'q.
- Yaqin PVZ saralash: frontend o'zi haversine bilan saralaydi (distanceKm). Backend ?sortBy=distance&center=... qo'llasa, frontend nearestFirst
