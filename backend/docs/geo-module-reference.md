# Geo Module — Data Structure Reference

> Module: `src/modules/geo/`
> Database: PostgreSQL
> Standards: ISO 3166-1, ISO 3166-2, ISO 4217, IETF BCP 47 / ISO 639
> Status: Production-ready (read-only reference data)

---

## ER Diagram

```
                                ┌─────────────────────────────────────┐
                                │            languages                │
                                │─────────────────────────────────────│
                                │ code          PK    VARCHAR(12)     │  ◄── IETF BCP 47
                                │ iso639_1            VARCHAR(2)      │
                                │ iso639_2            VARCHAR(3)      │
                                │ iso639_3            VARCHAR(3)      │
                                │ script              VARCHAR(4)      │
                                │ name_en             VARCHAR(100)    │
                                │ name_native         VARCHAR(100)    │
                                │ direction           VARCHAR(3)      │
                                │ is_active           BOOLEAN         │
                                │ is_default          BOOLEAN         │
                                │ sort_order          SMALLINT        │
                                │ updated_at          TIMESTAMPTZ     │
                                └──────────────┬──────────────────────┘
                                               │
                          ┌────────────────────┬┴──────────────────────┐
                          │ FK lang_code       │ FK lang_code          │ FK lang_code
                          ▼                    ▼                       ▼
  ┌───────────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────────┐
  │    country_translations       │  │  currency_translations   │  │  subdivision_translations     │
  │───────────────────────────────│  │──────────────────────────│  │──────────────────────────────│
  │ id            PK  UUID        │  │ id         PK  UUID      │  │ id            PK  UUID        │
  │ country_code  FK  VARCHAR(2)  │  │ currency_  FK VARCHAR(3) │  │ subdivision_  FK VARCHAR(10)  │
  │ lang_code     FK  VARCHAR(12) │  │ lang_code  FK VARCHAR(12)│  │ lang_code     FK VARCHAR(12)  │
  │ name              VARCHAR(255)│  │ name         VARCHAR(100)│  │ name              VARCHAR(255)│
  │ official_name     VARCHAR(255)│  └──────────┬───────────────┘  │ official_name     VARCHAR(255)│
  └──────────┬────────────────────┘             │                  │ local_variant     VARCHAR(255)│
             │                                  │                  └──────────┬───────────────────┘
             │ FK country_code                  │ FK currency_code            │ FK subdivision_code
             ▼                                  ▼                             ▼
  ┌──────────────────────────┐     ┌──────────────────────────┐  ┌───────────────────────────────┐
  │        countries         │     │       currencies         │  │        subdivisions           │
  │──────────────────────────│     │──────────────────────────│  │───────────────────────────────│
  │ alpha2   PK  VARCHAR(2)  │     │ code     PK  VARCHAR(3)  │  │ code          PK VARCHAR(10)  │
  │ alpha3   UQ  VARCHAR(3)  │     │ numeric  UQ  VARCHAR(3)  │  │ country_code  FK VARCHAR(2)   │
  │ numeric  UQ  VARCHAR(3)  │     │ name         VARCHAR(100)│  │ category_code FK VARCHAR(60)  │
  │ updated_at   TIMESTAMPTZ │     │ minor_unit   SMALLINT    │  │ parent_code   FK VARCHAR(10)  │
  └──────────┬───────────────┘     │ is_active    BOOLEAN     │  │ latitude         NUMERIC(10,7)│
             │                     │ sort_order   SMALLINT    │  │ longitude        NUMERIC(10,7)│
             │                     │ updated_at   TIMESTAMPTZ │  │ sort_order       SMALLINT     │
             │                     └─────────────┬────────────┘  │ is_active        BOOLEAN      │
             │                                   │               └───────────────────────────────┘
             │          ┌────────────────────┐   │
             │          │ country_currencies │   │
             └────FK───►│────────────────────│◄──┘
                        │ country_code CPK   │
                        │ currency_code CPK  │
                        │ is_primary BOOLEAN │
                        └────────────────────┘
```

---

## Table: `languages`

IETF BCP 47 language/locale tags. Drives UI locale pickers and translation lookups.

