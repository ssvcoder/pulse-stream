import { useEffect, useRef } from 'react'

// Dependency-free canvas line chart. Redraws whenever the data changes
// and on window resize; handles high-DPI screens via devicePixelRatio.
export default function LineChart({ data }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !data || data.length < 2) return

    const draw = () => {
      const dpr = window.devicePixelRatio || 1
      const rect = canvas.getBoundingClientRect()
      const width = rect.width
      const height = rect.height
      if (width === 0 || height === 0) return

      canvas.width = width * dpr
      canvas.height = height * dpr
      const ctx = canvas.getContext('2d')
      ctx.scale(dpr, dpr)
      ctx.clearRect(0, 0, width, height)

      const pad = { left: 6, right: 44, top: 12, bottom: 20 }
      const innerW = width - pad.left - pad.right
      const innerH = height - pad.top - pad.bottom
      const max = Math.max(...data.map((d) => d.count), 1)

      const x = (i) => pad.left + (i / (data.length - 1)) * innerW
      const y = (v) => pad.top + innerH - (v / max) * innerH

      // Horizontal gridlines + value labels.
      ctx.font = '10px system-ui, sans-serif'
      ctx.fillStyle = '#5b6b82'
      ctx.strokeStyle = '#1e2a3d'
      ctx.lineWidth = 1
      const steps = 4
      for (let s = 0; s <= steps; s++) {
        const value = (max / steps) * s
        const gy = y(value)
        ctx.beginPath()
        ctx.moveTo(pad.left, gy)
        ctx.lineTo(width - pad.right, gy)
        ctx.stroke()
        ctx.fillText(Math.round(value).toString(), width - pad.right + 6, gy + 3)
      }

      // Area fill under the line.
      const gradient = ctx.createLinearGradient(0, pad.top, 0, height - pad.bottom)
      gradient.addColorStop(0, 'rgba(56, 189, 248, 0.35)')
      gradient.addColorStop(1, 'rgba(56, 189, 248, 0.02)')
      ctx.beginPath()
      data.forEach((d, i) => (i === 0 ? ctx.moveTo(x(i), y(d.count)) : ctx.lineTo(x(i), y(d.count))))
      ctx.lineTo(x(data.length - 1), height - pad.bottom)
      ctx.lineTo(x(0), height - pad.bottom)
      ctx.closePath()
      ctx.fillStyle = gradient
      ctx.fill()

      // The line itself.
      ctx.beginPath()
      data.forEach((d, i) => (i === 0 ? ctx.moveTo(x(i), y(d.count)) : ctx.lineTo(x(i), y(d.count))))
      ctx.strokeStyle = '#38bdf8'
      ctx.lineWidth = 2
      ctx.lineJoin = 'round'
      ctx.stroke()

      // Current value marker.
      const last = data[data.length - 1]
      ctx.beginPath()
      ctx.arc(x(data.length - 1), y(last.count), 3.5, 0, Math.PI * 2)
      ctx.fillStyle = '#38bdf8'
      ctx.fill()
    }

    draw()
    window.addEventListener('resize', draw)
    return () => window.removeEventListener('resize', draw)
  }, [data])

  return <canvas ref={canvasRef} className="line-chart" aria-label="Events per second chart" />
}
