from datetime import date

from app.application.exceptions import EntityConflictError
from app.application.services._base import Service, logged_operation, require, validated
from app.domain.coach import Coach


class CoachService(Service):
    @logged_operation
    async def create_coach(
        self, first_name: str, last_name: str, date_of_birth: date, experience_years: int,
    ) -> Coach:
        async with self._uow() as work:
            entity = validated(Coach, first_name, last_name, date_of_birth, experience_years)
            saved = await work.coaches.add(entity)
            await work.commit()
            return saved

    async def get_coach(self, coach_id: int) -> Coach | None:
        async with self._uow() as work:
            return await work.coaches.get_by_id(coach_id)

    async def get_all_coaches(self) -> list[Coach]:
        async with self._uow() as work:
            return await work.coaches.get_all()

    async def search_by_last_name(self, last_name: str) -> list[Coach]:
        async with self._uow() as work:
            return await work.coaches.get_by_last_name(last_name)

    @logged_operation
    async def update_coach(
        self, coach_id: int, first_name: str | None = None, last_name: str | None = None, date_of_birth: date | None = None, experience_years: int | None = None,
    ) -> Coach:
        async with self._uow() as work:
            current = require(
                await work.coaches.get_by_id(coach_id, for_update=True), "Coach", coach_id,
            )
            entity = validated(
                Coach,
                current.first_name if first_name is None else first_name,
                current.last_name if last_name is None else last_name,
                current.date_of_birth if date_of_birth is None else date_of_birth,
                current.experience_years if experience_years is None else experience_years,
                id=coach_id,
            )
            saved = await work.coaches.update(entity)
            await work.commit()
            return saved

    @logged_operation
    async def delete_coach(self, coach_id: int) -> None:
        async with self._uow() as work:
            if await work.coaches.is_assigned(coach_id):
                raise EntityConflictError("Неможливо видалити тренера, оскільки він призначений команді. Спочатку призначте іншого тренера.")
            require(True if await work.coaches.delete(coach_id) else None, "Coach", coach_id)
            await work.commit()
