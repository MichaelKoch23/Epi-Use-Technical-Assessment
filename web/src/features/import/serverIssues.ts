import type { ImportRowResult } from './api'
import { IMPORT_HEADER } from './schema'

export interface RowIssue {
  reason: string
  columns: Set<string>
}

/**
 * The API reports a blocked row as one sentence, so the columns to highlight
 * are read back out of it. Anything unrecognised still shows as a row-level
 * message - the row is flagged either way, only the cell outline is lost.
 */
function columnsInReason(reason: string): Set<string> {
  const columns = new Set<string>()
  const text = reason.toLowerCase()

  // "manager 'EMP-9' not found" and cycle reports are about the manager column,
  // whose own name never appears in the sentence.
  if (text.includes('manager') || text.includes('reporting cycle')) {
    columns.add('manager_employee_number')
  }

  for (const column of IMPORT_HEADER) {
    if (column === 'manager_employee_number') continue
    if (text.includes(column)) columns.add(column)
  }
  return columns
}

/** Blocked rows from a dry run, keyed by their index in the table. */
export function issuesByRowIndex(rows: ImportRowResult[]): Map<number, RowIssue> {
  const issues = new Map<number, RowIssue>()
  for (const row of rows) {
    if (row.outcome !== 'blocked' || !row.reason) continue
    // row_number counts the header as row 1.
    issues.set(row.row_number - 2, {
      reason: row.reason,
      columns: columnsInReason(row.reason),
    })
  }
  return issues
}
