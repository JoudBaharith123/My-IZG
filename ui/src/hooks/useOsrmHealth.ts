import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

type OsrmHealthResponse = {
  service: string
  healthy: boolean
}

export function useOsrmHealth() {
  return useQuery({
    queryKey: ['osrm-health'],
    queryFn: async (): Promise<boolean> => {
      const { data } = await apiClient.get<OsrmHealthResponse>('/health/osrm')
      return Boolean(data?.healthy)
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: 1,
    meta: { description: 'OSRM health status' },
  })
}
