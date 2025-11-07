import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import { apiClient } from '../api/client'

export type RouteStop = {
  customer_id: string
  sequence: number
  arrival_min: number
  distance_from_prev_km: number | null
}

export type RoutePlan = {
  route_id: string
  day: string
  total_distance_km: number
  total_duration_min: number
  customer_count: number
  constraint_violations: Record<string, number>
  stops: RouteStop[]
}

export type OptimizeRoutesResponse = {
  zone_id: string
  metadata: Record<string, unknown>
  plans: RoutePlan[]
}

export type RouteConstraintsPayload = {
  max_customers_per_route?: number
  min_customers_per_route?: number
  max_route_duration_minutes?: number
  max_distance_per_route_km?: number
}

export type OptimizeRoutesPayload = {
  city: string
  zone_id: string
  customer_ids?: string[]
  constraints?: RouteConstraintsPayload
  persist?: boolean
}

export function useOptimizeRoutes() {
  return useMutation<OptimizeRoutesResponse, AxiosError, OptimizeRoutesPayload>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<OptimizeRoutesResponse>('/routes/optimize', payload)
      return data
    },
  })
}

