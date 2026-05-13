# TZ: Storefront list endpointlariga `variants[].skus[]` qo'shish

**Maqsad:** PLP / for-you / trending / search list response'larida har product uchun **to'liq SKU mapping** (id + razmer attribute mapping) qo'shish, shunda frontend "В корзину" / "Купить сейчас" tugmasi bosilganda **alohida `/storefront/products/{slug}` fetch qilmasdan** to'g'ridan-to'g'ri `POST /cart/items` ga `skuId` yubora oladi.

**Status:** Backend tarafdan kutilmoqda
**Authoritative spec:** `openapi.json` (uni yangilashni unutmang)
**Affected endpoints:** quyida ko'rsatilgan

---

## 1. Hozirgi holat (yaxshi qadam, lekin yetarli emas)

Sizning so'nggi yangilashingizdan keyin, list response'larda `variantOptions` field paydo bo'ldi. Bu — **product-level barcha mumkin attribute qiymatlari**:

```json
{
  "id": "019dd46d-...",
  "slug": "futbolki",
  "titleI18N": { "ru": "Футболки", "en": "Футболки" },
  "brand": { "id": "...", "name": "Adidas", "slug": "adidas" },
  "price": { "amount": 1200000, "currency": "RUB" },
  "variantCount": 1,
  "inStock": true,
  "variantOptions": [
    {
      "attributeId": "019dd39d-...",
      "attributeCode": "clothing_size",
      "attributeNameI18N": { "ru": "Размер одежды", "en": "Clothing Size" },
      "values": [
        { "valueId": "019dd39d-b095-...", "valueCode": "l",  "valueI18N": { "ru": "L",  "en": "L"  }, "sortOrder": 0 },
        { "valueId": "019dd39d-b090-...", "valueCode": "m",  "valueI18N": { "ru": "M",  "en": "M"  }, "sortOrder": 0 },
        { "valueId": "019dd39d-b089-...", "valueCode": "s",  "valueI18N": { "ru": "S",  "en": "S"  }, "sortOrder": 0 },
        { "valueId": "019dd39d-b09b-...", "valueCode": "xl", "valueI18N": { "ru": "XL", "en": "XL" }, "sortOrder": 0 },
        { "valueId": "019dd39d-b081-...", "valueCode": "xs", "valueI18N": { "ru": "XS", "en": "XS" }, "sortOrder": 0 }
      ]
    }
  ]
}
```

Bu yetarli **razmer chiplarini ko'rsatish** uchun. Lekin **cart action uchun yetarli emas** — chunki `POST /cart/items` `{skuId, quantity}` ni majburan kutadi, va frontend qaysi razmer qaysi `skuId`'ga mos kelishini bilmasligi sabab.

## 2. Etishmayotgan ma'lumot

`POST /api/v1/cart/items` (`AddItemRequest`) shartlari:

```json
{ "skuId": "uuid", "quantity": 1 }
```

Frontend SKU id'ni faqat `/storefront/products/{slug}` (PDP) endpointidan ola oladi — chunki list response'larida `variants[].skus[]` array yo'q.

Natija: PLP/for-you/trending sahifasida QuickAddSheet ochilganda yoki cart action paytida frontend qo'shimcha `GET /storefront/products/{slug}` so'rovini yuborishga majbur. Bu **N+1 antipattern** — har card uchun 1 ta extra fetch.

## 3. Talab — list response'larga `variants[].skus[]` qo'shish

Har list itemiga (`StorefrontProductCardResponse`) `variants` array qo'shing. Har variant — `StorefrontVariantResponse`, ichida `skus[]`. Har SKU — `StorefrontSKUResponse`, ichida `id` va `variantAttributes[]`.

Aslida bu data PDP (`StorefrontProductDetailResponse`) ichida allaqachon mavjud — uni list response'iga ham qo'shish kerak.

### Kutilayotgan response shape

