"""Seed languages and countries reference data.

Revision ID: 21_0004
Revises: 21_0003
Create Date: 2026-03-21
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "21_0004"
down_revision = "21_0003"
branch_labels = None
depends_on = None

# ------------------------------------------------------------------ #
#  Languages (IETF BCP 47)
# ------------------------------------------------------------------ #

LANGUAGES = [
    # code, iso639_1, iso639_2, iso639_3, script, name_en, name_native, direction, is_active, is_default, sort_order
    ("uz-Latn", "uz", "uzb", "uzb", "Latn", "Uzbek (Latin)", "O'zbekcha", "ltr", True, False, 1),
    ("uz-Cyrl", "uz", "uzb", "uzb", "Cyrl", "Uzbek (Cyrillic)", "Ўзбекча", "ltr", True, False, 2),
    ("ru", "ru", "rus", "rus", None, "Russian", "Русский", "ltr", True, True, 3),
    ("en", "en", "eng", "eng", None, "English", "English", "ltr", True, False, 4),
    ("kk", "kk", "kaz", "kaz", None, "Kazakh", "Қазақша", "ltr", False, False, 5),
    ("ky", "ky", "kir", "kir", None, "Kyrgyz", "Кыргызча", "ltr", False, False, 6),
    ("tg", "tg", "tgk", "tgk", None, "Tajik", "Тоҷикӣ", "ltr", False, False, 7),
    ("tk", "tk", "tuk", "tuk", None, "Turkmen", "Türkmençe", "ltr", False, False, 8),
    ("kaa", None, None, "kaa", "Latn", "Karakalpak", "Qaraqalpaqsha", "ltr", False, False, 9),
]

# ------------------------------------------------------------------ #
#  Countries (ISO 3166-1)
# ------------------------------------------------------------------ #

COUNTRIES = [
    # alpha2, alpha3, numeric, name
    # --- CIS / Central Asia ---
    ("UZ", "UZB", 860, "Uzbekistan"),
    ("KZ", "KAZ", 398, "Kazakhstan"),
    ("TJ", "TJK", 762, "Tajikistan"),
    ("KG", "KGZ", 417, "Kyrgyzstan"),
    ("TM", "TKM", 795, "Turkmenistan"),
    ("RU", "RUS", 643, "Russia"),
    ("BY", "BLR", 112, "Belarus"),
    ("UA", "UKR", 804, "Ukraine"),
    ("AZ", "AZE", 31, "Azerbaijan"),
    ("GE", "GEO", 268, "Georgia"),
    ("AM", "ARM", 51, "Armenia"),
    ("MD", "MDA", 498, "Moldova"),
    # --- Major trade partners ---
    ("CN", "CHN", 156, "China"),
    ("TR", "TUR", 792, "Turkey"),
    ("KR", "KOR", 410, "South Korea"),
    ("JP", "JPN", 392, "Japan"),
    ("IN", "IND", 356, "India"),
    ("AE", "ARE", 784, "United Arab Emirates"),
    ("SA", "SAU", 682, "Saudi Arabia"),
    ("US", "USA", 840, "United States"),
    ("GB", "GBR", 826, "United Kingdom"),
    ("DE", "DEU", 276, "Germany"),
    ("FR", "FRA", 250, "France"),
    ("IT", "ITA", 380, "Italy"),
    ("PL", "POL", 616, "Poland"),
    ("AF", "AFG", 4, "Afghanistan"),
]

# ------------------------------------------------------------------ #
#  Country translations
# ------------------------------------------------------------------ #

# fmt: off
COUNTRY_TRANSLATIONS = [
    # (country_code, lang_code, name, official_name)
    # --- Uzbekistan ---
    ("UZ", "en",      "Uzbekistan",     "Republic of Uzbekistan"),
    ("UZ", "ru",      "Узбекистан",     "Республика Узбекистан"),
    ("UZ", "uz-Latn", "O'zbekiston",    "O'zbekiston Respublikasi"),
    ("UZ", "uz-Cyrl", "Ўзбекистон",     "Ўзбекистон Республикаси"),
    # --- Kazakhstan ---
    ("KZ", "en",      "Kazakhstan",     "Republic of Kazakhstan"),
    ("KZ", "ru",      "Казахстан",      "Республика Казахстан"),
    ("KZ", "uz-Latn", "Qozog'iston",    "Qozog'iston Respublikasi"),
    ("KZ", "uz-Cyrl", "Қозоғистон",     "Қозоғистон Республикаси"),
    # --- Tajikistan ---
    ("TJ", "en",      "Tajikistan",     "Republic of Tajikistan"),
    ("TJ", "ru",      "Таджикистан",    "Республика Таджикистан"),
    ("TJ", "uz-Latn", "Tojikiston",     "Tojikiston Respublikasi"),
    # --- Kyrgyzstan ---
    ("KG", "en",      "Kyrgyzstan",     "Kyrgyz Republic"),
    ("KG", "ru",      "Кыргызстан",     "Кыргызская Республика"),
    ("KG", "uz-Latn", "Qirg'iziston",   "Qirg'iziston Respublikasi"),
    # --- Turkmenistan ---
    ("TM", "en",      "Turkmenistan",   None),
    ("TM", "ru",      "Туркменистан",   None),
    ("TM", "uz-Latn", "Turkmaniston",   None),
    # --- Russia ---
    ("RU", "en",      "Russia",         "Russian Federation"),
    ("RU", "ru",      "Россия",         "Российская Федерация"),
    ("RU", "uz-Latn", "Rossiya",        "Rossiya Federatsiyasi"),
    ("RU", "uz-Cyrl", "Россия",         "Россия Федерацияси"),
    # --- Belarus ---
    ("BY", "en",      "Belarus",        "Republic of Belarus"),
    ("BY", "ru",      "Беларусь",       "Республика Беларусь"),
    ("BY", "uz-Latn", "Belarus",        "Belarus Respublikasi"),
    # --- Ukraine ---
    ("UA", "en",      "Ukraine",        None),
    ("UA", "ru",      "Украина",        None),
    ("UA", "uz-Latn", "Ukraina",        None),
    # --- Azerbaijan ---
    ("AZ", "en",      "Azerbaijan",     "Republic of Azerbaijan"),
    ("AZ", "ru",      "Азербайджан",    "Азербайджанская Республика"),
    ("AZ", "uz-Latn", "Ozarbayjon",     "Ozarbayjon Respublikasi"),
    # --- Georgia ---
    ("GE", "en",      "Georgia",        None),
    ("GE", "ru",      "Грузия",         None),
    ("GE", "uz-Latn", "Gruziya",        None),
    # --- Armenia ---
    ("AM", "en",      "Armenia",        "Republic of Armenia"),
    ("AM", "ru",      "Армения",        "Республика Армения"),
    ("AM", "uz-Latn", "Armaniston",     "Armaniston Respublikasi"),
    # --- Moldova ---
    ("MD", "en",      "Moldova",        "Republic of Moldova"),
    ("MD", "ru",      "Молдова",        "Республика Молдова"),
    ("MD", "uz-Latn", "Moldova",        "Moldova Respublikasi"),
    # --- China ---
    ("CN", "en",      "China",          "People's Republic of China"),
    ("CN", "ru",      "Китай",          "Китайская Народная Республика"),
    ("CN", "uz-Latn", "Xitoy",          "Xitoy Xalq Respublikasi"),
    # --- Turkey ---
    ("TR", "en",      "Turkey",         "Republic of Turkiye"),
    ("TR", "ru",      "Турция",         "Турецкая Республика"),
    ("TR", "uz-Latn", "Turkiya",        "Turkiya Respublikasi"),
    # --- South Korea ---
    ("KR", "en",      "South Korea",    "Republic of Korea"),
    ("KR", "ru",      "Южная Корея",    "Республика Корея"),
    ("KR", "uz-Latn", "Janubiy Koreya", "Koreya Respublikasi"),
    # --- Japan ---
    ("JP", "en",      "Japan",          None),
    ("JP", "ru",      "Япония",         None),
    ("JP", "uz-Latn", "Yaponiya",       None),
    # --- India ---
    ("IN", "en",      "India",          "Republic of India"),
    ("IN", "ru",      "Индия",          "Республика Индия"),
    ("IN", "uz-Latn", "Hindiston",      "Hindiston Respublikasi"),
    # --- UAE ---
    ("AE", "en",      "United Arab Emirates", None),
    ("AE", "ru",      "ОАЭ",                  "Объединённые Арабские Эмираты"),
    ("AE", "uz-Latn", "BAA",                  "Birlashgan Arab Amirliklari"),
    # --- Saudi Arabia ---
    ("SA", "en",      "Saudi Arabia",   "Kingdom of Saudi Arabia"),
    ("SA", "ru",      "Саудовская Аравия", "Королевство Саудовская Аравия"),
    ("SA", "uz-Latn", "Saudiya Arabistoni", "Saudiya Arabistoni Qirolligi"),
    # --- USA ---
    ("US", "en",      "United States",  "United States of America"),
    ("US", "ru",      "США",            "Соединённые Штаты Америки"),
    ("US", "uz-Latn", "AQSh",           "Amerika Qo'shma Shtatlari"),
    # --- UK ---
    ("GB", "en",      "United Kingdom", "United Kingdom of Great Britain and Northern Ireland"),
    ("GB", "ru",      "Великобритания", "Соединённое Королевство Великобритании и Северной Ирландии"),
    ("GB", "uz-Latn", "Buyuk Britaniya", "Buyuk Britaniya va Shimoliy Irlandiya Qirolligi"),
    # --- Germany ---
    ("DE", "en",      "Germany",        "Federal Republic of Germany"),
    ("DE", "ru",      "Германия",       "Федеративная Республика Германия"),
    ("DE", "uz-Latn", "Germaniya",      "Germaniya Federativ Respublikasi"),
    # --- France ---
    ("FR", "en",      "France",         "French Republic"),
    ("FR", "ru",      "Франция",        "Французская Республика"),
    ("FR", "uz-Latn", "Fransiya",       "Fransiya Respublikasi"),
    # --- Italy ---
    ("IT", "en",      "Italy",          "Italian Republic"),
    ("IT", "ru",      "Италия",         "Итальянская Республика"),
    ("IT", "uz-Latn", "Italiya",        "Italiya Respublikasi"),
    # --- Poland ---
    ("PL", "en",      "Poland",         "Republic of Poland"),
    ("PL", "ru",      "Польша",         "Республика Польша"),
    ("PL", "uz-Latn", "Polsha",         "Polsha Respublikasi"),
    # --- Afghanistan ---
    ("AF", "en",      "Afghanistan",    "Islamic Emirate of Afghanistan"),
    ("AF", "ru",      "Афганистан",     "Исламский Эмират Афганистан"),
    ("AF", "uz-Latn", "Afgʻoniston",    "Afgʻoniston Islomiy Amirligi"),
]
# fmt: on


def upgrade() -> None:
    """Seed languages, countries, and country translations."""
    lang_t = sa.table(
        "languages",
        sa.column("code", sa.String),
        sa.column("iso639_1", sa.String),
        sa.column("iso639_2", sa.String),
        sa.column("iso639_3", sa.String),
        sa.column("script", sa.String),
        sa.column("name_en", sa.String),
        sa.column("name_native", sa.String),
        sa.column("direction", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_default", sa.Boolean),
        sa.column("sort_order", sa.SmallInteger),
    )
    country_t = sa.table(
        "countries",
        sa.column("alpha2", sa.String),
        sa.column("alpha3", sa.String),
        sa.column("numeric", sa.SmallInteger),
        sa.column("name", sa.String),
    )
    tr_t = sa.table(
        "country_translations",
        sa.column("id", sa.UUID),
        sa.column("country_code", sa.String),
        sa.column("lang_code", sa.String),
        sa.column("name", sa.String),
        sa.column("official_name", sa.String),
    )

    # 1. Languages
    for row in LANGUAGES:
        code, iso1, iso2, iso3, script, name_en, name_native, direction, active, default, sort = row
        op.execute(
            lang_t.insert().values(
                code=code,
                iso639_1=iso1,
                iso639_2=iso2,
                iso639_3=iso3,
                script=script,
                name_en=name_en,
                name_native=name_native,
                direction=direction,
                is_active=active,
                is_default=default,
                sort_order=sort,
            )
        )

    # 2. Countries
    for alpha2, alpha3, numeric, name in COUNTRIES:
        op.execute(
            country_t.insert().values(
                alpha2=alpha2, alpha3=alpha3, numeric=numeric, name=name,
            )
        )

    # 3. Country translations (deterministic UUIDs)
    for country_code, lang_code, name, official_name in COUNTRY_TRANSLATIONS:
        tr_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"country_tr.{country_code}.{lang_code}")
        op.execute(
            tr_t.insert().values(
                id=tr_id,
                country_code=country_code,
                lang_code=lang_code,
                name=name,
                official_name=official_name,
            )
        )


def downgrade() -> None:
    """Remove seed data (reverse order for FK safety)."""
    op.execute("DELETE FROM country_translations")
    op.execute("DELETE FROM countries")
    op.execute("DELETE FROM languages")
