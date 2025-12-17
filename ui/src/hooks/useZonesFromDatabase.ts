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
        
        // Return null if no zones found (empty polygons)
        if (!data || data.metadata?.map_overlays?.polygons?.length === 0) {
          return null
        }
        
        return data
      } catch (error) {
        console.error('Error fetching zones from database:', error)
        return null
      }
    },
    staleTime: 0, // Always refetch when invalidated (no stale time)
    enabled: Boolean(city && city !== 'all'), // Only fetch when city is selected
    refetchOnWindowFocus: true, // Refetch when window regains focus
    meta: { description: 'Zones loaded from database' },
  })
}

