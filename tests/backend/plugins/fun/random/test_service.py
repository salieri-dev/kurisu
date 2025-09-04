from unittest.mock import patch

import pytest
from plugins.fun.random import service as random_service
from utils.exceptions import BadRequestError


def test_roll_dice():
    """
    Tests that roll_dice returns a dictionary with an integer result between 1 and 6.
    """
    response = random_service.roll_dice()
    assert "result" in response
    assert isinstance(response["result"], int)
    assert 1 <= response["result"] <= 6


def test_flip_coin():
    """
    Tests that flip_coin returns one of the two expected strings.
    """
    response = random_service.flip_coin()
    assert "result" in response
    assert response["result"] in ["Орёл", "Решка"]


@patch("plugins.fun.random.service.random.choice")
def test_make_choice_is_deterministic_with_mock(mock_random_choice):
    """
    Tests that make_choice returns a predictable value by mocking `random.choice`.
    This ensures our logic is tested, not the random library itself.
    """
    mock_random_choice.return_value = "paper"
    options = "rock;paper;scissors"
    response = random_service.make_choice(options)
    assert response["choic e"] == "paper"
    mock_random_choice.assert_called_once_with(["rock", "paper", "scissors"])


def test_make_choice_raises_error_on_empty_input():
    """
    Tests that make_choice raises a BadRequestError when the input string is empty.
    This is a "sad path" test.
    """
    with pytest.raises(BadRequestError, match="No options provided"):
        random_service.make_choice("")


def test_make_choice_raises_error_on_whitespace_input():
    """
    Tests that make_choice raises a BadRequestError for input with only whitespace/semicolons.
    """
    with pytest.raises(BadRequestError, match="No valid options found"):
        random_service.make_choice(" ; ;; ")