```jsonc
{
  "id": "019dd46d-ed22-77e4-981e-c202bfad69a8",
  "slug": "futbolki",
  "titleI18N": { "ru": "Футболки", "en": "Футболки" },
  "image": { "url": "...", "imageVariants": null },
  "images": [ ... ],
  "price": { "amount": 1200000, "currency": "RUB" },
  "brand": { "id": "...", "name": "Adidas", "slug": "adidas", "logoUrl": null },
  "supplier": { "type": "local" },
  "popularityScore": 0,
  "publishedAt": "...",
  "variantCount": 1,
  "inStock": true,

  // ── HOZIR HAM BOR (saqlanadi) ──
  "variantOptions": [
    {
      "attributeId": "019dd39d-...",
      "attributeCode": "clothing_size",
      "attributeNameI18N": { "ru": "Размер одежды", "en": "Clothing Size" },
      "values": [ /* per-attribute possible values */ ]
    }
  ],

  // ── YANGI: kerakli ma'lumot ──
  "variants": [
    {
      "id": "019dd46d-ed22-77e4-981e-c20304f9edc1",
      "nameI18N": { "ru": "Футболки", "en": "Футболки" },
      "name": null,
      "sortOrder": 0,
      "skus": [
        {
          "id": "019dd46d-f0e4-7691-996b-9ffccbe370fa",
          "skuCode": "futbolki-001",
          "price": { "amount": 1200000, "currency": "RUB", "compareAt": null },
          "resolvedPrice": { "amount": 1200000, "currency": "RUB", "compareAt": null },
          "compareAtPrice": null,
          "isActive": true,
          "variantAttributes": [
            {
              "attributeId": "019dd39d-ad2b-72fd-be20-f870a1401716",
              "attributeValueId": "019dd39d-b095-71c1-afa8-6bd33d88e0fb",
              "attributeCode": "clothing_size",
              "attributeNameI18N": { "ru": "Размер одежды", "en": "Clothing Size" },
              "attributeName": null,
              "valueCode": "l",
              "valueI18N": { "ru": "L", "en": "L" },
              "value": null,
              "sortOrder": 0
            }
          ]
        }
        // ... boshqa SKU'lar (M, S, XL, XS)
      ]
    }
  ]
}
```

### Sxema sozlashlari

OpenAPI'da:

1. **`StorefrontProductCardResponse`** ga `variants: list[StorefrontVariantResponse]` field qo'shing (PDP'dagi shaklning aynan o'zi).
2. `StorefrontVariantResponse` va `StorefrontSKUResponse` allaqachon `openapi.json`'da bor — qayta ishlatilsin.
3. `StorefrontVariantAttributePairResponse` — denormalize bo'lgan shaklda (siz hozirgi PDP'da qaytarayotgandek `valueCode`, `valueI18N` to'liq).

### Affected endpointlar (barchasi)

| Endpoint | OperationId |
|---|---|
| `GET /api/v1/catalog/storefront/products` | list_storefront_products |
| `GET /api/v1/catalog/storefront/for-you` | for_you_feed |
| `GET /api/v1/catalog/storefront/trending` | trending_products |
| `GET /api/v1/catalog/storefront/search` | search_products |
| `GET /api/v1/catalog/storefront/products/{slug}/similar` | pdp_similar |
| `GET /api/v1/catalog/storefront/products/{slug}/also-viewed` | pdp_also_viewed |

PDP detail (`/storefront/products/{slug}`) o'zgarishsiz qoladi — u allaqachon to'g'ri shape qaytaradi.

## 4. Acceptance kriteriyalar

1. Yuqoridagi 6 ta endpoint response'ida har item uchun `variants[]` array bo'lsin.
2. Har `variants[i].skus[j].id` haqiqiy SKU UUID bo'lsin (`POST /cart/items {skuId}` ga uzatib bo'ladigan).
3. Har `variants[i].skus[j].variantAttributes[]` ichida hech bo'lmasa **bitta** denormalize attribute bo'lsin (`attributeCode` va `valueCode`/`valueI18N` bilan).
4. `variants[].skus[].isActive` field aniq qiymat (`true`/`false`) bo'lsin — out-of-stock filter uchun.
5. `variants[].skus[].resolvedPrice` ham yuborilsin — variantga qarab narx farqlansa.
6. `openapi.json`'dagi `StorefrontProductCardResponse` schemasiga yangi `variants` maydoni qo'shilsin va `version: 1.X.X` ko'tarilsin.
7. Yangi field'lar `null` yoki bo'sh array `[]` bo'lishi mumkin (mahsulot uchun variantlar yo'q bo'lsa) — frontend buni tinch ishlay oladi.

