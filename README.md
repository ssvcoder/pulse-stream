# PulseStream

A real-time analytics dashboard for e-commerce traffic. A simulated event
producer publishes orders, page views, and signups to a Kafka-style event
stream; a FastAPI backend aggregates them into rolling metrics and pushes a
live snapshot to a React dashboard over WebSocket — every second.

## Tech stack

| Layer    | Tech                                                        |
|----------|-------------------------------------------------------------|
| Backend  | Python 3.11, FastAPI, WebSocket, Pydantic, asyncio           |
| Streaming| In-memory event bus with a Kafka-style producer/consumer API (swap in `kafka-python` for a real broker) |
| Frontend | React 18, Vite, dependency-free canvas charts               |
| Infra    | Docker, docker-compose                                      |

## Architecture

```
                    +-------------------+
                    | TrafficProducer   |  simulated checkout / web / signup
                    | (orders, views,   |  services publishing realistic events
                    |  signups)         |
                    +--------+----------+
                             |  Producer.send("events", {...}, key=user_id)
                             v
                    +-------------------+
                    | EventBus          |  in-memory pub/sub, one queue/topic
                    | topic: "events"   |  (Kafka-style API)
                    +--------+----------+
                             |  Consumer poll loop
                             v
                    +-------------------+        1 snapshot / sec
                    | MetricsAggregator | --------------------+
                    | (5-min sliding    |                     |
                    |  window, per-sec   |                     v
                    |  history, top     |            +------------------+
                    |  products)        |            | FastAPI          |
                    +-------------------+            | /ws/metrics (WS) |
                                                     | /api/metrics     |
                                                     | /api/health      |
                                                     +--------+---------+
                                                              | WebSocket JSON
                                                              v
                                                     +------------------+
                                                     | React dashboard  |
                                                     | (Vite + canvas)  |
                                                     +------------------+
```

## How the streaming works

1. **Produce** — `TrafficProducer` (`backend/app/producer.py`) generates
   realistic events (weighted product catalog, Poisson arrivals with a slow
   traffic wave) and publishes them to the `events` topic via
   `Producer.send(topic, value, key=user_id)`.
2. **Consume** — `MetricsAggregator` (`backend/app/aggregator.py`) runs a
   poll loop over the topic, exactly like a Kafka consumer group member
   would, and maintains a 5-minute sliding window: per-second counts,
   per-type totals, top products by revenue, and a live event feed.
3. **Broadcast** — every second, `main.py` snapshots the aggregator and
   pushes it as JSON to every connected WebSocket client
   (`/ws/metrics`). The dashboard also does one REST fetch on load so it
   renders instantly, then lives off the socket (with auto-reconnect).

## Run it

### Option A — Docker (recommended)

```bash
docker compose up --build
```

- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

### Option B — local dev

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://localhost:8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

The Vite dev server proxies `/api` and `/ws` to the backend, so no extra
config is needed. Tune traffic with `EVENTS_PER_SECOND` (default `8`):

```bash
EVENTS_PER_SECOND=25 uvicorn app.main:app
```

## Point it at a real Kafka broker

The in-memory bus is only a stand-in. `backend/app/kafka_adapter.py`
provides `KafkaProducerAdapter` / `KafkaConsumerAdapter` with the **same
method signatures** as the in-memory `Producer` / `Consumer`:

1. `pip install kafka-python`
2. `export KAFKA_BOOTSTRAP_SERVERS=localhost:9092`
3. In `backend/app/main.py`, replace the wiring:

```python
from app.kafka_adapter import KafkaProducerAdapter, KafkaConsumerAdapter

producer = KafkaProducerAdapter(os.environ["KAFKA_BOOTSTRAP_SERVERS"])
consumer = KafkaConsumerAdapter(
    os.environ["KAFKA_BOOTSTRAP_SERVERS"], topic="events", group_id="pulse-stream",
)
```

`producer.py`, `aggregator.py`, and everything downstream work unchanged —
that is the point of the abstraction.

## Project layout

```
pulse-stream/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, WebSocket endpoint, broadcast loop
│   │   ├── bus.py           # in-memory event bus (Kafka-style API)
│   │   ├── kafka_adapter.py # real-broker adapters (kafka-python)
│   │   ├── events.py        # Pydantic event schemas
│   │   ├── producer.py      # simulated traffic generator
│   │   └── aggregator.py    # sliding-window metrics
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # dashboard layout + WebSocket hook
│   │   ├── components/      # LineChart (canvas), TopProducts, EventFeed
│   │   └── styles.css
│   └── Dockerfile           # Vite build -> nginx
├── Dockerfile               # backend image
├── docker-compose.yml
└── README.md
```
