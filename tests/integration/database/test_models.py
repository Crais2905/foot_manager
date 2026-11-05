from datetime import date

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.db.models import (
    Base, PersonModel, PlayerModel, CoachModel, FootballTeamModel,
    NationalTeamModel, TeamSquadModel, SquadPlayerModel,
    ChampionshipModel, ChampionshipParticipationModel,
)
from app.db.enums import PlayerPositionEnum
from tests.integration.database.conftest import migrate

pytestmark = pytest.mark.integration


def person_kwargs():
    return dict(first_name="Andrii", last_name="Test", date_of_birth=date(2000, 1, 1))


def player(number=1):
    return PlayerModel(**person_kwargs(), position=PlayerPositionEnum.GOALKEEPER, shirt_number=number)


def team(national=False, name="Team"):
    kwargs = dict(name=name, city="Kyiv", coach=CoachModel(**person_kwargs(), experience_years=5))
    return NationalTeamModel(**kwargs, country="Ukraine") if national else FootballTeamModel(**kwargs)


def championship():
    return ChampionshipModel(name="League", country="Ukraine", season="2026")


async def count(db, model):
    return await db.scalar(select(func.count()).select_from(model))


async def test_inheritance_and_relationships_survive_reload(db):
    plain = PersonModel(**person_kwargs())
    p = player()
    club, national = team(), team(True)
    national.coach = club.coach
    club.squad.players.append(p)
    national.squad.memberships.append(SquadPlayerModel(player=p, shirt_number=12))
    league = championship()
    entry = ChampionshipParticipationModel(team=club, championship=league, position=1)
    db.add_all([plain, club, national, entry])
    await db.commit()
    ids = p.id, club.coach.id, national.id, club.id, league.id
    db.expunge_all()
    p2 = await db.get(PersonModel, ids[0])
    coach = await db.get(PersonModel, ids[1])
    n2 = await db.get(FootballTeamModel, ids[2])
    c2 = await db.get(FootballTeamModel, ids[3])
    l2 = await db.get(ChampionshipModel, ids[4])
    assert isinstance(p2, PlayerModel)
    assert isinstance(coach, CoachModel)
    assert isinstance(n2, NationalTeamModel)
    assert n2.country == "Ukraine"
    assert n2.name == "Team"
    assert c2.squad.players == n2.squad.players == [p2]
    assert {m.shirt_number for m in p2.squad_memberships} == {1, 12}
    assert len(coach.teams) == 2
    assert l2.participations[0].team is c2
    assert c2.participations[0].position == 1
    assert await count(db, PersonModel) == 3
    assert await count(db, PlayerModel) == await count(db, CoachModel) == 1
    assert await count(db, TeamSquadModel) == 2


@pytest.mark.parametrize("number", [0, 100, -1])
async def test_invalid_player_number(db, number):
    db.add(player(number))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_invalid_position(db):
    p = player()
    p.position = "unknown"
    db.add(p)
    with pytest.raises(StatementError):
        await db.flush()


async def test_negative_experience(db):
    db.add(CoachModel(**person_kwargs(), experience_years=-1))
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.parametrize("kind", ["team", "position", "nonpositive"])
async def test_participation_constraints(db, kind):
    club, league = team(), championship()
    db.add(ChampionshipParticipationModel(team=club, championship=league, position=1))
    await db.flush()
    other = club if kind == "team" else team(name="Other")
    position = 0 if kind == "nonpositive" else (2 if kind == "team" else 1)
    db.add(ChampionshipParticipationModel(team=other, championship=league, position=position))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_same_position_in_different_championships(db):
    club = team()
    leagues = [championship(), ChampionshipModel(name="Cup", country="Ukraine", season="2026")]
    db.add_all([ChampionshipParticipationModel(team=club, championship=l, position=1) for l in leagues])
    await db.flush()
    assert await count(db, ChampionshipParticipationModel) == 2


async def test_championship_unique(db):
    db.add_all([championship(), championship()])
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.parametrize("kind", ["number", "player", "invalid_number"])
async def test_squad_membership_constraints(db, kind):
    club, p = team(), player()
    club.squad.players.append(p)
    db.add(club)
    await db.flush()
    # Use SQL for duplicate PK to avoid ORM identity-map warnings.
    if kind == "player":
        with pytest.raises(IntegrityError):
            await db.execute(SquadPlayerModel.__table__.insert().values(
                squad_id=club.squad.id, player_id=p.id, shirt_number=2))
    else:
        club.squad.memberships.append(SquadPlayerModel(player=player(2), shirt_number=100 if kind == "invalid_number" else 1))
        with pytest.raises(IntegrityError):
            await db.flush()


async def test_same_number_in_distinct_squads_and_free_players(db):
    a, b = team(name="A"), team(name="B")
    a.squad.players.append(player(10))
    b.squad.players.append(player(10))
    db.add_all([a, b, player(10), player(10)])
    await db.flush()
    assert await count(db, PlayerModel) == 4


