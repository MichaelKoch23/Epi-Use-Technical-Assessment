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
  subtree: (id: string, depth?: number) =>
    [...employeeKeys.detail(id), 'subtree', depth] as const,
  reportingLine: (id: string) => [...employeeKeys.detail(id), 'reporting-line'] as const,
  auditLog: (id: string, page?: number) => [...employeeKeys.detail(id), 'audit', page] as const,
  deletionPreview: (id: string, policy: string) =>
    [...employeeKeys.detail(id), 'deletion-preview', policy] as const,
}

export const profileKeys = {
  me: () => ['profile'] as const,
}

export const hierarchyKeys = {
  roots: () => ['hierarchy', 'roots'] as const,
}

export const analyticsKeys = {
  orgSummary: () => ['analytics', 'org-summary'] as const,
  branch: (employeeId: string) => ['analytics', 'branch', employeeId] as const,
}

export const searchKeys = {
  results: (q: string) => ['search', q] as const,
}

export const globalAuditKeys = {
  all: ['audit', 'global'] as const,
  page: (page: number) => [...globalAuditKeys.all, page] as const,
}
