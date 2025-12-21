import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../api/client'
import type { OptimizeRoutesResponse } from './useOptimizeRoutes'

export function useRoutesFromDatabase(zoneId?: string, city?: string) {
  return useQuery({
    queryKey: ['routes-from-database', zoneId ?? 'all', city ?? 'all'],
    queryFn: async (): Promise<OptimizeRoutesResponse | null> => {
      if (!zoneId) {
        return null
      }
      
      const params: Record<string, string> = {
        zone_id: zoneId,
      }
      if (city && city !== 'all') {
        params.city = city
      }
      
      try {
        const { data } = await apiClient.get<OptimizeRoutesResponse>('/routes/from-database', {
          params,
        })
        
        // Return null if no routes found
        if (!data || !data.plans || data.plans.length === 0) {
          return null
        }
        
        return data
      } catch (error) {
        console.error('Error fetching routes from database:', error)
        return null
      }
    },
    staleTime: 0, // Always refetch when invalidated (no stale time)
    enabled: Boolean(zoneId && zoneId !== 'all'), // Only fetch when zone is selected
    refetchOnWindowFocus: true, // Refetch when window regains focus
    meta: { description: 'Routes loaded from database' },
  })
}

