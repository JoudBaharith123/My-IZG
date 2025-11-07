"""Domain models for customer and depot records."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(slots=True)
class Customer:
    """Represents a customer location enriched with operational metadata."""

    area: Optional[str]
    region: Optional[str]
    city: Optional[str]
    zone: Optional[str]
    agent_id: Optional[str]
    agent_name: Optional[str]
    customer_id: str
    customer_name: str
    latitude: float
    longitude: float
    status: Optional[str]
    raw: dict


@dataclass(slots=True)
class Depot:
    """Represents a distribution center with coordinates."""

    code: str
    latitude: float
    longitude: float
    effective_date: Optional[date] = None
