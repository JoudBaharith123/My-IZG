import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type FilterMetadata = {
  filter_columns: string[]
  updated_at: string | null
}

export function useFilterMetadata() {
  return useQuery({
    queryKey: ['filter-metadata'],
    queryFn: async (): Promise<FilterMetadata> => {
      const { data } = await apiClient.get<FilterMetadata>('/customers/filters')
      return data
    },
    staleTime: 60_000,
    meta: { description: 'Available filter columns' },
  })
}
