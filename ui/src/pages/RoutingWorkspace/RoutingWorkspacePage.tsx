import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { AlertTriangle, Download, MapPin, RefreshCw, Route as RouteIcon } from 'lucide-react'

import { InteractiveMap, type MapPolyline } from '../../components/InteractiveMap'
import { CITY_VIEWPORTS, DEFAULT_VIEWPORT } from '../../config/cityViewports'
import { useCustomerCities } from '../../hooks/useCustomerCities'
import { useCustomerLocations } from '../../hooks/useCustomerLocations'
import { useOptimizeRoutes, type OptimizeRoutesPayload, type OptimizeRoutesResponse } from '../../hooks/useOptimizeRoutes'
import { useZoneSummaries, type ZoneSummary } from '../../hooks/useZoneSummaries'
import { colorFromString } from '../../utils/color'

type TabKey = 'metrics' | 'sequence' | 'downloads'

type RouteMetricRow = {
  routeId: string
  day: string
  customers: number
  distance: string
  duration: string
  violations: string
}

type RouteSequenceRow = {
  routeId: string
  stop: number
  customer: string
  eta: string
  distance: string
}

type DownloadItem = {
  label: string
  description: string
  disabled?: boolean
  onClick: () => void
}

const FALLBACK_CITIES = ['Jeddah', 'Riyadh', 'Dammam']
const inputClasses =
  'mt-1 w-full rounded-lg border border-gray-300 bg-background-light px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100'

