import { describe, expect, it } from 'vitest'
import { ImportFileError, parseImportFile, rowsToCsv } from '../csv'
import { IMPORT_HEADER, validateRows } from '../schema'
import { issuesByRowIndex } from '../serverIssues'
import type { ImportRowResult } from '../api'

const HEADER = IMPORT_HEADER.join(',')

function row(overrides: Partial<Record<string, string>> = {}): string {
  const values: Record<string, string> = {
    employee_number: 'EMP-09001',
    first_name: 'Thandi',
    last_name: 'Mokoena',
    email: 'thandi@example.com',
    birth_date: '1984-03-11',
    position: 'Platform Engineer',
    salary: '612000.00',
    currency: 'ZAR',
    manager_employee_number: '',
    ...overrides,
  }
  return IMPORT_HEADER.map((column) => values[column] ?? '').join(',')
}

describe('parseImportFile', () => {
  it('reads columns by heading, so a reordered file still imports', () => {
    const text = ['last_name,employee_number,first_name,email,birth_date,position,salary,currency,manager_employee_number',
      'Mokoena,EMP-1,Thandi,t@example.com,1984-03-11,Engineer,10.00,ZAR,'].join('\n')

    expect(parseImportFile(text)[0]).toEqual([
      'EMP-1', 'Thandi', 'Mokoena', 't@example.com', '1984-03-11', 'Engineer', '10.00', 'ZAR', '',
    ])
  })

  it('keeps a quoted comma inside one cell', () => {
    const text = `${HEADER}\nEMP-1,Johan,"Van der Merwe, Jr",j@example.com,1984-03-11,"Engineer, Senior",10.00,ZAR,`
    const [parsed] = parseImportFile(text)
    expect(parsed?.[2]).toBe('Van der Merwe, Jr')
    expect(parsed?.[5]).toBe('Engineer, Senior')
  })

  it('names the columns a file is missing rather than failing silently', () => {
    expect(() => parseImportFile('employee_number,first_name\nEMP-1,Thandi')).toThrow(
      ImportFileError
    )
    expect(() => parseImportFile('employee_number,first_name\nEMP-1,Thandi')).toThrow(/email/)
  })

  it('rejects an empty file', () => {
    expect(() => parseImportFile('')).toThrow(ImportFileError)
  })

  it('survives a byte order mark and blank lines', () => {
    const text = `\uFEFF${HEADER}\n\n${row()}\n\n`
    expect(parseImportFile(text)).toHaveLength(1)
  })

  it('round-trips an edited table back to CSV', () => {
    const text = `${HEADER}\n${row({ position: 'Engineer, Senior' })}`
    const parsed = parseImportFile(text)
    expect(parseImportFile(rowsToCsv(parsed))).toEqual(parsed)
  })

})

describe('validateRows', () => {
  it('passes a clean row and leaves the optional manager empty', () => {
    expect(validateRows(parseImportFile(`${HEADER}\n${row()}`)).size).toBe(0)
  })

  it('flags the offending cell, naming the column', () => {
    const rows = parseImportFile(
      [
        HEADER,
        row({ email: 'not-an-email' }),
        row({ birth_date: '14/07/1992' }),
        row({ salary: '-5' }),
        row({ salary: '100.999' }),
        row({ currency: 'RANDS' }),
        row({ position: '' }),
      ].join('\n')
    )
    const errors = validateRows(rows)

    expect(errors.get('0:email')).toMatch(/valid email/i)
    expect(errors.get('1:birth_date')).toMatch(/YYYY-MM-DD/)
    expect(errors.get('2:salary')).toMatch(/negative/i)
    expect(errors.get('3:salary')).toMatch(/decimal/i)
    expect(errors.get('4:currency')).toMatch(/3-letter/i)
    expect(errors.get('5:position')).toBe('Required')
    expect(errors.size).toBe(6)
  })

  it('rejects a birth date in the future', () => {
    const rows = parseImportFile(`${HEADER}\n${row({ birth_date: '2099-01-01' })}`)
    expect(validateRows(rows).get('0:birth_date')).toMatch(/future/i)
  })
})

describe('issuesByRowIndex', () => {
  function blocked(rowNumber: number, reason: string): ImportRowResult {
    return {
      row_number: rowNumber,
      employee_number: 'EMP-1',
      name: 'Test Person',
      outcome: 'blocked',
      reason,
    }
  }

  it('lines a blocked row up with its table row, counting the header', () => {
    const issues = issuesByRowIndex([blocked(2, 'invalid salary')])
    expect(issues.has(0)).toBe(true)
  })

  it('picks the columns out of the API wording', () => {
    const issues = issuesByRowIndex([
      blocked(2, 'missing required field(s): position, salary'),
      blocked(3, "manager 'EMP-99999' not found in the file or the database"),
      blocked(4, 'this change would create a reporting cycle'),
      blocked(5, "email 'a@b.com' is already used by employee 'EMP-00001'"),
      blocked(6, "invalid birth_date '14/07/1992' (expected YYYY-MM-DD)"),
    ])

    expect([...issues.get(0)!.columns]).toEqual(expect.arrayContaining(['position', 'salary']))
    expect([...issues.get(1)!.columns]).toEqual(['manager_employee_number'])
    expect([...issues.get(2)!.columns]).toEqual(['manager_employee_number'])
    expect([...issues.get(3)!.columns]).toEqual(['email'])
    expect([...issues.get(4)!.columns]).toEqual(['birth_date'])
  })

  it('keeps the reason even when no column can be matched', () => {
    const issues = issuesByRowIndex([blocked(2, 'something unexpected happened')])
    expect(issues.get(0)?.reason).toBe('something unexpected happened')
    expect(issues.get(0)?.columns.size).toBe(0)
  })

  it('ignores rows that are going to import', () => {
    const passing: ImportRowResult = {
      row_number: 2,
      employee_number: 'EMP-1',
      name: 'Test Person',
      outcome: 'will_create',
      reason: null,
    }
    expect(issuesByRowIndex([passing]).size).toBe(0)
  })
})
