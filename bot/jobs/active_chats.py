import asyncio
from structlog import get_logger
from pyrogram import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.api_client import backend_client
from utils.chat_info_helper import get_chat_profile_update

log = get_logger(__name__)

_job_instance = None


class ActiveChatsReconciliationJob:
    def __init__(self, client: Client):
        self.client = client
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.reconcile_all_chats, CronTrigger(hour=3, minute=5))
        self.scheduler.start()
        log.info("ActiveChatsReconciliationJob scheduler started (runs daily).")

    async def reconcile_all_chats(self):
        log.info("Starting daily reconciliation of all chat profiles.")
        try:
            response = await backend_client.get("/analytics/chats/all-ids")
            chat_ids = response.get("chat_ids", [])
            if not chat_ids:
                return

            log.info(f"Reconciling profiles for {len(chat_ids)} chats.")

            tasks = [
                get_chat_profile_update(self.client, chat_id) for chat_id in chat_ids
            ]
            profile_updates = await asyncio.gather(*tasks)
            valid_updates = [update for update in profile_updates if update is not None]

            batch_size = 100
            for i in range(0, len(valid_updates), batch_size):
                batch = valid_updates[i : i + batch_size]
                await backend_client.post(
                    "/analytics/chats/profiles/update", json={"updates": batch}
                )
                log.info(
                    f"Sent reconciliation batch {i // batch_size + 1} with {len(batch)} profiles."
                )

            log.info("Daily chat profile reconciliation complete.")
        except Exception as e:
            log.error(
                "ActiveChatsReconciliationJob failed.", error=str(e), exc_info=True
            )


def init_scheduled_jobs(client: Client):
    global _job_instance
    if not _job_instance:
        _job_instance = ActiveChatsReconciliationJob(client)


def get_job_instance():
    return _job_instance
