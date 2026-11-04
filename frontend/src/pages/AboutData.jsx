import { useEffect, useState } from 'react'

import { getFreshness } from '../api'
import Disclaimer from '../components/Disclaimer'
import { formatDate } from '../format'

const SCORE_STEPS = [
  {
    title: 'Demand',
    text: 'From the household survey, we work out what share of spending in your district goes to each of our 12 business types.',
  },
  {
    title: 'Supply',
    text: 'From the map, we work out what share of the district’s mapped businesses belong to each type. Using shares rather than counts means a district isn’t penalised just because fewer of its shops are mapped.',
  },
  {
    title: 'Gap',
    text: 'We compare the two. When households spend a bigger share on something than the share of businesses serving it, there may be room for one more.',
  },
  {
    title: 'Score',
    text: 'We turn each gap into a score from 0 to 100, ranked against every business type in every district we can rank, so scores can be compared between districts.',
  },
]

const NOT_DOING = [
  'It doesn’t give financial advice, and it can’t tell you how a business will do.',
  'It doesn’t know about rent, location, competition quality, or a business that closed there before.',
  'It doesn’t rank districts where too few businesses are mapped. It tells you so instead of guessing.',
  'It doesn’t store anything you enter.',
]

const CREDITS = [
  'Map data © OpenStreetMap contributors, available under the Open Database License (ODbL).',
  'District boundaries from geoBoundaries (gbOpen), under the Open Database License (ODbL).',
  'Household Income and Expenditure Survey 2019 and mid-year population estimates from the Department of Census and Statistics, Sri Lanka. Survey microdata is used under licence, and only district-level totals are shown.',
  'Daily Price Report from the Central Bank of Sri Lanka.',
]

function sources(freshness) {
  return [
    {
      name: 'Local businesses',
      from: 'OpenStreetMap, mapped by volunteers',
      use: 'How many shops and services of each type are already in your district.',
      date: freshness ? `Updated ${formatDate(freshness.osm.date)}` : null,
      stale: freshness?.osm.stale,
    },
    {
      name: 'Household spending',
      from: 'Household Income and Expenditure Survey, Dept. of Census & Statistics',
      use: 'How households in your district share their spending between kinds of goods and services. It was collected before the 2022 economic crisis, so we use only these shares, never rupee amounts.',
      date: freshness ? `Survey year ${freshness.hies.year}` : null,
    },
    {
      name: 'Population',
      from: 'Mid-year estimates, Dept. of Census & Statistics',
      use: 'How many businesses are mapped per person, to check whether a district is mapped well enough to rank.',
      date: freshness ? `Year ${freshness.population.year}` : null,
    },
    {
      name: 'Food prices',
      from: 'Daily Price Report, Central Bank of Sri Lanka',
      use: 'Whether ingredient prices for food businesses have risen over the last three months. This is a separate warning and never changes the score.',
      date: freshness ? `Updated ${formatDate(freshness.prices.date)}` : null,
      stale: freshness?.prices.stale,
    },
  ]
}

function Section({ title, children }) {
  return (
    <section className="rounded-2xl border border-stone-200 bg-white p-6 sm:p-8">
      <h2 className="text-xl font-bold text-ink">{title}</h2>
      {children}
    </section>
  )
}

export default function AboutData() {
  const [freshness, setFreshness] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getFreshness().then((result) => {
      if (result.ok) setFreshness(result.data)
      else setError(result.error)
    })
  }, [])

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">About the data</h1>
        <p className="mt-3 text-lg leading-relaxed text-stone-600">
          Livelihood Lens puts four public sources side by side to show which small business types a district may be
          missing. Here is where each number comes from, how old it is, and what the tool can&apos;t tell you.
        </p>
        {freshness?.placeholder && (
          <p className="mt-4 rounded-lg bg-stone-200/70 px-4 py-2 text-sm text-stone-700">
            Demo data – the app is currently running on placeholder figures, not real data.
          </p>
        )}
      </div>

      <Section title="Where the numbers come from">
        {error && <p className="mt-3 text-sm text-amber-800">{error} Dates are not shown.</p>}
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {sources(freshness).map((source) => (
            <article key={source.name} className="rounded-xl bg-stone-50 p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-bold text-ink">{source.name}</h3>
                {source.date && (
                  <span className={`font-mono text-sm ${source.stale ? 'text-amber-700' : 'text-stone-600'}`}>
                    {source.date}
                    {source.stale && ' · out of date'}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-stone-500">{source.from}</p>
              <p className="mt-3 leading-relaxed text-stone-700">{source.use}</p>
            </article>
          ))}
        </div>
      </Section>

      <Section title="How the gap score works">
        <ol className="mt-5 grid gap-5 md:grid-cols-2">
          {SCORE_STEPS.map((step, index) => (
            <li key={step.title} className="flex gap-4">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-soft font-bold text-brand-dark">
                {index + 1}
              </span>
              <p className="leading-relaxed text-stone-700">
                <strong className="font-semibold text-ink">{step.title}.</strong> {step.text}
              </p>
            </li>
          ))}
        </ol>
        <p className="mt-6 leading-relaxed text-stone-700">
          Each result also carries a confidence label. It drops when the survey is old, when the map or prices haven&apos;t
          been updated recently, or for business types the map rarely shows, such as home tuition.
        </p>
      </Section>

      <Section title="What this tool does not do">
        <ul className="mt-4 list-disc space-y-2 pl-5 leading-relaxed text-stone-700">
          {NOT_DOING.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <Disclaimer className="mt-5" />
      </Section>

      <Section title="Credits and licences">
        <ul className="mt-4 space-y-2 text-sm leading-relaxed text-stone-700">
          {CREDITS.map((credit) => (
            <li key={credit}>{credit}</li>
          ))}
        </ul>
      </Section>
    </div>
  )
}
