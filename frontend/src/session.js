// The last profile lives in sessionStorage so a refresh or "Edit your answers" can restore it.
// Storage can be blocked (private windows), so failures are ignored and the app still works.
const PROFILE_KEY = 'livelihood-lens:last-profile'

export function saveProfile(profile) {
  try {
    sessionStorage.setItem(PROFILE_KEY, JSON.stringify(profile))
  } catch {
    // Not saved; only refresh and "Edit your answers" lose the values.
  }
}

export function loadProfile() {
  try {
    return JSON.parse(sessionStorage.getItem(PROFILE_KEY)) ?? null
  } catch {
    return null
  }
}
