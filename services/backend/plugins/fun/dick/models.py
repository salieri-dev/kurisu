from pydantic import BaseModel, Field


class DickAttributes(BaseModel):
    """Model for generated dick attributes with raw numerical and calculated data."""

    length_erect: float = Field(..., description="Erect length in cm.")
    girth_erect: float = Field(..., description="Erect girth in cm.")
    volume_erect: float = Field(..., description="Erect volume in cm³.")
    length_flaccid: float = Field(..., description="Flaccid length in cm.")
    girth_flaccid: float = Field(..., description="Flaccid girth in cm.")
    volume_flaccid: float = Field(..., description="Flaccid volume in cm³.")
    rigidity: float = Field(..., description="Rigidity percentage (0-100).")
    curvature: float = Field(..., description="Curvature in degrees (-30 to 30).")
    velocity: float = Field(..., description="Velocity in km/h (0-30).")
    stamina: float = Field(..., description="Stamina in minutes (1-60).")
    refractory_period: float = Field(
        ..., description="Refractory period in minutes (5-120)."
    )
    sensitivity: float = Field(..., description="Sensitivity rating (1-10).")
    satisfaction_rating: float = Field(
        ..., description="Overall satisfaction rating (0-100)."
    )


class ImageResponse(BaseModel):
    """Model for the base64 encoded image response. THIS WAS MISSING."""

    image_base64: str = Field(..., description="Base64 encoded PNG image data.")
