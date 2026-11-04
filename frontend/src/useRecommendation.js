import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { postRecommend } from './api'
import { loadProfile, saveProfile } from './session'

function pageFor(response) {
  return response.status === 'ok' ? '/results' : '/no-data'
}

// Runs a recommendation and opens the page that matches its answer. Returns an error message, or null.
export async function recommendAndGo(navigate, profile) {
  saveProfile(profile)
  const result = await postRecommend(profile)
  if (!result.ok) return result.error
  navigate(pageFor(result.data), { state: { response: result.data, profile } })
  return null
}

// The response comes in router state after the profile form. After a refresh that state is gone,
// so the saved profile is sent again; with no saved profile the user goes back to the form.
export function useRecommendation(path) {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state?.response && location.state?.profile ? location.state : null
  const [fetched, setFetched] = useState(null)

  useEffect(() => {
    if (state) return
    const profile = loadProfile()
    if (!profile) {
      navigate('/', { replace: true })
      return
    }
    postRecommend(profile).then((result) => {
      if (!result.ok) {
        setFetched({ error: result.error, profile })
      } else if (pageFor(result.data) !== path) {
        navigate(pageFor(result.data), { replace: true, state: { response: result.data, profile } })
      } else {
        setFetched({ response: result.data, profile })
      }
    })
  }, [state, path, navigate])

  return state ?? fetched ?? { loading: true }
}
