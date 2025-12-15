import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import { apiClient } from '../api/client'

export type DeleteZonesResponse = {
  success: boolean
  deleted_count: number
  zone_ids: string[]
  message: string
}

export type DeleteZonesPayload = {
  zone_ids: string[]
}

export function useDeleteZones() {
  const queryClient = useQueryClient()

  return useMutation<DeleteZonesResponse, AxiosError, DeleteZonesPayload>({
    mutationFn: async (payload) => {
      // FastAPI expects multiple query params with the same name for lists
      const params = new URLSearchParams()
      payload.zone_ids.forEach((zoneId) => {
        params.append('zone_ids', zoneId)
      })
      const { data } = await apiClient.delete<DeleteZonesResponse>(`/zones/batch?${params.toString()}`)
      return data
    },
    onSuccess: () => {
      // Invalidate zone queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['zones-from-database'] })
      queryClient.invalidateQueries({ queryKey: ['database-zone-summaries'] })
      queryClient.invalidateQueries({ queryKey: ['unassigned-customers'] })
    },
  })
}

