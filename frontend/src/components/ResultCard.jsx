import { formatDate, formatLkrRange } from '../format'
import { skillLabel } from '../options'

const RANK_LABELS = ['Best match', 'Option 2', 'Option 3']

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-5 shrink-0" aria-hidden="true">
      <path d="m4.5 10.5 3.5 3.5 7.5-8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function AlertIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-5 shrink-0" aria-hidden="true">
      <circle cx="10" cy="10" r="7.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10 6v4.5M10 13.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-5 shrink-0" aria-hidden="true">
      <path d="M10 3 18 17H2L10 3Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M10 8v4M10 14.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function ScoreBar({ score, className = '' }) {
  return (
    <div className={`h-2.5 overflow-hidden rounded-full bg-stone-200 ${className}`} aria-hidden="true">
      <div className="h-full rounded-full bg-brand" style={{ width: `${score}%` }} />
    </div>
  )
}

function SourceChip({ children, stale }) {
  return (
    <span
      className={`rounded-md px-2.5 py-1 font-mono text-xs ${stale ? 'bg-amber-50 text-amber-800' : 'bg-stone-100 text-stone-700'}`}
    >
      {children}
    </span>
  )
}

function FitLine({ budgetFit }) {
  if (budgetFit === 'lower_end') {
    return (
      <p className="flex items-center gap-2 font-semibold text-amber-800">
        <AlertIcon /> Lower end fits your budget
      </p>
    )
  }
  return (
    <p className="flex items-center gap-2 font-semibold text-brand">
      <CheckIcon /> Fits your budget and skills
    </p>
  )
}

// card is one item of the API's results list; rank is its position, from 0.
export default function ResultCard({ card, rank, freshness }) {
  const best = rank === 0
  const pressure = card.cost_pressure
  const usesPrices = pressure.items_used.length > 0 || pressure.stale

  return (
    <article
      className={`flex flex-col rounded-2xl bg-white p-6 break-inside-avoid ${best ? 'border-2 border-brand' : 'border border-stone-200'}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className={`text-sm font-bold tracking-wider uppercase ${best ? 'text-brand' : 'text-stone-500'}`}>
            {RANK_LABELS[rank]}
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-ink">{card.label}</h2>
        </div>
        <p className="text-right">
          <span className="block text-5xl leading-none font-extrabold text-brand">{card.gap_score}</span>
          <span className="text-sm whitespace-nowrap text-stone-500">gap score</span>
        </p>
      </div>
      <ScoreBar score={card.gap_score} className="mt-5" />

      <dl className="mt-5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <dt className="whitespace-nowrap text-stone-600">Start-up cost</dt>
        <dd className="font-bold whitespace-nowrap text-ink">{formatLkrRange(card.cost_min_lkr, card.cost_max_lkr)}</dd>
      </dl>
      <div className="mt-3 border-b border-stone-200 pb-5">
        <FitLine budgetFit={card.budget_fit} />
      </div>

      <h3 className="mt-5 font-bold text-ink">Why this ranks here</h3>
      <p className="mt-1 leading-relaxed text-stone-700">{card.why}</p>

      {pressure.warning && (
        <div className="mt-5 rounded-xl bg-amber-50 p-4 text-amber-900">
          <p className="flex items-center gap-2 font-bold">
            <WarningIcon /> Cost pressure
          </p>
          <p className="mt-1 leading-relaxed">{pressure.message}</p>
        </div>
      )}

      <div className="mt-auto flex flex-wrap gap-2 pt-5">
        <SourceChip stale={false}>Spending · {freshness.hies.year}</SourceChip>
        <SourceChip stale={freshness.osm.stale}>Shops · {formatDate(freshness.osm.date, { withYear: false })}</SourceChip>
        {usesPrices && (
          <SourceChip stale={freshness.prices.stale}>
            Prices · {formatDate(freshness.prices.date, { withYear: false })}
          </SourceChip>
        )}
      </div>
    </article>
  )
}

// A lighter card for a category that needs a skill the user didn't select.
export function OtherOptionCard({ option }) {
  return (
    <article className="rounded-xl border border-dashed border-stone-300 bg-white/60 p-4 break-inside-avoid">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-bold text-ink">{option.label}</h3>
        <p className="text-right">
          <span className="block text-2xl leading-none font-extrabold text-stone-700">{option.gap_score}</span>
          <span className="text-xs whitespace-nowrap text-stone-500">gap score</span>
        </p>
      </div>
      <p className="mt-2 text-sm text-stone-600">
        {formatLkrRange(option.cost_min_lkr, option.cost_max_lkr)}
        {option.budget_fit === 'lower_end' && ' · lower end fits your budget'}
      </p>
      <p className="mt-1 text-sm font-semibold text-stone-700">
        Needs: {option.needs_skills.map(skillLabel).join(' or ')}
      </p>
    </article>
  )
}
