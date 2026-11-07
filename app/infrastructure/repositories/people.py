from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, func, select
from sqlalchemy.orm import raiseload

from app.db.models import CoachModel, FootballTeamModel, PlayerModel
from app.domain.coach import Coach
from app.domain.enums import PlayerPosition
from app.domain.player import Player
from app.infrastructure.mappers.mapping import IdentityMap, PersonMapper
from app.infrastructure.repositories.base import BaseRepository


class PlayerRepository(BaseRepository[PlayerModel, Player]):
    model_type = PlayerModel
    id_column = PlayerModel.__table__.c.id

    def _query(self) -> Select[PlayerModel]:
        return select(PlayerModel).options(raiseload("*"))

    def _to_domain(self, model: PlayerModel, identities: IdentityMap) -> Player:
        return cast(Player, PersonMapper.to_domain(model, identities))

    async def get_by_ids(self, player_ids: Sequence[int]) -> list[Player]:
        return await self._find_all(PlayerModel.id.in_(player_ids))

    async def get_by_name(self, name: str) -> list[Player]:
        full_name = func.concat(PlayerModel.first_name, " ", PlayerModel.last_name)
        return await self._find_all(full_name.icontains(name.strip(), autoescape=True))

    async def get_by_position(self, position: PlayerPosition) -> list[Player]:
        return await self._find_all(PlayerModel.position == position)

    async def add(self, entity: Player) -> Player:
        model = cast(PlayerModel, PersonMapper.to_model(entity))
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model, IdentityMap())

    async def update(self, entity: Player) -> Player:
        model = await self._require_model(entity.id, for_update=True)
        PersonMapper.copy_fields(entity, model)
        await self._session.flush()
        return self._to_domain(model, IdentityMap())


class CoachRepository(BaseRepository[CoachModel, Coach]):
    model_type = CoachModel
    id_column = CoachModel.__table__.c.id

    def _query(self) -> Select[CoachModel]:
        return select(CoachModel).options(raiseload("*"))

    def _to_domain(self, model: CoachModel, identities: IdentityMap) -> Coach:
        return cast(Coach, PersonMapper.to_domain(model, identities))

    async def get_by_last_name(self, last_name: str) -> list[Coach]:
        return await self._find_all(CoachModel.last_name.icontains(last_name.strip(), autoescape=True))

    async def is_assigned(self, coach_id: int) -> bool:
        return await self._session.scalar(
            select(FootballTeamModel.id).where(FootballTeamModel.coach_id == coach_id).limit(1)
        ) is not None

    async def add(self, entity: Coach) -> Coach:
        model = cast(CoachModel, PersonMapper.to_model(entity))
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model, IdentityMap())

    async def update(self, entity: Coach) -> Coach:
        model = await self._require_model(entity.id, for_update=True)
        PersonMapper.copy_fields(entity, model)
        await self._session.flush()
        return self._to_domain(model, IdentityMap())
