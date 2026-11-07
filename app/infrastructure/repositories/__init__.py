from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.repositories.people import CoachRepository, PlayerRepository
from app.infrastructure.repositories.teams import TeamRepository
from app.infrastructure.repositories.championships import ChampionshipRepository

__all__ = [
    "BaseRepository", "CoachRepository", "PlayerRepository", "TeamRepository",
    "ChampionshipRepository",
]
