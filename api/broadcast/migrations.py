"""Compatibility migration for existing broadcast controls; never enables X."""
from sqlalchemy import inspect, text


def ensure_x_column(engine):
    if "x_enabled" in {c["name"] for c in inspect(engine).get_columns("broadcast_control")}:
        return
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text(
                "ALTER TABLE broadcast_control ADD COLUMN IF NOT EXISTS "
                "x_enabled BOOLEAN NOT NULL DEFAULT FALSE"
            ))
        else:
            connection.execute(text(
                "ALTER TABLE broadcast_control ADD COLUMN x_enabled BOOLEAN NOT NULL DEFAULT FALSE"
            ))
