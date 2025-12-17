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
  const isDraggingRef = useRef(false)
  const isInitializedRef = useRef(false)
  const hasLocalEditsRef = useRef(false) // Track if user has made local edits

  // Initialize component once
  useEffect(() => {
    if (!map) return
    if (!positions || positions.length < 3) return
    if (isInitializedRef.current) return // Don't recreate if already initialized

    // Store initial positions
    currentPositionsRef.current = [...positions]

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
        marker.on('dragstart', () => {
          isDraggingRef.current = true
          hasLocalEditsRef.current = true // Mark that user has made local edits
        })

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
        
        // Update all markers to match new positions
        markersRef.current.forEach((m, i) => {
          if (i < newPositions.length) {
            m.setLatLng(newPositions[i])
          }
        })
        
        // Ensure polygon is closed (first point = last point) before sending to backend
        // Backend expects closed polygons
        const closedPositions = [...newPositions]
        if (closedPositions.length > 0) {
          const first = closedPositions[0]
          const last = closedPositions[closedPositions.length - 1]
          // Only add closing point if not already closed
          if (first[0] !== last[0] || first[1] !== last[1]) {
            closedPositions.push([first[0], first[1]])
          }
        }
        
        // Call onEdit with CLOSED polygon coordinates
        if (onEdit) {
          onEdit(id, closedPositions)
        }
        
        // Set dragging to false after a delay to allow the save to complete
        // This prevents the component from resetting if the query refetches quickly
        setTimeout(() => {
          isDraggingRef.current = false
        }, 500) // 500ms delay should be enough for the save to complete
      })

      marker.addTo(map)
      vertexMarkers.push(marker)
    })

    markersRef.current = vertexMarkers
    isInitializedRef.current = true

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
      isInitializedRef.current = false
    }
  }, [map, id, color, fillColor, tooltip, onEdit])

  // Update positions only when not dragging
  useEffect(() => {
    if (!isInitializedRef.current) return
    if (isDraggingRef.current) return
    
    // Check if positions changed
    const hasChanged = positions.length !== currentPositionsRef.current.length ||
      positions.some((pos, i) => {
        const current = currentPositionsRef.current[i]
        if (!current) return true
        const threshold = 0.00001
        return Math.abs(pos[0] - current[0]) > threshold || Math.abs(pos[1] - current[1]) > threshold
      })
    
    if (hasChanged) {
      currentPositionsRef.current = [...positions]
      
      // Update polygon
      if (polygonRef.current) {
        const closedPositions = [...positions]
        const first = closedPositions[0]
        const last = closedPositions[closedPositions.length - 1]
        if (first[0] !== last[0] || first[1] !== last[1]) {
          closedPositions.push([first[0], first[1]])
        }
        polygonRef.current.setLatLngs(closedPositions)
      }
      
      // Update markers
      markersRef.current.forEach((marker, index) => {
        if (index < positions.length) {
          marker.setLatLng(positions[index])
        }
      })
      
      if (hasLocalEditsRef.current) {
        hasLocalEditsRef.current = false
      }
    }
  }, [positions])

  return null
}

