import { useMemo, useRef, useState } from 'react'
import { CheckCircle2Icon, DownloadIcon, UploadIcon } from 'lucide-react'
import { toast } from 'sonner'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState } from '@/features/analytics/components/EmptyState'
import { useAuth } from '@/features/auth/useAuth'
import { EmployeesPagination } from '@/features/employees/EmployeesPagination'
import { getErrorMessage } from '@/lib/apiError'
import { cn } from '@/lib/utils'
import { blockedRowsToCsv, downloadTextFile, importEmployees, type ImportResult } from './api'
import { ImportFileError, parseImportFile, rowsToCsv, rowsToFile } from './csv'
import { ImportTable } from './ImportTable'
import { IMPORT_HEADER, validateRows } from './schema'
import { issuesByRowIndex, type RowIssue } from './serverIssues'
import { formatElapsed, useCommitProgress, useUnloadWarning } from './useCommitProgress'

const DEFAULT_PAGE_SIZE = 50

export function ImportPage() {
  const { canEdit } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)

  const [filename, setFilename] = useState<string | null>(null)
  const [rows, setRows] = useState<string[][]>([])
  const [rowIssues, setRowIssues] = useState<Map<number, RowIssue>>(new Map())
  const [result, setResult] = useState<ImportResult | null>(null)
  const [isChecking, setIsChecking] = useState(false)
  const [isCommitting, setIsCommitting] = useState(false)
  const [committed, setCommitted] = useState<ImportResult | null>(null)
  const [confirmCommit, setConfirmCommit] = useState(false)
  const [confirmDiscard, setConfirmDiscard] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  const { elapsed, isLongRunning } = useCommitProgress(isCommitting)
  useUnloadWarning(isCommitting)

  // Recomputed on every keystroke, so a corrected cell clears as it is typed.
  const cellErrors = useMemo(() => validateRows(rows), [rows])
  const rowsNeedingWork = useMemo(() => {
    const flagged = new Set(rowIssues.keys())
    for (const key of cellErrors.keys()) flagged.add(Number(key.split(':')[0]))
    return flagged
  }, [rowIssues, cellErrors])

  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const startIndex = (currentPage - 1) * pageSize
  const pageRows = rows.slice(startIndex, startIndex + pageSize)

  const reset = () => {
    setFilename(null)
    setRows([])
    setRowIssues(new Map())
    setResult(null)
    setCommitted(null)
    setPage(1)
  }

  /** Send the table as it stands for a dry run - the server is the authority. */
  const check = async (nextRows: string[][], name: string) => {
    setIsChecking(true)
    try {
      const dryRun = await importEmployees(rowsToFile(nextRows, name), true)
      setResult(dryRun)
      setRowIssues(issuesByRowIndex(dryRun.rows))
      return dryRun
    } catch (error) {
      toast.error('Could not check this file', {
        description: getErrorMessage(error, 'Nothing was written. Try again in a moment.'),
      })
      return null
    } finally {
      setIsChecking(false)
    }
  }

  const loadFile = async (file: File) => {
    let parsed: string[][]
    try {
      parsed = parseImportFile(await file.text())
    } catch (error) {
      toast.error('Could not read that file', {
        description:
          error instanceof ImportFileError
            ? error.message
            : 'Upload a UTF-8 CSV with the expected column headings.',
      })
      return
    }

    setFilename(file.name)
    setRows(parsed)
    setCommitted(null)
    setPage(1)
    await check(parsed, file.name)
  }

  const onCellChange = (rowIndex: number, columnIndex: number, value: string) => {
    setRows((previous) => {
      const next = [...previous]
      const row = [...(next[rowIndex] ?? [])]
      row[columnIndex] = value
      next[rowIndex] = row
      return next
    })

    // The server's verdict described the old value, so retire it rather than
    // leave a stale reason under a row that has just been edited.
    setRowIssues((previous) => {
      if (!previous.has(rowIndex)) return previous
      const next = new Map(previous)
      next.delete(rowIndex)
      return next
    })
  }

  const onSubmitClick = async () => {
    if (!filename) return
    if (cellErrors.size > 0) {
      toast.error('Cannot submit yet', {
        description: `${cellErrors.size} cell${cellErrors.size === 1 ? '' : 's'} still need fixing.`,
      })
      return
    }
    const dryRun = await check(rows, filename)
    if (!dryRun) return
    if (dryRun.blocked > 0) {
      toast.error('Cannot submit yet', {
        description: `The server blocked ${dryRun.blocked} row(s). Fix the highlighted cells and try again.`,
      })
      return
    }
    setConfirmCommit(true)
  }

  const commit = async () => {
    if (!filename) return
    setConfirmCommit(false)
    setIsCommitting(true)
    try {
      const outcome = await importEmployees(rowsToFile(rows, filename), false)
      if (outcome.committed) {
        setCommitted(outcome)
        setRows([])
        setRowIssues(new Map())
        setResult(null)
        toast.success('Import complete', {
          description: `${outcome.created} employee(s) created and ${outcome.updated} updated from ${filename}.`,
        })
      } else {
        setResult(outcome)
        setRowIssues(issuesByRowIndex(outcome.rows))
        toast.error('The import was not written', {
          description: `${outcome.blocked} row(s) were blocked. Fix the highlighted cells and try again.`,
        })
      }
    } catch (error) {
      toast.error('Could not commit the import', {
        description: getErrorMessage(error, 'Nothing was written. Try again in a moment.'),
      })
    } finally {
      setIsCommitting(false)
    }
  }

  if (!canEdit) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-2xl font-bold">Import</h1>
        <p className="text-muted-foreground">
          Only an HR administrator can import employee data.
        </p>
      </div>
    )
  }

  const isBusy = isChecking || isCommitting

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold">Import</h1>
        <p className="text-muted-foreground">
          Upload a CSV, correct anything it flags in the table, and commit once every row passes.
          Nothing is written until you do.
        </p>
      </div>

      {committed && (
        <EmptyState
          icon={CheckCircle2Icon}
          title="Import complete"
          action={<Button onClick={reset}>Import another file</Button>}
        >
          {committed.created} employee(s) created and {committed.updated} updated. They are in the
          employee list and the org chart now.
        </EmptyState>
      )}

      {rows.length === 0 && !committed && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault()
            setDragActive(true)
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragActive(false)
            const dropped = event.dataTransfer.files[0]
            if (dropped) void loadFile(dropped)
          }}
          className={cn(
            'flex flex-col items-center gap-2 rounded-md border-2 border-dashed border-border p-10 text-center transition-colors',
            dragActive && 'border-primary bg-accent',
            isBusy && 'pointer-events-none opacity-60'
          )}
        >
          {isChecking ? (
            <Spinner className="size-6 text-muted-foreground" />
          ) : (
            <UploadIcon className="size-6 text-muted-foreground" aria-hidden="true" />
          )}
          <span className="text-sm font-medium text-foreground">
            {isChecking ? 'Checking the file...' : 'Drop a CSV file, or click to browse'}
          </span>
          <span className="text-xs text-muted-foreground">{IMPORT_HEADER.join(', ')}</span>
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(event) => {
              const selected = event.target.files?.[0]
              if (selected) void loadFile(selected)
              event.target.value = ''
            }}
          />
        </button>
      )}

      {isCommitting && (
        <div
          role="status"
          aria-live="polite"
          className="flex flex-wrap items-center gap-3 rounded-md border border-brand-mid/30 bg-brand-mid/5 px-4 py-3 text-sm"
        >
          <Spinner />
          <span className="font-medium text-foreground">
            Writing {rows.length} row(s) from {filename}.
          </span>
          <span className="text-muted-foreground">
            Employees are written one at a time, so a file this size usually takes a while. Leave
            this tab open - nothing is saved until every row has been written.
          </span>
          <span className="ml-auto tabular-nums text-muted-foreground">
            {formatElapsed(elapsed)} elapsed
            {isLongRunning && ' - still going'}
          </span>
        </div>
      )}

      {rows.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <span className="font-medium text-foreground">{filename}</span>
              <span className="text-muted-foreground">{rows.length} row(s)</span>
              {result && (
                <>
                  <span className="font-medium text-status-safe">{result.created} to create</span>
                  <span className="font-medium text-status-alert">{result.updated} to update</span>
                </>
              )}
              {rowsNeedingWork.size > 0 ? (
                <Badge className="bg-status-critical/10 text-status-critical">
                  {rowsNeedingWork.size} row(s) need fixing
                </Badge>
              ) : (
                <Badge className="bg-status-safe/10 text-status-safe">Every row passes</Badge>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {result && result.blocked > 0 && (
                <Button
                  variant="outline"
                  onClick={() =>
                    downloadTextFile('import-errors.csv', blockedRowsToCsv(result.rows), 'text/csv')
                  }
                >
                  <DownloadIcon /> Error report
                </Button>
              )}
              <Button
                variant="outline"
                disabled={isBusy}
                onClick={() => downloadTextFile('import-edited.csv', rowsToCsv(rows), 'text/csv')}
              >
                <DownloadIcon /> Download edits
              </Button>
              <Button
                variant="outline"
                disabled={isBusy || !filename}
                onClick={() => filename && void check(rows, filename)}
              >
                {isChecking && <Spinner />}
                {isChecking ? 'Checking...' : 'Check again'}
              </Button>
              <Button variant="outline" disabled={isBusy} onClick={() => setConfirmDiscard(true)}>
                Discard
              </Button>
              <Button disabled={isBusy} onClick={() => void onSubmitClick()}>
                {isCommitting && <Spinner />}
                {isCommitting ? 'Importing...' : 'Submit'}
              </Button>
            </div>
          </div>

          {rowsNeedingWork.size > 0 && (
            <p role="status" className="text-sm text-muted-foreground">
              Edit any cell to correct it. A cell outlined in red failed validation, and the reason
              sits under its row.
            </p>
          )}

          <EmployeesPagination
            page={currentPage}
            pageSize={pageSize}
            total={rows.length}
            onPageChange={setPage}
            onPageSizeChange={(next) => {
              setPageSize(next)
              setPage(1)
            }}
          />

          <ImportTable
            rows={pageRows}
            startIndex={startIndex}
            cellErrors={cellErrors}
            rowIssues={rowIssues}
            onCellChange={onCellChange}
          />
        </div>
      )}

      <ConfirmDialog
        open={confirmCommit}
        onOpenChange={setConfirmCommit}
        title="Commit this import?"
        description={
          result ? (
            <>
              <span className="font-medium text-foreground">{result.created}</span> employee(s) will
              be created and{' '}
              <span className="font-medium text-foreground">{result.updated}</span> updated from{' '}
              {filename}. Updates overwrite the existing records, and the whole import is written in
              one go - either every row lands or none does. Writing runs one employee at a time, so
              expect it to take a while and leave the tab open while it does.
            </>
          ) : null
        }
        confirmLabel="Commit import"
        pendingLabel="Importing..."
        cancelLabel="Not yet"
        variant="default"
        isPending={isCommitting}
        onConfirm={() => void commit()}
      />

      <ConfirmDialog
        open={confirmDiscard}
        onOpenChange={setConfirmDiscard}
        title="Discard this file?"
        description="The loaded rows and every edit you have made are dropped. Nothing has been written, so the employee list is unaffected."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={() => {
          setConfirmDiscard(false)
          reset()
        }}
      />
    </div>
  )
}
