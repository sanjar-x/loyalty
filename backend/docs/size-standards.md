# Size Standards Reference — Streetwear & Fashion Catalog

## Architecture Decision

Размеры — это **разные системы измерения**, а не один атрибут с разными значениями. Каждая система размеров = отдельный `Attribute` в каталоге. `AttributeFamily` привязывает к категории только релевантные размерные атрибуты.

```
Family "Одежда (верх)"    -> clothing_size [XXS-5XL]
Family "Джинсы"           -> jeans_waist [W23-W56] + jeans_length [L28-L36]
Family "Обувь"            -> shoe_size_eu [35-50.5]
Family "Кепки (fitted)"   -> hat_fitted [6⅞-8¼]
Family "Аксессуары"       -> one_size [OSFM]
```

---

## 1. Clothing Alpha Sizes (Буквенные)

**Код атрибута:** `clothing_size`
**Категории:** Футболки, худи, свитшоты, куртки, ветровки, бомберы, майки, лонгсливы, жилеты
**UI Type:** `TEXT_BUTTON`
**Level:** `VARIANT` (разный размер на каждый SKU)

| Code  | RU  | EN  | Sort |
| ----- | --- | --- | ---- |
| `xxs` | XXS | XXS | 1    |
| `xs`  | XS  | XS  | 2    |
| `s`   | S   | S   | 3    |
| `m`   | M   | M   | 4    |
| `l`   | L   | L   | 5    |
| `xl`  | XL  | XL  | 6    |
| `xxl` | XXL | XXL | 7    |
| `3xl` | 3XL | 3XL | 8    |
| `4xl` | 4XL | 4XL | 9    |
| `5xl` | 5XL | 5XL | 10   |

### Conversion (meta_data)

| Alpha | US Chest | EU Numeric | UK    |
| ----- | -------- | ---------- | ----- |
| XXS   | 28-30    | 38-40      | 28-30 |
| XS    | 30-32    | 40-42      | 30-32 |
| S     | 34-36    | 44-46      | 34-36 |
| M     | 38-40    | 48-50      | 38-40 |
| L     | 42-44    | 52-54      | 42-44 |
| XL    | 46-48    | 56-58      | 46-48 |
| XXL   | 50-52    | 60-62      | 50-52 |
| 3XL   | 54-56    | 64-66      | 54-56 |

---

## 2. Pants Sizes (Штаны, шорты)

**Код атрибута:** `pants_size`
**Категории:** Штаны, шорты (не джинсы)
**UI Type:** `TEXT_BUTTON`
**Level:** `VARIANT`

Используем alpha — как для верха. Те же значения `clothing_size`. Штаны и шорты в streetwear обычно продаются в S/M/L/XL.

---

## 3. Jeans Sizes (Джинсы) — двойная система

Джинсы используют **два атрибута одновременно**: талия (waist) и длина (length).

### 3a. Jeans Waist

**Код атрибута:** `jeans_waist`
**UI Type:** `TEXT_BUTTON`
**Level:** `VARIANT`

| Code  | RU  | EN  | Sort |
| ----- | --- | --- | ---- |
| `w26` | W26 | W26 | 1    |
| `w27` | W27 | W27 | 2    |
| `w28` | W28 | W28 | 3    |
| `w29` | W29 | W29 | 4    |
| `w30` | W30 | W30 | 5    |
| `w31` | W31 | W31 | 6    |
| `w32` | W32 | W32 | 7    |
| `w33` | W33 | W33 | 8    |
| `w34` | W34 | W34 | 9    |
| `w36` | W36 | W36 | 10   |
| `w38` | W38 | W38 | 11   |
| `w40` | W40 | W40 | 12   |
| `w42` | W42 | W42 | 13   |

### 3b. Jeans Length

**Код атрибута:** `jeans_length`
**UI Type:** `TEXT_BUTTON`
**Level:** `VARIANT`

| Code  | RU            | EN            | Sort |
| ----- | ------------- | ------------- | ---- |
| `l28` | L28 (Short)   | L28 (Short)   | 1    |
| `l30` | L30 (Short)   | L30 (Short)   | 2    |
| `l32` | L32 (Regular) | L32 (Regular) | 3    |
| `l34` | L34 (Long)    | L34 (Long)    | 4    |
| `l36` | L36 (X-Long)  | L36 (X-Long)  | 5    |

### Waist → Alpha Mapping

| Waist   | Alpha |
| ------- | ----- |
| W28     | XS    |
| W29-W30 | S     |
| W31-W32 | M     |
| W33-W34 | L     |
| W36-W38 | XL    |
| W40+    | XXL+  |

---

## 4. Shoe Sizes — EU System

**Код атрибута:** `shoe_size_eu`
**Категории:** Кроссовки, кеды, ботинки, туфли, шлёпанцы
**UI Type:** `TEXT_BUTTON`
**Level:** `VARIANT`

