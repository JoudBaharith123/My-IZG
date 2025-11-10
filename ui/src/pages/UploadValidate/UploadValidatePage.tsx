import { useMemo, useRef, useState } from 'react'
import type { ReactNode, ChangeEvent } from 'react'
import { AlertCircle, Download, Edit3, Info, RefreshCw, UploadCloud } from 'lucide-react'

import { useCustomerStats } from '../../hooks/useCustomerStats'
import { useCustomerValidation } from '../../hooks/useCustomerValidation'
import type { CustomerValidationResponse } from '../../hooks/useCustomerValidation'
import { useUploadCustomers } from '../../hooks/useUploadCustomers'
import { ColumnMappingModal } from '../../components/ColumnMappingModal'
import type { FieldDefinition } from '../../components/ColumnMappingModal'
import { apiClient } from '../../api/client'

type IssueCard = {
  key: keyof CustomerValidationResponse['issues']
  title: string
  tone: 'error' | 'warning' | 'info'
  description: string
  count: number
}

type ValidationRow = {
  issueKey: IssueCard['key']
  issue: string
  customerId: string
  customerName: string
  city?: string | null
  zone?: string | null
  latitude?: number | null
  longitude?: number | null
}

const ISSUE_METADATA: Record<IssueCard['key'], { title: string; tone: IssueCard['tone']; description: string }> = {
  missingCoordinates: {
    title: 'Missing Coordinates',
    tone: 'error',
    description: 'Records without latitude/longitude cannot be processed until coordinates are provided.',
  },
  duplicateCustomers: {
    title: 'Duplicate Customer IDs',
    tone: 'warning',
    description: 'Duplicate IDs must be resolved before publishing new zones.',
  },
  financeClearance: {
    title: 'Finance Clearance Needed',
    tone: 'info',
    description: 'Customers with outstanding balances require finance clearance before reassignment.',
  },
}

type PreviewResponse = {
  fileName: string
  detectedColumns: string[]
  suggestedMappings: Record<string, string>
  requiredFields: FieldDefinition[]
}

