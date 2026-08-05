from pathlib import Path

routes = Path("api/copyhub/routes.py")
text = routes.read_text(encoding="utf-8")
start = text.index('@router.get("/admin/status")')
end = text.index('\n\n@router.post("/receiver/heartbeat")', start)
new_block = '''@router.get("/admin/status")
def admin_status(db: Session = Depends(get_db), admin: dict = Depends(require_super_admin)):
    channel = get_or_create_channel(db)
    receivers = db.query(CopyReceiver).filter(CopyReceiver.channel_id == channel.id).all()
    now = utc_now()
    receiver_rows = []
    running_count = 0
    online_count = 0

    for receiver in receivers:
        heartbeat_age_seconds = None
        if receiver.last_heartbeat_at is not None:
            heartbeat_age_seconds = max(0, int((now - receiver.last_heartbeat_at).total_seconds()))

        online = heartbeat_age_seconds is not None and heartbeat_age_seconds < 90
        connection_status = "ONLINE" if online else ("NEVER_CONNECTED" if receiver.last_heartbeat_at is None else "OFFLINE")
        if online:
            online_count += 1

        lifecycle = db.query(SubscriptionLifecycle).filter(
            SubscriptionLifecycle.subscriber_id == receiver.subscriber_id
        ).first()
        lifecycle_eligible = bool(
            lifecycle and lifecycle.status in {"ACTIVE", "GRACE"} and not lifecycle.manual_suspended
        )
        live_eligible = receiver.environment == "DEMO" or receiver.live_authorized
        terminal_ready = bool(online and receiver.metadata_verified)

        if not lifecycle_eligible:
            copy_status = "NOT_ELIGIBLE"
        elif not receiver.active:
            if connection_status == "NEVER_CONNECTED":
                copy_status = "AWAITING_TERMINAL"
            elif not online:
                copy_status = "OFFLINE"
            elif not receiver.metadata_verified:
                copy_status = "VERIFYING_TERMINAL"
            elif not live_eligible:
                copy_status = "LIVE_NOT_AUTHORIZED"
            else:
                copy_status = "READY_FOR_ACTIVATION"
        elif not online:
            copy_status = "OFFLINE"
        elif not receiver.metadata_verified:
            copy_status = "VERIFYING_TERMINAL"
        elif not live_eligible:
            copy_status = "LIVE_NOT_AUTHORIZED"
        elif channel.globally_paused:
            copy_status = "GLOBAL_PAUSED"
        elif receiver.paused:
            copy_status = "PAUSED"
        else:
            copy_status = "RUNNING"
            running_count += 1

        receiver_rows.append({
            "receiver_id": receiver.receiver_id,
            "account_number": receiver.account_number,
            "environment": receiver.environment,
            "currency_unit": receiver.currency_unit,
            "is_cent_account": receiver.is_cent_account,
            "metadata_verified": receiver.metadata_verified,
            "active": receiver.active,
            "paused": receiver.paused,
            "last_heartbeat_at": receiver.last_heartbeat_at,
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "connection_status": connection_status,
            "activation_status": "ACTIVE" if receiver.active else "INACTIVE",
            "copy_status": copy_status,
            "lifecycle_eligible": lifecycle_eligible,
            "terminal_ready": terminal_ready,
            "live_eligible": live_eligible,
            "can_activate": bool(not receiver.active and terminal_ready and lifecycle_eligible and live_eligible),
            "can_deactivate": bool(receiver.active),
            "can_pause": bool(receiver.active and not receiver.paused),
            "can_resume": bool(receiver.active and receiver.paused),
        })

    if not channel.active:
        operational_status = "DISABLED"
    elif channel.globally_paused:
        operational_status = "PAUSED"
    elif running_count:
        operational_status = "RUNNING"
    elif online_count:
        operational_status = "READY"
    else:
        operational_status = "OFFLINE"

    db.commit()
    return {
        "master_account": channel.master_account,
        "active": channel.active,
        "globally_paused": channel.globally_paused,
        "operational_status": operational_status,
        "receiver_count": len(receiver_rows),
        "online_receiver_count": online_count,
        "running_receiver_count": running_count,
        "receivers": receiver_rows,
    }
'''
routes.write_text(text[:start] + new_block + text[end:], encoding="utf-8")

frontend = Path("admin-frontend/js/admin-control.js")
js = frontend.read_text(encoding="utf-8")
start = js.index('  $("#copyhub-global-state").textContent=data.globally_paused?"PAUSED":"RUNNING";')
end = js.index("  $$('[data-copyhub-action]')", start)
new_js = '''  const globalStatus=data.operational_status||"UNKNOWN";
  $("#copyhub-global-state").textContent=globalStatus;
  $("#copyhub-global-state").className=`review-state state-${String(globalStatus).toLowerCase().replaceAll("_","-")}`;
  $("#copyhub-global-toggle").textContent=data.globally_paused?"Resume all copying":"Emergency pause";
  table.innerHTML=(data.receivers||[]).map(row=>{
   const heartbeat=row.last_heartbeat_at?new Date(row.last_heartbeat_at+"Z"):null;
   const primaryAction=row.active?"deactivate":"activate";
   const primaryAllowed=row.active?row.can_deactivate:row.can_activate;
   const pauseAction=row.paused?"resume":"pause";
   const pauseAllowed=row.paused?row.can_resume:row.can_pause;
   return `<tr><td>${escapeHtml(row.receiver_id)}</td><td><strong>${escapeHtml(row.account_number)}</strong></td><td>${stateBadge(row.environment)}</td><td>${escapeHtml(row.currency_unit)} · ${row.is_cent_account?"CENT":"STANDARD"}</td><td>${stateBadge(row.connection_status)}<br><small>${heartbeat?heartbeat.toLocaleString():"Never connected"}</small></td><td>${stateBadge(row.copy_status)}</td><td><div class="review-actions"><button data-copyhub-action="${primaryAction}" data-receiver="${escapeHtml(row.receiver_id)}" data-account="${escapeHtml(row.account_number)}" ${primaryAllowed?"":"disabled"}>${row.active?"Deactivate":"Activate"}</button><button data-copyhub-action="${pauseAction}" data-receiver="${escapeHtml(row.receiver_id)}" ${pauseAllowed?"":"disabled"}>${row.paused?"Resume":"Pause"}</button></div></td></tr>`;
  }).join("")||'<tr><td colspan="7">No copier receivers have been provisioned.</td></tr>';
'''
frontend.write_text(js[:start] + new_js + js[end:], encoding="utf-8")

Path("tests/test_copyhub_dynamic_status.py").write_text('''from pathlib import Path


def test_copyhub_frontend_uses_backend_derived_statuses():
    source = Path("admin-frontend/js/admin-control.js").read_text(encoding="utf-8")
    assert "row.connection_status" in source
    assert "row.copy_status" in source
    assert "Date.now()-heartbeat.getTime()" not in source
    assert 'row.active?"ACTIVE":"INACTIVE"' not in source


def test_copyhub_backend_exposes_dynamic_status_fields():
    source = Path("api/copyhub/routes.py").read_text(encoding="utf-8")
    for field in ("operational_status", "connection_status", "copy_status", "can_activate", "can_pause", "can_resume"):
        assert field in source
''', encoding="utf-8")

Path("scripts/apply_dynamic_copyhub_statuses.py").unlink()
for workflow in (
    Path(".github/workflows/apply-dynamic-copyhub-statuses.yml"),
    Path(".github/workflows/run-dynamic-copyhub-statuses.yml"),
):
    if workflow.exists():
        workflow.unlink()
