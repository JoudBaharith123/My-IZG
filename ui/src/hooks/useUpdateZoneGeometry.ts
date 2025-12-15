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
      const { data } = await apiClient.put<UpdateZoneGeometryResponse>(
        `/zones/${payload.zone_id}/geometry`,
        payload.coordinates
      )
      return data
    },
    onSuccess: () => {
      // Invalidate zone queries to refresh the map
      queryClient.invalidateQueries({ queryKey: ['zones-from-database'] })
      queryClient.invalidateQueries({ queryKey: ['database-zone-summaries'] })
    },
  })
}

