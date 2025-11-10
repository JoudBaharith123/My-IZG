import { useInfiniteQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { apiClient } from '../api/client'

export type CustomerLocation = {
  customer_id: string
  customer_name?: string | null
  city?: string | null
  zone?: string | null
  latitude: number
  longitude: number
}

export type CustomerLocationsResult = {
  items: CustomerLocation[]
  page: number
  pageSize: number
  total: number
  hasNextPage: boolean
}

type UseCustomerLocationsArgs = {
  city?: string | null
  zone?: string | null
  filters?: Record<string, string> | null
  pageSize?: number
  enabled?: boolean
}

type ApiResponse = {
  items: CustomerLocation[]
  page: number
  page_size: number
  total: number
  has_next_page: boolean
}

export function useCustomerLocations({ city, zone, filters, pageSize = 1500, enabled = true }: UseCustomerLocationsArgs) {
  const normalizedCity = city?.trim()
  const normalizedZone = zone?.trim()
  const query = useInfiniteQuery({
    queryKey: ['customer-locations', normalizedCity ?? 'ALL', normalizedZone ?? 'ALL', filters ?? {}, pageSize],
    queryFn: async ({ pageParam = 1 }): Promise<CustomerLocationsResult> => {
      const params: Record<string, string> = {
        page: String(pageParam),
        page_size: String(pageSize),
      }
      if (normalizedCity) {
        params.city = normalizedCity
      }
      if (normalizedZone) {
        params.zone = normalizedZone
      }
      // Add additional filters
      if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
          if (value) {
            // Normalize filter keys: AgentName -> agent_name, AgentId -> agent_id
            const normalizedKey = key
              .replace(/([A-Z])/g, '_$1')
              .toLowerCase()
              .replace(/^_/, '')
            params[normalizedKey] = value
          }
        })
      }
      const { data } = await apiClient.get<ApiResponse>('/customers/locations', {
        params,
      })
      if (!data) {
        return { items: [], page: pageParam, pageSize, total: 0, hasNextPage: false }
      }
      return {
        items: data.items ?? [],
        page: data.page ?? pageParam,
        pageSize: data.page_size ?? pageSize,
        total: data.total ?? 0,
        hasNextPage: Boolean(data.has_next_page),
      }
    },
    getNextPageParam: (lastPage) => (lastPage.hasNextPage ? lastPage.page + 1 : undefined),
    enabled: enabled && Boolean(normalizedCity || normalizedZone),
    staleTime: 300_000,
    meta: { description: 'Customer coordinate data for map overlays' },
  })

  const aggregated = useMemo(() => {
    const pages = query.data?.pages ?? []
    const items = pages.flatMap((page) => page.items)
    const total = pages.length ? pages[pages.length - 1].total : 0
    return {
      items,
      total,
      hasNextPage: query.hasNextPage ?? false,
      pageSize,
    }
  }, [pageSize, query.data?.pages, query.hasNextPage])

  return {
    ...aggregated,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    fetchNextPage: query.fetchNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    refetch: query.refetch,
  }
}
