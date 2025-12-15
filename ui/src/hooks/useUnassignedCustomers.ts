import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../api/client'

export type UnassignedCustomersResponse = {
  customer_ids: string[]
  count: number
  city: string
}

export function useUnassignedCustomers(city?: string) {
  return useQuery<UnassignedCustomersResponse>({
    queryKey: ['unassigned-customers', city ?? 'all'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (city && city !== 'all') {
        params.city = city
      }
      const { data } = await apiClient.get<UnassignedCustomersResponse>('/zones/unassigned-customers', {
        params,
      })
      return data ?? { customer_ids: [], count: 0, city: city || 'all' }
    },
    staleTime: 30_000, // 30 seconds
    enabled: Boolean(city && city !== 'all'), // Only fetch when a specific city is selected
    meta: { description: 'Unassigned customers from all zones' },
  })
}

