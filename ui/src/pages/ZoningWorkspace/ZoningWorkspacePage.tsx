import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { AlertTriangle, Download, Edit3, Pencil, Plus, RefreshCw, Target, Trash2 } from 'lucide-react'
import { InteractiveMap, type MapPolygon } from '../../components/InteractiveMap'
import { DrawableMap } from '../../components/DrawableMap'
import { FilterPanel } from '../../components/FilterPanel'
import { CITY_VIEWPORTS, DEFAULT_VIEWPORT } from '../../config/cityViewports'
import { useCustomerCities } from '../../hooks/useCustomerCities'
import { useCustomerLocations } from '../../hooks/useCustomerLocations'
import { colorFromString } from '../../utils/color'
import { countPointsInPolygon, doPolygonsOverlap } from '../../utils/geometry'

import {
  useGenerateZones,
  type BalancingMetadata,
  type BalancingTransfer,
  type GenerateZonesPayload,
  type GenerateZonesResponse,
  type ManualPolygonPayload,
} from '../../hooks/useGenerateZones'
import { useZonesFromDatabase } from '../../hooks/useZonesFromDatabase'

type Method = 'polar' | 'isochrone' | 'clustering' | 'manual'

type SummaryRow = {
  zone: string
  customers: number
  delta: string
  tolerance: 'in' | 'out'
}

type TransferRow = {
  customer: string
  fromZone: string
  toZone: string
  distance: string
}

type ManualPolygonForm = {
  id: string
  zoneId: string
  coordinates: string
  color?: string
  isEditing?: boolean
  isDrawing?: boolean
}

const inputClasses =
  'w-full rounded-lg border border-gray-300 bg-background-light px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100'

const defaultPolygons: ManualPolygonForm[] = [
  { id: createPolygonId(), zoneId: 'JED_MANUAL_01', coordinates: '21.60,39.10\n21.63,39.14\n21.58,39.18' },
]

const FALLBACK_CITIES = ['Jeddah', 'Riyadh', 'Dammam']
const ALL_CITIES_VALUE = 'all'

