from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import config, get_database_url

ROOT = Path(__file__).resolve().parents[3]


def migrate(connection, revision="head", downgrade=False):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.attributes["connection"] = connection
    (command.downgrade if downgrade else command.upgrade)(cfg, revision)


@pytest_asyncio.fixture
async def db_connection():
    # Each test owns a unique schema. No drops/updates touch public or pre-existing data.
    url = config("TEST_DATABASE_URL", default="") or get_database_url()
    configured = (ROOT / ".env").exists() or any(
        config(key, default="") for key in
        ("TEST_DATABASE_URL", "DATABASE_URL", "DATABASE_ALEMBIC_URL", "DB_NAME")
    )
    if not configured:
        pytest.skip("Set TEST_DATABASE_URL or configure .env for PostgreSQL integration tests")
    engine = create_async_engine(url, poolclass=NullPool)
    schema = "fm_test_" + uuid4().hex
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET search_path TO "{schema}"'))
            await connection.commit()
            try:
                await connection.run_sync(migrate)
                await connection.commit()
                yield connection
            finally:
                await connection.rollback()
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                await connection.commit()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db(db_connection):
    async with AsyncSession(bind=db_connection, expire_on_commit=False) as session:
        yield session
        await session.rollback()