| Column        | Type           | PK  | UQ  | Null | Default | Standard           |
| ------------- | -------------- | --- | --- | ---- | ------- | ------------------ |
| `code`        | `VARCHAR(12)`  | PK  |     |      |         | IETF BCP 47        |
| `iso639_1`    | `VARCHAR(2)`   |     |     | Yes  |         | ISO 639-1          |
| `iso639_2`    | `VARCHAR(3)`   |     |     | Yes  |         | ISO 639-2/T        |
| `iso639_3`    | `VARCHAR(3)`   |     |     | Yes  |         | ISO 639-3          |
| `script`      | `VARCHAR(4)`   |     |     | Yes  |         | ISO 15924          |
| `name_en`     | `VARCHAR(100)` |     |     |      |         |                    |
| `name_native` | `VARCHAR(100)` |     |     |      |         |                    |
| `direction`   | `VARCHAR(3)`   |     |     |      | `'ltr'` | `ltr` or `rtl`     |
| `is_active`   | `BOOLEAN`      |     |     |      | `true`  |                    |
| `is_default`  | `BOOLEAN`      |     |     |      | `false` | Exactly one `true` |
| `sort_order`  | `SMALLINT`     |     |     |      | `0`     |                    |
| `updated_at`  | `TIMESTAMPTZ`  |     |     |      | `now()` | Auto-updated       |

**Indexes:** `ix_languages_iso639_1(iso639_1)`, `ix_languages_active(is_active)`

### Seed Data (9 languages)

| code      | iso639_1 | script | name_en          | name_native   | direction | active | default |
| --------- | -------- | ------ | ---------------- | ------------- | --------- | ------ | ------- |
| `uz-Latn` | uz       | Latn   | Uzbek (Latin)    | O'zbekcha     | ltr       | Yes    | No      |
| `uz-Cyrl` | uz       | Cyrl   | Uzbek (Cyrillic) | Ўзбекча       | ltr       | Yes    | No      |
| `ru`      | ru       | —      | Russian          | Русский       | ltr       | Yes    | **Yes** |
| `en`      | en       | —      | English          | English       | ltr       | Yes    | No      |
| `kk`      | kk       | —      | Kazakh           | Қазақша       | ltr       | No     | No      |
| `ky`      | ky       | —      | Kyrgyz           | Кыргызча      | ltr       | No     | No      |
| `tg`      | tg       | —      | Tajik            | Тоҷикӣ        | ltr       | No     | No      |
| `tk`      | tk       | —      | Turkmen          | Türkmençe     | ltr       | No     | No      |
| `kaa`     | —        | Latn   | Karakalpak       | Qaraqalpaqsha | ltr       | No     | No      |

---

## Table: `countries`

ISO 3166-1 country reference. Names stored in `country_translations`.

| Column       | Type          | PK  | UQ  | Null | Default | Standard                         |
| ------------ | ------------- | --- | --- | ---- | ------- | -------------------------------- |
| `alpha2`     | `VARCHAR(2)`  | PK  |     |      |         | ISO 3166-1 Alpha-2               |
| `alpha3`     | `VARCHAR(3)`  |     | UQ  |      |         | ISO 3166-1 Alpha-3               |
| `numeric`    | `VARCHAR(3)`  |     | UQ  |      |         | ISO 3166-1 Numeric (zero-padded) |
| `updated_at` | `TIMESTAMPTZ` |     |     |      | `now()` | Auto-updated                     |

### Seed Data (25 countries)

**CIS / Central Asia:**

| alpha2 | alpha3 | numeric | Primary Currency |
| ------ | ------ | ------- | ---------------- |
| `UZ`   | UZB    | 860     | UZS              |
| `KZ`   | KAZ    | 398     | KZT              |
| `TJ`   | TJK    | 762     | TJS              |
| `KG`   | KGZ    | 417     | KGS              |
| `TM`   | TKM    | 795     | TMT              |
| `RU`   | RUS    | 643     | RUB              |
| `BY`   | BLR    | 112     | BYN              |
| `UA`   | UKR    | 804     | UAH              |
| `AZ`   | AZE    | 031     | AZN              |
| `GE`   | GEO    | 268     | GEL              |
| `AM`   | ARM    | 051     | AMD              |
| `MD`   | MDA    | 498     | MDL              |

**Trade Partners:**