| Code      | RU   | EN   | meta_data (US Men / US Women / UK)           | Sort |
| --------- | ---- | ---- | -------------------------------------------- | ---- |
| `eu-35`   | 35   | 35   | `{"us_w": "5", "uk": "2.5"}`                 | 1    |
| `eu-35.5` | 35.5 | 35.5 | `{"us_w": "5.5", "uk": "3"}`                 | 2    |
| `eu-36`   | 36   | 36   | `{"us_w": "5.5", "uk": "3.5"}`               | 3    |
| `eu-36.5` | 36.5 | 36.5 | `{"us_w": "6", "uk": "4"}`                   | 4    |
| `eu-37.5` | 37.5 | 37.5 | `{"us_w": "6.5", "uk": "4.5"}`               | 5    |
| `eu-38`   | 38   | 38   | `{"us_m": "5.5", "us_w": "7", "uk": "5"}`    | 6    |
| `eu-38.5` | 38.5 | 38.5 | `{"us_m": "6", "us_w": "7.5", "uk": "5.5"}`  | 7    |
| `eu-39`   | 39   | 39   | `{"us_m": "6.5", "us_w": "8", "uk": "6"}`    | 8    |
| `eu-40`   | 40   | 40   | `{"us_m": "7", "us_w": "8.5", "uk": "6"}`    | 9    |
| `eu-40.5` | 40.5 | 40.5 | `{"us_m": "7.5", "us_w": "9", "uk": "6.5"}`  | 10   |
| `eu-41`   | 41   | 41   | `{"us_m": "8", "us_w": "9.5", "uk": "7"}`    | 11   |
| `eu-42`   | 42   | 42   | `{"us_m": "8.5", "us_w": "10", "uk": "7.5"}` | 12   |
| `eu-42.5` | 42.5 | 42.5 | `{"us_m": "9", "us_w": "10.5", "uk": "8"}`   | 13   |
| `eu-43`   | 43   | 43   | `{"us_m": "9.5", "uk": "8.5"}`               | 14   |
| `eu-44`   | 44   | 44   | `{"us_m": "10", "uk": "9"}`                  | 15   |
| `eu-44.5` | 44.5 | 44.5 | `{"us_m": "10.5", "uk": "9.5"}`              | 16   |
| `eu-45`   | 45   | 45   | `{"us_m": "11", "uk": "10"}`                 | 17   |
| `eu-45.5` | 45.5 | 45.5 | `{"us_m": "11.5", "uk": "10.5"}`             | 18   |
| `eu-46`   | 46   | 46   | `{"us_m": "12", "uk": "11"}`                 | 19   |
| `eu-47`   | 47   | 47   | `{"us_m": "12.5", "uk": "12"}`               | 20   |
| `eu-47.5` | 47.5 | 47.5 | `{"us_m": "13", "uk": "12.5"}`               | 21   |
| `eu-48`   | 48   | 48   | `{"us_m": "14", "uk": "13"}`                 | 22   |
| `eu-48.5` | 48.5 | 48.5 | `{"us_m": "15", "uk": "14"}`                 | 23   |
| `eu-49.5` | 49.5 | 49.5 | `{"us_m": "16", "uk": "15"}`                 | 24   |
| `eu-50.5` | 50.5 | 50.5 | `{"us_m": "17", "uk": "16"}`                 | 25   |

> **Почему EU а не US:** EU размеры — unisex (одна шкала для мужчин и женщин). US/UK имеют отдельные мужские и женские шкалы, что усложняет каталог. Конвертация хранится в `meta_data`.

---

## 5. Hat Sizes (Кепки)

### 5a. Fitted Caps (New Era 59FIFTY и аналоги)

**Код атрибута:** `hat_fitted`
**UI Type:** `TEXT_BUTTON`
**Level:** `VARIANT`

| Code    | RU  | EN  | meta_data (cm)   | Sort |
| ------- | --- | --- | ---------------- | ---- |
| `6-7_8` | 6⅞  | 6⅞  | `{"cm": "54.9"}` | 1    |
| `7`     | 7   | 7   | `{"cm": "55.8"}` | 2    |
| `7-1_8` | 7⅛  | 7⅛  | `{"cm": "56.8"}` | 3    |
| `7-1_4` | 7¼  | 7¼  | `{"cm": "57.7"}` | 4    |
| `7-3_8` | 7⅜  | 7⅜  | `{"cm": "58.7"}` | 5    |
| `7-1_2` | 7½  | 7½  | `{"cm": "59.6"}` | 6    |
| `7-5_8` | 7⅝  | 7⅝  | `{"cm": "60.6"}` | 7    |
| `7-3_4` | 7¾  | 7¾  | `{"cm": "61.5"}` | 8    |
| `7-7_8` | 7⅞  | 7⅞  | `{"cm": "62.5"}` | 9    |
| `8`     | 8   | 8   | `{"cm": "63.5"}` | 10   |

### 5b. One Size (Snapbacks, Beanies)

**Код атрибута:** `one_size`
**Категории:** Снэпбеки, бини, шарфы, перчатки
**UI Type:** `TEXT_BUTTON`
**Level:** `VARIANT`

