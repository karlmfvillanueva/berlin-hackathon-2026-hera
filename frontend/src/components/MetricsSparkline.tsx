type Props = {
  values: number[]
  width?: number
  height?: number
  className?: string
}

export function MetricsSparkline({ values, width = 120, height = 30, className }: Props) {
  if (values.length < 2) {
    return (
      <div
        className={`text-body-sm text-muted-foreground ${className ?? ""}`}
        style={{ width, height }}
      >
        —
      </div>
    )
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const stepX = width / (values.length - 1)
  const path = values
    .map((v, i) => {
      const x = i * stepX
      const y = height - ((v - min) / range) * height
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
  return (
    <svg width={width} height={height} className={className} aria-hidden>
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
