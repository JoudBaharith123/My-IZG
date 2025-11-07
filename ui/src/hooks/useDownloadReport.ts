import { useMutation } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { apiClient } from '../api/client'
import type { ReportExport } from './useReportExports'

function triggerFileDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function useDownloadReport(onDownload?: (item: ReportExport) => void) {
  return useMutation<void, AxiosError, ReportExport>({
    mutationFn: async (exportItem) => {
      const response = await apiClient.get(exportItem.downloadPath, {
        responseType: 'blob',
      })
      const data = response.data as Blob
      const blob = data instanceof Blob ? data : new Blob([data], { type: response.headers['content-type'] || 'application/octet-stream' })
      triggerFileDownload(blob, exportItem.fileName)
      onDownload?.(exportItem)
    },
  })
}
