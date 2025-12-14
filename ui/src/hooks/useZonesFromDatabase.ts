import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../api/client'
import type { GenerateZonesResponse } from './useGenerateZones'

export function useZonesFromDatabase(city?: string, method?: string) {
  return useQuery({
    queryKey: ['zones-from-database', city ?? 'all', method ?? 'all'],
    queryFn: async (): Promise<GenerateZonesResponse | null> => {
      const params: Record<string, string> = {}
      if (city && city !== 'all') {
        params.city = city
      }
      if (method) {
        params.method = method
      }
      
      try {
        const { data } = await apiClient.get<GenerateZonesResponse>('/zones/from-database', {
          params,
        })
        
        console.log('📦 Fetched zones from database:', {
          city,
          method,
          polygonCount: data?.metadata?.map_overlays?.polygons?.length ?? 0,
          hasData: !!data,
        })
        
        // Return null if no zones found (empty polygons)
        if (!data || data.metadata?.map_overlays?.polygons?.length === 0) {
          return null
        }
        
        return data
      } catch (error) {
        console.error('❌ Error fetching zones from database:', error)
        return null
      }
    },
    staleTime: 30_000, // 30 seconds
    enabled: Boolean(city && city !== 'all'), // Only fetch when city is selected
    meta: { description: 'Zones loaded from database' },
  })
}

