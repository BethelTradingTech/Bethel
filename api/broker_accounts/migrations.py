"""Small idempotent compatibility migration for existing broker_accounts tables."""

from sqlalchemy import inspect, text


def ensure_multiplatform_columns(engine):
    inspector = inspect(engine)
    if "broker_accounts" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("broker_accounts")}
    additions = {
        "platform": "VARCHAR(32) NOT NULL DEFAULT 'MT5'",
        "connection_method": "VARCHAR(32) NOT NULL DEFAULT 'LOCAL_TERMINAL'",
        "execution_mode": "VARCHAR(16) NOT NULL DEFAULT 'PAPER'",
        "last_verified_at": "DATETIME",
        "live_authorized": "BOOLEAN NOT NULL DEFAULT 0",
        "live_authorized_at": "DATETIME",
        "live_authorized_by": "VARCHAR(255)",
        "account_type": "VARCHAR(16) NOT NULL DEFAULT 'STANDARD'",
        "starting_capital_usd": "FLOAT",
        "capital_verified": "BOOLEAN NOT NULL DEFAULT 0",
    }

    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(
                    text(f"ALTER TABLE broker_accounts ADD COLUMN {name} {definition}")
                )