| alpha2 | alpha3 | numeric | Primary Currency |
| ------ | ------ | ------- | ---------------- |
| `CN`   | CHN    | 156     | CNY              |
| `TR`   | TUR    | 792     | TRY              |
| `KR`   | KOR    | 410     | KRW              |
| `JP`   | JPN    | 392     | JPY              |
| `IN`   | IND    | 356     | INR              |
| `AE`   | ARE    | 784     | AED              |
| `SA`   | SAU    | 682     | SAR              |
| `US`   | USA    | 840     | USD              |
| `GB`   | GBR    | 826     | GBP              |
| `DE`   | DEU    | 276     | EUR              |
| `FR`   | FRA    | 250     | EUR              |
| `IT`   | ITA    | 380     | EUR              |
| `PL`   | POL    | 616     | PLN              |
| `AF`   | AFG    | 004     | AFN              |

---

## Table: `country_translations`

Multi-language country names. Each country has translations in `en`, `ru`, `uz-Latn`, `uz-Cyrl`.

| Column          | Type           | PK  | FK                         | Null | Unique                    |
| --------------- | -------------- | --- | -------------------------- | ---- | ------------------------- |
| `id`            | `UUID`         | PK  |                            |      |                           |
| `country_code`  | `VARCHAR(2)`   |     | `countries.alpha2` CASCADE |      | (country_code, lang_code) |
| `lang_code`     | `VARCHAR(12)`  |     | `languages.code` CASCADE   |      | (country_code, lang_code) |
| `name`          | `VARCHAR(255)` |     |                            |      |                           |
| `official_name` | `VARCHAR(255)` |     |                            | Yes  |                           |

**Indexes:** `ix_country_tr_lang(lang_code)`, `ix_country_tr_name(name)`

### Example: Uzbekistan

| lang_code | name        | official_name            |
| --------- | ----------- | ------------------------ |
| `en`      | Uzbekistan  | Republic of Uzbekistan   |
| `ru`      | Узбекистан  | Республика Узбекистан    |
| `uz-Latn` | O'zbekiston | O'zbekiston Respublikasi |
| `uz-Cyrl` | Ўзбекистон  | Ўзбекистон Республикаси  |

---

## Table: `currencies`

ISO 4217 currency reference with `minor_unit` for decimal precision.

| Column       | Type           | PK  | UQ  | Null | Default | Standard                           |
| ------------ | -------------- | --- | --- | ---- | ------- | ---------------------------------- |
| `code`       | `VARCHAR(3)`   | PK  |     |      |         | ISO 4217 Alpha-3                   |
| `numeric`    | `VARCHAR(3)`   |     | UQ  |      |         | ISO 4217 Numeric (zero-padded)     |
| `name`       | `VARCHAR(100)` |     |     |      |         | English name                       |
| `minor_unit` | `SMALLINT`     |     |     | Yes  |         | Decimal places (0-4, NULL for XXX) |
| `is_active`  | `BOOLEAN`      |     |     |      | `true`  |                                    |
| `sort_order` | `SMALLINT`     |     |     |      | `0`     |                                    |
| `updated_at` | `TIMESTAMPTZ`  |     |     |      | `now()` | Auto-updated                       |

**Indexes:** `ix_currencies_numeric`, `ix_currencies_active`, `ix_currencies_name`

### Minor Unit Reference

| minor_unit | Meaning          | Examples                  |
| ---------- | ---------------- | ------------------------- |
| `0`        | No decimals      | JPY (Yen), KRW (Won)      |
| `2`        | Standard (cents) | USD, EUR, UZS, RUB        |
| `3`        | Three decimals   | BHD (Bahraini Dinar), KWD |
| `4`        | Four decimals    | CLF (Unidad de Fomento)   |
| `NULL`     | No currency      | XXX, XTS                  |

### Seed Data (24 currencies)

