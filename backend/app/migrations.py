"""Lightweight schema auto-heal, run once at startup.

This app deliberately avoids Alembic for simplicity, using
Base.metadata.create_all() instead — but create_all() only creates missing
*tables*, never adds missing *columns* to a table that already exists. Every
time a column is added to an existing model (e.g. Package.exception_notified_at),
an existing deployment's database is left on the old table shape until
something adds the column for it, and any query touching that table then
fails outright since SQLAlchemy selects every mapped column by default.

This walks each mapped table, diffs its columns against what's actually in
the database, and issues `ALTER TABLE ... ADD COLUMN` for anything missing.
Only safe for nullable columns with no uniqueness/foreign-key constraints —
which is the only kind of column this app has added post-launch so far.
"""

import logging

from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


def ensure_schema(engine: Engine, base: type[DeclarativeBase]) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # brand new table — create_all() already built it in full

            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=conn.dialect)
                logger.warning("adding missing column %s.%s (%s)", table.name, column.name, col_type)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))
