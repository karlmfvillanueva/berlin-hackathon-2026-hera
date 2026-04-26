import { useEffect, useState } from "react"
import { AnimatePresence, motion, type HTMLMotionProps } from "motion/react"

import { cn } from "@/lib/utils"

interface WordRotateProps {
  words: string[]
  duration?: number
  motionProps?: HTMLMotionProps<"span">
  className?: string
}

export function WordRotate({
  words,
  duration = 2500,
  motionProps,
  className,
}: WordRotateProps) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(
      () => setIndex((prev) => (prev + 1) % words.length),
      duration,
    )
    return () => clearInterval(interval)
  }, [words, duration])

  return (
    <span className={cn("relative inline-block overflow-hidden align-baseline", className)}>
      <AnimatePresence mode="wait">
        <motion.span
          key={words[index]}
          className="inline-block"
          initial={{ y: "100%", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: "-100%", opacity: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          {...motionProps}
        >
          {words[index]}
        </motion.span>
      </AnimatePresence>
    </span>
  )
}