export function RoutingWorkspacePage() {
  const [tab, setTab] = useState<TabKey>('metrics')
  const [selectedCity, setSelectedCity] = useState('')
  const [selectedZone, setSelectedZone] = useState('')

  const [maxCustomersPerRoute, setMaxCustomersPerRoute] = useState(25)
  const [maxRouteDurationMinutes, setMaxRouteDurationMinutes] = useState(600)
  const [maxDistancePerRouteKm, setMaxDistancePerRouteKm] = useState(50)
  const [persistOutputs, setPersistOutputs] = useState(false)

  const [routeResult, setRouteResult] = useState<OptimizeRoutesResponse | null>(null)
  const [runMeta, setRunMeta] = useState<{ timestamp: string; durationSeconds: number } | null>(null)
  const [lastError, setLastError] = useState<string | null>(null)

  const { data: customerCities, isLoading: isCitiesLoading } = useCustomerCities()
  const { data: zoneSummaries, isLoading: isZonesLoading } = useZoneSummaries()
  const { mutateAsync: optimizeRoutes, isPending: isOptimizing } = useOptimizeRoutes()
  const {
    items: zoneCustomerPoints,
    total: zoneCustomerTotal,
    hasNextPage: hasMoreZoneCustomers,
    fetchNextPage: fetchMoreZoneCustomers,
    isFetchingNextPage: isFetchingMoreZoneCustomers,
  } = useCustomerLocations({
    city: selectedCity,
    zone: selectedZone || undefined,
    pageSize: 1500,
    enabled: Boolean(selectedCity),
  })

  const cityOptions = useMemo(() => {
    if (customerCities?.length) {
      return customerCities.map((entry) => entry.name)
    }
    return deriveCityOptions(zoneSummaries)
  }, [customerCities, zoneSummaries])

  useEffect(() => {
    if (!cityOptions.length) {
      if (selectedCity !== '') {
        setSelectedCity('')
      }
      return
    }
    if (!selectedCity || !cityOptions.includes(selectedCity)) {
      setSelectedCity(cityOptions[0])
    }
  }, [cityOptions, selectedCity])

  const zoneOptions = useMemo(
    () => filterZonesForCity(zoneSummaries, selectedCity),
    [zoneSummaries, selectedCity],
  )

  useEffect(() => {
    if (!zoneOptions.length) {
      if (selectedZone !== '') {
        setSelectedZone('')
        setRouteResult(null)
        setRunMeta(null)
      }
      return
    }
    if (!selectedZone || !zoneOptions.some((zone) => zone.zone === selectedZone)) {
      setSelectedZone(zoneOptions[0].zone)
    }
  }, [zoneOptions, selectedZone])

  const selectedZoneInfo = useMemo(
    () => zoneOptions.find((zone) => zone.zone === selectedZone) ?? null,
    [zoneOptions, selectedZone],
  )

  const metrics = useMemo<RouteMetricRow[]>(() => buildRouteMetrics(routeResult), [routeResult])
  const sequence = useMemo<RouteSequenceRow[]>(() => buildRouteSequence(routeResult), [routeResult])
  const downloadItems = useMemo<DownloadItem[]>(
    () => buildDownloadItems(routeResult, metrics, sequence, selectedZone, selectedCity),
    [metrics, routeResult, selectedCity, selectedZone, sequence],
  )

  const lastRunLabel = useMemo(() => {
    if (!runMeta || !routeResult) {
      return 'Not executed yet'
    }
    const timestamp = new Date(runMeta.timestamp).toLocaleString()
    const duration = `${runMeta.durationSeconds.toFixed(2)}s`
    return `${timestamp} - ${duration}`
  }, [routeResult, runMeta])

  const routeAssignments = useMemo(() => {
    const mapping = new Map<string, string>()
    if (!routeResult?.plans?.length) {
      return mapping
    }
    routeResult.plans.forEach((plan) => {
      plan.stops.forEach((stop) => {
        mapping.set(stop.customer_id, plan.route_id)
      })
    })
    return mapping
  }, [routeResult])

  const routeColorMap = useMemo(() => {
    if (!routeResult?.plans?.length) {
      return {}
    }
    const palette: Record<string, string> = {}
    routeResult.plans.forEach((plan, index) => {
      palette[plan.route_id] = colorFromString(plan.route_id, index)
    })
    return palette
  }, [routeResult])

  const mapViewport = useMemo(() => {
    if (!selectedCity) {
      return DEFAULT_VIEWPORT
    }
    return CITY_VIEWPORTS[selectedCity] ?? DEFAULT_VIEWPORT
  }, [selectedCity])

  const mapCaption = useMemo(() => {
    if (!selectedCity) {
      return 'Select a city to preview routes'
    }
    return `${selectedCity} - ${lastRunLabel}`
  }, [lastRunLabel, selectedCity])

  const defaultZoneColor = useMemo(() => {
    if (!selectedZone) {
      return '#2563eb'
    }
    return colorFromString(selectedZone)
  }, [selectedZone])

  const mapOverlayRoutes = useMemo(() => {
    const overlays = (routeResult?.metadata as { map_overlays?: { routes?: Array<Record<string, unknown>> } } | undefined)
      ?.map_overlays?.routes
    return (overlays ?? []) as Array<{
      route_id: string
      coordinates: Array<[number, number]>
      source?: string
    }>
  }, [routeResult])

  const routeMarkers = useMemo(() => {
    if (!zoneCustomerPoints.length) {
      return []
    }
    return zoneCustomerPoints.map((customer) => {
      const routeId = routeAssignments.get(customer.customer_id)
      const markerColor = routeId
        ? routeColorMap[routeId] ?? colorFromString(routeId)
        : defaultZoneColor

      const labelParts: string[] = []
      if (customer.customer_name) {
        labelParts.push(customer.customer_name)
      }
      labelParts.push(customer.customer_id)

      const detailLabel = routeId ?? customer.zone ?? 'Unassigned'

      return {
        id: customer.customer_id,
        position: [customer.latitude, customer.longitude] as [number, number],
        color: markerColor,
        tooltip: `${labelParts.join(' - ')} - ${detailLabel}`,
      }
    })
  }, [defaultZoneColor, routeAssignments, routeColorMap, zoneCustomerPoints])

  const routePolylines = useMemo<MapPolyline[]>(() => {
    if (!mapOverlayRoutes.length) {
      return []
    }
    return mapOverlayRoutes
      .filter((route) => route.coordinates.length >= 2)
      .map((route) => {
        const color = routeColorMap[route.route_id] ?? colorFromString(route.route_id)
        return {
          id: route.route_id + '-polyline',
          positions: route.coordinates.map((pair) => [pair[0], pair[1]]) as Array<[number, number]>,
          color,
          tooltip: route.route_id,
          weight: 4,
        }
      })
  }, [mapOverlayRoutes, routeColorMap])

  const handleGenerate = useCallback(async () => {
    if (!selectedCity || !selectedZone) {
      setLastError('Select a city and zone before generating routes.')
      return
    }
    setLastError(null)

    const payload: OptimizeRoutesPayload = {
      city: selectedCity,
      zone_id: selectedZone,
      persist: persistOutputs,
      constraints: {
        max_customers_per_route: maxCustomersPerRoute,
        max_route_duration_minutes: maxRouteDurationMinutes,
        max_distance_per_route_km: maxDistancePerRouteKm,
      },
    }

    const startedAt = performance.now()
    try {
      const response = await optimizeRoutes(payload)
      const durationSeconds = Number(((performance.now() - startedAt) / 1000).toFixed(2))
      setRouteResult(response)
      setRunMeta({ timestamp: new Date().toISOString(), durationSeconds })
      setTab('metrics')
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        (error as Error).message ??
        'Unable to generate routes.'
      setLastError(message)
    }
  }, [
    maxCustomersPerRoute,
    maxDistancePerRouteKm,
    maxRouteDurationMinutes,
    optimizeRoutes,
    persistOutputs,
    selectedCity,
    selectedZone,
  ])

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-3xl font-bold leading-tight text-gray-900 dark:text-white">Routing Workspace</h2>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Review zone-level route proposals, tweak constraints, and inspect violations before exporting to field teams.
          </p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          <RefreshCw className="h-4 w-4" /> Refresh OSRM Status
        </button>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,360px)_1fr]">
        <aside className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
          <section className="space-y-4">
            <Field label="City">
              <select
                value={selectedCity}
                onChange={(event) => setSelectedCity(event.target.value)}
                className={inputClasses}
                disabled={!cityOptions.length}
              >
                {!cityOptions.length ? (
                  <option value="">
                    {isCitiesLoading || isZonesLoading ? 'Loading cities…' : 'No cities detected'}
                  </option>
                ) : (
                  cityOptions.map((city) => (
                    <option key={city} value={city}>
                      {city}
                    </option>
                  ))
                )}
              </select>
            </Field>

            <Field label="Zone">
              <select
                value={selectedZone}
                onChange={(event) => setSelectedZone(event.target.value)}
                className={inputClasses}
                disabled={!zoneOptions.length}
              >
                {isZonesLoading && <option>Loading zones…</option>}
                {!isZonesLoading && !zoneOptions.length && <option>No zones available</option>}
                {zoneOptions.map((zone) => (
                  <option key={zone.zone} value={zone.zone}>
                    {zone.zone} ({zone.customers} customers)
                  </option>
                ))}
              </select>
              <p className="mt-2 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <MapPin className="h-3.5 w-3.5" />
                {selectedZoneInfo
                  ? `${selectedZoneInfo.city ?? 'Unknown city'} - ${selectedZoneInfo.customers} customers`
                  : 'Select a zone to view details'}
              </p>
            </Field>
          </section>

          <section className="grid gap-4">
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-gray-600 dark:text-gray-300">Customer filters</legend>
              <Checkbox label="Active customers only" defaultChecked />
              <Checkbox label="Requires finance clearance" />
              <Checkbox label="Priority outlets" />
            </fieldset>

            <div className="space-y-3 rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
              <SliderField
                label="Max customers per route"
                value={maxCustomersPerRoute}
                min={5}
                max={60}
                onChange={setMaxCustomersPerRoute}
              />
              <SliderField
                label="Max route duration (minutes)"
                value={maxRouteDurationMinutes}
                min={60}
                max={900}
                step={15}
                onChange={setMaxRouteDurationMinutes}
              />
              <SliderField
                label="Max route distance (km)"
                value={maxDistancePerRouteKm}
                min={10}
                max={200}
                onChange={setMaxDistancePerRouteKm}
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
              <input
                type="checkbox"
                checked={persistOutputs}
                onChange={(event) => setPersistOutputs(event.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary/40"
              />
              Persist outputs to disk (data/outputs/routes_*)
            </label>
          </section>

          <div className="space-y-2">
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isOptimizing || !selectedZone}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <RouteIcon className="h-4 w-4" />
              {isOptimizing ? 'Generating…' : 'Generate routes'}
            </button>
            <button
              type="button"
              onClick={() => {
                setRouteResult(null)
                setRunMeta(null)
                setLastError(null)
              }}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            >
              Clear results
            </button>
            {lastError ? (
              <p className="rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
                {lastError}
              </p>
            ) : null}
          </div>
        </aside>

        <section className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
          <div className="flex items-start gap-3 rounded-xl bg-warning/10 p-4 text-sm text-warning dark:bg-warning/20 dark:text-warning-100">
            <AlertTriangle className="h-5 w-5" />
            <p>
              Large customer reassignments may trigger the finance “clearness” process. Review the Transfers tab and coordinate with Finance
              before finalizing.
            </p>
          </div>

          <div className="space-y-2">
            <InteractiveMap center={mapViewport.center} zoom={mapViewport.zoom} caption={mapCaption} markers={routeMarkers} polylines={routePolylines} />
            {hasMoreZoneCustomers ? (
              <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                <p>
                  Displaying {zoneCustomerPoints.length.toLocaleString()} of {zoneCustomerTotal.toLocaleString()} customers in this zone.
                </p>
                <button
                  type="button"
                  onClick={() => fetchMoreZoneCustomers()}
                  disabled={isFetchingMoreZoneCustomers}
                  className="inline-flex items-center rounded-full border border-gray-300 px-3 py-1 font-semibold text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                >
                  {isFetchingMoreZoneCustomers ? 'Loading…' : 'Load more'}
                </button>
              </div>
            ) : null}
          </div>

          <div className="space-y-4 rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-background-dark/80">
            <nav className="flex gap-6 border-b border-gray-200 px-4 text-sm font-semibold dark:border-gray-700">
              <TabButton active={tab === 'metrics'} onClick={() => setTab('metrics')}>
                Metrics
              </TabButton>
              <TabButton active={tab === 'sequence'} onClick={() => setTab('sequence')}>
                Sequence ({sequence.length})
              </TabButton>
              <TabButton active={tab === 'downloads'} onClick={() => setTab('downloads')}>
                Downloads
              </TabButton>
            </nav>
            <div className="px-4 pb-4">
              {tab === 'metrics' && <RouteMetricsTable rows={metrics} hasResult={Boolean(routeResult)} />}
              {tab === 'sequence' && <RouteSequenceTable rows={sequence} hasResult={Boolean(routeResult)} />}
              {tab === 'downloads' && <DownloadsList items={downloadItems} />}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1 text-sm">
      <span className="font-medium text-gray-700 dark:text-gray-200">{label}</span>
      {children}
    </label>
  )
}

