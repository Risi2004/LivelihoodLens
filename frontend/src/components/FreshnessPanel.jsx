import { formatDate } from '../format'

// stale: a refreshing source that missed its refresh. old: a fixed survey shown in amber because of its age.
function SourceRow({ label, source, value, stale = false, old = false }) {
  return (
    <li className="flex items-start justify-between gap-4 border-b border-stone-100 py-3 last:border-0">
      <div>
        <p className="text-[15px] text-ink">{label}</p>
        <p className="text-xs text-stone-500">{source}</p>
      </div>
      <p className={`text-right font-mono text-sm ${stale || old ? 'text-amber-700' : 'text-ink'}`}>
        {value}
        {stale && <span className="block font-sans text-xs">out of date</span>}
      </p>
    </li>
  )
}

function StatusPill({ upToDate }) {
  return upToDate ? (
    <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand-dark">Up to date</span>
  ) : (
    <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">Some data is old</span>
  )
}

// freshness is the API's freshness block (GET /freshness, or the one inside a recommendation).
export default function FreshnessPanel({ freshness, error, className = '' }) {
  return (
    <section className={`rounded-2xl border border-stone-200 bg-white p-6 ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-ink">Data freshness</h2>
        {freshness && <StatusPill upToDate={!freshness.osm.stale && !freshness.prices.stale} />}
      </div>

      {error && <p className="mt-4 text-sm text-stone-600">{error}</p>}
      {!freshness && !error && <p className="mt-4 text-sm text-stone-500">Checking data dates…</p>}

      {freshness && (
        <>
          <ul className="mt-3">
            <SourceRow
              label="Local businesses"
              source="OpenStreetMap"
              value={formatDate(freshness.osm.date)}
              stale={freshness.osm.stale}
            />
            <SourceRow
              label="Food prices"
              source="Central Bank daily report"
              value={formatDate(freshness.prices.date)}
              stale={freshness.prices.stale}
            />
            <SourceRow
              label="Household spending"
              source="HIES, Dept. of Census & Statistics"
              value={freshness.hies.year}
              old={freshness.hies.over_age_limit}
            />
            <SourceRow label="Population" source="DCS mid-year estimates" value={freshness.population.year} />
          </ul>
          {freshness.hies.over_age_limit && (
            <p className="mt-3 text-xs leading-relaxed text-stone-500">
              Household spending comes from {freshness.hies.year}, before the 2022 economic crisis, so we use only how
              spending is shared between categories.
            </p>
          )}
          {freshness.placeholder && (
            <p className="mt-3 rounded-lg bg-stone-100 px-3 py-2 text-xs text-stone-600">
              Demo data – not real figures
            </p>
          )}
        </>
      )}
    </section>
  )
}
