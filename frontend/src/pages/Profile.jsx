import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getDistricts, getFreshness } from '../api'
import FreshnessPanel from '../components/FreshnessPanel'
import { formatLkr } from '../format'
import { BUDGET, HOURS, SKILLS } from '../options'
import { loadProfile } from '../session'
import { recommendAndGo } from '../useRecommendation'

const STEPS = [
  { title: 'Demand:', text: 'what households in your district spend on each kind of goods and service.' },
  { title: 'Supply:', text: 'how many local businesses already serve it.' },
  { title: 'Gap:', text: 'where demand is high and supply is thin, filtered to your budget and skills.' },
]

function chipClass(selected) {
  const base =
    'rounded-full border px-5 py-2.5 text-[15px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'
  return selected
    ? `${base} border-brand bg-brand text-white`
    : `${base} border-stone-300 bg-white text-ink hover:border-stone-400`
}

function FieldLabel({ id, children, hint }) {
  return (
    <p id={id} className="mb-3 text-[15px] font-semibold text-ink">
      {children} {hint && <span className="font-normal text-stone-500">{hint}</span>}
    </p>
  )
}

function DistrictSelect({ districts, error, value, onChange }) {
  const pilots = districts.filter((d) => d.is_pilot)
  const others = districts.filter((d) => !d.is_pilot)
  const option = (d) => (
    <option key={d.name} value={d.name}>
      {d.name}
      {d.coverage_flag === 'adequate' ? '' : ' (limited map data)'}
    </option>
  )

  return (
    <div>
      <label htmlFor="district" className="mb-3 block text-[15px] font-semibold text-ink">
        District
      </label>
      <select
        id="district"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={!districts.length}
        className="w-full rounded-xl border border-stone-300 bg-white px-4 py-3.5 text-lg text-ink focus:border-brand focus:outline-2 focus:outline-brand/30 disabled:bg-stone-50 disabled:text-stone-400"
      >
        <option value="">{districts.length ? 'Choose your district' : 'Loading districts…'}</option>
        {pilots.length > 0 && <optgroup label="Pilot districts">{pilots.map(option)}</optgroup>}
        {others.length > 0 && <optgroup label="Other districts">{others.map(option)}</optgroup>}
      </select>
      {error && <p className="mt-2 text-sm text-amber-800">{error}</p>}
    </div>
  )
}

function BudgetSlider({ value, onChange }) {
  return (
    <div>
      <label htmlFor="budget" className="mb-2 block text-[15px] font-semibold text-ink">
        Budget to invest
      </label>
      <p className="text-4xl font-extrabold tracking-tight text-ink" aria-hidden="true">
        {formatLkr(value)}
      </p>
      <input
        id="budget"
        type="range"
        min={BUDGET.min}
        max={BUDGET.max}
        step={BUDGET.step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-valuetext={formatLkr(value)}
        className="mt-4 w-full accent-brand"
      />
      <div className="mt-1 flex justify-between text-sm text-stone-500">
        <span>{BUDGET.min.toLocaleString('en-US')}</span>
        <span>{BUDGET.max.toLocaleString('en-US')}</span>
      </div>
    </div>
  )
}

const ARROW_STEPS = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }

