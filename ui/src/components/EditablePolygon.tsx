import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import type { LatLngTuple } from 'leaflet'
import L from 'leaflet'
import 'leaflet-draw'

interface EditablePolygonProps {
  id: string
  positions: LatLngTuple[]
  color?: string
  fillColor?: string
  tooltip?: string
  editable?: boolean
  onEdit?: (id: string, coordinates: LatLngTuple[]) => void
}

// Shared feature group and edit handler for all editable polygons
let sharedFeatureGroup: L.FeatureGroup | null = null
let editHandler: L.Draw.Edit | null = null
const polygonMap = new Map<string, { polygon: L.Polygon; markers: L.Marker[] }>()

// Initialize feature group on first use
function getOrCreateFeatureGroup(map: L.Map): L.FeatureGroup {
  if (!sharedFeatureGroup) {
    sharedFeatureGroup = new L.FeatureGroup()
    sharedFeatureGroup.addTo(map)
  }
  return sharedFeatureGroup
}

export function EditablePolygon({
  id,
  positions,
  color = '#2563eb',
  fillColor,
  tooltip,
  editable = false,
  onEdit,
}: EditablePolygonProps) {
  const map = useMap()
  const polygonRef = useRef<L.Polygon | null>(null)
  const markersRef = useRef<L.Marker[]>([])

  useEffect(() => {
    if (!map) return
    if (!positions || positions.length < 3) {
      console.warn(`EditablePolygon: Invalid positions for ${id}, need at least 3 points`)
      return // Need at least 3 points for a polygon
    }

    try {
      // Ensure polygon is closed (first and last point should be the same)
      const closedPositions = [...positions]
      const first = closedPositions[0]
      const last = closedPositions[closedPositions.length - 1]
      if (first[0] !== last[0] || first[1] !== last[1]) {
        closedPositions.push([first[0], first[1]])
      }

      // Get or create shared feature group
      const featureGroup = getOrCreateFeatureGroup(map)

      // Remove old polygon and markers if they exist
      const oldData = polygonMap.get(id)
      if (oldData) {
        try {
          featureGroup.removeLayer(oldData.polygon)
        } catch (e) {
          // Polygon might already be removed
        }
        oldData.markers.forEach(marker => {
          try {
            map.removeLayer(marker)
          } catch (e) {
            // Marker might already be removed
          }
        })
      }

      // Create polygon layer with enhanced styling for editable mode
      const polygon = L.polygon(closedPositions, {
      color: editable ? color : color,
      weight: editable ? 4 : 2, // Thicker border when editable
      fillColor: fillColor || color,
      fillOpacity: 0.15,
      opacity: editable ? 0.9 : 0.7,
      className: editable ? 'editable-zone-polygon' : '',
    })

    // Store polygon ID for reference
    ;(polygon as any)._polygonId = id

    polygonRef.current = polygon
    featureGroup.addLayer(polygon)

    // Add tooltip
    if (tooltip) {
      polygon.bindTooltip(tooltip, {
        permanent: false,
        direction: 'center',
        className: 'zone-tooltip',
      })
    }

    // Create draggable vertex markers if editable
    const vertexMarkers: L.Marker[] = []
    if (editable) {
      // Use original positions (not closed) for markers to avoid duplicate last marker
      positions.forEach((pos, index) => {
        const marker = L.marker([pos[0], pos[1]], {
          icon: L.divIcon({
            className: 'editable-vertex-icon',
            html: '<div></div>',
            iconSize: [12, 12],
            iconAnchor: [6, 6],
          }),
          draggable: true,
          zIndexOffset: 1000,
        })

        marker.on('drag', (e: L.LeafletEvent) => {
          const marker = e.target as L.Marker
          const newPos = marker.getLatLng()
          const newPositions = [...positions]
          newPositions[index] = [newPos.lat, newPos.lng]
          
          // Update polygon
          polygon.setLatLngs(newPositions)
          
          // Update other markers positions
          vertexMarkers.forEach((m, i) => {
            if (i !== index) {
              m.setLatLng(newPositions[i])
            }
          })
        })

        marker.on('dragend', () => {
          // Get updated positions from polygon
          const latLngs = polygon.getLatLngs()[0] as L.LatLng[]
          const newCoordinates: LatLngTuple[] = latLngs.map((latLng) => [latLng.lat, latLng.lng])
          
          // Update all markers to match polygon
          vertexMarkers.forEach((m, i) => {
            if (i < newCoordinates.length) {
              m.setLatLng(newCoordinates[i])
            }
          })
          
          if (onEdit) {
            onEdit(id, newCoordinates)
          }
        })

        marker.addTo(map)
        vertexMarkers.push(marker)
      })
    }

    markersRef.current = vertexMarkers
    polygonMap.set(id, { polygon, markers: vertexMarkers })

    // Setup editing with leaflet-draw for additional features (add vertices, etc.)
    if (editable && featureGroup) {
      // Create or update edit handler
      if (!editHandler) {
        editHandler = new L.Draw.Edit(featureGroup, {
          featureGroup: featureGroup,
          edit: {
            selectedPathOptions: {
              color: '#3b82f6',
              weight: 4,
            },
          },
        })

        // Enable editing
        editHandler.enable()

        // Listen for edit events (when using toolbar edit button)
        featureGroup.on('draw:edited', (e: any) => {
          const layers = e.layers
          layers.eachLayer((layer: L.Polygon) => {
            const polygonId = (layer as any)._polygonId
            if (polygonId) {
              const latLngs = layer.getLatLngs()[0] as L.LatLng[]
              const newCoordinates: LatLngTuple[] = latLngs.map((latLng) => [latLng.lat, latLng.lng])
              
              // Update vertex markers
              const data = polygonMap.get(polygonId)
              if (data) {
                data.markers.forEach((marker, i) => {
                  if (i < newCoordinates.length) {
                    marker.setLatLng(newCoordinates[i])
                  }
                })
              }
              
              if (onEdit) {
                onEdit(polygonId, newCoordinates)
              }
            }
          })
        })
      }
    }

      // Cleanup
      return () => {
        try {
          const featureGroup = sharedFeatureGroup
          if (polygonRef.current && featureGroup) {
            featureGroup.removeLayer(polygonRef.current)
          }
          markersRef.current.forEach(marker => {
            try {
              map.removeLayer(marker)
            } catch (e) {
              // Marker might already be removed
            }
          })
          polygonMap.delete(id)
        } catch (error) {
          console.error('Error cleaning up editable polygon:', error)
        }
      }
    } catch (error) {
      console.error('Error creating editable polygon:', error)
      return () => {} // Return empty cleanup function
    }
  }, [map, id, positions, color, fillColor, tooltip, editable, onEdit])

  // Update polygon when positions change (only if not currently being edited)
  useEffect(() => {
    if (polygonRef.current && !editable) {
      polygonRef.current.setLatLngs(positions)
      // Update markers too
      markersRef.current.forEach((marker, i) => {
        if (i < positions.length) {
          marker.setLatLng(positions[i])
        }
      })
    }
  }, [positions, editable])

  return null
}

// Cleanup function to disable editing when all polygons are removed
export function cleanupEditablePolygons() {
  if (editHandler) {
    editHandler.disable()
    editHandler = null
  }
  if (sharedFeatureGroup) {
    sharedFeatureGroup.clearLayers()
    sharedFeatureGroup = null
  }
  polygonMap.clear()
}

