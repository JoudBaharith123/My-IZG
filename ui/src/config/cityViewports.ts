export type CityViewport = {
  center: [number, number]
  zoom: number
}

export const DEFAULT_VIEWPORT: CityViewport = {
  center: [23.8859, 45.0792],
  zoom: 6,
}

export const CITY_VIEWPORTS: Record<string, CityViewport> = {
  Jeddah: { center: [21.4858, 39.1925], zoom: 11 },
  Riyadh: { center: [24.7136, 46.6753], zoom: 10 },
  Dammam: { center: [26.4207, 50.0888], zoom: 11 },
}
