"""Schema Nr. 2: Fingerabdruck der Quelldatei am Kachel-Metadatensatz.

Grundlage des Vergleichsjobs (pipeline/verify_db_mirror.py, Etappe E):
predictions.txt ist je Tag flüchtig (/tmp, wird vom nächsten Tag
überschrieben). Der beim Spiegeln festgehaltene SHA-256 erlaubt den
Treue-Nachweis auch nachträglich — die Zellen werden aus der DB im
exakten Dateiformat re-serialisiert und gegen den Fingerabdruck
verglichen.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tile_sets", sa.Column("predictions_sha256", sa.Text))


def downgrade():
    op.drop_column("tile_sets", "predictions_sha256")
