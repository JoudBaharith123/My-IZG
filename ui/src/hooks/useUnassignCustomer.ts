import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import { apiClient } from '../api/client'

export type UnassignCustomerResponse = {
  success: boolean
  customer_id: string
  zone_id: string
  message: string
}

export type UnassignCustomerPayload = {
  zone_id: string
  customer_id: string
}

export function useUnassignCustomer() {
  const queryClient = useQueryClient()

  return useMutation<UnassignCustomerResponse, AxiosError, UnassignCustomerPayload>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<UnassignCustomerResponse>(
        `/zones/${payload.zone_id}/customers/${payload.customer_id}/unassign`
      )
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

