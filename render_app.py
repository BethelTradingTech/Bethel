"""Render entry point with critical route isolation.

The main application keeps its existing startup behavior. This module only
ensures the read-only MT5 connector router remains mounted even if an unrelated
optional onboarding integration fails while main.py is importing.
"""

from main import app
from api.mt5_ingest.routes import router as mt5_ingest_router


SNAPSHOT_PATH = "/connector/v1/snapshot"

if not any(getattr(route, "path", None) == SNAPSHOT_PATH for route in app.routes):
    app.include_router(mt5_ingest_router)
    print("MT5 Connector API Loaded (isolated Render entry point)")
