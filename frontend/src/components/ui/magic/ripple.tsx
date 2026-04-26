import { cn } from "@/lib/utils"

interface RippleProps {
  className?: string
  mainCircleSize?: number
  mainCircleOpacity?: number
  numCircles?: number
  color?: string
}

export function Ripple({
  className,
  mainCircleSize = 210,
  mainCircleOpacity = 0.18,
  numCircles = 6,
  color = "#F94B12",
}: RippleProps) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 select-none [mask-image:linear-gradient(to_bottom,white,transparent)]",
        className,
      )}
    >
      {Array.from({ length: numCircles }).map((_, i) => {
        const size = mainCircleSize + i * 70
        const opacity = mainCircleOpacity - i * 0.025
        const animationDelay = `${i * 0.18}s`
        const borderStyle = i === numCircles - 1 ? "dashed" : "solid"
        return (
          <div
            key={i}
            style={{
              width: `${size}px`,
              height: `${size}px`,
              opacity,
              animationDelay,
              borderStyle,
              borderColor: color,
              borderWidth: "1px",
            }}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-ripple rounded-full"
          />
        )
      })}
    </div>
  )
}
