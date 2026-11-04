// Every call returns { ok: true, data } or { ok: false, error, status }, so pages never need try/catch.

// Set in frontend/.env (copy .env.example) locally, and in the hosting settings in production.
const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

const OFFLINE_MESSAGE =
  "We can't reach Livelihood Lens right now. Check your internet connection, or try again in a minute."
const NOT_CONFIGURED_MESSAGE = "Livelihood Lens isn't set up correctly: the address of its data service is missing."

if (!API_URL) console.error('VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env.')

function errorMessage(status, body) {
  // 422 bodies are { detail: [{ field, message }] } from the API's validation handler.
  if (status === 422 && Array.isArray(body?.detail)) {
    return body.detail.map((item) => item.message).join(' ')
  }
  if (status >= 500) {
    return `Something went wrong on our side (error ${status}). Please try again in a minute.`
  }
  return `The request didn't work (error ${status}). Please check your answers and try again.`
}

async function request(path, options = {}) {
  if (!API_URL) return { ok: false, error: NOT_CONFIGURED_MESSAGE, status: null }
  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    return { ok: false, error: OFFLINE_MESSAGE, status: null }
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    // An empty or non-JSON body is handled by the status check below.
  }
  if (!response.ok) {
    return { ok: false, error: errorMessage(response.status, body), status: response.status }
  }
  return { ok: true, data: body }
}

export function getHealth() {
  return request('/health')
}

export function getDistricts() {
  return request('/districts')
}

export function getCategories() {
  return request('/categories')
}

export function getFreshness() {
  return request('/freshness')
}

export function getGaps(categoryId) {
  return request(`/gaps?category_id=${encodeURIComponent(categoryId)}`)
}

// profile: { district, budget_lkr, skills: [], hours }
export function postRecommend(profile) {
  return request('/recommend', { method: 'POST', body: JSON.stringify(profile) })
}
