import asyncio
from structlog import get_logger
from pyrogram import Client
from utils.api_client import backend_client
from utils.chat_info_helper import get_chat_profile_update

log = get_logger(__name__)


class ActiveChatsReconciliationJob:
    """Manages the daily task of updating chat profiles on the backend."""

    def __init__(self, client: Client):
        self.client = client

    async def reconcile_all_chats(self):
        """Fetches all known chat IDs from backend and updates their profiles."""
        log.info("Starting daily reconciliation of all chat profiles.")
        try:
            response = await backend_client.get("/analytics/chats/all-ids")
            chat_ids = response.get("chat_ids", [])
            if not chat_ids:
                log.info("No chat IDs received from backend for reconciliation.")
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
                "ActiveChatsReconciliationJob failed during execution.",
                error=str(e),
                exc_info=True,
            )
