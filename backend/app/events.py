"""Event schemas for the simulated e-commerce traffic.

Every event that flows through the bus is one of these Pydantic models,
serialized with ``model_dump(mode="json")`` — the same shape a real
producer would publish to a Kafka topic.
"""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    timestamp: datetime = Field(default_factory=_now)
    user_id: str


class OrderEvent(BaseEvent):
    event_type: Literal["order"] = "order"
    product_id: str
    product_name: str
    category: str
    amount: float
    currency: str = "USD"


class PageViewEvent(BaseEvent):
    event_type: Literal["page_view"] = "page_view"
    page: str
    referrer: str


class SignupEvent(BaseEvent):
    event_type: Literal["signup"] = "signup"
    plan: Literal["free", "pro", "team"]
