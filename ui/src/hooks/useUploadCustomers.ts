import { useMutation, useQueryClient } from '@tanstack/react-query'

import { apiClient } from '../api/client'
import type { CustomerStatsResponse } from './useCustomerStats'

export function useUploadCustomers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (file: File): Promise<CustomerStatsResponse> => {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await apiClient.post<CustomerStatsResponse>('/customers/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer-stats'] })
      queryClient.invalidateQueries({ queryKey: ['customer-validation'] })
      queryClient.invalidateQueries({ queryKey: ['customer-locations'] })
      queryClient.invalidateQueries({ queryKey: ['customer-cities'] })
      queryClient.invalidateQueries({ queryKey: ['zone-summaries'] })
    },
  })
}
