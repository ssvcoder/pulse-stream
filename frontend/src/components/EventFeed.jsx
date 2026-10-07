const TYPE_LABELS = {
  order: 'ORDER',
  page_view: 'VIEW',
  signup: 'SIGNUP',
}

function describe(event) {
  switch (event.event_type) {
    case 'order':
      return `${event.product_name} — $${Number(event.amount).toFixed(2)}`
    case 'page_view':
      return `${event.page} via ${event.referrer}`
    case 'signup':
      return `${event.plan} plan`
    default:
      return event.event_type
  }
}

function timeAgo(iso) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  return `${Math.floor(seconds / 60)}m ago`
}

export default function EventFeed({ events }) {
  if (!events || events.length === 0) {
    return <p className="empty">Waiting for events…</p>
  }
  return (
    <ul className="feed">
      {events.map((event) => (
        <li key={event.event_id} className="feed-row">
          <span className={`badge badge-${event.event_type}`}>
            {TYPE_LABELS[event.event_type] || event.event_type}
          </span>
          <span className="feed-desc">{describe(event)}</span>
          <span className="feed-user">{event.user_id}</span>
          <span className="feed-time">{timeAgo(event.timestamp)}</span>
        </li>
      ))}
    </ul>
  )
}