function Checkbox({ label, defaultChecked }: { label: string; defaultChecked?: boolean }) {
  return (
    <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
      <input type="checkbox" defaultChecked={defaultChecked} className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary/40" />
      {label}
    </label>
  )
}

function SliderField({ label, value, min, max, step = 1, onChange }: { label: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void }) {
  return (
    <label className="block text-xs text-gray-600 dark:text-gray-300">
      <span className="flex items-center justify-between text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">
        <span>{label}</span>
        <span>{value}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-1 w-full accent-primary"
      />
    </label>
  )
}

function RouteMetricsTable({ rows, hasResult }: { rows: RouteMetricRow[]; hasResult: boolean }) {
  if (!rows.length) {
    return (
      <EmptyState message={hasResult ? 'No routes were returned for this request.' : 'Generate routes to view metrics.'} />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
        <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-300">
          <tr>
            <th className="px-4 py-3 text-left">Route ID</th>
            <th className="px-4 py-3 text-left">Day</th>
            <th className="px-4 py-3 text-left">Customers</th>
            <th className="px-4 py-3 text-left">Distance</th>
            <th className="px-4 py-3 text-left">Duration</th>
            <th className="px-4 py-3 text-left">Violations</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {rows.map((row) => (
            <tr key={row.routeId} className="bg-white dark:bg-background-dark/80">
              <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{row.routeId}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.day}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.customers}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.distance}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.duration}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.violations}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RouteSequenceTable({ rows, hasResult }: { rows: RouteSequenceRow[]; hasResult: boolean }) {
  if (!rows.length) {
    return <EmptyState message={hasResult ? 'No stops returned for this run.' : 'Generate routes to review stop sequence.'} />
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
        <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-300">
          <tr>
            <th className="px-4 py-3 text-left">Route ID</th>
            <th className="px-4 py-3 text-left">Stop</th>
            <th className="px-4 py-3 text-left">Customer</th>
            <th className="px-4 py-3 text-left">ETA</th>
            <th className="px-4 py-3 text-left">Distance from prev</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {rows.map((row, index) => (
            <tr key={row.routeId + '-' + index} className="bg-white dark:bg-background-dark/80">
              <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{row.routeId}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.stop}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.customer}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.eta}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.distance}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DownloadsList({ items }: { items: DownloadItem[] }) {
  if (!items.length) {
    return <EmptyState message="Generate routes to enable downloads." />
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm dark:border-gray-700 dark:bg-gray-800/60"
        >
          <div>
            <p className="font-semibold text-gray-800 dark:text-gray-100">{item.label}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{item.description}</p>
          </div>
          <button
            type="button"
            onClick={item.onClick}
            disabled={item.disabled}
            className="inline-flex items-center gap-2 rounded-full border border-primary px-3 py-1.5 text-xs font-semibold text-primary transition hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60 dark:border-primary-100 dark:text-primary-100 dark:hover:bg-primary/30"
          >
            <Download className="h-4 w-4" /> Download
          </button>
        </div>
      ))}
    </div>
  )
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  const base = 'border-b-2 px-1 py-4 transition'
  const classes = active
    ? base + ' border-primary text-primary'
    : base + ' border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
  return (
    <button type="button" onClick={onClick} className={classes}>
      {children}
    </button>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300">
      {message}
    </div>
  )
}

