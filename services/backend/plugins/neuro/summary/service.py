# path: backend/plugins/neuro/summary/service.py

from datetime import datetime
import os
from typing import Annotated, Dict
import pytz
from fastapi import Depends
from structlog import get_logger

from plugins.core.config.service import ConfigService, get_config_service
from utils.dependencies import get_llm_client
from utils.exceptions import BadRequestError, LLMError, ServiceError
from utils.llm_client import LLMClient
from .models import LLMSummaryResponse, SummaryDB, SummaryResponse
from .repository import (
    MessageRepository,
    SummaryRepository,
    get_message_repository_for_summary,
    get_summary_repository,
)

log = get_logger(__name__)
MOSCOW_TZ = pytz.timezone("Europe/Moscow")
DEFAULT_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "default_system_prompt.txt"
)


class SummaryService:
    def __init__(
        self,
        llm_client: Annotated[LLMClient, Depends(get_llm_client)],
        config: Annotated[ConfigService, Depends(get_config_service)],
        msg_repo: Annotated[
            MessageRepository, Depends(get_message_repository_for_summary)
        ],
        summary_repo: Annotated[SummaryRepository, Depends(get_summary_repository)],
    ):
        self.llm = llm_client
        self.config = config
        self.msg_repo = msg_repo
        self.summary_repo = summary_repo

    def _format_message_for_log(self, msg: Dict) -> str:
        """Formats a single message dictionary into a log string."""
        try:
            local_time = msg["date"].astimezone(MOSCOW_TZ).strftime("%H:%M:%S")
            user = msg.get("from_user", {})
            name = user.get("first_name", "Unknown")
            if last_name := user.get("last_name"):
                name += f" {last_name}"

            content = msg.get("text") or msg.get("caption", "[MEDIA]")
            content = content.replace("\n", " ")  # Keep summaries clean
            return f"[{local_time}] [{msg.get('id')}] {name}: {content}"
        except Exception:
            # Silently ignore formatting errors for individual messages
            return ""

    def _format_summary_text(
        self,
        summary: LLMSummaryResponse,
        chat_id: int,
        chat_title: str,
        date: datetime,
        roast_enabled: bool,
    ) -> str:
        """Formats the final summary text to be sent to the chat."""
        date_str = (
            "сегодня" if date.date() == datetime.now(MOSCOW_TZ).date() else "вчера"
        )
        text = f"📊 **Итоги обсуждений в чате «{chat_title}» за {date_str}**:\n\n"

        for theme in summary.themes:
            text += f"{theme.emoji} **{theme.name}** "
            if theme.messages_id:
                clean_chat_id = str(chat_id).replace("-100", "")
                links = [
                    f"[{i + 1}](https://t.me/c/{clean_chat_id}/{msg_id})"
                    for i, msg_id in enumerate(theme.messages_id)
                ]
                text += f"({', '.join(links)})\n"
            else:
                text += "\n"
            for point in theme.key_takeaways:
                text += f"• {point}\n"
            text += "\n"

        if roast_enabled and summary.bot_opinions:
            text += "🤖 **Мнение бота о вас всех**:\n"
            for opinion in summary.bot_opinions:
                text += f"• {opinion}\n"
            text += "\n**Вы можете отключить прожарку ботом командой** `/config disable summary_roast`"

        return text

    async def generate_summary(
        self, chat_id: int, chat_title: str, date_str: str
    ) -> SummaryResponse:
        """The main service method to generate a chat summary."""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise BadRequestError("Invalid date format. Please use YYYY-MM-DD.")

        # --- FIX: Use get_or_create for robust configuration loading ---
        min_messages = await self.config.get_or_create(
            "neuro/summary.min_messages_threshold",
            default=60,
            description="Minimum messages in a day for a summary to be generated.",
        )
        model = await self.config.get_or_create(
            "neuro/summary.model_name",
            default="openai/gpt-4o-mini",
            description="LLM model used for chat summarization.",
        )

        # Load the default prompt from the file
        try:
            with open(DEFAULT_PROMPT_PATH, "r", encoding="utf-8") as f:
                default_prompt_text = f.read()
        except FileNotFoundError:
            log.error(
                f"FATAL: Default system prompt file not found at {DEFAULT_PROMPT_PATH}"
            )
            raise ServiceError(
                "Server is misconfigured: Default summary prompt is missing."
            )

        system_prompt = await self.config.get_or_create(
            "neuro/summary.system_prompt",
            default=default_prompt_text,
            description="The system prompt for the chat summarization LLM.",
        )

        # We can fetch chat-specific config directly here too
        roast_enabled = await self.config.get(
            f"chat_config:{chat_id}:summary_roast_enabled", default=True
        )

        # 2. Fetch messages
        messages = await self.msg_repo.get_messages_for_summary(chat_id, target_date)
        if len(messages) < min_messages:
            raise BadRequestError(
                f"Not enough messages to generate a summary. Found {len(messages)}, need {min_messages}."
            )

        # ... (rest of the method is unchanged)
        # 3. Format chat log for LLM
        chat_log_lines = [self._format_message_for_log(msg) for msg in messages]
        chat_log = "\n".join(filter(None, chat_log_lines))

        # 4. Call LLM for summarization
        try:
            llm_response = await self.llm.structured_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chat_log},
                ],
                model=model,
                response_model=LLMSummaryResponse,
            )
        except Exception as e:
            log.error("LLM failed to generate summary", error=str(e))
            raise LLMError(
                "The language model failed to produce a valid summary."
            ) from e

        # 5. Store summary in DB
        summary_doc = SummaryDB(
            chat_id=chat_id,
            chat_title=chat_title,
            summary_date=target_date,
            themes=[theme.model_dump() for theme in llm_response.themes],
            bot_opinions=llm_response.bot_opinions,
            message_count=len(messages),
            model_used=model,
        )
        summary_id = await self.summary_repo.store_summary(summary_doc)

        # 6. Format response for the bot
        formatted_text = self._format_summary_text(
            llm_response, chat_id, chat_title, target_date, roast_enabled
        )

        return SummaryResponse(
            summary_id=summary_id,
            formatted_text=formatted_text,
            message_count=len(messages),
        )


def get_summary_service(
    service: Annotated[SummaryService, Depends(SummaryService)],
) -> SummaryService:
    """Dependency provider for the SummaryService."""
    return service
