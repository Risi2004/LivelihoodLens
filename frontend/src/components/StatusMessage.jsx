import { Link } from 'react-router-dom'

// Loading and error states shared by the pages that wait on the API.
export default function StatusMessage({ loading, error }) {
  if (loading) {
    return <p className="rounded-2xl border border-stone-200 bg-white p-8 text-stone-600">Loading…</p>
  }
  return (
    <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-amber-900">
      <p>{error}</p>
      <Link to="/" className="mt-4 inline-block font-semibold text-brand underline">
        Back to your answers
      </Link>
    </div>
  )
}