| code  | numeric | name                   | minor_unit |
| ----- | ------- | ---------------------- | ---------- |
| `UZS` | 860     | Uzbekistan Sum         | 2          |
| `KZT` | 398     | Tenge                  | 2          |
| `TJS` | 972     | Somoni                 | 2          |
| `KGS` | 417     | Som                    | 2          |
| `TMT` | 934     | Turkmenistan New Manat | 2          |
| `RUB` | 643     | Russian Ruble          | 2          |
| `BYN` | 933     | Belarussian Ruble      | 2          |
| `UAH` | 980     | Hryvnia                | 2          |
| `AZN` | 944     | Azerbaijan Manat       | 2          |
| `GEL` | 981     | Lari                   | 2          |
| `AMD` | 051     | Armenian Dram          | 2          |
| `MDL` | 498     | Moldovan Leu           | 2          |
| `CNY` | 156     | Yuan Renminbi          | 2          |
| `TRY` | 949     | Turkish Lira           | 2          |
| `KRW` | 410     | Won                    | **0**      |
| `JPY` | 392     | Yen                    | **0**      |
| `INR` | 356     | Indian Rupee           | 2          |
| `AED` | 784     | UAE Dirham             | 2          |
| `SAR` | 682     | Saudi Riyal            | 2          |
| `USD` | 840     | US Dollar              | 2          |
| `GBP` | 826     | Pound Sterling         | 2          |
| `EUR` | 978     | Euro                   | 2          |
| `PLN` | 985     | Zloty                  | 2          |
| `AFN` | 971     | Afghani                | 2          |

---

## Table: `currency_translations`

Multi-language currency names. Each currency translated into 4 languages.

| Column          | Type           | PK  | FK                        | Null | Unique                     |
| --------------- | -------------- | --- | ------------------------- | ---- | -------------------------- |
| `id`            | `UUID`         | PK  |                           |      |                            |
| `currency_code` | `VARCHAR(3)`   |     | `currencies.code` CASCADE |      | (currency_code, lang_code) |
| `lang_code`     | `VARCHAR(12)`  |     | `languages.code` CASCADE  |      | (currency_code, lang_code) |
| `name`          | `VARCHAR(100)` |     |                           |      |                            |

### Example: US Dollar

| lang_code | name         |
| --------- | ------------ |
| `en`      | US Dollar    |
| `ru`      | Доллар США   |
| `uz-Latn` | AQSh dollari |
| `uz-Cyrl` | АҚШ доллари  |

---

## Table: `country_currencies`

M:N bridge linking countries to their currencies.

| Column          | Type         | PK  | FK                         | Null | Default |
| --------------- | ------------ | --- | -------------------------- | ---- | ------- |
| `country_code`  | `VARCHAR(2)` | CPK | `countries.alpha2` CASCADE |      |         |
| `currency_code` | `VARCHAR(3)` | CPK | `currencies.code` CASCADE  |      |         |
| `is_primary`    | `BOOLEAN`    |     |                            |      | `false` |

**Index:** `ix_country_currencies_currency_code(currency_code)`

### Key relationships

- Germany (DE), France (FR), Italy (IT) all share `EUR`
- Each country has exactly one `is_primary = true` currency
- A country may accept multiple currencies (e.g., Bhutan: BTN + INR)

---

## Table: `subdivisions`

ISO 3166-2 administrative divisions (regions, provinces, oblasts).

| Column          | Type            | PK  | FK                                     | Null | Default         |
| --------------- | --------------- | --- | -------------------------------------- | ---- | --------------- |
| `code`          | `VARCHAR(10)`   | PK  |                                        |      | ISO 3166-2 code |
| `country_code`  | `VARCHAR(2)`    |     | `countries.alpha2` CASCADE             |      |                 |
| `category_code` | `VARCHAR(60)`   |     | `subdivision_categories.code` RESTRICT |      |                 |
| `parent_code`   | `VARCHAR(10)`   |     | `subdivisions.code` SET NULL           | Yes  |                 |
| `latitude`      | `NUMERIC(10,7)` |     |                                        | Yes  | WGS 84          |
| `longitude`     | `NUMERIC(10,7)` |     |                                        | Yes  | WGS 84          |
| `sort_order`    | `SMALLINT`      |     |                                        |      | `0`             |
| `is_active`     | `BOOLEAN`       |     |                                        |      | `true`          |

**Indexes:** `ix_subdivisions_country`, `ix_subdivisions_category(country_code, category_code)`, `ix_subdivisions_parent`

### FK Cascade Behaviors

| Relationship                             | ondelete | Reason                                     |
| ---------------------------------------- | -------- | ------------------------------------------ |
| `country_code → countries`               | CASCADE  | Country deleted = all subdivisions deleted |
| `category_code → subdivision_categories` | RESTRICT | Cannot delete category while in use        |
| `parent_code → subdivisions`             | SET NULL | Parent deleted = children become top-level |

