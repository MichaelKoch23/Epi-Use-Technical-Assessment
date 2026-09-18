import { IMPORT_COLUMNS, IMPORT_HEADER } from './schema'

function parseCsvText(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let quoted = false

  for (let i = 0; i < text.length; i++) {
    const char = text[i]

    if (quoted) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"'
          i++
        } else {
          quoted = false
        }
      } else {
        field += char
      }
      continue
    }

    if (char === '"') {
      quoted = true
    } else if (char === ',') {
      row.push(field)
      field = ''
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[i + 1] === '\n') i++
      row.push(field)
      rows.push(row)
      row = []
      field = ''
    } else {
      field += char
    }
  }

  if (field !== '' || row.length > 0) {
    row.push(field)
    rows.push(row)
  }
  return rows
}

export class ImportFileError extends Error {}

export function parseImportFile(text: string): string[][] {
  const withoutBom = text.replace(/^\uFEFF/, '')
  const rows = parseCsvText(withoutBom).filter((row) =>
    row.some((cell) => cell.trim() !== '')
  )
  if (rows.length === 0) throw new ImportFileError('That file is empty.')

  const header = rows[0]!.map((cell) => cell.trim().toLowerCase())
  const missing = IMPORT_HEADER.filter((column) => !header.includes(column))
  if (missing.length > 0) {
    throw new ImportFileError(
      `The header row is missing: ${missing.join(', ')}. Expected ${IMPORT_HEADER.join(', ')}.`
    )
  }

  const indexes = IMPORT_HEADER.map((column) => header.indexOf(column))
  return rows
    .slice(1)
    .map((row) => indexes.map((index) => (row[index] ?? '').trim()))
}

function csvCell(value: string): string {
  return /[",\n\r]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value
}

export function rowsToCsv(rows: string[][]): string {
  const lines = rows.map((row) =>
    IMPORT_COLUMNS.map((_, index) => csvCell(row[index] ?? '')).join(',')
  )
  return [IMPORT_HEADER.join(','), ...lines].join('\n')
}

export function rowsToFile(rows: string[][], filename: string): File {
  return new File([rowsToCsv(rows)], filename, { type: 'text/csv' })
}
