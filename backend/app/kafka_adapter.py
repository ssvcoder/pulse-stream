"""Point PulseStream at a real Kafka broker.

Steps:
  1. ``pip install kafka-python`` (already listed as optional in
     ``requirements.txt``)
  2. ``export KAFKA_BOOTSTRAP_SERVERS=localhost:9092``
  3. In ``main.py``, swap the wiring::

         from app.kafka_adapter import KafkaProducerAdapter, KafkaConsumerAdapter

         producer = KafkaProducerAdapter(os.environ["KAFKA_BOOTSTRAP_SERVERS"])
         consumer = KafkaConsumerAdapter(
             os.environ["KAFKA_BOOTSTRAP_SERVERS"],
             topic="events",
             group_id="pulse-stream",
         )

The adapter classes expose the exact same interface as ``bus.Producer``
(``send(topic, value, key)``) and ``bus.Consumer`` (``poll()`` / async
iteration), so ``producer.py``, ``aggregator.py`` and the rest of ``main.py``
work unchanged.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

Message = dict[str, Any]


def _require_kafka():
    try:
        from kafka import KafkaConsumer, KafkaProducer  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "kafka-python is not installed. Run: pip install kafka-python"
        ) from exc
    return KafkaConsumer, KafkaProducer


class KafkaProducerAdapter:
    """Drop-in replacement for ``bus.Producer`` backed by Kafka."""

    def __init__(self, bootstrap_servers: str) -> None:
        _, KafkaProducer = _require_kafka()
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )

    async def send(self, topic: str, value: Message,
                   key: str | None = None) -> None:
        loop = asyncio.get_running_loop()
        # kafka-python is blocking, so push the send onto a worker thread and
        # wait for the broker acknowledgement without stalling the event loop.
        future = self._producer.send(topic, key=key, value=value)
        await loop.run_in_executor(None, lambda: future.get(timeout=10))


class KafkaConsumerAdapter:
    """Drop-in replacement for ``bus.Consumer`` backed by Kafka."""

    def __init__(self, bootstrap_servers: str, topic: str,
                 group_id: str = "pulse-stream") -> None:
        KafkaConsumer, _ = _require_kafka()
        self._consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )

    async def poll(self, timeout: float = 1.0) -> Message | None:
        loop = asyncio.get_running_loop()
        records = await loop.run_in_executor(
            None, lambda: self._consumer.poll(timeout_ms=int(timeout * 1000), max_records=1))
        for _tp, messages in records.items():
            if messages:
                return messages[0].value
        return None

    def __aiter__(self) -> "KafkaConsumerAdapter":
        return self

    async def __anext__(self) -> Message:
        while True:
            message = await self.poll(timeout=1.0)
            if message is not None:
                return message
