"""Validated API inputs and provider-native structured itinerary output."""
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, StrictBool

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    collaborate: StrictBool = False

class TripRequest(StrictModel):
    destination: str = Field(min_length=1, max_length=150)
    days: int = Field(default=2, ge=1, le=30, strict=True)
    start_date: date | None = None
    interests: str = Field(default='local highlights', max_length=700)
    pace: str = Field(default='Relaxed', max_length=80)
    transport: str = Field(default='Walking and public transit', max_length=100)
    preferences: str = Field(default='flexible', max_length=300)
    food_preferences: str = Field(default='local food; no dietary restrictions specified', max_length=300)
    collaborate: StrictBool = False

# All output fields are required (nullable where appropriate), for strict schemas.
class PlaceReference(StrictModel):
    name: str
    city: str
    address: str | None

class Activity(StrictModel):
    period: str
    description: str
    place: PlaceReference | None

class DayPlan(StrictModel):
    day: int
    title: str
    activities: list[Activity]

class PlannerResponse(StrictModel):
    summary: str
    days: list[DayPlan]
    warnings: list[str]
