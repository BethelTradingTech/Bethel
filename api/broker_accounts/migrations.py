"""Small idempotent compatibility migration for existing broker_accounts tables."""

from sqlalchemy import inspect, text


def ensure_multiplatform_columns(engine):
    inspector = inspect(engine)
    if "broker_accounts" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("broker_accounts")}
    timestamp_type = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
    boolean_false = "FALSE" if engine.dialect.name == "postgresql" else "0"
    additions = {
        "platform": "VARCHAR(32) NOT NULL DEFAULT 'MT5'",
        "connection_method": "VARCHAR(32) NOT NULL DEFAULT 'LOCAL_TERMINAL'",
        "execution_mode": "VARCHAR(16) NOT NULL DEFAULT 'PAPER'",
        "last_verified_at": timestamp_type,
        "live_authorized": f"BOOLEAN NOT NULL DEFAULT {boolean_false}",
        "live_authorized_at": timestamp_type,
        "live_authorized_by": "VARCHAR(255)",
        "account_type": "VARCHAR(16) NOT NULL DEFAULT 'STANDARD'",
        "starting_capital_usd": "FLOAT",
        "capital_verified": f"BOOLEAN NOT NULL DEFAULT {boolean_false}",
    }

    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(
                    text(f"ALTER TABLE broker_accounts ADD COLUMN {name} {definition}")
                )
