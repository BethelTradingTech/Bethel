"""Legacy portfolio routes - permanently disabled.

This module is intentionally inert. Historical portfolio data remains in the
database and is accessed only through authenticated investor/admin APIs.
Mounting this router exposes no endpoints.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["Portfolio - Disabled"])

LEGACY_ROUTE_STATUS = "PERMANENTLY_DISABLED"
ACCESS_MODEL = "AUTHENTICATED_INVESTOR_OR_ADMIN_ONLY"