function deriveCityOptions(zones: ZoneSummary[] | undefined): string[] {
  if (!zones?.length) {
    return [...FALLBACK_CITIES]
  }
  const unique = new Set<string>()
  zones.forEach((zone) => {
    if (zone.city) {
      unique.add(zone.city)
    }
  })
  if (!unique.size) {
    FALLBACK_CITIES.forEach((city) => unique.add(city))
  }
  return Array.from(unique).sort()
}

function filterZonesForCity(zones: ZoneSummary[] | undefined, city: string): ZoneSummary[] {
  if (!zones?.length) {
    return []
  }
  if (!city) {
    return zones
  }
  return zones.filter((zone) => (zone.city ?? '').toLowerCase() === city.toLowerCase())
}

function buildRouteMetrics(result: OptimizeRoutesResponse | null): RouteMetricRow[] {
  if (!result?.plans?.length) {
    return []
  }
  return result.plans.map((plan) => ({
    routeId: plan.route_id,
    day: plan.day,
    customers: plan.customer_count,
    distance: formatDistance(plan.total_distance_km),
    duration: formatDuration(plan.total_duration_min),
    violations: formatViolations(plan.constraint_violations),
  }))
}

function buildRouteSequence(result: OptimizeRoutesResponse | null): RouteSequenceRow[] {
  if (!result?.plans?.length) {
    return []
  }
  return result.plans.flatMap((plan) =>
    plan.stops.map((stop) => ({
      routeId: plan.route_id,
      stop: stop.sequence,
      customer: stop.customer_id,
      eta: formatDuration(stop.arrival_min),
      distance: formatDistance(stop.distance_from_prev_km),
    })),
  )
}

