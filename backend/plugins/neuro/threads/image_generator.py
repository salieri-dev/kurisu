# backend/plugins/neuro/threads/image_generator.py

import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import imgkit
from jinja2 import Environment, FileSystemLoader
from PIL import Image
from structlog import get_logger
from utils.exceptions import ServiceError

from .models import LLMStoryResponse

logger = get_logger(__name__)


class BaseImageGenerator(ABC):
    """Abstract base class for thread image generators."""

    def __init__(self, template_name: str):
        # --- FIX STARTS HERE ---
        # Define separate paths for templates and assets
        base_dir = Path(__file__).parent
        self.templates_root = base_dir / "templates"
        self.assets_root = base_dir / "assets"
        # --- FIX ENDS HERE ---

        self.template_path = self.templates_root / template_name
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        # Jinja loader should only look for templates
        loader = FileSystemLoader(searchpath=self.templates_root)
        self.jinja_env = Environment(loader=loader, autoescape=True)

    def _get_random_image_details(self) -> dict[str, Any] | None:
        """Finds a random image and returns its details."""
        # --- FIX STARTS HERE ---
        # Image directory should be based on the assets_root
        image_dir = self.assets_root / self._get_asset_subdir()
        # --- FIX ENDS HERE ---
        if not image_dir.is_dir():
            logger.warning("Asset subdirectory not found", path=str(image_dir))
            return None

        images = (
            list(image_dir.glob("*.png"))
            + list(image_dir.glob("*.jpg"))
            + list(image_dir.glob("*.jpeg"))
        )
        if not images:
            logger.warning("No images found in asset subdirectory", path=str(image_dir))
            return None

        image_path = random.choice(images)
        try:
            with Image.open(image_path) as img:
                width, height = img.size
            size_kb = image_path.stat().st_size // 1024

            return {
                "url": f"file:///{image_path.resolve()}",
                "filename": image_path.name,
                "size_str": f"{size_kb} KB, {width}x{height}",
            }
        except Exception as e:
            logger.error(
                "Failed to process asset image", path=str(image_path), error=str(e)
            )
            return None

    def _format_date(self, dt: datetime, style: str) -> str:
        """Formats datetime object into a string."""
        if style == "dvach":
            weekday_ru = ["Пнд", "Втр", "Срд", "Чтв", "Птн", "Суб", "Вск"][dt.weekday()]
            return dt.strftime(f"%d/%m/%y ({weekday_ru}) %H:%M:%S")
        weekday_en = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dt.weekday()]
        return dt.strftime(f"%m/%d/%y({weekday_en})%H:%M:%S")

    @abstractmethod
    def _get_asset_subdir(self) -> str: ...

    @abstractmethod
    def _format_story(self, text: str) -> str: ...

    @abstractmethod
    def _format_comment(self, text: str, post_id: str) -> str: ...

    @abstractmethod
    def _prepare_context(
        self, post_id: str, response: LLMStoryResponse
    ) -> dict[str, Any]: ...

    def generate(self, response: LLMStoryResponse, post_id: str) -> bytes:
        """Generates a PNG image from the LLM response."""
        # The post_id is now passed in, not generated here.
        template = self.jinja_env.get_template(self.template_path.name)
        context = self._prepare_context(post_id, response)
        html_content = template.render(context)

        options = {
            "format": "png", "encoding": "UTF-8", "quality": 90,
            "width": 800, "enable-local-file-access": ""
        }
        try:
            image_bytes = imgkit.from_string(html_content, False, options=options)
            logger.info("Successfully generated thread image in memory.")
            return image_bytes
        except Exception as e:
            logger.error("imgkit failed to generate image", error=str(e), html=html_content[:500])
            raise ServiceError("Failed to render thread image. Ensure wkhtmltoimage is installed and in PATH.") from e


class DvachGenerator(BaseImageGenerator):
    def __init__(self):
        super().__init__("dvach_template.html")

    def _get_asset_subdir(self) -> str:
        return "bugurt"

    def _format_story(self, text: str) -> str:
        return "<br>@<br>".join(
            [p.strip() for p in text.replace("\n", "@").split("@") if p.strip()]
        )

    def _format_comment(self, text: str, post_id: str) -> str:
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">>"):
                line = f'<a href="#{line[2:].strip()}">&gt;&gt;{line[2:].strip()}</a>'
            elif line.startswith(">"):
                line = f'<span class="unkfunc">{line}</span>'
            lines.append(line)
        return "<br>".join(lines)

    def _prepare_context(
        self, post_id: str, response: LLMStoryResponse
    ) -> dict[str, Any]:
        now, comments = datetime.now(), []
        for i, comment_text in enumerate(response.comments):
            comments.append(
                {
                    "id": str(int(post_id) + i + 1),
                    "name": "Аноним",
                    "date": self._format_date(now, "dvach"),
                    "text": self._format_comment(comment_text, post_id),
                }
            )

        image_details = self._get_random_image_details()
        return {
            "post_id": post_id,
            "name": "Аноним",
            "date": self._format_date(now, "dvach"),
            "image_path": image_details["url"] if image_details else "",
            "image_name": "@not_salieri_bot",
            "image_size": image_details["size_str"] if image_details else "",
            "post_text": self._format_story(response.story),
            "comments": comments,
        }


class FourChanGenerator(BaseImageGenerator):
    def __init__(self):
        super().__init__("fourchan_template.html")

    def _get_asset_subdir(self) -> str:
        return "greentext"

    def _format_story(self, text: str) -> str:
        return "<br>".join(
            [
                f'<span class="quote">{line}</span>'
                if line.strip().startswith(">")
                else line
                for line in text.split("\n")
            ]
        )

    def _format_comment(self, text: str, post_id: str) -> str:
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">>"):
                line = f'<a href="#p{line[2:].strip()}" class="quotelink">&gt;&gt;{line[2:].strip()}</a>'
            elif line.startswith(">"):
                line = f'<span class="quote">{line}</span>'
            lines.append(line)
        return "<br>".join(lines)

    def _prepare_context(
        self, post_id: str, response: LLMStoryResponse
    ) -> dict[str, Any]:
        now, replies = datetime.now(), []
        for i, comment_text in enumerate(response.comments):
            replies.append(
                {
                    "id": str(int(post_id) + i + 1),
                    "name": "Anonymous",
                    "date": self._format_date(now, "4chan"),
                    "text": self._format_comment(comment_text, post_id),
                }
            )

        image_details = self._get_random_image_details()
        return {
            "thread_title": "Greentext",
            "post": {
                "id": post_id,
                "subject": "",
                "name": "Anonymous",
                "datetime": self._format_date(now, "4chan"),
                "has_image": bool(image_details),
                "image_url": image_details["url"] if image_details else "",
                "filename": image_details["filename"] if image_details else "",
                "filesize": image_details["size_str"] if image_details else "",
                "message": self._format_story(response.story),
            },
            "replies": replies,
        }
