import type { LatLngExpression, LatLngTuple } from 'leaflet'
import { CircleMarker, LayerGroup, MapContainer, Polygon, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import clsx from 'clsx'

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
                {marker.tooltip ? <Tooltip>{marker.tooltip}</Tooltip> : null}
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