---

## Table: `subdivision_categories`

Types of administrative divisions (PROVINCE, EMIRATE, OBLAST, etc.)

| Column       | Type          | PK  | Null | Default            |
| ------------ | ------------- | --- | ---- | ------------------ |
| `code`       | `VARCHAR(60)` | PK  |      | ISO category token |
| `sort_order` | `SMALLINT`    |     |      | `0`                |

---

## Table: `subdivision_translations` / `subdivision_category_translations`

Same pattern as country/currency translations. See ER diagram above.

Subdivision translations include an additional `local_variant` field for alternative local names (e.g., "Yugra" for Khanty-Mansi Autonomous Okrug).

---

## Cross-Module References

| Source                  | Column       | Target            | ondelete     |
| ----------------------- | ------------ | ----------------- | ------------ |
| `catalog.skus.currency` | `VARCHAR(3)` | `currencies.code` | **RESTRICT** |

The `RESTRICT` constraint prevents deletion of any currency that is referenced by a SKU.

---

## API Endpoints

All endpoints are public (no authentication), paginated, and cached for 1 hour.

### `GET /geo/countries`

List all countries with multi-language translations.

| Param    | Type      | Default | Description                              |
| -------- | --------- | ------- | ---------------------------------------- |
| `lang`   | `string?` | —       | Filter translations to one language code |
| `offset` | `int`     | 0       | Pagination offset (>= 0)                 |
| `limit`  | `int`     | 50      | Pagination limit (1-500)                 |

```json
{
  "items": [
    {
      "alpha2": "UZ",
      "alpha3": "UZB",
      "numeric": "860",
      "translations": [
        {
          "lang_code": "en",
          "name": "Uzbekistan",
          "official_name": "Republic of Uzbekistan"
        },
        {
          "lang_code": "ru",
          "name": "Узбекистан",
          "official_name": "Республика Узбекистан"
        }
      ]
    }
  ],
  "total": 25
}
```

### `GET /geo/currencies`

List currencies (active by default).

| Param              | Type      | Default | Description                         |
| ------------------ | --------- | ------- | ----------------------------------- |
| `lang`             | `string?` | —       | Filter translations to one language |
| `include_inactive` | `bool`    | false   | Include deactivated currencies      |
| `offset`           | `int`     | 0       | Pagination offset                   |
| `limit`            | `int`     | 50      | Pagination limit                    |

```json
{
  "items": [
    {
      "code": "UZS",
      "numeric": "860",
      "name": "Uzbekistan Sum",
      "minor_unit": 2,
      "translations": [{ "lang_code": "ru", "name": "Узбекский сум" }]
    }
  ],
  "total": 24
}
```

### `GET /geo/languages`

List supported languages.

| Param              | Type   | Default | Description                |
| ------------------ | ------ | ------- | -------------------------- |
| `include_inactive` | `bool` | false   | Include inactive languages |
| `offset`           | `int`  | 0       | Pagination offset          |
| `limit`            | `int`  | 50      | Pagination limit           |

```json
{
  "items": [
    {
      "code": "uz-Latn",
      "iso639_1": "uz",
      "iso639_2": "uzb",
      "iso639_3": "uzb",
      "script": "Latn",
      "name_en": "Uzbek (Latin)",
      "name_native": "O'zbekcha",
      "direction": "ltr",
      "is_active": true,
      "is_default": false,
      "sort_order": 1
    }
  ],
  "total": 9
}
```

### `GET /geo/countries/{country_code}/currencies`

List currencies for a specific country. Returns 404 if country not found.

| Param          | Type      | Default | Description                           |
| -------------- | --------- | ------- | ------------------------------------- |
| `country_code` | `path`    | —       | ISO 3166-1 Alpha-2 (case-insensitive) |
| `lang`         | `string?` | —       | Filter translations                   |
| `offset`       | `int`     | 0       | Pagination offset                     |
| `limit`        | `int`     | 50      | Pagination limit                      |

### `GET /geo/countries/{country_code}/subdivisions`

List administrative subdivisions for a country. Returns 404 if country not found.

