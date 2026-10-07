"""Rolling metrics over the event stream.

The aggregator is the single consumer of the "events" topic. It keeps a
sliding time window of everything it has seen and turns it into the JSON
snapshot the dashboard renders every second.
"""
from __future__ import annotations

import time
from collections import Counter, deque
from typing import Any

from .bus import Consumer

Message = dict[str, Any]


class MetricsAggregator:
    def __init__(self, consumer: Consumer, window_seconds: int = 300,
                 history_seconds: int = 120, feed_size: int = 20) -> None:
        self._consumer = consumer
        self._window = window_seconds        # sliding window for all metrics
        self._history_seconds = history_seconds  # per-second chart depth
        self._feed_size = feed_size

        self._events: deque[tuple[float, str]] = deque()   # (epoch, type)
        self._orders: deque[tuple[float, str, str, float]] = deque()  # (epoch, pid, name, amount)
        self._per_second: dict[int, int] = {}              # epoch_second -> count
        self._by_type: Counter[str] = Counter()
        self._recent: deque[Message] = deque(maxlen=feed_size)
        self._total_events = 0
        self._started_at = time.time()

    # -- consumption ----------------------------------------------------

    async def run(self) -> None:
        async for message in self._consumer:
            self._ingest(message)

    def _ingest(self, message: Message) -> None:
        now = time.time()
        event_type = message.get("event_type", "unknown")

        self._events.append((now, event_type))
        self._per_second[int(now)] = self._per_second.get(int(now), 0) + 1
        self._by_type[event_type] += 1
        self._recent.appendleft(message)
        self._total_events += 1

        if event_type == "order":
            self._orders.append((
                now,
                message.get("product_id", "?"),
                message.get("product_name", "Unknown product"),
                float(message.get("amount", 0.0)),
            ))

        self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0][0] < cutoff:
            _, event_type = self._events.popleft()
            self._by_type[event_type] -= 1
            if self._by_type[event_type] <= 0:
                del self._by_type[event_type]
        while self._orders and self._orders[0][0] < cutoff:
            self._orders.popleft()
        hist_cutoff = int(now) - self._history_seconds
        for second in [s for s in self._per_second if s < hist_cutoff]:
            del self._per_second[second]

    # -- snapshots ------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Everything the dashboard needs, in one JSON-serializable dict."""
        now = time.time()
        self._prune(now)

        # Per-second history with gaps filled so the chart never jumps.
        end = int(now)
        history = [
            {"t": second * 1000, "count": self._per_second.get(second, 0)}
            for second in range(end - self._history_seconds + 1, end + 1)
        ]
        recent_counts = [self._per_second.get(s, 0)
                         for s in range(end - 9, end + 1)]
        events_per_second = round(sum(recent_counts) / len(recent_counts), 1)

        products: dict[str, dict[str, Any]] = {}
        for _, pid, name, amount in self._orders:
            entry = products.setdefault(
                pid, {"product_id": pid, "name": name, "orders": 0, "revenue": 0.0})
            entry["orders"] += 1
            entry["revenue"] = round(entry["revenue"] + amount, 2)
        top_products = sorted(products.values(),
                              key=lambda p: p["revenue"], reverse=True)[:5]

        return {
            "timestamp": now,
            "uptime_seconds": round(now - self._started_at, 1),
            "events_per_second": events_per_second,
            "per_second_history": history,
            "by_type": dict(self._by_type),
            "top_products": top_products,
            "window_revenue": round(sum(p["revenue"] for p in products.values()), 2),
            "window_orders": len(self._orders),
            "total_events": self._total_events,
            "recent_events": list(self._recent)[:15],
        }
