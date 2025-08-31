"""Pydantic models for random plugin API responses."""

from pydantic import BaseModel


class ChoiceResponse(BaseModel):
    """Response model for random choice endpoint."""

    choice: str

    class Config:
        json_schema_extra = {"example": {"choice": "option1"}}


class DiceResponse(BaseModel):
    """Response model for dice roll endpoint."""

    result: int

    class Config:
        json_schema_extra = {"example": {"result": 4}}


class CoinResponse(BaseModel):
    """Response model for coin flip endpoint."""

    result: str

    class Config:
        json_schema_extra = {"example": {"result": "Орёл"}}


class EightBallResponse(BaseModel):
    """Response model for magic 8-ball endpoint."""

    prediction: str

    class Config:
        json_schema_extra = {"example": {"prediction": "Да"}}


class NumberResponse(BaseModel):
    """Response model for random number endpoint."""

    result: int

    class Config:
        json_schema_extra = {"example": {"result": 42}}
