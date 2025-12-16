import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import type { LatLngTuple } from 'leaflet'
import L from 'leaflet'

interface SimpleEditablePolygonProps {
  id: string
  positions: LatLngTuple[]
  color?: string
  fillColor?: string
  tooltip?: string
  onEdit?: (id: string, coordinates: LatLngTuple[]) => void
}

export function SimpleEditablePolygon({
  id,
  positions,
  color = '#2563eb',
  fillColor,
  tooltip,
  onEdit,
}: SimpleEditablePolygonProps) {
  const map = useMap()
  const polygonRef = useRef<L.Polygon | null>(null)
  const markersRef = useRef<L.Marker[]>([])
  const currentPositionsRef = useRef<LatLngTuple[]>(positions)

  useEffect(() => {
    if (!map) return
    if (!positions || positions.length < 3) return

    // Update ref with latest positions
    currentPositionsRef.current = [...positions]

    // Remove old polygon and markers
    if (polygonRef.current) {
      map.removeLayer(polygonRef.current)
    }
    markersRef.current.forEach(marker => {
      try {
        map.removeLayer(marker)
      } catch (e) {
        // Already removed
      }
    })
    markersRef.current = []

    // Create polygon - make sure it's closed
    const closedPositions = [...positions]
    if (closedPositions.length > 0) {
      const first = closedPositions[0]
      const last = closedPositions[closedPositions.length - 1]
      if (first[0] !== last[0] || first[1] !== last[1]) {
        closedPositions.push([first[0], first[1]])
      }
    }

    // Create polygon with visible edges
    const polygon = L.polygon(closedPositions, {
      color: color,
      weight: 4, // Thick border so edges are visible
      fillColor: fillColor || color,
      fillOpacity: 0.2,
      opacity: 0.9,
    })

    polygonRef.current = polygon
    polygon.addTo(map)

    // Add tooltip
    if (tooltip) {
      polygon.bindTooltip(tooltip, {
        permanent: false,
        direction: 'center',
      })
    }

    // Create draggable vertex markers at each corner
    const vertexMarkers: L.Marker[] = []
    positions.forEach((pos, index) => {
      // Create a visible, draggable marker for each vertex
      const marker = L.marker([pos[0], pos[1]], {
        icon: L.divIcon({
          className: 'zone-vertex-marker',
          html: '<div style="width: 14px; height: 14px; background-color: #3b82f6; border: 3px solid white; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.3); cursor: move;"></div>',
          iconSize: [14, 14],
          iconAnchor: [7, 7],
        }),
        draggable: true,
        zIndexOffset: 1000,
      })

      // Update polygon when vertex is dragged
      marker.on('drag', () => {
        const newPos = marker.getLatLng()
        const newPositions = [...currentPositionsRef.current]
        newPositions[index] = [newPos.lat, newPos.lng]
        currentPositionsRef.current = newPositions
        
        // Update polygon immediately
        const closedNewPositions = [...newPositions]
        const first = closedNewPositions[0]
        closedNewPositions.push([first[0], first[1]])
        if (polygonRef.current) {
          polygonRef.current.setLatLngs(closedNewPositions)
        }
      })

      // Save to database when drag ends
      marker.on('dragend', () => {
        const newPos = marker.getLatLng()
        const newPositions = [...currentPositionsRef.current]
        newPositions[index] = [newPos.lat, newPos.lng]
        currentPositionsRef.current = newPositions
        
        // Call onEdit to save to database
        if (onEdit) {
          onEdit(id, newPositions)
        }
      })

      marker.addTo(map)
      vertexMarkers.push(marker)
    })

    markersRef.current = vertexMarkers

    // Cleanup
    return () => {
      if (polygonRef.current) {
        map.removeLayer(polygonRef.current)
      }
      markersRef.current.forEach(marker => {
        try {
          map.removeLayer(marker)
        } catch (e) {
          // Already removed
        }
      })
    }
  }, [map, id, color, fillColor, tooltip, onEdit])

  return null
}

