"""Schema Nr. 1: Läufe, Spots, Ergebnisse, Kachel-Metadaten, API-Schlüssel.

Entwurf aus docs/plan.md (Etappe E). Große Binärdaten (GRIBs, Kacheln)
bleiben dateibasiert; hier liegen nur strukturierte Ergebnisse und
Metadaten. `cell_forecasts.values` sind die 28 Wertspalten einer
predictions.txt-Zeile (docs/predictions_format.md); `cell_id` ist die
Zeilennummer (0-basiert) — die Datei bleibt die Format-Referenz.
`accounts`/`api_keys` ersetzen die MySQL-Tabellen des Originals
(docs/web_inventory.md: Accounts, ApiKeys).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "forecast_runs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("gfs_cycle", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="running"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("exit_code", sa.Integer),
        sa.Column("code_git_sha", sa.Text),
        sa.Column("params", JSONB),
        sa.Column("error", sa.Text),
    )
    op.create_index("ix_forecast_runs_cycle", "forecast_runs", ["gfs_cycle"])

    op.create_table(
        "spots",
        sa.Column("id", sa.Integer, primary_key=True),  # fachliche ID des Bestands
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("lat", sa.Float(precision=53), nullable=False),
        sa.Column("lon", sa.Float(precision=53), nullable=False),
        sa.Column("nb_flights", sa.Integer),
        sa.Column("meta", JSONB),
    )

    op.create_table(
        "spot_forecasts",
        sa.Column("run_id", sa.BigInteger,
                  sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("spot_id", sa.Integer, sa.ForeignKey("spots.id"),
                  primary_key=True),
        sa.Column("valid_date", sa.Date, primary_key=True),
        sa.Column("flyability", sa.Float(precision=53), nullable=False),
    )
    op.create_index("ix_spot_forecasts_date", "spot_forecasts", ["valid_date"])

    op.create_table(
        "cell_forecasts",
        sa.Column("run_id", sa.BigInteger,
                  sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("valid_date", sa.Date, primary_key=True),
        sa.Column("cell_id", sa.Integer, primary_key=True),
        sa.Column("lat", sa.Float(precision=53), nullable=False),
        sa.Column("lon", sa.Float(precision=53), nullable=False),
        sa.Column("values", ARRAY(sa.Float(precision=53)), nullable=False),
    )

    op.create_table(
        "tile_sets",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.BigInteger,
                  sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("valid_date", sa.Date, nullable=False),
        sa.Column("zoom_min", sa.Integer, nullable=False),
        sa.Column("zoom_max", sa.Integer, nullable=False),
        sa.Column("base_path", sa.Text, nullable=False),
    )
    op.create_index("ix_tile_sets_run", "tile_sets", ["run_id"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.BigInteger,
                  sa.ForeignKey("accounts.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("api_key", sa.Text, nullable=False, unique=True),
        sa.Column("lat_lon_name", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade():
    for t in ("api_keys", "accounts", "tile_sets", "cell_forecasts",
              "spot_forecasts", "spots", "forecast_runs"):
        op.drop_table(t)