| Param          | Type      | Default | Description                           |
| -------------- | --------- | ------- | ------------------------------------- |
| `country_code` | `path`    | —       | ISO 3166-1 Alpha-2 (case-insensitive) |
| `lang`         | `string?` | —       | Filter translations                   |
| `offset`       | `int`     | 0       | Pagination offset                     |
| `limit`        | `int`     | 50      | Pagination limit                      |

```json
{
  "items": [
    {
      "code": "UZ-TO",
      "country_code": "UZ",
      "category_code": "REGION",
      "parent_code": null,
      "latitude": 41.3117,
      "longitude": 69.2797,
      "translations": [
        {
          "lang_code": "en",
          "name": "Tashkent",
          "official_name": null,
          "local_variant": null
        }
      ]
    }
  ],
  "total": 14
}
```

---

## HTTP Headers

All geo endpoints return:

```
Cache-Control: public, max-age=3600
```

Clients should cache reference data for at least 1 hour.

---

## Error Responses

| HTTP | Error Code              | Condition                                |
| ---- | ----------------------- | ---------------------------------------- |
| 404  | `COUNTRY_NOT_FOUND`     | `country_code` path param does not exist |
| 404  | `CURRENCY_NOT_FOUND`    | Currency code does not exist             |
| 404  | `LANGUAGE_NOT_FOUND`    | Language code does not exist             |
| 404  | `SUBDIVISION_NOT_FOUND` | Subdivision code does not exist          |

```json
{
  "message": "Country with code 'XY' not found.",
  "error_code": "COUNTRY_NOT_FOUND",
  "details": { "country_code": "XY" }
}
```

---

## Architecture

```
src/modules/geo/
├── domain/
│   ├── value_objects.py    # Country, Currency, Language, Subdivision (frozen attrs)
│   ├── interfaces.py       # ICountryRepository, ICurrencyRepository, ...
│   └── exceptions.py       # CountryNotFoundError, CurrencyNotFoundError, ...
├── application/
│   └── queries/
│       ├── list_countries.py      # ORM select + selectinload
│       ├── list_currencies.py     # ORM select + join + selectinload
│       ├── list_languages.py      # ORM select
│       ├── list_subdivisions.py   # ORM select + selectinload
│       └── read_models.py         # Pydantic DTOs
├── infrastructure/
│   ├── models.py                  # SQLAlchemy ORM (10 models)
│   └── repositories/
│       ├── country.py             # Data Mapper pattern
│       ├── currency.py
│       ├── language.py
│       └── subdivision.py
└── presentation/
    ├── router.py                  # FastAPI endpoints
    └── dependencies.py            # Dishka DI providers
```

### Design Decisions

| Decision      | Choice              | Rationale                                           |
| ------------- | ------------------- | --------------------------------------------------- |
| Primary keys  | Natural (ISO codes) | Stable, globally unique, human-readable             |
| Translations  | Separate tables     | FK integrity, sparse translations, row-level audit  |
| Lazy loading  | `lazy="raise"`      | Prevent N+1; explicit `selectinload()` in handlers  |
| Query pattern | ORM `select()`      | Consistent with catalog module, refactorable        |
| Counting      | `func.count()`      | Database-side, O(1) memory                          |
| Caching       | `Cache-Control: 1h` | Reference data is quasi-static                      |
| Soft delete   | `is_active` flag    | Currencies/languages can be hidden without deletion |

---

## Migration History

| Revision  | Date       | Description                                                  |
| --------- | ---------- | ------------------------------------------------------------ |
| `21_0001` | 2026-03-21 | Create `countries` table                                     |
| `21_0002` | 2026-03-21 | Create `languages` table                                     |
| `21_0003` | 2026-03-21 | Create `country_translations` table                          |
| `21_0004` | 2026-03-21 | Seed languages, countries, translations                      |
| `22_0001` | 2026-03-22 | Create currencies, currency_translations, country_currencies |
| `22_0002` | 2026-03-22 | Seed currencies, translations, country-currency links        |
| `22_0003` | 2026-03-22 | Refactor: Country.numeric → String(3), drop Country.name     |
| `22_0004` | 2026-03-22 | Add missing uz-Cyrl country translations                     |
| `22_0005` | 2026-03-22 | Add FK: catalog.SKU.currency → currencies.code               |
| `22_0006` | 2026-03-22 | Add updated_at to countries, currencies, languages           |
