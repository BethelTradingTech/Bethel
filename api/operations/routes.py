from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.auth.dependency import require_admin
from api.database import get_db
from api.operations.backup import (
    BACKUP_DIRECTORY,
    create_backup,
    verify_backup,
)
from api.operations.models import BackupRecord, SecurityEvent


router = APIRouter(prefix="/admin/operations", tags=["Operations and Security"])


@router.get("/backups")
def list_backups(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    rows = (
        db.query(BackupRecord)
        .order_by(BackupRecord.id.desc())
        .limit(200)
        .all()
    )
    return {
        "directory": str(BACKUP_DIRECTORY),
        "backups": [
            {
                "id": row.id,
                "filename": row.filename,
                "sha256": row.sha256,
                "size_bytes": row.size_bytes,
                "reason": row.reason,
                "integrity_status": row.integrity_status,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/backups")
def create_admin_backup(_admin=Depends(require_admin)):
    return {"status": "success", "backup": create_backup("ADMIN")}


@router.post("/backups/{filename}/verify")
def verify_admin_backup(filename: str, _admin=Depends(require_admin)):
    try:
        result = verify_backup(filename)
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if not result["valid"]:
        raise HTTPException(status_code=409, detail=result)
    return {"status": "success", "verification": result}


@router.get("/security-events")
def security_events(
    severity: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    query = db.query(SecurityEvent)
    if severity:
        query = query.filter(SecurityEvent.severity == severity.upper())
    rows = query.order_by(SecurityEvent.id.desc()).limit(min(max(limit, 1), 500)).all()
    return {
        "events": [
            {
                "id": row.id,
                "event_type": row.event_type,
                "severity": row.severity,
                "method": row.method,
                "path": row.path,
                "status_code": row.status_code,
                "actor": row.actor,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "detail": row.detail,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/security-summary")
def security_summary(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    totals = dict(
        db.query(SecurityEvent.severity, func.count(SecurityEvent.id))
        .group_by(SecurityEvent.severity)
        .all()
    )
    return {"status": "success", "totals": totals}
