from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, select
from sqlalchemy.orm import Load, raiseload, selectinload

from app.application.exceptions import EntityConflictError, EntityNotFoundError
from app.db.models import (
    CoachModel, FootballTeamModel, NationalTeamModel, PlayerModel, SquadPlayerModel,
    TeamSquadModel,
)
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam
from app.infrastructure.mappers.mapping import IdentityMap, PersonMapper, TeamMapper
from app.infrastructure.repositories.base import BaseRepository


def team_loads() -> tuple[Load, Load]:
    return (
        cast(Load, selectinload(FootballTeamModel.coach)),
        cast(Load, selectinload(FootballTeamModel.squad).selectinload(
            TeamSquadModel.memberships
        ).selectinload(SquadPlayerModel.player)),
    )


class TeamRepository(BaseRepository[FootballTeamModel, FootballTeam]):
    model_type = FootballTeamModel
    id_column = FootballTeamModel.__table__.c.id

    def _query(self) -> Select[FootballTeamModel]:
        return select(FootballTeamModel).options(raiseload("*"), *team_loads())

    def _to_domain(self, model: FootballTeamModel, identities: IdentityMap) -> FootballTeam:
        return TeamMapper.to_domain(model, identities)

    async def get_by_name(self, name: str) -> list[FootballTeam]:
        return await self._find_all(FootballTeamModel.name.icontains(name.strip(), autoescape=True))

    async def get_by_city(self, city: str) -> list[FootballTeam]:
        return await self._find_all(FootballTeamModel.city.icontains(city.strip(), autoescape=True))

    @staticmethod
    def _club_memberships():
        return (
            select(SquadPlayerModel.player_id, TeamSquadModel.team_id)
            .join(TeamSquadModel, TeamSquadModel.id == SquadPlayerModel.squad_id)
            .join(FootballTeamModel.__table__, FootballTeamModel.__table__.c.id == TeamSquadModel.team_id)
            .where(FootballTeamModel.__table__.c.team_type == "football_team")
        )

    async def get_player_clubs(self, player_ids: Sequence[int] | None = None) -> dict[int, FootballTeam]:
        query = self._club_memberships()
        if player_ids is not None:
            query = query.where(SquadPlayerModel.player_id.in_(player_ids))
        rows = (await self._session.execute(query)).all()
        teams = await self._find_all(FootballTeamModel.id.in_({row.team_id for row in rows}))
        by_id = {team.id: team for team in teams}
        return {row.player_id: by_id[row.team_id] for row in rows if row.team_id in by_id}

    async def _resolve_people(self, team: FootballTeam, identities: IdentityMap) -> None:
        if team.coach.id is not None:
            coach = await self._session.get(CoachModel, team.coach.id, options=[raiseload("*")])
            if coach is None:
                raise EntityNotFoundError(f"Coach {team.coach.id} not found.")
            identities.put(team.coach, team.coach.id, coach)

        player_ids = [player.id for player in team if player.id is not None]
        if player_ids:
            query = select(PlayerModel).where(PlayerModel.id.in_(player_ids)).options(raiseload("*"))
            players = {model.id: model for model in await self._session.scalars(query)}
            self._require_all(player_ids, set(players), "players")
            for player in team:
                if player.id is not None:
                    identities.put(player, player.id, players[player.id])

        if not isinstance(team, NationalTeam):
            # Lock stable player rows before checking assignments, including when no assignment exists.
            club_ids = set(player_ids)
            for player in team:
                mapped = identities.get(player, player.id, PlayerModel)
                if mapped is not None and mapped.id is not None:
                    club_ids.add(mapped.id)
            if club_ids:
                table = PlayerModel.__table__
                await self._session.execute(
                    select(table.c.id).where(table.c.id.in_(club_ids))
                    .order_by(table.c.id).with_for_update()
                )
                query_clubs = self._club_memberships().where(SquadPlayerModel.player_id.in_(club_ids))
                if team.id is not None:
                    query_clubs = query_clubs.where(TeamSquadModel.team_id != team.id)
                if (await self._session.execute(query_clubs.limit(1))).first() is not None:
                    raise EntityConflictError("A player already belongs to another club.")

    async def _insert(self, entity: FootballTeam, identities: IdentityMap) -> FootballTeamModel:
        await self._resolve_people(entity, identities)
        model = TeamMapper.to_model(entity, identities)
        self._session.add(model)
        await self._session.flush()
        return model

    async def add(self, entity: FootballTeam) -> FootballTeam:
        model = await self._insert(entity, IdentityMap())
        return self._to_domain(model, IdentityMap())

    async def update(self, entity: FootballTeam) -> FootballTeam:
        model = await self._require_model(entity.id, for_update=True)
        if isinstance(entity, NationalTeam) != isinstance(model, NationalTeamModel):
            raise EntityConflictError("Cannot change the type of a team.")
        identities = IdentityMap()
        await self._resolve_people(entity, identities)
        TeamMapper.copy_fields(entity, model, identities)
        if model.squad is None:
            model.squad = TeamSquadModel(memberships=[])
        desired = {item.player.id: item.shirt_number for item in entity.squad.memberships
                   if item.player.id is not None}
        removed = [item for item in model.squad.memberships
                   if desired.get(item.player_id) != item.shirt_number]
        for row in removed:
            model.squad.memberships.remove(row)
        if removed:
            # Release the old numbers first so renumbering may reuse or swap them.
            await self._session.flush()
        existing_ids = {item.player_id for item in model.squad.memberships}
        for item in entity.squad.memberships:
            if item.player.id not in existing_ids:
                player = cast(PlayerModel, PersonMapper.to_model(item.player, identities))
                model.squad.memberships.append(
                    SquadPlayerModel(player=player, shirt_number=item.shirt_number)
                )
        await self._session.flush()
        return self._to_domain(model, IdentityMap())
