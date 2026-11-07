import asyncio
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.exceptions import (
    ApplicationValidationError, EntityConflictError, EntityNotFoundError,
)
from app.application.services import (
    ChampionshipService, CoachService, NationalTeamService, PlayerService, TeamService,
)
from app.db.models import PersonModel
from app.domain.championship import Championship
from app.domain.coach import Coach
from app.domain.enums import PlayerPosition
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.infrastructure.mappers import PersonMapper
from app.infrastructure.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration
DOB = date(2000, 1, 1)


@pytest.fixture
def factory(db_connection):
    sessions = async_sessionmaker(bind=db_connection, expire_on_commit=False)
    return lambda: UnitOfWork(sessions)


async def test_team_and_people_services_round_trip(factory):
    coaches, players, teams = CoachService(factory), PlayerService(factory), TeamService(factory)
    coach = await coaches.create_coach("John", "Smith", DOB, 2)
    replacement = await coaches.create_coach("Eve", "Jones", DOB, 4)
    assert [coach.id] == [c.id for c in await coaches.search_by_last_name("SMI")]
    team = await teams.create_team("Alpha", "Kyiv", coach.id)
    player = await players.create_player("Sam", "Jones", DOB, PlayerPosition.GOALKEEPER, 1)
    await teams.add_player(team.id, player.id, 12)
    assert [team.id] == [t.id for t in await teams.search_by_city("KY")]
    assert [team.id] == [t.id for t in await teams.search_by_name("ALP")]
    assert await teams.search_by_name("%") == []
    assert [player.id] == [p.id for p in await players.search_by_name("sam j")]
    assert [player.id] == [p.id for p in await players.get_by_position(PlayerPosition.GOALKEEPER)]
    assert await players.get_player(99999) is None
    with pytest.raises(EntityNotFoundError):
        await teams.add_player(team.id, 99999)
    with pytest.raises(EntityConflictError):
        await coaches.delete_coach(coach.id)
    second = await teams.create_team("Beta", "Lviv", coach.id)
    with pytest.raises(EntityConflictError):
        await teams.add_player(second.id, player.id)
    assert len(await teams.get_team(second.id)) == 0
    updated = await players.update_player(player.id, shirt_number=7)
    assert updated.shirt_number == 7
    assert (await teams.get_team(team.id)).squad.memberships[0].shirt_number == 12
    await teams.remove_player(team.id, player.id)
    await teams.add_player(second.id, player.id, 17)
    await teams.update_team(team.id, coach_id=replacement.id)
    await coaches.update_coach(replacement.id, experience_years=6)
    assert (await teams.get_team(team.id)).coach.experience_years == 6
    await players.delete_player(player.id)
    assert len(await teams.get_team(second.id)) == 0
    await teams.delete_team(second.id)
    await coaches.delete_coach(coach.id)
    assert await coaches.get_coach(coach.id) is None


async def test_championship_service_conflicts_and_sort(factory):
    coach = await CoachService(factory).create_coach("A", "Coach", DOB, 3)
    teams, championships = TeamService(factory), ChampionshipService(factory)
    a = await teams.create_team("A", "Kyiv", coach.id)
    b = await teams.create_team("B", "Kyiv", coach.id)
    cup = await championships.create_championship("Cup", "Ukraine", "2026")
    with pytest.raises(EntityConflictError):
        await championships.create_championship("Cup", "Ukraine", "2026")
    await championships.add_team(cup.id, a.id, 3)
    await championships.add_team(cup.id, b.id, 1)
    assert [b.id, a.id] == [t.id for t in await championships.sort_by_position(cup.id)]
    before = await championships.get_championship(cup.id)
    await championships.update_team_position(cup.id, a.id, 2)
    with pytest.raises(EntityConflictError):
        await championships.update_team_position(cup.id, b.id, 2)
    after = await championships.get_championship(cup.id)
    assert {p.team.id: p.position for p in after} == {a.id: 2, b.id: 1}
    assert {p.team.id: p.id for p in before} == {p.team.id: p.id for p in after}
    assert [cup.id] == [c.id for c in await championships.get_by_season("2026")]
    await championships.remove_team(cup.id, a.id)
    assert [b.id] == [t.id for t in await championships.sort_by_position(cup.id)]


