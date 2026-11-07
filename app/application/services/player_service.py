from datetime import date

from app.application.services._base import Service, logged_operation, require, validated
from app.domain.player import Player
from app.domain.enums import PlayerPosition


class PlayerService(Service):
    @logged_operation
    async def create_player(
        self, first_name: str, last_name: str, date_of_birth: date, position: PlayerPosition, shirt_number: int,
    ) -> Player:
        async with self._uow() as work:
            entity = validated(Player, first_name, last_name, date_of_birth, position, shirt_number)
            saved = await work.players.add(entity)
            await work.commit()
            return saved

    async def get_player(self, player_id: int) -> Player | None:
        async with self._uow() as work:
            return await work.players.get_by_id(player_id)

    async def get_all_players(self) -> list[Player]:
        async with self._uow() as work:
            return await work.players.get_all()

    async def get_unassigned_players(self) -> list[Player]:
        async with self._uow() as work:
            clubs = await work.teams.get_player_clubs()
            return [player for player in await work.players.get_all() if player.id not in clubs]

    async def search_by_name(self, name: str) -> list[Player]:
        async with self._uow() as work:
            return await work.players.get_by_name(name)

    async def get_by_position(self, position: PlayerPosition) -> list[Player]:
        async with self._uow() as work:
            return await work.players.get_by_position(position)

    @logged_operation
    async def update_player(
        self, player_id: int, first_name: str | None = None, last_name: str | None = None, date_of_birth: date | None = None, position: PlayerPosition | None = None, shirt_number: int | None = None,
    ) -> Player:
        async with self._uow() as work:
            current = require(
                await work.players.get_by_id(player_id, for_update=True), "Player", player_id,
            )
            entity = validated(
                Player,
                current.first_name if first_name is None else first_name,
                current.last_name if last_name is None else last_name,
                current.date_of_birth if date_of_birth is None else date_of_birth,
                current.position if position is None else position,
                current.shirt_number if shirt_number is None else shirt_number,
                id=player_id,
            )
            saved = await work.players.update(entity)
            await work.commit()
            return saved

    @logged_operation
    async def delete_player(self, player_id: int) -> None:
        async with self._uow() as work:
            require(True if await work.players.delete(player_id) else None, "Player", player_id)
            await work.commit()
