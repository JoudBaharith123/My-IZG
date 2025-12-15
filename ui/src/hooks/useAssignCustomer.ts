import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import { apiClient } from '../api/client'

export type AssignCustomerResponse = {
  success: boolean
  customer_id: string
  zone_id: string
  message: string
}

export type AssignCustomerPayload = {
  zone_id: string
  customer_id: string
}

export function useAssignCustomer() {
  const queryClient = useQueryClient()

  return useMutation<AssignCustomerResponse, AxiosError, AssignCustomerPayload>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<AssignCustomerResponse>(
        `/zones/${payload.zone_id}/customers/${payload.customer_id}/assign`
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

