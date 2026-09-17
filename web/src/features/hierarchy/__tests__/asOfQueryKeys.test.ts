import { describe, expect, it } from 'vitest'
import { employeeKeys, hierarchyKeys } from '@/lib/queryKeys'
import { shiftIso } from '../useAsOf'

const ID = '11111111-1111-1111-1111-111111111111'

/**
 * §33: every hierarchy-shaped key must vary with as_of. A key that ignores it
 * would serve present-day data under a past-date banner - the quiet failure
 * this whole feature is most likely to produce.
 */
describe('hierarchy query keys carry as_of', () => {
  it('distinguishes two dates for every hierarchy key', () => {
    const a = '2026-09-17'
    const b = '2025-09-17'

    const pairs: Array<[readonly unknown[], readonly unknown[]]> = [
      [hierarchyKeys.roots(a), hierarchyKeys.roots(b)],
      [hierarchyKeys.tree(a), hierarchyKeys.tree(b)],
      [hierarchyKeys.tree(a, ID, 2), hierarchyKeys.tree(b, ID, 2)],
      [employeeKeys.subtree(ID, a), employeeKeys.subtree(ID, b)],
      [employeeKeys.subtree(ID, a, 2), employeeKeys.subtree(ID, b, 2)],
      [employeeKeys.reportingLine(ID, a), employeeKeys.reportingLine(ID, b)],
    ]

    for (const [first, second] of pairs) {
      expect(JSON.stringify(first)).not.toEqual(JSON.stringify(second))
    }
  })

  it('keeps the same key stable for the same date', () => {
    expect(employeeKeys.subtree(ID, '2026-09-17', 2)).toEqual(
      employeeKeys.subtree(ID, '2026-09-17', 2)
    )
  })

  it('separates a subtree from its depth-limited variant', () => {
    const asOf = '2026-09-17'
    expect(JSON.stringify(employeeKeys.subtree(ID, asOf, 1))).not.toEqual(
      JSON.stringify(employeeKeys.subtree(ID, asOf, 2))
    )
  })
})

describe('shiftIso', () => {
  it('steps back by whole months and years without drifting', () => {
    expect(shiftIso('2026-09-17', { months: -3 })).toBe('2026-06-17')
    expect(shiftIso('2026-09-17', { months: -12 })).toBe('2025-09-17')
  })

  it('clamps a month-end date rather than rolling into the next month', () => {
    expect(shiftIso('2026-03-31', { months: -1 })).toBe('2026-02-28')
    expect(shiftIso('2026-05-31', { months: -3 })).toBe('2026-02-28')
    expect(shiftIso('2024-05-31', { months: -3 })).toBe('2024-02-29')
  })
})
