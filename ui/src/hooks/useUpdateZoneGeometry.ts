import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import { apiClient } from '../api/client'

export type UpdateZoneGeometryPayload = {
  zone_id: string
  coordinates: Array<[number, number]>
}

export type UpdateZoneGeometryResponse = {
  success: boolean
  zone_id: string
  message: string
}

export function useUpdateZoneGeometry() {
  const queryClient = useQueryClient()

  return useMutation<UpdateZoneGeometryResponse, AxiosError, UpdateZoneGeometryPayload>({
    mutationFn: async (payload) => {
      // Backend expects coordinates as the request body (list of [lat, lon] pairs)
      const { data } = await apiClient.put<UpdateZoneGeometryResponse>(
        `/zones/${payload.zone_id}/geometry`,
        payload.coordinates  // Send coordinates array directly as body
      )
      return data
    },
    onSuccess: (data, variables) => {
      console.log(`🔄 Invalidating queries after successful update of zone ${variables.zone_id}`, data)
      // Invalidate zone queries to refresh the map - use prefix matching to catch all variations
      queryClient.invalidateQueries({ 
        queryKey: ['zones-from-database'],
        exact: false  // Match all queries that start with this key
      })
      queryClient.invalidateQueries({ 
        queryKey: ['database-zone-summaries'],
        exact: false  // Match all queries that start with this key
      })
      console.log(`✅ Queries invalidated for zone ${variables.zone_id}`)
    },
    onError: (error, variables) => {
      console.error(`❌ Error updating zone ${variables.zone_id}:`, error.message)
      // Still invalidate queries even on error, in case partial update succeeded
      queryClient.invalidateQueries({ 
        queryKey: ['zones-from-database'],
        exact: false
      })
      queryClient.invalidateQueries({ 
        queryKey: ['database-zone-summaries'],
        exact: false
      })
    },
  })
}