function buildDownloadItems(
  result: OptimizeRoutesResponse | null,
  metrics: RouteMetricRow[],
  sequence: RouteSequenceRow[],
  zone: string,
  city: string,
): DownloadItem[] {
  if (!result) {
    return []
  }
  const safeZone = zone || 'routes'
  const safeCity = city || 'city'
  return [
    {
      label: 'routes_summary.json',
      description: 'Raw optimization response for auditing',
      onClick: () => downloadJson(result, `routes_${safeCity}_${safeZone}.json`),
    },
    {
      label: 'route_metrics.csv',
      description: 'Distance, duration, and violations per route',
      disabled: !metrics.length,
      onClick: () => downloadCsv(buildRouteMetricsCsv(result), `route_metrics_${safeCity}_${safeZone}.csv`),
    },
    {
      label: 'route_sequence.csv',
      description: 'Stop-by-stop customer visit order',
      disabled: !sequence.length,
      onClick: () => downloadCsv(buildRouteSequenceCsv(result), `route_sequence_${safeCity}_${safeZone}.csv`),
    },
  ]
}

function formatDistance(km: number | undefined): string {
  if (km == null || Number.isNaN(km)) {
    return '--'
  }
  return km.toFixed(1) + ' km'
}

function formatDuration(minutes: number | undefined): string {
  if (minutes == null || Number.isNaN(minutes)) {
    return '--'
  }
  const wholeMinutes = Math.round(minutes)
  const hours = Math.floor(wholeMinutes / 60)
  const remaining = wholeMinutes % 60
  if (hours === 0) {
    return `${remaining} min`
  }
  return `${hours} h ${remaining} min`
}

