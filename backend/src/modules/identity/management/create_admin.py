"""Create the first admin identity.

Solves the bootstrap problem: system roles are seeded on startup,
but there is no API to create the very first admin without already
being an admin.

Usage:
    python -m src.modules.identity.management.create_admin \
        --email admin@example.com --password 'S3cret!' [--username admin]
"""

import argparse
import asyncio
import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.security.password import Argon2PasswordHasher
from src.modules.identity.domain.seed import ROLE_BY_NAME

logger = structlog.get_logger(__name__)

_INSERT_IDENTITY = text("""
    INSERT INTO identities (id, primary_auth_method, account_type, is_active)
    VALUES (:id, 'LOCAL', 'STAFF', true)
""")

_INSERT_CREDENTIALS = text("""
    INSERT INTO local_credentials (identity_id, email, password_hash)
    VALUES (:identity_id, :email, :password_hash)
""")

_INSERT_STAFF_MEMBER = text("""
    INSERT INTO staff_members (id, first_name, last_name, username, invited_by)
    VALUES (:id, 'Admin', '', :username, :id)
""")

_INSERT_IDENTITY_ROLE = text("""
    INSERT INTO identity_roles (identity_id, role_id)
    VALUES (:identity_id, :role_id)
    ON CONFLICT DO NOTHING
""")

_CHECK_EMAIL = text("""
    SELECT 1 FROM local_credentials WHERE email = :email
""")


async def create_admin(
    session_factory: async_sessionmaker[AsyncSession],
    email: str,
    password: str,
    username: str | None = None,
) -> uuid.UUID | None:
    """Create a STAFF identity with the 'admin' role.

    Returns the new identity ID, or None if the email already exists.
    """
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash(password)
    identity_id = uuid.uuid4()
    admin_role = ROLE_BY_NAME["admin"]

    async with session_factory() as session, session.begin():
        exists = (await session.execute(_CHECK_EMAIL, {"email": email})).scalar()
        if exists:
            logger.warning("admin.email_exists", email=email)
            return None

        await session.execute(_INSERT_IDENTITY, {"id": identity_id})
        await session.execute(
            _INSERT_CREDENTIALS,
            {
                "identity_id": identity_id,
                "email": email,
                "password_hash": password_hash,
            },
        )
        await session.execute(
            _INSERT_IDENTITY_ROLE,
            {"identity_id": identity_id, "role_id": admin_role.id},
        )
        await session.execute(
            _INSERT_STAFF_MEMBER,
            {"id": identity_id, "username": username},
        )

    logger.info("admin.created", identity_id=str(identity_id), email=email)
    return identity_id


if __name__ == "__main__":
    from src.bootstrap.container import create_container
    from src.bootstrap.logger import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(description="Create admin identity")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument(
        "--username", required=False, default=None, help="Admin username"
    )
    args = parser.parse_args()

    async def main() -> None:
        container = create_container()
        async with container() as app_scope:
            factory = await app_scope.get(async_sessionmaker[AsyncSession])
            result = await create_admin(
                factory, args.email, args.password, args.username
            )
        await container.close()
        if result:
            print(f"Admin created: {result}")
        else:
            print("Email already registered — no action taken.")

    asyncio.run(main())
