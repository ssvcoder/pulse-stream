"""PulseStream API — FastAPI app streaming live analytics.

Pipeline: TrafficProducer -> (EventBus topic "events") -> MetricsAggregator
          -> WebSocket broadcast to dashboard clients, one snapshot per second.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .aggregator import MetricsAggregator
from .bus import EventBus
from .producer import TOPIC, TrafficProducer

EVENTS_PER_SECOND = float(os.getenv("EVENTS_PER_SECOND", "8"))
BROADCAST_INTERVAL = 1.0  # seconds between dashboard updates


async def _broadcast_loop(app: FastAPI) -> None:
    """Push the latest snapshot to every connected dashboard, every second."""
    while True:
        await asyncio.sleep(BROADCAST_INTERVAL)
        snapshot = app.state.aggregator.snapshot()
        dead = []
        for ws in list(app.state.connections):
            try:
                await ws.send_json(snapshot)
            except Exception:
                dead.append(ws)  # client went away; drop it next round
        for ws in dead:
            app.state.connections.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = EventBus()
    aggregator = MetricsAggregator(bus.consumer(TOPIC))
    traffic = TrafficProducer(bus.producer(), events_per_second=EVENTS_PER_SECOND)

    app.state.aggregator = aggregator
    app.state.connections: set[WebSocket] = set()

    tasks = [
        asyncio.create_task(traffic.run(), name="traffic-producer"),
        asyncio.create_task(aggregator.run(), name="aggregator"),
        asyncio.create_task(_broadcast_loop(app), name="broadcaster"),
    ]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="PulseStream", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo dashboard; tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metrics")
async def metrics() -> dict:
    """Latest snapshot as plain REST (used by the dashboard on first load)."""
    return app.state.aggregator.snapshot()


@app.websocket("/ws/metrics")
async def metrics_ws(websocket: WebSocket) -> None:
    """Live snapshot stream. Clients get the current state immediately,
    then one update per second until they disconnect."""
    await websocket.accept()
    app.state.connections.add(websocket)
    try:
        await websocket.send_json(app.state.aggregator.snapshot())
        while True:
            # We don't expect client messages; this just keeps the
            # connection open and surfaces disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        app.state.connections.discard(websocket)
