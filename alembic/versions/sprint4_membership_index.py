"""Index player memberships; demonstrates a reversible follow-up schema change."""
from alembic import op

revision = "sprint4_membership_index"
down_revision = "sprint4_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_squad_players_player_id", "squad_players", ["player_id"])


def downgrade() -> None:
    op.drop_index("ix_squad_players_player_id", table_name="squad_players")
