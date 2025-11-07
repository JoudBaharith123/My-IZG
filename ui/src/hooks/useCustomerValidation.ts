import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export type CustomerValidationIssue = {
  count: number
  sample?: Array<Record<string, unknown>> | null
  duplicates?: Array<Record<string, unknown>> | null
}

export type CustomerValidationResponse = {
  totalRecords: number
  issues: {
    missingCoordinates: CustomerValidationIssue
    duplicateCustomers: CustomerValidationIssue
    financeClearance: CustomerValidationIssue
    [key: string]: CustomerValidationIssue
  }
}

export function useCustomerValidation() {
  return useQuery({
    queryKey: ['customer-validation'],
    queryFn: async (): Promise<CustomerValidationResponse> => {
      const { data } = await apiClient.get<CustomerValidationResponse>('/customers/validation')
      return data
    },
    staleTime: 60_000,
    meta: { description: 'Customer dataset validation summary' },
  })
}
