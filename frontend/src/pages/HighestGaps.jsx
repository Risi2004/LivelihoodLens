import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { getCategories, getDistricts, getGaps } from '../api'
import { ScoreBar } from '../components/ResultCard'
import { formatNumber } from '../format'

const COVERAGE_LABELS = { adequate: 'Good', low: 'Low', insufficient: 'Insufficient' }

function RankedRow({ rank, row, district }) {
  return (
    <li className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 border-b border-stone-100 py-4 last:border-0 sm:grid-cols-[2.5rem_minmax(8rem,1fr)_minmax(0,2fr)_6rem_9rem]">
      <span className="text-stone-500">{rank}</span>
      <span className="font-semibold text-ink">{row.district}</span>
      <span className="text-right text-lg font-bold text-brand sm:order-last sm:hidden">{row.gap_score}</span>
      <div className="col-span-3 flex items-center gap-3 sm:col-span-1">
        <ScoreBar score={row.gap_score} className="flex-1" />
        <span className="hidden w-8 text-right font-bold text-brand sm:inline">{row.gap_score}</span>
      </div>
      <span className="col-span-3 text-sm text-stone-600 sm:col-span-1">
        <span className="sm:hidden">Map coverage: </span>
        {district ? COVERAGE_LABELS[district.coverage_flag] : '…'}
      </span>
      <span className="col-span-3 text-sm whitespace-nowrap text-stone-600 sm:col-span-1 sm:text-right">
        {district ? `${formatNumber(district.total_businesses)} businesses` : ''}
      </span>
    </li>
  )
}

function NotRankedRow({ row, district }) {
  const reason = row.coverage_flag === 'adequate' ? 'data out of date' : 'map coverage too low'
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-stone-100 py-3 text-stone-500 last:border-0">
      <span className="font-semibold">{row.district}</span>
      <span className="text-sm">
        Not ranked: {reason}
        {district && ` · ${formatNumber(district.total_businesses)} businesses`}
      </span>
    </li>
  )
}

export default function HighestGaps() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [categories, setCategories] = useState([])
  const [districts, setDistricts] = useState([])
  const [gaps, setGaps] = useState(null) // { categoryId, data } or { categoryId, error }
  const [listError, setListError] = useState(null)

  const requested = searchParams.get('category')
  const categoryId = categories.some((c) => c.id === requested) ? requested : categories[0]?.id

  useEffect(() => {
    getCategories().then((result) => {
      if (result.ok) setCategories(result.data)
      else setListError(result.error)
    })
    getDistricts().then((result) => {
      if (result.ok) setDistricts(result.data)
    })
  }, [])

  useEffect(() => {
    if (!categoryId) return
    getGaps(categoryId).then((result) => {
      setGaps(result.ok ? { categoryId, data: result.data } : { categoryId, error: result.error })
    })
  }, [categoryId])

  const current = gaps?.categoryId === categoryId ? gaps : null
  const byName = Object.fromEntries(districts.map((d) => [d.name, d]))
  const label = categories.find((c) => c.id === categoryId)?.label

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
            Where is {label ? label.toLowerCase() : 'each business type'} under-served?
          </h1>
          <p className="mt-3 text-lg leading-relaxed text-stone-600">
            Gap score by district: how much households spend on this compared with the share of local businesses
            already serving it.
          </p>
        </div>
        <div className="md:w-80">
          <label htmlFor="category" className="mb-2 block font-semibold text-ink">
            Business type
          </label>
          <select
            id="category"
            value={categoryId ?? ''}
            onChange={(event) => setSearchParams({ category: event.target.value })}
            disabled={!categories.length}
            className="w-full rounded-xl border border-stone-300 bg-white px-4 py-3 text-lg text-ink focus:border-brand focus:outline-2 focus:outline-brand/30"
          >
            {!categories.length && <option value="">{listError ? 'Business types unavailable' : 'Loading…'}</option>}
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {listError && <p className="rounded-lg bg-amber-50 px-4 py-3 text-amber-900">{listError}</p>}
      {current?.data?.freshness.placeholder && (
        <p className="rounded-lg bg-stone-200/70 px-4 py-2 text-sm text-stone-700">Demo data – not real figures</p>
      )}

      <section className="rounded-2xl border border-stone-200 bg-white p-6">
        <div className="hidden grid-cols-[2.5rem_minmax(8rem,1fr)_minmax(0,2fr)_6rem_9rem] gap-x-3 border-b border-stone-200 pb-3 text-sm font-semibold text-stone-500 sm:grid">
          <span>#</span>
          <span>District</span>
          <span>Gap score</span>
          <span>Map coverage</span>
          <span className="text-right">Mapped</span>
        </div>
        {!current && !listError && <p className="py-6 text-stone-500">Loading districts…</p>}
        {current?.error && <p className="py-6 text-amber-800">{current.error}</p>}
        {current?.data && (
          <>
            {current.data.ranked.length === 0 && (
              <p className="py-6 text-stone-600">No district can be ranked with the current data.</p>
            )}
            <ol>
              {current.data.ranked.map((row, index) => (
                <RankedRow key={row.district} rank={index + 1} row={row} district={byName[row.district]} />
              ))}
            </ol>
            {current.data.not_ranked.length > 0 && (
              <>
                <h2 className="mt-6 text-sm font-semibold text-stone-500">
                  {current.data.not_ranked.length} districts not ranked
                </h2>
                <ul>
                  {current.data.not_ranked.map((row) => (
                    <NotRankedRow key={row.district} row={row} district={byName[row.district]} />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </section>

      <p className="text-stone-600">
        Want results for your own budget and skills?{' '}
        <Link to="/" className="font-semibold text-brand underline">
          Find opportunities
        </Link>
      </p>
    </div>
  )
}
