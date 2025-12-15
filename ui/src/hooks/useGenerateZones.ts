import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import { apiClient } from '../api/client'

export type ZoneCount = {
  zone_id: string
  customer_count: number
}

export type BalancingTransfer = {
  customer_id: string
  from_zone: string
  to_zone: string
  distance_km?: number
}

export type BalancingMetadata = {
  transfers?: BalancingTransfer[]
  counts_before?: Record<string, number>
  counts_after?: Record<string, number>
  tolerance?: number
}

export type GenerateZonesResponse = {
  city: string
  method: string
  assignments: Record<string, string>
  counts: ZoneCount[]
  metadata: Record<string, unknown>
}

export type ManualPolygonPayload = {
  zone_id: string
  coordinates: Array<[number, number]>
}

export type GenerateZonesPayload = {
  city: string
  method: 'polar' | 'isochrone' | 'clustering' | 'manual'
  target_zones?: number
  rotation_offset?: number
  thresholds?: number[]
  max_customers_per_zone?: number
  polygons?: ManualPolygonPayload[]
  balance?: boolean
  balance_tolerance?: number
  delete_existing_zones?: string[]  // Zone IDs to delete before generating
}

export function useGenerateZones() {
  return useMutation<GenerateZonesResponse, AxiosError, GenerateZonesPayload>({
    mutationFn: async (payload) => {
      const { delete_existing_zones, ...requestPayload } = payload
      const params: Record<string, string | string[]> = {}
      if (delete_existing_zones && delete_existing_zones.length > 0) {
        // FastAPI expects multiple query params with the same name for lists
        // axios will handle this automatically when we pass an array
        params.delete_existing_zones = delete_existing_zones
      }
      const { data } = await apiClient.post<GenerateZonesResponse>('/zones/generate', requestPayload, {
        params,
      })
      return data
    },
  })
}