async def test_national_team_keeps_club_numbers_and_validates_origins(factory):
    coaches, players = CoachService(factory), PlayerService(factory)
    teams, national = TeamService(factory), NationalTeamService(factory)
    coach = await coaches.create_coach("A", "Coach", DOB, 3)
    a = await teams.create_team("A", "Kyiv", coach.id)
    b = await teams.create_team("B", "Lviv", coach.id)
    ids = []
    for n in range(1, 13):
        position = PlayerPosition.GOALKEEPER if n == 1 else PlayerPosition.DEFENDER
        p = await players.create_player(f"P{n}", "Player", DOB, position, 1)
        await teams.add_player(a.id if n < 12 else b.id, p.id, n)
        ids.append(p.id)

    assert {p.id for p in await national.get_available_players("Ukraine")} == set(ids)
    with pytest.raises(ApplicationValidationError, match="two clubs"):
        await national.create_national_team(
            "Ukraine", "National", "Kyiv", coach.id, ids[:11],
            {pid: n for n, pid in enumerate(ids[:11], 20)},
        )
    with pytest.raises(ApplicationValidationError):
        await national.create_national_team(
            "Ukraine", "National", "Kyiv", coach.id, ids, dict.fromkeys(ids, 21),
        )
    numbers = {pid: n for n, pid in enumerate(ids, 20)}
    result = await national.create_national_team("Ukraine", "National", "Kyiv", coach.id, ids, numbers)
    restored = await national.get_national_team(result.id)
    assert isinstance(restored, NationalTeam)
    assert {m.player.id: m.shirt_number for m in restored.squad.memberships} == numbers
    assert len(await teams.get_team(a.id)) == 11
    with pytest.raises(ApplicationValidationError):
        await national.update_squad(result.id, ids[1:])
    await national.update_squad(result.id, ids, {ids[0]: 21, ids[1]: 20})
    restored = await national.get_national_team(result.id)
    assert {m.player.id: m.shirt_number for m in restored.squad.memberships}[ids[0]] == 21


async def test_uow_rollback_after_failed_roster_and_on_exit_without_commit(factory):
    with pytest.raises(ValueError, match="Номер 5"):
        async with factory() as work:
            coach = await work.coaches.add(Coach("A", "Coach", DOB, 1))
            team = await work.teams.add(FootballTeam("Team", "Kyiv", coach))
            player = await work.players.add(Player("A", "Player", DOB, PlayerPosition.FORWARD, 5))
            team.add_player(player)
            await work.teams.update(team)
            team.add_player(Player("B", "Player", DOB, PlayerPosition.FORWARD, 5))
    async with factory() as work:
        assert await work.teams.get_all() == []
        assert await work.players.get_all() == []
        assert await work.coaches.get_all() == []
        await work.coaches.add(Coach("A", "Coach", DOB, 1))
    async with factory() as work:
        assert await work.coaches.get_all() == []


async def test_repository_transient_graph_commit_and_team_delete(factory, db_connection):
    coach = Coach("A", "Coach", DOB, 1)
    player = Player("A", "Player", DOB, PlayerPosition.GOALKEEPER, 8)
    team = FootballTeam("A", "Kyiv", coach)
    national = NationalTeam("National", "Kyiv", coach, "Ukraine")
    team.add_player(player, 2)
    national.add_player(player, 4)
    cup = Championship("Cup", "Ukraine", "2026")
    cup.add_team(team, 1)
    cup.add_team(national, 2)
    async with factory() as work:
        result = await work.championships.add(cup)
        await work.commit()
    a, b = result.sort_by_position()
    assert a[0].id == b[0].id
    assert a.coach.id == b.coach.id
    async with async_sessionmaker(bind=db_connection)() as session:
        model = await session.get(PersonModel, a[0].id)
        assert isinstance(PersonMapper.to_domain(model), Player)
    async with factory() as work:
        assert await work.teams.delete(a.id)
        assert not await work.teams.delete(a.id)
        await work.commit()
    async with factory() as work:
        assert await work.players.get_by_id(a[0].id) is not None
        assert await work.coaches.get_by_id(a.coach.id) is not None
        assert [b.id] == [t.id for t in (await work.championships.get_by_id(result.id)).get_teams()]


async def test_concurrent_club_signings_allow_only_one_assignment(factory, db_connection):
    coach = await CoachService(factory).create_coach("A", "Coach", DOB, 3)
    teams = TeamService(factory)
    a = await teams.create_team("A", "Kyiv", coach.id)
    b = await teams.create_team("B", "Lviv", coach.id)
    player = await PlayerService(factory).create_player(
        "A", "Player", DOB, PlayerPosition.GOALKEEPER, 1,
    )
    schema = await db_connection.scalar(text("SELECT current_schema()"))
    await db_connection.commit()

    async def sign(team_id):
        async with db_connection.engine.connect() as connection:
            await connection.execute(
                text("SELECT set_config('search_path', :schema, false)"), {"schema": schema}
            )
            await connection.commit()
            sessions = async_sessionmaker(bind=connection, expire_on_commit=False)
            return await TeamService(lambda: UnitOfWork(sessions)).add_player(team_id, player.id)

    results = await asyncio.wait_for(
        asyncio.gather(sign(a.id), sign(b.id), return_exceptions=True), timeout=10,
    )
    assert sum(isinstance(result, FootballTeam) for result in results) == 1
    assert sum(isinstance(result, EntityConflictError) for result in results) == 1
    assert sum(len(team) for team in await teams.get_all_teams()) == 1
