import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import { apiClient } from '../api/client'

export type RemoveCustomerPayload = {
  zone_id: string
  route_id: string
  customer_id: string
}

export type TransferCustomerPayload = {
  zone_id: string
  from_route_id: string
  to_route_id: string
  customer_id: string
}

export type UpdateRouteResponse = {
  success: boolean
  message: string
}

export function useRemoveCustomerFromRoute() {
  const queryClient = useQueryClient()
  
  return useMutation<UpdateRouteResponse, AxiosError, RemoveCustomerPayload>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<UpdateRouteResponse>('/routes/remove-customer', payload)
      return data
    },
    onSuccess: () => {
      // Invalidate relevant queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      queryClient.invalidateQueries({ queryKey: ['zone-summaries'] })
    },
  })
}

export function useTransferCustomer() {
  const queryClient = useQueryClient()
  
  return useMutation<UpdateRouteResponse, AxiosError, TransferCustomerPayload>({
    mutationFn: async (payload) => {
      const { data } = await apiClient.post<UpdateRouteResponse>('/routes/transfer-customer', payload)
      return data
    },
    onSuccess: () => {
      // Invalidate relevant queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      queryClient.invalidateQueries({ queryKey: ['zone-summaries'] })
    },
  })
}


