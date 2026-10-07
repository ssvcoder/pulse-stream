"""Simulated e-commerce traffic generator.

In a real deployment this module is replaced by actual services publishing
to Kafka (checkout service -> "events" topic, etc.). Here it plays that
role so the full streaming pipeline can run with zero infrastructure.
"""
from __future__ import annotations

import asyncio
import math
import random
import time

from .bus import Producer
from .events import OrderEvent, PageViewEvent, SignupEvent

# A small catalog with realistic prices. The first few entries get a higher
# weight below so the "top products" chart has believable leaders.
PRODUCTS = [
    ("p1001", "Aurora Wireless Headphones", "Electronics", 129.99, 5),
    ("p1002", "Nimbus Mechanical Keyboard", "Electronics", 89.99, 4),
    ("p1003", "Terra Insulated Bottle", "Home", 34.95, 4),
    ("p1004", "Vertex Ergonomic Chair", "Furniture", 249.00, 2),
    ("p1005", "Pulse Fitness Tracker", "Electronics", 79.99, 3),
    ("p1006", "Lumen Desk Lamp", "Home", 49.99, 2),
    ("p1007", "Atlas Backpack", "Apparel", 69.99, 3),
    ("p1008", "Drift Running Shoes", "Apparel", 119.99, 3),
    ("p1009", "Echo Smart Speaker", "Electronics", 59.99, 2),
    ("p1010", "Harbor Ceramic Mug Set", "Home", 29.99, 2),
    ("p1011", "Summit Yoga Mat", "Sports", 39.99, 1),
    ("p1012", "Bolt Portable Charger", "Electronics", 24.99, 1),
]

PAGES = ["/", "/products", "/products/aurora-headphones", "/pricing",
         "/checkout", "/blog", "/deals", "/support"]
REFERRERS = ["google", "direct", "newsletter", "twitter", "instagram", "bing"]
PLANS = ["free", "free", "free", "pro", "pro", "team"]  # weighted toward free

TOPIC = "events"


class TrafficProducer:
    """Publishes random, realistic events to the bus in an endless loop."""

    def __init__(self, producer: Producer, events_per_second: float = 8.0,
                 seed: int | None = None) -> None:
        self._producer = producer
        self._rate = events_per_second
        self._rng = random.Random(seed)
        self._user_counter = 0

    def _next_user(self) -> str:
        # Stable pool of ~2k users so the feed feels like repeat traffic.
        self._user_counter += 1
        return f"u{self._rng.randint(1, 2000):05d}"

    def _random_event(self):
        roll = self._rng.random()
        if roll < 0.20:
            pid, name, category, price, weight = self._rng.choices(
                PRODUCTS, weights=[p[4] for p in PRODUCTS])[0]
            return OrderEvent(
                user_id=self._next_user(),
                product_id=pid, product_name=name,
                category=category, amount=price,
            )
        if roll < 0.30:
            return SignupEvent(
                user_id=self._next_user(),
                plan=self._rng.choice(PLANS),
            )
        return PageViewEvent(
            user_id=self._next_user(),
            page=self._rng.choice(PAGES),
            referrer=self._rng.choice(REFERRERS),
        )

    async def run(self) -> None:
        """Publish forever. Inter-arrival times are exponential (Poisson
        process) with a slow sine wave on top so traffic visibly ebbs."""
        while True:
            wave = 1.0 + 0.35 * math.sin(time.time() / 45.0)
            event = self._random_event()
            # user_id doubles as the record key, like a Kafka partition key.
            await self._producer.send(
                TOPIC, event.model_dump(mode="json"), key=event.user_id)
            await asyncio.sleep(self._rng.expovariate(self._rate * wave))
