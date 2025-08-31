# backend/plugins/neuro/threads/image_generator.py

import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import imgkit
from jinja2 import Environment, FileSystemLoader
from structlog import get_logger
from utils.exceptions import ServiceError

from .models import LLMStoryResponse

logger = get_logger(__name__)


class BaseImageGenerator(ABC):
    """Abstract base class for thread image generators."""

    def __init__(self, template_name: str):
        self.template_path = Path(__file__).parent / "assets" / template_name
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        # Jinja setup
        loader = FileSystemLoader(searchpath=self.template_path.parent)
        self.jinja_env = Environment(loader=loader, autoescape=True)

    def _format_date(self, dt: datetime, style: str) -> str:
        """Formats datetime object into a string."""
        if style == "dvach":
            weekday_ru = ["Пнд", "Втр", "Срд", "Чтв", "Птн", "Суб", "Вск"][dt.weekday()]
            return dt.strftime(f"%d/%m/%y ({weekday_ru}) %H:%M:%S")
        # Default to 4chan style
        weekday_en = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dt.weekday()]
        return dt.strftime(f"%m/%d/%y({weekday_en})%H:%M:%S")

    @abstractmethod
    def _format_story(self, text: str) -> str: ...

    @abstractmethod
    def _format_comment(self, text: str, post_id: str) -> str: ...

    @abstractmethod
    def _prepare_context(
        self, post_id: str, response: LLMStoryResponse
    ) -> dict[str, Any]: ...

    def generate(self, response: LLMStoryResponse) -> bytes:
        """Generates a PNG image from the LLM response."""
        post_id = str(random.randint(10000000, 99999999))
        template = self.jinja_env.get_template(self.template_path.name)
        context = self._prepare_context(post_id, response)
        html_content = template.render(context)

        options = {
            "format": "png",
            "encoding": "UTF-8",
            "quality": 90,
            "width": 800,
            "enable-local-file-access": "",
        }
        try:
            image_bytes = imgkit.from_string(html_content, False, options=options)
            logger.info("Successfully generated thread image in memory.")
            return image_bytes
        except Exception as e:
            logger.error(
                "imgkit failed to generate image", error=str(e), html=html_content[:500]
            )
            raise ServiceError(
                "Failed to render thread image. Ensure wkhtmltoimage is installed and in PATH."
            ) from e


class DvachGenerator(BaseImageGenerator):
    """Generator for 2ch-style 'bugurt' threads."""

    def __init__(self):
        super().__init__("dvach_template.html")

    def _format_story(self, text: str) -> str:
        parts = [p.strip() for p in text.replace("\n", "@").split("@") if p.strip()]
        return "<br>@<br>".join(parts)

    def _format_comment(self, text: str, post_id: str) -> str:
        lines = text.split("\n")
        formatted = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">>"):
                ref_id = line[2:].strip()
                line = f'<a href="#{ref_id}">&gt;&gt;{ref_id}</a>'
            elif line.startswith(">"):
                line = f'<span class="unkfunc">{line}</span>'
            formatted.append(line)
        return "<br>".join(formatted)

    def _prepare_context(
        self, post_id: str, response: LLMStoryResponse
    ) -> dict[str, Any]:
        now = datetime.now()
        comments = []
        for i, comment_text in enumerate(response.comments):
            comments.append(
                {
                    "id": str(int(post_id) + i + 1),
                    "name": "Аноним",
                    "date": self._format_date(now, "dvach"),
                    "text": self._format_comment(comment_text, post_id),
                }
            )

        return {
            "post_id": post_id,
            "name": "Аноним",
            "date": self._format_date(now, "dvach"),
            "image_path": "",  # No random images for simplicity
            "image_name": "",
            "image_size": "",
            "post_text": self._format_story(response.story),
            "comments": comments,
        }


class FourChanGenerator(BaseImageGenerator):
    """Generator for 4chan-style 'greentext' threads."""

    def __init__(self):
        super().__init__("fourchan_template.html")

    def _format_story(self, text: str) -> str:
        lines = [
            f'<span class="quote">{line}</span>'
            if line.strip().startswith(">")
            else line
            for line in text.split("\n")
        ]
        return "<br>".join(lines)

    def _format_comment(self, text: str, post_id: str) -> str:
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">>"):
                ref_id = line[2:].strip()
                line = f'<a href="#p{ref_id}" class="quotelink">&gt;&gt;{ref_id}</a>'
            elif line.startswith(">"):
                line = f'<span class="quote">{line}</span>'
            lines.append(line)
        return "<br>".join(lines)

    def _prepare_context(
        self, post_id: str, response: LLMStoryResponse
    ) -> dict[str, Any]:
        now = datetime.now()
        replies = []
        for i, comment_text in enumerate(response.comments):
            replies.append(
                {
                    "id": str(int(post_id) + i + 1),
                    "name": "Anonymous",
                    "date": self._format_date(now, "4chan"),
                    "text": self._format_comment(comment_text, post_id),
                }
            )

        return {
            "thread_title": "Greentext",
            "post": {
                "id": post_id,
                "subject": "",
                "name": "Anonymous",
                "datetime": self._format_date(now, "4chan"),
                "has_image": False,
                "message": self._format_story(response.story),
            },
            "replies": replies,
        }
