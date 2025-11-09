import { useState, useEffect } from 'react'
import { X, Check, AlertCircle } from 'lucide-react'

export type FieldDefinition = {
  field: string
  description: string
  required: boolean
}

export type ColumnMappingModalProps = {
  isOpen: boolean
  onClose: () => void
  onConfirm: (mappings: Record<string, string>, filterColumns: string[]) => void
  fileName: string
  detectedColumns: string[]
  suggestedMappings: Record<string, string>
  requiredFields: FieldDefinition[]
  initialFilterColumns?: string[]
}

export function ColumnMappingModal({
  isOpen,
  onClose,
  onConfirm,
  fileName,
  detectedColumns,
  suggestedMappings,
  requiredFields,
  initialFilterColumns = [],
}: ColumnMappingModalProps) {
  const [mappings, setMappings] = useState<Record<string, string>>(suggestedMappings)
  const [filterColumns, setFilterColumns] = useState<Set<string>>(new Set(initialFilterColumns))

  useEffect(() => {
    setMappings(suggestedMappings)
  }, [suggestedMappings])

  useEffect(() => {
    setFilterColumns(new Set(initialFilterColumns))
  }, [initialFilterColumns])

  const handleMappingChange = (field: string, csvColumn: string) => {
    setMappings((prev) => ({
      ...prev,
      [field]: csvColumn,
    }))
  }

  const handleFilterToggle = (csvColumn: string) => {
    setFilterColumns((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(csvColumn)) {
        newSet.delete(csvColumn)
      } else {
        newSet.add(csvColumn)
      }
      return newSet
    })
  }

  const isMapped = (field: string) => {
    return mappings[field] && mappings[field] !== ''
  }

  const requiredFieldsMapped = requiredFields.filter((f) => f.required).every((f) => isMapped(f.field))

  const handleConfirm = () => {
    if (!requiredFieldsMapped) {
      return
    }
    // Filter out empty mappings
    const finalMappings = Object.fromEntries(Object.entries(mappings).filter(([_, v]) => v && v !== ''))
    onConfirm(finalMappings, Array.from(filterColumns))
    onClose()
  }

  if (!isOpen) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-auto rounded-2xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-background-dark">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 dark:border-gray-700 dark:bg-background-dark">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Map Columns</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              File: <span className="font-semibold">{fileName}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Instructions */}
        <div className="border-b border-gray-200 bg-blue-50 px-6 py-3 text-sm text-blue-800 dark:border-gray-700 dark:bg-blue-500/10 dark:text-blue-200">
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <div>
              <p className="font-semibold">Map your CSV columns to system fields</p>
              <p className="text-xs">
                Fields marked with <span className="text-red-600 dark:text-red-400">*</span> are required. You can also select which columns to use as filters.
              </p>
            </div>
          </div>
        </div>

        {/* Mapping Table */}
        <div className="p-6">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-200">System Field</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-200">Description</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-200">CSV Column</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-700 dark:text-gray-200">Use as Filter</th>
                  <th className="px-4 py-3 text-center font-semibold text-gray-700 dark:text-gray-200">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-background-dark">
                {requiredFields.map((fieldDef) => {
                  const mapped = isMapped(fieldDef.field)
                  const selectedColumn = mappings[fieldDef.field]

                  return (
                    <tr key={fieldDef.field}>
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                        {fieldDef.field}
                        {fieldDef.required && <span className="ml-1 text-red-600 dark:text-red-400">*</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{fieldDef.description}</td>
                      <td className="px-4 py-3">
                        <select
                          value={selectedColumn || ''}
                          onChange={(e) => handleMappingChange(fieldDef.field, e.target.value)}
                          className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 transition focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-600 dark:bg-background-dark dark:text-white"
                        >
                          <option value="">-- Not mapped --</option>
                          {detectedColumns.map((col) => (
                            <option key={col} value={col}>
                              {col}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={selectedColumn ? filterColumns.has(selectedColumn) : false}
                          onChange={() => selectedColumn && handleFilterToggle(selectedColumn)}
                          disabled={!selectedColumn}
                          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        {mapped ? (
                          <Check className="inline h-5 w-5 text-green-600 dark:text-green-400" />
                        ) : fieldDef.required ? (
                          <AlertCircle className="inline h-5 w-5 text-red-600 dark:text-red-400" />
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Filter Summary */}
          {filterColumns.size > 0 && (
            <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200">
              <p className="font-semibold">Selected Filter Columns ({filterColumns.size}):</p>
              <p className="mt-1 text-xs">{Array.from(filterColumns).join(', ')}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 flex items-center justify-between border-t border-gray-200 bg-gray-50 px-6 py-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="text-sm text-gray-600 dark:text-gray-300">
            {requiredFieldsMapped ? (
              <span className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <Check className="h-4 w-4" />
                All required fields mapped
              </span>
            ) : (
              <span className="flex items-center gap-2 text-red-600 dark:text-red-400">
                <AlertCircle className="h-4 w-4" />
                Please map all required fields
              </span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={!requiredFieldsMapped}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Confirm & Upload
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
