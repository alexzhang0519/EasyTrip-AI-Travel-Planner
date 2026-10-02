from typing import TypedDict

class PlanningState(TypedDict, total=False):
    messages: list[dict]
    request: str
    place_report: dict
    weather_report: dict
    result: list[dict]
