"""Seed currencies, translations, and country-currency links.

Revision ID: 22_0002
Revises: 22_0001
Create Date: 2026-03-22
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "22_0002"
down_revision = "22_0001"
branch_labels = None
depends_on = None

# ------------------------------------------------------------------ #
#  Currencies (ISO 4217)
# ------------------------------------------------------------------ #

# (code, numeric, name, minor_unit, sort_order)
CURRENCIES = [
    # --- CIS / Central Asia ---
    ("UZS", "860", "Uzbekistan Sum", 2, 1),
    ("KZT", "398", "Tenge", 2, 2),
    ("TJS", "972", "Somoni", 2, 3),
    ("KGS", "417", "Som", 2, 4),
    ("TMT", "934", "Turkmenistan New Manat", 2, 5),
    ("RUB", "643", "Russian Ruble", 2, 6),
    ("BYN", "933", "Belarussian Ruble", 2, 7),
    ("UAH", "980", "Hryvnia", 2, 8),
    ("AZN", "944", "Azerbaijan Manat", 2, 9),
    ("GEL", "981", "Lari", 2, 10),
    ("AMD", "051", "Armenian Dram", 2, 11),
    ("MDL", "498", "Moldovan Leu", 2, 12),
    # --- Major trade partners ---
    ("CNY", "156", "Yuan Renminbi", 2, 13),
    ("TRY", "949", "Turkish Lira", 2, 14),
    ("KRW", "410", "Won", 0, 15),
    ("JPY", "392", "Yen", 0, 16),
    ("INR", "356", "Indian Rupee", 2, 17),
    ("AED", "784", "UAE Dirham", 2, 18),
    ("SAR", "682", "Saudi Riyal", 2, 19),
    ("USD", "840", "US Dollar", 2, 20),
    ("GBP", "826", "Pound Sterling", 2, 21),
    ("EUR", "978", "Euro", 2, 22),
    ("PLN", "985", "Zloty", 2, 23),
    ("AFN", "971", "Afghani", 2, 24),
]

# ------------------------------------------------------------------ #
#  Currency translations
# ------------------------------------------------------------------ #

# fmt: off
# (currency_code, lang_code, name)
CURRENCY_TRANSLATIONS = [
    # --- UZS ---
    ("UZS", "en",      "Uzbekistan Sum"),
    ("UZS", "ru",      "Узбекский сум"),
    ("UZS", "uz-Latn", "O'zbek so'mi"),
    ("UZS", "uz-Cyrl", "Ўзбек сўми"),
    # --- KZT ---
    ("KZT", "en",      "Tenge"),
    ("KZT", "ru",      "Тенге"),
    ("KZT", "uz-Latn", "Tenge"),
    ("KZT", "uz-Cyrl", "Тенге"),
    # --- TJS ---
    ("TJS", "en",      "Somoni"),
    ("TJS", "ru",      "Сомони"),
    ("TJS", "uz-Latn", "Somoni"),
    ("TJS", "uz-Cyrl", "Сомони"),
    # --- KGS ---
    ("KGS", "en",      "Som"),
    ("KGS", "ru",      "Сом"),
    ("KGS", "uz-Latn", "Som"),
    ("KGS", "uz-Cyrl", "Сом"),
    # --- TMT ---
    ("TMT", "en",      "Turkmenistan New Manat"),
    ("TMT", "ru",      "Туркменский манат"),
    ("TMT", "uz-Latn", "Turkman manati"),
    ("TMT", "uz-Cyrl", "Туркман манати"),
    # --- RUB ---
    ("RUB", "en",      "Russian Ruble"),
    ("RUB", "ru",      "Российский рубль"),
    ("RUB", "uz-Latn", "Rossiya rubli"),
    ("RUB", "uz-Cyrl", "Россия рубли"),
    # --- BYN ---
    ("BYN", "en",      "Belarussian Ruble"),
    ("BYN", "ru",      "Белорусский рубль"),
    ("BYN", "uz-Latn", "Belarus rubli"),
    ("BYN", "uz-Cyrl", "Беларус рубли"),
    # --- UAH ---
    ("UAH", "en",      "Hryvnia"),
    ("UAH", "ru",      "Гривна"),
    ("UAH", "uz-Latn", "Grivna"),
    ("UAH", "uz-Cyrl", "Гривна"),
    # --- AZN ---
    ("AZN", "en",      "Azerbaijan Manat"),
    ("AZN", "ru",      "Азербайджанский манат"),
    ("AZN", "uz-Latn", "Ozarbayjon manati"),
    ("AZN", "uz-Cyrl", "Озарбайжон манати"),
    # --- GEL ---
    ("GEL", "en",      "Lari"),
    ("GEL", "ru",      "Лари"),
    ("GEL", "uz-Latn", "Lari"),
    ("GEL", "uz-Cyrl", "Лари"),
    # --- AMD ---
    ("AMD", "en",      "Armenian Dram"),
    ("AMD", "ru",      "Армянский драм"),
    ("AMD", "uz-Latn", "Arman drami"),
    ("AMD", "uz-Cyrl", "Арман драми"),
    # --- MDL ---
    ("MDL", "en",      "Moldovan Leu"),
    ("MDL", "ru",      "Молдавский лей"),
    ("MDL", "uz-Latn", "Moldova leyi"),
    ("MDL", "uz-Cyrl", "Молдова лейи"),
    # --- CNY ---
    ("CNY", "en",      "Yuan Renminbi"),
    ("CNY", "ru",      "Китайский юань"),
    ("CNY", "uz-Latn", "Xitoy yuani"),
    ("CNY", "uz-Cyrl", "Хитой юани"),
    # --- TRY ---
    ("TRY", "en",      "Turkish Lira"),
    ("TRY", "ru",      "Турецкая лира"),
    ("TRY", "uz-Latn", "Turk lirasi"),
    ("TRY", "uz-Cyrl", "Турк лираси"),
    # --- KRW ---
    ("KRW", "en",      "Won"),
    ("KRW", "ru",      "Южнокорейская вона"),
    ("KRW", "uz-Latn", "Janubiy Koreya voni"),
    ("KRW", "uz-Cyrl", "Жанубий Корея вони"),
    # --- JPY ---
    ("JPY", "en",      "Yen"),
    ("JPY", "ru",      "Японская иена"),
    ("JPY", "uz-Latn", "Yaponiya iyenasi"),
    ("JPY", "uz-Cyrl", "Япония ийенаси"),
    # --- INR ---
    ("INR", "en",      "Indian Rupee"),
    ("INR", "ru",      "Индийская рупия"),
    ("INR", "uz-Latn", "Hind rupiyasi"),
    ("INR", "uz-Cyrl", "Ҳинд рупияси"),
    # --- AED ---
    ("AED", "en",      "UAE Dirham"),
    ("AED", "ru",      "Дирхам ОАЭ"),
    ("AED", "uz-Latn", "BAA dirhami"),
    ("AED", "uz-Cyrl", "БАА дирҳами"),
    # --- SAR ---
    ("SAR", "en",      "Saudi Riyal"),
    ("SAR", "ru",      "Саудовский риял"),
    ("SAR", "uz-Latn", "Saudiya riyoli"),
    ("SAR", "uz-Cyrl", "Саудия риёли"),
    # --- USD ---
    ("USD", "en",      "US Dollar"),
    ("USD", "ru",      "Доллар США"),
    ("USD", "uz-Latn", "AQSh dollari"),
    ("USD", "uz-Cyrl", "АҚШ доллари"),
    # --- GBP ---
    ("GBP", "en",      "Pound Sterling"),
    ("GBP", "ru",      "Фунт стерлингов"),
    ("GBP", "uz-Latn", "Funt sterling"),
    ("GBP", "uz-Cyrl", "Фунт стерлинг"),
    # --- EUR ---
    ("EUR", "en",      "Euro"),
    ("EUR", "ru",      "Евро"),
    ("EUR", "uz-Latn", "Yevro"),
    ("EUR", "uz-Cyrl", "Евро"),
    # --- PLN ---
    ("PLN", "en",      "Zloty"),
    ("PLN", "ru",      "Злотый"),
    ("PLN", "uz-Latn", "Zlotiy"),
    ("PLN", "uz-Cyrl", "Злотий"),
    # --- AFN ---
    ("AFN", "en",      "Afghani"),
    ("AFN", "ru",      "Афгани"),
    ("AFN", "uz-Latn", "Afgʻoni"),
    ("AFN", "uz-Cyrl", "Афғони"),
]
# fmt: on

# ------------------------------------------------------------------ #
#  Country-currency links
# ------------------------------------------------------------------ #

# (country_code, currency_code, is_primary)
COUNTRY_CURRENCIES = [
    # --- CIS / Central Asia ---
    ("UZ", "UZS", True),
    ("KZ", "KZT", True),
    ("TJ", "TJS", True),
    ("KG", "KGS", True),
    ("TM", "TMT", True),
    ("RU", "RUB", True),
    ("BY", "BYN", True),
    ("UA", "UAH", True),
    ("AZ", "AZN", True),
    ("GE", "GEL", True),
    ("AM", "AMD", True),
    ("MD", "MDL", True),
    # --- Major trade partners ---
    ("CN", "CNY", True),
    ("TR", "TRY", True),
    ("KR", "KRW", True),
    ("JP", "JPY", True),
    ("IN", "INR", True),
    ("AE", "AED", True),
    ("SA", "SAR", True),
    ("US", "USD", True),
    ("GB", "GBP", True),
    ("DE", "EUR", True),
    ("FR", "EUR", True),
    ("IT", "EUR", True),
    ("PL", "PLN", True),
    ("AF", "AFN", True),
]


def upgrade() -> None:
    """Seed currencies, translations, and country-currency links."""
    currency_t = sa.table(
        "currencies",
        sa.column("code", sa.String),
        sa.column("numeric", sa.String),
        sa.column("name", sa.String),
        sa.column("minor_unit", sa.SmallInteger),
        sa.column("sort_order", sa.SmallInteger),
    )
    tr_t = sa.table(
        "currency_translations",
        sa.column("id", sa.UUID),
        sa.column("currency_code", sa.String),
        sa.column("lang_code", sa.String),
        sa.column("name", sa.String),
    )
    link_t = sa.table(
        "country_currencies",
        sa.column("country_code", sa.String),
        sa.column("currency_code", sa.String),
        sa.column("is_primary", sa.Boolean),
    )

    # 1. Currencies
    for code, numeric, name, minor_unit, sort_order in CURRENCIES:
        op.execute(
            currency_t.insert().values(
                code=code,
                numeric=numeric,
                name=name,
                minor_unit=minor_unit,
                sort_order=sort_order,
            )
        )

    # 2. Currency translations (deterministic UUIDs)
    for currency_code, lang_code, name in CURRENCY_TRANSLATIONS:
        tr_id = uuid.uuid5(
            uuid.NAMESPACE_DNS, f"currency_tr.{currency_code}.{lang_code}",
        )
        op.execute(
            tr_t.insert().values(
                id=tr_id,
                currency_code=currency_code,
                lang_code=lang_code,
                name=name,
            )
        )

    # 3. Country-currency links
    for country_code, currency_code, is_primary in COUNTRY_CURRENCIES:
        op.execute(
            link_t.insert().values(
                country_code=country_code,
                currency_code=currency_code,
                is_primary=is_primary,
            )
        )


def downgrade() -> None:
    """Remove seed data (reverse order for FK safety)."""
    op.execute("DELETE FROM country_currencies")
    op.execute("DELETE FROM currency_translations")
    op.execute("DELETE FROM currencies")