| Code   | RU          | EN       | Sort |
| ------ | ----------- | -------- | ---- |
| `osfm` | Один размер | One Size | 1    |

---

## 6. Belt Sizes (Ремни)

**Код атрибута:** `belt_size`
**UI Type:** `DROPDOWN`
**Level:** `VARIANT`

Streetwear ремни обычно продаются в alpha или inches:

| Code | RU              | EN          | meta_data (waist_cm)                           | Sort |
| ---- | --------------- | ----------- | ---------------------------------------------- | ---- |
| `s`  | S (70-80 см)    | S (28-30")  | `{"waist_cm": "70-80", "waist_in": "28-30"}`   | 1    |
| `m`  | M (80-90 см)    | M (32-34")  | `{"waist_cm": "80-90", "waist_in": "32-34"}`   | 2    |
| `l`  | L (90-100 см)   | L (36-38")  | `{"waist_cm": "90-100", "waist_in": "36-38"}`  | 3    |
| `xl` | XL (100-110 см) | XL (40-42") | `{"waist_cm": "100-110", "waist_in": "40-42"}` | 4    |

---

## 7. Ring Sizes (Кольца)

**Код атрибута:** `ring_size`
**UI Type:** `DROPDOWN`
**Level:** `VARIANT`

| Code | RU    | EN     | meta_data (mm)                                   | Sort |
| ---- | ----- | ------ | ------------------------------------------------ | ---- |
| `15` | 15 мм | US 4   | `{"diameter_mm": 15.0, "us": "4", "eu": "47"}`   | 1    |
| `16` | 16 мм | US 5.5 | `{"diameter_mm": 16.0, "us": "5.5", "eu": "50"}` | 2    |
| `17` | 17 мм | US 7   | `{"diameter_mm": 17.3, "us": "7", "eu": "54"}`   | 3    |
| `18` | 18 мм | US 8   | `{"diameter_mm": 18.2, "us": "8", "eu": "57"}`   | 4    |
| `19` | 19 мм | US 9   | `{"diameter_mm": 19.0, "us": "9", "eu": "59"}`   | 5    |
| `20` | 20 мм | US 10  | `{"diameter_mm": 19.8, "us": "10", "eu": "62"}`  | 6    |
| `21` | 21 мм | US 11  | `{"diameter_mm": 20.6, "us": "11", "eu": "65"}`  | 7    |
| `22` | 22 мм | US 12  | `{"diameter_mm": 21.4, "us": "12", "eu": "67"}`  | 8    |

---

## Recommended Family Structure

```
Family "Одежда" (clothing)
├── binds: clothing_size [XXS-5XL] — required
├── assigned to: category "Одежда"
│
├── Family "Джинсы" (jeans) — extends "Одежда"
│   ├── excludes: clothing_size (джинсы не в S/M/L)
│   ├── binds: jeans_waist [W26-W42] — required
│   └── binds: jeans_length [L28-L36] — recommended
│
└── Family "Носки" (socks) — extends "Одежда"
    ├── overrides: clothing_size → sort_order=1, requirement=optional
    └── (носки часто в one_size или S/M/L)

Family "Обувь" (footwear)
├── binds: shoe_size_eu [35-50.5] — required
└── assigned to: category "Обувь"

Family "Аксессуары" (accessories)
├── assigned to: category "Аксессуары"
│
├── Family "Кепки fitted" (fitted_caps) — extends "Аксессуары"
│   └── binds: hat_fitted [6⅞-8] — required
│
├── Family "Снэпбеки/Бини" (snapback_beanie) — extends "Аксессуары"
│   └── binds: one_size [OSFM] — required
│
├── Family "Ремни" (belts) — extends "Аксессуары"
│   └── binds: belt_size [S-XL] — required
│
└── Family "Кольца" (rings) — extends "Аксессуары"
    └── binds: ring_size [15-22mm] — required
```

---

## Summary: Attributes to Create

| Attribute Code  | Name (RU)         | Values Count  | Categories                |
| --------------- | ----------------- | ------------- | ------------------------- |
| `clothing_size` | Размер одежды     | 10 (XXS-5XL)  | Футболки, худи, куртки... |
| `jeans_waist`   | Талия (джинсы)    | 13 (W26-W42)  | Джинсы                    |
| `jeans_length`  | Длина (джинсы)    | 5 (L28-L36)   | Джинсы                    |
| `shoe_size_eu`  | Размер обуви (EU) | 25 (35-50.5)  | Кроссовки, ботинки...     |
| `hat_fitted`    | Размер кепки      | 10 (6⅞-8)     | Fitted caps               |
| `one_size`      | Один размер       | 1 (OSFM)      | Снэпбеки, бини, шарфы     |
| `belt_size`     | Размер ремня      | 4 (S-XL)      | Ремни                     |
| `ring_size`     | Размер кольца     | 8 (15-22mm)   | Кольца                    |
| **Total**       |                   | **76 values** |                           |
