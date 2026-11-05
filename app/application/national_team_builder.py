from app.domain.coach import Coach
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.domain.enums import PlayerPosition


class NationalTeamBuilder:
    def __init__(
        self,
        available_players: list[Player],
        player_teams: dict[Player, FootballTeam] | None = None,
    ) -> None:
        if not isinstance(available_players, list):
            raise TypeError("Список доступних гравців повинен бути list.")
        if any(not isinstance(player, Player) for player in available_players):
            raise TypeError("Список доступних гравців може містити лише Player.")
        if len(set(available_players)) != len(available_players):
            raise ValueError("Список доступних гравців не повинен містити повторів.")
        if player_teams is not None:
            if not isinstance(player_teams, dict):
                raise TypeError("Відображення гравців на клуби повинно бути словником.")
            for player, team in player_teams.items():
                if not isinstance(player, Player) or player not in available_players:
                    raise ValueError("Клуб можна вказати лише для доступного гравця.")
                if not isinstance(team, FootballTeam):
                    raise TypeError("Клуб повинен бути об'єктом FootballTeam.")

        self._available_players = available_players.copy()
        self._selected_players: list[Player] = []
        self._player_teams = player_teams.copy() if player_teams is not None else {}

    @property
    def player_teams(self) -> dict[Player, FootballTeam]:
        return self._player_teams.copy()

    @property
    def available_players(self) -> list[Player]:
        return self._available_players.copy()

    @property
    def selected_players(self) -> list[Player]:
        return self._selected_players.copy()

    def add_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("Можна вибирати лише об'єкти Player.")
        if player not in self.available_players:
            raise ValueError("Цього гравця немає серед доступних.")
        if player in self.selected_players:
            raise ValueError("Цей гравець уже вибраний.")
        self._selected_players.append(player)

    def remove_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("Потрібно передати об'єкт Player.")
        if player not in self.selected_players:
            raise ValueError("Цього гравця немає серед вибраних.")
        self._selected_players.remove(player)

    def get_selected_players(self) -> list[Player]:
        return self.selected_players.copy()

    def validate_squad(self) -> bool:
        players = self.selected_players
        if len(players) < NationalTeam.MIN_SQUAD_SIZE:
            return False
        if any(not isinstance(player, Player) for player in players):
            return False
        if len(set(players)) != len(players):
            return False
        if any(player not in self.available_players for player in players):
            return False
        if not any(player.position is PlayerPosition.GOALKEEPER for player in players):
            return False
        if len({player.shirt_number for player in players}) != len(players):
            return False
        return True

    def build(
        self,
        country: str,
        name: str,
        city: str,
        coach: Coach,
    ) -> NationalTeam:
        if not isinstance(coach, Coach):
            raise TypeError("Тренер повинен бути об'єктом Coach.")
        if not isinstance(country, str) or not country.strip():
            raise ValueError("Назва країни не може бути порожньою.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Назва збірної не може бути порожньою.")
        if not isinstance(city, str) or not city.strip():
            raise ValueError("Місто не може бути порожнім.")
        if not self.validate_squad():
            raise ValueError("Вибраний склад не відповідає вимогам збірної.")

        national_team = NationalTeam(name, city, coach, country)
        for player in self.selected_players:
            national_team.add_player(player)
        return national_team

    def clear(self) -> None:
        self._selected_players.clear()
