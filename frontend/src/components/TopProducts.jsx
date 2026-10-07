export default function TopProducts({ products }) {
  if (!products || products.length === 0) {
    return <p className="empty">No orders in the window yet.</p>
  }
  const maxRevenue = Math.max(...products.map((p) => p.revenue), 1)

  return (
    <ul className="products">
      {products.map((p, i) => (
        <li key={p.product_id} className="product-row">
          <span className="rank">{i + 1}</span>
          <div className="product-info">
            <div className="product-name">{p.name}</div>
            <div className="product-meta">
              {p.orders} order{p.orders === 1 ? '' : 's'}
            </div>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${(p.revenue / maxRevenue) * 100}%` }}
              />
            </div>
          </div>
          <span className="product-revenue">${p.revenue.toLocaleString()}</span>
        </li>
      ))}
    </ul>
  )
}
