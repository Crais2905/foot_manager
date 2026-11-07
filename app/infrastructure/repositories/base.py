from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.application.exceptions import EntityNotFoundError
from app.db.base import Base
from app.infrastructure.mappers.mapping import IdentityMap

Model = TypeVar("Model", bound=Base)
Entity = TypeVar("Entity")


class BaseRepository(Generic[Model, Entity]):
    """Reads return None for absent IDs. Delete returns whether a row existed."""

    model_type: type[Model]
    id_column: ColumnElement[int]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _query(self) -> Select[Model]:
        return select(self.model_type)

    def _to_domain(self, model: Model, identities: IdentityMap) -> Entity:
        raise NotImplementedError

    async def _find_model(self, entity_id: int, *, for_update: bool = False) -> Model | None:
        query = self._query().where(self.id_column == entity_id)
        if for_update:
            query = query.with_for_update(of=self.id_column)
        return await self._session.scalar(query)

    async def _require_model(self, entity_id: int | None, *, for_update: bool = False) -> Model:
        model = None if entity_id is None else await self._find_model(entity_id, for_update=for_update)
        if model is None:
            raise EntityNotFoundError(f"{self.model_type.__name__} {entity_id} not found.")
        return model

    async def get_by_id(self, entity_id: int, *, for_update: bool = False) -> Entity | None:
        model = await self._find_model(entity_id, for_update=for_update)
        return self._to_domain(model, IdentityMap()) if model is not None else None

    async def _find_all(self, *conditions: ColumnElement[bool]) -> list[Entity]:
        models = await self._session.scalars(self._query().where(*conditions).order_by(self.id_column))
        identities = IdentityMap()
        return [self._to_domain(model, identities) for model in models]

    async def get_all(self) -> list[Entity]:
        return await self._find_all()

    async def add(self, entity: Entity) -> Entity:
        raise NotImplementedError

    async def delete(self, entity_id: int) -> bool:
        model = await self._find_model(entity_id, for_update=True)
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _require_all(ids: Sequence[int], found: set[int], label: str) -> None:
        missing = sorted(set(ids) - found)
        if missing:
            raise EntityNotFoundError(f"Missing {label}: {missing}.")
