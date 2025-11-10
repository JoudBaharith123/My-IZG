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
