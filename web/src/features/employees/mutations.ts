import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import type { components } from '@/lib/api-types'
import { getAccessToken } from '@/lib/auth'
import { triggerDownload } from '@/lib/download'
import { employeeKeys, type EmployeeListFilters } from '@/lib/queryKeys'

type EmployeeCreate = components['schemas']['EmployeeCreate']
type EmployeeUpdate = components['schemas']['EmployeeUpdate']
type DeletionPolicy = 'reparent' | 'promote_to_root' | 'cascade'

/** Thrown by the update mutation on a 409 so callers can distinguish a
 * version conflict (§ conflict dialogue) from any other failure. */
export class VersionConflict extends Error {
  employeeId: string

  constructor(employeeId: string, message: string) {
    super(message)
    this.name = 'VersionConflict'
    this.employeeId = employeeId
  }
}

export function useCreateEmployeeMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: EmployeeCreate) => {
      const { data, error } = await apiClient.POST('/api/v1/employees', { body })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all })
    },
  })
}

export function useUpdateEmployeeMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      version,
      body,
    }: {
      id: string
      version: number
      body: EmployeeUpdate
    }) => {
      const { data, error, response } = await apiClient.PATCH('/api/v1/employees/{employee_id}', {
        params: {
          path: { employee_id: id },
          header: { 'If-Match': `"${version}"` },
        },
        body,
      })
      if (error) {
        if (response.status === 409) {
          throw new VersionConflict(id, 'The record changed since it was last read')
        }
        throw error
      }
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all })
    },
  })
}

export function useReassignManagerMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      version,
      managerId,
    }: {
      id: string
      version: number
      managerId: string | null
    }) => {
      const { data, error, response } = await apiClient.PUT('/api/v1/employees/{employee_id}/manager', {
        params: {
          path: { employee_id: id },
          header: { 'If-Match': `"${version}"` },
        },
        body: { manager_id: managerId },
      })
      if (error) {
        if (response.status === 409) {
          throw new VersionConflict(id, 'The record changed since it was last read')
        }
        throw error
      }
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all })
    },
  })
}

export function useDeleteEmployeeMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, policy }: { id: string; policy: DeletionPolicy }) => {
      const { error } = await apiClient.DELETE('/api/v1/employees/{employee_id}', {
        params: { path: { employee_id: id }, query: { policy } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all })
    },
  })
}

export function useRestoreEmployeeMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data, error } = await apiClient.POST('/api/v1/employees/{employee_id}/restore', {
        params: { path: { employee_id: id } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: employeeKeys.all })
    },
  })
}

export async function fetchDeletionPreview(id: string, policy: DeletionPolicy) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/deletion-preview', {
    params: { path: { employee_id: id }, query: { policy } },
  })
  if (error) throw error
  return data
}

export async function fetchEmployee(id: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}', {
    params: { path: { employee_id: id } },
  })
  if (error) throw error
  return data
}

/** `GET /exports/employees.csv` — a plain `fetch` with the bearer token
 * attached by hand, same as the import upload, since the response is a
 * file download rather than JSON the generated client expects. Honours
 * whatever filters/sort are currently applied on the list page, minus
 * pagination — the export is always the full filtered set. */
export async function exportEmployeesCsv(filters: EmployeeListFilters): Promise<void> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (key === 'page' || key === 'page_size' || value === undefined || value === null) continue
    params.set(key, String(value))
  }

  const token = getAccessToken()
  const response = await fetch(`/api/v1/exports/employees.csv?${params.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!response.ok) throw new Error('Failed to export employees')

  triggerDownload('employees.csv', await response.blob())
}

export async function fetchAuditLog(id: string, page: number) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/audit', {
    params: { path: { employee_id: id }, query: { page } },
  })
  if (error) throw error
  return data
}
