const STYLES = {
  high: { pill: 'bg-emerald-50 text-emerald-900', dot: 'bg-emerald-600' },
  medium: { pill: 'bg-amber-50 text-amber-900', dot: 'bg-amber-500' },
  low: { pill: 'bg-orange-50 text-orange-900', dot: 'bg-orange-600' },
}

// level is "high", "medium", "low", or null when there are no results to rate.
export default function ConfidenceBadge({ level }) {
  const style = STYLES[level] ?? { pill: 'bg-stone-100 text-stone-700', dot: 'bg-stone-400' }
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold ${style.pill}`}
    >
      <span className={`size-2.5 rounded-full ${style.dot}`} aria-hidden="true" />
      Confidence: {level ?? 'not available'}
    </span>
  )
}
