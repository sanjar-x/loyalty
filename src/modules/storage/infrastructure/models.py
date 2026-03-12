# src/modules/storage/infrastructure/models.py

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StorageObject(Base):
    """
    Централизованный реестр всех файлов системы.
    Синхронизировано с метаданными S3-совместимого хранилища.
    """

    __tablename__ = "storage_objects"

    # 1. Идентификация
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        comment="Внутренний ID объекта в нашей БД",
    )
    bucket_name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        comment="Название бакета в S3",
    )
    # Полный путь к файлу в бакете (например, 'brands/123/logo.webp')
    object_key: Mapped[str] = mapped_column(
        String(1024),
        comment="Полный путь к файлу в бакете",
    )

    # 2. Версионирование (Если бакет поддерживает versioning)
    version_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="ID версии S3 объекта"
    )
    is_latest: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        comment="Является ли эта версия актуальной",
    )

    # 3. Физические характеристики
    size_bytes: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0"), comment="Размер файла в байтах"
    )
    # (полезно для проверки целостности)
    etag: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="MD5 хэш файла от S3",
    )

    # 4. Метаданные контента (HTTP Headers)  (например, 'image/jpeg', 'application/pdf')
    content_type: Mapped[str] = mapped_column(
        String(255),
        index=True,
        comment="MIME-тип",
    )
    content_encoding: Mapped[str | None] = mapped_column(String(255))
    cache_control: Mapped[str | None] = mapped_column(String(255))

    # 5. Системные поля
    owner_module: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        comment="Имя модуля-владельца (например, 'catalog', 'users'). Для аудита.",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Это поле мы обновляем, если файл перезаписали (и сменился ETag)
    last_modified_in_s3: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        comment="Время последней модификации на стороне самого S3",
    )

    __table_args__ = (
        Index(
            "uix_storage_active_object",
            "bucket_name",
            "object_key",
            unique=True,
            postgresql_where=text("is_latest = true"),
        ),
    )
