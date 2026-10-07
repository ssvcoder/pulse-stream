"""In-memory event bus with a Kafka-style producer/consumer API.

Everything in this project talks to the bus only through the ``Producer``
and ``Consumer`` classes below. Their method signatures deliberately mirror
``kafka.KafkaProducer.send()`` and the ``KafkaConsumer`` poll loop, so the
whole pipeline can be pointed at a real broker by swapping this module for
``kafka_adapter.py`` — no other code changes needed.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

# A message is just a JSON-serializable dict, like a Kafka record value.
Message = dict[str, Any]


class EventBus:
    """A tiny pub/sub broker: one asyncio queue per topic."""

    def __init__(self) -> None:
        self._topics: dict[str, asyncio.Queue[Message]] = defaultdict(asyncio.Queue)

    def producer(self) -> "Producer":
        return Producer(self)

    def consumer(self, topic: str) -> "Consumer":
        return Consumer(self._topics[topic])

    async def _publish(self, topic: str, message: Message) -> None:
        await self._topics[topic].put(message)


class Producer:
    """Mirrors ``kafka.KafkaProducer.send(topic, value=..., key=...)``."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def send(self, topic: str, value: Message, key: str | None = None) -> None:
        # The key travels with the record, exactly as a Kafka record key would,
        # so consumers can partition or route on it later.
        record = {"_key": key, **value} if key is not None else value
        await self._bus._publish(topic, record)


class Consumer:
    """Mirrors the ``KafkaConsumer`` poll loop over a single topic."""

    def __init__(self, queue: asyncio.Queue[Message]) -> None:
        self._queue = queue

    async def poll(self, timeout: float = 1.0) -> Message | None:
        """Return the next message, or None if the timeout elapses."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    def __aiter__(self) -> "Consumer":
        return self

    async def __anext__(self) -> Message:
        return await self._queue.get()
