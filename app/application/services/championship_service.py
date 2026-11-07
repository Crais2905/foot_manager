from dataclasses import dataclass
from typing import Literal

from app.application.services._base import Service, logged_operation, require, validated
from app.domain.championship import Championship
from app.domain.football_team import FootballTeam


@dataclass(frozen=True)
class Standing:
    team: FootballTeam
    position: int


class ChampionshipService(Service):
    @logged_operation
    async def create_championship(self, name: str, country: str, season: str) -> Championship:
        async with self._uow() as work:
            saved = await work.championships.add(validated(Championship, name, country, season))
            await work.commit()
            return saved

    async def get_championship(self, championship_id: int) -> Championship | None:
        async with self._uow() as work:
            return await work.championships.get_by_id(championship_id)

    async def get_all_championships(self) -> list[Championship]:
        async with self._uow() as work:
            return await work.championships.get_all()

    async def get_by_season(self, season: str) -> list[Championship]:
        async with self._uow() as work:
            return await work.championships.get_by_season(season)

    @logged_operation
    async def add_team(self, championship_id: int, team_id: int, position: int) -> None:
        async with self._uow() as work:
            championship = require(
                await work.championships.get_by_id(championship_id, for_update=True),
                "Championship", championship_id,
            )
            team = require(await work.teams.get_by_id(team_id), "Team", team_id)
            validated(championship.add_team, team, position)
            await work.championships.update(championship)
            await work.commit()

    @logged_operation
    async def remove_team(self, championship_id: int, team_id: int) -> None:
        async with self._uow() as work:
            championship = require(
                await work.championships.get_by_id(championship_id, for_update=True),
                "Championship", championship_id,
            )
            entry = require(next((p for p in championship if p.team.id == team_id), None),
                            "Participation for team", team_id)
            championship.remove_team(entry.team)
            await work.championships.update(championship)
            await work.commit()

    @logged_operation
    async def update_team_position(
        self, championship_id: int, team_id: int, new_position: int
    ) -> None:
        async with self._uow() as work:
            championship = require(
                await work.championships.get_by_id(championship_id, for_update=True),
                "Championship", championship_id,
            )
            entry = require(next((p for p in championship if p.team.id == team_id), None),
                            "Participation for team", team_id)
            validated(entry.set_position, new_position)
            await work.championships.update(championship)
            await work.commit()

    async def sort_by_position(self, championship_id: int) -> list[FootballTeam]:
        return [row.team for row in await self.get_standings(championship_id)]

    async def sort_by_coach(self, championship_id: int) -> list[FootballTeam]:
        return [row.team for row in await self.get_standings(championship_id, order="coach")]

    async def get_teams_by_position_range(
        self, championship_id: int, start: int, end: int,
    ) -> list[FootballTeam]:
        rows = await self.get_standings(championship_id, position_range=(start, end))
        return [row.team for row in rows]

    @logged_operation
    async def update_championship(
        self, championship_id: int, name: str, country: str, season: str,
    ) -> Championship:
        async with self._uow() as work:
            championship = require(
                await work.championships.get_by_id(championship_id, for_update=True),
                "Championship", championship_id,
            )
            details = validated(Championship, name, country, season)
            championship.name = details.name
            championship.country = details.country
            championship.season = details.season
            saved = await work.championships.update(championship)
            await work.commit()
            return saved

    async def get_standings(
        self, championship_id: int, *, order: Literal["position", "coach"] = "position",
        position_range: tuple[int, int] | None = None,
    ) -> list[Standing]:
        championship = require(await self.get_championship(championship_id),
                               "Championship", championship_id)
        positions = {entry.team: entry.position for entry in championship}
        if position_range is not None:
            teams = validated(championship.get_teams_by_position_range, *position_range)
        elif order == "coach":
            teams = championship.sort_by_coach()
        else:
            teams = championship.sort_by_position()
        return [Standing(team, positions[team]) for team in teams]

    @logged_operation
    async def delete_championship(self, championship_id: int) -> None:
        async with self._uow() as work:
            require(True if await work.championships.delete(championship_id) else None,
                    "Championship", championship_id)
            await work.commit()
