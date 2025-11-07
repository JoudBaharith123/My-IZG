import { useEffect, useRef } from 'react'
import type { LatLngExpression, LatLngTuple } from 'leaflet'
import L from 'leaflet'
import { CircleMarker, LayerGroup, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet-draw'
import clsx from 'clsx'

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

  useEffect(() => {
    if (!map) return

    // Create feature group for drawn items
    const featureGroup = new L.FeatureGroup()
    featureGroup.addTo(map)
    featureGroupRef.current = featureGroup

    // Initialize draw control
    const drawControl = new L.Control.Draw({
      position: 'topright',
      draw: {
        polygon: {
          allowIntersection: false,
          showArea: true,
          shapeOptions: {
            color: '#3b82f6',
            weight: 2,
            fillOpacity: 0.2,
          },
        },
        polyline: false,
        rectangle: false,
        circle: false,
        marker: false,
        circlemarker: false,
      },
      edit: {
        featureGroup: featureGroup,
        remove: true,
        edit: {} as never,
      },
    })

    drawControl.addTo(map)
    drawControlRef.current = drawControl

    // Event handlers
    map.on(L.Draw.Event.CREATED, (event: L.LeafletEvent) => {
      const drawEvent = event as unknown as L.DrawEvents.Created
      const layer = drawEvent.layer as L.Polygon

      if (drawEvent.layerType === 'polygon') {
        featureGroup.addLayer(layer)

        const latLngs = layer.getLatLngs()[0] as L.LatLng[]
        const coordinates: Array<[number, number]> = latLngs.map((latLng) => [latLng.lat, latLng.lng])

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
          const layerId = L.Util.stamp(layer).toString()

          if (onPolygonEdited) {
            onPolygonEdited(layerId, coordinates)
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
      if (drawControlRef.current) {
        map.removeControl(drawControlRef.current)
      }
      if (featureGroupRef.current) {
        map.removeLayer(featureGroupRef.current)
      }
      map.off(L.Draw.Event.CREATED)
      map.off(L.Draw.Event.EDITED)
      map.off(L.Draw.Event.DELETED)
    }
  }, [map, onPolygonCreated, onPolygonEdited, onPolygonDeleted])

  // Render existing polygons
  useEffect(() => {
    if (!featureGroupRef.current) return

    // Clear existing layers
    featureGroupRef.current.clearLayers()

    // Add drawn polygons
    drawnPolygons.forEach((polygon) => {
      const latLngs: LatLngTuple[] = polygon.coordinates.map((coord) => [coord[0], coord[1]])
      const layer = L.polygon(latLngs, {
        color: '#3b82f6',
        weight: 2,
        fillOpacity: 0.2,
      })

      // Add tooltip with customer count if available
      if (polygon.customerCount !== undefined) {
        layer.bindTooltip(`${polygon.customerCount} customers`, { permanent: false, sticky: true })
      }

      featureGroupRef.current?.addLayer(layer)
    })
  }, [drawnPolygons])

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

      {/* Drawing instructions */}
      <div className="pointer-events-none absolute left-3 top-3 rounded-lg bg-blue-50/90 px-3 py-2 text-xs text-blue-800 shadow backdrop-blur dark:bg-blue-900/70 dark:text-blue-100">
        <p className="font-semibold">Drawing Tools:</p>
        <p>• Click polygon tool (top right) to start</p>
        <p>• Click map to add vertices</p>
        <p>• Double-click or click first point to finish</p>
        <p>• Use edit tool to move vertices</p>
      </div>
    </div>
  )
}
