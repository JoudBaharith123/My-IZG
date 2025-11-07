import { NavLink, Outlet } from 'react-router-dom'
import { clsx } from 'clsx'
import { useOsrmHealth } from '../../hooks/useOsrmHealth'

const navItems = [
  { to: '/upload', label: 'Upload & Validate' },
  { to: '/zoning', label: 'Zoning Workspace' },
  { to: '/routing', label: 'Routing Workspace' },
  { to: '/reports', label: 'Reports' },
]

export function AppLayout() {
  const { data: osrmHealthy, isLoading, isError } = useOsrmHealth()
  const osrmStatus = isLoading ? 'Checking…' : isError ? 'Unavailable' : osrmHealthy ? 'Healthy' : 'Degraded'
  const osrmTone = isLoading
    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-200'
    : osrmHealthy && !isError
      ? 'bg-green-100 text-green-800 dark:bg-green-500/20 dark:text-green-200'
      : 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-200'
  return (
    <div className="flex min-h-screen flex-col bg-background-light text-gray-900 dark:bg-background-dark dark:text-gray-100">
      <header className="flex flex-col gap-4 border-b border-gray-200 bg-white px-4 py-4 shadow-sm dark:border-gray-800 dark:bg-background-dark">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-primary">Binder Logistics</p>
            <h1 className="text-2xl font-bold">Intelligent Zone Generator</h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className={clsx('inline-flex items-center gap-2 rounded-full px-3 py-1 font-medium transition', osrmTone)}>
              <span
                className={clsx(
                  'h-2 w-2 rounded-full',
                  osrmHealthy && !isError ? 'bg-green-500' : isLoading ? 'bg-yellow-500' : 'bg-red-500',
                )}
              />
              OSRM {osrmStatus}
            </div>
            <button className="hidden rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary/90 md:block">
              Run Plan
            </button>
          </div>
        </div>
        <nav className="flex flex-wrap gap-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'rounded-full px-4 py-2 text-sm font-medium transition',
                  isActive
                    ? 'bg-primary text-white shadow'
                    : 'bg-white text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10">
        <Outlet />
      </main>
    </div>
  )
}