export function UploadValidatePage() {
  const { data: statsData } = useCustomerStats()
  const { data: validationData, isLoading: validationLoading } = useCustomerValidation()
  const uploadMutation = useUploadCustomers()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [showMappingModal, setShowMappingModal] = useState(false)
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isEditMode, setIsEditMode] = useState(false)
  const [isLoadingFileInfo, setIsLoadingFileInfo] = useState(false)

  const stats = useMemo(
    () => [
      { label: 'Total Customers', value: statsData?.totalCustomers.toLocaleString() ?? '—' },
      {
        label: '% Unassigned',
        value: statsData ? `${statsData.unassignedPercentage.toFixed(1)}%` : '—',
      },
      { label: 'Zones Detected', value: statsData?.zonesDetected?.toString() ?? '—' },
    ],
    [statsData],
  )

  const topZones = useMemo(
    () =>
      (statsData?.topZones ?? []).map((zone) => ({
        label: zone.code,
        percentage: `${Math.round(zone.ratio * 100)}%`,
      })),
    [statsData],
  )

  const totalRecords = validationData?.totalRecords ?? statsData?.totalCustomers ?? 0

  const validationCards: IssueCard[] = useMemo(() => {
    if (!validationData?.issues) {
      return []
    }
    return (Object.keys(ISSUE_METADATA) as Array<IssueCard['key']>).map((key) => ({
      key,
      title: ISSUE_METADATA[key].title,
      tone: ISSUE_METADATA[key].tone,
      description: ISSUE_METADATA[key].description,
      count: validationData.issues[key]?.count ?? 0,
    }))
  }, [validationData])

  const issueRows = useMemo<ValidationRow[]>(() => {
    if (!validationData?.issues) {
      return []
    }
    const rows: ValidationRow[] = []
    const pushRecord = (record: Record<string, unknown>, issueKey: IssueCard['key'], label: string) => {
      const customerId = toStringValue(record.customer_id)
      const customerName = toStringValue(record.customer_name)
      rows.push({
        issueKey,
        issue: label,
        customerId,
        customerName,
        city: toOptionalString(record.city),
        zone: toOptionalString(record.zone),
        latitude: toOptionalNumber(record.latitude),
        longitude: toOptionalNumber(record.longitude),
      })
    }

    validationData.issues.missingCoordinates?.sample?.forEach((record) => {
      pushRecord(record, 'missingCoordinates', 'Missing coordinates')
    })

    validationData.issues.duplicateCustomers?.duplicates?.forEach((entry: any) => {
      const duplicateLabel = `Duplicate ID ${toStringValue(entry.customer_id)}`
      entry.records?.forEach((record: Record<string, unknown>) => {
        pushRecord(record, 'duplicateCustomers', duplicateLabel)
      })
    })

    validationData.issues.financeClearance?.sample?.forEach((record) => {
      pushRecord(record, 'financeClearance', 'Finance clearance required')
    })

    return rows.slice(0, 500)
  }, [validationData])

  const [searchTerm, setSearchTerm] = useState('')
  const filteredIssueRows = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase()
    if (!normalized) {
      return issueRows
    }
    return issueRows.filter((row) =>
      [row.customerId, row.customerName, row.city ?? '', row.zone ?? '', row.issue]
        .join(' ')
        .toLowerCase()
        .includes(normalized),
    )
  }, [issueRows, searchTerm])

  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    setUploadMessage(null)
    setUploadError(null)
    setSelectedFile(file)

    // Call preview endpoint to get column mappings
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await apiClient.post<PreviewResponse>('/customers/upload/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setPreviewData(response.data)
      setShowMappingModal(true)
      event.target.value = ''
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to preview file'
      setUploadError(message)
      event.target.value = ''
    }
  }

  const handleEditMappings = async () => {
    setUploadMessage(null)
    setUploadError(null)
    setIsLoadingFileInfo(true)

    try {
      const response = await apiClient.get<PreviewResponse & { currentFilterColumns: string[] }>('/customers/current-file-info')
      setPreviewData(response.data)
      setIsEditMode(true)
      setShowMappingModal(true)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load file info'
      setUploadError(message)
    } finally {
      setIsLoadingFileInfo(false)
    }
  }

  const handleConfirmMapping = (mappings: Record<string, string>, filterColumns: string[]) => {
    if (isEditMode) {
      // Re-process existing file with new mappings
      handleReprocessMappings(mappings, filterColumns)
    } else if (selectedFile) {
      // Upload new file with mappings
      uploadMutation.mutate(
        {
          file: selectedFile,
          mappings,
          filterColumns,
        },
        {
          onSuccess: (data) => {
            setUploadMessage(`Upload complete: ${data.lastUpload.fileName}`)
            setSelectedFile(null)
            setPreviewData(null)
          },
          onError: (error) => {
            const message = error instanceof Error ? error.message : 'Unable to upload dataset.'
            setUploadError(message)
            setSelectedFile(null)
            setPreviewData(null)
          },
        },
      )
    }
  }

  const handleReprocessMappings = async (mappings: Record<string, string>, filterColumns: string[]) => {
    try {
      const formData = new FormData()
      formData.append('mappings', JSON.stringify(mappings))
      formData.append('filter_columns', JSON.stringify(filterColumns))

      const response = await apiClient.put('/customers/reprocess-mappings', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setUploadMessage('Mappings updated successfully')
      setPreviewData(null)
      setIsEditMode(false)
      setShowMappingModal(false)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update mappings'
      setUploadError(message)
    }
  }

  return (
    <div className="space-y-8">
      {/* Column Mapping Modal */}
      {previewData && (
        <ColumnMappingModal
          isOpen={showMappingModal}
          onClose={() => {
            setShowMappingModal(false)
            setPreviewData(null)
            setSelectedFile(null)
            setIsEditMode(false)
          }}
          onConfirm={handleConfirmMapping}
          fileName={previewData.fileName}
          detectedColumns={previewData.detectedColumns}
          suggestedMappings={previewData.suggestedMappings}
          requiredFields={previewData.requiredFields}
          initialFilterColumns={(previewData as PreviewResponse & { currentFilterColumns?: string[] }).currentFilterColumns}
        />
      )}

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-3xl font-bold leading-tight text-gray-900 dark:text-white">Customer Data Upload &amp; Validation</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Upload customer data, validate for errors, and review the results before processing.
            </p>
          </div>
          <button className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-100 dark:hover:bg-gray-800">
            <RefreshCw className="h-4 w-4" /> Refresh Status
          </button>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-background-dark">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-gray-500 dark:text-gray-400">Last Upload</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{formatDateTime(statsData?.lastUpload?.modifiedAt)}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                File: {statsData?.lastUpload?.fileName ?? '—'} ({formatBytes(statsData?.lastUpload?.sizeBytes)})
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-2 rounded-full bg-orange-100 px-3 py-1 text-sm font-medium text-orange-600 dark:bg-orange-500/20 dark:text-orange-300">
                <AlertCircle className="h-4 w-4" /> Latest validation run: Warning
              </div>
              <button
                type="button"
                onClick={handleEditMappings}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                disabled={isLoadingFileInfo || !statsData?.lastUpload?.fileName}
              >
                <Edit3 className="h-4 w-4" /> {isLoadingFileInfo ? 'Loading…' : 'Edit Mappings'}
              </button>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
                disabled={uploadMutation.isPending}
              >
                <UploadCloud className="h-4 w-4" /> {uploadMutation.isPending ? 'Uploading…' : 'Upload New Dataset'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx"
                hidden
                onChange={handleFileUpload}
              />
            </div>
          </div>
          {(uploadMessage || uploadError) && (
            <p className={`mt-3 text-xs ${uploadError ? 'text-red-600 dark:text-red-300' : 'text-gray-600 dark:text-gray-300'}`}>
              {uploadError ? uploadError : uploadMessage}
            </p>
          )}
        </div>

        <div className="flex gap-3 rounded-xl border border-primary/20 bg-primary/10 p-4 text-sm text-primary dark:border-primary/40 dark:bg-primary/20 dark:text-primary-50">
          <Info className="h-5 w-5" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Finance Clearance Requirement</h3>
            <p className="text-xs text-gray-700 dark:text-gray-200">
              Customers with outstanding balances require finance clearance before reassignment. Review the validation results below and coordinate with Finance before publishing new zones.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-gray-800 dark:bg-background-dark/70">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{stat.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
          </div>
        ))}
        {topZones.length ? (
          <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-gray-800 dark:bg-background-dark/70">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Top Zones</p>
            <ul className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-300">
              {topZones.map((zone) => (
                <li key={zone.label} className="flex items-center justify-between">
                  <span>{zone.label}</span>
                  <span className="font-semibold text-primary dark:text-primary-100">{zone.percentage}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Validation Results</h3>
        <div className="mt-4 space-y-3">
          {validationLoading ? (
            <PlaceholderCard message="Analyzing customer dataset…" />
          ) : (
            validationCards.map((section) => {
              const cardRows = issueRows.filter((row) => row.issueKey === section.key)
              return (
                <details
                  key={section.key}
                  className="overflow-hidden rounded-lg border border-gray-200 bg-gray-50 text-sm shadow-sm transition dark:border-gray-700 dark:bg-gray-800/60"
                >
                  <summary className="flex cursor-pointer items-center justify-between px-4 py-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge tone={section.tone}>{section.title}</Badge>
                        <span className="text-gray-500 dark:text-gray-400">{formatIssueCount(section.count, totalRecords)}</span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{section.description}</p>
                    </div>
                    <span className="text-xs font-semibold text-primary">View details</span>
                  </summary>
                  <div className="border-t border-gray-200 bg-white px-4 py-4 dark:border-gray-700 dark:bg-background-dark/80">
                    {cardRows.length ? <IssueSampleTable rows={cardRows} /> : <p className="text-xs text-gray-500 dark:text-gray-400">No sample records for this issue.</p>}
                    <button className="mt-3 inline-flex items-center gap-2 rounded-full border border-primary px-3 py-1.5 text-xs font-semibold text-primary transition hover:bg-primary/10 dark:border-primary-100 dark:text-primary-100 dark:hover:bg-primary/30">
                      <Download className="h-4 w-4" /> Export issue list
                    </button>
                  </div>
                </details>
              )
            })
          )}
        </div>
      </div>

      <section className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
        <div className="flex flex-col gap-3 border-b border-gray-200 px-4 py-3 text-sm dark:border-gray-700 md:flex-row md:items-center md:justify-between">
          <div className="relative w-full md:max-w-md">
            <SearchInput
              placeholder="Search validation samples..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Showing {filteredIssueRows.length} of {issueRows.length} issue samples
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
            <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-300">
              <tr>
                <th className="px-4 py-3 text-left">CusId</th>
                <th className="px-4 py-3 text-left">CusName</th>
                <th className="px-4 py-3 text-left">City</th>
                <th className="px-4 py-3 text-left">Zone</th>
                <th className="px-4 py-3 text-left">Latitude</th>
                <th className="px-4 py-3 text-left">Longitude</th>
                <th className="px-4 py-3 text-left">Issue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredIssueRows.map((row, index) => (
                <tr key={`${row.issueKey}-${index}`} className="bg-white dark:bg-background-dark/70">
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{row.customerId || '—'}</td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-200">{row.customerName || '—'}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.city || '—'}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.zone || '—'}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{formatCoordinate(row.latitude)}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{formatCoordinate(row.longitude)}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{row.issue}</td>
                </tr>
              ))}
              {!filteredIssueRows.length && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-300">
                    No issue records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function Badge({ tone, children }: { tone: 'error' | 'warning' | 'info'; children: ReactNode }) {
  const toneStyles: Record<'error' | 'warning' | 'info', string> = {
    error: 'bg-red-100 text-red-600 dark:bg-red-500/20 dark:text-red-300',
    warning: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-500/20 dark:text-yellow-300',
    info: 'bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-300',
  }
  return <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${toneStyles[tone]}`}>{children}</span>
}

function PlaceholderCard({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-center text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300">
      {message}
    </div>
  )
}

function SearchInput({ placeholder, value, onChange }: { placeholder: string; value: string; onChange: (event: ChangeEvent<HTMLInputElement>) => void }) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-4 w-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z" />
        </svg>
      </span>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className="w-full rounded-full border border-gray-200 bg-white py-2 pl-10 pr-4 text-sm text-gray-700 shadow-sm transition focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:border-gray-700 dark:bg-background-dark/80 dark:text-gray-200"
      />
    </div>
  )
}

function IssueSampleTable({ rows }: { rows: ValidationRow[] }) {
  const sample = rows.slice(0, 6)
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-xs dark:divide-gray-700">
        <thead className="bg-gray-100 text-[11px] font-semibold uppercase text-gray-500 dark:bg-gray-900 dark:text-gray-300">
          <tr>
            <th className="px-3 py-2 text-left">CusId</th>
            <th className="px-3 py-2 text-left">Name</th>
            <th className="px-3 py-2 text-left">City</th>
            <th className="px-3 py-2 text-left">Zone</th>
            <th className="px-3 py-2 text-left">Issue</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {sample.map((row, index) => (
            <tr key={`${row.issueKey}-sample-${index}`} className="bg-white dark:bg-background-dark/70">
              <td className="px-3 py-2 text-gray-700 dark:text-gray-200">{row.customerId || '—'}</td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-200">{row.customerName || '—'}</td>
              <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{row.city || '—'}</td>
              <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{row.zone || '—'}</td>
              <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{row.issue}</td>
            </tr>
          ))}
          {!sample.length && (
            <tr>
              <td colSpan={5} className="px-3 py-2 text-center text-gray-500 dark:text-gray-300">
                No sample records available.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function formatIssueCount(count: number, total: number): string {
  if (!total) {
    return count.toString()
  }
  const percentage = ((count / total) * 100).toFixed(1)
  return `${count.toLocaleString()} (${percentage}%)`
}

function formatCoordinate(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—'
  }
  return value.toFixed(5)
}

function formatBytes(size?: number | null): string {
  if (!size || size <= 0) {
    return '—'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = size
  let idx = 0
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024
    idx += 1
  }
  const precision = idx === 0 ? 0 : 1
  return `${value.toFixed(precision)} ${units[idx]}`
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function toStringValue(value: unknown): string {
  if (typeof value === 'string') {
    return value.trim()
  }
  if (typeof value === 'number') {
    return value.toString()
  }
  return ''
}

function toOptionalString(value: unknown): string | null {
  const normalized = toStringValue(value)
  return normalized || null
}

function toOptionalNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (!Number.isNaN(parsed)) {
      return parsed
    }
  }
  return null
}

