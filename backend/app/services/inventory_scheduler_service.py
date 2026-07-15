import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.database import SessionLocal
from app.models.inventory_schedule import InventorySchedule
from app.services.inventory_snapshot_service import InventorySnapshotService, list_active_inventory_schedules


logger = logging.getLogger(__name__)
JOB_PREFIX = "inventory-schedule-"
SYNC_JOB_ID = "inventory-schedules-sync"


def calculate_next_run_at(schedule: InventorySchedule, now: Optional[datetime] = None):
    trigger = CronTrigger(
        hour=schedule.run_time.hour,
        minute=schedule.run_time.minute,
        second=0,
        timezone=schedule.timezone,
    )
    return trigger.get_next_fire_time(None, now or datetime.now(timezone.utc))


class InventorySchedulerService:
    def __init__(self, config: Settings = settings, scheduler=None, session_factory=SessionLocal):
        self.config = config
        self.scheduler = scheduler or BackgroundScheduler(timezone="Asia/Seoul")
        self.session_factory = session_factory
        self.started = False

    def start(self):
        if self.started or not self.config.inventory_scheduler_enabled:
            return
        self.scheduler.start(paused=True)
        self.started = True
        self.reload_jobs()
        self.scheduler.add_job(
            self.reload_jobs,
            IntervalTrigger(minutes=1),
            args=[],
            id=SYNC_JOB_ID,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.resume()
        logger.info("Inventory snapshot scheduler started")

    def shutdown(self):
        if not self.started:
            return
        self.scheduler.shutdown(wait=False)
        self.started = False
        logger.info("Inventory snapshot scheduler stopped")

    def reload_jobs(self):
        if not self.started:
            return
        for job in self.scheduler.get_jobs():
            if job.id.startswith(JOB_PREFIX):
                self.scheduler.remove_job(job.id)
        db = self.session_factory()
        try:
            schedules = list_active_inventory_schedules(db)
            for schedule in schedules:
                job = self.scheduler.add_job(
                    self.run_schedule,
                    CronTrigger(
                        hour=schedule.run_time.hour,
                        minute=schedule.run_time.minute,
                        second=0,
                        timezone=schedule.timezone,
                    ),
                    args=[schedule.id],
                    id="{}{}".format(JOB_PREFIX, schedule.id),
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=300,
                )
                schedule.next_run_at = job.next_run_time
            db.commit()
            logger.info("Inventory snapshot schedules loaded active_count=%s", len(schedules))
        except Exception as exc:
            db.rollback()
            logger.error("Inventory scheduler load failed error_type=%s", type(exc).__name__)
        finally:
            db.close()

    def run_schedule(self, schedule_id: int):
        db = self.session_factory()
        try:
            InventorySnapshotService(config=self.config).run_schedule(db, schedule_id)
            schedule = db.get(InventorySchedule, schedule_id)
            if schedule and schedule.is_active:
                schedule.next_run_at = calculate_next_run_at(schedule)
                db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(
                "Inventory scheduled execution failed schedule_id=%s error_type=%s",
                schedule_id, type(exc).__name__,
            )
        finally:
            db.close()


_inventory_scheduler = InventorySchedulerService()


def get_inventory_scheduler() -> InventorySchedulerService:
    return _inventory_scheduler


def refresh_inventory_scheduler():
    get_inventory_scheduler().reload_jobs()


def apply_schedule_payload(schedule: InventorySchedule, payload):
    values = payload.model_dump()
    for key, value in values.items():
        setattr(schedule, key, value)
    schedule.next_run_at = calculate_next_run_at(schedule) if schedule.is_active else None
    return schedule
