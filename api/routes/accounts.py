from fastapi import APIRouter, Depends

from api.auth.dependency import require_admin


router = APIRouter(prefix="/accounts", tags=["Trading Accounts"])


@router.get("/")
def get_accounts(_admin=Depends(require_admin)):
    """Legacy endpoint retained without fabricated account data."""
    return {"accounts": [], "source": "broker-accounts"}
