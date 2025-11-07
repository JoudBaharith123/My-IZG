import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type CustomerLastUpload = {
  fileName: string
  sizeBytes?: number | null
  modifiedAt?: string | null
}

export type CustomerStatsResponse = {
  totalCustomers: number
  unassignedPercentage: number
  zonesDetected: number
  topZones: Array<{ code: string; ratio: number; customers: number }>
  lastUpload: CustomerLastUpload
}

const fallback: CustomerStatsResponse = {
  totalCustomers: 26831,
  unassignedPercentage: 16.2,
  zonesDetected: 45,
  topZones: [
    { code: 'JED-N1', ratio: 0.85, customers: 1204 },
    { code: 'RYD-C2', ratio: 0.7, customers: 980 },
    { code: 'JED-S5', ratio: 0.6, customers: 840 },
  ],
  lastUpload: {
    fileName: '--',
    sizeBytes: null,
    modifiedAt: null,
  },
}

export function useCustomerStats() {
  return useQuery({
    queryKey: ['customer-stats'],
    queryFn: async (): Promise<CustomerStatsResponse> => {
      try {
        const { data } = await apiClient.get<CustomerStatsResponse>('/customers/stats')
        return data ?? fallback
      } catch (error) {
        return fallback
      }
    },
    staleTime: 60_000,
    retry: 1,
    meta: { description: 'Customer dataset statistics' },
  })
}