export function ZoningWorkspacePage() {
  const [city, setCity] = useState('')  // No default city
  const [method, setMethod] = useState<Method>('clustering')
  const [targetZones, setTargetZones] = useState(5)  // Changed from 12 to 5 (more reasonable default)
  const [rotationOffset, setRotationOffset] = useState(0)  // Changed from 15 to 0
  const [thresholds, setThresholds] = useState<number[]>([15, 30, 45, 60])
  const [maxCustomersPerZone, setMaxCustomersPerZone] = useState(1000)  // Changed from 500 to 1000 (allows larger zones)
  const [maxCustomersInput, setMaxCustomersInput] = useState<string>('1000')  // Local state for input field
  const [applyBalancing, setApplyBalancing] = useState(true)
  const [balanceTolerance, setBalanceTolerance] = useState(20)
  const [manualPolygons, setManualPolygons] = useState<ManualPolygonForm[]>(defaultPolygons)
  const [result, setResult] = useState<GenerateZonesResponse | null>(null)
  const [lastError, setLastError] = useState<string | null>(null)
  const [runMeta, setRunMeta] = useState<{ durationSeconds: number; timestamp: string } | null>(null)
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({})
  const [selectedZone, setSelectedZone] = useState<string>('')  // Filter by generated zone

  const { mutateAsync: generateZones, isPending, isError } = useGenerateZones()
  const { data: cityCatalog } = useCustomerCities()
  
  // Fetch zones from database when city changes and no result exists
  const { data: dbZones } = useZonesFromDatabase(
    city && city !== ALL_CITIES_VALUE ? city : undefined,
    undefined // Don't filter by method - show all zones for the city
  )
  const cityOptions = useMemo(() => {
    const cities: string[] = []
    // Add "All Cities" as first option
    cities.push(ALL_CITIES_VALUE)

    if (cityCatalog?.length) {
      cities.push(...cityCatalog.map((entry) => entry.name))
    } else {
      cities.push(...FALLBACK_CITIES)
    }
    return cities
  }, [cityCatalog])

  useEffect(() => {
    if (!cityOptions.length) {
      if (city !== '') {
        setCity('')
      }
      return
    }
    if (!city || !cityOptions.includes(city)) {
      setCity(cityOptions[0])
    }
  }, [city, cityOptions])

  const {
    items: customerPoints,
    total: customerTotal,
    hasNextPage: hasMoreCustomerPages,
    fetchNextPage: fetchNextCustomerPage,
    isFetchingNextPage: isFetchingMoreCustomers,
  } = useCustomerLocations({
    city: city || ALL_CITIES_VALUE,
    filters: activeFilters,
    pageSize: 5000,  // Increased from 1500 to show all city customers
    enabled: Boolean(city)
  })

  const mapViewport = useMemo(() => {
    return CITY_VIEWPORTS[city] ?? DEFAULT_VIEWPORT
  }, [city])

  // Use database zones for counts and assignments when no result exists
  const effectiveResult = useMemo(() => {
    // Prefer result from generation, otherwise use zones from database
    const effective = result || dbZones
    if (dbZones && !result) {
      console.log('🗺️ Using zones from database:', {
        polygonCount: dbZones.metadata?.map_overlays?.polygons?.length ?? 0,
        city: dbZones.city,
        method: dbZones.method,
      })
    }
    return effective
  }, [result, dbZones])
  
  const balancingMetadata = useMemo<BalancingMetadata | null>(() => {
    if (!effectiveResult?.metadata) {
      return null
    }
    const metadata = effectiveResult.metadata as { balancing?: BalancingMetadata }
    return metadata.balancing ?? null
  }, [effectiveResult])

  const mapOverlayPolygons = useMemo(() => {
    if (!effectiveResult?.metadata) {
      return []
    }
    
    const metadata = effectiveResult.metadata as { map_overlays?: { polygons?: Array<Record<string, unknown>> } } | undefined
    return (metadata?.map_overlays?.polygons ?? []) as Array<{
      zone_id: string
      coordinates: Array<[number, number]>
      centroid?: [number, number]
      source?: string
      customer_count?: number
    }>
  }, [effectiveResult])

  const zoneColorMap = useMemo(() => {
    const zoneSet = new Set<string>()
    let hasUnassigned = false

    if (effectiveResult?.assignments) {
      Object.values(effectiveResult.assignments).forEach((zoneId) => {
        if (zoneId) {
          zoneSet.add(zoneId)
        }
      })
    }

    customerPoints.forEach((location) => {
      const zoneId = location.zone?.trim()
      if (zoneId) {
        zoneSet.add(zoneId)
      } else {
        hasUnassigned = true
      }
      if (effectiveResult?.assignments && !(location.customer_id in effectiveResult.assignments)) {
        hasUnassigned = true
      }
    })

    mapOverlayPolygons.forEach((polygon) => {
      if (polygon.zone_id) {
        zoneSet.add(polygon.zone_id)
      }
    })

    const palette: Record<string, string> = {}
    Array.from(zoneSet)
      .sort((a, b) => a.localeCompare(b))
      .forEach((zoneId, index) => {
        palette[zoneId] = colorFromString(zoneId, index)
      })

    if (hasUnassigned) {
      palette.Unassigned = '#6b7280'
    }

    return palette
  }, [customerPoints, mapOverlayPolygons, effectiveResult])

  const summaryRows = useMemo<SummaryRow[]>(() => {
    if (!effectiveResult?.counts?.length) {
      return []
    }
    const counts = effectiveResult.counts
    const total = counts.reduce((acc, row) => acc + row.customer_count, 0)
    if (!total) {
      return counts.map((row) => ({ zone: row.zone_id, customers: row.customer_count, delta: '+0.0%', tolerance: 'in' }))
    }
    const average = total / counts.length
    const toleranceRatio =
      balancingMetadata?.tolerance ?? (applyBalancing ? Number((balanceTolerance / 100).toFixed(2)) : 0)

    return counts.map((row) => {
      const deltaPct = ((row.customer_count - average) / (average || 1)) * 100
      const withinTolerance =
        !toleranceRatio || Math.abs(row.customer_count - average) <= average * toleranceRatio + 1e-6
      return {
        zone: row.zone_id,
        customers: row.customer_count,
        delta: formatPercent(deltaPct),
        tolerance: withinTolerance ? 'in' : 'out',
      }
    })
  }, [applyBalancing, balanceTolerance, balancingMetadata?.tolerance, effectiveResult])

  const transfers = useMemo<TransferRow[]>(() => {
    const list = balancingMetadata?.transfers ?? []
    return list.map((transfer: BalancingTransfer) => ({
      customer: transfer.customer_id,
      fromZone: transfer.from_zone,
      toZone: transfer.to_zone,
      distance: transfer.distance_km != null ? transfer.distance_km.toFixed(1) + ' km' : '—',
    }))
  }, [balancingMetadata?.transfers])

  const lastRunLabel = useMemo(() => {
    // Show run metadata only for newly generated zones, otherwise show zone count from database
    if (runMeta && result?.counts) {
      const timestamp = new Date(runMeta.timestamp)
      const zoneCount = result.counts.length
      let label = timestamp.toLocaleString() + ' - ' + zoneCount.toString() + ' zone'
      if (zoneCount !== 1) {
        label += 's'
      }
      return label
    } else if (effectiveResult?.counts && effectiveResult.counts.length > 0) {
      const zoneCount = effectiveResult.counts.length
      let label = zoneCount.toString() + ' zone'
      if (zoneCount !== 1) {
        label += 's'
      }
      label += ' (from database)'
      return label
    }
    return 'Not executed yet'
  }, [result?.counts, effectiveResult?.counts, runMeta])

  const mapCaption = useMemo(() => {
    if (!city) {
      return 'Select a city to view customers'
    }
    const cityLabel = city === ALL_CITIES_VALUE ? 'All Cities' : city
    return cityLabel + ' - ' + lastRunLabel
  }, [city, lastRunLabel])

  const zoneMarkers = useMemo(() => {
    if (!customerPoints.length) {
      return []
    }
    const assignments = effectiveResult?.assignments ?? {}
    // Use smaller markers for large datasets
    const markerRadius = customerPoints.length > 2000 ? 3 : customerPoints.length > 1000 ? 4 : 6

    // Filter by selected zone if one is selected
    const filteredCustomers = selectedZone
      ? customerPoints.filter((customer) => {
          const assignedZone = assignments[customer.customer_id] ?? customer.zone ?? 'Unassigned'
          return assignedZone === selectedZone
        })
      : customerPoints

    return filteredCustomers.map((customer) => {
      const assignedZone = assignments[customer.customer_id] ?? customer.zone ?? 'Unassigned'
      const markerColor =
        zoneColorMap[assignedZone] ??
        (assignedZone === 'Unassigned' ? '#6b7280' : colorFromString(assignedZone))

      const nameParts: string[] = []
      if (customer.customer_name) {
        nameParts.push(customer.customer_name)
      }
      nameParts.push(customer.customer_id)

      return {
        id: customer.customer_id,
        position: [customer.latitude, customer.longitude] as [number, number],
        color: markerColor,
        radius: markerRadius,
        tooltip: `${nameParts.join(' - ')} - ${assignedZone}`,
      }
    })
  }, [customerPoints, result, zoneColorMap, selectedZone])

  const polygonOverlays = useMemo<MapPolygon[]>(() => {
    if (!mapOverlayPolygons.length) {
      return []
    }
    // Filter by selected zone if one is selected
    const filteredPolygons = selectedZone
      ? mapOverlayPolygons.filter((polygon) => polygon.zone_id === selectedZone)
      : mapOverlayPolygons
    
    return filteredPolygons
      .filter((polygon) => polygon.coordinates.length >= 3)
      .map((polygon) => {
        const color = zoneColorMap[polygon.zone_id] ?? colorFromString(polygon.zone_id)
        const customerCount = (polygon as any).customer_count || 0
        const tooltipText = customerCount > 0 
          ? `${polygon.zone_id} (${customerCount} customers)`
          : polygon.zone_id
        
        return {
          id: polygon.zone_id + '-polygon',
          positions: polygon.coordinates.map((pair) => [pair[0], pair[1]]) as Array<[number, number]>,
          color,
          fillColor: color,
          tooltip: tooltipText,  // Show zone ID + customer count
        }
      })
  }, [mapOverlayPolygons, zoneColorMap, selectedZone])

  const handleRun = useCallback(async () => {
    setLastError(null)
    if (!city) {
      setLastError('Select a city before generating zones.')
      return
    }
    if (city === ALL_CITIES_VALUE) {
      setLastError('Cannot generate zones for "All Cities". Please select a specific city.')
      return
    }
    const payload: GenerateZonesPayload = {
      city,
      method,
      balance: applyBalancing,
      balance_tolerance: Number((balanceTolerance / 100).toFixed(3)),
    }

    if (method !== 'manual') {
      payload.target_zones = targetZones
    }
    if (method === 'polar') {
      payload.rotation_offset = rotationOffset
    }
    if (method === 'isochrone') {
      payload.thresholds = thresholds
    }
    if (method === 'clustering') {
      payload.max_customers_per_zone = maxCustomersPerZone
    }
    if (method === 'manual') {
      let polygons: ManualPolygonPayload[]
      try {
        polygons = parseManualPolygons(manualPolygons)
      } catch (error) {
        setLastError((error as Error).message)
        return
      }
      if (!polygons.length) {
        setLastError('Add at least one polygon with 3 or more vertices before running manual zoning.')
        return
      }
      payload.polygons = polygons
    }

    const start = performance.now()
    try {
      const response = await generateZones(payload)
      const durationSeconds = Number(((performance.now() - start) / 1000).toFixed(2))
      setResult(response)
      setRunMeta({ durationSeconds, timestamp: new Date().toISOString() })
      setSelectedZone('')  // Reset zone filter when new zones are generated
    } catch (error) {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        (error as Error).message ??
        'Unable to generate zones.'
      setLastError(message)
    }
  }, [
    applyBalancing,
    balanceTolerance,
    city,
    generateZones,
    manualPolygons,
    maxCustomersPerZone,
    method,
    rotationOffset,
    targetZones,
    thresholds,
  ])

  // Sync input state when maxCustomersPerZone changes externally
  useEffect(() => {
    if (method === 'clustering') {
      setMaxCustomersInput(String(maxCustomersPerZone))
    }
  }, [maxCustomersPerZone, method])

  const handleReset = useCallback(() => {
    setTargetZones(5)  // Changed from 12 to 5
    setRotationOffset(0)  // Changed from 15 to 0
    setThresholds([15, 30, 45, 60])
    setMaxCustomersPerZone(1000)  // Changed from 500 to 1000
    setMaxCustomersInput('1000')
    setManualPolygons(defaultPolygons)
    setApplyBalancing(true)
    setBalanceTolerance(20)
    setResult(null)
    setRunMeta(null)
    setSelectedZone('')  // Reset zone filter
    setLastError(null)
  }, [])

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Zoning Workspace</h2>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Configure parameters and generate zone assignments using the Intelligent Zone Generator backend.
          </p>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-100 dark:hover:bg-gray-800"
        >
          <RefreshCw className="h-4 w-4" /> Refresh OSRM Status
        </button>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <div className="space-y-5">
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60 space-y-5">
            <Field label="City">
              <select
                value={city}
                onChange={(event) => setCity(event.target.value)}
                className={inputClasses}
                disabled={!cityOptions.length}
              >
                {cityOptions.length ? (
                  cityOptions.map((option) => (
                    <option key={option} value={option}>
                      {option === ALL_CITIES_VALUE ? 'All Cities' : option}
                    </option>
                  ))
                ) : (
                  <option value="">No cities detected</option>
                )}
              </select>
            </Field>
          </section>

          {/* Zone Filter - Shows Generated Zones (including manual) */}
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Zone (Generated)
            </label>
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
                disabled={
                (method === 'manual' && manualPolygons.filter(p => p.coordinates).length === 0) ||
                (method !== 'manual' && (!effectiveResult || !effectiveResult.counts || !Array.isArray(effectiveResult.counts) || effectiveResult.counts.length === 0))
              }
              className="w-full rounded-lg border border-gray-300 bg-background-light px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {method === 'manual' ? (
                <>
                  <option value="">All Zones</option>
                  {manualPolygons
                    .filter((p) => p.coordinates && p.zoneId)
                    .sort((a, b) => a.zoneId.localeCompare(b.zoneId))
                    .map((polygon) => {
                      const coords = polygon.coordinates.split('\n')
                        .map((line) => line.trim())
                        .filter(Boolean)
                        .map((line) => {
                          const parts = line.split(',')
                          return [Number(parts[0]), Number(parts[1])] as [number, number]
                        })
                        .filter((coord) => Number.isFinite(coord[0]) && Number.isFinite(coord[1]))
                      const customerCount = coords.length >= 3 ? countPointsInPolygon(customerPoints, coords) : 0
                      return (
                        <option key={polygon.id} value={polygon.zoneId}>
                          {polygon.zoneId} ({customerCount} customers)
                        </option>
                      )
                    })}
                </>
              ) : effectiveResult && effectiveResult.counts && Array.isArray(effectiveResult.counts) && effectiveResult.counts.length > 0 ? (
                <>
                  <option value="">All Zones</option>
                  {effectiveResult.counts
                    .sort((a, b) => a.zone_id.localeCompare(b.zone_id))
                    .map((zoneCount) => (
                      <option key={zoneCount.zone_id} value={zoneCount.zone_id}>
                        {zoneCount.zone_id} ({zoneCount.customer_count} customers)
                      </option>
                    ))}
                </>
              ) : (
                <option value="">No zones generated yet</option>
              )}
            </select>
          </section>

          <FilterPanel
            onFiltersChange={setActiveFilters}
            activeFilters={activeFilters}
            customerCount={selectedZone ? zoneMarkers.length : customerPoints.length}
            totalCustomers={customerTotal}
            selectedCity={city !== ALL_CITIES_VALUE ? city : undefined}
          />

          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60 space-y-5">
            <Field label="Target zones">
            <input
              type="number"
              min={1}
              max={24}
              value={targetZones}
              onChange={(event) => setTargetZones(Number(event.target.value))}
              className={inputClasses}
            />
          </Field>

          <Field label="Method">
            <div className="grid grid-cols-2 gap-2">
              {(['polar', 'isochrone', 'clustering', 'manual'] as Method[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setMethod(option)}
                  className={
                    method === option
                      ? 'rounded-lg bg-primary px-3 py-2 text-sm font-semibold capitalize text-white shadow'
                      : 'rounded-lg bg-gray-100 px-3 py-2 text-sm font-semibold capitalize text-gray-700 transition hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700'
                  }
                >
                  {option}
                </button>
              ))}
            </div>
          </Field>

          {method === 'polar' && (
            <>
              <Field label={'Rotation offset (' + rotationOffset.toFixed(0) + '°)'}>
                <input
                  type="range"
                  min={0}
                  max={90}
                  value={rotationOffset}
                  onChange={(event) => setRotationOffset(Number(event.target.value))}
                  className="w-full accent-primary"
                />
              </Field>
              <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 dark:bg-blue-900/20 dark:border-blue-800">
                <p className="text-xs font-semibold text-blue-800 dark:text-blue-200 mb-1">
                  💡 Center Point Recommendation
                </p>
                <p className="text-xs text-blue-700 dark:text-blue-300">
                  Polar zones radiate from the depot/distribution center. Sectors are drawn from this central point outward at equal angles.
                </p>
              </div>
            </>
          )}

          {method === 'isochrone' && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Travel time thresholds (minutes)</p>
              <div className="flex flex-wrap gap-2">
                {thresholds.map((value, index) => (
                  <span
                    key={String(value) + '-' + String(index)}
                    className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary dark:bg-primary/20 dark:text-primary-100"
                  >
                    {value}
                    <button
                      type="button"
                      aria-label="Remove threshold"
                      className="rounded-full p-1 hover:bg-primary/20 dark:hover:bg-primary/40"
                      onClick={() => setThresholds(thresholds.filter((_, idx) => idx !== index))}
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setThresholds((prev) => [...prev, prev.length ? prev[prev.length - 1] + 15 : 15])}
                className="inline-flex items-center gap-2 rounded-full border border-gray-300 px-3 py-1 text-xs font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
              >
                <Plus className="h-3 w-3" /> Add threshold
              </button>
            </div>
          )}

          {method === 'clustering' && (
            <Field label="Target max customers per zone">
              <input
                type="number"
                min={230}
                max={5000}
                value={maxCustomersInput}
                onChange={(event) => {
                  // Allow free typing - update local input state
                  setMaxCustomersInput(event.target.value)
                }}
                onBlur={(event) => {
                  // Validate when user finishes editing (clicks away)
                  const value = Number(event.target.value)
                  if (isNaN(value) || value < 230) {
                    const finalValue = 230
                    setMaxCustomersPerZone(finalValue)
                    setMaxCustomersInput(String(finalValue))
                  } else if (value > 5000) {
                    const finalValue = 5000
                    setMaxCustomersPerZone(finalValue)
                    setMaxCustomersInput(String(finalValue))
                  } else {
                    setMaxCustomersPerZone(value)
                    setMaxCustomersInput(String(value))
                  }
                }}
                className={inputClasses}
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Target value (not enforced). Minimum: 230 customers per zone.
              </p>
            </Field>
          )}

          {method === 'manual' && (
            <ManualPolygonEditor
              polygons={manualPolygons}
              onChange={setManualPolygons}
              customerPoints={customerPoints}
            />
          )}

          <div className="rounded-xl border border-primary/30 bg-primary/10 p-4 text-sm dark:border-primary/40 dark:bg-primary/20">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-primary dark:text-primary-100">Balance after generation</span>
              <input
                type="checkbox"
                checked={applyBalancing}
                onChange={(event) => setApplyBalancing(event.target.checked)}
                className="h-4 w-4 rounded border-primary text-primary focus:ring-primary/40"
              />
            </div>
            <label className="mt-3 block text-xs text-primary dark:text-primary-100">
              {'Tolerance (' + balanceTolerance.toString() + '%)'}
              <input
                type="range"
                min={0}
                max={40}
                value={balanceTolerance}
                onChange={(event) => setBalanceTolerance(Number(event.target.value))}
                className="mt-1 w-full accent-primary"
              />
            </label>
          </div>

          <div className="space-y-2">
            <button
              type="button"
              onClick={handleRun}
              disabled={isPending || !city}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <Target className="h-4 w-4" />
              {isPending ? 'Running…' : 'Generate zones'}
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            >
              Reset parameters
            </button>
            {lastError ? (
              <p className="rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
                {lastError}
              </p>
            ) : isError ? (
              <p className="rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
                Unable to generate zones. Adjust parameters and try again.
              </p>
            ) : null}
          </div>

          {/* Results Section */}
          <div className="rounded-lg border border-yellow-200 bg-yellow-50/80 p-3 text-sm text-yellow-800 dark:border-yellow-500/40 dark:bg-yellow-500/10 dark:text-yellow-100">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              <p>Transfers may trigger finance “clearness”. Review before publishing.</p>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300">
            <p className="font-semibold text-gray-800 dark:text-gray-100">Last run</p>
            <p>{runMeta ? lastRunLabel + ' - ' + runMeta.durationSeconds.toString() + 's' : 'Not executed yet'}</p>
          </div>

          <SummaryTable rows={summaryRows} hasResult={Boolean(result)} />

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Transfers</h3>
            {transfers.length ? (
              <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-300">
                {transfers.map((transfer) => (
                  <li key={transfer.customer + '-' + transfer.toZone} className="rounded-md border border-gray-200 bg-white/80 px-3 py-2 dark:border-gray-700 dark:bg-gray-900/60">
                    <span className="font-semibold text-gray-800 dark:text-gray-100">{transfer.customer}</span>
                    {' moved from '}
                    <span className="font-semibold text-gray-800 dark:text-gray-100">{transfer.fromZone}</span>
                    {' to '}
                    <span className="font-semibold text-gray-800 dark:text-gray-100">{transfer.toZone}</span>
                    {' - ' + transfer.distance}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300">
                No balancing transfers recorded for the latest run.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Downloads</h3>
            <div className="flex flex-wrap gap-2">
              <DownloadButton
                disabled={!result}
                onClick={() => {
                  if (result) {
                    downloadJson(result, 'zones_' + result.method + '_' + city + '.json')
                  }
                }}
              >
                Summary (JSON)
              </DownloadButton>
              <DownloadButton
                disabled={!result}
                onClick={() => {
                  if (result) {
                    downloadCsv(buildAssignmentsCsv(result), 'zone_assignments_' + city + '.csv')
                  }
                }}
              >
                Assignments (CSV)
              </DownloadButton>
              <DownloadButton
                disabled={!transfers.length}
                onClick={() => {
                  if (transfers.length) {
                    downloadCsv(buildTransfersCsv(transfers), 'zone_transfers_' + city + '.csv')
                  }
                }}
              >
                Transfers (CSV)
              </DownloadButton>
              <DownloadButton
                disabled={!result}
                onClick={() => {
                  if (result && polygonOverlays.length > 0) {
                    const geojson = buildGeoJSON(polygonOverlays, result, city, result.method)
                    downloadJson(geojson, 'zones_' + result.method + '_' + city + '.geojson')
                  }
                }}
              >
                GeoJSON
              </DownloadButton>
            </div>
          </div>
        </section>
        </div>

        {/* Main map area - right column */}
        <section className="space-y-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
          {/* Warning for large dataset */}
          {city === ALL_CITIES_VALUE && customerTotal > 5000 && (
            <div className="flex items-center gap-3 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800 dark:border-yellow-500/30 dark:bg-yellow-500/10 dark:text-yellow-200">
              <AlertTriangle className="h-5 w-5" />
              <div>
                <p className="font-semibold">Large dataset detected ({customerTotal.toLocaleString()} customers)</p>
                <p className="text-xs">
                  For better performance, select a specific city. Currently showing first {customerPoints.length.toLocaleString()} customers.
                </p>
              </div>
            </div>
          )}

          {method === 'manual' ? (
            <DrawableMap
              center={mapViewport.center}
              zoom={mapViewport.zoom}
              markers={zoneMarkers}
              drawnPolygons={manualPolygons
                .map((p) => {
                  const coords = parsePolygonCoordinates(p.coordinates)
                  return {
                    id: p.id,
                    zoneId: p.zoneId,
                    coordinates: coords,
                    customerCount: coords.length >= 3 ? countPointsInPolygon(customerPoints, coords) : 0,
                    color: p.color,
                    isEditing: p.isEditing,
                    isDrawing: p.isDrawing,
                  }
                })
                .filter((p) => p.coordinates.length >= 3 || p.isDrawing)}
              onPolygonCreated={(coordinates) => {
                const coordinatesStr = coordinates.map((coord) => `${coord[0].toFixed(5)},${coord[1].toFixed(5)}`).join('\n')
                
                // Check for overlaps with existing polygons
                const existingPolygons = manualPolygons
                  .filter((p) => p.coordinates && parsePolygonCoordinates(p.coordinates).length >= 3)
                  .map((p) => ({ id: p.id, zoneId: p.zoneId, coordinates: parsePolygonCoordinates(p.coordinates) }))
                
                let hasOverlap = false
                let overlappingZoneId = ''
                
                for (const existing of existingPolygons) {
                  if (doPolygonsOverlap(coordinates, existing.coordinates)) {
                    hasOverlap = true
                    overlappingZoneId = existing.zoneId
                    break
                  }
                }
                
                if (hasOverlap) {
                  // Show error and don't save the polygon
                  setLastError(`Cannot create overlapping zone! This polygon overlaps with zone "${overlappingZoneId}". Each zone must be unique and not overlap with others.`)
                  return
                }
                
                // Find the polygon that's in drawing mode
                const drawingPolygon = manualPolygons.find((p) => p.isDrawing)

                if (drawingPolygon) {
                  // Update the drawing polygon with coordinates and disable drawing mode
                  console.log('📍 Assigning drawn polygon to', drawingPolygon.zoneId)
                  setManualPolygons(
                    manualPolygons.map((p) =>
                      p.id === drawingPolygon.id
                        ? { ...p, coordinates: coordinatesStr, isDrawing: false }
                        : p
                    )
                  )
                } else {
                  // Fallback: create new polygon if no drawing mode active
                  setManualPolygons([
                    ...manualPolygons,
                    { id: createPolygonId(), zoneId: 'MANUAL_' + String(manualPolygons.length + 1).padStart(2, '0'), coordinates: coordinatesStr },
                  ])
                }
              }}
              onPolygonEdited={(polygonId, coordinates) => {
                const coordinatesStr = coordinates.map((coord) => `${coord[0].toFixed(5)},${coord[1].toFixed(5)}`).join('\n')
                
                // Check for overlaps with OTHER existing polygons (not the one being edited)
                const otherPolygons = manualPolygons
                  .filter((p) => p.id !== polygonId && p.coordinates)
                  .map((p) => {
                    const coords = p.coordinates.split('\n')
                      .map((line) => line.trim())
                      .filter(Boolean)
                      .map((line) => {
                        const parts = line.split(',')
                        return [Number(parts[0]), Number(parts[1])] as [number, number]
                      })
                      .filter((coord) => Number.isFinite(coord[0]) && Number.isFinite(coord[1]))
                    return { id: p.id, zoneId: p.zoneId, coordinates: coords }
                  })
                  .filter((p) => p.coordinates.length >= 3)
                
                let hasOverlap = false
                let overlappingZoneId = ''
                
                for (const other of otherPolygons) {
                  if (doPolygonsOverlap(coordinates, other.coordinates)) {
                    hasOverlap = true
                    overlappingZoneId = other.zoneId
                    break
                  }
                }
                
                if (hasOverlap) {
                  // Show error and revert the edit
                  setLastError(`Cannot edit zone - it would overlap with zone "${overlappingZoneId}"! Each zone must be unique and not overlap with others.`)
                  // Don't update the polygon
                  return
                }
                
                // No overlap, update the polygon
                console.log('📝 Updating polygon', polygonId, 'with new coordinates')
                setManualPolygons(
                  manualPolygons.map((p) => (p.id === polygonId ? { ...p, coordinates: coordinatesStr } : p))
                )
              }}
              onPolygonDeleted={() => {
                if (manualPolygons.length > 0) {
                  setManualPolygons(manualPolygons.slice(0, -1))
                }
              }}
              caption={`${city} - Draw polygons to define zones`}
              className="h-[calc(100vh-12rem)]"
            />
          ) : (
            <InteractiveMap
              center={mapViewport.center}
              zoom={mapViewport.zoom}
              caption={mapCaption}
              markers={zoneMarkers}
              polygons={polygonOverlays}
              className="h-[calc(100vh-12rem)]"
            />
          )}

          {/* Customer count info */}
          {hasMoreCustomerPages ? (
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
              <p>
                Displaying {customerPoints.length.toLocaleString()} of {customerTotal.toLocaleString()} customers for this selection.
              </p>
              <button
                type="button"
                onClick={() => fetchNextCustomerPage()}
                disabled={isFetchingMoreCustomers}
                className="inline-flex items-center rounded-full border border-gray-300 px-3 py-1 font-semibold text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                {isFetchingMoreCustomers ? 'Loading…' : 'Load more'}
              </button>
            </div>
          ) : null}
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

function ManualPolygonEditor({
  polygons,
  onChange,
  customerPoints,
}: {
  polygons: ManualPolygonForm[]
  onChange: (value: ManualPolygonForm[]) => void
  customerPoints: Array<{ customer_id: string; latitude: number; longitude: number; customer_name?: string; zone?: string }>
}) {
  // Calculate customer counts for each polygon
  const polygonsWithCounts = useMemo(() => {
    return polygons.map((polygon) => {
      const coordinates = parsePolygonCoordinates(polygon.coordinates)
      const count = coordinates.length >= 3 ? countPointsInPolygon(customerPoints, coordinates) : 0
      return { ...polygon, customerCount: count }
    })
  }, [polygons, customerPoints])

  const updatePolygon = (id: string, updates: Partial<ManualPolygonForm>) => {
    onChange(polygons.map((polygon) => (polygon.id === id ? { ...polygon, ...updates } : polygon)))
  }

  const removePolygon = (id: string) => {
    onChange(polygons.filter((polygon) => polygon.id !== id))
  }

  const addPolygon = () => {
    onChange([
      ...polygons,
      { id: createPolygonId(), zoneId: 'MANUAL_' + String(polygons.length + 1).padStart(2, '0'), coordinates: '' },
    ])
  }

  return (
    <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm dark:border-gray-700 dark:bg-gray-800/60">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Manual polygons</p>
        <button
          type="button"
          onClick={addPolygon}
          className="inline-flex items-center gap-2 rounded-full border border-primary px-3 py-1 text-xs font-semibold text-primary transition hover:bg-primary/10 dark:border-primary-100 dark:text-primary-100 dark:hover:bg-primary/30"
        >
          <Plus className="h-3 w-3" /> Add polygon
        </button>
      </div>

      {/* List of polygons with customer counts and manual coordinate entry */}
      <div className="space-y-2">
        {polygons.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white p-4 text-center dark:border-gray-600 dark:bg-gray-900/60">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Draw polygons on the main map or add them manually
            </p>
          </div>
        ) : (
          polygons.map((polygon) => {
            const polygonData = polygonsWithCounts.find((p) => p.id === polygon.id)
            const customerCount = polygonData?.customerCount ?? 0
            const coordinates = parsePolygonCoordinates(polygon.coordinates)
            const area = calculatePolygonArea(coordinates)
            const polygonColor = polygon.color || '#3b82f6'

            return (
            <div key={polygon.id} className="space-y-2 rounded-lg border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-700 dark:bg-gray-900/60">
              {/* Header with Zone ID and action buttons */}
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={polygon.zoneId}
                  onChange={(event) => updatePolygon(polygon.id, { zoneId: event.target.value })}
                  className={inputClasses}
                  placeholder="Zone ID"
                  readOnly={!polygon.isEditing}
                  disabled={!polygon.isEditing}
                />
                <button
                  type="button"
                  onClick={() => {
                    console.log('🔘 Draw button clicked! Polygon:', polygon.id, 'isDrawing:', polygon.isDrawing, 'coordinates:', polygon.coordinates)
                    // If activating drawing, disable drawing on all other polygons
                    if (!polygon.isDrawing) {
                      console.log('🖍️ Activating drawing mode for polygon:', polygon.id)
                      const updated = polygons.map((p) =>
                        p.id === polygon.id
                          ? { ...p, isDrawing: true, isEditing: false }
                          : { ...p, isDrawing: false }
                      )
                      console.log('📋 Updated polygons:', updated)
                      onChange(updated)
                    } else {
                      console.log('🛑 Deactivating drawing mode for polygon:', polygon.id)
                      updatePolygon(polygon.id, { isDrawing: false })
                    }
                  }}
                  disabled={polygon.coordinates.trim() !== ''}
                  className={`rounded-full p-2 transition ${
                    polygon.coordinates.trim() !== ''
                      ? 'cursor-not-allowed text-gray-300 dark:text-gray-600'
                      : polygon.isDrawing
                      ? 'bg-green-100 text-green-600 dark:bg-green-900/40 dark:text-green-300'
                      : 'text-gray-500 hover:bg-gray-100 hover:text-green-500 dark:hover:bg-gray-800'
                  }`}
                  title={
                    polygon.coordinates.trim() !== ''
                      ? "Polygon already drawn"
                      : polygon.isDrawing
                      ? "Stop drawing"
                      : "Draw this polygon"
                  }
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => updatePolygon(polygon.id, { isEditing: !polygon.isEditing })}
                  disabled={polygon.coordinates.trim() === ''}
                  className={`rounded-full p-2 transition ${
                    polygon.coordinates.trim() === ''
                      ? 'cursor-not-allowed text-gray-300 dark:text-gray-600'
                      : polygon.isEditing
                      ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-300'
                      : 'text-gray-500 hover:bg-gray-100 hover:text-blue-500 dark:hover:bg-gray-800'
                  }`}
                  title={
                    polygon.coordinates.trim() === ''
                      ? "No polygon to edit"
                      : polygon.isEditing
                      ? "Stop editing"
                      : "Edit this polygon"
                  }
                >
                  <Edit3 className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => removePolygon(polygon.id)}
                  className="rounded-full p-2 text-gray-500 transition hover:bg-gray-100 hover:text-red-500 dark:hover:bg-gray-800"
                  disabled={polygons.length === 1}
                  title="Delete polygon"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              {/* Color picker and stats */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Color:</label>
                  <input
                    type="color"
                    value={polygonColor}
                    onChange={(event) => updatePolygon(polygon.id, { color: event.target.value })}
                    className={`h-8 w-12 rounded border border-gray-300 dark:border-gray-600 ${
                      polygon.isEditing ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
                    }`}
                    title={polygon.isEditing ? "Choose polygon color" : "Enable edit mode to change color"}
                    disabled={!polygon.isEditing}
                  />
                </div>
                <div className="flex-1 text-xs text-gray-600 dark:text-gray-400">
                  <span className="font-semibold">{customerCount}</span> customers •{' '}
                  <span className="font-semibold">{area.toFixed(2)}</span> km²
                </div>
              </div>

              {/* Coordinates textarea */}
              <textarea
                value={polygon.coordinates}
                onChange={(event) => updatePolygon(polygon.id, { coordinates: event.target.value })}
                rows={4}
                className="w-full rounded-lg border border-gray-300 bg-background-light px-3 py-2 text-xs text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
                placeholder="Lat,Lon (one per line)"
                readOnly={!polygon.isEditing}
                disabled={!polygon.isEditing}
              />
              <p className="text-[11px] text-gray-400 dark:text-gray-500">
                Enter latitude,longitude per line (minimum three vertices)
              </p>
            </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// Helper function to parse coordinates from string
function parsePolygonCoordinates(coordinatesStr: string): Array<[number, number]> {
  const lines = coordinatesStr
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const coordinates: Array<[number, number]> = []
  for (const line of lines) {
    const parts = line.split(',')
    if (parts.length === 2) {
      const lat = Number(parts[0].trim())
      const lon = Number(parts[1].trim())
      if (Number.isFinite(lat) && Number.isFinite(lon)) {
        coordinates.push([lat, lon])
      }
    }
  }
  return coordinates
}

// Calculate polygon area in km² using the Haversine formula
function calculatePolygonArea(coordinates: Array<[number, number]>): number {
  if (coordinates.length < 3) return 0

  // Earths radius in kilometers
  const EARTH_RADIUS_KM = 6371

  // Convert degrees to radians
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180

  // Calculate area using spherical excess formula
  let area = 0
  const numPoints = coordinates.length

  for (let i = 0; i < numPoints; i++) {
    const [lat1, lon1] = coordinates[i]
    const [lat2, lon2] = coordinates[(i + 1) % numPoints]

    const lat1Rad = toRadians(lat1)
    const lat2Rad = toRadians(lat2)
    const lon1Rad = toRadians(lon1)
    const lon2Rad = toRadians(lon2)

    area += (lon2Rad - lon1Rad) * (2 + Math.sin(lat1Rad) + Math.sin(lat2Rad))
  }

  area = Math.abs((area * EARTH_RADIUS_KM * EARTH_RADIUS_KM) / 2)
  return area
}

function SummaryTable({ rows, hasResult }: { rows: SummaryRow[]; hasResult: boolean }) {
  if (!rows.length) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300">
        {hasResult ? 'No zone counts were returned for this run.' : 'Run the solver to see zone counts.'}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
        <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-300">
          <tr>
            <th className="px-4 py-3 text-left">Zone</th>
            <th className="px-4 py-3 text-left">Customers</th>
            <th className="px-4 py-3 text-left">Δ %</th>
            <th className="px-4 py-3 text-left">Tolerance</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {rows.map((row) => (
            <tr key={row.zone} className="bg-white dark:bg-background-dark/80">
              <td className="px-4 py-3 font-semibold text-gray-900 dark:text-white">{row.zone}</td>
              <td className="px-4 py-3 text-gray-700 dark:text-gray-200">{row.customers.toLocaleString()}</td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.delta}</td>
              <td className="px-4 py-3">
                {row.tolerance === 'in' ? (
                  <span className="inline-flex rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700 dark:bg-green-500/20 dark:text-green-200">
                    In tolerance
                  </span>
                ) : (
                  <span className="inline-flex rounded-full bg-yellow-100 px-3 py-1 text-xs font-semibold text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-200">
                    Outside tolerance
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DownloadButton({ disabled, onClick, children }: { disabled?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-2 rounded-full border border-primary px-3 py-1.5 text-xs font-semibold text-primary transition hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60 dark:border-primary-100 dark:text-primary-100 dark:hover:bg-primary/30"
    >
      <Download className="h-4 w-4" /> {children}
    </button>
  )
}

function createPolygonId() {
  return 'poly-' + Math.random().toString(36).slice(2, 8)
}

function parseManualPolygons(forms: ManualPolygonForm[]): ManualPolygonPayload[] {
  const polygons: ManualPolygonPayload[] = []
  for (const form of forms) {
    const zoneId = form.zoneId.trim()
    if (!zoneId) {
      continue
    }
    const lines = form.coordinates
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
    if (!lines.length) {
      continue
    }
    const coordinates: Array<[number, number]> = []
    for (const line of lines) {
      const parts = line.split(',')
      if (parts.length !== 2) {
        throw new Error('Invalid coordinate pair "' + line + '" in zone ' + zoneId + '.')
      }
      const lat = Number(parts[0].trim())
      const lon = Number(parts[1].trim())
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        throw new Error('Coordinates must be numeric for zone ' + zoneId + '. Found "' + line + '".')
      }
      coordinates.push([lat, lon])
    }
    if (coordinates.length < 3) {
      throw new Error('Zone ' + zoneId + ' must have at least three coordinate points.')
    }
    polygons.push({ zone_id: zoneId, coordinates })
  }
  return polygons
}

function formatPercent(value: number) {
  if (Number.isNaN(value)) {
    return '0.0%'
  }
  const sign = value >= 0 ? '+' : ''
  return sign + value.toFixed(1) + '%'
}

function downloadJson(data: GenerateZonesResponse, filename: string) {
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

function buildAssignmentsCsv(result: GenerateZonesResponse) {
  const header = 'CustomerId,ZoneId'
  const rows = Object.entries(result.assignments).map(([customerId, zoneId]) => customerId + ',' + zoneId)
  return [header, ...rows].join('\n')
}

function buildTransfersCsv(rows: TransferRow[]) {
  const header = 'CustomerId,FromZone,ToZone,DistanceKm'
  const csvRows = rows.map((row) => row.customer + ',' + row.fromZone + ',' + row.toZone + ',' + row.distance.replace(' km', ''))
  return [header, ...csvRows].join('\n')
}

function buildGeoJSON(
  polygons: MapPolygon[],
  result: GenerateZonesResponse,
  city: string,
  method: string
): unknown[] {
  return polygons.map((polygon, index) => {
    const zoneId = polygon.id.replace('-polygon', '')
    const coordinates = polygon.positions.map((pos) => `${pos[1]} ${pos[0]}`).join(',')
    const wkt = `POLYGON((${coordinates}))`

    // Calculate centroid
    const lats = polygon.positions.map((pos) => pos[0])
    const lons = polygon.positions.map((pos) => pos[1])
    const centroidLat = lats.reduce((a, b) => a + b, 0) / lats.length
    const centroidLon = lons.reduce((a, b) => a + b, 0) / lons.length

    const customerCount = result.counts?.find((c) => c.zone_id === zoneId)?.customer_count || 0

    return {
      id: crypto.randomUUID(),
      name: zoneId,
      group: city.toUpperCase(),
      featureClass: '2',
      wkt,
      json: JSON.stringify({
        type: method,
        subType: null,
        labelPoint: { _x: centroidLon, _y: centroidLat },
      }),
      visible: true,
      symbology: {
        fillColor: polygon.fillColor || polygon.color,
        fillOpacity: 0.33,
        lineColor: 'black',
        lineWidth: 2,
        lineOpacity: 0.5,
        scale: null,
      },
      styledGeom: null,
      notes: `tag : ${city.toUpperCase()}|${zoneId}\ngroup : ${city.toUpperCase()}\nname : ${zoneId}\nmethod : ${method}\ncustomers : ${customerCount}\n`,
      nodeTags: [],
      nameTagPlacementPoint: null,
      simplificationMeters: 0,
      modifiedTimestamp: 0,
      managerId: null,
      collapsed: true,
      locked: null,
    }
  })
}
