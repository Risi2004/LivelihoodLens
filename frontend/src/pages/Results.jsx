import { Link, useNavigate } from 'react-router-dom'

import ConfidenceBadge from '../components/ConfidenceBadge'
import Disclaimer from '../components/Disclaimer'
import ResultCard, { OtherOptionCard } from '../components/ResultCard'
import StatusMessage from '../components/StatusMessage'
import { formatLkr, formatToday } from '../format'
import { hoursLabel, skillLabel } from '../options'
import { useRecommendation } from '../useRecommendation'

// Column count follows the number of cards, so one or two cards don't look like gaps.
// On paper the cards stack, because three columns are too narrow on A4.
const GRID_BY_COUNT = {
  1: 'max-w-md print:max-w-none',
  2: 'md:grid-cols-2 max-w-4xl print:max-w-none print:grid-cols-1',
  3: 'md:grid-cols-2 lg:grid-cols-3 print:grid-cols-1',
}

function heading(count, district) {
  if (count === 0) return `No matches in ${district} yet`
  if (count === 1) return `Top opportunity in ${district}`
  return `Top ${count} opportunities in ${district}`
}

function profileLine(profile) {
  const skills = profile.skills.map(skillLabel).join(', ')
  return `Budget ${formatLkr(profile.budget_lkr)} · ${skills} · ${hoursLabel(profile.hours)} hours a week`
}

const outlineButton =
  'inline-flex items-center justify-center rounded-xl border-2 border-brand px-6 py-3 font-bold text-brand transition-colors hover:bg-brand-soft'

export default function Results() {
  const navigate = useNavigate()
  const { response, profile, loading, error } = useRecommendation('/results')
  if (loading || error) return <StatusMessage loading={loading} error={error} />

  const results = response.results
  const others = response.other_options
  const freshness = response.freshness
  const topCategory = results[0]?.category_id ?? others[0]?.category_id

  return (
    <div className="space-y-8">
      {freshness.placeholder && (
        <p className="rounded-lg bg-stone-200/70 px-4 py-2 text-sm text-stone-700">Demo data – not real figures</p>
      )}

      <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div>
          <Link to="/" state={{ profile }} className="font-semibold text-brand hover:underline print:hidden">
            ← Edit your answers
          </Link>
          <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-ink sm:text-[42px] sm:leading-tight">
            {heading(results.length, response.district)}
          </h1>
          <p className="mt-2 text-lg text-stone-600">{profileLine(profile)}</p>
          <p className="mt-1 hidden text-sm text-stone-500 print:block">Printed {formatToday()}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {response.confidence && <ConfidenceBadge level={response.confidence} />}
          {results.length > 0 && (
            <button type="button" onClick={() => window.print()} className={`${outlineButton} print:hidden`}>
              Print / save PDF
            </button>
          )}
        </div>
      </div>

      {results.length > 0 ? (
        <div className={`grid gap-6 ${GRID_BY_COUNT[results.length]}`}>
          {results.map((card, rank) => (
            <ResultCard key={card.category_id} card={card} rank={rank} freshness={freshness} />
          ))}
        </div>
      ) : (
        <section className="rounded-2xl border border-stone-200 bg-white p-8">
          <h2 className="text-xl font-bold text-ink">Try changing your answers</h2>
          <p className="mt-2 max-w-2xl leading-relaxed text-stone-700">{response.message}</p>
          <Link to="/" state={{ profile }} className={`${outlineButton} mt-5 print:hidden`}>
            Change your answers
          </Link>
        </section>
      )}

      {results.length > 0 && results.length < 3 && response.message && (
        <p className="text-stone-600">{response.message}</p>
      )}

      {others.length > 0 && (
        <section>
          <h2 className="text-lg font-bold text-stone-700">Also worth considering — needs a skill you didn&apos;t select</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {others.map((option) => (
              <OtherOptionCard key={option.category_id} option={option} />
            ))}
          </div>
        </section>
      )}

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex flex-wrap gap-3 print:hidden">
          {topCategory && (
            <Link to={`/gaps?category=${topCategory}`} className={outlineButton}>
              Compare districts
            </Link>
          )}
          <button
            type="button"
            onClick={() => navigate('/', { state: { profile: { ...profile, district: '' } } })}
            className={outlineButton}
          >
            Compare another district
          </button>
        </div>
        <Disclaimer text={response.disclaimer} className="max-w-xl" />
      </div>
    </div>
  )
}
