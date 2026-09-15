import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, getActorId } from '@/lib/apiClient'
import type { components } from '@/lib/api-types'
import { employeeKeys } from '@/lib/queryKeys'

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

function authHeader() {
  return { 'X-Actor-Id': getActorId() ?? '' }
}

export function useCreateEmployeeMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: EmployeeCreate) => {
      const { data, error } = await apiClient.POST('/api/v1/employees', {
        params: { header: authHeader() },
        body,
      })
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
          header: { ...authHeader(), 'If-Match': `"${version}"` },
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
          header: { ...authHeader(), 'If-Match': `"${version}"` },
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
        params: { path: { employee_id: id }, query: { policy }, header: authHeader() },
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
        params: { path: { employee_id: id }, header: authHeader() },
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
    params: { path: { employee_id: id }, query: { policy }, header: authHeader() },
  })
  if (error) throw error
  return data
}

export async function fetchEmployee(id: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}', {
    params: { path: { employee_id: id }, header: authHeader() },
  })
  if (error) throw error
  return data
}
