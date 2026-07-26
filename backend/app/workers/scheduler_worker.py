from __future__ import annotations

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.dependencies.database import SessionLocal
from app.services.notification_service import NotificationService
from app.services.scheduler_service import SchedulerService

logger = logging.getLogger("scheduler_worker")


def run_reminder_job() -> None:
    with SessionLocal() as db:
        scheduler = SchedulerService(db, NotificationService(db))
        sent = scheduler.process_due_reminders(reminder_window_hours=24)
        logger.info("Reminder job finished, sent=%s", sent)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_reminder_job, "interval", minutes=5, id="reservation-reminder")
    scheduler.start()
    logger.info("Scheduler worker started")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
