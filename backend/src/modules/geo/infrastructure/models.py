"""ORM models for the Geo bounded context.

Maps geographic and locale reference data to PostgreSQL:

* **Country** (ISO 3166-1) + translations
* **Currency** (ISO 4217) + translations + country bridge
* **Language** (IETF BCP 47 / ISO 639)
* **Subdivision** (ISO 3166-2) + translations
* **SubdivisionCategory** + translations

These models belong to the infrastructure layer and must never leak
into the domain or application layers -- repositories translate between
ORM and domain value objects using the Data Mapper pattern.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base

# ===================================================================
#  Language (IETF BCP 47)
# ===================================================================


class LanguageModel(Base):
    """Persistent representation of a supported language / locale.

    Uses the IETF BCP 47 tag as a **natural primary key**.
    """

    __tablename__ = "languages"

    # -- identification ------------------------------------------------ #

    code: Mapped[str] = mapped_column(
        String(12),
        primary_key=True,
        comment="IETF BCP 47 tag (e.g. uz-Latn, en, ru)",
    )
    iso639_1: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        comment="ISO 639-1 alpha-2 (e.g. uz, ru, en)",
    )
    iso639_2: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO 639-2/T alpha-3 (e.g. uzb, rus, eng)",
    )
    iso639_3: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO 639-3 alpha-3 (e.g. uzb, kaa)",
    )
    script: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
        comment="ISO 15924 script code (e.g. Latn, Cyrl, Arab)",
    )

    # -- display ------------------------------------------------------- #

    name_en: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="English name (e.g. Uzbek (Latin))",
    )
    name_native: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Endonym (e.g. Русский)",
    )
    direction: Mapped[str] = mapped_column(
        String(3),
        default="ltr",
        server_default="ltr",
        comment="Text direction: ltr or rtl",
    )

    # -- flags --------------------------------------------------------- #

    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        comment="Available for selection in UI",
    )
    is_default: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        comment="Default fallback language (exactly one True)",
    )
    sort_order: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        server_default="0",
        comment="Display order in language pickers",
    )

    # -- audit --------------------------------------------------------- #

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modification timestamp",
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        Index("ix_languages_iso639_1", "iso639_1"),
        Index("ix_languages_active", "is_active"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Language {self.code}>"


# ===================================================================
#  Country (ISO 3166-1)
# ===================================================================


class CountryModel(Base):
    """Persistent representation of a country per ISO 3166-1.

    Uses the **Alpha-2 code as a natural primary key**.

    All relationships use ``lazy="raise"`` to prevent accidental
    eager loading; use explicit ``selectinload()`` when needed.
    """

    __tablename__ = "countries"

    alpha2: Mapped[str] = mapped_column(
        String(2),
        primary_key=True,
        comment="ISO 3166-1 Alpha-2 code (e.g. KZ)",
    )
    alpha3: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        unique=True,
        comment="ISO 3166-1 Alpha-3 code (e.g. KAZ)",
    )
    numeric: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        unique=True,
        comment="ISO 3166-1 Numeric code, zero-padded (e.g. 398)",
    )

    # -- audit --------------------------------------------------------- #

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modification timestamp",
    )

    # -- relationships ------------------------------------------------- #

    translations: Mapped[list[CountryTranslationModel]] = relationship(
        back_populates="country",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    currency_links: Mapped[list[CountryCurrencyModel]] = relationship(
        back_populates="country",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    subdivisions: Mapped[list[SubdivisionModel]] = relationship(
        back_populates="country",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class CountryTranslationModel(Base):
    """Country name in a specific language.

    Natural key: ``(country_code, lang_code)``.
    """

    __tablename__ = "country_translations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate primary key",
    )
    country_code: Mapped[str] = mapped_column(
        String(2),
        ForeignKey("countries.alpha2", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> countries.alpha2",
    )
    lang_code: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("languages.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> languages.code (IETF BCP 47)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Translated short name (e.g. Россия)",
    )
    official_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Official name if different from short",
    )

    # -- relationships ------------------------------------------------- #

    country: Mapped[CountryModel] = relationship(
        back_populates="translations", lazy="joined"
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        UniqueConstraint("country_code", "lang_code", name="uq_country_lang"),
        Index("ix_country_tr_lang", "lang_code"),
        Index("ix_country_tr_name", "name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CountryTranslation {self.country_code}/{self.lang_code}>"


# ===================================================================
#  Currency (ISO 4217)
# ===================================================================


class CurrencyModel(Base):
    """Persistent representation of a currency per ISO 4217.

    Uses the **Alpha-3 code as a natural primary key**.
    """

    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(
        String(3),
        primary_key=True,
        comment="ISO 4217 alpha-3 code (e.g. UZS, USD, EUR)",
    )
    numeric: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        unique=True,
        comment="ISO 4217 numeric code, zero-padded (e.g. 840, 978)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Common English name (e.g. US Dollar)",
    )
    minor_unit: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Decimal places (2 for USD, 0 for JPY, 3 for BHD, NULL for XXX)",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        comment="Available for selection in UI / API",
    )
    sort_order: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        server_default="0",
        comment="Display order in currency pickers",
    )

    # -- audit --------------------------------------------------------- #

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modification timestamp",
    )

    # -- relationships ------------------------------------------------- #

    translations: Mapped[list[CurrencyTranslationModel]] = relationship(
        back_populates="currency",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    country_links: Mapped[list[CountryCurrencyModel]] = relationship(
        back_populates="currency",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        Index("ix_currencies_numeric", "numeric"),
        Index("ix_currencies_active", "is_active"),
        Index("ix_currencies_name", "name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Currency {self.code}>"


class CurrencyTranslationModel(Base):
    """Currency name in a specific language.

    Natural key: ``(currency_code, lang_code)``.
    """

    __tablename__ = "currency_translations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate primary key",
    )
    currency_code: Mapped[str] = mapped_column(
        String(3),
        ForeignKey("currencies.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> currencies.code",
    )
    lang_code: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("languages.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> languages.code (IETF BCP 47)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Translated currency name (e.g. Доллар США)",
    )

    # -- relationships ------------------------------------------------- #

    currency: Mapped[CurrencyModel] = relationship(
        back_populates="translations", lazy="joined"
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        UniqueConstraint("currency_code", "lang_code", name="uq_currency_lang"),
        Index("ix_currency_tr_lang", "lang_code"),
        Index("ix_currency_tr_name", "name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CurrencyTranslation {self.currency_code}/{self.lang_code}>"


class CountryCurrencyModel(Base):
    """Bridge table linking countries to their currencies (M:N).

    Composite primary key: ``(country_code, currency_code)``.
    """

    __tablename__ = "country_currencies"

    country_code: Mapped[str] = mapped_column(
        String(2),
        ForeignKey("countries.alpha2", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> countries.alpha2 (ISO 3166-1)",
    )
    currency_code: Mapped[str] = mapped_column(
        String(3),
        ForeignKey("currencies.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> currencies.code (ISO 4217)",
    )
    is_primary: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        comment="Whether this is the country's primary/official currency",
    )

    # -- relationships ------------------------------------------------- #

    country: Mapped[CountryModel] = relationship(
        back_populates="currency_links", lazy="joined"
    )
    currency: Mapped[CurrencyModel] = relationship(
        back_populates="country_links", lazy="joined"
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        PrimaryKeyConstraint("country_code", "currency_code"),
        Index("ix_country_currencies_currency_code", "currency_code"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CountryCurrency {self.country_code}/{self.currency_code}>"


# ===================================================================
#  Subdivision Category (ISO 3166-2 type labels)
# ===================================================================


class SubdivisionCategoryModel(Base):
    """ISO 3166-2 subdivision type (e.g. PROVINCE, EMIRATE)."""

    __tablename__ = "subdivision_categories"

    code: Mapped[str] = mapped_column(
        String(60),
        primary_key=True,
        comment="ISO category token (e.g. PROVINCE, EMIRATE)",
    )
    sort_order: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        server_default="0",
        comment="Display order in category filters",
    )

    # -- relationships ------------------------------------------------- #

    translations: Mapped[list[SubdivisionCategoryTranslationModel]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SubdivisionCategory {self.code}>"


class SubdivisionCategoryTranslationModel(Base):
    """Category label in a specific language.

    Natural key: ``(category_code, lang_code)``.
    """

    __tablename__ = "subdivision_category_translations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate primary key",
    )
    category_code: Mapped[str] = mapped_column(
        String(60),
        ForeignKey("subdivision_categories.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> subdivision_categories.code",
    )
    lang_code: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("languages.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> languages.code (IETF BCP 47)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Translated label (e.g. Область, Province)",
    )

    # -- relationships ------------------------------------------------- #

    category: Mapped[SubdivisionCategoryModel] = relationship(
        back_populates="translations", lazy="joined"
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        UniqueConstraint("category_code", "lang_code", name="uq_sub_category_lang"),
        Index("ix_sub_cat_tr_lang", "lang_code"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SubdivisionCategoryTranslation {self.category_code}/{self.lang_code}>"


# ===================================================================
#  Subdivision (ISO 3166-2)
# ===================================================================


class SubdivisionModel(Base):
    """ISO 3166-2 administrative subdivision.

    Uses the **full ISO 3166-2 code as a natural primary key**
    (e.g. ``"RU-MOW"``, ``"UZ-TO"``).
    """

    __tablename__ = "subdivisions"

    code: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="ISO 3166-2 code (e.g. RU-MOW, UZ-TO)",
    )
    country_code: Mapped[str] = mapped_column(
        String(2),
        ForeignKey("countries.alpha2", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> countries.alpha2",
    )
    category_code: Mapped[str] = mapped_column(
        String(60),
        ForeignKey("subdivision_categories.code", ondelete="RESTRICT"),
        nullable=False,
        comment="FK -> subdivision_categories.code",
    )
    parent_code: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("subdivisions.code", ondelete="SET NULL"),
        nullable=True,
        comment="Parent subdivision for nested levels",
    )
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Centroid latitude (WGS 84)",
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Centroid longitude (WGS 84)",
    )
    sort_order: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        server_default="0",
        comment="Display order within parent country",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        comment="Soft-delete / visibility flag",
    )

    # -- relationships ------------------------------------------------- #

    country: Mapped[CountryModel] = relationship(
        back_populates="subdivisions", lazy="joined"
    )
    category: Mapped[SubdivisionCategoryModel] = relationship(lazy="joined")
    parent: Mapped[SubdivisionModel | None] = relationship(
        remote_side=[code], lazy="select"
    )
    translations: Mapped[list[SubdivisionTranslationModel]] = relationship(
        back_populates="subdivision",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        Index("ix_subdivisions_country", "country_code"),
        Index("ix_subdivisions_category", "country_code", "category_code"),
        Index("ix_subdivisions_parent", "parent_code"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Subdivision {self.code}>"


class SubdivisionTranslationModel(Base):
    """Subdivision name in a specific language.

    Natural key: ``(subdivision_code, lang_code)``.
    """

    __tablename__ = "subdivision_translations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate primary key",
    )
    subdivision_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("subdivisions.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> subdivisions.code",
    )
    lang_code: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("languages.code", ondelete="CASCADE"),
        nullable=False,
        comment="FK -> languages.code (IETF BCP 47)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Translated name (e.g. Москва, Moscow)",
    )
    official_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Full official name if different from short",
    )
    local_variant: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Alternative / local name (e.g. Yugra for KhMAO)",
    )

    # -- relationships ------------------------------------------------- #

    subdivision: Mapped[SubdivisionModel] = relationship(
        back_populates="translations", lazy="joined"
    )

    # -- table-level constraints --------------------------------------- #

    __table_args__ = (
        UniqueConstraint("subdivision_code", "lang_code", name="uq_subdivision_lang"),
        Index("ix_sub_tr_lang", "lang_code"),
        Index("ix_sub_tr_name", "name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SubdivisionTranslation {self.subdivision_code}/{self.lang_code}>"