async def test_one_squad_per_team(db):
    club = team()
    db.add(club)
    await db.flush()
    db.add(TeamSquadModel(team_id=club.id))
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.parametrize("target,bulk", [("team", False), ("team", True), ("championship", False), ("championship", True), ("player", False), ("player", True)])
async def test_cascades_preserve_independent_entities(db, target, bulk):
    club, p, league = team(True), player(), championship()
    club.squad.players.append(p)
    db.add(ChampionshipParticipationModel(team=club, championship=league, position=1))
    await db.commit()
    target_class, target_id = {
        "team": (FootballTeamModel, club.id),
        "championship": (ChampionshipModel, league.id),
        # Joined inheritance: bulk delete must target the root person row.
        "player": (PersonModel, p.id),
    }[target]
    db.expunge_all()
    if bulk:
        await db.execute(delete(target_class).where(target_class.id == target_id))
    else:
        await db.delete(await db.get(target_class, target_id))
    await db.commit()
    assert await count(db, CoachModel) == 1
    assert await count(db, PlayerModel) == (0 if target == "player" else 1)
    assert await count(db, TeamSquadModel) == (0 if target == "team" else 1)
    assert await count(db, FootballTeamModel) == (0 if target == "team" else 1)
    assert await count(db, ChampionshipModel) == (0 if target == "championship" else 1)
    assert await count(db, ChampionshipParticipationModel) == (1 if target == "player" else 0)
    assert await count(db, SquadPlayerModel) == (1 if target == "championship" else 0)


@pytest.mark.parametrize("loaded", [True, False])
async def test_assigned_coach_cannot_be_deleted(db, loaded):
    club = team()
    db.add(club)
    await db.commit()
    coach_id = club.coach.id
    db.expunge_all()
    coach = await db.get(CoachModel, coach_id)
    if not loaded:
        db.expire(coach, ["teams"])
    with pytest.raises(IntegrityError):
        await db.delete(coach)
        await db.flush()
    await db.rollback()
    assert await count(db, FootballTeamModel) == 1


async def test_unassigned_coach_can_be_deleted(db):
    coach = CoachModel(**person_kwargs(), experience_years=0)
    db.add(coach)
    await db.commit()
    await db.delete(coach)
    await db.flush()
    assert await count(db, PersonModel) == 0


@pytest.mark.parametrize("field", ["name", "city", "coach_id"])
async def test_required_team_fields(db, field):
    club = team()
    if field == "coach_id":
        club.coach = None
    else:
        setattr(club, field, " ")
    db.add(club)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_country_nonempty(db):
    club = team(True)
    club.country = " "
    db.add(club)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_migration_upgrade_downgrade_and_metadata(db_connection):
    conn = db_connection
    def diff(connection):
        legacy = {"player", "coach", "football_team", "nation_team", "championship", "championship_participation"}
        ctx = MigrationContext.configure(connection, opts={
            "include_object": lambda obj, name, type_, reflected, compare_to:
                not (type_ == "table" and reflected and name in legacy),
            "compare_type": True,
        })
        return compare_metadata(ctx, Base.metadata)
    assert await conn.run_sync(diff) == []
    await conn.commit()
    await conn.run_sync(lambda c: migrate(c, "-1", downgrade=True))
    await conn.commit()
    indexes = await conn.run_sync(lambda c: inspect(c).get_indexes("squad_players"))
    assert not any(i["name"] == "ix_squad_players_player_id" for i in indexes)
    await conn.run_sync(migrate)
    await conn.commit()
    assert await conn.run_sync(diff) == []
    await conn.commit()
    await conn.run_sync(lambda c: migrate(c, "base", downgrade=True))
    await conn.commit()
    tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert tables == ["alembic_version"]
    await conn.run_sync(migrate)
    await conn.commit()
    assert await conn.run_sync(diff) == []


async def test_session_context_commits_and_rolls_back(db_connection, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.db import session as session_module
    monkeypatch.setattr(session_module, "SessionFactory", async_sessionmaker(
        bind=db_connection, expire_on_commit=False))
    async with session_module.get_session() as session:
        session.add(PersonModel(**person_kwargs()))
    assert (await db_connection.execute(text("SELECT count(*) FROM persons"))).scalar() == 1
    await db_connection.commit()
    with pytest.raises(RuntimeError, match="abort"):
        async with session_module.get_session() as session:
            session.add(PersonModel(**person_kwargs()))
            await session.flush()
            raise RuntimeError("abort")
    assert (await db_connection.execute(text("SELECT count(*) FROM persons"))).scalar() == 1


async def test_migration_keeps_legacy_records(db_connection):
    conn = db_connection
    await conn.run_sync(lambda c: migrate(c, "02af816be675", downgrade=True))
    await conn.execute(text("INSERT INTO championship (id, title, country, season) VALUES (1, 'Legacy', 'Ukraine', '2026')"))
    await conn.commit()
    await conn.run_sync(migrate)
    await conn.commit()
    assert (await conn.execute(text("SELECT title FROM championship WHERE id=1"))).scalar() == "Legacy"
    await conn.commit()
    await conn.run_sync(lambda c: migrate(c, "02af816be675", downgrade=True))
    await conn.commit()
    assert (await conn.execute(text("SELECT title FROM championship WHERE id=1"))).scalar() == "Legacy"