// A radio group: one Tab stop, arrow keys move and select, as screen reader users expect.
function HoursPicker({ value, onChange }) {
  const buttons = useRef([])
  const selectedIndex = HOURS.findIndex((hours) => hours.id === value)
  const tabIndex = selectedIndex === -1 ? 0 : selectedIndex

  function handleKeyDown(event, index) {
    let next = null
    if (event.key in ARROW_STEPS) next = (index + ARROW_STEPS[event.key] + HOURS.length) % HOURS.length
    if (event.key === 'Home') next = 0
    if (event.key === 'End') next = HOURS.length - 1
    if (next === null) return
    event.preventDefault()
    onChange(HOURS[next].id)
    buttons.current[next]?.focus()
  }

  return (
    <div role="radiogroup" aria-labelledby="hours-label" className="flex flex-wrap gap-3">
      {HOURS.map((hours, index) => {
        const selected = hours.id === value
        return (
          <button
            key={hours.id}
            ref={(element) => {
              buttons.current[index] = element
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={index === tabIndex ? 0 : -1}
            onClick={() => onChange(hours.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={chipClass(selected)}
          >
            {hours.label}
          </button>
        )
      })}
    </div>
  )
}

function HowItWorks() {
  return (
    <section className="rounded-2xl border border-stone-200 bg-white p-6">
      <h2 className="text-lg font-bold text-ink">How it works</h2>
      <ol className="mt-4 space-y-5">
        {STEPS.map((step, index) => (
          <li key={step.title} className="flex gap-4">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-soft font-bold text-brand-dark">
              {index + 1}
            </span>
            <p className="leading-relaxed text-stone-700">
              <strong className="font-semibold text-ink">{step.title}</strong> {step.text}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}

function initialProfile(location) {
  // "Edit your answers" passes the profile in router state; a refresh falls back to sessionStorage.
  const saved = location.state?.profile ?? loadProfile()
  return {
    district: saved?.district ?? '',
    budget_lkr: saved?.budget_lkr ?? BUDGET.default,
    skills: saved?.skills ?? [],
    hours: saved?.hours ?? '',
  }
}

function missingAnswers(profile) {
  const missing = []
  if (!profile.district) missing.push('choose your district')
  if (!profile.skills.length) missing.push('choose at least one skill')
  if (!profile.hours) missing.push('choose how many hours you can work')
  return missing
}

export default function Profile() {
  const location = useLocation()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(() => initialProfile(location))
  const [districts, setDistricts] = useState([])
  const [districtError, setDistrictError] = useState(null)
  const [freshness, setFreshness] = useState(null)
  const [freshnessError, setFreshnessError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  useEffect(() => {
    getDistricts().then((result) => {
      if (result.ok) setDistricts(result.data)
      else setDistrictError(result.error)
    })
    getFreshness().then((result) => {
      if (result.ok) setFreshness(result.data)
      else setFreshnessError(result.error)
    })
  }, [])

  function update(field, value) {
    setProfile((current) => ({ ...current, [field]: value }))
    setFormError(null)
  }

  function toggleSkill(id) {
    const skills = profile.skills.includes(id) ? profile.skills.filter((s) => s !== id) : [...profile.skills, id]
    update('skills', skills)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const missing = missingAnswers(profile)
    if (missing.length) {
      setFormError(`Please ${missing.join(', ')}.`)
      return
    }

    setSubmitting(true)
    setFormError(null)
    const error = await recommendAndGo(navigate, profile)
    if (error) {
      setSubmitting(false)
      setFormError(error)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <form
        onSubmit={handleSubmit}
        noValidate
        className="rounded-2xl border border-stone-200 bg-white p-6 sm:p-10"
        aria-describedby={formError ? 'form-error' : undefined}
      >
        <p className="text-sm font-semibold tracking-wider text-brand uppercase">Step 1 of 2</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-ink sm:text-[42px] sm:leading-tight">
          What could you start in your district?
        </h1>
        <p className="mt-3 text-lg leading-relaxed text-stone-600">
          Answer four questions. We compare local household spending with the businesses already there, and show what
          your area is missing. Nothing you enter is stored.
        </p>

        <div className="mt-8 grid gap-8 md:grid-cols-2">
          <DistrictSelect
            districts={districts}
            error={districtError}
            value={profile.district}
            onChange={(value) => update('district', value)}
          />
          <BudgetSlider value={profile.budget_lkr} onChange={(value) => update('budget_lkr', value)} />
        </div>

        <fieldset className="mt-8">
          <legend className="contents">
            <FieldLabel hint="(choose any)">Your skills</FieldLabel>
          </legend>
          <div className="flex flex-wrap gap-3">
            {SKILLS.map((skill) => {
              const selected = profile.skills.includes(skill.id)
              return (
                <button
                  key={skill.id}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => toggleSkill(skill.id)}
                  className={chipClass(selected)}
                >
                  {skill.label}
                </button>
              )
            })}
          </div>
        </fieldset>

        <div className="mt-8">
          <FieldLabel id="hours-label">Hours you can work each week</FieldLabel>
          <HoursPicker value={profile.hours} onChange={(value) => update('hours', value)} />
        </div>

        <div className="mt-10 flex flex-col gap-5 border-t border-stone-200 pt-8 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-sm text-sm leading-relaxed text-stone-500">
            Results are a demand indicator, not financial advice or a promise of profit.
          </p>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-8 py-4 text-lg font-bold text-white transition-colors hover:bg-brand-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-wait disabled:opacity-70"
          >
            {submitting ? 'Finding opportunities…' : 'Find opportunities'}
            {!submitting && <span aria-hidden="true">→</span>}
          </button>
        </div>

        {formError && (
          <p id="form-error" role="alert" className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {formError}
          </p>
        )}
      </form>

      <div className="space-y-6 lg:self-start">
        <HowItWorks />
        <FreshnessPanel freshness={freshness} error={freshnessError} />
      </div>
    </div>
  )
}
