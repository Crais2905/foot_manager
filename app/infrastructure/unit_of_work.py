from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database_errors import log_database_error, translate_database_error
from app.db.session import SessionFactory
from app.infrastructure.repositories import (
    ChampionshipRepository, CoachRepository, PlayerRepository, TeamRepository,
)


class UnitOfWork:
    """Own a session. Exiting without an explicit commit rolls back."""

    def __init__(self, session_factory: Callable[[], AsyncSession] | None = None) -> None:
        self._factory = session_factory if session_factory is not None else SessionFactory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of Work is already active.")
        self._session = session = self._factory()
        self.players = PlayerRepository(session)
        self.coaches = CoachRepository(session)
        self.teams = TeamRepository(session)
        self.championships = ChampionshipRepository(session)
        return self

    def _active_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of Work is not active.")
        return self._session

    async def commit(self) -> None:
        await self._active_session().commit()

    async def rollback(self) -> None:
        await self._active_session().rollback()

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._active_session()
        try:
            try:
                await session.rollback()
            finally:
                await session.close()
        except Exception as cleanup_error:
            translated = translate_database_error(cleanup_error)
            if translated is None:
                raise
            log_database_error(cleanup_error, translated)
            if exc is None:
                raise translated from cleanup_error
        finally:
            self._session = None

        if exc is not None:
            translated = translate_database_error(exc)
            if translated is not None:
                log_database_error(exc, translated)
                raise translated from exc
