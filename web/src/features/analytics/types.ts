import type { components } from '@/lib/api-types'

export type OrgSummary =
  | components['schemas']['OrgSummaryRead']
  | components['schemas']['OrgSummaryReadRestricted']

export type BranchSummary =
  | components['schemas']['BranchSummaryRead']
  | components['schemas']['BranchSummaryReadRestricted']

export type CostSummary = components['schemas']['CostSummaryRead']

/** A `viewer` payload omits `cost` entirely (§9.3) rather than nulling it -
 * this is how the client tells the two shapes apart. Overloaded rather than
 * generic: `OrgSummaryReadRestricted`/`BranchSummaryReadRestricted` don't
 * have a `cost` property at all, so a single generic constrained to
 * `{ cost?: CostSummary }` can't express either union. */
export function hasCost(
  summary: OrgSummary
): summary is components['schemas']['OrgSummaryRead']
export function hasCost(
  summary: BranchSummary
): summary is components['schemas']['BranchSummaryRead']
export function hasCost(summary: OrgSummary | BranchSummary): boolean {
  return 'cost' in summary
}
