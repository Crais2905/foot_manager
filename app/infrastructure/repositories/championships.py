from sqlalchemy import Select, select
from sqlalchemy.orm import raiseload, selectinload

from app.db.models import ChampionshipModel, ChampionshipParticipationModel, FootballTeamModel
from app.domain.championship import Championship
from app.infrastructure.mappers.mapping import ChampionshipMapper, IdentityMap
from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.repositories.teams import TeamRepository, team_loads


class ChampionshipRepository(BaseRepository[ChampionshipModel, Championship]):
    model_type = ChampionshipModel
    id_column = ChampionshipModel.__table__.c.id

    def _query(self) -> Select[ChampionshipModel]:
        return select(ChampionshipModel).options(
            raiseload("*"),
            selectinload(ChampionshipModel.participations)
            .selectinload(ChampionshipParticipationModel.team).options(*team_loads()),
        )

    def _to_domain(self, model: ChampionshipModel, identities: IdentityMap) -> Championship:
        return ChampionshipMapper.to_domain(model, identities)

    async def get_by_season(self, season: str) -> list[Championship]:
        return await self._find_all(ChampionshipModel.season == season.strip())

    async def _resolve_teams(self, championship: Championship) -> IdentityMap:
        teams = TeamRepository(self._session)
        identities = IdentityMap()
        ids = [entry.team.id for entry in championship if entry.team.id is not None]
        rows = await self._session.scalars(teams._query().where(FootballTeamModel.id.in_(ids)))
        models = {model.id: model for model in rows}
        self._require_all(ids, set(models), "teams")
        for entry in championship:
            team = entry.team
            if team.id is None:
                await teams._insert(team, identities)
            else:
                identities.put(team, team.id, models[team.id])
        return identities

    async def add(self, entity: Championship) -> Championship:
        model = ChampionshipMapper.to_model(entity, await self._resolve_teams(entity))
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model, IdentityMap())

    async def update(self, entity: Championship) -> Championship:
        model = await self._require_model(entity.id, for_update=True)
        identities = await self._resolve_teams(entity)
        model.name, model.country, model.season = entity.name, entity.country, entity.season
        entries = {entry.team.id: entry for entry in entity if entry.team.id is not None}
        changed_ids: dict[int, int] = {}
        for row in list(model.participations):
            entry = entries.get(row.team_id)
            if entry is None or entry.position != row.position:
                if entry is not None:
                    changed_ids[row.team_id] = row.id
                model.participations.remove(row)
        if changed_ids or self._session.dirty:
            await self._session.flush()
        existing = {row.team_id for row in model.participations}
        for entry in entity:
            if entry.team.id not in existing:
                row = ChampionshipMapper.participation_to_model(entry, identities)
                # IDs come from this aggregate, never from a detached replacement.
                if entry.team.id in changed_ids:
                    row.id = changed_ids[entry.team.id]
                elif entry.id is not None:
                    del row.id
                model.participations.append(row)
        await self._session.flush()
        return self._to_domain(model, IdentityMap())
