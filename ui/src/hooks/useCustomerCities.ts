import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../api/client'

export type CustomerCity = {
  name: string
  customers: number
}

export function useCustomerCities() {
  return useQuery({
    queryKey: ['customer-cities'],
    queryFn: async (): Promise<CustomerCity[]> => {
      const { data } = await apiClient.get<CustomerCity[]>('/customers/cities')
      return data ?? []
    },
    staleTime: 5 * 60 * 1000,
    meta: { description: 'Available customer cities derived from dataset.' },
  })
}
