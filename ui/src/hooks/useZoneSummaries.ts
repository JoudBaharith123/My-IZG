import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type ZoneSummary = {
  zone: string
  city?: string | null
  customers: number
}

export function useZoneSummaries(city?: string) {
  return useQuery({
    queryKey: ['zone-summaries', city ?? 'ALL'],
    queryFn: async (): Promise<ZoneSummary[]> => {
      const { data } = await apiClient.get<ZoneSummary[]>('/customers/zones', {
        params: city ? { city } : undefined,
      })
      return data ?? []
    },
    staleTime: 60_000,
    meta: { description: 'Available zones derived from customer dataset' },
  })
}

