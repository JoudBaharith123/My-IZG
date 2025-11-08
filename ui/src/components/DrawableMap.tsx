import { useEffect, useRef } from 'react'
import type { LatLngExpression, LatLngTuple } from 'leaflet'
import L from 'leaflet'
import { CircleMarker, LayerGroup, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet-draw'
import clsx from 'clsx'

// Add custom CSS for customer count labels and draw controls
const customerCountStyles = `
  .customer-count-label {
    background-color: rgba(59, 130, 246, 0.95) !important;
    border: 2px solid white !important;
    border-radius: 8px !important;
    padding: 6px 12px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    color: white !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
    pointer-events: none !important;
  }
  .customer-count-label::before {
    display: none !important;
  }

  /* Ensure draw controls are visible and properly positioned */
  .leaflet-draw {
    z-index: 1000 !important;
  }
  .leaflet-draw-toolbar {
    z-index: 1000 !important;
    position: relative !important;
    display: block !important;
    visibility: visible !important;
  }
  .leaflet-top.leaflet-right {
    position: absolute !important;
    top: 10px !important;
    right: 10px !important;
    pointer-events: auto !important;
    z-index: 1000 !important;
  }
  .leaflet-draw-toolbar.leaflet-bar {
    position: relative !important;
    display: block !important;
  }
  .leaflet-draw-toolbar a {
    display: block !important;
    width: 30px !important;
    height: 30px !important;
    line-height: 30px !important;
    text-align: center !important;
    text-decoration: none !important;
    background-color: white !important;
    border-bottom: 1px solid #ccc !important;
  }
  .leaflet-draw-toolbar a:first-child {
    border-top-left-radius: 4px !important;
    border-top-right-radius: 4px !important;
  }
  .leaflet-draw-toolbar a:last-child {
    border-bottom-left-radius: 4px !important;
    border-bottom-right-radius: 4px !important;
    border-bottom: none !important;
  }
`

// Inject styles once
if (typeof document !== 'undefined' && !document.getElementById('customer-count-styles')) {
  const styleEl = document.createElement('style')
  styleEl.id = 'customer-count-styles'
  styleEl.textContent = customerCountStyles
  document.head.appendChild(styleEl)
}

export type MapMarker = {
  id: string
  position: LatLngExpression
  color?: string
  radius?: number
  tooltip?: string
}

export type DrawnPolygon = {
  id: string
  coordinates: Array<[number, number]>
  customerCount?: number
  zoneId?: string
  color?: string
  isEditing?: boolean
  isDrawing?: boolean
}

export type DrawableMapProps = {
  center?: LatLngExpression
  zoom?: number
  className?: string
  caption?: string
  markers?: MapMarker[]
  onPolygonCreated?: (coordinates: Array<[number, number]>) => void
  onPolygonEdited?: (id: string, coordinates: Array<[number, number]>) => void
  onPolygonDeleted?: (id: string) => void
  drawnPolygons?: DrawnPolygon[]
}

const DEFAULT_CENTER: LatLngExpression = [23.8859, 45.0792]

// Drawing control component
function DrawControl({
  onPolygonCreated,
  onPolygonEdited,
  onPolygonDeleted,
  drawnPolygons = [],
}: {
  onPolygonCreated?: (coordinates: Array<[number, number]>) => void
  onPolygonEdited?: (id: string, coordinates: Array<[number, number]>) => void
  onPolygonDeleted?: (id: string) => void
  drawnPolygons?: DrawnPolygon[]
}) {
  const map = useMap()
  const featureGroupRef = useRef<L.FeatureGroup | null>(null)
  const drawControlRef = useRef<L.Control.Draw | null>(null)

  // Initialize map infrastructure (runs once)
  useEffect(() => {
    if (!map) return

    // Create feature group for drawn items
    const featureGroup = new L.FeatureGroup()
    featureGroup.addTo(map)
    featureGroupRef.current = featureGroup

    // Event handlers - set up once

    // When drawing starts, disable double-click zoom
    map.on(L.Draw.Event.DRAWSTART, () => {
      console.log('🎨 Drawing started - double-click zoom disabled')
      map.doubleClickZoom.disable()
    })

    // When drawing stops (completed or cancelled), re-enable double-click zoom
    map.on(L.Draw.Event.DRAWSTOP, () => {
      console.log('🛑 Drawing stopped - double-click zoom re-enabled')
      map.doubleClickZoom.enable()
    })

    map.on(L.Draw.Event.CREATED, (event: L.LeafletEvent) => {
      const drawEvent = event as unknown as L.DrawEvents.Created
      const layer = drawEvent.layer as L.Polygon

      if (drawEvent.layerType === 'polygon') {
        featureGroup.addLayer(layer)

        const latLngs = layer.getLatLngs()[0] as L.LatLng[]
        const coordinates: Array<[number, number]> = latLngs.map((latLng) => [latLng.lat, latLng.lng])

        console.log('🎯 Polygon created with', coordinates.length, 'vertices:', coordinates)

        // Store the layer ID for future reference
        const layerId = L.Util.stamp(layer)
        ;(layer as unknown as { _leaflet_id: number })._leaflet_id = layerId

        if (onPolygonCreated) {
          onPolygonCreated(coordinates)
        }
      }
    })

    map.on(L.Draw.Event.EDITED, (event: L.LeafletEvent) => {
      const editEvent = event as unknown as L.DrawEvents.Edited
      const layers = editEvent.layers
      layers.eachLayer((layer) => {
        if (layer instanceof L.Polygon) {
          const latLngs = layer.getLatLngs()[0] as L.LatLng[]
          const coordinates: Array<[number, number]> = latLngs.map((latLng) => [latLng.lat, latLng.lng])
          // Use stored polygon ID if available, otherwise fall back to layer ID
          const polygonId = (layer as any)._polygonId || L.Util.stamp(layer).toString()

          console.log('✏️ Polygon edited:', polygonId, 'with', coordinates.length, 'vertices')

          if (onPolygonEdited) {
            onPolygonEdited(polygonId, coordinates)
          }
        }
      })
    })

    map.on(L.Draw.Event.DELETED, (event: L.LeafletEvent) => {
      const deleteEvent = event as unknown as L.DrawEvents.Deleted
      const layers = deleteEvent.layers
      layers.eachLayer((layer) => {
        const layerId = L.Util.stamp(layer).toString()

        if (onPolygonDeleted) {
          onPolygonDeleted(layerId)
        }
      })
    })

    // Cleanup
    return () => {
      if (featureGroupRef.current) {
        map.removeLayer(featureGroupRef.current)
      }
      map.off(L.Draw.Event.CREATED)
      map.off(L.Draw.Event.EDITED)
      map.off(L.Draw.Event.DELETED)
      map.off(L.Draw.Event.DRAWSTART)
      map.off(L.Draw.Event.DRAWSTOP)
      // Re-enable double-click zoom on cleanup
      map.doubleClickZoom.enable()
    }
  }, [map, onPolygonCreated, onPolygonEdited, onPolygonDeleted])

  // Manage draw controls based on drawing mode
  useEffect(() => {
    if (!map || !featureGroupRef.current) return

    const hasDrawingPolygon = drawnPolygons.some((p) => p.isDrawing)
    console.log('🔍 Drawing mode check:', hasDrawingPolygon)

    // Add controls if needed and not already added
    if (hasDrawingPolygon && !drawControlRef.current) {
      console.log('✅ Adding draw controls to map')
      const drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
          polygon: {
            allowIntersection: false,
            showArea: false,  // Disabled to prevent "type is not defined" error
            repeatMode: false,
            shapeOptions: {
              stroke: true,
              color: '#3b82f6',
              weight: 3,
              opacity: 0.8,
              fill: true,
              fillColor: '#3b82f6',
              fillOpacity: 0.15,
            },
          },
          polyline: false,
          rectangle: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
        edit: {
          featureGroup: featureGroupRef.current,
          remove: false,
        },
      })

      drawControl.addTo(map)
      drawControlRef.current = drawControl

      // Hide the toolbar but automatically activate drawing
      setTimeout(() => {
        // Hide the toolbar
        const toolbar = document.querySelector('.leaflet-draw-toolbar')
        if (toolbar instanceof HTMLElement) {
          toolbar.style.display = 'none'
          console.log('🙈 Draw toolbar hidden')
        }

        // Automatically click the polygon button to start drawing
        const polygonButton = document.querySelector('.leaflet-draw-draw-polygon') as HTMLElement
        if (polygonButton) {
          polygonButton.click()
          console.log('🎨 Auto-activated polygon drawing mode')
        }
      }, 50)

      // Debug: Log the DOM element
      setTimeout(() => {
        const drawToolbar = document.querySelector('.leaflet-draw-toolbar')
        const parentContainer = document.querySelector('.leaflet-top.leaflet-right')
        console.log('🔧 Draw toolbar element:', drawToolbar)
        console.log('📦 Parent container:', parentContainer)
        if (drawToolbar) {
          const styles = window.getComputedStyle(drawToolbar)
          console.log('📊 Toolbar styles:', {
            display: styles.display,
            visibility: styles.visibility,
            position: styles.position,
            zIndex: styles.zIndex,
            top: styles.top,
            right: styles.right
          })
        }
        if (parentContainer) {
          const parentStyles = window.getComputedStyle(parentContainer)
          console.log('📊 Parent container styles:', {
            display: parentStyles.display,
            visibility: parentStyles.visibility,
            position: parentStyles.position,
            zIndex: parentStyles.zIndex,
            top: parentStyles.top,
            right: parentStyles.right,
            width: parentStyles.width,
            height: parentStyles.height
          })
        }
      }, 100)
    }
    // Remove controls if no longer needed
    else if (!hasDrawingPolygon && drawControlRef.current) {
      console.log('❌ Removing draw controls from map')
      map.removeControl(drawControlRef.current)
      drawControlRef.current = null
    }
  }, [map, drawnPolygons])

  // Render existing polygons
  useEffect(() => {
    if (!featureGroupRef.current) return

    // Clear existing layers
    featureGroupRef.current.clearLayers()

    // Add drawn polygons
    drawnPolygons.forEach((polygon) => {
      // Skip polygons without coordinates (in drawing mode but not yet drawn)
      if (polygon.coordinates.length < 3) {
        return
      }

      const latLngs: LatLngTuple[] = polygon.coordinates.map((coord) => [coord[0], coord[1]])
      const polygonColor = polygon.color || '#3b82f6'
      const layer = L.polygon(latLngs, {
        color: polygonColor,
        fillColor: polygonColor,
        weight: 3,
        fillOpacity: 0.15,
      })

      // Store polygon ID on the layer for reference
      ;(layer as any)._polygonId = polygon.id

      // Make the layer editable if isEditing is true
      if (polygon.isEditing) {
        layer.editing?.enable()

        // Listen for edit events on this specific polygon
        layer.on('edit', () => {
          const latLngs = layer.getLatLngs()[0] as L.LatLng[]
          const coordinates: Array<[number, number]> = latLngs.map((latLng) => [latLng.lat, latLng.lng])
          const polygonId = (layer as any)._polygonId

          console.log('🔄 Polygon vertex moved:', polygonId)

          if (onPolygonEdited) {
            onPolygonEdited(polygonId, coordinates)
          }
        })
      } else {
        // Disable editing if isEditing is false
        layer.editing?.disable()
      }

      // Add tooltip with zone name and customer count - make it permanent and visible
      if (polygon.customerCount !== undefined || polygon.zoneId) {
        const zoneName = polygon.zoneId || 'Zone'
        const customerInfo = polygon.customerCount !== undefined ? `${polygon.customerCount} customers` : 'No customers'
        layer.bindTooltip(`<strong>${zoneName}</strong><br/>📍 ${customerInfo}`, {
          permanent: true,
          direction: 'center',
          className: 'customer-count-label',
          opacity: 0.9
        })
      }

      featureGroupRef.current?.addLayer(layer)
    })
  }, [drawnPolygons, onPolygonEdited])

  return null
}

