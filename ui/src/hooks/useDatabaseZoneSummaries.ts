import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../api/client'
import type { ZoneSummary } from './useZoneSummaries'

export function useDatabaseZoneSummaries(city?: string) {
  return useQuery({
    queryKey: ['database-zone-summaries', city ?? 'ALL'],
    queryFn: async (): Promise<ZoneSummary[]> => {
      const params: Record<string, string> = {}
      if (city) {
        params.city = city
      }
      
      try {
        const { data } = await apiClient.get<ZoneSummary[]>('/zones/summaries', {
          params,
        })
        
        console.log('📦 Fetched zone summaries from database:', {
          city: city || 'all',
          zoneCount: data?.length ?? 0,
        })
        
        return data ?? []
      } catch (error) {
        console.error('❌ Error fetching zone summaries from database:', error)
        return []
      }
    },
    enabled: Boolean(city), // Only fetch when city is provided
    staleTime: 60_000, // 1 minute
    meta: { description: 'Zone summaries loaded from database' },
  })
}

