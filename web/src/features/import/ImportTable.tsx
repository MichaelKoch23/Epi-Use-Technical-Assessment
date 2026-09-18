import { Fragment } from 'react'
import { AlertTriangleIcon, CheckCircle2Icon } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { IMPORT_COLUMNS } from './schema'
import type { RowIssue } from './serverIssues'

export function ImportTable({
  rows,
  startIndex,
  cellErrors,
  rowIssues,
  onCellChange,
}: {
  /** The page being shown, not the whole file. */
  rows: string[][]
  startIndex: number
  /** Client-side errors, keyed `${rowIndex}:${columnName}`. */
  cellErrors: Map<string, string>
  /** Server verdicts from the last check, keyed by row index. */
  rowIssues: Map<number, RowIssue>
  onCellChange: (rowIndex: number, columnIndex: number, value: string) => void
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-20">Row</TableHead>
            {IMPORT_COLUMNS.map((column) => (
              <TableHead key={column.name} className="min-w-40">
                {column.label}
                {column.optional && (
                  <span className="ml-1 text-xs font-normal text-muted-foreground">optional</span>
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, index) => {
            const rowIndex = startIndex + index
            const issue = rowIssues.get(rowIndex)
            const clientErrors = IMPORT_COLUMNS.map((column) =>
              cellErrors.get(`${rowIndex}:${column.name}`)
            )
            const hasError = Boolean(issue) || clientErrors.some(Boolean)

            return (
              <Fragment key={rowIndex}>
              <TableRow className={cn(hasError && 'bg-status-critical/5')}>
                <TableCell className="align-top text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    {hasError ? (
                      <AlertTriangleIcon
                        className="size-3.5 text-status-critical"
                        aria-label="Has errors"
                      />
                    ) : (
                      <CheckCircle2Icon className="size-3.5 text-status-safe" aria-label="Valid" />
                    )}
                    {/* The file's own line number, so it matches the error report. */}
                    {rowIndex + 2}
                  </span>
                </TableCell>

                {IMPORT_COLUMNS.map((column, columnIndex) => {
                  const error = clientErrors[columnIndex] ?? (issue?.columns.has(column.name)
                    ? issue.reason
                    : undefined)
                  return (
                    <TableCell key={column.name} className="align-top">
                      <Input
                        value={row[columnIndex] ?? ''}
                        aria-label={`${column.label}, row ${rowIndex + 2}`}
                        aria-invalid={Boolean(error)}
                        title={error}
                        onChange={(event) =>
                          onCellChange(rowIndex, columnIndex, event.target.value)
                        }
                        className="h-8"
                      />
                      {clientErrors[columnIndex] && (
                        <span className="mt-1 block text-xs font-medium text-status-critical">
                          {clientErrors[columnIndex]}
                        </span>
                      )}
                    </TableCell>
                  )
                })}
              </TableRow>

              {issue && (
                <TableRow className="bg-status-critical/5 hover:bg-status-critical/5">
                  <TableCell />
                  <TableCell
                    colSpan={IMPORT_COLUMNS.length}
                    className="pt-0 text-xs font-medium text-status-critical"
                  >
                    {issue.reason}
                  </TableCell>
                </TableRow>
              )}
              </Fragment>
            )
          })}

          {rows.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={IMPORT_COLUMNS.length + 1}
                className="py-8 text-center text-sm text-muted-foreground"
              >
                No rows on this page.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
