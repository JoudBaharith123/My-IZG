import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type ReportExport = {
  id: string
  runId: string
  runType: string
  fileName: string
  fileType: string
  sizeBytes: number
  createdAt: string | null
  city?: string | null
  zone?: string | null
  method?: string | null
  author?: string | null
  runLabel?: string | null
  tags?: string[] | null
  notes?: string | null
  description?: string | null
  downloadPath: string
}

export function useReportExports(params?: {
  runType?: string
  city?: string
  zone?: string
  fileType?: string
  search?: string
  limit?: number
}) {
  return useQuery({
    queryKey: ['report-exports', params ?? {}],
    queryFn: async (): Promise<ReportExport[]> => {
      const { data } = await apiClient.get<ReportExport[]>('/reports/exports', {
        params,
      })
      return data ?? []
    },
    staleTime: 60_000,
    meta: { description: 'Available export files from recent runs' },
  })
}
