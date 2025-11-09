import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type ColumnValuesResponse = {
  column: string
  values: string[]
  total_unique: number
  returned: number
}

export function useColumnValues(columnName: string | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['column-values', columnName],
    queryFn: async (): Promise<ColumnValuesResponse> => {
      if (!columnName) {
        throw new Error('Column name is required')
      }
      const { data } = await apiClient.get<ColumnValuesResponse>(`/customers/filter-values/${columnName}`)
      return data
    },
    enabled: enabled && !!columnName,
    staleTime: 60_000,
    meta: { description: `Values for column ${columnName}` },
  })
}
