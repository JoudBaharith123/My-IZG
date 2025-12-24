import type { LatLngExpression, LatLngTuple } from 'leaflet'
import L from 'leaflet'
import { Fragment } from 'react'
import { CircleMarker, LayerGroup, MapContainer, Marker, Polygon, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import clsx from 'clsx'
import { SimpleEditablePolygon } from './SimpleEditablePolygon'

// Add custom CSS for customer tooltips and editable polygons
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

  /* Zone vertex markers - visible and draggable */
  .zone-vertex-marker {
    background: transparent !important;
    border: none !important;
  }

  .zone-vertex-marker div {
    cursor: move !important;
    transition: transform 0.2s, background-color 0.2s !important;
  }

  .zone-vertex-marker div:hover {
    transform: scale(1.4) !important;
    background-color: #2563eb !important;
  }

  /* Editable polygon styling - visible vertices */
  .editable-zone-polygon {
    stroke-dasharray: 5, 5;
    animation: dash 20s linear infinite;
  }

  @keyframes dash {
    to {
      stroke-dashoffset: -1000;
    }
  }

  /* Make vertices more visible */
  .leaflet-marker-icon.editable-vertex-icon {
    background-color: #3b82f6 !important;
    border: 3px solid white !important;
    border-radius: 50% !important;
    width: 12px !important;
    height: 12px !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
    cursor: move !important;
  }

  .leaflet-marker-icon.editable-vertex-icon:hover {
    background-color: #2563eb !important;
    transform: scale(1.3);
    transition: transform 0.2s;
  }

  /* Middle markers (for adding new vertices) */
  .leaflet-edit-marker-selected {
    background-color: #10b981 !important;
    border: 2px solid white !important;
  }

  /* Zone tooltip styling */
  .zone-tooltip {
    background-color: rgba(255, 255, 255, 0.95) !important;
    border: 2px solid #3b82f6 !important;
    border-radius: 6px !important;
    padding: 6px 10px !important;
    font-weight: 600 !important;
  }

  /* Stop number label styling - for DivIcon markers */
  .stop-number-marker {
    background: transparent !important;
    border: none !important;
  }
  
  .stop-number-label {
    background-color: rgba(255, 255, 255, 0.98) !important;
    border: 2px solid #1f2937 !important;
    border-radius: 50% !important;
    width: 26px !important;
    height: 26px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-weight: 800 !important;
    font-size: 13px !important;
    color: #1f2937 !important;
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.25) !important;
    pointer-events: none !important;
    line-height: 1 !important;
    padding: 0 !important;
    margin: 0 !important;
    opacity: 1 !important;
    visibility: visible !important;
    z-index: 1000 !important;
  }
  
  /* Ensure stop numbers stay visible on map interactions */
  .leaflet-container .stop-number-label {
    pointer-events: none !important;
    opacity: 1 !important;
    visibility: visible !important;
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
  stopNumber?: number // Stop sequence number to display above marker
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
  editable?: boolean
  onPolygonEdit?: (id: string, coordinates: Array<[number, number]>) => void
}

const DEFAULT_CENTER: LatLngExpression = [23.8859, 45.0792]

// Helper function to calculate position offset for stop number label
// Moves the position slightly north to appear above the marker
// Uses a fixed offset that works reasonably well across zoom levels
function getStopNumberPosition(position: LatLngExpression, radius: number): LatLngExpression {
  if (Array.isArray(position)) {
    const [lat, lng] = position
    // Calculate offset in degrees to position label above the marker
    // Approximately 0.0001 degrees ≈ 11 meters, which works well for positioning
    // Offset increases with marker radius to position further above larger markers
    const offsetDegrees = (radius + 10) * 0.00008
    return [lat + offsetDegrees, lng]
  }
  return position
}

export function InteractiveMap({
  center = DEFAULT_CENTER,
  zoom = 6,
  className,
  caption,
  markers,
  polygons,
  polylines,
  editable = false,
  onPolygonEdit,
}: InteractiveMapProps) {
  return (
    <div
      className={clsx(
        'relative h-full w-full overflow-hidden rounded-2xl border border-gray-200 bg-gray-200 dark:border-gray-700 dark:bg-gray-900',
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
            {polygons?.map((polygon) => 
              editable ? (
                <SimpleEditablePolygon
                  key={polygon.id}
                  id={polygon.id}
                  positions={polygon.positions}
                  color={polygon.color ?? '#2563eb'}
                  fillColor={polygon.fillColor ?? polygon.color ?? '#2563eb'}
                  tooltip={polygon.tooltip}
                  onEdit={onPolygonEdit}
                />
              ) : (
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
              )
            )}
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
              <Fragment key={marker.id}>
                <CircleMarker
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
                      offset={marker.stopNumber !== undefined ? [0, -35] : [0, -10]}
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
                {marker.stopNumber !== undefined ? (
                  <Marker
                    position={getStopNumberPosition(marker.position, marker.radius ?? 6)}
                    icon={L.divIcon({
                      className: 'stop-number-marker',
                      html: `<div class="stop-number-label">${marker.stopNumber}</div>`,
                      iconSize: [26, 26],
                      iconAnchor: [13, 13],
                    })}
                    zIndexOffset={1000}
                    interactive={false}
                  />
                ) : null}
              </Fragment>
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
