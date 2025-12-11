/**
 * Geometry utility functions for spatial calculations
 */

/**
 * Check if a point is inside a polygon using ray-casting algorithm
 * @param lat - Point latitude
 * @param lon - Point longitude
 * @param polygon - Array of [lat, lon] coordinates defining the polygon
 * @returns true if point is inside polygon, false otherwise
 */
export function isPointInPolygon(
  lat: number,
  lon: number,
  polygon: Array<[number, number]>
): boolean {
  if (polygon.length < 3) {
    return false
  }

  let inside = false
  const n = polygon.length

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i][0]
    const yi = polygon[i][1]
    const xj = polygon[j][0]
    const yj = polygon[j][1]

    const intersect =
      yi > lon !== yj > lon && lat < ((xj - xi) * (lon - yi)) / (yj - yi) + xi

    if (intersect) {
      inside = !inside
    }
  }

  return inside
}

/**
 * Count how many points fall within a polygon
 * @param points - Array of points with lat/lon coordinates
 * @param polygon - Array of [lat, lon] coordinates defining the polygon
 * @returns Number of points inside the polygon
 */
export function countPointsInPolygon(
  points: Array<{ latitude: number; longitude: number }>,
  polygon: Array<[number, number]>
): number {
  if (polygon.length < 3) {
    return 0
  }

  let count = 0
  for (const point of points) {
    if (isPointInPolygon(point.latitude, point.longitude, polygon)) {
      count++
    }
  }

  return count
}

/**
 * Get the customer IDs that fall within a polygon
 * @param customers - Array of customers with coordinates
 * @param polygon - Array of [lat, lon] coordinates defining the polygon
 * @returns Array of customer IDs inside the polygon
 */
export function getCustomersInPolygon(
  customers: Array<{ customer_id: string; latitude: number; longitude: number }>,
  polygon: Array<[number, number]>
): string[] {
  if (polygon.length < 3) {
    return []
  }

  const customersInside: string[] = []
  for (const customer of customers) {
    if (isPointInPolygon(customer.latitude, customer.longitude, polygon)) {
      customersInside.push(customer.customer_id)
    }
  }

  return customersInside
}

/**
 * Check if two polygons overlap/intersect
 */
export function doPolygonsOverlap(
  polygon1: Array<[number, number]>,
  polygon2: Array<[number, number]>,
): boolean {
  if (polygon1.length < 3 || polygon2.length < 3) {
    return false
  }

  // Check if any vertex of polygon1 is inside polygon2
  for (const [lat, lon] of polygon1) {
    if (isPointInPolygon(lat, lon, polygon2)) {
      return true
    }
  }

  // Check if any vertex of polygon2 is inside polygon1
  for (const [lat, lon] of polygon2) {
    if (isPointInPolygon(lat, lon, polygon1)) {
      return true
    }
  }

  // Check if any edges intersect
  for (let i = 0; i < polygon1.length; i++) {
    const p1Start = polygon1[i]
    const p1End = polygon1[(i + 1) % polygon1.length]
    
    for (let j = 0; j < polygon2.length; j++) {
      const p2Start = polygon2[j]
      const p2End = polygon2[(j + 1) % polygon2.length]
      
      if (doLineSegmentsIntersect(p1Start, p1End, p2Start, p2End)) {
        return true
      }
    }
  }

  return false
}

/**
 * Check if two line segments intersect
 */
function doLineSegmentsIntersect(
  p1: [number, number],
  p2: [number, number],
  p3: [number, number],
  p4: [number, number],
): boolean {
  const ccw = (a: [number, number], b: [number, number], c: [number, number]) => {
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
  }
  
  return ccw(p1, p3, p4) !== ccw(p2, p3, p4) && ccw(p1, p2, p3) !== ccw(p1, p2, p4)
}