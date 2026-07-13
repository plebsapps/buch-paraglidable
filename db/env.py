"""Alembic-Umgebung (Etappe E).

Migrationen sind reine SQL-/DDL-Skripte ohne Modell-Autogenerierung —
das Schema ist bewusst klein und wird von Hand versioniert (Schema Nr. 1
aufwärts, docs/plan.md). Die Verbindungs-URL kommt aus PARAGLIDABLE_DB_URL.
"""
import os

from alembic import context
from sqlalchemy import create_engine

DB_URL = os.environ.get("PARAGLIDABLE_DB_URL")
if not DB_URL:
    raise SystemExit("PARAGLIDABLE_DB_URL ist nicht gesetzt (siehe docker-compose.yml)")


def run_migrations_online():
    engine = create_engine(DB_URL)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
