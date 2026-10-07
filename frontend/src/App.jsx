import { useEffect, useState } from 'react'
import LineChart from './components/LineChart.jsx'
import TopProducts from './components/TopProducts.jsx'
import EventFeed from './components/EventFeed.jsx'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/metrics'
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Connect to the snapshot stream, with automatic reconnect. A REST fetch
// first means the page renders instantly instead of waiting on the socket.
function useLiveMetrics() {
  const [snapshot, setSnapshot] = useState(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let ws = null
    let retryTimer = null
    let cancelled = false

    const connect = () => {
      ws = new WebSocket(WS_URL)
      ws.onopen = () => setConnected(true)
      ws.onmessage = (event) => setSnapshot(JSON.parse(event.data))
      ws.onerror = () => ws.close()
      ws.onclose = () => {
        setConnected(false)
        if (!cancelled) retryTimer = setTimeout(connect, 2000)
      }
    }

    fetch(`${API_URL}/api/metrics`)
      .then((res) => res.json())
      .then(setSnapshot)
      .catch(() => {})
    connect()

    return () => {
      cancelled = true
      clearTimeout(retryTimer)
      if (ws) ws.close()
    }
  }, [])

  return { snapshot, connected }
}

function KpiCard({ label, value, sub }) {
  return (
    <div className="card kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

export default function App() {
  const { snapshot, connected } = useLiveMetrics()

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>PulseStream</h1>
          <p className="subtitle">Real-time e-commerce analytics</p>
        </div>
        <div className={`status ${connected ? 'on' : 'off'}`}>
          <span className="dot" />
          {connected ? 'Live' : 'Reconnecting…'}
        </div>
      </header>

      {!snapshot ? (
        <div className="card loading">Connecting to stream…</div>
      ) : (
        <>
          <section className="kpis">
            <KpiCard
              label="Events / sec"
              value={snapshot.events_per_second}
              sub="last 10s average"
            />
            <KpiCard
              label="Orders (5 min)"
              value={snapshot.window_orders}
              sub={`$${snapshot.window_revenue.toLocaleString()} revenue`}
            />
            <KpiCard
              label="Page views (5 min)"
              value={(snapshot.by_type.page_view || 0).toLocaleString()}
            />
            <KpiCard
              label="Signups (5 min)"
              value={(snapshot.by_type.signup || 0).toLocaleString()}
            />
          </section>

          <section className="grid">
            <div className="card chart-card">
              <h2>Throughput</h2>
              <p className="card-sub">Events per second, last 2 minutes</p>
              <LineChart data={snapshot.per_second_history} />
            </div>
            <div className="card">
              <h2>Top products</h2>
              <p className="card-sub">By revenue, last 5 minutes</p>
              <TopProducts products={snapshot.top_products} />
            </div>
          </section>

          <section className="card">
            <h2>Live event feed</h2>
            <p className="card-sub">Latest events off the stream</p>
            <EventFeed events={snapshot.recent_events} />
          </section>

          <footer className="footer">
            {snapshot.total_events.toLocaleString()} events processed since
            startup · uptime {Math.round(snapshot.uptime_seconds)}s
          </footer>
        </>
      )}
    </div>
  )
}
