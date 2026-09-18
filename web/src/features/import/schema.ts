/**
 * The shape of an import file, mirrored from the API's own field rules so the
 * table can flag a bad cell before anything is sent. The server re-checks every
 * one of these and stays the authority - this only saves a round trip.
 */
export type ImportColumnType = 'text' | 'email' | 'date' | 'number' | 'currency'

export interface ImportColumn {
  name: string
  label: string
  type: ImportColumnType
  optional?: boolean
  maxLength?: number
}

export const IMPORT_COLUMNS: ImportColumn[] = [
  { name: 'employee_number', label: 'Employee no.', type: 'text', maxLength: 64 },
  { name: 'first_name', label: 'First name', type: 'text', maxLength: 100 },
  { name: 'last_name', label: 'Last name', type: 'text', maxLength: 100 },
  { name: 'email', label: 'Email', type: 'email', maxLength: 320 },
  { name: 'birth_date', label: 'Birth date', type: 'date' },
  { name: 'position', label: 'Position', type: 'text', maxLength: 120 },
  { name: 'salary', label: 'Salary', type: 'number' },
  { name: 'currency', label: 'Currency', type: 'currency' },
  { name: 'manager_employee_number', label: 'Manager no.', type: 'text', optional: true, maxLength: 64 },
]

export const IMPORT_HEADER = IMPORT_COLUMNS.map((column) => column.name)

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const CURRENCY_PATTERN = /^[A-Za-z]{3}$/
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const MAX_SALARY = 9999999999.99

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export function validateCell(value: string, column: ImportColumn): string | null {
  const text = value.trim()
  if (!text) return column.optional ? null : 'Required'
  if (column.maxLength && text.length > column.maxLength) {
    return `Must be ${column.maxLength} characters or fewer`
  }

  switch (column.type) {
    case 'email':
      return EMAIL_PATTERN.test(text) ? null : 'Must be a valid email address'

    case 'currency':
      return CURRENCY_PATTERN.test(text) ? null : 'Must be a 3-letter code, such as ZAR'

    case 'date': {
      if (!ISO_DATE_PATTERN.test(text)) return 'Must be a date as YYYY-MM-DD'
      const parsed = new Date(`${text}T00:00:00Z`)
      if (Number.isNaN(parsed.getTime())) return 'Not a real date'
      if (text > todayIso()) return 'Must not be in the future'
      if (text <= '1900-01-01') return 'Must be after 1900-01-01'
      return null
    }

    case 'number': {
      if (!/^-?\d+(\.\d+)?$/.test(text)) return 'Must be a number'
      const amount = Number(text)
      if (amount < 0) return 'Must not be negative'
      if (amount > MAX_SALARY) return 'Above the maximum salary'
      const decimals = text.split('.')[1]?.length ?? 0
      if (decimals > 2) return 'At most 2 decimal places'
      return null
    }

    default:
      return null
  }
}

/** Every cell error in the file, keyed `${rowIndex}:${columnName}`. */
export function validateRows(rows: string[][]): Map<string, string> {
  const errors = new Map<string, string>()
  rows.forEach((row, rowIndex) => {
    IMPORT_COLUMNS.forEach((column, columnIndex) => {
      const error = validateCell(row[columnIndex] ?? '', column)
      if (error) errors.set(`${rowIndex}:${column.name}`, error)
    })
  })
  return errors
}
