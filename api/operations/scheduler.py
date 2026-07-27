from apscheduler.schedulers.background import BackgroundScheduler

from api.operations.backup import ensure_scheduled_backup


_scheduler = BackgroundScheduler(daemon=True)


def start_operations_scheduler() -> None:
    if _scheduler.running:
        return
    _scheduler.add_job(
        ensure_scheduled_backup,
        trigger="interval",
        hours=1,
        id="bethel_database_backup_check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
