"""Legacy investor MT5 account routes - permanently disabled.

This module is intentionally inert. MT5 account linking and visibility are
handled only by the secured broker-account and investor-dashboard APIs.
Mounting this router exposes no endpoints.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/mt5-accounts", tags=["MT5 Accounts - Disabled"])

LEGACY_ROUTE_STATUS = "PERMANENTLY_DISABLED"
ACCESS_MODEL = "AUTHENTICATED_INVESTOR_OR_ADMIN_ONLY"
