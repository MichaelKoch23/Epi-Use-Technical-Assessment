import type { ImportRowResult } from './api'
import { IMPORT_HEADER } from './schema'

export interface RowIssue {
  reason: string
  columns: Set<string>
}

function columnsInReason(reason: string): Set<string> {
  const columns = new Set<string>()
  const text = reason.toLowerCase()

  if (text.includes('manager') || text.includes('reporting cycle')) {
    columns.add('manager_employee_number')
  }

  for (const column of IMPORT_HEADER) {
    if (column === 'manager_employee_number') continue
    if (text.includes(column)) columns.add(column)
  }
  return columns
}

export function issuesByRowIndex(rows: ImportRowResult[]): Map<number, RowIssue> {
  const issues = new Map<number, RowIssue>()
  for (const row of rows) {
    if (row.outcome !== 'blocked' || !row.reason) continue
    issues.set(row.row_number - 2, {
      reason: row.reason,
      columns: columnsInReason(row.reason),
    })
  }
  return issues
}
