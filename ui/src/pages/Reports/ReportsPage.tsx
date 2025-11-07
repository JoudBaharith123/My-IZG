import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { CalendarDays, Clock, Database, Download, Search, Share2 } from 'lucide-react'

import { useReportExports } from '../../hooks/useReportExports'
import type { ReportExport } from '../../hooks/useReportExports'
import { useReportRuns } from '../../hooks/useReportRuns'
import type { ReportRun } from '../../hooks/useReportRuns'
import { useDownloadReport } from '../../hooks/useDownloadReport'

const ALL_FILTER = 'All'

export function ReportsPage() {
  const { data: exportsData = [], isLoading: exportsLoading } = useReportExports()
  const { data: runsData = [], isLoading: runsLoading } = useReportRuns()

  const fileFilters = useMemo(() => {
    const filters = new Set<string>([ALL_FILTER])
    exportsData.forEach((item) => {
      filters.add(item.fileType || 'Other')
    })
    return Array.from(filters)
  }, [exportsData])

  const [activeFilter, setActiveFilter] = useState<string>(ALL_FILTER)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    if (!fileFilters.length) {
      setActiveFilter(ALL_FILTER)
      return
    }
    if (!fileFilters.includes(activeFilter)) {
      setActiveFilter(fileFilters[0])
    }
  }, [fileFilters, activeFilter])

  const normalizedSearch = searchTerm.trim().toLowerCase()
  const filteredExports = useMemo(() => {
    return exportsData.filter((item) => {
      const matchesFilter = activeFilter === ALL_FILTER || item.fileType === activeFilter
      if (!matchesFilter) {
        return false
      }
      if (!normalizedSearch) {
        return true
      }
      const haystack = [
        item.fileName,
        item.description ?? '',
        item.city ?? '',
        item.zone ?? '',
        item.method ?? '',
        item.author ?? '',
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(normalizedSearch)
    })
  }, [activeFilter, exportsData, normalizedSearch])

  const downloadReport = useDownloadReport((item) => {
    console.info('report-download', { id: item.id, fileName: item.fileName, runId: item.runId })
  })

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-3xl font-bold leading-tight text-gray-900 dark:text-white">Reports &amp; Exports</h2>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Access the latest zone and route exports, share reports with stakeholders, and review run history.
          </p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
          <Database className="h-4 w-4" /> Open export directory
        </button>
      </header>

      <div className="flex flex-col gap-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {fileFilters.map((filter) => (
              <FilterPill key={filter} active={activeFilter === filter} onClick={() => setActiveFilter(filter)}>
                {filter}
              </FilterPill>
            ))}
          </div>
          <div className="flex w-full items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 lg:max-w-xs">
            <Search className="h-4 w-4" />
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search exports"
              className="flex-1 bg-transparent outline-none"
            />
          </div>
        </div>

        {exportsLoading ? (
          <PlaceholderCard message="Loading exports…" />
        ) : filteredExports.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredExports.map((item) => (
              <ReportCard
                key={item.id}
                exportItem={item}
                isDownloading={downloadReport.isPending && downloadReport.variables?.id === item.id}
                onDownload={() => downloadReport.mutate(item)}
              />
            ))}
          </div>
        ) : (
          <PlaceholderCard message="No exports found for the selected filter." />
        )}
      </div>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Run History</h3>
            <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
              <Download className="h-4 w-4" /> Export log
            </button>
          </div>

          {runsLoading ? (
            <PlaceholderCard message="Loading run history…" />
          ) : runsData.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
                <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-300">
                  <tr>
                    <th className="px-4 py-3 text-left">Run ID</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-left">City</th>
                    <th className="px-4 py-3 text-left">Zone</th>
                    <th className="px-4 py-3 text-left">Author</th>
                    <th className="px-4 py-3 text-left">Zones</th>
                    <th className="px-4 py-3 text-left">Routes</th>
                    <th className="px-4 py-3 text-left">Created</th>
                    <th className="px-4 py-3 text-left">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {runsData.map((run) => (
                    <tr key={run.id} className="bg-white dark:bg-background-dark/80">
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{run.id}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{formatRunType(run)}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{run.city ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{run.zone ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{run.author ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{run.zoneCount}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{run.routeCount}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{formatDate(run.createdAt)}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={run.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <PlaceholderCard message="No runs recorded yet." />
          )}
        </div>

        <aside className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-background-dark/60">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Schedule &amp; Sharing</h3>
          <div className="space-y-3 text-sm text-gray-600 dark:text-gray-300">
            <InfoCard icon={<CalendarDays className="h-5 w-5 text-primary" />} title="Scheduled Exports" subtitle="Weekly customer routes every Saturday at 18:00" />
            <InfoCard icon={<Clock className="h-5 w-5 text-primary" />} title="Retention Policy" subtitle="Exports retained for 90 days. Archive older runs to external storage." />
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm dark:border-gray-700 dark:bg-gray-800/60">
            <p className="text-gray-600 dark:text-gray-300">Share reports with stakeholders:</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <ShareButton label="Email Finance" />
              <ShareButton label="Notify Ops" />
              <ShareButton label="Copy Link" />
            </div>
          </div>
        </aside>
      </section>
    </div>
  )
}

function ReportCard({ exportItem, onDownload, isDownloading }: { exportItem: ReportExport; onDownload: () => void; isDownloading: boolean }) {
  const generatedAt = formatDate(exportItem.createdAt)
  const fileType = exportItem.fileType || 'FILE'
  const supplemental = [exportItem.city, exportItem.zone, exportItem.method].filter(Boolean).join(' • ')
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-background-dark/70">
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-primary dark:bg-primary/20 dark:text-primary-100">{fileType}</span>
        <span>{formatBytes(exportItem.sizeBytes)}</span>
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{exportItem.fileName}</h4>
        <p className="text-xs text-gray-500 dark:text-gray-400">{exportItem.description ?? 'Run export file'}</p>
        {supplemental && <p className="text-xs text-gray-400 dark:text-gray-500">{supplemental}</p>}
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">Generated: {generatedAt}</p>
      <div className="mt-auto flex items-center gap-2">
        <button
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={onDownload}
          disabled={isDownloading}
        >
          <Download className="h-4 w-4" /> {isDownloading ? 'Downloading…' : 'Download'}
        </button>
        <button className="inline-flex items-center justify-center rounded-lg border border-gray-200 p-2 text-xs font-semibold text-gray-600 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800">
          <Share2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

function FilterPill({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  const base = 'rounded-full border px-3 py-1 text-xs font-semibold transition'
  const classes = active
    ? base + ' border-primary bg-primary text-white shadow'
    : base + ' border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
  return (
    <button type="button" onClick={onClick} className={classes}>
      {children}
    </button>
  )
}

function StatusBadge({ status }: { status: string }) {
  const base = 'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold'
  const normalized = status?.toLowerCase()
  if (normalized === 'optimal' || normalized === 'complete') {
    return <span className={base + ' bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-200'}>{status}</span>
  }
  return <span className={base + ' bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-200'}>{status || 'Pending'}</span>
}

function ShareButton({ label }: { label: string }) {
  return (
    <button className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
      <Share2 className="h-4 w-4" /> {label}
    </button>
  )
}

function InfoCard({ icon, title, subtitle }: { icon: ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-gray-50 p-4 dark:bg-gray-800/60">
      {icon}
      <div>
        <p className="font-semibold text-gray-900 dark:text-white">{title}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
      </div>
    </div>
  )
}

function PlaceholderCard({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-300">
      {message}
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return '—'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  const precision = unitIndex === 0 ? 0 : 1
  return `${value.toFixed(precision)} ${units[unitIndex]}`
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function formatRunType(run: ReportRun): string {
  if (run.runType === 'zones') {
    return run.method ? `Zones • ${run.method}` : 'Zones'
  }
  if (run.runType === 'routes') {
    return run.zone ? `Routes • ${run.zone}` : 'Routes'
  }
  return run.runType || 'Run'
}
