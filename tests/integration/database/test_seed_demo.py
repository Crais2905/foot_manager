import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.national_team import NationalTeam
from app.infrastructure.unit_of_work import UnitOfWork
from app.seed_demo import DEMO_NAME, seed_demo

pytestmark = pytest.mark.integration


async def test_seed_demo_populates_squads_and_can_be_rerun(db_connection):
    sessions = async_sessionmaker(bind=db_connection, expire_on_commit=False)

    def factory():
        return UnitOfWork(sessions)

    assert await seed_demo(factory)
    assert not await seed_demo(factory)
    async with factory() as work:
        assert len(await work.players.get_all()) == 48
        assert len(await work.coaches.get_all()) == 5
        teams = await work.teams.get_all()
        assert len(teams) == 5
        league, = await work.championships.get_all()
        assert league.name == DEMO_NAME
        assert [entry.position for entry in league] == [1, 2, 3, 4]
        national = next(team for team in teams if isinstance(team, NationalTeam))
        clubs = {member.player.id: member.shirt_number for team in teams if team is not national
                 for member in team.squad.memberships}
        assert len(national) == 11
        assert all(clubs[member.player.id] != member.shirt_number
                   for member in national.squad.memberships)