export function DrawableMap({
  center = DEFAULT_CENTER,
  zoom = 6,
  className,
  caption,
  markers = [],
  onPolygonCreated,
  onPolygonEdited,
  onPolygonDeleted,
  drawnPolygons = [],
}: DrawableMapProps) {
  return (
    <div
      className={clsx(
        'relative h-[55vh] w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-200 dark:border-gray-700 dark:bg-gray-900',
        className,
      )}
    >
      <MapContainer center={center} zoom={zoom} scrollWheelZoom={true} className="h-full w-full" style={{ minHeight: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Draw Control */}
        <DrawControl
          onPolygonCreated={onPolygonCreated}
          onPolygonEdited={onPolygonEdited}
          onPolygonDeleted={onPolygonDeleted}
          drawnPolygons={drawnPolygons}
        />

        {/* Customer markers */}
        {markers.length > 0 && (
          <LayerGroup>
            {markers.map((marker) => (
              <CircleMarker
                key={marker.id}
                center={marker.position}
                radius={marker.radius ?? 6}
                pathOptions={{
                  color: marker.color ?? '#2563eb',
                  fillColor: marker.color ?? '#2563eb',
                  fillOpacity: 0.85,
                  weight: 1,
                }}
              >
                {marker.tooltip ? <Tooltip>{marker.tooltip}</Tooltip> : null}
              </CircleMarker>
            ))}
          </LayerGroup>
        )}
      </MapContainer>

      {caption ? (
        <div className="pointer-events-none absolute bottom-3 right-3 rounded-lg bg-white/85 px-3 py-1 text-xs font-medium text-gray-700 shadow backdrop-blur dark:bg-gray-800/70 dark:text-gray-200">
          {caption}
        </div>
      ) : null}

      {/* Drawing instructions - only show when in drawing mode */}
      {drawnPolygons.some((p) => p.isDrawing) && (
        <div className="pointer-events-none absolute left-3 top-3 rounded-lg bg-blue-50/95 px-4 py-3 text-sm text-blue-900 shadow-lg backdrop-blur dark:bg-blue-900/80 dark:text-blue-50">
          <p className="mb-2 font-bold text-blue-950 dark:text-blue-100">🖍️ How to Draw Zones:</p>
          <ol className="ml-4 list-decimal space-y-1">
            <li><strong>SINGLE-CLICK</strong> on the map to place each vertex (corner)</li>
            <li>Add as many vertices as you need (4, 5, 6, 10... unlimited!)</li>
            <li className="font-semibold text-red-800 dark:text-red-200">⚠️ DO NOT DOUBLE-CLICK! Use single clicks only</li>
            <li className="font-semibold text-blue-950 dark:text-blue-100">✅ To finish: CLICK THE FIRST POINT to close</li>
            <li>The customer count will update automatically</li>
          </ol>
        </div>
      )}
    </div>
  )
}
