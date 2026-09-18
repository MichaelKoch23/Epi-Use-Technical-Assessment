import type { components } from '@/lib/api-types'
import { authedFetch } from '@/lib/apiClient'
import { triggerDownload } from '@/lib/download'

export type ImportResult = components['schemas']['ImportResult']
export type ImportRowResult = components['schemas']['ImportRowResult']

export async function importEmployees(file: File, dryRun: boolean): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await authedFetch(`/api/v1/imports/employees?dry_run=${dryRun}`, {
    method: 'POST',
    body: formData,
  })

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw body ?? new Error('Import failed')
  return body as ImportResult
}

function csvCell(value: string | null | undefined): string {
  const text = value ?? ''
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function blockedRowsToCsv(rows: ImportRowResult[]): string {
  const header = 'row_number,employee_number,name,reason'
  const lines = rows
    .filter((row) => row.outcome === 'blocked')
    .map((row) =>
      [
        String(row.row_number),
        csvCell(row.employee_number),
        csvCell(row.name),
        csvCell(row.reason),
      ].join(',')
    )
  return [header, ...lines].join('\n')
}

export function downloadTextFile(filename: string, content: string, mimeType: string): void {
  triggerDownload(filename, new Blob([content], { type: mimeType }))
}
