import * as React from "react"
import { motion } from "motion/react"

import { cn } from "@/lib/utils"

interface AnimatedListProps {
  children: React.ReactNode
  className?: string
  delay?: number
  staggerDelay?: number
}

/**
 * Stagger-reveals each child on mount. We avoid IntersectionObserver-gating
 * because the ideal wrapper for grid children is `display: contents`, which
 * has zero dimensions and never triggers IO. On-mount reveal keeps the
 * editorial feel without the layout coupling.
 */
export function AnimatedList({
  children,
  className,
  delay = 0,
  staggerDelay = 0.12,
}: AnimatedListProps) {
  const items = React.Children.toArray(children)

  return (
    <div className={cn("contents", className)}>
      {items.map((child, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.55,
            delay: delay + i * staggerDelay,
            ease: [0.16, 1, 0.3, 1],
          }}
        >
          {child}
        </motion.div>
      ))}
    </div>
  )
}
