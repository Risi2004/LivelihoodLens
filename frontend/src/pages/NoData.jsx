import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getDistricts } from '../api'
import StatusMessage from '../components/StatusMessage'
import { formatDate, formatLkr, formatNumber } from '../format'
import { hoursLabel, skillLabel } from '../options'
import { recommendAndGo, useRecommendation } from '../useRecommendation'

const COVERAGE_LABELS = { adequate: 'Good', low: 'Low', insufficient: 'Insufficient' }

function SearchAlertIcon() {
  return (
    <span className="mx-auto flex size-24 items-center justify-center rounded-full bg-amber-50">
      <svg viewBox="0 0 48 48" className="size-11 text-amber-700" aria-hidden="true">
        <circle cx="21" cy="21" r="13" fill="none" stroke="currentColor" strokeWidth="3.5" />
        <path d="m31 31 9 9" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
        <path d="M21 13.5v9M21 28v.5" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
      </svg>
    </span>
  )
}

function Explanation({ response, district }) {
  if (response.failed_rule === 'stale_data') {
    // The heading already says we can't rank right now, so this only says why.
    const age = response.freshness.osm.age_days
    return (
      <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-stone-700">
        {age === null
          ? 'Business and price data are out of date'
          : `Business data is ${age} days old and price data is also out of date`}
        , so we won&apos;t guess.
      </p>
    )
  }
  if (!district) {
    return <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-stone-700">{response.reason}</p>
  }
  // Low coverage gets its own opening, so it reads differently from an insufficient district.
  const opening = district.coverage_flag === 'low' ? `Business mapping in ${district.name} is still incomplete. ` : ''
  const mapped = (
    <>
      {opening}Only about <strong className="text-ink">{formatNumber(district.total_businesses)} businesses</strong> are
      mapped
    </>
  )
  if (response.failed_rule === 'total_businesses') {
    return (
      <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-stone-700">
        {mapped}
        {opening ? '' : ` in ${district.name}`}. We need at least <strong className="text-ink">{response.min_required}</strong> to
        reliably compare local supply with what households spend, so we won&apos;t guess.
      </p>
    )
  }
  return (
    <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-stone-700">
      {mapped} for roughly <strong className="text-ink">{formatNumber(district.population)} people</strong>. With so
      few mapped, we can&apos;t reliably compare local supply with what households spend, so we won&apos;t guess.
    </p>
  )
}

// Bar of this district's value against the rule it failed. Colombo is shown for scale on the per-person rule.
function CoverageBar({ response, district, colombo }) {
  const byTotal = response.failed_rule === 'total_businesses'
  const value = byTotal ? district.total_businesses : district.per_10k
  const minimum = response.min_required
  const reference = !byTotal && colombo && colombo.name !== district.name ? colombo.per_10k : null
  const scaleMax = Math.max(value, minimum, reference ?? 0) * (reference ? 1 : 1.25)
  const percent = (number) => `${Math.min(100, (number / scaleMax) * 100)}%`

  return (
    <div className="mx-auto mt-8 max-w-xl rounded-xl bg-stone-50 p-5 text-left">
      <div className="flex items-baseline justify-between gap-3">
        <p className="font-semibold text-ink">{byTotal ? 'Businesses mapped' : 'Businesses mapped per 10,000 people'}</p>
        <p className="font-mono font-semibold text-ink">{byTotal ? formatNumber(value) : value.toFixed(1)}</p>
      </div>
      <div className="relative mt-3 h-3 rounded-full bg-stone-200" aria-hidden="true">
        <div className="h-full rounded-full bg-amber-600" style={{ width: percent(value) }} />
        <div className="absolute -top-1.5 h-6 w-0.5 bg-ink" style={{ left: percent(minimum) }} />
      </div>
      <div className="mt-3 flex flex-wrap justify-between gap-x-4 gap-y-1 text-sm text-stone-600">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-amber-600" aria-hidden="true" />
          {district.name}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3.5 w-0.5 bg-ink" aria-hidden="true" />
          Minimum to rank: {formatNumber(minimum)}
        </span>
        {reference && <span>Colombo: ~{Math.round(reference)}</span>}
      </div>
    </div>
  )
}

function SideCard({ title, children }) {
  return (
    <section className="rounded-2xl border border-stone-200 bg-white p-6">
      <h2 className="text-lg font-bold text-ink">{title}</h2>
      {children}
    </section>
  )
}

function CheckRow({ label, value, tone = 'normal' }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-stone-100 py-3 last:border-0">
      <dt className="text-stone-600">{label}</dt>
      <dd className={`text-right font-mono font-semibold ${tone === 'warn' ? 'text-amber-700' : 'text-ink'}`}>{value}</dd>
    </div>
  )
}

