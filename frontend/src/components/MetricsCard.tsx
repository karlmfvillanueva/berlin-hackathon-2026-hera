import { Card } from "@/components/ui/card"

type Props = {
  label: string
  value: string | number
  hint?: string
}

export function MetricsCard({ label, value, hint }: Props) {
  return (
    <Card className="p-5">
      <p className="text-label text-secondary mb-2">{label}</p>
      <p className="text-display">{value}</p>
      {hint && <p className="text-body-sm text-muted-foreground mt-2">{hint}</p>}
    </Card>
  )
}
