import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type ColumnValuesResponse = {
  column: string
  values: string[]
  total_unique: number
  returned: number
}

export type UseColumnValuesOptions = {
  city?: string
  enabled?: boolean
}

export function useColumnValues(
  columnName: string | null, 
  options: UseColumnValuesOptions = {}
) {
  const { city, enabled = true } = options
  
  return useQuery({
    queryKey: ['column-values', columnName, city || 'all'],
    queryFn: async (): Promise<ColumnValuesResponse> => {
      if (!columnName) {
        throw new Error('Column name is required')
      }
      const params: Record<string, string> = {}
      if (city && city !== 'all') {
        params.city = city
      }
      const { data } = await apiClient.get<ColumnValuesResponse>(
        `/customers/filter-values/${columnName}`,
        { params }
      )
      return data
    },
    enabled: enabled && !!columnName,
    staleTime: 60_000,
    meta: { description: `Values for column ${columnName}` },
  })
}
