import { Link, NavLink } from 'react-router-dom'

const LINKS = [
  { to: '/', label: 'Find opportunities' },
  { to: '/gaps', label: 'Highest gaps' },
  { to: '/about', label: 'About the data' },
]

function LogoMark() {
  return (
    <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-brand">
      <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="5.5" fill="none" stroke="#fff" strokeWidth="2.4" />
        <path d="M14.8 14.8 19 19" stroke="#f0b43c" strokeWidth="2.8" strokeLinecap="round" />
      </svg>
    </span>
  )
}

function linkClass({ isActive }) {
  const base = 'rounded-lg px-2 py-2 text-sm font-medium whitespace-nowrap transition-colors sm:px-3 sm:text-[15px]'
  return isActive
    ? `${base} bg-brand-soft text-brand-dark`
    : `${base} text-stone-700 hover:bg-stone-100 hover:text-ink`
}

export default function Navbar() {
  return (
    <header className="border-b border-stone-200 bg-white print:hidden">
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3"
      >
        <Link to="/" className="flex items-center gap-2.5 text-lg font-bold tracking-tight text-ink">
          <LogoMark />
          Livelihood Lens
        </Link>
        <div className="-mx-2 flex flex-wrap items-center gap-1 sm:mx-0">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === '/'} className={linkClass}>
              {link.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </header>
  )
}
