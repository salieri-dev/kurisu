"""
Generates thread-style images (like 2ch or 4chan) from LLM-generated content.

This module contains the logic for:
1.  Using an abstract AssetService to fetch random images for the threads.
2.  Sanitizing text from the LLM to prevent HTML injection vulnerabilities.
3.  Rendering the sanitized content into an HTML template using Jinja2.
4.  Converting the final HTML into a PNG image using the imgkit library.
"""

import html
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import imgkit
from jinja2 import Environment, FileSystemLoader
from PIL import Image
from structlog import get_logger
from utils.asset_service import AssetService
from utils.exceptions import NotFoundError, ServiceError

from .models import LLMStoryResponse

logger = get_logger(__name__)


class BaseImageGenerator(ABC):
    """Abstract base class for thread image generators."""

    def __init__(self, template_name: str, asset_service: AssetService):
        """
        Initializes the generator with a template and the asset service.

        Args:
            template_name: The filename of the Jinja2 template to use.
            asset_service: An instance of a class that implements the AssetService protocol.
        """
        self.asset_service = asset_service
        templates_root = Path(__file__).parent / "templates"
        self.template_path = templates_root / template_name

        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        loader = FileSystemLoader(searchpath=templates_root)
        self.jinja_env = Environment(loader=loader, autoescape=True)

    def _get_random_image_details(self) -> dict[str, Any] | None:
        """Finds a random image using the AssetService and returns its details."""
        try:
            asset_category = f"neuro/threads/assets/{self._get_asset_subdir()}"
            assets = self.asset_service.get_random_assets(asset_category, count=1)
        except NotFoundError:
            logger.warning("No assets found for category", category=asset_category)
            return None

        if not assets:
            return None

        asset = assets[0]
        try:
            with Image.open(asset.path) as img:
                width, height = img.size
            size_kb = asset.size_bytes // 1024

            return {
                "url": f"file:///{asset.path.resolve()}",
                "filename": asset.filename,
                "size_str": f"{size_kb} KB, {width}x{height}",
            }
        except Exception as e:
            logger.error(
                "Failed to process asset image", path=str(asset.path), error=str(e)
            )
            return None

    def _format_date(self, dt: datetime, style: str) -> str:
        """Formats a datetime object into a board-specific string."""
        if style == "dvach":
            weekday_ru = ["Пнд", "Втр", "Срд", "Чтв", "Птн", "Суб", "Вск"][dt.weekday()]
            return dt.strftime(f"%d/%m/%y ({weekday_ru}) %H:%M:%S")

        weekday_en = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dt.weekday()]
        return dt.strftime(f"%m/%d/%y({weekday_en})%H:%M:%S")

    @abstractmethod
    def _get_asset_subdir(self) -> str:
        """Returns the specific asset subdirectory name for the generator."""
        ...

    @abstractmethod
    def _format_story(self, text: str) -> str:
        """Sanitizes and formats the main story text into safe HTML."""
        ...

    @abstractmethod
    def _format_comment(self, text: str, post_id: str) -> str:
        """Sanitizes and formats a comment text into safe HTML."""
        ...

    @abstractmethod
    def _prepare_context(
        self, post_id: str, response: LLMStoryResponse
    ) -> dict[str, Any]:
        """Prepares the full context dictionary for rendering the Jinja2 template."""
        ...

    def generate(self, response: LLMStoryResponse, post_id: str) -> bytes:
        """Generates a PNG image from the LLM response."""
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
                "Failed to render thread image due to a server-side error."
            ) from e


class DvachGenerator(BaseImageGenerator):
    """Concrete implementation for generating 2ch-style 'bugurt' threads."""

    def __init__(self, asset_service: AssetService):
        super().__init__("dvach_template.html", asset_service)

    def _get_asset_subdir(self) -> str:
        return "bugurt"

    def _format_story(self, text: str) -> str:
        parts = [p.strip() for p in text.replace("\n", "@").split("@") if p.strip()]
        escaped_parts = [html.escape(part) for part in parts]
        return "<br>@<br>".join(escaped_parts)

    def _format_comment(self, text: str, post_id: str) -> str:
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            escaped_line = html.escape(line)
            if line.startswith(">>"):
                link_target = line[2:].strip()
                line_html = f'<a href="#{link_target}">&gt;&gt;{link_target}</a>'
            elif line.startswith(">"):
                line_html = f'<span class="unkfunc">{escaped_line}</span>'
            else:
                line_html = escaped_line
            lines.append(line_html)
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
    """Concrete implementation for generating 4chan-style 'greentext' threads."""

    def __init__(self, asset_service: AssetService):
        super().__init__("fourchan_template.html", asset_service)

    def _get_asset_subdir(self) -> str:
        return "greentext"

    def _format_story(self, text: str) -> str:
        lines = []
        for line in text.split("\n"):
            escaped_line = html.escape(line)
            if line.strip().startswith(">"):
                lines.append(f'<span class="quote">{escaped_line}</span>')
            else:
                lines.append(escaped_line)
        return "<br>".join(lines)

    def _format_comment(self, text: str, post_id: str) -> str:
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            escaped_line = html.escape(line)
            if line.startswith(">>"):
                link_target = line[2:].strip()
                line_html = f'<a href="#p{link_target}" class="quotelink">&gt;&gt;{link_target}</a>'
            elif line.startswith(">"):
                line_html = f'<span class="quote">{escaped_line}</span>'
            else:
                line_html = escaped_line
            lines.append(line_html)
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