## 5. Performance kuzatuvi

| Hozirgi | Yangidan keyin |
|---|---|
| 1 list response (~5 KB) + N ta product detail fetch (~1 KB har biri) | 1 list response (~10–15 KB) |
| Misol: 12 ta card uchun ~17 KB total + 12 ta network roundtrip | ~12-15 KB total + 0 ta extra roundtrip |
| Foydalanuvchi tezkorlik: cart action'da +700ms loading | Foydalanuvchi tezkorlik: instant (0ms qo'shimcha) |

Server payload biroz oshadi (~3-5 KB per item), lekin **N+1 antipattern butunlay yo'qoladi**, network roundtrip soni ~10x kamayadi, va frontend QuickAddSheet'ni instant render qila oladi.

## 6. Frontend tomondagi avtomatik moslashuv

Frontend allaqachon **forward-compatible** kod yozilgan:

```js
// components/blocks/product/QuickAddSheet.jsx
const hasVariantsFromCard =
  Array.isArray(product?.variants) && product.variants.length > 0;

useGetProductByIdQuery(detailKey, {
  skip: !open || !detailKey || hasVariantsFromCard,
});
```

Backend `variants[]` qo'sha bo'lishi bilan **frontend hech qanday o'zgartirishsiz** avtomatik ravishda fetch'ni o'chiradi va list response'dan o'qiydi.

Faqat `lib/format/mapStorefrontProduct.js` ichidagi `variants` mapping allaqachon ishlaydi (PDP uchun yozilgan, list uchun ham qayta ishlatiladi).

## 7. Test plani

Backend deploy bo'lgandan keyin frontend tomondan tekshirish:

1. Bosh sahifani Network tab bilan oching.
2. `/api/backend/api/v1/catalog/storefront/for-you?limit=10` response'ini tekshiring → har itemda `variants[].skus[].id` bo'lishi kerak.
3. Biror card'dagi "Доставка" tugmasini bosing (QuickAddSheet ochish).
4. Network tab'da **`/storefront/products/{slug}` so'rovi tushmasligi kerak** — bu success belgisi.
5. Razmer chiplari instant ko'rinishi kerak.
6. Razmer tanlab "В корзину" / "Купить сейчас" bosing → `POST /cart/items` darhol jo'naydi (loading yo'q).

## 8. Oldindan ko'rsatilgan masalalar (FAQ)

**Savol:** Response og'irligi oshmaydimi?
**Javob:** Oshadi, lekin minimal — har card ~3-5KB. Yuqorida hisoblangan: 12 itemli list ~17KB → ~15KB (chunki har item endi to'liq, lekin extra roundtrip yo'q). Mobile bandwidth uchun **net win**.

**Savol:** Pagination'da har sahifa uchun og'irlik oshib ketsami?
**Javob:** `limit=10` standart uchun ~12-15KB total acceptable. Agar `limit=50+` bo'ladigan endpoint bo'lsa, alohida `?include_skus=false` query param qo'shish mumkin (lekin standart `true` bo'lsin).

**Savol:** SKU listini cache qilsa bo'ladimi?
**Javob:** Ha — `Cache-Control: max-age=60, stale-while-revalidate=300` standartni saqlab qoldiring. SKU mapping kam o'zgaradi.

**Savol:** Mahsulotda `variants[]` umuman bo'lmasa nima bo'ladi?
**Javob:** `variants: []` qaytaring (yoki mavjud `variantOptions: []` bilan birga). Frontend o'zi tinch ishlaydi (`hasVariantsFromCard` `false` qoladi va eski fetch yo'lidan boradi).
