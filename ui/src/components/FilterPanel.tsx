import { useState } from 'react'
import { Filter, X } from 'lucide-react'
import { useFilterMetadata } from '../hooks/useFilterMetadata'
import { useColumnValues } from '../hooks/useColumnValues'

export type FilterPanelProps = {
  onFiltersChange: (filters: Record<string, string>) => void
  activeFilters: Record<string, string>
  customerCount?: number
  totalCustomers?: number
}

export function FilterPanel({ onFiltersChange, activeFilters, customerCount, totalCustomers }: FilterPanelProps) {
  const { data: filterMetadata } = useFilterMetadata()
  const filterColumns = filterMetadata?.filter_columns || []

  if (filterColumns.length === 0) {
    return null
  }

  const handleFilterChange = (column: string, value: string) => {
    const newFilters = { ...activeFilters }
    if (value === '' || value === 'all') {
      delete newFilters[column]
    } else {
      newFilters[column] = value
    }
    onFiltersChange(newFilters)
  }

  const handleClearAll = () => {
    onFiltersChange({})
  }

  const hasActiveFilters = Object.keys(activeFilters).length > 0

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Filters</h3>
        </div>
        {hasActiveFilters && (
          <button
            onClick={handleClearAll}
            className="flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-gray-600 transition hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <X className="h-4 w-4" />
            Clear all
          </button>
        )}
      </div>

      {/* Customer Count */}
      {customerCount !== undefined && totalCustomers !== undefined && (
        <div className="mb-4 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-sm dark:border-primary/40 dark:bg-primary/20">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-primary dark:text-primary-100">
              {hasActiveFilters ? 'Filtered:' : 'Total:'}
            </span>
            <span className="text-lg font-bold text-primary dark:text-primary-100">
              {customerCount.toLocaleString()}
              {hasActiveFilters && totalCustomers > 0 && (
                <span className="ml-2 text-xs font-normal opacity-70">
                  of {totalCustomers.toLocaleString()}
                </span>
              )}
            </span>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {filterColumns.map((column) => (
          <FilterDropdown
            key={column}
            column={column}
            value={activeFilters[column] || ''}
            onChange={(value) => handleFilterChange(column, value)}
          />
        ))}
      </div>

      {hasActiveFilters && (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200">
          <p className="font-semibold">Active Filters:</p>
          <ul className="mt-1 space-y-1 text-xs">
            {Object.entries(activeFilters).map(([column, value]) => (
              <li key={column}>
                {column}: <span className="font-semibold">{value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

type FilterDropdownProps = {
  column: string
  value: string
  onChange: (value: string) => void
}

function FilterDropdown({ column, value, onChange }: FilterDropdownProps) {
  const { data, isLoading } = useColumnValues(column)
  const values = data?.values || []

  const displayName = column.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())

  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">{displayName}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={isLoading}
        className="w-full rounded-lg border border-gray-300 bg-background-light px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 disabled:opacity-50"
      >
        <option value="">All {displayName}</option>
        {values.map((val) => (
          <option key={val} value={val}>
            {val}
          </option>
        ))}
      </select>
      {data && data.total_unique > data.returned && (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Showing {data.returned} of {data.total_unique} options
        </p>
      )}
    </div>
  )
}