const primaryButton =
  'inline-flex items-center justify-center rounded-xl bg-brand px-6 py-3.5 font-bold text-white transition-colors hover:bg-brand-dark disabled:opacity-70'
const outlineButton =
  'inline-flex items-center justify-center rounded-xl border-2 border-brand px-6 py-3 font-bold text-brand transition-colors hover:bg-brand-soft disabled:opacity-70'

export default function NoData() {
  const navigate = useNavigate()
  const { response, profile, loading, error } = useRecommendation('/no-data')
  const [districts, setDistricts] = useState([])
  const [showNeighbours, setShowNeighbours] = useState(false)
  const [checking, setChecking] = useState(null)
  const [retryError, setRetryError] = useState(null)

  useEffect(() => {
    getDistricts().then((result) => {
      if (result.ok) setDistricts(result.data)
    })
  }, [])

  if (loading || error) return <StatusMessage loading={loading} error={error} />

  const district = districts.find((d) => d.name === response.district)
  const colombo = districts.find((d) => d.name === 'Colombo')
  const freshness = response.freshness
  const suggestions = response.suggestions
  const stale = response.failed_rule === 'stale_data'

  async function tryDistrict(name) {
    setChecking(name)
    setRetryError(null)
    const message = await recommendAndGo(navigate, { ...profile, district: name })
    setChecking(null)
    if (message) setRetryError(message)
  }

  function chooseAnother() {
    navigate('/', { state: { profile: { ...profile, district: '' } } })
  }

  const skills = profile.skills.map(skillLabel).join(', ')

  return (
    <div className="space-y-6">
      <div>
        <Link to="/" state={{ profile }} className="font-semibold text-brand hover:underline">
          ← Edit your answers
        </Link>
        <p className="mt-2 text-stone-600">
          {response.district} · Budget {formatLkr(profile.budget_lkr)} · {skills} · {hoursLabel(profile.hours)} hours a
          week
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-2xl border border-stone-200 bg-white p-6 text-center sm:p-10">
          <SearchAlertIcon />
          <h1 className="mt-6 text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
            We can&apos;t rank {response.district} {stale ? 'right now' : 'yet'}
          </h1>
          <Explanation response={response} district={district} />
          {district && !stale && <CoverageBar response={response} district={district} colombo={colombo} />}

          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <button type="button" onClick={chooseAnother} className={primaryButton}>
              Choose another district
            </button>
            {suggestions.length > 0 && (
              <button
                type="button"
                onClick={() => setShowNeighbours((open) => !open)}
                aria-expanded={showNeighbours}
                className={outlineButton}
              >
                See neighbouring districts
              </button>
            )}
          </div>

          {showNeighbours && (
            <div className="mt-6">
              <p className="text-sm text-stone-600">These neighbours have enough businesses mapped to rank:</p>
              <div className="mt-3 flex flex-wrap justify-center gap-3">
                {suggestions.map((name) => (
                  <button
                    key={name}
                    type="button"
                    onClick={() => tryDistrict(name)}
                    disabled={checking !== null}
                    className="rounded-full border border-brand px-5 py-2 font-semibold text-brand hover:bg-brand-soft disabled:opacity-60"
                  >
                    {checking === name ? `Checking ${name}…` : name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {retryError && (
            <p role="alert" className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {retryError}
            </p>
          )}
        </section>

        <div className="space-y-6 lg:self-start">
          <SideCard title="What you can do">
            <ul className="mt-4 space-y-4 text-stone-700">
              {suggestions.length > 0 && (
                <li>
                  Try a neighbouring district such as{' '}
                  <button
                    type="button"
                    onClick={() => tryDistrict(suggestions[0])}
                    disabled={checking !== null}
                    className="font-semibold text-brand underline"
                  >
                    {suggestions[0]}
                  </button>
                  , where coverage is good enough to rank.
                </li>
              )}
              <li>Talk to your local livelihood or Samurdhi officer about demand in your area.</li>
              <li>Check again later: business data was last updated {formatDate(freshness.osm.date)}.</li>
            </ul>
          </SideCard>

          <SideCard title={`Data checks for ${response.district}`}>
            <dl className="mt-3">
              <CheckRow
                label="Map coverage"
                value={district ? COVERAGE_LABELS[district.coverage_flag] : '…'}
                tone={district?.coverage_flag === 'adequate' ? 'normal' : 'warn'}
              />
              <CheckRow
                label="Businesses data"
                value={formatDate(freshness.osm.date)}
                tone={freshness.osm.stale ? 'warn' : 'normal'}
              />
              <CheckRow label="Household spending" value={freshness.hies.year} />
            </dl>
          </SideCard>
        </div>
      </div>
    </div>
  )
}
