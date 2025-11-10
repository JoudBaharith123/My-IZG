import { useMutation, useQueryClient } from '@tanstack/react-query'

import { apiClient } from '../api/client'
import type { CustomerStatsResponse } from './useCustomerStats'

export interface UploadCustomersParams {
  file: File
  mappings?: Record<string, string>
  filterColumns?: string[]
}

export function useUploadCustomers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: UploadCustomersParams): Promise<CustomerStatsResponse> => {
      const formData = new FormData()
      formData.append('file', params.file)

      if (params.mappings) {
        formData.append('mappings', JSON.stringify(params.mappings))
      }

      if (params.filterColumns) {
        formData.append('filter_columns', JSON.stringify(params.filterColumns))
      }

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
