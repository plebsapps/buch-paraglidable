"""Schema Nr. 3: genau ein API-Schlüssel je Konto.

Das Original ersetzte per MySQL "REPLACE INTO ApiKeys" den Schlüssel
eines Kontos; das PostgreSQL-Gegenstück ist ein Upsert über einen
Unique-Constraint auf account_id.
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_api_keys_account", "api_keys", ["account_id"])


def downgrade():
    op.drop_constraint("uq_api_keys_account", "api_keys")
