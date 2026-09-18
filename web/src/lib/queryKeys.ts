import type { paths } from './api-types'

export type EmployeeListFilters = NonNullable<
  paths['/api/v1/employees']['get']['parameters']['query']
>

export const employeeKeys = {
  all: ['employees'] as const,
  lists: () => [...employeeKeys.all, 'list'] as const,
  positions: () => [...employeeKeys.all, 'positions'] as const,
  list: (filters: EmployeeListFilters) => [...employeeKeys.lists(), filters] as const,
  details: () => [...employeeKeys.all, 'detail'] as const,
  detail: (id: string) => [...employeeKeys.details(), id] as const,
  // asOf is a required argument on every hierarchy-shaped key, so a call site
  // cannot silently reuse present-day data under a past-date banner - the
  // compiler refuses to let you omit it.
  subtree: (id: string, asOf: string, depth?: number) =>
    [...employeeKeys.detail(id), 'subtree', asOf, depth] as const,
  reportingLine: (id: string, asOf: string) =>
    [...employeeKeys.detail(id), 'reporting-line', asOf] as const,
  assignmentHistory: (id: string) =>
    [...employeeKeys.detail(id), 'assignment-history'] as const,
  auditLog: (id: string, page?: number) => [...employeeKeys.detail(id), 'audit', page] as const,
  deletionPreview: (id: string, policy: string) =>
    [...employeeKeys.detail(id), 'deletion-preview', policy] as const,
}

export const profileKeys = {
  me: () => ['profile'] as const,
}

export const hierarchyKeys = {
  all: ['hierarchy'] as const,
  roots: (asOf: string) => [...hierarchyKeys.all, 'roots', asOf] as const,
  tree: (asOf: string, rootId?: string, depth?: number) =>
    [...hierarchyKeys.all, 'tree', asOf, rootId, depth] as const,
  scheduled: () => [...hierarchyKeys.all, 'scheduled'] as const,
  diff: (from: string, to: string) => [...hierarchyKeys.all, 'diff', from, to] as const,
}

export const analyticsKeys = {
  all: ['analytics'] as const,
  orgSummary: () => [...analyticsKeys.all, 'org-summary'] as const,
  branch: (employeeId: string) => [...analyticsKeys.all, 'branch', employeeId] as const,
}

export const searchKeys = {
  results: (q: string) => ['search', q] as const,
}

export const globalAuditKeys = {
  all: ['audit', 'global'] as const,
  page: (page: number) => [...globalAuditKeys.all, page] as const,
}
