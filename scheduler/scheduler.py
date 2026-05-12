"""
scheduler/scheduler.py
APScheduler config — runs the pipeline every Sunday at 08:00 local time.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

_scheduler = None


def _pipeline_job():
    """Imported lazily to avoid circular imports at startup."""
    from core.pipeline import run_full_pipeline
    run_full_pipeline()


def start_scheduler(hour: int = 8, day_of_week: str = "sun"):
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        _pipeline_job,
        trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=0),
        id="weekly_job_scan",
        name="Weekly Job Match Pipeline",
        replace_existing=True,
    )
    _scheduler.start()
    atexit.register(lambda: _scheduler.shutdown(wait=False))
    print(f"[Scheduler] Started — runs every {day_of_week.upper()} at {hour:02d}:00 IST")
    return _scheduler


def get_next_run() -> str | None:
    if not _scheduler or not _scheduler.running:
        return None
    job = _scheduler.get_job("weekly_job_scan")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%A, %B %d at %H:%M %Z")
    return None
