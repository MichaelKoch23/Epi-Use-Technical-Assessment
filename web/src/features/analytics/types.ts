import type { components } from '@/lib/api-types'

export type OrgSummary =
  | components['schemas']['OrgSummaryRead']
  | components['schemas']['OrgSummaryReadRestricted']

export type BranchSummary =
  | components['schemas']['BranchSummaryRead']
  | components['schemas']['BranchSummaryReadRestricted']

export type CostSummary = components['schemas']['CostSummaryRead']

export function hasCost(
  summary: OrgSummary
): summary is components['schemas']['OrgSummaryRead']
export function hasCost(
  summary: BranchSummary
): summary is components['schemas']['BranchSummaryRead']
export function hasCost(summary: OrgSummary | BranchSummary): boolean {
  return 'cost' in summary
}
