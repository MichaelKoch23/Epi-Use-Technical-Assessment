import { apiClient } from '@/lib/apiClient'
import type { components } from '@/lib/api-types'

export type MovePreview =
  | components['schemas']['MovePreviewRead']
  | components['schemas']['MovePreviewReadRestricted']
export type StructureDiff =
  | components['schemas']['StructureDiffRead']
  | components['schemas']['StructureDiffReadRestricted']
export type ScheduledAssignment = components['schemas']['ScheduledAssignmentRead']
export type AssignmentHistoryItem = components['schemas']['AssignmentHistoryItemRead']
export type CancelledAssignment = components['schemas']['CancelledAssignmentRead']

export function hasCostDelta(
  preview: MovePreview
): preview is components['schemas']['MovePreviewRead'] {
  return 'cost_delta' in preview
}

export function hasDiffCost(
  diff: StructureDiff
): diff is components['schemas']['StructureDiffRead'] {
  return 'cost' in diff
}

export async function fetchScheduled(): Promise<ScheduledAssignment[]> {
  const { data, error } = await apiClient.GET('/api/v1/hierarchy/scheduled')
  if (error) throw error
  return data.items
}

export async function cancelScheduled(assignmentId: string): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/hierarchy/scheduled/{assignment_id}', {
    params: { path: { assignment_id: assignmentId } },
  })
  if (error) throw error
}

export async function fetchMovePreview(
  employeeId: string,
  newManagerId: string | null,
  asOf: string
): Promise<MovePreview> {
  const { data, error } = await apiClient.POST('/api/v1/employees/{employee_id}/move-preview', {
    params: { path: { employee_id: employeeId } },
    body: { new_manager_id: newManagerId, as_of: asOf },
  })
  if (error) throw error
  return data
}

export async function fetchAssignmentHistory(
  employeeId: string
): Promise<AssignmentHistoryItem[]> {
  const { data, error } = await apiClient.GET(
    '/api/v1/employees/{employee_id}/assignment-history',
    { params: { path: { employee_id: employeeId } } }
  )
  if (error) throw error
  return data.items
}

export async function fetchStructureDiff(from: string, to: string): Promise<StructureDiff> {
  const { data, error } = await apiClient.GET('/api/v1/hierarchy/diff', {
    params: { query: { from, to } },
  })
  if (error) throw error
  return data
}
