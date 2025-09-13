# path: bot/jobs/manager.py

from structlog import get_logger
from pyrogram import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from .summary_job import SummaryJob
from .active_chats import ActiveChatsReconciliationJob

log = get_logger(__name__)
MOSCOW_TZ = pytz.timezone("Europe/Moscow")

_job_manager_instance = None


class ScheduledJobsManager:
    """Initializes and manages all scheduled jobs for the bot."""

    def __init__(self, client: Client):
        self.client = client
        self.scheduler = AsyncIOScheduler(timezone=str(MOSCOW_TZ))

        # --- Job 1: Daily Chat Profile Reconciliation ---
        self.reconciliation_job = ActiveChatsReconciliationJob(client)
        self.scheduler.add_job(
            self.reconciliation_job.reconcile_all_chats,
            CronTrigger(hour=3, minute=5, timezone=MOSCOW_TZ),
            id="reconcile_chats_job",
            name="Daily Chat Profile Reconciliation",
        )

        # --- Job 2: Daily Chat Summary Generation ---
        self.summary_job = SummaryJob(client)
        self.scheduler.add_job(
            self.summary_job.run_daily_summary,
            CronTrigger(hour=10, minute=0, timezone=MOSCOW_TZ),  # Runs at 10:00 AM MSK
            id="daily_summary_job",
            name="Daily Chat Summary Generation",
        )

        self.scheduler.start()
        log.info(
            "ScheduledJobsManager started.",
            jobs=[job.id for job in self.scheduler.get_jobs()],
        )

    def get_reconciliation_job(self) -> ActiveChatsReconciliationJob:
        """Allows access to job instances for manual triggering."""
        return self.reconciliation_job


def init_scheduled_jobs(client: Client):
    """Initializes the singleton ScheduledJobsManager."""
    global _job_manager_instance
    if not _job_manager_instance:
        _job_manager_instance = ScheduledJobsManager(client)


def get_job_manager_instance() -> ScheduledJobsManager | None:
    """Returns the active job manager instance."""
    return _job_manager_instance
