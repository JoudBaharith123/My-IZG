import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { AlertTriangle, Download, MapPin, RefreshCw, Route as RouteIcon, X, ArrowRight } from 'lucide-react'

import { InteractiveMap, type MapPolyline } from '../../components/InteractiveMap'
import { CITY_VIEWPORTS, DEFAULT_VIEWPORT } from '../../config/cityViewports'
import { useCustomerCities } from '../../hooks/useCustomerCities'
import { useCustomerLocations } from '../../hooks/useCustomerLocations'
import { useOptimizeRoutes, type OptimizeRoutesPayload, type OptimizeRoutesResponse } from '../../hooks/useOptimizeRoutes'
import { useRoutesFromDatabase } from '../../hooks/useRoutesFromDatabase'
import { useZoneSummaries, type ZoneSummary } from '../../hooks/useZoneSummaries'
import { useDatabaseZoneSummaries } from '../../hooks/useDatabaseZoneSummaries'
import { useRemoveCustomerFromRoute, useTransferCustomer } from '../../hooks/useUpdateRoute'
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
  const [startFromDepot, setStartFromDepot] = useState(true) // Default to starting from DC/depot
  const [persistOutputs, setPersistOutputs] = useState(true) // Default to true to always save routes

  const [routeResult, setRouteResult] = useState<OptimizeRoutesResponse | null>(null)
  const [runMeta, setRunMeta] = useState<{ timestamp: string; durationSeconds: number } | null>(null)
  const [lastError, setLastError] = useState<string | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string>('')
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null)

  const { data: customerCities, isLoading: isCitiesLoading } = useCustomerCities()
  
  // Use database zones instead of customer zones (from CSV)
  const { data: zoneSummaries, isLoading: isZonesLoading } = useDatabaseZoneSummaries(selectedCity || undefined)
  const { mutateAsync: optimizeRoutes, isPending: isOptimizing } = useOptimizeRoutes()
  const { mutateAsync: removeCustomer, isPending: isRemovingCustomer } = useRemoveCustomerFromRoute()
  const { mutateAsync: transferCustomer, isPending: isTransferringCustomer } = useTransferCustomer()
  
  // Fetch routes from database when zone is selected
  const { data: dbRoutes, isLoading: isLoadingDbRoutes } = useRoutesFromDatabase(
    selectedZone || undefined,
    selectedCity || undefined
  )
  const {
    items: zoneCustomerPoints,
    total: zoneCustomerTotal,
    hasNextPage: hasMoreZoneCustomers,
    fetchNextPage: fetchMoreZoneCustomers,
    isFetchingNextPage: isFetchingMoreZoneCustomers,
    isLoading: isLoadingCustomers,
  } = useCustomerLocations({
    city: selectedCity,
    zone: selectedZone || undefined,
    pageSize: 5000, // Increased to show more customers like zoning workspace
    enabled: Boolean(selectedCity), // Show map when city is selected (zone is optional)
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

  // Load routes from database when zone is selected
  useEffect(() => {
    if (dbRoutes && selectedZone) {
      setRouteResult(dbRoutes)
      // Set metadata to indicate routes were loaded from database
      setRunMeta({
        timestamp: new Date().toISOString(),
        durationSeconds: 0,
      })
    } else if (!selectedZone) {
      // Clear routes when zone is deselected
      setRouteResult(null)
      setRunMeta(null)
    }
  }, [dbRoutes, selectedZone])

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
    // Always show map - use city viewport if city selected, otherwise default
    if (selectedCity) {
      return CITY_VIEWPORTS[selectedCity] ?? DEFAULT_VIEWPORT
    }
    return DEFAULT_VIEWPORT
  }, [selectedCity])

  const mapCaption = useMemo(() => {
    if (!selectedCity) {
      return 'Select a city to view customers and routes'
    }
    if (!selectedZone) {
      return `${selectedCity} - Select a zone to view customers`
    }
    if (routeResult) {
      return `${selectedCity} - ${selectedZone} - ${lastRunLabel}`
    }
    return `${selectedCity} - ${selectedZone} - ${zoneCustomerPoints.length} customers`
  }, [lastRunLabel, selectedCity, selectedZone, routeResult, zoneCustomerPoints.length])

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
    
    // Build a map of customer_id -> stop number for quick lookup
    const customerStopNumberMap = new Map<string, number>()
    if (routeResult?.plans?.length) {
      routeResult.plans.forEach((plan) => {
        plan.stops.forEach((stop) => {
          customerStopNumberMap.set(stop.customer_id, stop.sequence)
        })
      })
    }
    
    // Filter by selected route if one is selected AND routes exist
    const filteredCustomers = selectedRouteId && routeResult?.plans?.length
      ? zoneCustomerPoints.filter((customer) => {
          const routeId = routeAssignments.get(customer.customer_id)
          return routeId === selectedRouteId
        })
      : zoneCustomerPoints
    
    // Use smaller markers for large datasets (like zoning workspace)
    const markerRadius = zoneCustomerPoints.length > 2000 ? 3 : zoneCustomerPoints.length > 1000 ? 4 : 6
    
    return filteredCustomers.map((customer) => {
      // If routes exist, use route colors, otherwise use zone colors
      const routeId = routeAssignments.get(customer.customer_id)
      const markerColor = routeId && routeResult?.plans?.length
        ? routeColorMap[routeId] ?? colorFromString(routeId)
        : (customer.zone ? colorFromString(customer.zone) : defaultZoneColor)

      const labelParts: string[] = []
      if (customer.customer_name) {
        labelParts.push(customer.customer_name)
      }
      labelParts.push(customer.customer_id)

      // Show route if assigned, otherwise show zone or city
      const detailLabel = routeId && routeResult?.plans?.length
        ? `Route: ${routeId}`
        : (customer.zone ? `Zone: ${customer.zone}` : (selectedCity ? `City: ${selectedCity}` : 'Unassigned'))

      // Get stop number if customer is in a route
      const stopNumber = customerStopNumberMap.get(customer.customer_id)

      return {
        id: customer.customer_id,
        position: [customer.latitude, customer.longitude] as [number, number],
        color: markerColor,
        radius: markerRadius,
        tooltip: `${labelParts.join(' - ')}\n${detailLabel}`,
        stopNumber: stopNumber,
      }
    })
  }, [defaultZoneColor, routeAssignments, routeColorMap, zoneCustomerPoints, selectedRouteId, routeResult, selectedCity])
  
  // Get route options for dropdown
  const routeOptions = useMemo(() => {
    if (!routeResult?.plans?.length) {
      return []
    }
    return routeResult.plans.map((plan) => ({
      routeId: plan.route_id,
      label: `${plan.route_id} (${plan.customer_count} customers, ${plan.day})`,
      customerCount: plan.customer_count,
    }))
  }, [routeResult])
  
  // Get customers for selected route (from route result)
  const selectedRouteCustomers = useMemo(() => {
    if (!selectedRouteId || !routeResult?.plans) {
      return []
    }
    const plan = routeResult.plans.find((p) => p.route_id === selectedRouteId)
    return plan?.stops || []
  }, [selectedRouteId, routeResult])
  
  // Get all customers for the selected route (from zone customer points)
  const selectedRouteCustomerPoints = useMemo(() => {
    if (!selectedRouteId) {
      return zoneCustomerPoints
    }
    return zoneCustomerPoints.filter((customer) => {
      const routeId = routeAssignments.get(customer.customer_id)
      return routeId === selectedRouteId
    })
  }, [selectedRouteId, zoneCustomerPoints, routeAssignments])

  const routePolylines = useMemo<MapPolyline[]>(() => {
    if (!mapOverlayRoutes.length || !routeResult?.plans?.length) {
      return []
    }
    // Filter by selected route if one is selected
    const filteredRoutes = selectedRouteId
      ? mapOverlayRoutes.filter((route) => route.route_id === selectedRouteId)
      : mapOverlayRoutes
    
    // Log coordinates for debugging
    filteredRoutes.forEach((route) => {
      if (route.coordinates && route.coordinates.length > 0) {
        const firstCoord = route.coordinates[0]
        console.log(`[Frontend] Route ${route.route_id}: ${route.coordinates.length} coordinates, first=(${firstCoord[0]}, ${firstCoord[1]})`)
      }
    })
    
    return filteredRoutes
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
  }, [mapOverlayRoutes, routeColorMap, selectedRouteId, routeResult])

  const handleGenerate = useCallback(async () => {
    if (!selectedCity || !selectedZone) {
      setLastError('Select a city and zone before generating routes.')
      return
    }
    setLastError(null)
    setSelectedRouteId('') // Reset route filter

    const payload: OptimizeRoutesPayload = {
      city: selectedCity,
      zone_id: selectedZone,
      persist: persistOutputs,
      start_from_depot: startFromDepot,
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
    startFromDepot,
  ])
  
  const handleRemoveCustomer = useCallback(async (customerId: string, routeId: string) => {
    if (!selectedZone) {
      setLastError('No zone selected')
      return
    }
    try {
      await removeCustomer({
        zone_id: selectedZone,
        route_id: routeId,
        customer_id: customerId,
      })
      // Refresh route result by removing customer from local state
      if (routeResult) {
        const updatedPlans = routeResult.plans.map((plan) => {
          if (plan.route_id === routeId) {
            return {
              ...plan,
              stops: plan.stops.filter((stop) => stop.customer_id !== customerId),
              customer_count: plan.customer_count - 1,
            }
          }
          return plan
        })
        setRouteResult({ ...routeResult, plans: updatedPlans })
      }
      setSelectedCustomerId(null)
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        (error as Error).message ??
        'Failed to remove customer'
      setLastError(message)
    }
  }, [selectedZone, removeCustomer, routeResult])
  
  const handleTransferCustomer = useCallback(async (customerId: string, fromRouteId: string, toRouteId: string) => {
    if (!selectedZone) {
      setLastError('No zone selected')
      return
    }
    try {
      await transferCustomer({
        zone_id: selectedZone,
        from_route_id: fromRouteId,
        to_route_id: toRouteId,
        customer_id: customerId,
      })
      // Refresh route result by moving customer between routes
      if (routeResult) {
        let customerStop: typeof routeResult.plans[0]['stops'][0] | undefined
        const updatedPlans = routeResult.plans.map((plan) => {
          if (plan.route_id === fromRouteId) {
            // Find and remove from source route
            customerStop = plan.stops.find((stop) => stop.customer_id === customerId)
            return {
              ...plan,
              stops: plan.stops.filter((stop) => stop.customer_id !== customerId),
              customer_count: plan.customer_count - 1,
            }
          }
          return plan
        }).map((plan) => {
          if (plan.route_id === toRouteId && customerStop) {
            // Add to destination route
            const maxSequence = Math.max(...plan.stops.map((s) => s.sequence), 0)
            return {
              ...plan,
              stops: [...plan.stops, { ...customerStop, sequence: maxSequence + 1 }],
              customer_count: plan.customer_count + 1,
            }
          }
          return plan
        })
        setRouteResult({ ...routeResult, plans: updatedPlans })
      }
      setSelectedCustomerId(null)
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        (error as Error).message ??
        'Failed to transfer customer'
      setLastError(message)
    }
  }, [selectedZone, transferCustomer, routeResult])

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
            
            {routeOptions.length > 0 ? (
              <Field label="Filter by Route">
                <select
                  value={selectedRouteId}
                  onChange={(event) => setSelectedRouteId(event.target.value)}
                  className={inputClasses}
                >
                  <option value="">All routes ({zoneCustomerPoints.length} customers)</option>
                  {routeOptions.map((route) => (
                    <option key={route.routeId} value={route.routeId}>
                      {route.label}
                    </option>
                  ))}
                </select>
                {selectedRouteId ? (
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    Showing {selectedRouteCustomerPoints.length} of {selectedRouteCustomers.length} customers in this route
                  </p>
                ) : (
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    Showing all {zoneCustomerPoints.length} customers in zone
                  </p>
                )}
              </Field>
            ) : zoneCustomerPoints.length > 0 ? (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600 dark:border-gray-700 dark:bg-gray-800/60 dark:text-gray-300">
                <p className="font-medium">Zone Customers</p>
                <p className="mt-1">{zoneCustomerPoints.length.toLocaleString()} customers in this zone</p>
                <p className="mt-2 text-gray-500 dark:text-gray-400">
                  Generate routes to assign customers to routes and filter by route.
                </p>
              </div>
            ) : null}
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

            <div className="space-y-3 rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-200">
                Route Start Point
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                  <input
                    type="radio"
                    name="routeStart"
                    checked={startFromDepot}
                    onChange={() => setStartFromDepot(true)}
                    className="h-4 w-4 border-gray-300 text-primary focus:ring-primary/40"
                  />
                  Start from DC/Depot (default)
                </label>
                <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                  <input
                    type="radio"
                    name="routeStart"
                    checked={!startFromDepot}
                    onChange={() => setStartFromDepot(false)}
                    className="h-4 w-4 border-gray-300 text-primary focus:ring-primary/40"
                  />
                  Start from first customer
                </label>
              </div>
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
            {isLoadingCustomers && selectedCity ? (
              <div className="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 p-8 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300">
                Loading customers...
              </div>
            ) : !selectedCity ? (
              <div className="relative h-[600px] w-full overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                <InteractiveMap center={mapViewport.center} zoom={mapViewport.zoom} caption={mapCaption} markers={[]} polylines={[]} />
                <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm dark:bg-gray-900/80">
                  <div className="text-center">
                    <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">Select a city to view customers</p>
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Choose a city from the dropdown to see customers on the map</p>
                  </div>
                </div>
              </div>
            ) : zoneCustomerPoints.length === 0 ? (
              <div className="relative h-[600px] w-full overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                <InteractiveMap center={mapViewport.center} zoom={mapViewport.zoom} caption={mapCaption} markers={[]} polylines={[]} />
                <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm dark:bg-gray-900/80">
                  <div className="text-center">
                    <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">
                      {selectedZone
                        ? `No customers found for zone "${selectedZone}"`
                        : 'Select a zone to view customers'}
                    </p>
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                      {selectedZone
                        ? `Make sure the zone has customers assigned in ${selectedCity}`
                        : `Choose a zone from the dropdown to see customers in ${selectedCity}`}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <InteractiveMap center={mapViewport.center} zoom={mapViewport.zoom} caption={mapCaption} markers={routeMarkers} polylines={routePolylines} />
                {hasMoreZoneCustomers ? (
                  <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                    <p>
                      Displaying {zoneCustomerPoints.length.toLocaleString()} of {zoneCustomerTotal.toLocaleString()} customers{selectedZone ? ` in zone "${selectedZone}"` : ` in ${selectedCity}`}.
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
                ) : (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Displaying {zoneCustomerPoints.length.toLocaleString()} {zoneCustomerPoints.length === 1 ? 'customer' : 'customers'}{selectedZone ? ` in zone "${selectedZone}"` : ` in ${selectedCity}`}.
                  </div>
                )}
              </>
            )}
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
              {tab === 'sequence' && (
                <RouteSequenceTable 
                  rows={sequence} 
                  hasResult={Boolean(routeResult)}
                  onRemoveCustomer={handleRemoveCustomer}
                  onTransferCustomer={handleTransferCustomer}
                  routeOptions={routeOptions}
                  selectedZone={selectedZone}
                  isRemoving={isRemovingCustomer}
                  isTransferring={isTransferringCustomer}
                />
              )}
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

function RouteSequenceTable({ 
  rows, 
  hasResult,
  onRemoveCustomer,
  onTransferCustomer,
  routeOptions,
  selectedZone,
  isRemoving,
  isTransferring,
}: { 
  rows: RouteSequenceRow[]
  hasResult: boolean
  onRemoveCustomer?: (customerId: string, routeId: string) => void
  onTransferCustomer?: (customerId: string, fromRouteId: string, toRouteId: string) => void
  routeOptions?: Array<{ routeId: string; label: string }>
  selectedZone?: string
  isRemoving?: boolean
  isTransferring?: boolean
}) {
  const [transferringCustomer, setTransferringCustomer] = useState<{ customerId: string; routeId: string } | null>(null)
  
  if (!rows.length) {
    return <EmptyState message={hasResult ? 'No stops returned for this run.' : 'Generate routes to review stop sequence.'} />
  }

  const handleTransferClick = (customerId: string, routeId: string) => {
    setTransferringCustomer({ customerId, routeId })
  }
  
  const handleTransferConfirm = (toRouteId: string) => {
    if (transferringCustomer && onTransferCustomer) {
      onTransferCustomer(transferringCustomer.customerId, transferringCustomer.routeId, toRouteId)
      setTransferringCustomer(null)
    }
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
            <th className="px-4 py-3 text-left">Actions</th>
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
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  {transferringCustomer?.customerId === row.customer ? (
                    <div className="flex items-center gap-2">
                      <select
                        className="rounded border border-gray-300 px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-800"
                        onChange={(e) => {
                          if (e.target.value) {
                            handleTransferConfirm(e.target.value)
                          }
                        }}
                        disabled={isTransferring}
                      >
                        <option value="">Select route...</option>
                        {routeOptions?.filter((r) => r.routeId !== row.routeId).map((route) => (
                          <option key={route.routeId} value={route.routeId}>
                            {route.label}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => setTransferringCustomer(null)}
                        className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400"
                        disabled={isTransferring}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      {onTransferCustomer && routeOptions && routeOptions.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleTransferClick(row.customer, row.routeId)}
                          disabled={isTransferring}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-primary hover:bg-primary/10 disabled:opacity-50"
                          title="Transfer to another route"
                        >
                          <ArrowRight className="h-3 w-3" />
                          Transfer
                        </button>
                      )}
                      {onRemoveCustomer && (
                        <button
                          type="button"
                          onClick={() => onRemoveCustomer(row.customer, row.routeId)}
                          disabled={isRemoving}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-900/20"
                          title="Remove from route"
                        >
                          <X className="h-3 w-3" />
                          Remove
                        </button>
                      )}
                    </>
                  )}
                </div>
              </td>
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

