import logging
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.exceptions import DatabaseError, EntityNotFoundError
from app.application.services import CoachService, NationalTeamService, TeamService
from app.domain.national_team import NationalTeam
from app.infrastructure.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_query_failure_is_logged_translated_and_rolled_back(db_connection, caplog):
    sessions = async_sessionmaker(bind=db_connection, expire_on_commit=False)
    with caplog.at_level(logging.ERROR, logger="app.infrastructure.database_errors"):
        with pytest.raises(DatabaseError):
            async with UnitOfWork(sessions) as work:
                await work._active_session().execute(text("SELECT missing_sprint10_column"))
    assert any("SQLSTATE=42703" in item.getMessage() and item.exc_info
               for item in caplog.records)
    async with UnitOfWork(sessions) as work:
        assert await work.players.get_all() == []


async def test_national_team_deletion_is_type_safe_and_preserves_player(db_connection):
    from app.domain.enums import PlayerPosition
    from app.domain.player import Player

    sessions = async_sessionmaker(bind=db_connection, expire_on_commit=False)

    def factory():
        return UnitOfWork(sessions)

    coach = await CoachService(factory).create_coach("A", "Coach", date(1980, 1, 1), 1)
    club = await TeamService(factory).create_team("Club", "Kyiv", coach.id)
    async with factory() as work:
        team = NationalTeam("National", "Kyiv", coach, "Ukraine")
        team.add_player(Player("A", "Player", date(2000, 1, 1), PlayerPosition.GOALKEEPER, 1))
        national = await work.teams.add(team)
        player_id = national[0].id
        await work.commit()

    service = NationalTeamService(factory)
    with pytest.raises(EntityNotFoundError):
        await service.delete_national_team(club.id)
    await service.delete_national_team(national.id)
    async with factory() as work:
        assert await work.teams.get_by_id(club.id) is not None
        assert await work.teams.get_by_id(national.id) is None
        assert await work.players.get_by_id(player_id) is not None
