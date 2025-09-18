"""Random generation service functions."""

import random
from typing import Any

from utils.exceptions import BadRequestError

MAGIC_8BALL_RESPONSES = [
    "Бесспорно",
    "Предрешено",
    "Никаких сомнений",
    "Определённо да",
    "Можешь быть уверен в этом",
    "Мне кажется — «да»",
    "Вероятнее всего",
    "Хорошие перспективы",
    "Знаки говорят — «да»",
    "Да",
    "Пока не ясно, попробуй снова",
    "Спроси позже",
    "Лучше не рассказывать",
    "Сейчас нельзя предсказать",
    "Сконцентрируйся и спроси опять",
    "Даже не думай",
    "Мой ответ — «нет»",
    "По моим данным — «нет»",
    "Перспективы не очень хорошие",
    "Весьма сомнительно",
]


def make_choice(options_text: str) -> dict[str, Any]:
    """
    Choose a random option from a list separated by semicolons.

    Args:
        options_text: String with options separated by semicolons

    Returns:
        Dict with result

    Raises:
        BadRequestError: If no valid options are provided.
    """
    if not options_text or not options_text.strip():
        raise BadRequestError(
            "No options provided. Please separate choices with a semicolon."
        )

    options = [opt.strip() for opt in options_text.split(";") if opt.strip()]

    if not options:
        raise BadRequestError("No valid options found after parsing.")

    return {"choice": random.choice(options)}


def roll_dice() -> dict[str, Any]:
    """
    Roll a dice (1-6).

    Returns:
        Dict with result
    """
    return {"result": random.randint(1, 6)}


def flip_coin() -> dict[str, Any]:
    """
    Flip a coin.

    Returns:
        Dict with result
    """
    return {"result": random.choice(["Орёл", "Решка"])}


def magic_8ball() -> dict[str, Any]:
    """
    Get a magic 8-ball prediction.

    Returns:
        Dict with result
    """
    return {"prediction": random.choice(MAGIC_8BALL_RESPONSES)}


def generate_random_number(
    min_value: int | None = None, max_value: int | None = None
) -> dict[str, Any]:
    """
    Generate a random number in a range.

    Args:
        min_value: Minimum value (default: 1)
        max_value: Maximum value (default: 100)

    Returns:
        Dict with result
    """
    min_val = min_value if min_value is not None else 1
    max_val = max_value if max_value is not None else 100

    if min_val > max_val:
        min_val, max_val = max_val, min_val

    return {"result": random.randint(min_val, max_val)}