function formatViolations(violations: Record<string, number> | undefined): string {
  if (!violations || !Object.keys(violations).length) {
    return '--'
  }
  return Object.entries(violations)
    .map(([key, value]) => `${key}: ${value.toFixed(1)}`)
    .join(', ')
}

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  triggerDownload(blob, filename)
}

function downloadCsv(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  triggerDownload(blob, filename)
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function buildRouteMetricsCsv(result: OptimizeRoutesResponse): string {
  const header = 'RouteId,Day,Customers,TotalDistanceKm,TotalDurationMin,Violations'
  const rows = result.plans.map((plan) => {
    const violations = formatViolations(plan.constraint_violations)
    return [
      plan.route_id,
      plan.day,
      plan.customer_count.toString(),
      plan.total_distance_km.toFixed(3),
      plan.total_duration_min.toFixed(2),
      violations,
    ].join(',')
  })
  return [header, ...rows].join('\n')
}

function buildRouteSequenceCsv(result: OptimizeRoutesResponse): string {
  const header = 'RouteId,Stop,CustomerId,ArrivalMinutes,DistanceFromPreviousKm'
  const rows = result.plans.flatMap((plan) =>
    plan.stops.map((stop) =>
      [
        plan.route_id,
        stop.sequence.toString(),
        stop.customer_id,
        stop.arrival_min.toFixed(2),
        stop.distance_from_prev_km != null ? stop.distance_from_prev_km.toFixed(3) : '',
      ].join(','),
    ),
  )
  return [header, ...rows].join('\n')
}

