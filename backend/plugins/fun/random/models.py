"""Pydantic models for random plugin API responses."""

from pydantic import BaseModel, ConfigDict


class ChoiceResponse(BaseModel):
    choice: str
    model_config = {"json_schema_extra": {"examples": [{"choice": "option1"}]}}


class DiceResponse(BaseModel):
    """Response model for dice roll endpoint."""

    result: int

    model_config = ConfigDict(json_schema_extra={"examples": [{"result": 4}]})


class CoinResponse(BaseModel):
    """Response model for coin flip endpoint."""

    result: str

    model_config = ConfigDict(json_schema_extra={"examples": [{"result": "Орёл"}]})


class EightBallResponse(BaseModel):
    """Response model for magic 8-ball endpoint."""

    prediction: str

    model_config = ConfigDict(json_schema_extra={"examples": [{"prediction": "Да"}]})


class NumberResponse(BaseModel):
    """Response model for random number endpoint."""

    result: int

    model_config = ConfigDict(json_schema_extra={"examples": [{"result": 42}]})
