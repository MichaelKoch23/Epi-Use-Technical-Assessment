import type { components } from '@/lib/api-types'
import { getAccessToken } from '@/lib/auth'
import { triggerDownload } from '@/lib/download'

export type ImportResult = components['schemas']['ImportResult']
export type ImportRowResult = components['schemas']['ImportRowResult']

/** `POST /imports/employees` takes `multipart/form-data`, which the
 * generated `openapi-fetch` client handles awkwardly - a plain `fetch`
 * with the bearer token attached by hand is the same fallback
 * `apiClient.ts` itself already uses for `/auth/refresh`. */
export async function importEmployees(file: File, dryRun: boolean): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)

  const token = getAccessToken()
  const response = await fetch(`/api/v1/imports/employees?dry_run=${dryRun}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
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

/** A client-built CSV of just the blocked rows - the same report a dry
 * run's "download error report" button offers, so a user can fix their
 * source file without re-reading the whole dry-run table row by row. */
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
