import { useRef, useState } from 'react'
import {
  AlertTriangleIcon,
  BanIcon,
  CheckCircle2Icon,
  DownloadIcon,
  UploadIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/useAuth'
import { getErrorMessage } from '@/lib/apiError'
import { cn } from '@/lib/utils'
import {
  blockedRowsToCsv,
  downloadTextFile,
  importEmployees,
  type ImportResult,
  type ImportRowResult,
} from './api'

const OUTCOME_META: Record<
  ImportRowResult['outcome'],
  { icon: typeof CheckCircle2Icon; label: string; className: string; badgeClassName: string }
> = {
  will_create: {
    icon: CheckCircle2Icon,
    label: 'Will import',
    className: 'text-status-safe',
    badgeClassName: 'bg-status-safe/10 text-status-safe',
  },
  will_update: {
    icon: AlertTriangleIcon,
    label: 'Will update',
    className: 'text-status-alert',
    badgeClassName: 'bg-status-alert/10 text-status-alert',
  },
  blocked: {
    icon: BanIcon,
    label: 'Blocked',
    className: 'text-status-critical',
    badgeClassName: 'bg-status-critical/10 text-status-critical',
  },
}

function rowDetail(row: ImportRowResult): string {
  if (row.outcome === 'blocked') return row.reason ?? 'Blocked'
  if (row.outcome === 'will_update') return 'Employee number already exists - will be updated'
  return 'New employee - will be created'
}

function ImportRow({ row }: { row: ImportRowResult }) {
  const meta = OUTCOME_META[row.outcome]
  const Icon = meta.icon
  return (
    <div className="flex items-start gap-3 border-b border-border py-3 last:border-none">
      <Icon className={cn('mt-0.5 size-4 shrink-0', meta.className)} aria-hidden="true" />
      <div className="flex-1">
        <div className="text-sm font-medium text-foreground">
          Row {row.row_number}
          {row.employee_number && <> · {row.employee_number}</>}
          {row.name && <> · {row.name}</>}
        </div>
        <div className="text-xs text-muted-foreground">{rowDetail(row)}</div>
      </div>
      <Badge className={meta.badgeClassName}>{meta.label}</Badge>
    </div>
  )
}

function ResultSummary({ result }: { result: ImportResult }) {
  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <span className="font-medium text-status-safe">{result.created} to create</span>
      <span className="font-medium text-status-alert">{result.updated} to update</span>
      <span className="font-medium text-status-critical">{result.blocked} blocked</span>
      {result.committed && <Badge className="bg-status-safe/10 text-status-safe">Committed</Badge>}
    </div>
  )
}

export function ImportPage() {
  const { canEdit } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  const validate = async (selected: File) => {
    setFile(selected)
    setResult(null)
    setIsBusy(true)
    try {
      const dryRun = await importEmployees(selected, true)
      setResult(dryRun)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to validate the file'))
    } finally {
      setIsBusy(false)
    }
  }

  const commit = async () => {
    if (!file) return
    setIsBusy(true)
    try {
      const committed = await importEmployees(file, false)
      setResult(committed)
      if (committed.committed) {
        toast.success(
          `Imported ${committed.created} new and ${committed.updated} updated employee(s)`
        )
      }
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to commit the import'))
    } finally {
      setIsBusy(false)
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

  const blockedRows = result?.rows.filter((r) => r.outcome === 'blocked') ?? []

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold">Import</h1>
        <p className="text-muted-foreground">
          Upload a CSV or XLSX file. It's always validated first - nothing is written until you
          review the results and commit.
        </p>
      </div>

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragActive(false)
          const dropped = e.dataTransfer.files[0]
          if (dropped) void validate(dropped)
        }}
        className={cn(
          'flex flex-col items-center gap-2 rounded-md border-2 border-dashed border-border p-10 text-center transition-colors',
          dragActive && 'border-primary bg-accent',
          isBusy && 'pointer-events-none opacity-60'
        )}
      >
        <UploadIcon className="size-6 text-muted-foreground" aria-hidden="true" />
        <span className="text-sm font-medium text-foreground">
          {file ? file.name : 'Drop a CSV or XLSX file, or click to browse'}
        </span>
        <span className="text-xs text-muted-foreground">
          employee_number, first_name, last_name, email, birth_date, position, salary, currency,
          manager_employee_number
        </span>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          onChange={(e) => {
            const selected = e.target.files?.[0]
            if (selected) void validate(selected)
            e.target.value = ''
          }}
        />
      </button>

      {isBusy && <p className="text-sm text-muted-foreground">Validating…</p>}

      {result && (
        <div className="flex flex-col gap-3">
          <ResultSummary result={result} />

          <div className="overflow-hidden rounded-md border border-border px-4">
            {result.rows.map((row) => (
              <ImportRow key={row.row_number} row={row} />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {blockedRows.length > 0 && (
              <Button
                variant="outline"
                onClick={() =>
                  downloadTextFile(
                    'import-errors.csv',
                    blockedRowsToCsv(result.rows),
                    'text/csv'
                  )
                }
              >
                <DownloadIcon /> Download error report
              </Button>
            )}
            <Button
              onClick={() => void commit()}
              disabled={isBusy || result.blocked > 0 || result.committed}
            >
              {result.committed ? 'Committed' : 'Commit import'}
            </Button>
          </div>
          {result.blocked > 0 && !result.committed && (
            <p className="text-xs text-muted-foreground">
              Fix the blocked rows and re-upload - a partial import isn't allowed, so nothing
              commits until every row passes.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
