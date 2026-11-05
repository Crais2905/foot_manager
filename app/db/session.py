from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from decouple import Config, RepositoryEnv
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_ENV = Path(__file__).resolve().parents[2] / ".env"
config = Config(RepositoryEnv(str(_ENV))) if _ENV.exists() else Config()


def get_database_url() -> str | URL:
    # Environment variables take precedence over .env; legacy configuration remains supported.
    explicit = config("DATABASE_URL", default="") or config("DATABASE_ALEMBIC_URL", default="")
    if explicit:
        return explicit
    return URL.create(
        "postgresql+asyncpg",
        username=config("DB_USER", default="postgres"),
        password=config("DB_PASSWORD", default=""),
        host=config("DB_HOST", default="localhost"),
        port=config("DB_PORT", default=5432, cast=int),
        database=config("DB_NAME", default="football_manager"),
    )


engine = create_async_engine(get_database_url(), pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Commit on success; rollback on error; always close the session."""
    async with SessionFactory() as session:
        async with session.begin():
            yield session


async def close_database() -> None:
    await engine.dispose()
