import { useCallback, useEffect, useMemo, useState, useRef } from 'react'
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
import { useUpdateZoneGeometry } from '../../hooks/useUpdateZoneGeometry'
import { useUnassignCustomer } from '../../hooks/useUnassignCustomer'
import { useAssignCustomer } from '../../hooks/useAssignCustomer'
import { useUnassignedCustomers } from '../../hooks/useUnassignedCustomers'
import { useDatabaseZoneSummaries } from '../../hooks/useDatabaseZoneSummaries'
import { useDeleteZones } from '../../hooks/useDeleteZones'

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
  const [editMode, setEditMode] = useState(false)  // Enable editing for all zones
  const [selectedUnassignedCustomer, setSelectedUnassignedCustomer] = useState<string>('')  // Selected customer from unassigned pool
  const [selectedZoneCustomer, setSelectedZoneCustomer] = useState<string>('')  // Selected customer from zone dropdown
  const [showTransferModal, setShowTransferModal] = useState(false)  // Show transfer modal
  const [customerToTransfer, setCustomerToTransfer] = useState<string>('')  // Customer ID to transfer
  const [selectedZonesForAction, setSelectedZonesForAction] = useState<Set<string>>(new Set())  // Zones selected for delete/regenerate

  const { mutateAsync: generateZones, isPending, isError } = useGenerateZones()
  const { mutateAsync: updateZoneGeometry } = useUpdateZoneGeometry()
  const { mutateAsync: unassignCustomer, isPending: isUnassigning } = useUnassignCustomer()
  const { mutateAsync: assignCustomer, isPending: isAssigning } = useAssignCustomer()
  const { mutateAsync: deleteZones, isPending: isDeletingZones } = useDeleteZones()
  const { data: cityCatalog } = useCustomerCities()
  
  // Fetch zones from database when city changes and no result exists
  const { data: dbZones } = useZonesFromDatabase(
    city && city !== ALL_CITIES_VALUE ? city : undefined,
    undefined // Don't filter by method - show all zones for the city
  )
  
  // Get unassigned customers and zone summaries for transfer
  const { data: unassignedCustomers } = useUnassignedCustomers(city && city !== ALL_CITIES_VALUE ? city : undefined)
  const { data: zoneSummariesForTransfer } = useDatabaseZoneSummaries(city && city !== ALL_CITIES_VALUE ? city : undefined)
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
      const metadata = dbZones.metadata as { map_overlays?: { polygons?: Array<unknown> } } | undefined
      console.log('🗺️ Using zones from database:', {
        polygonCount: metadata?.map_overlays?.polygons?.length ?? 0,
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

  // Calculate actual customer count for selected zone based on assignments
  const selectedZoneCustomerCount = useMemo(() => {
    if (!selectedZone || !effectiveResult?.assignments) {
      return null
    }
    
    const assignments = effectiveResult.assignments
    // Count customers assigned to this zone in the assignments
    const count = Object.values(assignments).filter(zoneId => zoneId === selectedZone).length
    return count
  }, [selectedZone, effectiveResult?.assignments])

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
          // Check assignments first, then fall back to customer.zone
          const assignedZone = assignments[customer.customer_id] ?? customer.zone ?? 'Unassigned'
          const matches = assignedZone === selectedZone
          return matches
        })
      : customerPoints

    return filteredCustomers.map((customer) => {
      const assignedZone = assignments[customer.customer_id] ?? customer.zone ?? 'Unassigned'
      const markerColor =
        zoneColorMap[assignedZone] ??
        (assignedZone === 'Unassigned' ? '#6b7280' : colorFromString(assignedZone))

      // Format tooltip with customer name as primary info
      let tooltipText = ''
      if (customer.customer_name) {
        tooltipText = `${customer.customer_name}\n${customer.customer_id}`
      } else {
        tooltipText = customer.customer_id
      }
      tooltipText += `\nZone: ${assignedZone}`

      return {
        id: customer.customer_id,
        position: [customer.latitude, customer.longitude] as [number, number],
        color: markerColor,
        radius: markerRadius,
        tooltip: tooltipText,
        // Store customer info for potential popup
        customerName: customer.customer_name || customer.customer_id,
        customerId: customer.customer_id,
        zone: assignedZone,
      }
    })
  }, [customerPoints, effectiveResult, zoneColorMap, selectedZone])

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

    // If zones are selected for regeneration, delete them first
    if (selectedZonesForAction.size > 0) {
      payload.delete_existing_zones = Array.from(selectedZonesForAction)
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
    selectedZonesForAction,
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
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setEditMode(!editMode)}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition ${
              editMode
                ? 'border-primary bg-primary text-white hover:bg-primary/90'
                : 'border-gray-200 text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-100 dark:hover:bg-gray-800'
            }`}
            disabled={!polygonOverlays.length}
          >
            <Pencil className="h-4 w-4" /> {editMode ? 'Exit Edit Mode' : 'Edit Zones'}
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-100 dark:hover:bg-gray-800"
          >
            <RefreshCw className="h-4 w-4" /> Refresh OSRM Status
          </button>
        </div>
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
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60 space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Zone (Generated)
              </label>
              <select
                value={selectedZone}
                onChange={(e) => {
                  setSelectedZone(e.target.value)
                  setSelectedZoneCustomer('') // Clear selected customer when zone changes
                }}
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
                  {(() => {
                    // Calculate actual counts from assignments for accuracy
                    const assignments = effectiveResult.assignments ?? {}
                    const actualCounts = new Map<string, number>()
                    Object.values(assignments).forEach((zoneId) => {
                      if (zoneId) {
                        actualCounts.set(zoneId, (actualCounts.get(zoneId) || 0) + 1)
                      }
                    })
                    
                    return effectiveResult.counts
                      .sort((a, b) => a.zone_id.localeCompare(b.zone_id))
                      .map((zoneCount) => {
                        // Use actual count from assignments if available, otherwise use stored count
                        const actualCount = actualCounts.get(zoneCount.zone_id) ?? zoneCount.customer_count
                        return (
                          <option key={zoneCount.zone_id} value={zoneCount.zone_id}>
                            {zoneCount.zone_id} ({actualCount} customers)
                          </option>
                        )
                      })
                  })()}
                </>
              ) : (
                <option value="">No zones generated yet</option>
              )}
            </select>
            </div>

            {/* Zone Selection for Delete/Regenerate */}
            {effectiveResult && effectiveResult.counts && Array.isArray(effectiveResult.counts) && effectiveResult.counts.length > 0 && (
              <div className="space-y-2 border-t border-gray-200 pt-4 dark:border-gray-700">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Select Zones for Actions
                </label>
                <div className="max-h-48 space-y-2 overflow-y-auto">
                  {effectiveResult.counts
                    .sort((a, b) => a.zone_id.localeCompare(b.zone_id))
                    .map((zoneCount) => {
                      const isSelected = selectedZonesForAction.has(zoneCount.zone_id)
                      return (
                        <label
                          key={zoneCount.zone_id}
                          className="flex items-center gap-2 rounded-lg border border-gray-200 p-2 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800/60 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              const newSelected = new Set(selectedZonesForAction)
                              if (e.target.checked) {
                                newSelected.add(zoneCount.zone_id)
                              } else {
                                newSelected.delete(zoneCount.zone_id)
                              }
                              setSelectedZonesForAction(newSelected)
                            }}
                            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                          />
                          <span className="flex-1 text-sm text-gray-900 dark:text-white">
                            {zoneCount.zone_id} ({zoneCount.customer_count} customers)
                          </span>
                        </label>
                      )
                    })}
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={async () => {
                      if (selectedZonesForAction.size === 0) {
                        setLastError('Please select at least one zone to delete')
                        return
                      }
                      if (!confirm(`Are you sure you want to delete ${selectedZonesForAction.size} zone(s)? This action cannot be undone.`)) {
                        return
                      }
                      try {
                        await deleteZones({ zone_ids: Array.from(selectedZonesForAction) })
                        setSelectedZonesForAction(new Set())
                        setSelectedZone('')
                        console.log(`✅ Deleted ${selectedZonesForAction.size} zone(s)`)
                      } catch (error) {
                        console.error(`❌ Failed to delete zones:`, error)
                        setLastError(`Failed to delete zones. Please try again.`)
                      }
                    }}
                    disabled={selectedZonesForAction.size === 0 || isDeletingZones}
                    className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isDeletingZones ? 'Deleting...' : `Delete (${selectedZonesForAction.size})`}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedZonesForAction.size === 0) {
                        setLastError('Please select at least one zone to regenerate')
                        return
                      }
                      // Set the target zones to match selected zones count for regeneration
                      const targetZonesCount = selectedZonesForAction.size
                      setTargetZones(targetZonesCount)
                      // Show info message
                      setLastError(null)
                      // Note: The actual regeneration will happen when user clicks "Run" button
                      // The selected zones will be deleted and new ones created
                    }}
                    disabled={selectedZonesForAction.size === 0}
                    className="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Prepare Regenerate ({selectedZonesForAction.size})
                  </button>
                </div>
                {selectedZonesForAction.size > 0 && (
                  <button
                    type="button"
                    onClick={() => setSelectedZonesForAction(new Set())}
                    className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                  >
                    Clear Selection
                  </button>
                )}
              </div>
            )}

            {/* Zone Customers Dropdown - Show customers in selected zone */}
            {selectedZone && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Customers in Zone
                </label>
                {(() => {
                  const assignments = effectiveResult?.assignments ?? {}
                  const zoneCustomers = customerPoints.filter((customer) => {
                    const assignedZone = assignments[customer.customer_id] ?? customer.zone ?? 'Unassigned'
                    return assignedZone === selectedZone
                  })

                  if (zoneCustomers.length === 0) {
                    return <p className="text-sm text-gray-500 dark:text-gray-400">No customers in this zone</p>
                  }

                  return (
                    <div className="space-y-2">
                      <SearchableCustomerDropdown
                        customers={zoneCustomers}
                        value={selectedZoneCustomer}
                        onChange={setSelectedZoneCustomer}
                        placeholder="Search customers in zone..."
                      />
                      
                      {selectedZoneCustomer && zoneCustomers.some(c => c.customer_id === selectedZoneCustomer) && (
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={async () => {
                              try {
                                await unassignCustomer({
                                  zone_id: selectedZone,
                                  customer_id: selectedZoneCustomer,
                                })
                                setSelectedZoneCustomer('')
                                console.log(`✅ Customer ${selectedZoneCustomer} unassigned from zone ${selectedZone}`)
                              } catch (error) {
                                console.error(`❌ Failed to unassign customer:`, error)
                                setLastError(`Failed to unassign customer. Please try again.`)
                              }
                            }}
                            disabled={isUnassigning}
                            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Unassign
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setCustomerToTransfer(selectedZoneCustomer)
                              setShowTransferModal(true)
                            }}
                            disabled={isAssigning}
                            className="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Transfer
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })()}
              </div>
            )}
          </section>

          {/* Unassigned Pool */}
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Unassigned Pool ({unassignedCustomers?.count || 0})
            </label>
            <p className="mb-2 text-xs text-gray-500 dark:text-gray-400">
              Unassigned customers will be automatically assigned when zones are created that include their location. You can also manually assign them to a zone below.
            </p>
            {unassignedCustomers?.customer_ids && unassignedCustomers.customer_ids.length > 0 ? (
              <>
                <SearchableCustomerDropdown
                  customers={unassignedCustomers.customer_ids.map((customerId) => {
                    const customer = customerPoints.find(c => c.customer_id === customerId)
                    return {
                      customer_id: customerId,
                      customer_name: customer?.customer_name || null,
                    }
                  })}
                  value={selectedUnassignedCustomer}
                  onChange={setSelectedUnassignedCustomer}
                  placeholder="Search unassigned customers..."
                />
                {selectedUnassignedCustomer && (
                  <button
                    type="button"
                    onClick={() => {
                      setCustomerToTransfer(selectedUnassignedCustomer)
                      setShowTransferModal(true)
                    }}
                    className="mt-2 w-full rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!selectedUnassignedCustomer || isAssigning}
                  >
                    Assign to Zone
                  </button>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">No unassigned customers</p>
            )}
          </section>

          <FilterPanel
            onFiltersChange={setActiveFilters}
            activeFilters={activeFilters}
            customerCount={
              selectedZone && selectedZoneCustomerCount !== null
                ? selectedZoneCustomerCount  // Use actual count from assignments
                : selectedZone
                ? zoneMarkers.length  // Fallback to marker count if assignments not available
                : customerPoints.length
            }
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
              {isPending 
                ? 'Running…' 
                : selectedZonesForAction.size > 0 
                  ? `Regenerate ${selectedZonesForAction.size} Zone(s)`
                  : 'Generate zones'}
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
          ) : editMode ? (
            <InteractiveMap
              center={mapViewport.center}
              zoom={mapViewport.zoom}
              caption={`${mapCaption} - Edit Mode: Drag the blue circles at polygon corners to reshape zones. Changes are saved automatically.`}
              markers={zoneMarkers}
              polygons={polygonOverlays}
              editable={true}
              onPolygonEdit={async (polygonId, coordinates) => {
                // Extract zone_id from polygon id (format: "zone_id-polygon")
                const zoneId = polygonId.replace('-polygon', '')
                
                try {
                  await updateZoneGeometry({
                    zone_id: zoneId,
                    coordinates: coordinates as Array<[number, number]>,
                  })
                  console.log(`✅ Zone ${zoneId} geometry updated successfully`)
                  setLastError(null)
                } catch (error) {
                  console.error(`❌ Failed to update zone ${zoneId}:`, error)
                  setLastError(`Failed to update zone ${zoneId}. Please try again.`)
                }
              }}
              className="h-[calc(100vh-12rem)]"
            />
          ) : (
            <InteractiveMap
              center={mapViewport.center}
              zoom={mapViewport.zoom}
              caption={mapCaption}
              markers={zoneMarkers}
              polygons={polygonOverlays}
              editable={false}
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

      {/* Transfer Customer Modal */}
      {showTransferModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50">
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
              Assign Customer to Zone
            </h3>
            <p className="mb-4 text-sm text-gray-600 dark:text-gray-300">
              Customer: <strong>{customerToTransfer}</strong>
            </p>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Select Zone
            </label>
            <select
              id="transferZoneSelect"
              className="mb-4 w-full rounded-lg border border-gray-300 bg-background-light px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="">Select a zone...</option>
              {zoneSummariesForTransfer?.map((zone) => (
                <option key={zone.zone} value={zone.zone}>
                  {zone.zone} ({zone.customers} customers)
                </option>
              ))}
            </select>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={async () => {
                  const selectElement = document.getElementById('transferZoneSelect') as HTMLSelectElement
                  const targetZoneId = selectElement?.value
                  
                  if (!targetZoneId) {
                    setLastError('Please select a zone')
                    return
                  }
                  
                  try {
                    await assignCustomer({
                      zone_id: targetZoneId,
                      customer_id: customerToTransfer,
                    })
                    setShowTransferModal(false)
                    setCustomerToTransfer('')
                    setSelectedUnassignedCustomer('')
                    setSelectedZoneCustomer('')
                    console.log(`✅ Customer ${customerToTransfer} assigned to zone ${targetZoneId}`)
                  } catch (error) {
                    console.error(`❌ Failed to transfer customer:`, error)
                    setLastError(`Failed to transfer customer to zone. Please try again.`)
                  }
                }}
                disabled={isAssigning}
                className="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isAssigning ? 'Transferring...' : 'Transfer'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowTransferModal(false)
                  setCustomerToTransfer('')
                }}
                disabled={isAssigning}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
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

// Searchable dropdown component for customer selection
function SearchableCustomerDropdown({
  customers,
  value,
  onChange,
  placeholder = 'Select a customer...',
}: {
  customers: Array<{ customer_id: string; customer_name?: string | null }>
  value: string
  onChange: (customerId: string) => void
  placeholder?: string
}) {
  const [searchTerm, setSearchTerm] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Filter customers based on search term
  const filteredCustomers = useMemo(() => {
    if (!searchTerm.trim()) {
      return customers
    }
    const lowerSearch = searchTerm.toLowerCase()
    return customers.filter((customer) => {
      const name = (customer.customer_name || '').toLowerCase()
      const id = customer.customer_id.toLowerCase()
      return name.includes(lowerSearch) || id.includes(lowerSearch)
    })
  }, [customers, searchTerm])

  // Get display name for selected customer
  const selectedCustomer = customers.find((c) => c.customer_id === value)
  const displayValue = selectedCustomer
    ? selectedCustomer.customer_name
      ? `${selectedCustomer.customer_name} (${selectedCustomer.customer_id})`
      : selectedCustomer.customer_id
    : ''

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleSelect = (customerId: string) => {
    onChange(customerId)
    setSearchTerm('')
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={isOpen ? searchTerm : displayValue}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            setIsOpen(true)
          }}
          onFocus={() => {
            setSearchTerm('')
            setIsOpen(true)
          }}
          placeholder={placeholder}
          className="w-full rounded-lg border border-gray-300 bg-background-light px-3 py-2 pr-8 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
        />
        {!isOpen && displayValue && (
          <button
            type="button"
            onClick={() => {
              onChange('')
              setSearchTerm('')
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Clear selection"
          >
            ×
          </button>
        )}
      </div>

      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-gray-300 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800"
        >
          {filteredCustomers.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No customers found</div>
          ) : (
            <ul className="py-1">
              {filteredCustomers.map((customer) => {
                const displayName = customer.customer_name
                  ? `${customer.customer_name} (${customer.customer_id})`
                  : customer.customer_id
                const isSelected = customer.customer_id === value
                return (
                  <li
                    key={customer.customer_id}
                    onClick={() => handleSelect(customer.customer_id)}
                    className={`cursor-pointer px-3 py-2 text-sm transition ${
                      isSelected
                        ? 'bg-primary text-white'
                        : 'text-gray-900 hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    {displayName}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
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
  return polygons.map((polygon) => {
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
