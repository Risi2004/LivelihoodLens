// "2026-10-19" -> "19 Oct 2026". Parsed as a local date so it never shifts a day across time zones.
export function formatDate(isoDate, { withYear = true } = {}) {
  if (!isoDate) return 'Not available'
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    ...(withYear ? { year: 'numeric' } : {}),
  })
}

// 75000 -> "LKR 75,000"
export function formatLkr(amount) {
  return `LKR ${Number(amount).toLocaleString('en-US')}`
}

// (40000, 70000) -> "LKR 40,000–70,000"
export function formatLkrRange(min, max) {
  return `${formatLkr(min)}–${Number(max).toLocaleString('en-US')}`
}

// 509000 -> "509,000"
export function formatNumber(value) {
  return Number(value).toLocaleString('en-US')
}

// Today as "4 Nov 2026", for printed pages.
export function formatToday() {
  return new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
