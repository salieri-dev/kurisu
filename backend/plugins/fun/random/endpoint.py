"""Random generation API endpoints."""

from fastapi import APIRouter, Query
from plugins.fun.random import service as random_service
from plugins.fun.random.models import (
    ChoiceResponse,
    CoinResponse,
    DiceResponse,
    EightBallResponse,
    NumberResponse,
)

router = APIRouter()


@router.get(
    "/choice",
    response_model=ChoiceResponse,
    summary="Make a random choice",
    description=(
        "Choose a random option from a list of options separated by semicolons."
    ),
)
def make_choice(
    options: str = Query(
        ...,
        description="Options separated by semicolons (e.g., 'option1;option2;option3')",
        example="rock;paper;scissors",
    ),
):
    """
    Choose a random option from a list separated by semicolons.
    The service will raise a BadRequestError for invalid input, handled globally.
    """
    result = random_service.make_choice(options)
    return ChoiceResponse(choice=result["choice"])


@router.get(
    "/roll",
    response_model=DiceResponse,
    summary="Roll a dice",
    description=(
        "Roll a standard six-sided dice and get a random number between 1 and 6."
    ),
)
def roll_dice():
    """Roll a dice (1-6)."""

    return DiceResponse(**random_service.roll_dice())


@router.get(
    "/flip",
    response_model=CoinResponse,
    summary="Flip a coin",
    description="Flip a coin and get either 'Орёл' (heads) or 'Решка' (tails).",
)
def flip_coin():
    """Flip a coin."""
    return CoinResponse(**random_service.flip_coin())


@router.get(
    "/8ball",
    response_model=EightBallResponse,
    summary="Magic 8-ball prediction",
    description=(
        "Get a random prediction from a magic 8-ball with various possible answers."
    ),
)
def magic_8ball():
    """Get a magic 8-ball prediction."""
    return EightBallResponse(**random_service.magic_8ball())


@router.get(
    "/number",
    response_model=NumberResponse,
    summary="Generate random number",
    description="Generate a random integer within a specified range.",
)
def generate_random_number(
    min_value: int | None = Query(
        None, description="Minimum value (default: 1)", ge=0, example=1
    ),
    max_value: int | None = Query(
        None, description="Maximum value (default: 100)", ge=1, example=100
    ),
):
    """Generate a random number in a range."""
    return NumberResponse(**random_service.generate_random_number(min_value, max_value))
