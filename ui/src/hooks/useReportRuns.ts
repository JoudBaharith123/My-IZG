import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type ReportRun = {
  id: string
  runType: string
  createdAt: string | null
  city?: string | null
  zone?: string | null
  method?: string | null
  author?: string | null
  runLabel?: string | null
  tags?: string[] | null
  notes?: string | null
  zoneCount: number
  routeCount: number
  status: string
}

export function useReportRuns(params?: {
  runType?: string
  city?: string
  zone?: string
  search?: string
  limit?: number
}) {
  return useQuery({
    queryKey: ['report-runs', params ?? {}],
    queryFn: async (): Promise<ReportRun[]> => {
      const { data } = await apiClient.get<ReportRun[]>('/reports/runs', {
        params,
      })
      return data ?? []
    },
    staleTime: 60_000,
    meta: { description: 'Report run history manifest' },
  })
}
