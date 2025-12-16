import type { LatLngExpression, LatLngTuple } from 'leaflet'
import { CircleMarker, LayerGroup, MapContainer, Polygon, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import clsx from 'clsx'

// Add custom CSS for customer tooltips
const customerTooltipStyles = `
  /* Enhanced customer tooltip styling */
  .customer-tooltip {
    background-color: rgba(255, 255, 255, 0.98) !important;
    border: 2px solid #3b82f6 !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #1f2937 !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    max-width: 250px !important;
    white-space: pre-line !important;
    line-height: 1.6 !important;
    z-index: 1000 !important;
  }
  
  .customer-tooltip .leaflet-tooltip-content {
    margin: 0 !important;
  }
  
  .customer-tooltip::before {
    border-top-color: #3b82f6 !important;
  }
`

// Inject styles once
if (typeof document !== 'undefined' && !document.getElementById('customer-tooltip-styles')) {
  const styleEl = document.createElement('style')
  styleEl.id = 'customer-tooltip-styles'
  styleEl.textContent = customerTooltipStyles
  document.head.appendChild(styleEl)
}

export type MapMarker = {
  id: string
  position: LatLngExpression
  color?: string
  radius?: number
  tooltip?: string
}

export type MapPolygon = {
  id: string
  positions: LatLngTuple[]
  color?: string
  fillColor?: string
  tooltip?: string
}

export type MapPolyline = {
  id: string
  positions: LatLngTuple[]
  color?: string
  weight?: number
  tooltip?: string
}

export type InteractiveMapProps = {
  center?: LatLngExpression
  zoom?: number
  className?: string
  caption?: string
  markers?: MapMarker[]
  polygons?: MapPolygon[]
  polylines?: MapPolyline[]
}

const DEFAULT_CENTER: LatLngExpression = [23.8859, 45.0792]

export function InteractiveMap({
  center = DEFAULT_CENTER,
  zoom = 6,
  className,
  caption,
  markers,
  polygons,
  polylines,
}: InteractiveMapProps) {
  return (
    <div
      className={clsx(
        'relative h-[55vh] w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-200 dark:border-gray-700 dark:bg-gray-900',
        className,
      )}
    >
      <MapContainer center={center} zoom={zoom} scrollWheelZoom={false} className="h-full w-full" style={{ minHeight: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {(polygons?.length || markers?.length || polylines?.length) ? (
          <LayerGroup>
            {polygons?.map((polygon) => (
              <Polygon
                key={polygon.id}
                positions={polygon.positions}
                pathOptions={{
                  color: polygon.color ?? '#2563eb',
                  weight: 2,
                  fillOpacity: 0.1,
                  fillColor: polygon.fillColor ?? polygon.color ?? '#2563eb',
                }}
              >
                {polygon.tooltip ? <Tooltip sticky>{polygon.tooltip}</Tooltip> : null}
              </Polygon>
            ))}
            {polylines?.map((line) => (
              <Polyline
                key={line.id}
                positions={line.positions}
                pathOptions={{
                  color: line.color ?? '#2563eb',
                  weight: line.weight ?? 4,
                  opacity: 0.75,
                }}
              >
                {line.tooltip ? <Tooltip sticky>{line.tooltip}</Tooltip> : null}
              </Polyline>
            ))}
            {markers?.map((marker) => (
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
                {marker.tooltip ? (
                  <Tooltip 
                    sticky 
                    permanent={false}
                    direction="top"
                    offset={[0, -10]}
                    className="customer-tooltip"
                  >
                    <div style={{ 
                      whiteSpace: 'pre-line',
                      textAlign: 'left',
                      lineHeight: '1.5',
                      fontWeight: '500'
                    }}>
                      {marker.tooltip}
                    </div>
                  </Tooltip>
                ) : null}
              </CircleMarker>
            ))}
          </LayerGroup>
        ) : null}
      </MapContainer>
      {caption ? (
        <div className="pointer-events-none absolute bottom-3 right-3 rounded-lg bg-white/85 px-3 py-1 text-xs font-medium text-gray-700 shadow backdrop-blur dark:bg-gray-800/70 dark:text-gray-200">
          {caption}
        </div>
      ) : null}
    </div>
  )
}
